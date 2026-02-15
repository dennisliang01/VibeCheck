"""Base agent class for all specialized agents."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from core.models import CodeFragment, AgentResult, AgentType, ValidationContext


class BaseAgent(ABC):
    """Base class for all validation agents."""

    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.findings: List[Dict[str, Any]] = []
        self.gaps: List[Dict[str, Any]] = []
        self.examples: List[Dict[str, Any]] = []

    @abstractmethod
    def analyze(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Analyze code fragments and return results."""
        pass

    def add_finding(
        self,
        description: str,
        severity: str,
        file: Optional[str] = None,
        line: Optional[int] = None,
        suggestion: Optional[str] = None,
    ):
        """Add a finding."""
        self.findings.append(
            {
                "description": description,
                "severity": severity,
                "file": file,
                "line": line,
                "suggestion": suggestion,
            }
        )

    def add_gap(self, description: str, impact: str, fix_example: Optional[str] = None):
        """Add a gap."""
        self.gaps.append(
            {"description": description, "impact": impact, "fix_example": fix_example}
        )

    def add_example(self, title: str, code: str, explanation: str):
        """Add an example."""
        self.examples.append({"title": title, "code": code, "explanation": explanation})

    def calculate_score(
        self, max_score: int = 100, deductions: Dict[str, int] = None
    ) -> int:
        """Calculate score based on findings."""
        if deductions is None:
            deductions = {"critical": 30, "high": 15, "medium": 8, "low": 3}

        score = max_score
        for finding in self.findings:
            severity = finding.get("severity", "low")
            score -= deductions.get(severity, 0)

        for gap in self.gaps:
            impact = gap.get("impact", "low")
            score -= deductions.get(impact, 0)

        return max(0, score)

    def reset(self):
        """Reset agent state."""
        self.findings = []
        self.gaps = []
        self.examples = []
