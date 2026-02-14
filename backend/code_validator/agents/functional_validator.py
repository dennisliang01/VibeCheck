"""Agent 1: Functional Validator - Validates code functionality and test coverage."""

import re
from typing import List, Dict, Any
from agents.base_agent import BaseAgent
from core.models import CodeFragment, AgentResult, AgentType, ValidationContext


class FunctionalValidator(BaseAgent):
    """Validates that code does what it should do, robustly."""

    def __init__(self):
        super().__init__(AgentType.FUNCTIONAL)
        self.test_patterns = {
            "python": [r"def test_", r"class Test", r"@pytest"],
            "javascript": [r"it\s*\(", r"describe\s*\(", r"test\s*\(", r"\.test\("],
            "typescript": [r"it\s*\(", r"describe\s*\(", r"test\s*\(", r"\.test\("],
            "java": [r"@Test", r"void test"],
            "go": [r"func Test"],
            "rust": [r"#\[test\]", r"fn test_"],
        }

    def analyze(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Analyze code for functional validation."""
        self.reset()

        test_fragments = [f for f in fragments if self._is_test_file(f)]
        source_fragments = [f for f in fragments if not self._is_test_file(f)]

        # Check 1: Unit tests present
        self._check_unit_tests(test_fragments, source_fragments, context)

        # Check 2: Edge cases coverage
        self._check_edge_cases(test_fragments)

        # Check 3: Input validation
        self._check_input_validation(source_fragments)

        # Check 4: Absurd/antagonist cases
        self._check_antagonist_cases(test_fragments)

        # Check 5: Non-regression tests
        self._check_non_regression_tests(test_fragments)

        # Check 6: Snapshot tests for structured outputs
        self._check_snapshot_tests(test_fragments, context)

        # Check 7: Contract tests
        self._check_contract_tests(source_fragments, test_fragments)

        # Check 8: Mutation testing indicators
        self._check_mutation_indicators(test_fragments)

        score = self.calculate_score()

        return AgentResult(
            agent_type=self.agent_type,
            score=score,
            gaps=self.gaps,
            findings=self.findings,
            examples=self.examples,
            raw_analysis={
                "test_count": len(test_fragments),
                "source_count": len(source_fragments),
                "test_coverage_estimate": self._estimate_coverage(
                    test_fragments, source_fragments
                ),
            },
        )

    def _is_test_file(self, fragment: CodeFragment) -> bool:
        """Check if fragment is from a test file."""
        test_indicators = ["test", "spec", "__tests__", "tests/"]
        return any(
            indicator in fragment.file_path.lower() for indicator in test_indicators
        )

    def _check_unit_tests(
        self,
        test_fragments: List[CodeFragment],
        source_fragments: List[CodeFragment],
        context: ValidationContext,
    ):
        """Check if unit tests are present and pass."""
        if not test_fragments:
            self.add_gap(
                description="No test files found in the project",
                impact="critical",
                fix_example="Create test files following naming conventions: *.test.js, *_test.py, etc.",
            )
            return

        # Count test functions
        test_count = sum(
            1
            for f in test_fragments
            for pattern in self.test_patterns.get(context.language, [])
            if re.search(pattern, f.content)
        )

        source_functions = sum(
            1 for f in source_fragments if f.fragment_type == "function"
        )

        if source_functions > 0 and test_count == 0:
            self.add_gap(
                description=f"Found {source_functions} functions but no unit tests",
                impact="critical",
                fix_example="Add unit tests for each public function",
            )
        elif test_count < source_functions * 0.5:
            self.add_gap(
                description=f"low test coverage: {test_count} tests for {source_functions} functions",
                impact="high",
                fix_example="Increase test coverage to at least 80%",
            )

    def _check_edge_cases(self, test_fragments: List[CodeFragment]):
        """Check if edge cases are identified and covered."""
        edge_case_patterns = [
            r"null",
            r"undefined",
            r"None",
            r"empty",
            r"\\[\\]",
            r'""',
            r"0\b",
            r"-1",
            r"max",
            r"min",
            r"Infinity",
            r"NaN",
            r"edge",
            r"corner",
            r"boundary",
        ]

        edge_case_found = any(
            re.search(pattern, f.content, re.IGNORECASE)
            for f in test_fragments
            for pattern in edge_case_patterns
        )

        if not edge_case_found and test_fragments:
            self.add_gap(
                description="No explicit edge case tests found",
                impact="high",
                fix_example="""
# Add tests for edge cases:
def test_function_with_null_input():
    assert function(None) == expected_result

def test_function_with_empty_input():
    assert function([]) == expected_result

def test_function_with_extreme_values():
    assert function(MAX_INT) == expected_result
""",
            )

    def _check_input_validation(self, source_fragments: List[CodeFragment]):
        """Check if extreme inputs are handled."""
        validation_patterns = [
            r"if\s+\w+\s*(==|!=)\s*(null|undefined|None)",
            r"if\s+not\s+\w+",
            r"try\s*:",
            r"except",
            r"catch",
            r"raise\s+",
            r"throw\s+",
            r"assert\s+",
            r"\.validate",
            r"validator",
        ]

        for fragment in source_fragments:
            if fragment.fragment_type == "function":
                has_validation = any(
                    re.search(pattern, fragment.content)
                    for pattern in validation_patterns
                )

                if not has_validation and len(fragment.content) > 100:
                    self.add_finding(
                        description=f"Function '{fragment.metadata.get('name', 'unknown')}' lacks input validation",
                        severity="medium",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Add input validation at the start of the function",
                    )

    def _check_antagonist_cases(self, test_fragments: List[CodeFragment]):
        """Check if absurd/antagonist cases are handled."""
        antagonist_patterns = [
            r"malicious",
            r"attack",
            r"injection",
            r"xss",
            r"sql",
            r"negative",
            r"invalid",
            r"wrong",
            r"bad",
            r"error",
        ]

        antagonist_found = any(
            re.search(pattern, f.content, re.IGNORECASE)
            for f in test_fragments
            for pattern in antagonist_patterns
        )

        if not antagonist_found and test_fragments:
            self.add_finding(
                description="Consider adding tests for antagonist/malicious inputs",
                severity="low",
                suggestion="Test how your code handles unexpected or malicious inputs",
            )

    def _check_non_regression_tests(self, test_fragments: List[CodeFragment]):
        """Check for non-regression tests."""
        regression_patterns = [
            r"regression",
            r"bug",
            r"fix",
            r"issue",
            r"ticket",
            r"#[0-9]+",
            r"github",
            r"jira",
        ]

        regression_found = any(
            re.search(pattern, f.content, re.IGNORECASE)
            for f in test_fragments
            for pattern in regression_patterns
        )

        if not regression_found and test_fragments:
            self.add_finding(
                description="Consider documenting non-regression tests with bug references",
                severity="low",
                suggestion="Add comments linking tests to specific bugs or issues",
            )

    def _check_snapshot_tests(
        self, test_fragments: List[CodeFragment], context: ValidationContext
    ):
        """Check for snapshot tests for structured outputs."""
        snapshot_patterns = [r"snapshot", r"toMatchSnapshot", r"snapshot\(", r"approve"]

        api_patterns = [r"api", r"endpoint", r"response", r"json", r"serialize"]

        has_api_code = any(
            re.search(pattern, f.content, re.IGNORECASE)
            for f in test_fragments
            for pattern in api_patterns
        )

        has_snapshot_tests = any(
            re.search(pattern, f.content, re.IGNORECASE)
            for f in test_fragments
            for pattern in snapshot_patterns
        )

        if has_api_code and not has_snapshot_tests:
            self.add_finding(
                description="API/JSON outputs should have snapshot tests",
                severity="medium",
                suggestion="Add snapshot tests to detect unexpected changes in API responses",
            )

    def _check_contract_tests(
        self, source_fragments: List[CodeFragment], test_fragments: List[CodeFragment]
    ):
        """Check for contract tests (types, formats)."""
        contract_patterns = [
            r"contract",
            r"interface",
            r"type",
            r"schema",
            r"validation",
            r"pydantic",
            r"zod",
            r"joi",
            r"yup",
            r"@types",
        ]

        has_contract_tests = any(
            re.search(pattern, f.content, re.IGNORECASE)
            for f in test_fragments
            for pattern in contract_patterns
        )

        if not has_contract_tests and test_fragments:
            self.add_finding(
                description="Consider adding contract tests for type validation",
                severity="medium",
                suggestion="Test that functions accept/reject correct types at runtime",
            )

    def _check_mutation_indicators(self, test_fragments: List[CodeFragment]):
        """Check indicators for mutation testing."""
        # Check if tests would catch simple mutations
        assertion_patterns = [
            r"assertEqual",
            r"assertTrue",
            r"assertFalse",
            r"assertRaises",
            r"expect\(",
            r"toBe",
            r"toEqual",
            r"toThrow",
            r"toMatch",
        ]

        assertion_count = sum(
            1
            for f in test_fragments
            for pattern in assertion_patterns
            if re.search(pattern, f.content)
        )

        if assertion_count < len(test_fragments) * 2 and test_fragments:
            self.add_finding(
                description="low assertion density - mutation testing may reveal weak tests",
                severity="medium",
                suggestion="Add more specific assertions to catch code mutations",
            )

    def _estimate_coverage(
        self, test_fragments: List[CodeFragment], source_fragments: List[CodeFragment]
    ) -> str:
        """Estimate test coverage."""
        if not source_fragments:
            return "N/A"

        source_funcs = len(
            [f for f in source_fragments if f.fragment_type == "function"]
        )
        if source_funcs == 0:
            return "N/A"

        # Rough estimation based on test file count
        test_ratio = (
            len(test_fragments) / len(source_fragments) if source_fragments else 0
        )

        if test_ratio >= 0.8:
            return "high (>80%)"
        elif test_ratio >= 0.5:
            return "medium (50-80%)"
        elif test_ratio > 0:
            return "low (<50%)"
        else:
            return "none"
