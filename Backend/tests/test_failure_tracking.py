"""Tests for agent failure tracking and graceful degradation."""

import pytest

from codeval.schemas import AgentReport, AgentFinding, Evidence, SeveritySummary
from codeval.agents.base import BaseAgent


class DummyAgent(BaseAgent):
    """Test agent for unit testing _merge_reports."""

    name = "test_agent"

    async def run(self, fingerprint, files, heuristics, llm_enabled):
        return AgentReport(agent=self.name)


class TestMergeReports:
    def test_merge_reports_llm_ok_true(self):
        agent = DummyAgent()
        findings = [
            AgentFinding(
                id="h1",
                severity="medium",
                confidence=0.9,
                title="Test",
                evidence=Evidence(file="test.py", lines=(1,)),
                source="test_agent",
            )
        ]
        report = agent._merge_reports(findings, None, llm_ok=True)
        assert report.analyzed is True
        assert len(report.findings) == 1

    def test_merge_reports_llm_ok_false(self):
        agent = DummyAgent()
        findings = [
            AgentFinding(
                id="h1",
                severity="low",
                confidence=0.9,
                title="Heuristic",
                evidence=Evidence(file="test.py", lines=(1,)),
                source="test_agent",
            )
        ]
        report = agent._merge_reports(findings, None, llm_ok=False)
        assert report.analyzed is False
        # Heuristic findings should still be present
        assert len(report.findings) == 1

    def test_merge_reports_with_llm_findings(self):
        agent = DummyAgent()
        heuristic = AgentFinding(
            id="h1",
            severity="low",
            confidence=0.9,
            title="Heuristic",
            evidence=Evidence(file="test.py", lines=(1,)),
            source="test_agent",
        )
        llm_finding = AgentFinding(
            id="llm1",
            severity="high",
            confidence=0.8,
            title="LLM Finding",
            evidence=Evidence(file="test.py", lines=(10,)),
            source="",
        )
        llm_report = AgentReport(
            agent="test_agent",
            findings=[llm_finding],
        )
        report = agent._merge_reports([heuristic], llm_report, llm_ok=True)
        assert report.analyzed is True
        assert len(report.findings) == 2
        # LLM finding should have source set to agent name
        assert report.findings[1].source == "test_agent"


class TestAgentReportSchema:
    def test_analyzed_defaults_true(self):
        report = AgentReport(agent="test")
        assert report.analyzed is True

    def test_analyzed_can_be_false(self):
        report = AgentReport(agent="test", analyzed=False)
        assert report.analyzed is False
