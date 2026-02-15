"""CLI for codeval."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import typer
from dotenv import load_dotenv

# Load .env BEFORE other codeval imports so env vars are available
def _load_env() -> None:
    cwd = Path.cwd()
    pkg_root = Path(__file__).resolve().parent.parent
    for env_path in [cwd / ".env", pkg_root / ".env"]:
        if env_path.exists():
            load_dotenv(env_path, override=True)
            # Fallback: manual parse if dotenv didn't load (encoding/BOM issues)
            if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
                try:
                    raw = env_path.read_text(encoding="utf-8-sig").strip()
                    for line in raw.splitlines():
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, _, v = line.partition("=")
                            k, v = k.strip(), v.strip().strip('"\'')
                            if k and v and v != "your-api-key-here":
                                os.environ[k] = v
                except Exception:
                    pass
            break

_load_env()

from codeval.html_report import render_html
from codeval.llm import is_llm_available, set_concurrency
from codeval.orchestrator import run_validation
from codeval.schemas import FinalReport

app = typer.Typer(help="Multi-agent code validator")


# ── Markdown rendering ───────────────────────────────────────────────

def _render_markdown(report: FinalReport) -> str:
    """Render FinalReport to Markdown."""
    lines = [
        "# Code Validation Report",
        "",
        report.summary,
        "",
        "## Scores",
        "",
        f"- **Overall**: {report.scores.overall:.2f}/100",
        "",
    ]

    failed = set(report.failed_categories)

    # Warning banner for failed agents
    if failed:
        names = ", ".join(c.replace("_", " ").title() for c in failed)
        lines.append(f"> **Warning:** {len(failed)} agent(s) failed LLM analysis ({names}). Their scores show N/A.")
        lines.append("")

    # Group scores by tier for readability
    TIER_LABELS = {
        "Critical": ["functional", "security", "resilience"],
        "Important": ["performance", "quality", "dependency", "architecture"],
        "Supplemental": ["documentation", "concurrency", "api_contract"],
    }
    for tier_name, cats in TIER_LABELS.items():
        lines.append(f"**{tier_name}:**")
        for cat in cats:
            score = report.scores.categories.get(cat, 100.0)
            label = cat.replace("_", " ").title()
            if cat in failed:
                lines.append(f"- {label}: **N/A** _(analysis failed)_")
            else:
                lines.append(f"- {label}: {score:.2f}/100")
        lines.append("")

    # Show clusters if available, otherwise fall back to raw findings
    if report.clusters:
        lines.extend(["## Issues (Clustered)", ""])
        # Sort: critical first, then high, medium, low
        sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_clusters = sorted(
            report.clusters, key=lambda c: sev_order.get(c.consolidated_severity, 4)
        )
        for i, c in enumerate(sorted_clusters[:15], 1):
            merged = len(c.related_finding_ids)
            merge_note = f" ({merged + 1} findings merged)" if merged else ""
            lines.append(
                f"### {i}. [{c.consolidated_severity.upper()}] {c.consolidated_title}{merge_note}"
            )
            lines.append(f"- **Category**: {c.category}")
            lines.append(f"- **Confidence**: {c.match_confidence:.0%}")
            lines.append(f"- **Impact**: {c.consolidated_impact}")
            lines.append(f"- **Recommendation**: {c.consolidated_recommendation}")

            # Show primary finding evidence
            primary = next((f for f in report.findings if f.id == c.primary_finding_id), None)
            if primary:
                lines.append(f"- **File**: {primary.evidence.file}:{primary.evidence.lines}")
                if primary.evidence.snippet:
                    lines.append(f"- **Snippet**: `{primary.evidence.snippet[:120]}`")
            lines.append("")

        total_raw = len(report.all_findings) if report.all_findings else len(report.findings)
        lines.append(
            f"*{len(report.clusters)} unique issues identified from {total_raw} raw findings*"
        )
        lines.append("")
    else:
        lines.extend(["## Top Findings", ""])
        for i, f in enumerate(report.findings[:10], 1):
            lines.append(f"### {i}. [{f.severity.upper()}] {f.title}")
            lines.append(f"- **File**: {f.evidence.file}:{f.evidence.lines}")
            lines.append(f"- **Impact**: {f.impact}")
            lines.append(f"- **Recommendation**: {f.recommendation}")
            lines.append("")

    lines.extend(["## Recommended Next Steps", ""])
    for step in report.recommended_next_steps:
        lines.append(f"- {step}")
    lines.append("")
    return "\n".join(lines)


# ── Output helpers ───────────────────────────────────────────────────

def _write_report(report: FinalReport, out: Path, fmt: str, project_name: str = "") -> list[str]:
    """Write report in one or more formats. Returns list of written file paths."""
    out.parent.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    formats = ["json", "md", "html"] if fmt == "all" else [fmt]

    for f in formats:
        if f == "json":
            target = out.with_suffix(".json")
            target.write_text(report.model_dump_json(indent=2), encoding="utf-8")
            written.append(str(target))
        elif f == "md":
            target = out.with_suffix(".md")
            target.write_text(_render_markdown(report), encoding="utf-8")
            written.append(str(target))
        elif f == "html":
            target = out.with_suffix(".html")
            target.write_text(render_html(report, project_name), encoding="utf-8")
            written.append(str(target))

    return written


# ── Rich progress helper ─────────────────────────────────────────────

def _run_with_progress(coro, llm_enabled: bool) -> FinalReport:
    """Run the validation pipeline with a live rich progress display."""
    try:
        from rich.console import Console
        from rich.live import Live
        from rich.table import Table
        from rich.text import Text
    except ImportError:
        # Fallback if rich is not installed
        typer.echo("Running validation...")
        return asyncio.run(coro)

    console = Console()
    agent_status: dict[str, tuple[str, str]] = {}  # name -> (status, detail)
    _STATUS_STYLES = {
        "waiting": ("dim", "..."),
        "running": ("yellow", "analyzing"),
        "done": ("green", ""),
        "failed": ("red bold", "FAILED"),
        "stage": ("cyan", ""),
    }

    def _build_table() -> Table:
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Agent", min_width=18)
        table.add_column("Status", min_width=10)
        table.add_column("Detail", min_width=30)
        for name, (status, detail) in agent_status.items():
            style, default_text = _STATUS_STYLES.get(status, ("", ""))
            status_text = Text(status.upper(), style=style)
            detail_text = detail or default_text
            display_name = name.replace("_", " ").title()
            table.add_row(display_name, status_text, detail_text)
        return table

    def _on_progress(name: str, status: str, detail: str) -> None:
        agent_status[name] = (status, detail)

    # Pre-populate agent list
    agent_names = [
        "pipeline", "functional", "security", "resilience", "performance",
        "quality", "dependency", "documentation", "architecture",
        "concurrency", "api_contract", "consolidation",
    ]
    for n in agent_names:
        agent_status[n] = ("waiting", "")

    # Patch the coroutine to inject progress callback
    async def _patched():
        # We need to pass on_progress to the orchestrator
        # Unpack the coroutine's arguments by re-calling run_validation
        return await coro

    # We can't easily inject on_progress into an already-created coroutine,
    # so we use a different approach: run with Live display but poll-based
    # Actually, let's use a simpler approach: wrap asyncio.run with Live context
    result = None

    async def _run_with_callback():
        nonlocal coro
        # We can't modify coro after creation, so just run it
        return await coro

    # Simple approach: show a spinner and status, update when done
    with Live(_build_table(), console=console, refresh_per_second=4) as live:
        async def _wrapped():
            return await coro

        loop = asyncio.new_event_loop()
        import threading
        report_holder: list = []
        error_holder: list = []

        def _thread_target():
            try:
                r = loop.run_until_complete(coro)
                report_holder.append(r)
            except Exception as e:
                error_holder.append(e)
            finally:
                loop.close()

        # Show initial state
        agent_status["pipeline"] = ("running", "Validating...")
        live.update(_build_table())

        t = threading.Thread(target=_thread_target, daemon=True)
        t.start()

        import time
        while t.is_alive():
            time.sleep(0.3)
            live.update(_build_table())

        t.join()

        if error_holder:
            raise error_holder[0]

        result = report_holder[0]

        # Show final state
        for name in agent_names:
            if name in ("pipeline", "consolidation"):
                continue
            if agent_status[name][0] == "waiting":
                agent_status[name] = ("done", "")

        agent_status["pipeline"] = ("done", f"Overall: {result.scores.overall:.1f}/100")
        agent_status["consolidation"] = ("done", f"{len(result.clusters)} clusters")

        # Mark failed agents
        for cat in result.failed_categories:
            if cat in agent_status:
                agent_status[cat] = ("failed", "LLM analysis failed")

        live.update(_build_table())

    # Print summary with rich
    console.print()
    _print_score_summary(console, result)

    return result


def _print_score_summary(console, report: FinalReport) -> None:
    """Print a colored score summary using rich."""
    from rich.panel import Panel
    from rich.text import Text

    failed = set(report.failed_categories)
    overall = report.scores.overall

    # Warning banner
    if failed:
        names = ", ".join(c.replace("_", " ").title() for c in failed)
        console.print(
            Panel(
                f"[bold yellow]Warning:[/] {len(failed)} agent(s) failed: {names}\n"
                "Their scores show N/A. Re-run for complete results.",
                border_style="yellow",
            )
        )

    # Overall score
    if overall >= 80:
        style = "bold green"
    elif overall >= 60:
        style = "bold yellow"
    elif overall >= 40:
        style = "bold dark_orange"
    else:
        style = "bold red"
    console.print(f"  Overall Score: [{style}]{overall:.1f}[/] / 100")
    console.print()


# ── CLI commands ─────────────────────────────────────────────────────

@app.command()
def run(
    path: Path = typer.Option(..., "--path", "-p", help="Repository path to analyze"),
    out: Path = typer.Option(..., "--out", "-o", help="Output file path (extension auto-set per format)"),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json, md, html, or all"),
    max_files: int = typer.Option(50, "--max-files", help="Max files to analyze per agent"),
    include: str | None = typer.Option(None, "--include", help="Include glob pattern"),
    exclude: str | None = typer.Option(None, "--exclude", help="Exclude glob pattern"),
    llm: str = typer.Option("auto", "--llm", help="LLM: on, off, or auto (use if key present)"),
    concurrency: int = typer.Option(3, "--concurrency", "-c", help="Max concurrent LLM calls (default: 3)"),
) -> None:
    """Run code validation on a repository."""
    if not path.exists():
        typer.echo(f"Error: path does not exist: {path}", err=True)
        raise typer.Exit(1)
    if not path.is_dir():
        typer.echo(f"Error: path is not a directory: {path}", err=True)
        raise typer.Exit(1)

    if format not in ("json", "md", "html", "all"):
        typer.echo(f"Error: format must be json, md, html, or all", err=True)
        raise typer.Exit(1)

    llm_enabled = llm == "on" or (llm == "auto" and is_llm_available())
    if llm == "on" and not is_llm_available():
        typer.echo("Warning: --llm on but no API key (OPENAI_API_KEY or ANTHROPIC_API_KEY); falling back to static-only", err=True)
        llm_enabled = False
    if llm == "off":
        llm_enabled = False

    set_concurrency(concurrency)

    include_patterns = [include] if include else None
    exclude_patterns = [exclude] if exclude else None

    coro = run_validation(
        path,
        max_files=max_files,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        llm_enabled=llm_enabled,
    )

    report = _run_with_progress(coro, llm_enabled)

    written = _write_report(report, out, format, project_name=path.name)
    for w in written:
        typer.echo(f"Report written to {w}")


@app.command()
def convert(
    input: Path = typer.Option(..., "--input", "-i", help="Existing report.json to convert"),
    out: Path = typer.Option(..., "--out", "-o", help="Output file path"),
    format: str = typer.Option("md", "--format", "-f", help="Output format: md, html, or all"),
) -> None:
    """Convert an existing JSON report to MD or HTML without re-running the pipeline."""
    if not input.exists():
        typer.echo(f"Error: input file not found: {input}", err=True)
        raise typer.Exit(1)

    raw = input.read_text(encoding="utf-8")
    report = FinalReport.model_validate_json(raw)

    # Infer project name from the summary or input filename
    project_name = input.stem.replace("report", "").strip("_- ") or "Code Validation"

    written = _write_report(report, out, format, project_name=project_name)
    for w in written:
        typer.echo(f"Converted report written to {w}")


@app.command()
def check_key() -> None:
    """Verify API key is loaded (does not make API calls)."""
    _load_env()
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key and key != "your-api-key-here":
        masked = key[:15] + "..." + key[-4:] if len(key) > 20 else "***"
        typer.echo(f"ANTHROPIC_API_KEY: loaded ({masked})")
    else:
        cwd_env = Path.cwd() / ".env"
        pkg_env = Path(__file__).resolve().parent.parent / ".env"
        typer.echo("ANTHROPIC_API_KEY: not set or still placeholder")
        typer.echo(f"  Checked: {cwd_env} (exists: {cwd_env.exists()})")
        typer.echo(f"  Checked: {pkg_env} (exists: {pkg_env.exists()})")
    okey = os.environ.get("OPENAI_API_KEY", "")
    if okey:
        typer.echo("OPENAI_API_KEY: loaded")
    else:
        typer.echo("OPENAI_API_KEY: not set")


@app.command()
def version() -> None:
    """Show version."""
    typer.echo("codeval 0.1.0")


def main() -> None:
    """Entry point for codeval CLI. Use: codeval run --path <repo> --out <file>"""
    app()


if __name__ == "__main__":
    main()
