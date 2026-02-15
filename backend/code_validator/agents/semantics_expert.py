"""Agent 9: Semantics & Intention - Ensures code is semantically understandable."""

import re
from typing import List, Dict, Any
from agents.base_agent import BaseAgent
from core.models import CodeFragment, AgentResult, AgentType, ValidationContext


class SemanticsExpert(BaseAgent):
    """S'assure que le code est comprehensible semantiquement."""

    def __init__(self):
        super().__init__(AgentType.SEMANTICS)

    def analyze(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Analyze code for semantic clarity."""
        self.reset()

        # Check 1: Variable names reflect their role
        self._check_variable_names(fragments)

        # Check 2: Function names reflect their role
        self._check_function_names(fragments)

        # Check 3: Technically correct but semantically empty names
        self._check_empty_names(fragments)

        # Check 4: Self-documenting code
        self._check_self_documenting(fragments)

        # Check 5: New developer comprehension
        self._check_comprehension(fragments)

        # Check 6: Abstraction level
        self._check_abstraction_level(fragments)

        score = self.calculate_score()

        return AgentResult(
            agent_type=self.agent_type,
            score=score,
            gaps=self.gaps,
            findings=self.findings,
            examples=self.examples,
            raw_analysis={
                "naming_quality": self._assess_naming_quality(fragments),
                "renaming_suggestions": len(
                    [
                        f
                        for f in self.findings
                        if "rename" in f.get("suggestion", "").lower()
                    ]
                ),
                "comprehension_score": score,
            },
        )

    def _check_variable_names(self, fragments: List[CodeFragment]):
        """Check if variable names reflect their role."""
        bad_variable_patterns = [
            (r"\b(data|d)\b", "data", "Use specific name like userData, orderData"),
            (
                r"\b(result|r)\b",
                "result",
                "Use specific name like calculationResult, queryResult",
            ),
            (r"\b(temp|tmp|t)\b", "temp", "Use descriptive name indicating purpose"),
            (r"\b(val|v|value)\b", "value", "Use domain-specific name"),
            (r"\b(obj|o|object)\b", "obj", "Use specific type name"),
            (r"\b(arr|a|array)\b", "arr", "Use plural noun like users, orders"),
            (r"\b(item|i|it)\b", "item", "Use specific name like product, lineItem"),
            (
                r"\b(x|y|z)\b",
                "single letter",
                "Use descriptive name unless in math context",
            ),
        ]

        for fragment in fragments:
            for pattern, bad_name, suggestion in bad_variable_patterns:
                matches = re.findall(pattern, fragment.content)
                if matches:
                    self.add_finding(
                        description=f"Generic variable name '{bad_name}' doesn't reflect role",
                        severity="low",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion=suggestion,
                    )

    def _check_function_names(self, fragments: List[CodeFragment]):
        """Check if function names reflect their role."""
        for fragment in fragments:
            if fragment.fragment_type == "function":
                name = fragment.metadata.get("name", "")

                # Check for generic function names
                generic_names = [
                    "process",
                    "handle",
                    "do",
                    "manage",
                    "execute",
                    "run",
                    "perform",
                    "operate",
                    "work",
                ]

                if name in generic_names or any(
                    name.startswith(g) for g in generic_names
                ):
                    self.add_finding(
                        description=f"Function name '{name}' is too generic",
                        severity="medium",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion=f"Rename to describe what it does, e.g., '{name}UserRegistration' or 'validateOrder'",
                    )

                # Check for inconsistent naming
                if name.startswith("get") and "delete" in fragment.content.lower():
                    self.add_finding(
                        description=f"Function '{name}' suggests getter but performs deletion",
                        severity="high",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Rename to reflect actual behavior, e.g., 'deleteAndGet' or just 'delete'",
                    )

    def _check_empty_names(self, fragments: List[CodeFragment]):
        """Check for technically correct but semantically empty names."""
        empty_patterns = [
            (r"\b\w*Manager\b", "Manager", "Too vague - what does it manage?"),
            (r"\b\w*Service\b", "Service", "Too vague - what service does it provide?"),
            (r"\b\w*Handler\b", "Handler", "Too vague - what does it handle?"),
            (r"\b\w*Processor\b", "Processor", "Too vague - what does it process?"),
            (r"\b\w*Helper\b", "Helper", "Too vague - what does it help with?"),
            (r"\b\w*Util\b", "Util", "Too vague - what utility does it provide?"),
            (r"\bhandle\w*\b", "handleX", 'What does "handle" mean specifically?'),
            (r"\bprocess\w*\b", "processX", 'What does "process" mean specifically?'),
            (r"\bdo\w*\b", "doX", 'What does "do" mean specifically?'),
        ]

        for fragment in fragments:
            for pattern, bad_name, reason in empty_patterns:
                if re.search(pattern, fragment.content):
                    self.add_finding(
                        description=f"Semantically empty name '{bad_name}': {reason}",
                        severity="low",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Use specific, domain-relevant names",
                    )

    def _check_self_documenting(self, fragments: List[CodeFragment]):
        """Check if code is self-documenting."""
        for fragment in fragments:
            if fragment.fragment_type == "function":
                # Check function length
                lines = len(fragment.content.split("\n"))
                if lines > 50:
                    self.add_finding(
                        description=f"Long function ({lines} lines) - hard to understand at a glance",
                        severity="medium",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Extract smaller, well-named functions",
                    )

                # Check for excessive comments
                comment_lines = len(re.findall(r"(#|//|\*)", fragment.content))
                code_lines = lines - comment_lines

                if code_lines > 0 and comment_lines / code_lines > 0.5:
                    self.add_finding(
                        description="high comment-to-code ratio - code may not be self-documenting",
                        severity="low",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Improve naming to reduce need for comments",
                    )

    def _check_comprehension(self, fragments: List[CodeFragment]):
        """Check if a new developer could understand the code."""
        complexity_indicators = [
            r"\breduce\s*\(",
            r"\bmap\s*\(.*\bmap\s*\(",
            r"\bfilter\s*\(.*\bmap\s*\(.*\breduce",
            r"\?\s*\?\s*\?",  # Nested ternary
            r"\[.*for.*for.*in.*in",  # Nested comprehensions
        ]

        for fragment in fragments:
            for pattern in complexity_indicators:
                if re.search(pattern, fragment.content):
                    self.add_finding(
                        description="Complex one-liner - may be hard for new developers",
                        severity="low",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Break into multiple steps with intermediate variables",
                    )

    def _check_abstraction_level(self, fragments: List[CodeFragment]):
        """Check if abstractions are at the right level."""
        for fragment in fragments:
            content = fragment.content

            # Check mixing high and low level in same function
            high_level_ops = ["process", "orchestrate", "coordinate", "manage"]
            low_level_ops = [
                "slice",
                "split",
                "charAt",
                "substring",
                "indexOf",
                "push",
                "pop",
            ]

            has_high = any(op in content for op in high_level_ops)
            has_low = sum(1 for op in low_level_ops if op in content)

            if has_high and has_low > 3:
                self.add_finding(
                    description="Mixed abstraction levels in same function",
                    severity="medium",
                    file=fragment.file_path,
                    line=fragment.start_line,
                    suggestion="Extract low-level operations into helper functions",
                )

    def _assess_naming_quality(self, fragments: List[CodeFragment]) -> str:
        """Assess overall naming quality."""
        bad_names = 0
        total_names = 0

        generic_patterns = [
            r"\b(data|temp|val|obj|arr|item|result)\b",
            r"\w*(Manager|Service|Handler|Processor|Helper|Util)\b",
        ]

        for fragment in fragments:
            if fragment.fragment_type == "function":
                total_names += 1
                if any(re.search(p, fragment.content) for p in generic_patterns):
                    bad_names += 1

        if total_names == 0:
            return "N/A"

        quality = 1 - (bad_names / total_names)
        if quality >= 0.8:
            return "good"
        elif quality >= 0.5:
            return "fair"
        else:
            return "poor"
