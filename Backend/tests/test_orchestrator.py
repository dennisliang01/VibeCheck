"""Tests for orchestrator."""

import pytest

from codeval.orchestrator import run_validation, _compute_scores_from_clusters
from codeval.schemas import FindingCluster, ALL_CATEGORIES


@pytest.mark.asyncio
async def test_run_validation_returns_report(sample_repo):
    report = await run_validation(sample_repo, llm_enabled=False)
    assert report.summary
    assert report.scores.overall >= 0
    assert report.scores.overall <= 100
    assert report.fingerprint is not None
    assert report.recommended_next_steps


@pytest.mark.asyncio
async def test_run_validation_with_findings(sample_repo_with_patterns):
    report = await run_validation(sample_repo_with_patterns, llm_enabled=False)
    # Should have heuristic-based findings (eval, shell=True, except)
    assert len(report.findings) >= 1
    assert report.scores.overall < 100


@pytest.mark.asyncio
async def test_run_validation_has_failed_categories_field(sample_repo):
    """FinalReport should always have failed_categories (empty when all succeed)."""
    report = await run_validation(sample_repo, llm_enabled=False)
    assert isinstance(report.failed_categories, list)
    # LLM disabled → agents don't fail, so failed_categories should be empty
    assert len(report.failed_categories) == 0


def test_compute_scores_no_clusters():
    """No clusters → all categories score 100."""
    scores = _compute_scores_from_clusters([], [])
    assert scores.overall == 100.0
    for cat in ALL_CATEGORIES:
        assert scores.categories[cat] == 100.0


def test_compute_scores_with_failed_categories():
    """Failed categories get -1 and are excluded from overall score."""
    clusters = [
        FindingCluster(
            cluster_id="c1",
            primary_finding_id="f1",
            consolidated_title="test",
            consolidated_severity="high",
            category="security",
        )
    ]
    scores = _compute_scores_from_clusters(clusters, ["documentation", "concurrency"])
    # Failed categories should be -1
    assert scores.categories["documentation"] == -1.0
    assert scores.categories["concurrency"] == -1.0
    # Security should be penalized (not 100)
    assert scores.categories["security"] < 100.0
    # Non-penalized, non-failed categories should still be 100
    assert scores.categories["functional"] == 100.0
    # Overall should be >0 (not dragged down by N/A categories)
    assert scores.overall > 0


def test_compute_scores_all_failed():
    """If all categories fail, overall should still be floor."""
    scores = _compute_scores_from_clusters([], ALL_CATEGORIES.copy())
    assert scores.overall >= 10.0
    for cat in ALL_CATEGORIES:
        assert scores.categories[cat] == -1.0
