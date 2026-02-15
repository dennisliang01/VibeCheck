"""Orchestrator: 4-stage pipeline for multi-agent validation."""

from __future__ import annotations

import asyncio
import logging
import math
import time
from pathlib import Path

from codeval.agents import (
    ApiContractAgent,
    ArchitectureAgent,
    ConcurrencyAgent,
    DependencyAgent,
    DocumentationAgent,
    FunctionalAgent,
    PerformanceAgent,
    QualityAgent,
    ResilienceAgent,
    SecurityAgent,
)
from codeval.agents.consolidation import consolidate_findings
from codeval.fingerprint import fingerprint_repo
from codeval.heuristics import run_heuristics
from codeval.schemas import (
    ALL_CATEGORIES,
    AgentFinding,
    AgentReport,
    CodebaseFingerprint,
    FindingCluster,
    FinalReport,
    HeuristicHit,
    ReportScores,
)
from codeval.slicer import slice_repo

logger = logging.getLogger(__name__)

# ── Agent name → category mapping ────────────────────────────────────
AGENT_CATEGORY_MAP: dict[str, str] = {
    "functional": "functional",
    "security": "security",
    "resilience": "resilience",
    "performance": "performance",
    "quality": "quality",
    "dependency": "dependency",
    "documentation": "documentation",
    "architecture": "architecture",
    "concurrency": "concurrency",
    "api_contract": "api_contract",
}

# ── Scoring constants ────────────────────────────────────────────────
# Per-cluster penalty by consolidated severity (diminishing returns applied later)
SEVERITY_WEIGHTS = {"critical": 25, "high": 15, "medium": 8, "low": 3}

# Category weights for overall score (sum = 1.0)
CATEGORY_WEIGHTS: dict[str, float] = {
    "functional": 0.15,
    "security": 0.15,
    "resilience": 0.10,
    "performance": 0.10,
    "quality": 0.10,
    "dependency": 0.10,
    "documentation": 0.08,
    "architecture": 0.10,
    "concurrency": 0.07,
    "api_contract": 0.05,
}

# Minimum possible category score (floor) so scores never hit 0
CATEGORY_FLOOR = 10.0


# ── Progress callback type ────────────────────────────────────────────
# Callable[[agent_name: str, status: str, detail: str], None]
ProgressCallback = object  # typed loosely to avoid import issues


async def run_validation(
    path: str | Path,
    *,
    max_files: int = 50,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    llm_enabled: bool = True,
    on_progress: object | None = None,
) -> FinalReport:
    """
    Run full validation pipeline:
        A) Fingerprint + heuristics
        B) 10 specialist agents (all run in parallel)
        C) Consolidation agent (LLM clustering or proximity fallback)
        D) Score on clusters, build final report

    Args:
        on_progress: Optional callback(agent_name, status, detail) for live progress.
    """
    root = Path(path).resolve()
    if not root.is_dir():
        return FinalReport(summary="Path is not a directory")

    _notify = on_progress if callable(on_progress) else lambda *a: None

    # ── Stage A: Fingerprint ──────────────────────────────────────
    _notify("pipeline", "stage", "Fingerprinting codebase...")
    fingerprint = fingerprint_repo(root, include_patterns, exclude_patterns)
    heuristics = run_heuristics(root, include_patterns, exclude_patterns)

    # ── Stage B: Route and run all 10 specialist agents ───────────
    agents = [
        FunctionalAgent(),
        SecurityAgent(),
        ResilienceAgent(),
        PerformanceAgent(),
        QualityAgent(),
        DependencyAgent(),
        DocumentationAgent(),
        ArchitectureAgent(),
        ConcurrencyAgent(),
        ApiContractAgent(),
    ]

    async def _run_agent(agent):
        agent.root_path = root
        files = slice_repo(
            root,
            fingerprint,
            agent.name,
            heuristics,
            max_files=max_files,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        )
        _notify(agent.name, "running", "")
        try:
            report = await agent.run(fingerprint, files, heuristics, llm_enabled)
            n = len(report.findings)
            status = "done" if report.analyzed else "failed"
            _notify(agent.name, status, f"{n} findings")
            return report
        except Exception as exc:
            logger.warning("Agent %s crashed: %s", agent.name, exc)
            _notify(agent.name, "failed", str(exc))
            return AgentReport(agent=agent.name, analyzed=False)

    _t0 = time.perf_counter()
    tasks = [asyncio.create_task(_run_agent(a)) for a in agents]
    reports: list[AgentReport] = list(await asyncio.gather(*tasks))
    elapsed = time.perf_counter() - _t0
    logger.info("Stage B (all agents): %.2fs", elapsed)

    # ── Identify failed categories ────────────────────────────────
    failed_categories: list[str] = []
    for r in reports:
        if not r.analyzed:
            cat = AGENT_CATEGORY_MAP.get(r.agent, r.agent)
            if cat not in failed_categories:
                failed_categories.append(cat)
            logger.warning("Agent '%s' analysis incomplete (LLM failed); category '%s' marked N/A", r.agent, cat)

    # Collect all raw findings
    all_findings: list[AgentFinding] = []
    for r in reports:
        all_findings.extend(r.findings)

    # ── Stage C: Consolidation (LLM clustering) ──────────────────
    _notify("consolidation", "running", "Clustering findings...")
    consolidation = await consolidate_findings(all_findings, fingerprint, llm_enabled)
    clusters = consolidation.clusters
    _notify("consolidation", "done", f"{len(clusters)} clusters")

    # Build the deduplicated "primary" findings list from clusters
    finding_map = {f.id: f for f in all_findings}
    deduped: list[AgentFinding] = []
    for c in clusters:
        primary = finding_map.get(c.primary_finding_id)
        if primary:
            deduped.append(primary)

    # ── Stage D: Score on clusters, build final report ────────────
    scores = _compute_scores_from_clusters(clusters, failed_categories)
    next_steps = _recommended_next_steps(clusters, fingerprint, failed_categories)

    n_raw = len(all_findings)
    n_clusters = len(clusters)
    n_merged = n_raw - n_clusters
    fail_note = ""
    if failed_categories:
        fail_note = f" ({len(failed_categories)} agent(s) failed: {', '.join(failed_categories)})"
    summary = (
        f"Validated {root.name}: {n_clusters} unique issues "
        f"(from {n_raw} raw findings, {n_merged} merged), "
        f"overall score {scores.overall:.2f}/100{fail_note}"
    )

    return FinalReport(
        summary=summary,
        scores=scores,
        findings=deduped,
        clusters=clusters,
        all_findings=all_findings,
        recommended_next_steps=next_steps,
        fingerprint=fingerprint,
        failed_categories=failed_categories,
    )


# ── Scoring (cluster-based with diminishing returns) ─────────────────


def _compute_scores_from_clusters(
    clusters: list[FindingCluster],
    failed_categories: list[str] | None = None,
) -> ReportScores:
    """
    Compute category and overall scores based on clusters.

    Uses diminishing-returns penalty so many findings don't bottom-out at 0.
    Formula per category:
        penalty = sum of severity weights for each cluster in category
        effective_penalty = 100 * (1 - e^(-penalty / 80))
        score = max(FLOOR, 100 - effective_penalty)

    Failed categories get a score of -1 (sentinel) and are excluded from
    the overall weighted average.
    """
    failed = set(failed_categories or [])
    cat_raw_penalty: dict[str, float] = {cat: 0.0 for cat in ALL_CATEGORIES}

    for c in clusters:
        cat = c.category if c.category in cat_raw_penalty else "functional"
        cat_raw_penalty[cat] += SEVERITY_WEIGHTS.get(c.consolidated_severity, 0)

    cat_scores: dict[str, float] = {}
    for cat in ALL_CATEGORIES:
        if cat in failed:
            cat_scores[cat] = -1.0  # Sentinel: N/A
            continue
        raw_penalty = cat_raw_penalty[cat]
        effective_penalty = 100.0 * (1.0 - math.exp(-raw_penalty / 80.0))
        cat_scores[cat] = round(max(CATEGORY_FLOOR, 100.0 - effective_penalty), 2)

    # Weighted overall – renormalize excluding failed categories
    active_weight_sum = sum(
        CATEGORY_WEIGHTS.get(cat, 0.0)
        for cat in ALL_CATEGORIES
        if cat not in failed
    )
    if active_weight_sum > 0:
        overall = sum(
            cat_scores[cat] * (CATEGORY_WEIGHTS.get(cat, 0.0) / active_weight_sum)
            for cat in ALL_CATEGORIES
            if cat not in failed
        )
    else:
        overall = 0.0

    overall = round(max(CATEGORY_FLOOR, min(100.0, overall)), 2)

    return ReportScores(categories=cat_scores, overall=overall)


# ── Next steps (cluster-based) ───────────────────────────────────────


def _recommended_next_steps(
    clusters: list[FindingCluster],
    fingerprint: CodebaseFingerprint,
    failed_categories: list[str] | None = None,
) -> list[str]:
    """Generate recommended next steps from clusters."""
    steps: list[str] = []

    # Warn about failed agents first
    if failed_categories:
        steps.append(
            f"Re-run validation for {len(failed_categories)} failed agent(s) "
            f"({', '.join(failed_categories)}) -- their scores show N/A"
        )

    critical = [c for c in clusters if c.consolidated_severity == "critical"]
    high = [c for c in clusters if c.consolidated_severity == "high"]

    if critical:
        steps.append(
            f"Address {len(critical)} critical issue(s) first: "
            + ", ".join(c.consolidated_title[:60] for c in critical[:3])
        )
    if high:
        steps.append(f"Review {len(high)} high-severity issue(s)")
    if not fingerprint.has_tests:
        steps.append("Add tests (no test patterns detected)")

    # Category-specific recommendations
    dep_clusters = [c for c in clusters if c.category == "dependency" and c.consolidated_severity in ("critical", "high")]
    if dep_clusters:
        steps.append(f"Upgrade {len(dep_clusters)} vulnerable dependency(ies)")
    doc_clusters = [c for c in clusters if c.category == "documentation" and c.consolidated_severity in ("critical", "high")]
    if doc_clusters:
        steps.append("Improve documentation coverage")

    if fingerprint.entrypoints and not steps:
        steps.append("Review entrypoints for correctness")
    if not steps:
        steps.append("No urgent issues; consider periodic re-validation")

    return steps[:7]
