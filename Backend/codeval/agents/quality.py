"""Code Quality Agent: detects code smells, complexity, and maintainability issues."""

from __future__ import annotations

from codeval.agents.base import BaseAgent
from codeval.llm import complete
from codeval.schemas import (
    AgentReport,
    CodebaseFingerprint,
    FileSnippet,
    HeuristicHit,
)

QUALITY_SYSTEM = """You are a code quality and maintainability expert. Analyze the codebase for:
- Functions exceeding ~50 lines (too long, should be split)
- High cyclomatic complexity (deeply nested if/for/while, >3 nesting levels)
- DRY violations (copy-pasted code blocks across files or within a file)
- Magic numbers and magic strings (unexplained literal values)
- Poor naming conventions (single-character variables outside loops, misleading names,
  inconsistent casing)
- Unused imports or dead variables
- God classes or god modules (>500 lines with mixed responsibilities)
- Inconsistent code style within the same file/project
- Missing type hints (Python) or type annotations (TypeScript)
- Overly complex conditionals that should be refactored

Severity guidelines:
- critical: god classes with 1000+ lines mixing unrelated concerns
- high: DRY violations (same block copy-pasted 3+ times), functions >100 lines
- medium: magic numbers in logic, functions 50-100 lines, missing type hints
- low: minor naming issues, unused imports, style inconsistencies

Return JSON only. Verify each finding's evidence.file and evidence.lines exist in the provided snippets.
Ensure recommendations are feasible. Use this exact schema:
{
  "agent": "quality",
  "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
  "findings": [
    {
      "id": "unique-id",
      "severity": "critical|high|medium|low",
      "confidence": 0.0-1.0,
      "title": "short title",
      "evidence": {"file": "path", "lines": [start, end] or [line], "snippet": "..."},
      "impact": "description of maintainability impact",
      "recommendation": "what to do",
      "patch_hint": "optional refactoring suggestion",
      "test_hint": "optional",
      "source": "quality"
    }
  ],
  "questions": []
}"""


class QualityAgent(BaseAgent):
    """Reviews code quality: complexity, DRY, naming, god classes."""

    name = "quality"

    async def run(
        self,
        fingerprint: CodebaseFingerprint,
        files: list[FileSnippet],
        heuristics: list[HeuristicHit],
        llm_enabled: bool,
    ) -> AgentReport:
        heuristic_findings = self._heuristics_to_findings(heuristics, "quality")

        if not llm_enabled:
            return self._merge_reports(heuristic_findings, None, llm_ok=True)

        context = _build_context(fingerprint, files)
        user_prompt = f"""Codebase fingerprint:
{context['fingerprint']}

File snippets ({len(files)} files):
{context['snippets']}

Analyze for code quality and maintainability issues. Return JSON with findings.
Self-check: confirm each finding's evidence.file and evidence.lines are present in the snippets above."""

        llm_report = await complete(QUALITY_SYSTEM, user_prompt, AgentReport)
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
        f"--- {f.path} (lines {f.line_start}-{f.line_end or '?'}, score={f.relevance_score:.1f}) ---\n{f.content}"
        for f in files[:20]
    )
    return {"fingerprint": fp_str, "snippets": snippets_str}
