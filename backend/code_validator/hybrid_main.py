"""Hybrid Main Entry Point - Supports both static and LLM-powered analysis."""

import argparse
import json
import sys
import os
import traceback
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Load .env from code_validator directory (OPENAI_API_KEY, ANTHROPIC_API_KEY)
_env_path = Path(__file__).parent / ".env"
_env_file_exists = _env_path.exists()
_env_loaded = False
try:
    from dotenv import load_dotenv
    _env_loaded = load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv not installed, use shell env only

from core.coordinator import CoordinatorAgent
from core.models import ValidationReport
from utils.zip_handler import ZipHandler
from core.validation_logger import logger, LogLevel, EventType


def _mask_key(key: str) -> str:
    """Mask API key for safe display (e.g. sk-***...xyz1)."""
    if not key or len(key) < 12:
        return "***" if key else ""
    return key[:7] + "***" + key[-4:]


def print_env_status():
    """Print whether .env is connected and if API keys are accessible (keys masked unless SHOW_API_KEYS=1)."""
    print("=" * 60)
    print("ENV / API KEYS STATUS")
    print("=" * 60)
    print(f"  .env file path     : {_env_path.resolve()}")
    print(f"  .env file exists   : {'yes' if _env_file_exists else 'no'}")
    try:
        from dotenv import load_dotenv
        print(f"  .env loaded        : {'yes' if _env_loaded else 'no (or no new vars)'}")
    except ImportError:
        print("  .env loaded        : N/A (python-dotenv not installed)")
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    show_full = os.getenv("SHOW_API_KEYS", "").strip() in ("1", "true", "yes")
    if show_full:
        print(f"  OPENAI_API_KEY     : {repr(openai_key) if openai_key else 'NOT SET'}")
        print(f"  ANTHROPIC_API_KEY  : {repr(anthropic_key) if anthropic_key else 'NOT SET'}")
        print("  (full keys shown because SHOW_API_KEYS=1)")
    else:
        print(f"  OPENAI_API_KEY     : {'set (' + _mask_key(openai_key) + ')' if openai_key else 'NOT SET'}")
        print(f"  ANTHROPIC_API_KEY  : {'set (' + _mask_key(anthropic_key) + ')' if anthropic_key else 'NOT SET'}")
        print("  (set SHOW_API_KEYS=1 to print full keys)")
    print("=" * 60)
    print()


def check_llm_setup():
    """Check if LLM environment is properly configured."""
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not openai_key and not anthropic_key:
        print("=" * 80)
        print("⚠️  WARNING: No LLM API keys configured!")
        print("=" * 80)
        print()
        print("The hybrid system will fall back to static analysis only.")
        print()
        print("To enable LLM analysis, either:")
        print("  1. Create a .env file in this directory (copy from .env.example)")
        print("  2. Or set environment variables:")
        print("     export OPENAI_API_KEY='sk-...'")
        print("     export ANTHROPIC_API_KEY='sk-ant-...'")
        print()
        print("Install the required packages:")
        print("  pip install openai anthropic")
        print()
        print("Continuing with static analysis only...")
        print("=" * 80)
        print()
        return False

    return True


def format_report_as_text(report: ValidationReport, show_llm_info: bool = True) -> str:
    """Format validation report as human-readable text with LLM info."""
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("AI CODE VALIDATION REPORT - HYBRID EDITION")
    lines.append("=" * 80)
    lines.append("")

    # Verdict
    verdict_emoji = {"SHIP": "🟢", "FIX": "🟡", "BLOCK": "🔴"}
    lines.append(
        f"VERDICT: {verdict_emoji.get(report.verdict.value, '⚪')} {report.verdict.value}"
    )
    lines.append(f"GLOBAL SCORE: {report.global_score}/100")

    # LLM Info
    if show_llm_info:
        llm_findings = sum(
            1
            for r in report.agent_results.values()
            for f in r.findings
            if f.get("source") == "llm"
        )
        if llm_findings > 0:
            lines.append(f"LLM-ENHANCED FINDINGS: {llm_findings}")

    lines.append("")

    # Detailed scores
    lines.append("-" * 80)
    lines.append("DETAILED SCORES")
    lines.append("-" * 80)
    for category, score in sorted(report.detailed_scores.items(), key=lambda x: -x[1]):
        bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))

        # Indicate if LLM was used
        agent_result = report.agent_results.get(category)
        llm_indicator = ""
        if agent_result and show_llm_info:
            raw = agent_result.raw_analysis
            if raw.get("llm_findings") is not None:
                llm_indicator = f" [LLM:{raw.get('llm_findings', 0)}]"
            elif raw.get("static_findings") is not None:
                llm_indicator = " [STATIC]"

        lines.append(f"  {category:20s} [{bar}] {score:3d}/100{llm_indicator}")
    lines.append("")

    # Blocking critiques
    if report.blocking_critiques:
        lines.append("-" * 80)
        lines.append("🚫 BLOCKING CRITIQUES")
        lines.append("-" * 80)
        for i, critique in enumerate(report.blocking_critiques, 1):
            lines.append(f"  {i}. {critique}")
        lines.append("")

    # Recommendations
    if report.recommendations:
        lines.append("-" * 80)
        lines.append("📋 PRIORITIZED RECOMMENDATIONS")
        lines.append("-" * 80)

        severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}

        for i, rec in enumerate(report.recommendations[:20], 1):
            emoji = severity_emoji.get(rec.severity.value, "⚪")
            source_indicator = ""
            if show_llm_info and hasattr(rec, "source"):
                source_indicator = f" [{rec.source.upper()}]" if rec.source else ""

            lines.append(
                f"\n  {i}. {emoji} [{rec.severity.value.upper()}]{source_indicator} {rec.category}"
            )
            lines.append(f"     Description: {rec.description}")
            lines.append(f"     Fix: {rec.fix_suggested}")
            if rec.file:
                lines.append(f"     Location: {rec.file}:{rec.line or '?'}")

        if len(report.recommendations) > 20:
            lines.append(
                f"\n  ... and {len(report.recommendations) - 20} more recommendations"
            )
        lines.append("")

    # Executive summary
    lines.append("-" * 80)
    lines.append("📝 EXECUTIVE SUMMARY")
    lines.append("-" * 80)
    lines.append(f"  {report.executive_summary}")
    lines.append("")

    # LLM Analysis Summary
    if show_llm_info:
        lines.append("-" * 80)
        lines.append("🤖 LLM ANALYSIS SUMMARY")
        lines.append("-" * 80)

        for agent_name, result in report.agent_results.items():
            raw = result.raw_analysis
            if raw.get("llm_findings") is not None:
                lines.append(f"\n  {agent_name.upper()}:")
                lines.append(f"    Static findings: {raw.get('static_findings', 0)}")
                lines.append(f"    LLM findings: {raw.get('llm_findings', 0)}")
                lines.append(f"    Fused findings: {raw.get('fused_findings', 0)}")
                if raw.get("llm_model"):
                    lines.append(f"    LLM model: {raw.get('llm_model')}")

    lines.append("")
    lines.append("=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)

    return "\n".join(lines)


def main():
    """Main entry point for hybrid validation."""
    print_env_status()
    parser = argparse.ArgumentParser(
        description="AI Code Validation - Hybrid Edition (Static + LLM)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (auto-detects LLM availability)
  python hybrid_main.py code.zip
  
  # Force static-only mode
  python hybrid_main.py code.zip --static-only
  
  # Specify LLM provider
  python hybrid_main.py code.zip --llm-provider anthropic
  
  # With user story
  python hybrid_main.py code.zip --user-story "As a user..."
  
  # JSON output
  python hybrid_main.py code.zip --format json --output report.json

Environment Variables:
  OPENAI_API_KEY      - OpenAI API key
  ANTHROPIC_API_KEY   - Anthropic API key
  
For more info on model selection:
  See MODEL_RECOMMENDATIONS.md
        """,
    )

    parser.add_argument("input", help="Path to ZIP file or project directory")

    parser.add_argument("--user-story", help="User story for context", default=None)

    parser.add_argument(
        "--output", "-o", help="Output file path (default: stdout)", default=None
    )

    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)",
    )

    parser.add_argument(
        "--static-only", action="store_true", help="Disable LLM analysis (static only)"
    )

    parser.add_argument(
        "--llm-provider",
        choices=["openai", "anthropic", "auto"],
        default="auto",
        help="LLM provider (default: auto)",
    )

    parser.add_argument(
        "--show-llm-info",
        action="store_true",
        default=True,
        help="Show LLM analysis details in output",
    )

    args = parser.parse_args()

    # Start logging session
    session_id = logger.start_session()

    # Validate input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input not found: {args.input}", file=sys.stderr)
        logger.log_error(
            "main", f"Input not found: {args.input}", FileNotFoundError(args.input)
        )
        logger.end_session(success=False)
        sys.exit(1)

    # Log CLI input
    logger.log_event(
        EventType.CLI_INPUT,
        LogLevel.INFO,
        "main",
        "CLI arguments received",
        {
            "input_path": str(args.input),
            "is_zip": input_path.suffix == ".zip",
            "user_story": args.user_story,
            "output_path": args.output,
            "format": args.format,
            "workers": args.workers,
            "static_only": args.static_only,
            "llm_provider": args.llm_provider,
            "show_llm_info": args.show_llm_info,
        },
    )

    # Check LLM setup
    llm_available = check_llm_setup()

    # Log environment setup
    logger.log_event(
        EventType.ENVIRONMENT_SETUP,
        LogLevel.INFO,
        "main",
        "Environment setup complete",
        {
            "llm_available": llm_available,
            "openai_key_present": bool(os.getenv("OPENAI_API_KEY")),
            "anthropic_key_present": bool(os.getenv("ANTHROPIC_API_KEY")),
            "mode": (
                "static_only" if args.static_only or not llm_available else "hybrid"
            ),
            "selected_provider": args.llm_provider,
        },
    )

    if args.static_only:
        print("Running in STATIC-ONLY mode (LLM disabled)")
    elif not llm_available:
        print("Running in STATIC-ONLY mode (no API keys configured)")
    else:
        print("Running in HYBRID mode (Static + LLM)")

    # Handle ZIP file
    zip_handler = None
    project_path = str(input_path)

    if input_path.suffix == ".zip":
        print(f"Extracting ZIP file: {args.input}")
        zip_handler = ZipHandler()
        try:
            project_path = zip_handler.extract(str(input_path))
            print(f"Extracted to: {project_path}")
        except Exception as e:
            print(f"Error extracting ZIP: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        # Run validation
        print("\nStarting validation...")
        print("-" * 80)

        coordinator = CoordinatorAgent(max_workers=args.workers)
        report = coordinator.validate(project_path, args.user_story)

        # Format output
        if args.format == "json":
            output = json.dumps(report.to_dict(), indent=2)
        else:
            output = format_report_as_text(report, args.show_llm_info)

        # Write output
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"\nReport written to: {args.output}")
        else:
            print("\n" + output)

        # Log report generation
        logger.log_event(
            EventType.REPORT_GENERATION,
            LogLevel.INFO,
            "main",
            "Report generated successfully",
            {
                "format": args.format,
                "output_path": args.output,
                "verdict": report.verdict.value,
                "global_score": report.global_score,
                "blocking_critiques_count": len(report.blocking_critiques),
                "recommendations_count": len(report.recommendations),
            },
        )

        # End logging session successfully
        logger.end_session(success=True)

        # Print log file location
        print(f"\n{'='*80}")
        print(f"📋 Detailed logs saved to: {logger.get_log_file_path()}")
        print(f"{'='*80}")

        # Exit with appropriate code
        if report.verdict.value == "BLOCK":
            sys.exit(2)
        elif report.verdict.value == "FIX":
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        # Log error
        logger.log_error("main", f"Validation failed: {str(e)}", e)
        logger.end_session(success=False)

        print(f"\n{'='*80}")
        print(f"📋 Error logs saved to: {logger.get_log_file_path()}")
        print(f"{'='*80}")

        raise

    finally:
        # Cleanup
        if zip_handler:
            zip_handler.cleanup()


if __name__ == "__main__":
    main()
