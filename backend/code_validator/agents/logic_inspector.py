"""Agent 2: Logic Inspector - Detects logical bugs and anti-patterns."""

import re
from typing import List, Dict, Any
from agents.base_agent import BaseAgent
from core.models import CodeFragment, AgentResult, AgentType, ValidationContext


class LogicInspector(BaseAgent):
    """Detects bugs logicaux et anti-patterns."""

    def __init__(self):
        super().__init__(AgentType.LOGIC)

    def analyze(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Analyze code for logical bugs and anti-patterns."""
        self.reset()

        source_fragments = [
            f for f in fragments if f.fragment_type in ["function", "method"]
        ]

        # Check 1: Unbounded loops (infinite loop risk)
        self._check_unbounded_loops(source_fragments)

        # Check 2: Dead code (unreachable conditions)
        self._check_dead_code(source_fragments)

        # Check 3: Impossible branches
        self._check_impossible_branches(source_fragments)

        # Check 4: State spaghetti (variables mutated in multiple places)
        self._check_state_spaghetti(source_fragments)

        # Check 5: Magic values
        self._check_magic_values(source_fragments)

        # Check 6: AI Red Flags
        self._check_ai_red_flags(source_fragments)

        # Check 7: System invariants
        self._check_invariants(source_fragments)

        # Check 8: Property-based testing applicability
        self._check_property_testing(source_fragments)

        score = self.calculate_score()

        return AgentResult(
            agent_type=self.agent_type,
            score=score,
            gaps=self.gaps,
            findings=self.findings,
            examples=self.examples,
            raw_analysis={
                "functions_analyzed": len(source_fragments),
                "potential_bugs": len(
                    [f for f in self.findings if f["severity"] in ["critical", "high"]]
                ),
            },
        )

    def _check_unbounded_loops(self, fragments: List[CodeFragment]):
        """Check for unbounded loops (infinite loop risk)."""
        loop_patterns = [
            (r"while\s*\(\s*true\s*\)", "while (true)"),
            (r"while\s+True", "while True"),
            (r"for\s*\(;;\)", "for(;;)"),
            (r"loop\s*\{", "loop {"),
        ]

        for fragment in fragments:
            for pattern, example in loop_patterns:
                if re.search(pattern, fragment.content):
                    # Check if there's a break condition
                    if (
                        "break" not in fragment.content
                        and "return" not in fragment.content
                    ):
                        self.add_finding(
                            description=f"Potential infinite loop: {example} without break/return",
                            severity="critical",
                            file=fragment.file_path,
                            line=fragment.start_line,
                            suggestion="Add a break condition or use a bounded loop",
                        )

    def _check_dead_code(self, fragments: List[CodeFragment]):
        """Check for dead code (unreachable conditions)."""
        dead_code_patterns = [
            (r"if\s*\(\s*false\s*\)", "if (false)"),
            (r"if\s+False", "if False"),
            (r"if\s*\(\s*0\s*\)", "if (0)"),
        ]

        for fragment in fragments:
            for pattern, example in dead_code_patterns:
                if re.search(pattern, fragment.content):
                    self.add_finding(
                        description=f"Dead code detected: {example} will never execute",
                        severity="medium",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Remove dead code or fix the condition",
                    )

    def _check_impossible_branches(self, fragments: List[CodeFragment]):
        """Check for logically impossible branches."""
        for fragment in fragments:
            content = fragment.content

            # Check for contradictory conditions
            contradictory_patterns = [
                (
                    r"if\s*\([^)]+\)\s*\{[^}]*\}\s*else\s*if\s*\(\s*!?\1\s*\)",
                    "Contradictory conditions",
                ),
            ]

            # Check for same condition in if-elif chain
            if_pattern = r"if\s*\(([^)]+)\)"
            elif_pattern = r"else\s+if\s*\(([^)]+)\)"

            if_matches = re.findall(if_pattern, content)
            elif_matches = re.findall(elif_pattern, content)

            for cond in if_matches:
                if cond in elif_matches:
                    self.add_finding(
                        description=f"Duplicate condition in if-elif chain: {cond}",
                        severity="high",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Remove duplicate condition or fix the logic",
                    )

    def _check_state_spaghetti(self, fragments: List[CodeFragment]):
        """Check for variables mutated in multiple places."""
        for fragment in fragments:
            # Find variable assignments
            assignment_pattern = r"(\w+)\s*=\s*[^=]"
            assignments = re.findall(assignment_pattern, fragment.content)

            # Count mutations per variable
            var_counts = {}
            for var in assignments:
                if var not in ["if", "for", "while", "return", "yield", "await"]:
                    var_counts[var] = var_counts.get(var, 0) + 1

            # Flag variables mutated more than 3 times
            for var, count in var_counts.items():
                if count > 3:
                    self.add_finding(
                        description=f"Variable '{var}' mutated {count} times - potential state spaghetti",
                        severity="medium",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Consider refactoring to reduce mutations or use immutable patterns",
                    )

    def _check_magic_values(self, fragments: List[CodeFragment]):
        """Check for unnamed magic values."""
        magic_patterns = [
            (r"[^\w](\d{3,})[^\w]", "Numeric literal"),
            (
                r'["\']([a-zA-Z_]+[a-zA-Z0-9_]*\.[a-zA-Z]+)["\']',
                "String that looks like a constant",
            ),
        ]

        common_constants = [
            "0",
            "1",
            "2",
            "10",
            "100",
            "200",
            "404",
            "500",
            "true",
            "false",
            "null",
            "None",
        ]

        for fragment in fragments:
            for pattern, desc in magic_patterns:
                matches = re.findall(pattern, fragment.content)
                for match in matches:
                    if match not in common_constants and len(match) > 2:
                        self.add_finding(
                            description=f"Magic value detected: {match}",
                            severity="low",
                            file=fragment.file_path,
                            line=fragment.start_line,
                            suggestion=f"Extract '{match}' into a named constant",
                        )

    def _check_ai_red_flags(self, fragments: List[CodeFragment]):
        """Check for AI-generated code red flags."""
        red_flags = [
            (
                r"if\s*\([^)]+\)\s*\{[^}]*\}\s*else\s*\{[^}]*\}\s*else\s*\{",
                "Cascading defensive ifs",
            ),
            (r"if\s*\([^)]+\)\s*\{[^}]*if\s*\(", "Nested defensive ifs"),
            (
                r"if\s*\([^)]+\)\s*\{\s*if\s*\([^)]+\)\s*\{\s*if\s*\(",
                "Deeply nested ifs",
            ),
        ]

        verbose_empty_pattern = r"\{\s*\}"

        for fragment in fragments:
            # Check for defensive if cascades
            defensive_count = len(re.findall(r"if\s*\([^)]*\)", fragment.content))
            if defensive_count > 5:
                self.add_finding(
                    description=f"Excessive defensive if statements ({defensive_count}) - possible AI verbosity",
                    severity="medium",
                    file=fragment.file_path,
                    line=fragment.start_line,
                    suggestion="Consolidate validation logic or use early returns",
                )

            # Check for duplicate logic
            lines = fragment.content.split("\n")
            line_set = set()
            duplicates = []
            for i, line in enumerate(lines):
                stripped = line.strip()
                if len(stripped) > 20 and stripped in line_set:
                    duplicates.append((i, stripped))
                line_set.add(stripped)

            if duplicates:
                self.add_finding(
                    description=f"Duplicate logic detected - possible copy-paste from AI",
                    severity="medium",
                    file=fragment.file_path,
                    line=fragment.start_line + duplicates[0][0],
                    suggestion="Extract common logic into a shared function",
                )

            # Check for verbose but empty code
            empty_blocks = re.findall(verbose_empty_pattern, fragment.content)
            if len(empty_blocks) > 2:
                self.add_finding(
                    description="Empty code blocks detected - possible AI placeholder",
                    severity="low",
                    file=fragment.file_path,
                    line=fragment.start_line,
                    suggestion="Remove empty blocks or implement the missing logic",
                )

    def _check_invariants(self, fragments: List[CodeFragment]):
        """Check for system invariants that should always hold."""
        # Look for comments indicating invariants
        invariant_patterns = [
            r"invariant",
            r"always",
            r"never",
            r"must be",
            r"should always",
        ]

        invariant_found = any(
            re.search(pattern, f.content, re.IGNORECASE)
            for f in fragments
            for pattern in invariant_patterns
        )

        if not invariant_found:
            self.add_finding(
                description="No explicit invariants documented",
                severity="low",
                suggestion="Document key invariants that should always hold true",
            )

    def _check_property_testing(self, fragments: List[CodeFragment]):
        """Check if property-based testing is applicable."""
        # Look for functions with clear mathematical properties
        property_indicators = [
            r"def\s+\w+.*sort",
            r"def\s+\w+.*filter",
            r"def\s+\w+.*map",
            r"def\s+\w+.*reduce",
            r"def\s+\w+.*transform",
            r"function\s+\w+.*sort",
            r"function\s+\w+.*filter",
        ]

        has_pure_functions = any(
            re.search(pattern, f.content, re.IGNORECASE)
            for f in fragments
            for pattern in property_indicators
        )

        if has_pure_functions:
            self.add_example(
                title="Property-based testing applicable",
                code="""
# Consider using property-based testing:
# Python: hypothesis
# JavaScript: fast-check
# Java: jqwik

# Example property:
# For all lists L: sort(L) should be ordered
# For all lists L: length(sort(L)) == length(L)
""",
                explanation="Pure functions with clear mathematical properties are ideal for property-based testing",
            )
