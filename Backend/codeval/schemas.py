"""Pydantic schemas for agent outputs and final report."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# All valid agent / scoring categories
CategoryLiteral = Literal[
    "functional",
    "security",
    "resilience",
    "performance",
    "quality",
    "dependency",
    "documentation",
    "architecture",
    "concurrency",
    "api_contract",
]

ALL_CATEGORIES: list[str] = [
    "functional",
    "security",
    "resilience",
    "performance",
    "quality",
    "dependency",
    "documentation",
    "architecture",
    "concurrency",
    "api_contract",
]


class Evidence(BaseModel):
    """Evidence for a finding: file, lines, and snippet."""

    file: str
    lines: tuple[int, ...] = (0,)  # (line,) or (start, end)
    snippet: str = ""

    @field_validator("lines", mode="before")
    @classmethod
    def lines_to_tuple(cls, v: object) -> tuple[int, ...]:
        if isinstance(v, list):
            return tuple(int(x) for x in v)
        if isinstance(v, tuple):
            return v
        return (int(v),) if v is not None else (0,)


class AgentFinding(BaseModel):
    """A single finding from an agent."""

    id: str
    severity: Literal["critical", "high", "medium", "low"]
    confidence: float = Field(ge=0, le=1)
    title: str
    evidence: Evidence
    impact: str = ""
    recommendation: str = ""
    patch_hint: str = ""
    test_hint: str = ""
    source: str = ""


class SeveritySummary(BaseModel):
    """Counts by severity."""

    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class AgentReport(BaseModel):
    """Report from a single agent."""

    agent: str
    summary: SeveritySummary = Field(default_factory=SeveritySummary)
    findings: list[AgentFinding] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    analyzed: bool = True  # False when LLM call failed (heuristics-only fallback)


class CodebaseFingerprint(BaseModel):
    """Lightweight codebase fingerprint for routing."""

    languages: dict[str, int] = Field(default_factory=dict)
    frameworks: list[str] = Field(default_factory=list)
    has_tests: bool = False
    entrypoints: list[str] = Field(default_factory=list)
    dependency_files: list[str] = Field(default_factory=list)
    test_patterns: list[str] = Field(default_factory=list)


class ReportScores(BaseModel):
    """Dynamic scores for the final report. Keys = category names, plus 'overall'."""

    categories: dict[str, float] = Field(default_factory=lambda: {c: 100.0 for c in ALL_CATEGORIES})
    overall: float = 100.0


class FindingCluster(BaseModel):
    """A cluster of related findings representing one root issue."""

    cluster_id: str
    primary_finding_id: str
    related_finding_ids: list[str] = Field(default_factory=list)
    match_confidence: float = Field(ge=0, le=1, default=1.0)
    consolidated_title: str = ""
    consolidated_severity: Literal["critical", "high", "medium", "low"] = "medium"
    consolidated_impact: str = ""
    consolidated_recommendation: str = ""
    category: CategoryLiteral = "functional"


class ConsolidationReport(BaseModel):
    """Output of the Consolidation Agent: clusters of related findings."""

    clusters: list[FindingCluster] = Field(default_factory=list)


class FinalReport(BaseModel):
    """Consolidated validation report."""

    summary: str = ""
    scores: ReportScores = Field(default_factory=ReportScores)
    findings: list[AgentFinding] = Field(default_factory=list)
    clusters: list[FindingCluster] = Field(default_factory=list)
    all_findings: list[AgentFinding] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    fingerprint: CodebaseFingerprint | None = None
    failed_categories: list[str] = Field(default_factory=list)  # Categories where LLM failed


class HeuristicHit(BaseModel):
    """A hit from static heuristics."""

    file: str
    line: int
    pattern_id: str
    snippet: str = ""
    category: Literal["functional", "security", "resilience"] = "functional"


class FileSnippet(BaseModel):
    """A file with extracted snippets for context."""

    path: str
    content: str
    relevance_score: float = 0.0
    line_start: int = 1
    line_end: int | None = None


def agent_report_json_schema() -> dict:
    """Export JSON schema for AgentReport."""
    return AgentReport.model_json_schema()


def final_report_json_schema() -> dict:
    """Export JSON schema for FinalReport."""
    return FinalReport.model_json_schema()
