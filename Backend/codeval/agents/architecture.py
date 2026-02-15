"""Architecture Agent: detects structural and design issues."""

from __future__ import annotations

from codeval.agents.base import BaseAgent
from codeval.llm import complete
from codeval.schemas import (
    AgentReport,
    CodebaseFingerprint,
    FileSnippet,
    HeuristicHit,
)

ARCHITECTURE_SYSTEM = """You are a software architecture and design expert. Analyze the codebase for:
- Circular imports / circular dependencies between modules
- SOLID principle violations:
  - Single Responsibility: classes/modules with mixed unrelated concerns
  - Open/Closed: code that requires modification instead of extension
  - Liskov Substitution: subclasses that break parent contracts
  - Interface Segregation: fat interfaces forcing unused implementations
  - Dependency Inversion: high-level modules depending on low-level details
- High coupling: files importing 10+ other project modules
- Low cohesion: modules containing unrelated functionality
- Layer violations (e.g., UI/view code directly calling database queries,
  controllers containing business logic)
- Missing separation of concerns (mixing I/O, logic, and presentation)
- God objects / god modules (single file doing everything)
- Missing dependency injection (hardcoded dependencies)
- Improper use of global state

Severity guidelines:
- critical: circular dependencies causing import errors, severe layer violations
- high: god objects, SOLID violations in core modules, high coupling (10+ imports)
- medium: missing dependency injection, minor layer violations
- low: minor cohesion issues, style-level architecture concerns

Return JSON only. Verify each finding's evidence.file and evidence.lines exist in the provided snippets.
Ensure recommendations are feasible. Use this exact schema:
{
  "agent": "architecture",
  "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
  "findings": [
    {
      "id": "unique-id",
      "severity": "critical|high|medium|low",
      "confidence": 0.0-1.0,
      "title": "short title",
      "evidence": {"file": "path", "lines": [start, end] or [line], "snippet": "..."},
      "impact": "description of architectural impact",
      "recommendation": "refactoring suggestion",
      "patch_hint": "optional restructuring approach",
      "test_hint": "optional",
      "source": "architecture"
    }
  ],
  "questions": []
}"""


class ArchitectureAgent(BaseAgent):
    """Reviews architecture: SOLID, coupling, cohesion, circular deps, layers."""

    name = "architecture"

    async def run(
        self,
        fingerprint: CodebaseFingerprint,
        files: list[FileSnippet],
        heuristics: list[HeuristicHit],
        llm_enabled: bool,
    ) -> AgentReport:
        heuristic_findings = self._heuristics_to_findings(heuristics, "architecture")

        if not llm_enabled:
            return self._merge_reports(heuristic_findings, None, llm_ok=True)

        context = _build_context(fingerprint, files)
        user_prompt = f"""Codebase fingerprint:
{context['fingerprint']}

File snippets ({len(files)} files, showing import sections and structure):
{context['snippets']}

Analyze for architecture and design issues. Pay special attention to import patterns,
module responsibilities, and layer boundaries. Return JSON with findings.
Self-check: confirm each finding's evidence.file and evidence.lines are present in the snippets above."""

        llm_report = await complete(ARCHITECTURE_SYSTEM, user_prompt, AgentReport)
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
