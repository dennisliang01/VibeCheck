"""Data models for the code validation system."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class Verdict(Enum):
    """Final verdict options."""

    SHIP = "SHIP"
    FIX = "FIX"
    BLOCK = "BLOCK"


class Severity(Enum):
    """Severity levels for recommendations."""

    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class AgentType(Enum):
    """Types of specialized agents."""

    FUNCTIONAL = "functional"
    LOGIC = "logic"
    ARCHITECTURE = "architecture"
    TECHNICAL_DEBT = "technical_debt"
    PERFORMANCE = "performance"
    SECURITY = "security"
    OBSERVABILITY = "observability"
    RESILIENCE = "resilience"
    SEMANTICS = "semantics"
    DEPLOYMENT = "deployment"


@dataclass
class CodeFragment:
    """Represents a logical unit of code."""

    file_path: str
    content: str
    fragment_type: str  # 'function', 'class', 'module', 'test', etc.
    start_line: int
    end_line: int
    language: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result from a single agent analysis."""

    agent_type: AgentType
    score: int  # 0-100
    gaps: List[Dict[str, Any]]
    findings: List[Dict[str, Any]]
    examples: List[Dict[str, Any]]
    raw_analysis: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Recommendation:
    """A prioritized recommendation."""

    severity: Severity
    category: str
    description: str
    fix_suggested: str
    file: Optional[str] = None
    line: Optional[int] = None
    code_snippet: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete validation report."""

    verdict: Verdict
    global_score: int
    detailed_scores: Dict[str, int]
    blocking_critiques: List[str]
    recommendations: List[Recommendation]
    executive_summary: str
    agent_results: Dict[str, AgentResult] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary format."""
        return {
            "verdict": self.verdict.value,
            "score_global": self.global_score,
            "scores_detailles": self.detailed_scores,
            "critiques_bloquantes": self.blocking_critiques,
            "recommandations_prioritaires": [
                {
                    "severite": r.severity.value,
                    "categorie": r.category,
                    "description": r.description,
                    "fix_suggere": r.fix_suggested,
                    "fichier": r.file,
                    "ligne": r.line,
                }
                for r in self.recommendations
            ],
            "resume_executif": self.executive_summary,
            "metadata": self.metadata,
        }


@dataclass
class ValidationContext:
    """Context for validation."""

    language: str
    framework: Optional[str]
    user_story: Optional[str]
    entry_points: List[str]
    dependencies: List[str]
    test_files: List[str]
    config_files: List[str]
