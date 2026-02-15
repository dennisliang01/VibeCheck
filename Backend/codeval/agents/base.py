"""Base agent ABC for specialist agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from codeval.schemas import (
    AgentFinding,
    AgentReport,
    CodebaseFingerprint,
    Evidence,
    FileSnippet,
    HeuristicHit,
    SeveritySummary,
)


class BaseAgent(ABC):
    """Abstract base for specialist agents."""

    name: str = ""
    root_path: Path | None = None  # Set by orchestrator before run()

    @abstractmethod
    async def run(
        self,
        fingerprint: CodebaseFingerprint,
        files: list[FileSnippet],
        heuristics: list[HeuristicHit],
        llm_enabled: bool,
    ) -> AgentReport:
        """Run agent analysis. Merge heuristics with optional LLM findings."""
        ...

    def _heuristics_to_findings(
        self,
        heuristics: list[HeuristicHit],
        category_filter: str | None = None,
    ) -> list[AgentFinding]:
        """Convert heuristic hits to AgentFinding for this agent's category."""
        findings: list[AgentFinding] = []
        severity_map = {
            "TODO_FIXME": "low",
            "BARE_EXCEPT": "medium",
            "BROAD_EXCEPT": "low",
            "EVAL_EXEC": "critical",
            "SHELL_TRUE": "high",
            "SQL_CONCAT": "critical",
            "UNSAFE_DESERIALIZE": "high",
            "MISSING_TIMEOUT": "medium",
        }
        for i, h in enumerate(heuristics):
            if category_filter and h.category != category_filter:
                continue
            severity = severity_map.get(h.pattern_id, "medium")
            findings.append(
                AgentFinding(
                    id=f"{self.name}-heur-{i}",
                    severity=severity,
                    confidence=0.9,
                    title=f"Static heuristic: {h.pattern_id}",
                    evidence=Evidence(
                        file=h.file,
                        lines=(h.line,),
                        snippet=h.snippet,
                    ),
                    impact=f"Pattern {h.pattern_id} detected at {h.file}:{h.line}",
                    recommendation=f"Review and address {h.pattern_id} pattern",
                    patch_hint="",
                    test_hint="",
                    source=self.name,
                )
            )
        return findings

    def _merge_reports(
        self,
        heuristic_findings: list[AgentFinding],
        llm_report: AgentReport | None,
        *,
        llm_ok: bool = True,
    ) -> AgentReport:
        """Merge heuristic findings with LLM report.

        Args:
            heuristic_findings: Findings from static heuristics.
            llm_report: Parsed LLM report (None if LLM was disabled or failed).
            llm_ok: Whether the LLM call succeeded. When False, the report is
                     marked ``analyzed=False`` to signal downstream scoring should
                     treat this category as incomplete.
        """
        all_findings = list(heuristic_findings)
        if llm_report and llm_report.findings:
            for f in llm_report.findings:
                f.source = self.name
                all_findings.append(f)

        summary = SeveritySummary()
        for f in all_findings:
            setattr(summary, f.severity, getattr(summary, f.severity) + 1)

        return AgentReport(
            agent=self.name,
            summary=summary,
            findings=all_findings,
            questions=llm_report.questions if llm_report else [],
            analyzed=llm_ok,
        )
