"""Coordinator Agent - Entry point that orchestrates all specialized agents."""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from pathlib import Path

from core.models import (
    CodeFragment,
    ValidationContext,
    AgentResult,
    ValidationReport,
    Verdict,
    Recommendation,
    Severity,
)
from core.code_parser import CodeParser
from core.validation_logger import logger, LogLevel, EventType
from agents.hybrid_functional_validator import HybridFunctionalValidator
from agents.hybrid_logic_inspector import HybridLogicInspector
from agents.hybrid_structural_architect import HybridStructuralArchitect
from agents.hybrid_technical_debt_hunter import HybridTechnicalDebtHunter
from agents.hybrid_performance_expert import HybridPerformanceExpert
from agents.hybrid_security_auditor import HybridSecurityAuditor
from agents.hybrid_observability_debug import HybridObservabilityDebug
from agents.hybrid_resilience_manager import HybridResilienceManager
from agents.hybrid_semantics_expert import HybridSemanticsExpert
from agents.hybrid_deployment_expert import HybridDeploymentExpert


class CoordinatorAgent:
    """Coordinates all specialized agents for code validation."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.agents = {
            "functional": HybridFunctionalValidator(),
            "logic": HybridLogicInspector(),
            "architecture": HybridStructuralArchitect(),
            "technical_debt": HybridTechnicalDebtHunter(),
            "performance": HybridPerformanceExpert(),
            "security": HybridSecurityAuditor(),
            "observability": HybridObservabilityDebug(),
            "resilience": HybridResilienceManager(),
            "semantics": HybridSemanticsExpert(),
            "deployment": HybridDeploymentExpert(),
        }

    def validate(
        self, project_path: str, user_story: Optional[str] = None
    ) -> ValidationReport:
        """Run complete validation on a project.

        Args:
            project_path: Path to the project directory
            user_story: Optional user story for context

        Returns:
            Complete validation report
        """
        start_time = time.time()

        # Step 1: Parse and fragment code
        parse_start = time.time()
        parser = CodeParser(project_path)
        fragments, context = parser.parse_project()
        parse_time = int((time.time() - parse_start) * 1000)

        # Log project parsing
        logger.log_event(
            EventType.PROJECT_PARSING,
            LogLevel.INFO,
            "coordinator",
            "Project parsing complete",
            {
                "project_path": project_path,
                "language": context.language,
                "framework": context.framework,
                "files_found": len(set(f.file_path for f in fragments)),
                "fragments_created": len(fragments),
                "entry_points": context.entry_points,
                "test_files_count": len(context.test_files),
                "parsing_time_ms": parse_time,
            },
        )

        if user_story:
            context.user_story = user_story

        # Step 2: Determine which agents are needed
        agents_to_run = self._select_agents(fragments, context)

        # Log agent orchestration start
        logger.log_event(
            EventType.AGENT_ORCHESTRATION_START,
            LogLevel.INFO,
            "coordinator",
            "Starting agent orchestration",
            {
                "agents_selected": agents_to_run,
                "max_workers": self.max_workers,
                "total_fragments": len(fragments),
            },
        )

        # Step 3: Run agents in parallel
        agent_results = self._run_agents_parallel(fragments, context, agents_to_run)

        # Step 4: Cross-agent analysis (agents can question each other)
        cross_start = time.time()
        self._cross_agent_analysis(agent_results, fragments)
        cross_time = int((time.time() - cross_start) * 1000)

        logger.log_event(
            EventType.CROSS_AGENT_ANALYSIS,
            LogLevel.INFO,
            "coordinator",
            "Cross-agent analysis complete",
            {"execution_time_ms": cross_time},
        )

        # Step 5: Aggregate results and produce verdict
        agg_start = time.time()
        report = self._aggregate_results(agent_results, context)
        agg_time = int((time.time() - agg_start) * 1000)

        total_time = int((time.time() - start_time) * 1000)

        # Log result aggregation
        logger.log_event(
            EventType.RESULT_AGGREGATION,
            LogLevel.INFO,
            "coordinator",
            "Result aggregation complete",
            {
                "detailed_scores": report.detailed_scores,
                "global_score": report.global_score,
                "blocking_critiques_count": len(report.blocking_critiques),
                "recommendations_count": len(report.recommendations),
                "verdict": report.verdict.value,
                "aggregation_time_ms": agg_time,
                "total_validation_time_ms": total_time,
            },
        )

        return report

    def _select_agents(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> List[str]:
        """Select which agents are relevant for this codebase."""
        # All agents run by default, but we could filter based on:
        # - Language/framework
        # - Presence of certain file types
        # - Code complexity
        return list(self.agents.keys())

    def _run_agents_parallel(
        self,
        fragments: List[CodeFragment],
        context: ValidationContext,
        agent_names: List[str],
    ) -> Dict[str, AgentResult]:
        """Run selected agents in parallel."""
        results = {}

        def run_agent(name: str) -> tuple:
            agent_start = time.time()
            agent = self.agents[name]

            # Log agent execution start
            logger.log_event(
                EventType.AGENT_EXECUTION_START,
                LogLevel.INFO,
                "coordinator",
                f"Agent {name} starting",
                {
                    "agent_name": name,
                    "agent_type": agent.agent_type.value,
                    "fragments_count": len(fragments),
                },
            )

            try:
                result = agent.analyze(fragments, context)

                agent_time = int((time.time() - agent_start) * 1000)

                # Log agent execution complete
                logger.log_event(
                    EventType.AGENT_EXECUTION_COMPLETE,
                    LogLevel.INFO,
                    "coordinator",
                    f"Agent {name} complete",
                    {
                        "agent_name": name,
                        "final_score": result.score,
                        "findings_count": len(result.findings),
                        "gaps_count": len(result.gaps),
                        "examples_count": len(result.examples),
                        "used_llm": result.raw_analysis.get("llm_score") is not None,
                        "llm_model": result.raw_analysis.get("llm_model"),
                        "total_execution_time_ms": agent_time,
                    },
                )

                return name, result

            except Exception as e:
                # Log error
                logger.log_error(
                    "coordinator", f"Agent {name} failed", e, agent_name=name
                )

                # Return a failed result
                return name, AgentResult(
                    agent_type=agent.agent_type,
                    score=0,
                    gaps=[
                        {"description": f"Agent failed: {str(e)}", "impact": "critical"}
                    ],
                    findings=[],
                    examples=[],
                )

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(run_agent, name): name for name in agent_names}

            for future in as_completed(futures):
                name, result = future.result()
                results[name] = result

        return results

    def _cross_agent_analysis(
        self, results: Dict[str, AgentResult], fragments: List[CodeFragment]
    ):
        """Allow agents to cross-question each other."""
        # Example cross-checks:

        # Security asks Logic to verify auth flows
        security_result = results.get("security")
        logic_result = results.get("logic")

        if security_result and logic_result:
            # If security found auth issues, logic should verify the flow
            auth_findings = [
                f
                for f in security_result.findings
                if "auth" in f.get("description", "").lower()
            ]
            if auth_findings:
                logic_result.findings.append(
                    {
                        "description": "Cross-check: Verify authentication flow logic",
                        "severity": "medium",
                        "suggestion": "Ensure auth checks are in the correct order",
                    }
                )

        # Performance asks Architecture about caching strategy
        perf_result = results.get("performance")
        arch_result = results.get("architecture")

        if perf_result and arch_result:
            cache_findings = [
                f
                for f in perf_result.findings
                if "cache" in f.get("description", "").lower()
            ]
            if cache_findings:
                arch_result.findings.append(
                    {
                        "description": "Cross-check: Caching layer placement",
                        "severity": "medium",
                        "suggestion": "Ensure cache is at the right architectural boundary",
                    }
                )

        # Resilience asks Observability about error tracking
        res_result = results.get("resilience")
        obs_result = results.get("observability")

        if res_result and obs_result:
            error_findings = [
                f
                for f in res_result.findings
                if "error" in f.get("description", "").lower()
            ]
            if error_findings:
                obs_result.findings.append(
                    {
                        "description": "Cross-check: Ensure error tracking is observable",
                        "severity": "medium",
                        "suggestion": "Add error metrics and structured error logging",
                    }
                )

    def _aggregate_results(
        self, results: Dict[str, AgentResult], context: ValidationContext
    ) -> ValidationReport:
        """Aggregate all agent results into final report."""

        # Calculate detailed scores
        detailed_scores = {name: result.score for name, result in results.items()}

        # Calculate global score (weighted average)
        weights = {
            "security": 1.5,
            "functional": 1.3,
            "logic": 1.2,
            "resilience": 1.2,
            "performance": 1.1,
            "architecture": 1.0,
            "observability": 0.9,
            "technical_debt": 0.8,
            "semantics": 0.7,
            "deployment": 0.6,
        }

        weighted_sum = sum(
            detailed_scores.get(name, 0) * weights.get(name, 1.0)
            for name in detailed_scores
        )
        total_weight = sum(weights.get(name, 1.0) for name in detailed_scores)
        global_score = int(weighted_sum / total_weight) if total_weight > 0 else 0

        # Collect blocking critiques
        blocking_critiques = []
        for name, result in results.items():
            for finding in result.findings:
                if finding.get("severity") == "critical":
                    blocking_critiques.append(
                        f"[{name.upper()}] {finding.get('description')}"
                    )
            for gap in result.gaps:
                if gap.get("impact") == "critical":
                    blocking_critiques.append(
                        f"[{name.upper()}] {gap.get('description')}"
                    )

        # Generate recommendations
        recommendations = self._generate_recommendations(results)

        # Determine verdict
        verdict = self._determine_verdict(global_score, blocking_critiques)

        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            global_score, detailed_scores, blocking_critiques, results
        )

        return ValidationReport(
            verdict=verdict,
            global_score=global_score,
            detailed_scores=detailed_scores,
            blocking_critiques=blocking_critiques,
            recommendations=recommendations,
            executive_summary=executive_summary,
            agent_results=results,
            metadata={
                "language": context.language,
                "framework": context.framework,
                "files_analyzed": len(set(f.file_path for f in [])),
            },
        )

    def _generate_recommendations(
        self, results: Dict[str, AgentResult]
    ) -> List[Recommendation]:
        """Generate prioritized recommendations from all findings."""
        recommendations = []

        severity_priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        for name, result in results.items():
            # Add findings as recommendations
            for finding in result.findings:
                severity = finding.get("severity", "low")
                recommendations.append(
                    Recommendation(
                        severity=Severity(severity),
                        category=name,
                        description=finding.get("description", ""),
                        fix_suggested=finding.get("suggestion", ""),
                        file=finding.get("file"),
                        line=finding.get("line"),
                    )
                )

            # Add gaps as recommendations
            for gap in result.gaps:
                impact = gap.get("impact", "low")
                recommendations.append(
                    Recommendation(
                        severity=Severity(impact),
                        category=name,
                        description=gap.get("description", ""),
                        fix_suggested=gap.get("fix_example", ""),
                    )
                )

        # Sort by severity
        recommendations.sort(key=lambda r: severity_priority.get(r.severity.value, 4))

        return recommendations

    def _determine_verdict(
        self, global_score: int, blocking_critiques: List[str]
    ) -> Verdict:
        """Determine final verdict."""
        # BLOCK if critical security/performance issues
        critical_security = any("security" in c.lower() for c in blocking_critiques)

        if global_score < 60 or critical_security:
            return Verdict.BLOCK
        elif global_score < 85 or blocking_critiques:
            return Verdict.FIX
        else:
            return Verdict.SHIP

    def _generate_executive_summary(
        self,
        global_score: int,
        detailed_scores: Dict[str, int],
        blocking_critiques: List[str],
        results: Dict[str, AgentResult],
    ) -> str:
        """Generate executive summary."""
        parts = []

        # Overall assessment
        if global_score >= 85:
            parts.append(
                "The code is production-ready with minor improvements possible."
            )
        elif global_score >= 60:
            parts.append(
                "The code is generally solid but requires attention to specific areas before shipping."
            )
        else:
            parts.append(
                "The code has significant issues that must be addressed before production deployment."
            )

        # Strong areas
        strong_areas = [name for name, score in detailed_scores.items() if score >= 85]
        if strong_areas:
            parts.append(f"Strong areas: {', '.join(strong_areas[:3])}.")

        # Weak areas
        weak_areas = [
            (name, score) for name, score in detailed_scores.items() if score < 70
        ]
        weak_areas.sort(key=lambda x: x[1])
        if weak_areas:
            weak_names = [name for name, _ in weak_areas[:3]]
            parts.append(f"Areas needing attention: {', '.join(weak_names)}.")

        # critical issues
        if blocking_critiques:
            parts.append(f"Found {len(blocking_critiques)} critical blocking issue(s).")

        # Key metrics
        total_findings = sum(len(r.findings) for r in results.values())
        total_gaps = sum(len(r.gaps) for r in results.values())
        parts.append(f"Total findings: {total_findings}, gaps: {total_gaps}.")

        return " ".join(parts)
