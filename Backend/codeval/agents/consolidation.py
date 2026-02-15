"""Consolidation Agent: clusters related findings using LLM."""

from __future__ import annotations

import logging
from collections import defaultdict

from codeval.llm import complete
from codeval.schemas import (
    ALL_CATEGORIES,
    AgentFinding,
    CodebaseFingerprint,
    ConsolidationReport,
    FindingCluster,
)

logger = logging.getLogger(__name__)

CONSOLIDATION_SYSTEM = """You are a Consolidation Agent for a multi-agent code validator. You receive
a draft report containing findings from TEN specialist agents that analyzed
the same codebase independently:
  functional, security, resilience, performance, quality, dependency,
  documentation, architecture, concurrency, api_contract

Your job:
1. Identify findings that describe the SAME root cause, even if they use
   different titles, come from different agents, or reference slightly
   different line numbers in the same code region.

2. Group related findings into clusters. A cluster = one real issue that
   was flagged multiple times.

3. For each cluster, select the PRIMARY finding (the one with the richest
   detail and most actionable recommendation) and list the others as
   RELATED. Prefer LLM-generated findings over heuristic findings as primary.

4. Assign a consolidated severity to each cluster. Use the highest severity
   from any finding in the cluster.

5. Write a consolidated title and impact that captures ALL perspectives
   (e.g. if functional says "bug" and security says "vulnerability",
   the consolidated version should mention both).

6. Assign a match_confidence (0.0-1.0) to each cluster indicating how
   certain you are that all grouped findings are truly the same issue.

7. Assign a category to each cluster. Choose the MOST relevant domain:
   "functional", "security", "resilience", "performance", "quality",
   "dependency", "documentation", "architecture", "concurrency", or "api_contract"

Matching heuristics to consider:
- Same file + within 10 lines = very likely same issue
- Same file + similar code pattern = likely same issue
- Different files but identical pattern (e.g. bare except in two places)
  = DIFFERENT issues, do NOT merge
- A heuristic hit (id contains "heur") and an LLM finding covering the
  same file+region = same issue, prefer the LLM finding as primary
- "No test coverage" from functional and "untested code" from resilience
  about the same codebase = same root issue
- An issue about error handling in a specific function flagged by both
  functional and resilience = same root issue
- A performance issue about N+1 queries and a quality issue about loop
  complexity in the same function = may be related (use performance category)
- A security issue about input validation and an api_contract issue about
  missing request validation on the same endpoint = same root issue
  (use security category)
- An architecture issue about god objects and a quality issue about long
  functions in the same file = may be related (use architecture category)
- A documentation issue about missing docstrings and a quality issue about
  poor naming in the same file = DIFFERENT issues, keep separate
- A dependency CVE and a security finding about the same package = same issue
  (use dependency category)

Return JSON only. Use this exact schema:
{
  "clusters": [
    {
      "cluster_id": "cluster-001",
      "primary_finding_id": "the-best-finding-id",
      "related_finding_ids": ["other-id-1", "other-id-2"],
      "match_confidence": 0.95,
      "consolidated_title": "merged title covering all perspectives",
      "consolidated_severity": "critical|high|medium|low",
      "consolidated_impact": "merged impact statement",
      "consolidated_recommendation": "merged actionable recommendation",
      "category": "functional|security|resilience|performance|quality|dependency|documentation|architecture|concurrency|api_contract"
    }
  ]
}

Rules:
- Every finding MUST appear in exactly one cluster (either as primary or related).
  Do NOT drop any findings.
- Findings that are truly unique should be a cluster of size 1 (primary only,
  empty related_finding_ids).
- Do NOT merge findings from different files unless they are clearly the same
  systemic issue (e.g. "no tests" is codebase-wide).
- Be conservative: when uncertain, keep findings as separate clusters."""


def _build_consolidation_prompt(
    findings: list[AgentFinding],
    fingerprint: CodebaseFingerprint,
) -> str:
    """Build rich context prompt for the Consolidation Agent."""
    # File coverage: which agents flagged each file
    file_agents: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for f in findings:
        file_agents[f.evidence.file][f.source] += 1

    file_coverage_lines = []
    for fpath, agents in sorted(file_agents.items()):
        parts = ", ".join(f"{agent} ({count})" for agent, count in sorted(agents.items()))
        file_coverage_lines.append(f"  {fpath}: flagged by {parts}")
    file_coverage = "\n".join(file_coverage_lines) or "  (none)"

    # Findings list with full detail
    findings_lines = []
    for i, f in enumerate(findings, 1):
        is_heuristic = "heur" in f.id
        origin = "heuristic" if is_heuristic else "LLM"
        findings_lines.append(f"""### Finding {i} of {len(findings)}
- ID: {f.id}
- Source: {f.source} agent ({origin})
- Severity: {f.severity} (confidence: {f.confidence})
- Title: {f.title}
- File: {f.evidence.file}, lines {f.evidence.lines}
- Snippet:
  {f.evidence.snippet[:300]}
- Impact: {f.impact}
- Recommendation: {f.recommendation}""")

    findings_text = "\n\n".join(findings_lines)

    return f"""## Codebase Fingerprint
Languages: {fingerprint.languages}
Frameworks: {fingerprint.frameworks}
Has tests: {fingerprint.has_tests}
Entrypoints: {fingerprint.entrypoints}

## File Coverage
{file_coverage}

## All Draft Findings ({len(findings)} total)

{findings_text}

Cluster these findings by root cause. Return JSON matching the schema."""


async def consolidate_findings(
    findings: list[AgentFinding],
    fingerprint: CodebaseFingerprint,
    llm_enabled: bool,
) -> ConsolidationReport:
    """
    Run the Consolidation Agent to cluster related findings.

    If LLM is disabled, falls back to a simple proximity-based dedup.
    """
    if not findings:
        return ConsolidationReport(clusters=[])

    if llm_enabled:
        user_prompt = _build_consolidation_prompt(findings, fingerprint)
        result = await complete(CONSOLIDATION_SYSTEM, user_prompt, ConsolidationReport)
        if result and result.clusters:
            # Validate: ensure every finding is accounted for
            all_ids = {f.id for f in findings}
            clustered_ids: set[str] = set()
            for c in result.clusters:
                clustered_ids.add(c.primary_finding_id)
                clustered_ids.update(c.related_finding_ids)

            missing = all_ids - clustered_ids
            if missing:
                # Add missing findings as single-item clusters
                for fid in missing:
                    f = next((x for x in findings if x.id == fid), None)
                    if f:
                        result.clusters.append(
                            FindingCluster(
                                cluster_id=f"cluster-orphan-{fid}",
                                primary_finding_id=fid,
                                related_finding_ids=[],
                                match_confidence=1.0,
                                consolidated_title=f.title,
                                consolidated_severity=f.severity,
                                consolidated_impact=f.impact,
                                consolidated_recommendation=f.recommendation,
                                category=f.source if f.source in ALL_CATEGORIES else "functional",
                            )
                        )
            return result

    # Fallback: proximity-based clustering (no LLM)
    return _fallback_cluster(findings)


def _fallback_cluster(findings: list[AgentFinding]) -> ConsolidationReport:
    """Simple proximity-based clustering when LLM is unavailable."""
    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}

    # Group by (file, line_bucket) where bucket = line // 10
    buckets: dict[tuple[str, int], list[AgentFinding]] = defaultdict(list)
    for f in findings:
        line = f.evidence.lines[0] if f.evidence.lines else 0
        bucket_key = (f.evidence.file, line // 10)
        buckets[bucket_key].append(f)

    clusters: list[FindingCluster] = []
    cluster_idx = 0
    for (file, bucket), group in buckets.items():
        cluster_idx += 1
        # Sort: prefer LLM over heuristic, then highest severity
        group.sort(
            key=lambda x: (0 if "heur" in x.id else 1, severity_order.get(x.severity, 0)),
            reverse=True,
        )
        primary = group[0]
        related = [f.id for f in group[1:]]
        best_severity = max(group, key=lambda x: severity_order.get(x.severity, 0)).severity
        cat = primary.source if primary.source in ALL_CATEGORIES else "functional"

        clusters.append(
            FindingCluster(
                cluster_id=f"cluster-{cluster_idx:03d}",
                primary_finding_id=primary.id,
                related_finding_ids=related,
                match_confidence=0.8 if len(group) > 1 else 1.0,
                consolidated_title=primary.title,
                consolidated_severity=best_severity,
                consolidated_impact=primary.impact,
                consolidated_recommendation=primary.recommendation,
                category=cat,
            )
        )

    return ConsolidationReport(clusters=clusters)
