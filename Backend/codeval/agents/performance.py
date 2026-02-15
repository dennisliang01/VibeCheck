"""Performance Agent: detects performance anti-patterns and bottlenecks."""

from __future__ import annotations

from codeval.agents.base import BaseAgent
from codeval.llm import complete
from codeval.schemas import (
    AgentReport,
    CodebaseFingerprint,
    FileSnippet,
    HeuristicHit,
)

PERFORMANCE_SYSTEM = """You are a performance engineering expert. Analyze the codebase for:
- N+1 query patterns (loop executing one query per item instead of batch)
- O(n^2) or worse nested loops on data collections
- Repeated object allocations in hot paths or loops
- Missing caching / memoization for expensive repeated computations
- Large unnecessary object copies (deep copies, list slicing entire arrays)
- Using list comprehensions where generators would save memory
- Synchronous blocking I/O in async contexts (sync file reads, time.sleep in async)
- Missing database indexes hinted by query patterns
- Unnecessary re-computation (same value calculated multiple times)
- Loading entire datasets into memory when streaming/pagination would suffice

Severity guidelines:
- critical: O(n^2)+ on unbounded input, N+1 queries that scale with user data
- high: blocking I/O in async, missing pagination on large datasets
- medium: unnecessary copies, missing caching, generator vs list
- low: minor allocations, style-level performance hints

Return JSON only. Verify each finding's evidence.file and evidence.lines exist in the provided snippets.
Ensure recommendations are feasible. Use this exact schema:
{
  "agent": "performance",
  "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
  "findings": [
    {
      "id": "unique-id",
      "severity": "critical|high|medium|low",
      "confidence": 0.0-1.0,
      "title": "short title",
      "evidence": {"file": "path", "lines": [start, end] or [line], "snippet": "..."},
      "impact": "description of performance impact with estimated complexity",
      "recommendation": "what to do",
      "patch_hint": "optional code fix",
      "test_hint": "optional benchmark suggestion",
      "source": "performance"
    }
  ],
  "questions": []
}"""


class PerformanceAgent(BaseAgent):
    """Detects performance anti-patterns: N+1, O(n^2), missing caching, blocking I/O."""

    name = "performance"

    async def run(
        self,
        fingerprint: CodebaseFingerprint,
        files: list[FileSnippet],
        heuristics: list[HeuristicHit],
        llm_enabled: bool,
    ) -> AgentReport:
        heuristic_findings = self._heuristics_to_findings(heuristics, "performance")

        if not llm_enabled:
            return self._merge_reports(heuristic_findings, None, llm_ok=True)

        context = _build_context(fingerprint, files)
        user_prompt = f"""Codebase fingerprint:
{context['fingerprint']}

File snippets ({len(files)} files):
{context['snippets']}

Analyze for performance anti-patterns. Return JSON with findings.
Self-check: confirm each finding's evidence.file and evidence.lines are present in the snippets above."""

        llm_report = await complete(PERFORMANCE_SYSTEM, user_prompt, AgentReport)
        return self._merge_reports(heuristic_findings, llm_report, llm_ok=bool(llm_report))


def _build_context(
    fingerprint: CodebaseFingerprint,
    files: list[FileSnippet],
) -> dict[str, str]:
    fp_str = (
        f"languages={fingerprint.languages}, frameworks={fingerprint.frameworks}, "
        f"has_tests={fingerprint.has_tests}, entrypoints={fingerprint.entrypoints}"
    )
    snippets_str = "\n\n".join(
        f"--- {f.path} (lines {f.line_start}-{f.line_end or '?'}) ---\n{f.content}"
        for f in files[:20]
    )
    return {"fingerprint": fp_str, "snippets": snippets_str}
