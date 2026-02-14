"""Agent 6: Security Auditor - Detects vulnerabilities."""

import re
from typing import List, Dict, Any
from agents.base_agent import BaseAgent
from core.models import CodeFragment, AgentResult, AgentType, ValidationContext


class SecurityAuditor(BaseAgent):
    """Detects vulnerabilities without external tools."""

    def __init__(self):
        super().__init__(AgentType.SECURITY)

    def analyze(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Analyze code for security vulnerabilities."""
        self.reset()

        # Check 1: Input sanitization
        self._check_input_sanitization(fragments)

        # Check 2: Zero trust on user data
        self._check_zero_trust(fragments)

        # Check 3: Secrets in code
        self._check_secrets(fragments)

        # Check 4: Sensitive data in logs
        self._check_sensitive_logs(fragments)

        # Check 5: Authorization checks
        self._check_authorization(fragments)

        # Check 6: Authentication
        self._check_authentication(fragments)

        # Check critical AI red flags
        self._check_critical_red_flags(fragments)

        score = self.calculate_score()

        return AgentResult(
            agent_type=self.agent_type,
            score=score,
            gaps=self.gaps,
            findings=self.findings,
            examples=self.examples,
            raw_analysis={
                "critical_vulnerabilities": len(
                    [f for f in self.findings if f["severity"] == "critical"]
                ),
                "high_vulnerabilities": len(
                    [f for f in self.findings if f["severity"] == "high"]
                ),
                "security_score": score,
            },
        )

    def _check_input_sanitization(self, fragments: List[CodeFragment]):
        """Check if inputs are sanitized and validated."""
        input_sources = [
            r"request\.(args|form|json|body)",
            r"req\.(body|params|query)",
            r"event\.(body|pathParameters|queryStringParameters)",
            r"sys\.argv",
            r"input\s*\(",
            r"argv\[",
        ]

        validation_patterns = [
            r"validate",
            r"schema",
            r"validator",
            r"sanitiz",
            r"@validates",
            r"pydantic",
            r"joi",
            r"yup",
            r"zod",
            r"try\s*:",
            r"except",
            r"catch",
        ]

        for fragment in fragments:
            has_input = any(re.search(p, fragment.content) for p in input_sources)
            has_validation = any(
                re.search(p, fragment.content, re.IGNORECASE)
                for p in validation_patterns
            )

            if has_input and not has_validation:
                self.add_finding(
                    description="User input received without validation",
                    severity="critical",
                    file=fragment.file_path,
                    line=fragment.start_line,
                    suggestion="Add input validation using a schema validator",
                )

    def _check_zero_trust(self, fragments: List[CodeFragment]):
        """Check for zero trust on user data."""
        dangerous_usage_patterns = [
            (r"eval\s*\(", "eval() with potentially user input"),
            (r"exec\s*\(", "exec() with potentially user input"),
            (r"new\s+Function\s*\(", "new Function() with potentially user input"),
            (r"document\.write\s*\(", "document.write() with potentially user input"),
            (r"\.innerHTML\s*=", "innerHTML assignment with potentially user input"),
            (r"html\s*=.*\+", "HTML string concatenation"),
        ]

        for fragment in fragments:
            for pattern, desc in dangerous_usage_patterns:
                if re.search(pattern, fragment.content):
                    self.add_finding(
                        description=f"Dangerous operation: {desc}",
                        severity="critical",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Never execute or render user input directly - sanitize first",
                    )

    def _check_secrets(self, fragments: List[CodeFragment]):
        """Check for secrets in code."""
        secret_patterns = [
            (r'api[_-]?key\s*[=:]\s*["\']\w+', "API key"),
            (r'password\s*[=:]\s*["\'][^"\']+', "Password"),
            (r'secret\s*[=:]\s*["\']\w+', "Secret"),
            (r'token\s*[=:]\s*["\']\w+', "Token"),
            (r'aws_access_key_id\s*[=:]\s*["\']\w+', "AWS Access Key"),
            (r'aws_secret_access_key\s*[=:]\s*["\']\w+', "AWS Secret Key"),
            (r'private[_-]?key\s*[=:]\s*["\']', "Private Key"),
            (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API Key"),
            (r"ghp_[a-zA-Z0-9]{36}", "GitHub Token"),
        ]

        for fragment in fragments:
            for pattern, secret_type in secret_patterns:
                matches = re.findall(pattern, fragment.content, re.IGNORECASE)
                for match in matches:
                    self.add_finding(
                        description=f"Potential {secret_type} exposed in code",
                        severity="critical",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Move secrets to environment variables or a secrets manager",
                    )

    def _check_sensitive_logs(self, fragments: List[CodeFragment]):
        """Check for sensitive data in logs."""
        log_patterns = [
            r"console\.(log|debug|info)",
            r"print\s*\(",
            r"logger\.(debug|info)",
        ]

        sensitive_patterns = [
            r"password",
            r"token",
            r"secret",
            r"key",
            r"credential",
            r"ssn",
            r"credit",
            r"card",
            r"email",
            r"phone",
        ]

        for fragment in fragments:
            for log_pat in log_patterns:
                log_matches = re.finditer(log_pat, fragment.content)
                for match in log_matches:
                    # Check context after log statement
                    context_start = match.end()
                    context_end = min(context_start + 200, len(fragment.content))
                    log_context = fragment.content[context_start:context_end]

                    for sensitive_pat in sensitive_patterns:
                        if re.search(sensitive_pat, log_context, re.IGNORECASE):
                            self.add_finding(
                                description=f"Potentially sensitive data ('{sensitive_pat}') may be logged",
                                severity="high",
                                file=fragment.file_path,
                                line=fragment.start_line,
                                suggestion="Redact sensitive fields before logging",
                            )

    def _check_authorization(self, fragments: List[CodeFragment]):
        """Check for authorization checks."""
        auth_patterns = [
            r"@require_auth",
            r"@login_required",
            r"@authenticated",
            r"check_permission",
            r"has_permission",
            r"can_access",
            r"is_authorized",
            r"authorize",
            r"@roles_allowed",
            r"@permission_required",
            r"@admin_required",
        ]

        # Entry points that should have auth
        entry_patterns = [
            r"@app\.route",
            r"app\.(get|post|put|delete)",
            r"router\.(get|post|put|delete)",
            r"exports\.(handler|main)",
        ]

        for fragment in fragments:
            is_entry = any(re.search(p, fragment.content) for p in entry_patterns)
            has_auth = any(
                re.search(p, fragment.content, re.IGNORECASE) for p in auth_patterns
            )

            if is_entry and not has_auth:
                # Check if it's a public endpoint (health check, etc.)
                if (
                    "health" not in fragment.content.lower()
                    and "public" not in fragment.content.lower()
                ):
                    self.add_finding(
                        description="Endpoint without explicit authorization check",
                        severity="high",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Add @login_required or equivalent decorator",
                    )

    def _check_authentication(self, fragments: List[CodeFragment]):
        """Check for authentication where necessary."""
        auth_indicators = [
            r"jwt",
            r"token",
            r"session",
            r"cookie",
            r"auth",
            r"login",
            r"password",
            r"oauth",
            r"saml",
        ]

        has_auth_system = any(
            re.search(p, f.content, re.IGNORECASE)
            for f in fragments
            for p in auth_indicators
        )

        if not has_auth_system:
            # Check if this looks like an API/backend service
            api_indicators = ["api", "endpoint", "route", "controller", "handler"]
            looks_like_api = any(
                re.search(p, f.content, re.IGNORECASE)
                for f in fragments
                for p in api_indicators
            )

            if looks_like_api:
                self.add_finding(
                    description="No authentication mechanism detected in API service",
                    severity="critical",
                    suggestion="Implement authentication (JWT, OAuth, Session-based)",
                )

    def _check_critical_red_flags(self, fragments: List[CodeFragment]):
        """Check for critical AI-generated security red flags."""
        critical_flags = [
            (r"eval\s*\(", "eval() - critical: Can execute arbitrary code"),
            (
                r"new\s+Function\s*\(",
                "new Function() - critical: Can execute arbitrary code",
            ),
            (
                r"`[^`]*\$\{[^}]*\}[^`]*`.*user",
                "Template literal with user input - possible injection",
            ),
            (
                r'\.query\s*\(\s*[`"\'][^`"\']*\$',
                "SQL query with string interpolation - SQL injection",
            ),
            (r"JSON\.parse\s*\([^)]*user", "JSON.parse on untrusted data"),
            (r"pickle\.(loads|load)", "pickle.loads - can execute arbitrary code"),
            (r"yaml\.load\s*\([^)]*\)", "yaml.load without safe loader"),
            (r"\.readFile\s*\([^)]*\+", "Path traversal possible"),
        ]

        for fragment in fragments:
            for pattern, desc in critical_flags:
                if re.search(pattern, fragment.content, re.IGNORECASE):
                    self.add_finding(
                        description=f"critical SECURITY ISSUE: {desc}",
                        severity="critical",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="IMMEDIATE FIX REQUIRED - Never use these patterns with user input",
                    )

        # Check for complete absence of validation
        validation_anywhere = any(
            re.search(r"valid|sanitiz|escape|encode", f.content, re.IGNORECASE)
            for f in fragments
        )

        user_input_anywhere = any(
            re.search(r"request|req|input|body|params", f.content, re.IGNORECASE)
            for f in fragments
        )

        if user_input_anywhere and not validation_anywhere:
            self.add_finding(
                description="No validation detected despite user input handling",
                severity="critical",
                suggestion="Add comprehensive input validation throughout the application",
            )
