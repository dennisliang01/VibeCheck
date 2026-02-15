"""API Contract Agent: validates REST endpoints, schemas, and error responses."""

from __future__ import annotations

from codeval.agents.base import BaseAgent
from codeval.llm import complete
from codeval.schemas import (
    AgentReport,
    CodebaseFingerprint,
    FileSnippet,
    HeuristicHit,
)

API_CONTRACT_SYSTEM = """You are an API design and contract validation expert. Analyze the codebase for:
- REST endpoints missing input validation or request schema validation
- Inconsistent error response formats across endpoints (some return JSON errors,
  others return plain text or HTML)
- Missing or incorrect HTTP status codes (always returning 200, using wrong codes)
- No rate limiting or throttling on public endpoints
- Missing CORS configuration for browser-facing APIs
- Endpoints without authentication/authorization checks where needed
- Missing request/response content type headers
- Inconsistent URL naming conventions (mixing camelCase and snake_case)
- Missing pagination on list endpoints that could return large datasets
- No API versioning strategy
- GraphQL: missing input validation, N+1 resolver patterns, overly permissive schemas

Severity guidelines:
- critical: endpoints without auth where required, no input validation on mutations
- high: inconsistent error formats, missing rate limiting, wrong HTTP status codes
- medium: missing CORS config, no pagination on list endpoints
- low: URL naming inconsistencies, missing content-type headers, no versioning

Return JSON only. Verify each finding's evidence.file and evidence.lines exist in the provided snippets.
Ensure recommendations are feasible. Use this exact schema:
{
  "agent": "api_contract",
  "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
  "findings": [
    {
      "id": "unique-id",
      "severity": "critical|high|medium|low",
      "confidence": 0.0-1.0,
      "title": "short title",
      "evidence": {"file": "path", "lines": [start, end] or [line], "snippet": "..."},
      "impact": "description of API contract issue",
      "recommendation": "what to fix",
      "patch_hint": "optional endpoint fix",
      "test_hint": "optional API test suggestion",
      "source": "api_contract"
    }
  ],
  "questions": []
}"""


class ApiContractAgent(BaseAgent):
    """Reviews API contracts: endpoints, validation, error formats, auth."""

    name = "api_contract"

    async def run(
        self,
        fingerprint: CodebaseFingerprint,
        files: list[FileSnippet],
        heuristics: list[HeuristicHit],
        llm_enabled: bool,
    ) -> AgentReport:
        heuristic_findings = self._heuristics_to_findings(heuristics, "api_contract")

        if not llm_enabled:
            return self._merge_reports(heuristic_findings, None, llm_ok=True)

        context = _build_context(fingerprint, files)
        user_prompt = f"""Codebase fingerprint:
{context['fingerprint']}

File snippets ({len(files)} files, focusing on route/controller files):
{context['snippets']}

Analyze for API contract and endpoint issues. Return JSON with findings.
Self-check: confirm each finding's evidence.file and evidence.lines are present in the snippets above."""

        llm_report = await complete(API_CONTRACT_SYSTEM, user_prompt, AgentReport)
        return self._merge_reports(heuristic_findings, llm_report, llm_ok=bool(llm_report))


def _build_context(
    fingerprint: CodebaseFingerprint,
    files: list[FileSnippet],
) -> dict[str, str]:
    fp_str = (
        f"languages={fingerprint.languages}, frameworks={fingerprint.frameworks}, "
        f"has_tests={fingerprint.has_tests}, entrypoints={fingerprint.entrypoints}"
    )
    snippets_str = "\n\n".join(
        f"--- {f.path} (lines {f.line_start}-{f.line_end or '?'}) ---\n{f.content}"
        for f in files[:20]
    )
    return {"fingerprint": fp_str, "snippets": snippets_str}
