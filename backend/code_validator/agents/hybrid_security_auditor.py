"""Hybrid Security Auditor - Combines static analysis with LLM security review."""

import json
from typing import List, Dict, Any

from agents.hybrid_base_agent import HybridBaseAgent, HybridConfig
from agents.security_auditor import SecurityAuditor
from core.models import CodeFragment, AgentResult, AgentType, ValidationContext
from core.llm_client import LLMClient
from prompts import SECURITY_ANALYSIS_PROMPT, SECURITY_CONTEXT_PROMPT


class HybridSecurityAuditor(HybridBaseAgent):
    """
    Hybrid Security Auditor combining static pattern matching with LLM analysis.

    Uses Claude 3.5 Sonnet for deep security analysis due to its superior
    reasoning capabilities and lower false positive rate.
    """

    def __init__(self, hybrid_config: HybridConfig = None):
        # Security always uses LLM due to critical nature
        config = hybrid_config or HybridConfig(
            use_llm=True,
            llm_for_critical_only=False,
            static_threshold=100,  # Always use LLM
            max_llm_calls=5,
            min_confidence=0.75,
        )
        super().__init__(AgentType.SECURITY, config)
        self.static_agent = SecurityAuditor()

    def _static_analysis(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Run static security analysis."""
        self.static_agent.reset()
        return self.static_agent.analyze(fragments, context)

    async def _llm_analysis(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Run LLM security analysis."""

        # Select relevant fragments for security analysis
        security_fragments = self._select_security_context(fragments)
        code_context = self._build_code_context(security_fragments)

        # Build context for the prompt
        context_info = self._build_context_info(context)

        # Create the prompt
        prompt = SECURITY_ANALYSIS_PROMPT.format(
            code=code_context,
            file_path=(
                security_fragments[0].file_path if security_fragments else "unknown"
            ),
            language=context.language or "unknown",
            framework=context.framework or "unknown",
            context=context_info,
        )

        # Call LLM
        response = await self.llm_client.analyze(
            prompt=prompt,
            context={"task": "security_analysis"},
            temperature=0.1,  # low temperature for consistent results
            max_tokens=4000,
            response_format="json",
        )

        # Parse LLM findings
        llm_findings = self._parse_llm_response(response)

        # Calculate LLM score
        score = self._calculate_llm_score(llm_findings)

        # Build examples from LLM suggestions
        examples = self._extract_examples(llm_findings)

        return AgentResult(
            agent_type=self.agent_type,
            score=score,
            gaps=[],  # LLM doesn't typically identify gaps
            findings=llm_findings,
            examples=examples,
            raw_analysis={
                "llm_model": response.model,
                "llm_confidence": response.confidence,
                "llm_usage": response.usage,
                "findings_count": len(llm_findings),
            },
        )

    def _select_security_context(
        self, fragments: List[CodeFragment]
    ) -> List[CodeFragment]:
        """Select fragments most relevant to security analysis."""
        security_keywords = [
            "auth",
            "login",
            "password",
            "token",
            "session",
            "jwt",
            "input",
            "request",
            "query",
            "sql",
            "exec",
            "eval",
            "user",
            "admin",
            "permission",
            "role",
            "access",
            "encrypt",
            "hash",
            "crypto",
            "certificate",
            "file",
            "path",
            "upload",
            "download",
            "api",
            "endpoint",
            "route",
            "handler",
        ]

        # Score each fragment by security relevance
        scored_fragments = []
        for fragment in fragments:
            score = 0
            content_lower = fragment.content.lower()

            # Check for security keywords
            for keyword in security_keywords:
                if keyword in content_lower:
                    score += 1

            # Prioritize entry points
            if fragment.fragment_type in ["function", "method"]:
                score += 2

            scored_fragments.append((score, fragment))

        # Sort by score and select top fragments
        scored_fragments.sort(key=lambda x: -x[0])

        selected = []
        total_chars = 0

        for score, fragment in scored_fragments:
            if score == 0:
                continue  # Skip non-security-related fragments
            if total_chars + len(fragment.content) > self.hybrid_config.context_window:
                break
            selected.append(fragment)
            total_chars += len(fragment.content)

        # If no security-related fragments found, use top functions
        if not selected:
            for score, fragment in scored_fragments[:5]:
                if (
                    total_chars + len(fragment.content)
                    > self.hybrid_config.context_window
                ):
                    break
                selected.append(fragment)
                total_chars += len(fragment.content)

        return selected

    def _build_context_info(self, context: ValidationContext) -> str:
        """Build context information for the LLM prompt."""
        parts = []

        if context.entry_points:
            parts.append(f"Entry points: {', '.join(context.entry_points)}")

        if context.dependencies:
            parts.append(f"Dependencies: {', '.join(context.dependencies[:5])}")

        if context.test_files:
            parts.append(f"Test files: {len(context.test_files)} found")

        return "\n".join(parts) if parts else "No additional context available"

    def _parse_llm_response(self, response: Any) -> List[Dict[str, Any]]:
        """Parse LLM security analysis response."""
        try:
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Extract JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            else:
                json_str = content

            data = json.loads(json_str.strip())
            findings = data.get("findings", [])

            # Normalize and enhance findings
            normalized = []
            for finding in findings:
                normalized_finding = {
                    "severity": finding.get("severity", "medium").lower(),
                    "category": finding.get("category", "GENERAL"),
                    "description": finding.get("description", ""),
                    "suggestion": finding.get("fix", ""),
                    "attack_scenario": finding.get("attack_scenario", ""),
                    "cwe": finding.get("cwe", ""),
                    "line": finding.get("line"),
                    "file": finding.get("file"),
                    "source": "llm",
                    "llm_confidence": finding.get("confidence", 0.8),
                    "llm_model": (
                        response.model if hasattr(response, "model") else "unknown"
                    ),
                }
                normalized.append(normalized_finding)

            return normalized

        except Exception as e:
            print(f"Error parsing LLM security response: {e}")
            return []

    def _calculate_llm_score(self, findings: List[Dict[str, Any]]) -> int:
        """Calculate score based on LLM findings."""
        deductions = {"critical": 25, "high": 15, "medium": 8, "low": 3}

        score = 100
        for finding in findings:
            severity = finding.get("severity", "low")
            score -= deductions.get(severity, 0)

        return max(0, score)

    def _extract_examples(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract code examples from LLM findings."""
        examples = []

        for finding in findings:
            fix = finding.get("suggestion", "")
            if fix and len(fix) > 20:
                examples.append(
                    {
                        "title": f"Fix for: {finding.get('description', 'Issue')[:50]}...",
                        "code": fix,
                        "explanation": finding.get("attack_scenario", ""),
                    }
                )

        return examples
