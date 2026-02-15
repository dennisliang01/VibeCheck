"""Tests for HTML report generation."""

import pytest

from codeval.html_report import render_html
from codeval.schemas import (
    AgentFinding,
    Evidence,
    FinalReport,
    FindingCluster,
    ReportScores,
)


def _make_report(
    *,
    failed_categories: list[str] | None = None,
    n_findings: int = 2,
) -> FinalReport:
    """Create a test report with controllable parameters."""
    findings = []
    clusters = []
    for i in range(n_findings):
        fid = f"test-{i}"
        findings.append(
            AgentFinding(
                id=fid,
                severity="high" if i % 2 == 0 else "medium",
                confidence=0.9,
                title=f"Test finding {i}",
                evidence=Evidence(file="src/main.py", lines=(i * 10 + 1,), snippet=f"code line {i}"),
                impact=f"Impact of finding {i}",
                recommendation=f"Fix finding {i}",
                source="functional",
            )
        )
        clusters.append(
            FindingCluster(
                cluster_id=f"cluster-{i}",
                primary_finding_id=fid,
                consolidated_title=f"Issue {i}",
                consolidated_severity="high" if i % 2 == 0 else "medium",
                consolidated_impact=f"Impact {i}",
                consolidated_recommendation=f"Recommendation {i}",
                category="functional",
            )
        )

    categories = {cat: 85.0 for cat in [
        "functional", "security", "resilience", "performance",
        "quality", "dependency", "documentation", "architecture",
        "concurrency", "api_contract",
    ]}
    for cat in (failed_categories or []):
        categories[cat] = -1.0

    return FinalReport(
        summary="Test summary",
        scores=ReportScores(categories=categories, overall=85.0),
        findings=findings,
        clusters=clusters,
        all_findings=findings,
        recommended_next_steps=["Fix critical issues first"],
        failed_categories=failed_categories or [],
    )


def test_html_is_valid_html():
    """Basic check: output contains expected HTML structure."""
    report = _make_report()
    html = render_html(report, "TestProject")
    assert "<!DOCTYPE html>" in html
    assert "<html" in html
    assert "</html>" in html
    assert "TestProject" in html


def test_html_contains_scores():
    """HTML should display category scores."""
    report = _make_report()
    html = render_html(report, "MyProject")
    assert "85" in html  # Overall score
    assert "Functional" in html
    assert "Security" in html


def test_html_contains_issues():
    """HTML should display issue cards."""
    report = _make_report(n_findings=3)
    html = render_html(report, "TestProject")
    assert "Issue 0" in html
    assert "Issue 1" in html
    assert "Issue 2" in html
    assert "HIGH" in html


def test_html_na_for_failed_categories():
    """Failed categories should show N/A badge."""
    report = _make_report(failed_categories=["documentation", "concurrency"])
    html = render_html(report, "TestProject")
    assert "N/A" in html
    assert "Warning" in html or "warning" in html
    # Should mention the failed agents
    assert "Documentation" in html
    assert "Concurrency" in html


def test_html_no_warnings_when_all_succeed():
    """No warning banner when no agents failed."""
    report = _make_report(failed_categories=[])
    html = render_html(report, "TestProject")
    # The CSS class definition will exist, but the actual <div class="warning-banner"> should not
    assert '<div class="warning-banner">' not in html


def test_html_empty_report():
    """Empty report should still produce valid HTML."""
    report = FinalReport(summary="Empty")
    html = render_html(report, "EmptyProject")
    assert "<!DOCTYPE html>" in html
    assert "EmptyProject" in html
    assert "No issues found" in html
