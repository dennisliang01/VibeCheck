"""Concurrency Agent: detects threading, async, and race condition issues."""

from __future__ import annotations

from codeval.agents.base import BaseAgent
from codeval.llm import complete
from codeval.schemas import (
    AgentReport,
    CodebaseFingerprint,
    FileSnippet,
    HeuristicHit,
)

CONCURRENCY_SYSTEM = """You are a concurrency and parallel programming expert. Analyze the codebase for:
- Shared mutable state accessed without locks or synchronization
- Async functions calling synchronous blocking I/O (file reads, time.sleep,
  requests.get inside async def)
- Missing `await` on coroutines (calling async function without await)
- Thread-unsafe singleton patterns (lazy init without lock)
- Race conditions in shared resources (files, databases, caches)
- Fire-and-forget async tasks without error handling
- Deadlock potential (multiple locks acquired in inconsistent order)
- Using threading.Thread without daemon flag or join
- Global mutable state modified from multiple threads/tasks
- Missing asyncio.Lock / threading.Lock around critical sections
- Spawning unlimited threads/tasks without a pool or semaphore

Severity guidelines:
- critical: race conditions on shared data, missing await on coroutines
- high: blocking I/O in async, thread-unsafe singletons, deadlock risk
- medium: fire-and-forget tasks, missing error handling in spawned threads
- low: minor sync issues, using threading where asyncio would be better

Return JSON only. Verify each finding's evidence.file and evidence.lines exist in the provided snippets.
Ensure recommendations are feasible. Use this exact schema:
{
  "agent": "concurrency",
  "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
  "findings": [
    {
      "id": "unique-id",
      "severity": "critical|high|medium|low",
      "confidence": 0.0-1.0,
      "title": "short title",
      "evidence": {"file": "path", "lines": [start, end] or [line], "snippet": "..."},
      "impact": "description of concurrency risk",
      "recommendation": "what to do",
      "patch_hint": "optional fix with synchronization primitives",
      "test_hint": "optional concurrency test suggestion",
      "source": "concurrency"
    }
  ],
  "questions": []
}"""


class ConcurrencyAgent(BaseAgent):
    """Reviews concurrency: race conditions, async/await, threading safety."""

    name = "concurrency"

    async def run(
        self,
        fingerprint: CodebaseFingerprint,
        files: list[FileSnippet],
        heuristics: list[HeuristicHit],
        llm_enabled: bool,
    ) -> AgentReport:
        heuristic_findings = self._heuristics_to_findings(heuristics, "concurrency")

        if not llm_enabled:
            return self._merge_reports(heuristic_findings, None, llm_ok=True)

        context = _build_context(fingerprint, files)
        user_prompt = f"""Codebase fingerprint:
{context['fingerprint']}

File snippets ({len(files)} files):
{context['snippets']}

Analyze for concurrency and thread-safety issues. Return JSON with findings.
Self-check: confirm each finding's evidence.file and evidence.lines are present in the snippets above."""

        llm_report = await complete(CONCURRENCY_SYSTEM, user_prompt, AgentReport)
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
