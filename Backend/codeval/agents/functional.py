"""Functional Validator agent."""

from __future__ import annotations

from codeval.agents.base import BaseAgent
from codeval.llm import complete
from codeval.schemas import (
    AgentReport,
    CodebaseFingerprint,
    FileSnippet,
    HeuristicHit,
)

FUNCTIONAL_SYSTEM = """You are a functional code validator expert. Analyze the codebase for:
- Entrypoint correctness and discoverability
- Test coverage gaps
- TODO/FIXME that indicate incomplete work
- Dead code or unreachable paths

Return JSON only. Verify each finding's evidence.file and evidence.lines exist in the provided snippets.
Ensure recommendations are feasible. Use this exact schema:
{
  "agent": "functional",
  "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
  "findings": [
    {
      "id": "unique-id",
      "severity": "critical|high|medium|low",
      "confidence": 0.0-1.0,
      "title": "short title",
      "evidence": {"file": "path", "lines": [start, end] or [line], "snippet": "..."},
      "impact": "description",
      "recommendation": "what to do",
      "patch_hint": "optional",
      "test_hint": "optional",
      "source": "functional"
    }
  ],
  "questions": []
}"""


class FunctionalAgent(BaseAgent):
    """Validates functional aspects: entrypoints, tests, TODO/FIXME."""

    name = "functional"

    async def run(
        self,
        fingerprint: CodebaseFingerprint,
        files: list[FileSnippet],
        heuristics: list[HeuristicHit],
        llm_enabled: bool,
    ) -> AgentReport:
        heuristic_findings = self._heuristics_to_findings(heuristics, "functional")

        if not llm_enabled:
            return self._merge_reports(heuristic_findings, None, llm_ok=True)

        context = _build_context(fingerprint, files, heuristics, "functional")
        user_prompt = f"""Codebase fingerprint:
{context['fingerprint']}

File snippets:
{context['snippets']}

Static heuristic hits (functional):
{context['heuristics']}

Analyze and return JSON with findings. Verify evidence lines exist in snippets. Self-check: confirm each finding's evidence.file and evidence.lines are present."""

        llm_report = await complete(FUNCTIONAL_SYSTEM, user_prompt, AgentReport)
        return self._merge_reports(heuristic_findings, llm_report, llm_ok=bool(llm_report))


def _build_context(
    fingerprint: CodebaseFingerprint,
    files: list[FileSnippet],
    heuristics: list[HeuristicHit],
    category: str,
) -> dict[str, str]:
    fp_str = f"languages={fingerprint.languages}, frameworks={fingerprint.frameworks}, has_tests={fingerprint.has_tests}, entrypoints={fingerprint.entrypoints}"
    snippets_str = "\n\n".join(
        f"--- {f.path} (lines {f.line_start}-{f.line_end or '?'}) ---\n{f.content}"
        for f in files[:20]
    )
    heur_str = "\n".join(
        f"- {h.file}:{h.line} {h.pattern_id}: {h.snippet[:100]}"
        for h in heuristics
        if h.category == category
    ) or "(none)"
    return {
        "fingerprint": fp_str,
        "snippets": snippets_str,
        "heuristics": heur_str,
    }
