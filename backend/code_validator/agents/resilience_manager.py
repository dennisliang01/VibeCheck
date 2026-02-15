"""Agent 8: Resilience Manager - Validates robustness against failures."""

import re
from typing import List, Dict, Any
from agents.base_agent import BaseAgent
from core.models import CodeFragment, AgentResult, AgentType, ValidationContext


class ResilienceManager(BaseAgent):
    """Valide la robustesse face aux failures."""

    def __init__(self):
        super().__init__(AgentType.RESILIENCE)

    def analyze(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Analyze code for error handling and resilience."""
        self.reset()

        # Check 1: Error path coverage
        self._check_error_paths(fragments)

        # Check 2: Recoverable vs fatal errors
        self._check_error_classification(fragments)

        # Check 3: Retry policies
        self._check_retry_policies(fragments)

        # Check 4: Circuit breakers
        self._check_circuit_breakers(fragments)

        # Check 5: Timeouts
        self._check_timeouts(fragments)

        # Check 6: External error isolation
        self._check_error_isolation(fragments)

        # Check 7: Graceful degradation
        self._check_graceful_degradation(fragments)

        # Check 8: Atomic transactions
        self._check_transactions(fragments)

        # Check red flags
        self._check_red_flags(fragments)

        score = self.calculate_score()

        return AgentResult(
            agent_type=self.agent_type,
            score=score,
            gaps=self.gaps,
            findings=self.findings,
            examples=self.examples,
            raw_analysis={
                "error_coverage": self._assess_error_coverage(fragments),
                "resilience_patterns": len(self.examples),
                "critical_gaps": len(
                    [g for g in self.gaps if g["impact"] == "critical"]
                ),
            },
        )

    def _check_error_paths(self, fragments: List[CodeFragment]):
        """Check if all error paths are covered."""
        for fragment in fragments:
            if fragment.fragment_type == "function":
                content = fragment.content

                # Check for async operations without error handling
                async_patterns = [
                    r"await\s+",
                    r"\.then\s*\(",
                    r"async\s+",
                ]

                error_patterns = [
                    r"try\s*:",
                    r"catch",
                    r"\.catch\s*\(",
                    r"except",
                    r"finally",
                ]

                has_async = any(re.search(p, content) for p in async_patterns)
                has_error_handling = any(re.search(p, content) for p in error_patterns)

                if has_async and not has_error_handling:
                    self.add_finding(
                        description=f"Async operations without error handling in '{fragment.metadata.get('name')}'",
                        severity="critical",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Wrap async operations in try/catch blocks",
                    )

    def _check_error_classification(self, fragments: List[CodeFragment]):
        """Check for distinction between recoverable and fatal errors."""
        error_types = [
            r"RecoverableError",
            r"FatalError",
            r"RetryableError",
            r"BusinessError",
            r"TechnicalError",
            r"DomainError",
        ]

        has_classification = any(
            re.search(p, f.content) for f in fragments for p in error_types
        )

        if not has_classification:
            # Check if there are custom errors at all
            custom_errors = [
                r"class\s+\w+Error",
                r"extends\s+Error",
                r"Exception\s*:",
            ]

            has_custom = any(
                re.search(p, f.content) for f in fragments for p in custom_errors
            )

            if not has_custom:
                self.add_finding(
                    description="No custom error types for error classification",
                    severity="medium",
                    suggestion="Create custom error types to distinguish recoverable vs fatal errors",
                )

                self.add_example(
                    title="Error classification example",
                    code="""
class AppError extends Error {
  constructor(message, isRecoverable = false) {
    super(message);
    this.isRecoverable = isRecoverable;
  }
}

class ValidationError extends AppError {
  constructor(message) {
    super(message, true); // Recoverable
  }
}

class DatabaseConnectionError extends AppError {
  constructor(message) {
    super(message, true); // Recoverable with retry
  }
}
""",
                    explanation="Classify errors to handle them appropriately",
                )

    def _check_retry_policies(self, fragments: List[CodeFragment]):
        """Check for retry policies with exponential backoff."""
        retry_patterns = [
            r"retry",
            r"backoff",
            r"@retry",
            r"retries",
        ]

        exponential_patterns = [
            r"exponential",
            r"2\s*\*\s*attempt",
            r"Math\.pow\s*\(",
            r"attempt\s*\*\s*2",
        ]

        external_calls = [
            r"fetch\s*\(",
            r"axios\.",
            r"requests\.",
            r"http\.",
            r"\.query\s*\(",
            r"database",
            r"api",
        ]

        for fragment in fragments:
            has_external = any(re.search(p, fragment.content) for p in external_calls)
            has_retry = any(
                re.search(p, fragment.content, re.IGNORECASE) for p in retry_patterns
            )
            has_exponential = any(
                re.search(p, fragment.content, re.IGNORECASE)
                for p in exponential_patterns
            )

            if has_external and not has_retry:
                self.add_finding(
                    description="External calls without retry policy",
                    severity="high",
                    file=fragment.file_path,
                    line=fragment.start_line,
                    suggestion="Add retry with exponential backoff for transient failures",
                )
            elif has_retry and not has_exponential:
                self.add_finding(
                    description="Retry without exponential backoff",
                    severity="medium",
                    file=fragment.file_path,
                    line=fragment.start_line,
                    suggestion="Use exponential backoff to avoid thundering herd",
                )

    def _check_circuit_breakers(self, fragments: List[CodeFragment]):
        """Check for circuit breakers on external calls."""
        circuit_patterns = [
            r"circuit",
            r"breaker",
            r"CircuitBreaker",
            r"opossum",
            r"hystrix",
            r"resilience4j",
        ]

        external_calls = [
            r"fetch\s*\(",
            r"axios\.",
            r"requests\.",
            r"http\.",
            r"\.query\s*\(",
            r"database",
            r"api",
            r"external",
        ]

        for fragment in fragments:
            has_external = any(re.search(p, fragment.content) for p in external_calls)
            has_circuit = any(
                re.search(p, fragment.content, re.IGNORECASE) for p in circuit_patterns
            )

            if has_external and not has_circuit:
                self.add_finding(
                    description="External calls without circuit breaker",
                    severity="medium",
                    file=fragment.file_path,
                    line=fragment.start_line,
                    suggestion="Add circuit breaker to prevent cascade failures",
                )

    def _check_timeouts(self, fragments: List[CodeFragment]):
        """Check for explicit timeouts on I/O operations."""
        io_patterns = [
            r"fetch\s*\(",
            r"axios\.",
            r"requests\.",
            r"http\.",
            r"\.query\s*\(",
            r"database",
            r"connect",
        ]

        timeout_patterns = [
            r"timeout",
            r"Timeout",
            r"setTimeout",
            r"deadline",
            r"AbortController",
        ]

        for fragment in fragments:
            has_io = any(re.search(p, fragment.content) for p in io_patterns)
            has_timeout = any(re.search(p, fragment.content) for p in timeout_patterns)

            if has_io and not has_timeout:
                self.add_finding(
                    description="I/O operations without explicit timeout",
                    severity="high",
                    file=fragment.file_path,
                    line=fragment.start_line,
                    suggestion="Always set timeouts on external calls",
                )

    def _check_error_isolation(self, fragments: List[CodeFragment]):
        """Check if external errors are isolated from domain."""
        domain_patterns = [
            r"domain",
            r"entity",
            r"model",
            r"business",
        ]

        external_patterns = [
            r"HTTPError",
            r"ConnectionError",
            r"TimeoutError",
            r"SQL",
            r"axios",
            r"fetch",
        ]

        for fragment in fragments:
            is_domain = any(
                re.search(p, fragment.file_path, re.IGNORECASE) for p in domain_patterns
            )
            has_external_errors = any(
                re.search(p, fragment.content) for p in external_patterns
            )

            if is_domain and has_external_errors:
                self.add_finding(
                    description="Domain layer references external error types",
                    severity="medium",
                    file=fragment.file_path,
                    line=fragment.start_line,
                    suggestion="Map external errors to domain errors at the boundary",
                )

    def _check_graceful_degradation(self, fragments: List[CodeFragment]):
        """Check for graceful degradation patterns."""
        degradation_patterns = [
            r"fallback",
            r"degrade",
            r"cache.*fallback",
            r"default.*value",
            r"optional",
            r"mock",
        ]

        has_degradation = any(
            re.search(p, f.content, re.IGNORECASE)
            for f in fragments
            for p in degradation_patterns
        )

        if not has_degradation:
            # Check if this is a service with external dependencies
            external_deps = [
                r"api",
                r"database",
                r"cache",
                r"external",
            ]

            has_deps = any(
                re.search(p, f.content, re.IGNORECASE)
                for f in fragments
                for p in external_deps
            )

            if has_deps:
                self.add_finding(
                    description="No graceful degradation pattern detected",
                    severity="medium",
                    suggestion="Implement fallback mechanisms for external service failures",
                )

    def _check_transactions(self, fragments: List[CodeFragment]):
        """Check for atomic transactions where necessary."""
        transaction_patterns = [
            r"transaction",
            r"@transactional",
            r"atomic",
            r"begin.*commit",
            r"with.*transaction",
        ]

        multi_write_patterns = [
            r"insert.*insert",
            r"update.*update",
            r"create.*create",
            r"save.*save",
        ]

        for fragment in fragments:
            has_transaction = any(
                re.search(p, fragment.content, re.IGNORECASE)
                for p in transaction_patterns
            )
            multi_writes = any(
                re.search(p, fragment.content, re.IGNORECASE)
                for p in multi_write_patterns
            )

            if multi_writes and not has_transaction:
                self.add_finding(
                    description="Multiple database operations without transaction",
                    severity="high",
                    file=fragment.file_path,
                    line=fragment.start_line,
                    suggestion="Wrap related operations in a transaction for atomicity",
                )

    def _check_red_flags(self, fragments: List[CodeFragment]):
        """Check for error handling red flags."""
        red_flags = [
            (r"catch\s*\([^)]*\)\s*\{\s*\}", "Empty catch block - errors swallowed"),
            (r"except[^:]*:\s*pass", "Empty except block - errors swallowed"),
            (r"\.catch\s*\(\s*\)\s*;", "Empty catch - errors swallowed"),
            (
                r"catch\s*\([^)]*\)\s*\{\s*return\s*null\s*\}",
                "Catch and return null - hides errors",
            ),
            (r"Promise.*then\s*\([^)]*\)\s*[^.]*\(?!catch\)", "Promise without catch"),
            (
                r"async\s+function.*\{[^}]*await[^}]*\}(?!\s*catch)",
                "Async/await without try/catch",
            ),
        ]

        for fragment in fragments:
            for pattern, desc in red_flags:
                if re.search(pattern, fragment.content):
                    self.add_finding(
                        description=f"RED FLAG: {desc}",
                        severity="critical",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Never swallow errors - log them and handle appropriately",
                    )

    def _assess_error_coverage(self, fragments: List[CodeFragment]) -> str:
        """Assess error path coverage."""
        functions_with_errors = 0
        total_functions = 0

        for fragment in fragments:
            if fragment.fragment_type == "function":
                total_functions += 1
                has_error_handling = re.search(
                    r"try|catch|except|\.catch\s*\(", fragment.content
                )
                if has_error_handling:
                    functions_with_errors += 1

        if total_functions == 0:
            return "N/A"

        coverage = functions_with_errors / total_functions
        if coverage >= 0.8:
            return "good"
        elif coverage >= 0.5:
            return "partial"
        else:
            return "poor"
