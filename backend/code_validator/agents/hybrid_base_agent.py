"""Hybrid Base Agent - Combines static analysis with LLM analysis."""

import json
import asyncio
import time
from abc import abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from core.models import CodeFragment, AgentResult, AgentType, ValidationContext
from core.llm_client import LLMClient
from agents.base_agent import BaseAgent
from core.validation_logger import logger, LogLevel, EventType


@dataclass
class HybridConfig:
    """Configuration for hybrid analysis."""

    use_llm: bool = True
    llm_for_critical_only: bool = False  # Only use LLM if static finds issues
    static_threshold: int = 70  # Use LLM if static score below this
    max_llm_calls: int = 5  # Limit LLM calls per agent
    context_window: int = 8000  # Max chars to send to LLM
    min_confidence: float = 0.7  # Minimum LLM confidence to accept finding


class HybridBaseAgent(BaseAgent):
    """Base agent with hybrid static + LLM analysis."""

    def __init__(
        self, agent_type: AgentType, hybrid_config: Optional[HybridConfig] = None
    ):
        super().__init__(agent_type)
        self.hybrid_config = hybrid_config or HybridConfig()
        self.llm_client: Optional[LLMClient] = None
        self.task_type = agent_type.value.lower()

        if self.hybrid_config.use_llm:
            try:
                self.llm_client = LLMClient(task_type=self.task_type)
            except (ValueError, ImportError) as e:
                print(
                    f"Warning: Could not initialize LLM client for {agent_type.value}: {e}"
                )
                self.llm_client = None

    def analyze(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Run hybrid analysis (static + optional LLM)."""

        # Set logging context for this thread
        logger.set_context(self.task_type, self.agent_type.value)

        # Step 1: Always run static analysis
        static_start = time.time()
        static_result = self._static_analysis(fragments, context)
        static_time = int((time.time() - static_start) * 1000)

        # Log static analysis results
        logger.log_event(
            EventType.STATIC_ANALYSIS_COMPLETE,
            LogLevel.INFO,
            "agent",
            f"Static analysis complete for {self.task_type}",
            {
                "agent_name": self.task_type,
                "score": static_result.score,
                "findings_count": len(static_result.findings),
                "gaps_count": len(static_result.gaps),
                "critical_findings": sum(
                    1 for f in static_result.findings if f.get("severity") == "critical"
                ),
                "high_findings": sum(
                    1 for f in static_result.findings if f.get("severity") == "high"
                ),
                "medium_findings": sum(
                    1 for f in static_result.findings if f.get("severity") == "medium"
                ),
                "low_findings": sum(
                    1 for f in static_result.findings if f.get("severity") == "low"
                ),
            },
            execution_time_ms=static_time,
        )

        # Step 2: Decide if LLM analysis is needed
        should_use = self._should_use_llm(static_result)

        # Log LLM decision
        logger.log_event(
            EventType.LLM_DECISION,
            LogLevel.INFO,
            "agent",
            f"LLM decision for {self.task_type}: {'YES' if should_use else 'NO'}",
            {
                "agent_name": self.task_type,
                "should_use_llm": should_use,
                "reasoning": self._get_llm_decision_reasoning(
                    static_result, should_use
                ),
                "llm_client_available": self.llm_client is not None,
                "static_score": static_result.score,
                "threshold": self.hybrid_config.static_threshold,
                "critical_issues_found": any(
                    f.get("severity") == "critical" for f in static_result.findings
                ),
            },
        )

        if not should_use:
            logger.clear_context()
            return static_result

        # Step 3: Run LLM analysis
        try:
            llm_result = asyncio.run(self._llm_analysis(fragments, context))

            # Step 4: Fuse results
            fusion_start = time.time()
            fused_result = self._fuse_results(static_result, llm_result)
            fusion_time = int((time.time() - fusion_start) * 1000)

            # Log result fusion
            logger.log_event(
                EventType.RESULT_FUSION,
                LogLevel.INFO,
                "agent",
                f"Result fusion complete for {self.task_type}",
                {
                    "agent_name": self.task_type,
                    "static_findings": len(static_result.findings),
                    "llm_findings": len(llm_result.findings),
                    "duplicates_removed": len(static_result.findings)
                    + len(llm_result.findings)
                    - len(fused_result.findings),
                    "final_findings": len(fused_result.findings),
                    "fused_score": fused_result.score,
                    "static_score": static_result.score,
                    "llm_score": llm_result.score,
                    "fusion_strategy": "deduplicate_and_prioritize",
                },
                execution_time_ms=fusion_time,
            )

            logger.clear_context()
            return fused_result

        except Exception as e:
            print(f"LLM analysis failed for {self.agent_type.value}: {e}")
            logger.log_error(
                "agent",
                f"LLM analysis failed for {self.task_type}",
                e,
                agent_name=self.task_type,
            )
            # Fall back to static results
            logger.clear_context()
            return static_result

    def _should_use_llm(self, static_result: AgentResult) -> bool:
        """Determine if LLM analysis should be run. Hybrid agents always use both static and LLM when use_llm=True."""
        if not self.llm_client:
            return False
        # Hybrid agents always run LLM when configured (both static + LLM every time)
        if self.hybrid_config.use_llm:
            return True
        if self.hybrid_config.llm_for_critical_only:
            has_critical = any(
                f.get("severity") == "critical" for f in static_result.findings
            )
            return has_critical
        if static_result.score < self.hybrid_config.static_threshold:
            return True
        return False

    def _get_llm_decision_reasoning(
        self, static_result: AgentResult, should_use: bool
    ) -> str:
        """Generate reasoning for LLM decision."""
        reasons = []

        if not self.llm_client:
            return "LLM client not available"

        if not should_use:
            if static_result.score >= self.hybrid_config.static_threshold:
                reasons.append(
                    f"Score above threshold ({static_result.score} >= {self.hybrid_config.static_threshold})"
                )
            if not any(f.get("severity") == "critical" for f in static_result.findings):
                reasons.append("No critical findings")
            if self.task_type not in ["security", "architecture", "semantics"]:
                reasons.append(
                    f"Agent type '{self.task_type}' doesn't require LLM for good scores"
                )
        else:
            if self.hybrid_config.llm_for_critical_only:
                has_critical = any(
                    f.get("severity") == "critical" for f in static_result.findings
                )
                if has_critical:
                    reasons.append("critical findings detected")

            if static_result.score < self.hybrid_config.static_threshold:
                reasons.append(
                    f"Score below threshold ({static_result.score} < {self.hybrid_config.static_threshold})"
                )

            if self.task_type in ["security", "architecture", "semantics"]:
                reasons.append(f"Agent type '{self.task_type}' always uses LLM")

        return (
            " | ".join(reasons)
            if reasons
            else ("Using LLM for enhanced analysis" if should_use else "LLM not needed")
        )

    @abstractmethod
    def _static_analysis(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Run static analysis - implement in subclass."""
        pass

    @abstractmethod
    async def _llm_analysis(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Run LLM analysis - implement in subclass."""
        pass

    def _select_context_for_llm(
        self, fragments: List[CodeFragment]
    ) -> List[CodeFragment]:
        """Select most relevant code fragments for LLM analysis."""
        # Priority: functions/methods > classes > modules
        priority_order = ["function", "method", "class", "module"]

        sorted_fragments = sorted(
            fragments,
            key=lambda f: (
                priority_order.index(f.fragment_type)
                if f.fragment_type in priority_order
                else 99
            ),
        )

        # Select fragments up to context window
        selected = []
        total_chars = 0

        for fragment in sorted_fragments:
            if total_chars + len(fragment.content) > self.hybrid_config.context_window:
                break
            selected.append(fragment)
            total_chars += len(fragment.content)

        # Log context selection
        logger.log_event(
            EventType.LLM_CONTEXT_SELECTION,
            LogLevel.DEBUG,
            "agent",
            f"Context selection for {self.task_type}",
            {
                "agent_name": self.task_type,
                "total_fragments": len(fragments),
                "selected_fragments": len(selected),
                "total_chars": total_chars,
                "context_window_limit": self.hybrid_config.context_window,
                "fragments_by_type": {
                    ftype: sum(1 for f in selected if f.fragment_type == ftype)
                    for ftype in set(f.fragment_type for f in selected)
                },
            },
        )

        return selected

    def _build_code_context(self, fragments: List[CodeFragment]) -> str:
        """Build code context string for LLM prompt."""
        parts = []
        for f in fragments:
            parts.append(f"// File: {f.file_path}:{f.start_line}")
            parts.append(f"// Type: {f.fragment_type}")
            if f.metadata.get("name"):
                parts.append(f"// Name: {f.metadata['name']}")
            parts.append(f.content)
            parts.append("")
        return "\n".join(parts)

    def _build_context_info(self, context: ValidationContext) -> str:
        """Build context information for the LLM prompt. Override in subclass if needed."""
        parts = []
        if context.entry_points:
            parts.append(f"Entry points: {', '.join(context.entry_points)}")
        if context.dependencies:
            parts.append(f"Dependencies: {', '.join(context.dependencies[:5])}")
        if context.test_files:
            parts.append(f"Test files: {len(context.test_files)} found")
        if context.user_story:
            parts.append(f"User story: {context.user_story}")
        return "\n".join(parts) if parts else "No additional context available"

    def _parse_llm_response(self, response: Any) -> List[Dict[str, Any]]:
        """Parse LLM response into findings."""
        try:
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Try to extract JSON
            # Look for JSON block
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            else:
                json_str = content

            data = json.loads(json_str.strip())
            findings = data.get("findings", [])

            # Add metadata and normalize suggestion field for each finding
            for finding in findings:
                finding["source"] = "llm"
                finding["llm_confidence"] = finding.get("confidence", 0.8)
                finding["llm_model"] = (
                    response.model if hasattr(response, "model") else "unknown"
                )
                if "suggestion" not in finding or not finding["suggestion"]:
                    finding["suggestion"] = (
                        finding.get("fix")
                        or finding.get("refactoring")
                        or finding.get("implementation")
                        or finding.get("mitigation")
                        or finding.get("pattern")
                        or finding.get("example")
                        or ""
                    )

            return findings

        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response as JSON: {e}")
            return []
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return []

    def _fuse_results(self, static: AgentResult, llm: AgentResult) -> AgentResult:
        """Fuse static and LLM analysis results."""

        # Deduplicate findings
        deduplicated = []
        seen = set()

        # Process static findings first (more reliable)
        for finding in static.findings:
            key = self._finding_key(finding)
            if key not in seen:
                seen.add(key)
                finding["source"] = "static"
                finding["confidence"] = 1.0
                deduplicated.append(finding)

        # Add LLM findings if not duplicates and confidence is high enough
        for finding in llm.findings:
            key = self._finding_key(finding)
            if key not in seen:
                confidence = finding.get("llm_confidence", 0.8)
                if confidence >= self.hybrid_config.min_confidence:
                    seen.add(key)
                    deduplicated.append(finding)

        # Sort by severity and confidence
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        deduplicated.sort(
            key=lambda f: (
                severity_order.get(f.get("severity", "low"), 4),
                -f.get("confidence", 0),
            )
        )

        # Combine gaps
        all_gaps = static.gaps + llm.gaps

        # Combine examples (prefer LLM examples as they're more contextual)
        all_examples = llm.examples + static.examples

        # Recalculate score
        score = self._calculate_fused_score(static.score, llm.score, deduplicated)

        raw = {
            "static_score": static.score,
            "llm_score": llm.score,
            "static_findings": len(static.findings),
            "llm_findings": len(llm.findings),
            "fused_findings": len(deduplicated),
            "fusion_strategy": "deduplicate_and_prioritize",
        }
        if llm.raw_analysis:
            raw["llm_model"] = llm.raw_analysis.get("llm_model")
            raw["llm_usage"] = llm.raw_analysis.get("llm_usage")
        return AgentResult(
            agent_type=static.agent_type,
            score=score,
            gaps=all_gaps,
            findings=deduplicated,
            examples=all_examples,
            raw_analysis=raw,
        )

    def _calculate_llm_score_from_findings(self, findings: List[Dict[str, Any]]) -> int:
        """Calculate score from LLM findings (deductions by severity)."""
        deductions = {"critical": 25, "high": 15, "medium": 8, "low": 3}
        score = 100
        for finding in findings:
            severity = (finding.get("severity") or "low").lower()
            score -= deductions.get(severity, 0)
        return max(0, score)

    def _extract_examples_from_findings(
        self, findings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract code examples from LLM findings for report."""
        examples = []
        for finding in findings:
            fix = (
                finding.get("suggestion")
                or finding.get("fix")
                or finding.get("refactoring")
                or finding.get("implementation")
                or ""
            )
            if fix and len(str(fix)) > 20:
                examples.append(
                    {
                        "title": f"Fix for: {(finding.get('description') or 'Issue')[:50]}...",
                        "code": str(fix),
                        "explanation": finding.get("impact")
                        or finding.get("consequence")
                        or finding.get("failure_scenario")
                        or "",
                    }
                )
        return examples

    def _finding_key(self, finding: Dict[str, Any]) -> Tuple:
        """Generate a key for deduplication."""
        return (
            finding.get("file"),
            finding.get("line"),
            finding.get("description", "")[:50].lower(),
        )

    def _calculate_fused_score(
        self, static_score: int, llm_score: int, findings: List[Dict]
    ) -> int:
        """Calculate fused score considering both analyses."""
        # Start with static score (more reliable)
        score = static_score

        # Apply penalties for LLM-found critical issues
        llm_critical = sum(
            1
            for f in findings
            if f.get("source") == "llm" and f.get("severity") == "critical"
        )
        score -= llm_critical * 10

        # Boost if both agree on high score
        if static_score >= 80 and llm_score >= 80:
            score = min(100, score + 5)

        return max(0, score)


def create_hybrid_agent(
    agent_class, agent_type: AgentType, hybrid_config: Optional[HybridConfig] = None
):
    """Factory function to create a hybrid agent from a static agent class."""

    class HybridAgent(HybridBaseAgent):
        def __init__(self):
            super().__init__(agent_type, hybrid_config)
            self.static_agent = agent_class()

        def _static_analysis(self, fragments, context):
            """Delegate to original static agent."""
            self.static_agent.reset()
            return self.static_agent.analyze(fragments, context)

        async def _llm_analysis(self, fragments, context):
            """Override in specific hybrid implementations."""
            raise NotImplementedError("Must implement _llm_analysis")

    return HybridAgent
