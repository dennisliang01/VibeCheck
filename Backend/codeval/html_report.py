"""Generate a self-contained HTML validation report.

The output is a single HTML file with all CSS/JS inlined -- no external
dependencies.  Designed to look polished when opened in any browser, including
projector screens at hackathon demos.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

from codeval.schemas import FinalReport

# ── Severity styling ─────────────────────────────────────────────────
_SEV_COLORS = {
    "critical": "#dc2626",
    "high": "#ea580c",
    "medium": "#ca8a04",
    "low": "#2563eb",
}
_SEV_BG = {
    "critical": "#fef2f2",
    "high": "#fff7ed",
    "medium": "#fefce8",
    "low": "#eff6ff",
}


def _score_color(score: float) -> str:
    """Map score to a color on a red-yellow-green gradient."""
    if score < 0:
        return "#94a3b8"  # slate for N/A
    if score >= 80:
        return "#16a34a"
    if score >= 60:
        return "#ca8a04"
    if score >= 40:
        return "#ea580c"
    return "#dc2626"


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def render_html(report: FinalReport, project_name: str = "") -> str:
    """Render a FinalReport to a self-contained HTML string."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    name = _esc(project_name or "Code Validation Report")
    overall = report.scores.overall
    overall_color = _score_color(overall)
    failed = set(report.failed_categories)

    # ── Category bars ─────────────────────────────────────────────
    TIER_ORDER = [
        ("Critical", ["functional", "security", "resilience"]),
        ("Important", ["performance", "quality", "dependency", "architecture"]),
        ("Supplemental", ["documentation", "concurrency", "api_contract"]),
    ]
    cat_rows = []
    for tier_name, cats in TIER_ORDER:
        cat_rows.append(f'<tr><td colspan="3" class="tier-header">{tier_name}</td></tr>')
        for cat in cats:
            score = report.scores.categories.get(cat, 100.0)
            label = cat.replace("_", " ").title()
            if cat in failed:
                cat_rows.append(
                    f'<tr>'
                    f'<td class="cat-name">{label}</td>'
                    f'<td class="cat-bar"><div class="bar-track"><div class="bar-fill bar-na" style="width:100%"></div></div></td>'
                    f'<td class="cat-score na-badge">N/A</td>'
                    f'</tr>'
                )
            else:
                color = _score_color(score)
                pct = max(0, min(100, score))
                cat_rows.append(
                    f'<tr>'
                    f'<td class="cat-name">{label}</td>'
                    f'<td class="cat-bar"><div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{color}"></div></div></td>'
                    f'<td class="cat-score" style="color:{color}">{score:.1f}</td>'
                    f'</tr>'
                )
    cat_table = "\n".join(cat_rows)

    # ── Warning banner ────────────────────────────────────────────
    warning_html = ""
    if failed:
        names = ", ".join(c.replace("_", " ").title() for c in failed)
        warning_html = (
            f'<div class="warning-banner">'
            f'<strong>Warning:</strong> {len(failed)} agent(s) failed LLM analysis '
            f'({names}). Their scores show N/A. Re-run to get complete results.'
            f'</div>'
        )

    # ── Issue cards ───────────────────────────────────────────────
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_clusters = sorted(
        report.clusters,
        key=lambda c: sev_order.get(c.consolidated_severity, 4),
    )

    finding_map = {f.id: f for f in (report.all_findings or report.findings)}
    issue_cards = []
    for i, c in enumerate(sorted_clusters, 1):
        sev = c.consolidated_severity
        sev_color = _SEV_COLORS.get(sev, "#6b7280")
        sev_bg = _SEV_BG.get(sev, "#f9fafb")
        primary = finding_map.get(c.primary_finding_id)
        merged_count = len(c.related_finding_ids)
        merge_badge = f' <span class="merge-badge">+{merged_count} merged</span>' if merged_count else ""
        cat_label = c.category.replace("_", " ").title()

        evidence_html = ""
        if primary and primary.evidence.snippet:
            snippet = _esc(primary.evidence.snippet[:500])
            file_ref = _esc(f"{primary.evidence.file}:{primary.evidence.lines}")
            evidence_html = (
                f'<div class="evidence">'
                f'<div class="evidence-file">{file_ref}</div>'
                f'<pre><code>{snippet}</code></pre>'
                f'</div>'
            )

        issue_cards.append(
            f'<div class="issue-card" style="border-left:4px solid {sev_color};background:{sev_bg}">'
            f'<div class="issue-header">'
            f'<span class="sev-badge" style="background:{sev_color}">{sev.upper()}</span>'
            f'<span class="issue-title">{_esc(c.consolidated_title)}{merge_badge}</span>'
            f'<span class="issue-cat">{cat_label}</span>'
            f'</div>'
            f'<div class="issue-body">'
            f'<p><strong>Impact:</strong> {_esc(c.consolidated_impact)}</p>'
            f'<p><strong>Recommendation:</strong> {_esc(c.consolidated_recommendation)}</p>'
            f'{evidence_html}'
            f'</div>'
            f'</div>'
        )
    issues_html = "\n".join(issue_cards) if issue_cards else '<p class="no-issues">No issues found.</p>'

    n_raw = len(report.all_findings) if report.all_findings else len(report.findings)
    n_clusters = len(report.clusters)

    # ── Next steps ────────────────────────────────────────────────
    steps_html = "\n".join(
        f"<li>{_esc(s)}</li>" for s in report.recommended_next_steps
    )

    # ── Donut chart (pure CSS) ────────────────────────────────────
    # conic-gradient for the donut
    pct = max(0, min(100, overall))
    donut_gradient = f"conic-gradient({overall_color} {pct * 3.6}deg, #e5e7eb {pct * 3.6}deg)"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name}</title>
<style>
*,*::before,*::after{{box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  margin:0;padding:0;background:#f8fafc;color:#1e293b;line-height:1.6}}
.container{{max-width:960px;margin:0 auto;padding:2rem 1.5rem}}
header{{text-align:center;padding:2rem 0 1rem}}
header h1{{margin:0;font-size:1.75rem;color:#0f172a}}
header .subtitle{{color:#64748b;font-size:0.95rem}}
.warning-banner{{background:#fef3c7;border:1px solid #f59e0b;border-radius:8px;
  padding:0.75rem 1rem;margin:1rem 0;color:#92400e;font-size:0.9rem}}
.score-section{{display:flex;align-items:center;gap:2rem;margin:1.5rem 0;
  background:#fff;border-radius:12px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.08)}}
.donut-wrap{{position:relative;width:140px;height:140px;flex-shrink:0}}
.donut{{width:140px;height:140px;border-radius:50%;
  background:{donut_gradient};
  display:flex;align-items:center;justify-content:center}}
.donut-hole{{width:100px;height:100px;border-radius:50%;background:#fff;
  display:flex;align-items:center;justify-content:center;flex-direction:column}}
.donut-score{{font-size:1.8rem;font-weight:700;color:{overall_color};line-height:1}}
.donut-label{{font-size:0.7rem;color:#64748b;margin-top:2px}}
.cat-table{{flex:1;width:100%;border-collapse:collapse}}
.cat-table td{{padding:0.3rem 0.5rem;font-size:0.85rem}}
.tier-header{{font-weight:600;color:#475569;padding-top:0.6rem !important;font-size:0.8rem;
  text-transform:uppercase;letter-spacing:0.05em}}
.cat-name{{width:130px;color:#334155}}
.cat-bar{{width:auto}}
.bar-track{{height:10px;background:#e2e8f0;border-radius:5px;overflow:hidden;min-width:120px}}
.bar-fill{{height:100%;border-radius:5px;transition:width 0.5s}}
.bar-na{{background:#cbd5e1}}
.cat-score{{width:50px;text-align:right;font-weight:600;font-size:0.85rem}}
.na-badge{{color:#94a3b8;font-style:italic}}
h2{{font-size:1.25rem;color:#0f172a;margin:2rem 0 1rem;padding-bottom:0.5rem;
  border-bottom:2px solid #e2e8f0}}
.issues-meta{{color:#64748b;font-size:0.85rem;margin-bottom:1rem}}
.issue-card{{border-radius:8px;padding:1rem 1.25rem;margin-bottom:0.75rem}}
.issue-header{{display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap}}
.sev-badge{{color:#fff;padding:2px 8px;border-radius:4px;font-size:0.7rem;
  font-weight:700;letter-spacing:0.03em}}
.issue-title{{font-weight:600;font-size:0.95rem;flex:1}}
.issue-cat{{font-size:0.75rem;color:#64748b;background:#f1f5f9;padding:2px 8px;
  border-radius:4px}}
.merge-badge{{font-size:0.7rem;color:#6b7280;font-weight:400}}
.issue-body{{margin-top:0.5rem;font-size:0.88rem}}
.issue-body p{{margin:0.25rem 0}}
.evidence{{margin-top:0.5rem;background:#f8fafc;border:1px solid #e2e8f0;
  border-radius:6px;overflow:hidden}}
.evidence-file{{padding:0.3rem 0.75rem;background:#f1f5f9;font-size:0.75rem;
  color:#475569;font-family:monospace}}
.evidence pre{{margin:0;padding:0.5rem 0.75rem;overflow-x:auto;font-size:0.8rem;
  line-height:1.5}}
.evidence code{{font-family:"Fira Code","Cascadia Code",Consolas,monospace}}
.no-issues{{color:#16a34a;font-weight:500}}
.steps ol{{padding-left:1.5rem}}
.steps li{{margin-bottom:0.3rem;font-size:0.9rem}}
footer{{text-align:center;padding:2rem 0 1rem;color:#94a3b8;font-size:0.75rem;
  border-top:1px solid #e2e8f0;margin-top:2rem}}
@media(max-width:700px){{
  .score-section{{flex-direction:column;align-items:center}}
  .donut-wrap{{margin-bottom:1rem}}
}}
</style>
</head>
<body>
<div class="container">

<header>
  <h1>{name}</h1>
  <div class="subtitle">Generated {now} by codeval 0.1.0</div>
</header>

{warning_html}

<div class="score-section">
  <div class="donut-wrap">
    <div class="donut">
      <div class="donut-hole">
        <div class="donut-score">{overall:.0f}</div>
        <div class="donut-label">/ 100</div>
      </div>
    </div>
  </div>
  <table class="cat-table">
    {cat_table}
  </table>
</div>

<h2>Issues ({n_clusters} unique from {n_raw} raw findings)</h2>
<div class="issues-section">
  {issues_html}
</div>

<div class="steps">
  <h2>Recommended Next Steps</h2>
  <ol>{steps_html}</ol>
</div>

<footer>
  codeval &middot; Multi-Agent Code Validator &middot; {now}
</footer>

</div>
</body>
</html>"""
