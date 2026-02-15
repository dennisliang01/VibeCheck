"""Agent 7: Observability & Debug - Ensures production diagnosability."""

import re
from typing import List, Dict, Any
from agents.base_agent import BaseAgent
from core.models import CodeFragment, AgentResult, AgentType, ValidationContext


class ObservabilityDebug(BaseAgent):
    """Garantit la capacite a diagnostiquer en production."""

    def __init__(self):
        super().__init__(AgentType.OBSERVABILITY)

    def analyze(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Analyze code for observability."""
        self.reset()

        # Check 1: Structured logs
        self._check_structured_logs(fragments)

        # Check 2: Log levels
        self._check_log_levels(fragments)

        # Check 3: Log pollution
        self._check_log_pollution(fragments)

        # Check 4: Context in logs
        self._check_log_context(fragments)

        # Check 5: Error context
        self._check_error_context(fragments)

        # Check 6: Request IDs
        self._check_request_ids(fragments)

        # Check 7: Fail fast vs silent
        self._check_fail_behavior(fragments)

        # Check 8: Business metrics
        self._check_business_metrics(fragments)

        # Check 9: Health checks
        self._check_health_checks(fragments)

        # Check 10: Circuit breakers
        self._check_circuit_breakers(fragments)

        score = self.calculate_score()

        return AgentResult(
            agent_type=self.agent_type,
            score=score,
            gaps=self.gaps,
            findings=self.findings,
            examples=self.examples,
            raw_analysis={
                "observability_gaps": len(self.gaps),
                "logging_quality": self._assess_logging_quality(fragments),
                "tracing_support": self._assess_tracing(fragments),
            },
        )

    def _check_structured_logs(self, fragments: List[CodeFragment]):
        """Check if logs are structured (JSON)."""
        log_patterns = [
            r"console\.(log|info|warn|error)",
            r"print\s*\(",
            r"logger\.(debug|info|warn|error)",
        ]

        structured_patterns = [
            r"json\.(dumps|dump)",
            r"JSON\.stringify",
            r'\{[^}]*"[^"]+"[^}]*\}',  # Looks like JSON object
        ]

        for fragment in fragments:
            has_logs = any(re.search(p, fragment.content) for p in log_patterns)
            is_structured = any(
                re.search(p, fragment.content) for p in structured_patterns
            )

            if has_logs and not is_structured:
                self.add_finding(
                    description="Unstructured logging detected",
                    severity="medium",
                    file=fragment.file_path,
                    line=fragment.start_line,
                    suggestion="Use structured JSON logs for better parsing by Loki/Datadog/ELK",
                )

                self.add_example(
                    title="Structured logging example",
                    code="""
# Instead of:
logger.info(f"User {user_id} logged in from {ip}")

# Use:
logger.info({
    "event": "user_login",
    "user_id": user_id,
    "ip": ip,
    "timestamp": datetime.utcnow().isoformat()
})
""",
                    explanation="Structured logs are queryable and parseable by log aggregation tools",
                )

    def _check_log_levels(self, fragments: List[CodeFragment]):
        """Check if logs use appropriate levels."""
        level_patterns = [
            r"\.debug\s*\(",
            r"\.info\s*\(",
            r"\.warn\s*\(",
            r"\.error\s*\(",
        ]

        for fragment in fragments:
            has_levels = any(re.search(p, fragment.content) for p in level_patterns)

            if not has_levels:
                # Check if there are logs without levels
                simple_logs = re.findall(r"console\.(log)\s*\(", fragment.content)
                if simple_logs:
                    self.add_finding(
                        description="Logs without proper level distinction",
                        severity="low",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Use appropriate log levels: debug, info, warn, error",
                    )

    def _check_log_pollution(self, fragments: List[CodeFragment]):
        """Check for log pollution (too much noise)."""
        log_patterns = [
            r"console\.(log|debug)",
            r"logger\.(debug|info)",
            r"print\s*\(",
        ]

        for fragment in fragments:
            log_count = sum(len(re.findall(p, fragment.content)) for p in log_patterns)
            line_count = len(fragment.content.split("\n"))

            if line_count > 0 and log_count / line_count > 0.3:
                self.add_finding(
                    description=f"high log density ({log_count} logs in {line_count} lines) - potential noise",
                    severity="low",
                    file=fragment.file_path,
                    line=fragment.start_line,
                    suggestion="Reduce log frequency or use debug level for verbose logs",
                )

    def _check_log_context(self, fragments: List[CodeFragment]):
        """Check if logs have sufficient context."""
        context_patterns = [
            r"userId",
            r"user_id",
            r"requestId",
            r"request_id",
            r"correlationId",
            r"correlation_id",
            r"traceId",
            r"trace_id",
            r"sessionId",
            r"session_id",
        ]

        for fragment in fragments:
            has_logs = re.search(r"console\.|logger\.|print\s*\(", fragment.content)
            has_context = any(re.search(p, fragment.content) for p in context_patterns)

            if has_logs and not has_context:
                self.add_finding(
                    description="Logs may lack sufficient context for debugging",
                    severity="medium",
                    file=fragment.file_path,
                    line=fragment.start_line,
                    suggestion="Include userId, requestId, correlationId in logs",
                )

    def _check_error_context(self, fragments: List[CodeFragment]):
        """Check if errors are contextualized."""
        error_patterns = [
            r"catch\s*\(",
            r"except",
            r"\.catch\s*\(",
        ]

        context_patterns = [
            r"context",
            r"metadata",
            r"details",
            r"extra",
            r"userId",
            r"action",
            r"operation",
        ]

        for fragment in fragments:
            for pattern in error_patterns:
                matches = re.finditer(pattern, fragment.content)
                for match in matches:
                    # Check context after catch
                    context_start = match.end()
                    context_end = min(context_start + 300, len(fragment.content))
                    catch_context = fragment.content[context_start:context_end]

                    has_context = any(
                        re.search(p, catch_context, re.IGNORECASE)
                        for p in context_patterns
                    )

                    if not has_context:
                        self.add_finding(
                            description="Error handling without sufficient context",
                            severity="medium",
                            file=fragment.file_path,
                            line=fragment.start_line,
                            suggestion="Add context (userId, operation, metadata) to error logs",
                        )

    def _check_request_ids(self, fragments: List[CodeFragment]):
        """Check for request ID tracing."""
        request_id_patterns = [
            r"requestId",
            r"request_id",
            r"X-Request-ID",
            r"correlationId",
            r"correlation_id",
            r"traceId",
        ]

        has_request_ids = any(
            re.search(p, f.content, re.IGNORECASE)
            for f in fragments
            for p in request_id_patterns
        )

        if not has_request_ids:
            # Check if this is a web service
            web_indicators = [
                "app.get",
                "app.post",
                "router",
                "handler",
                "request",
                "response",
            ]
            looks_like_web = any(
                re.search(p, f.content) for f in fragments for p in web_indicators
            )

            if looks_like_web:
                self.add_finding(
                    description="No request ID tracing detected",
                    severity="medium",
                    suggestion="Generate and propagate request IDs for distributed tracing",
                )

    def _check_fail_behavior(self, fragments: List[CodeFragment]):
        """Check fail fast vs fail silent behavior."""
        silent_fail_patterns = [
            r"catch\s*\([^)]*\)\s*\{\s*\}",  # Empty catch
            r"except[^:]*:\s*pass",  # Python empty except
            r"\.catch\s*\(\s*\)\s*;",  # Empty JS catch
        ]

        for fragment in fragments:
            for pattern in silent_fail_patterns:
                if re.search(pattern, fragment.content):
                    self.add_finding(
                        description="Silent failure detected - errors are swallowed",
                        severity="critical",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Never silently swallow errors - at minimum log them",
                    )

    def _check_business_metrics(self, fragments: List[CodeFragment]):
        """Check for business metrics, not just technical ones."""
        metric_patterns = [
            r"metrics",
            r"counter",
            r"histogram",
            r"gauge",
            r"prometheus",
            r"datadog",
            r"statsd",
        ]

        business_indicators = [
            r"order",
            r"payment",
            r"user",
            r"signup",
            r"purchase",
            r"revenue",
            r"conversion",
            r"retention",
        ]

        has_metrics = any(
            re.search(p, f.content, re.IGNORECASE)
            for f in fragments
            for p in metric_patterns
        )

        has_business_logic = any(
            re.search(p, f.content, re.IGNORECASE)
            for f in fragments
            for p in business_indicators
        )

        if has_business_logic and not has_metrics:
            self.add_finding(
                description="Business logic without business metrics",
                severity="medium",
                suggestion="Add business metrics (orders created, payments processed, etc.)",
            )

    def _check_health_checks(self, fragments: List[CodeFragment]):
        """Check for health check endpoints."""
        health_patterns = [
            r"health",
            r"ready",
            r"liveness",
            r"/ping",
            r"/status",
        ]

        has_health = any(
            re.search(p, f.content, re.IGNORECASE)
            for f in fragments
            for p in health_patterns
        )

        # Check if this is a service
        service_indicators = [
            "app.listen",
            "server.listen",
            "createServer",
            "uvicorn",
            "gunicorn",
        ]
        looks_like_service = any(
            re.search(p, f.content) for f in fragments for p in service_indicators
        )

        if looks_like_service and not has_health:
            self.add_finding(
                description="No health check endpoint detected",
                severity="medium",
                suggestion="Add /health and /ready endpoints for orchestration",
            )

    def _check_circuit_breakers(self, fragments: List[CodeFragment]):
        """Check for circuit breakers on external calls."""
        external_call_patterns = [
            r"fetch\s*\(",
            r"axios\.",
            r"requests\.",
            r"http\.",
            r"https\.",
            r"\.query\s*\(",
            r"\.find\s*\(",
            r"\.get\s*\(",
        ]

        circuit_breaker_patterns = [
            r"circuit",
            r"breaker",
            r"timeout",
            r"retry",
            r"@retry",
            r"backoff",
            r"resilience",
        ]

        for fragment in fragments:
            has_external = any(
                re.search(p, fragment.content) for p in external_call_patterns
            )
            has_circuit = any(
                re.search(p, fragment.content, re.IGNORECASE)
                for p in circuit_breaker_patterns
            )

            if has_external and not has_circuit:
                self.add_finding(
                    description="External calls without circuit breaker pattern",
                    severity="medium",
                    file=fragment.file_path,
                    line=fragment.start_line,
                    suggestion="Add circuit breakers to prevent cascade failures",
                )

    def _assess_logging_quality(self, fragments: List[CodeFragment]) -> str:
        """Assess overall logging quality."""
        has_logs = any(
            re.search(r"console\.|logger\.|print\s*\(", f.content) for f in fragments
        )

        has_structure = any(
            re.search(r'json|JSON\.stringify|\{[^}]*"[^"]+"[^}]*\}', f.content)
            for f in fragments
        )

        if has_logs and has_structure:
            return "good"
        elif has_logs:
            return "needs_structure"
        else:
            return "missing"

    def _assess_tracing(self, fragments: List[CodeFragment]) -> str:
        """Assess tracing support."""
        tracing_patterns = [
            r"traceId",
            r"spanId",
            r"X-Request-ID",
            r"opentelemetry",
            r"jaeger",
            r"zipkin",
            r"distributed",
        ]

        has_tracing = any(
            re.search(p, f.content, re.IGNORECASE)
            for f in fragments
            for p in tracing_patterns
        )

        return "supported" if has_tracing else "missing"
