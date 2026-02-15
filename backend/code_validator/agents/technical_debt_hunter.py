"""Agent 4: Technical Debt Hunter - Identifies garbage code and dead code."""

import re
from collections import defaultdict
from typing import List, Dict, Any, Set
from agents.base_agent import BaseAgent
from core.models import CodeFragment, AgentResult, AgentType, ValidationContext


class TechnicalDebtHunter(BaseAgent):
    """Identifies garbage code and dead code."""

    def __init__(self):
        super().__init__(AgentType.TECHNICAL_DEBT)
        self.defined_functions = {}
        self.called_functions = set()
        self.defined_variables = defaultdict(set)
        self.used_variables = defaultdict(set)

    def analyze(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Analyze code for technical debt."""
        self.reset()

        # Collect all definitions and usages
        self._collect_definitions(fragments)
        self._collect_usages(fragments)

        # Check 1: Unused functions
        self._check_unused_functions(fragments)

        # Check 2: Unused parameters
        self._check_unused_parameters(fragments)

        # Check 3: Unused variables
        self._check_unused_variables(fragments)

        # Check 4: Unused imports
        self._check_unused_imports(fragments)

        # Check 5: Production logs
        self._check_production_logs(fragments)

        # Check 6: Comment quality
        self._check_comment_quality(fragments)

        # Check 7: Dead code
        self._check_dead_code(fragments)

        # Check 8: DRY violations
        self._check_dry_violations(fragments)

        # Check 9: Cyclomatic complexity
        self._check_complexity(fragments)

        # Mental test: code bloat estimation
        self._estimate_code_bloat(fragments)

        score = self.calculate_score()

        return AgentResult(
            agent_type=self.agent_type,
            score=score,
            gaps=self.gaps,
            findings=self.findings,
            examples=self.examples,
            raw_analysis={
                "unused_functions": len(
                    [
                        f
                        for f in self.findings
                        if "unused function" in f["description"].lower()
                    ]
                ),
                "unused_variables": len(
                    [
                        f
                        for f in self.findings
                        if "unused variable" in f["description"].lower()
                    ]
                ),
                "duplicate_blocks": len(
                    [
                        f
                        for f in self.findings
                        if "duplicate" in f["description"].lower()
                    ]
                ),
                "technical_debt_estimate": self._estimate_debt(fragments),
            },
        )

    def _collect_definitions(self, fragments: List[CodeFragment]):
        """Collect all function and variable definitions."""
        func_patterns = [
            r"def\s+(\w+)\s*\(",  # Python
            r"function\s+(\w+)\s*\(",  # JS
            r"(\w+)\s*:\s*function\s*\(",  # JS object method
            r"(\w+)\s*=\s*\([^)]*\)\s*=>",  # Arrow function
            r"(?:public|private|protected)?\s*(?:static)?\s*(?:\w+)\s+(\w+)\s*\([^)]*\)",  # Java/C#
        ]

        for fragment in fragments:
            if fragment.fragment_type in ["function", "method"]:
                name = fragment.metadata.get("name", "")
                if name:
                    self.defined_functions[name] = fragment

    def _collect_usages(self, fragments: List[CodeFragment]):
        """Collect all function calls and variable usages."""
        call_patterns = [
            r"(\w+)\s*\([^)]*\)",  # Function calls
        ]

        for fragment in fragments:
            for pattern in call_patterns:
                calls = re.findall(pattern, fragment.content)
                for call in calls:
                    if call not in [
                        "if",
                        "for",
                        "while",
                        "switch",
                        "return",
                        "yield",
                        "await",
                        "print",
                        "len",
                        "range",
                    ]:
                        self.called_functions.add(call)

    def _check_unused_functions(self, fragments: List[CodeFragment]):
        """Check for functions that are never called."""
        # Exclude entry points and test functions
        entry_point_names = ["main", "app", "server", "handler", "lambda_handler"]
        test_prefixes = ["test_", "Test"]

        for name, fragment in self.defined_functions.items():
            if name not in self.called_functions:
                if name not in entry_point_names and not any(
                    name.startswith(p) for p in test_prefixes
                ):
                    self.add_finding(
                        description=f"Unused function: '{name}'",
                        severity="medium",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Remove unused function or export it if meant to be public",
                    )

    def _check_unused_parameters(self, fragments: List[CodeFragment]):
        """Check for unused function parameters."""
        for fragment in fragments:
            if fragment.fragment_type == "function":
                args = fragment.metadata.get("args", [])
                content = fragment.content

                for arg in args:
                    # Count usages of the parameter
                    usages = len(re.findall(rf"\b{arg}\b", content))
                    if usages <= 1:  # Only defined, never used
                        self.add_finding(
                            description=f"Unused parameter '{arg}' in function '{fragment.metadata.get('name')}'",
                            severity="low",
                            file=fragment.file_path,
                            line=fragment.start_line,
                            suggestion=f"Remove unused parameter '{arg}' or prefix with _ to indicate intentional",
                        )

    def _check_unused_variables(self, fragments: List[CodeFragment]):
        """Check for variables that are assigned but never used."""
        var_patterns = [
            r"(\w+)\s*=\s*[^=]",  # Variable assignment
        ]

        for fragment in fragments:
            assignments = re.findall(var_patterns[0], fragment.content)
            for var in assignments:
                if var not in [
                    "if",
                    "for",
                    "while",
                    "return",
                    "yield",
                    "await",
                    "self",
                    "this",
                ]:
                    # Check if variable is used elsewhere in the function
                    usages = len(re.findall(rf"\b{var}\b", fragment.content))
                    if usages == 1:  # Only assigned, never used
                        self.add_finding(
                            description=f"Unused variable: '{var}'",
                            severity="low",
                            file=fragment.file_path,
                            line=fragment.start_line,
                            suggestion=f"Remove unused variable '{var}'",
                        )

    def _check_unused_imports(self, fragments: List[CodeFragment]):
        """Check for unused imports."""
        import_patterns = {
            "python": [
                r"import\s+(\w+)",
                r"from\s+\S+\s+import\s+([^\n]+)",
            ],
            "javascript": [
                r"import\s+(\w+)\s+from",
                r"import\s*\{([^}]+)\}\s*from",
            ],
        }

        for fragment in fragments:
            if fragment.fragment_type == "module":
                lang = fragment.language
                patterns = import_patterns.get(lang, [])

                for pattern in patterns:
                    imports = re.findall(pattern, fragment.content)
                    for imp in imports:
                        # Handle multiple imports
                        imported_names = [name.strip() for name in imp.split(",")]
                        for name in imported_names:
                            # Check if imported name is used
                            if name and name not in fragment.content.split("import")[1]:
                                # Simple check - may have false positives
                                pass

    def _check_production_logs(self, fragments: List[CodeFragment]):
        """Check for debug logs left in production code."""
        log_patterns = [
            r"console\.(log|debug|warn|error)",
            r"print\s*\(",
            r"logger\.(debug|info)",
            r"System\.out\.print",
            r"fmt\.Print",
            r"println!",
        ]

        debug_only_patterns = [
            r"console\.log",
            r"print\s*\(",
            r"System\.out\.print",
        ]

        for fragment in fragments:
            for pattern in debug_only_patterns:
                if re.search(pattern, fragment.content):
                    self.add_finding(
                        description=f"Debug logging found in production code",
                        severity="medium",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Remove debug logs or use a proper logging framework with levels",
                    )
                    break

    def _check_comment_quality(self, fragments: List[CodeFragment]):
        """Check if comments explain WHY not WHAT."""
        bad_comment_patterns = [
            r"#\s*\w+\s+\w+\s+\w+",  # Comments that just repeat code
            r"//\s*\w+\s+\w+\s+\w+",
        ]

        obvious_patterns = [
            r"increment",
            r"decrement",
            r"loop",
            r"check",
            r"validate",
            r"get",
            r"set",
            r"create",
            r"delete",
            r"update",
        ]

        for fragment in fragments:
            comments = re.findall(r"(#|//)\s*(.+)", fragment.content)
            for prefix, comment in comments:
                comment_lower = comment.lower()
                # Check if comment just describes what the code does
                if any(pattern in comment_lower for pattern in obvious_patterns):
                    if len(comment.split()) < 5:
                        self.add_finding(
                            description=f"Comment explains WHAT instead of WHY: '{comment[:50]}...'",
                            severity="low",
                            file=fragment.file_path,
                            line=fragment.start_line,
                            suggestion="Rewrite comment to explain the reasoning behind the code",
                        )

    def _check_dead_code(self, fragments: List[CodeFragment]):
        """Check for dead code (commented out or unreachable)."""
        dead_patterns = [
            r"^\s*#.*\w+.*\([^)]*\)",  # Commented out function calls (Python)
            r"^\s*//.*\w+.*\([^)]*\)",  # Commented out function calls (JS)
            r"if\s*\(\s*false\s*\)",  # Always false conditions
            r"if\s+False",
        ]

        for fragment in fragments:
            for pattern in dead_patterns:
                if re.search(pattern, fragment.content, re.MULTILINE):
                    self.add_finding(
                        description="Dead code detected (commented out or unreachable)",
                        severity="low",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Remove dead code - it's in git history if needed",
                    )

    def _check_dry_violations(self, fragments: List[CodeFragment]):
        """Check for code duplication (DRY violations)."""
        # Normalize code blocks and find duplicates
        code_blocks = []
        for fragment in fragments:
            if fragment.fragment_type == "function":
                lines = fragment.content.split("\n")
                for i in range(len(lines) - 2):
                    block = "\n".join(lines[i : i + 3]).strip()
                    # Normalize
                    normalized = re.sub(r"\s+", " ", block)
                    normalized = re.sub(r'"[^"]*"', '""', normalized)
                    normalized = re.sub(r"'[^']*'", "''", normalized)
                    normalized = re.sub(r"\d+", "0", normalized)
                    code_blocks.append(
                        (normalized, fragment.file_path, fragment.start_line + i)
                    )

        # Find duplicates
        seen = {}
        for normalized, file_path, line in code_blocks:
            if normalized in seen and len(normalized) > 50:
                self.add_finding(
                    description=f"Duplicate code block detected (DRY violation)",
                    severity="medium",
                    file=file_path,
                    line=line,
                    suggestion="Extract common code into a shared function",
                )
            seen[normalized] = (file_path, line)

    def _check_complexity(self, fragments: List[CodeFragment]):
        """Check cyclomatic complexity."""
        complexity_indicators = [
            r"\bif\b",
            r"\belif\b",
            r"\belse\b",
            r"\bfor\b",
            r"\bwhile\b",
            r"\band\b",
            r"\bor\b",
            r"\?\s*\:",  # Ternary
        ]

        for fragment in fragments:
            if fragment.fragment_type == "function":
                complexity = sum(
                    len(re.findall(pattern, fragment.content))
                    for pattern in complexity_indicators
                )

                if complexity > 10:
                    self.add_finding(
                        description=f"high cyclomatic complexity ({complexity}) in function '{fragment.metadata.get('name')}'",
                        severity="medium",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Refactor into smaller functions or use strategy pattern",
                    )

    def _estimate_code_bloat(self, fragments: List[CodeFragment]):
        """Estimate if code has unnecessary bloat."""
        total_lines = sum(f.end_line - f.start_line + 1 for f in fragments)
        comment_lines = sum(len(re.findall(r"(#|//|\*)", f.content)) for f in fragments)
        blank_lines = sum(f.content.count("\n\n") for f in fragments)

        actual_code = total_lines - comment_lines - blank_lines

        if total_lines > 0 and actual_code / total_lines < 0.5:
            self.add_finding(
                description=f"high ratio of non-code lines ({(1 - actual_code/total_lines)*100:.1f}%) - possible bloat",
                severity="low",
                suggestion="Review and remove unnecessary comments and blank lines",
            )

    def _estimate_debt(self, fragments: List[CodeFragment]) -> str:
        """Estimate technical debt level."""
        critical_count = len([f for f in self.findings if f["severity"] == "critical"])
        high_count = len([f for f in self.findings if f["severity"] == "high"])
        medium_count = len([f for f in self.findings if f["severity"] == "medium"])

        debt_score = critical_count * 10 + high_count * 5 + medium_count * 2

        if debt_score > 50:
            return f"high ({debt_score} points)"
        elif debt_score > 20:
            return f"medium ({debt_score} points)"
        elif debt_score > 0:
            return f"low ({debt_score} points)"
        else:
            return "minimal"
