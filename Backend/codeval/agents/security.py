"""Security Reviewer agent."""

from __future__ import annotations

from codeval.agents.base import BaseAgent
from codeval.llm import complete
from codeval.schemas import (
    AgentReport,
    CodebaseFingerprint,
    FileSnippet,
    HeuristicHit,
)

SECURITY_SYSTEM = """You are a security code reviewer expert. Analyze the codebase for:
- eval/exec usage (code injection)
- SQL injection (string concatenation in queries)
- subprocess with shell=True
- Unsafe deserialization (pickle, yaml.unsafe_load)
- Missing input validation
- Authentication/authorization issues

Return JSON only. Verify each finding's evidence.file and evidence.lines exist in the provided snippets.
Ensure recommendations are feasible. Use this exact schema:
{
  "agent": "security",
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
      "source": "security"
    }
  ],
  "questions": []
}"""


class SecurityAgent(BaseAgent):
    """Reviews security: eval/exec, SQL injection, subprocess, deserialization, auth."""

    name = "security"

    async def run(
        self,
        fingerprint: CodebaseFingerprint,
        files: list[FileSnippet],
        heuristics: list[HeuristicHit],
        llm_enabled: bool,
    ) -> AgentReport:
        heuristic_findings = self._heuristics_to_findings(heuristics, "security")

        if not llm_enabled:
            return self._merge_reports(heuristic_findings, None, llm_ok=True)

        context = _build_context(fingerprint, files, heuristics, "security")
        user_prompt = f"""Codebase fingerprint:
{context['fingerprint']}

File snippets:
{context['snippets']}

Static heuristic hits (security):
{context['heuristics']}

Analyze and return JSON with findings. Verify evidence lines exist in snippets. Self-check: confirm each finding's evidence.file and evidence.lines are present."""

        llm_report = await complete(SECURITY_SYSTEM, user_prompt, AgentReport)
        return self._merge_reports(heuristic_findings, llm_report, llm_ok=bool(llm_report))


def _build_context(
    fingerprint: CodebaseFingerprint,
    files: list[FileSnippet],
    heuristics: list[HeuristicHit],
    category: str,
) -> dict[str, str]:
    fp_str = f"languages={fingerprint.languages}, frameworks={fingerprint.frameworks}"
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
