"""Documentation Agent: detects missing or inadequate documentation."""

from __future__ import annotations

from codeval.agents.base import BaseAgent
from codeval.llm import complete
from codeval.schemas import (
    AgentReport,
    CodebaseFingerprint,
    FileSnippet,
    HeuristicHit,
)

DOCUMENTATION_SYSTEM = """You are a documentation quality expert. Analyze the codebase for:
- Public functions/classes missing docstrings or JSDoc comments
- README file missing or incomplete (no install, usage, or contributing sections)
- API endpoints without documentation or inline descriptions
- Misleading or stale comments that contradict the code
- Missing type hints (Python) or type annotations (TypeScript/JavaScript)
- Complex algorithms without explanatory comments
- Missing changelog or version documentation for libraries
- Configuration files without comments explaining options
- Missing inline examples for complex utility functions

Severity guidelines:
- critical: no README at all for a published package, API without any docs
- high: public API functions without docstrings, misleading comments
- medium: missing type hints on public interfaces, incomplete README sections
- low: minor missing comments, internal functions without docstrings

Return JSON only. Verify each finding's evidence.file and evidence.lines exist in the provided snippets.
Ensure recommendations are feasible. Use this exact schema:
{
  "agent": "documentation",
  "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
  "findings": [
    {
      "id": "unique-id",
      "severity": "critical|high|medium|low",
      "confidence": 0.0-1.0,
      "title": "short title",
      "evidence": {"file": "path", "lines": [start, end] or [line], "snippet": "..."},
      "impact": "description of documentation gap impact",
      "recommendation": "what to document",
      "patch_hint": "optional docstring template",
      "test_hint": "optional",
      "source": "documentation"
    }
  ],
  "questions": []
}"""


class DocumentationAgent(BaseAgent):
    """Reviews documentation: docstrings, README, type hints, comments."""

    name = "documentation"

    async def run(
        self,
        fingerprint: CodebaseFingerprint,
        files: list[FileSnippet],
        heuristics: list[HeuristicHit],
        llm_enabled: bool,
    ) -> AgentReport:
        heuristic_findings = self._heuristics_to_findings(heuristics, "documentation")

        if not llm_enabled:
            return self._merge_reports(heuristic_findings, None, llm_ok=True)

        context = _build_context(fingerprint, files)
        user_prompt = f"""Codebase fingerprint:
{context['fingerprint']}

File snippets ({len(files)} files):
{context['snippets']}

Analyze for documentation gaps and quality issues. Return JSON with findings.
Self-check: confirm each finding's evidence.file and evidence.lines are present in the snippets above."""

        llm_report = await complete(DOCUMENTATION_SYSTEM, user_prompt, AgentReport)
        return self._merge_reports(heuristic_findings, llm_report, llm_ok=bool(llm_report))


def _build_context(
    fingerprint: CodebaseFingerprint,
    files: list[FileSnippet],
) -> dict[str, str]:
    fp_str = (
        f"languages={fingerprint.languages}, frameworks={fingerprint.frameworks}, "
        f"has_tests={fingerprint.has_tests}, entrypoints={fingerprint.entrypoints}, "
        f"dependency_files={fingerprint.dependency_files}"
    )
    snippets_str = "\n\n".join(
        f"--- {f.path} (lines {f.line_start}-{f.line_end or '?'}) ---\n{f.content}"
        for f in files[:20]
    )
    return {"fingerprint": fp_str, "snippets": snippets_str}
