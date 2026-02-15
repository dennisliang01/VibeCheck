"""Hybrid Deployment Expert - Static analysis + LLM (GPT-4o Mini)."""

from typing import List
from agents.hybrid_base_agent import HybridBaseAgent, HybridConfig
from agents.deployment_expert import DeploymentExpert
from core.models import CodeFragment, AgentResult, AgentType, ValidationContext
from prompts import DEPLOYMENT_PROMPT


class HybridDeploymentExpert(HybridBaseAgent):
    """Hybrid Deployment Expert. Uses GPT-4o Mini for deployment checks."""

    def __init__(self, hybrid_config: HybridConfig = None):
        config = hybrid_config or HybridConfig(
            use_llm=True,
            llm_for_critical_only=False,
            static_threshold=100,
            max_llm_calls=5,
            min_confidence=0.75,
        )
        super().__init__(AgentType.DEPLOYMENT, config)
        self.static_agent = DeploymentExpert()

    def _static_analysis(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        self.static_agent.reset()
        return self.static_agent.analyze(fragments, context)

    async def _llm_analysis(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        selected = self._select_context_for_llm(fragments)
        if not selected:
            return AgentResult(
                agent_type=self.agent_type,
                score=100,
                gaps=[],
                findings=[],
                examples=[],
                raw_analysis={},
            )
        code_context = self._build_code_context(selected)
        context_info = self._build_context_info(context)
        file_path = selected[0].file_path if selected else "unknown"
        prompt = DEPLOYMENT_PROMPT.format(
            code=code_context,
            file_path=file_path,
            language=context.language or "unknown",
            framework=context.framework or "unknown",
            context=context_info,
        )
        response = await self.llm_client.analyze(
            prompt=prompt,
            context={"task": "deployment_analysis"},
            temperature=0.1,
            max_tokens=4000,
            response_format="json",
        )
        llm_findings = self._parse_llm_response(response)
        score = self._calculate_llm_score_from_findings(llm_findings)
        examples = self._extract_examples_from_findings(llm_findings)
        return AgentResult(
            agent_type=self.agent_type,
            score=score,
            gaps=[],
            findings=llm_findings,
            examples=examples,
            raw_analysis={
                "llm_model": response.model,
                "llm_confidence": response.confidence,
                "llm_usage": response.usage,
                "findings_count": len(llm_findings),
            },
        )
