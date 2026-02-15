"""Tests for heuristics module."""

import pytest

from codeval.heuristics import run_heuristics


def test_heuristics_detect_eval(sample_repo_with_patterns):
    hits = run_heuristics(sample_repo_with_patterns)
    eval_hits = [h for h in hits if h.pattern_id == "EVAL_EXEC"]
    assert len(eval_hits) >= 1
    assert any("danger" in h.file for h in eval_hits)


def test_heuristics_detect_shell_true(sample_repo_with_patterns):
    hits = run_heuristics(sample_repo_with_patterns)
    shell_hits = [h for h in hits if h.pattern_id == "SHELL_TRUE"]
    assert len(shell_hits) >= 1


def test_heuristics_detect_bare_except(sample_repo_with_patterns):
    hits = run_heuristics(sample_repo_with_patterns)
    bare_hits = [h for h in hits if h.pattern_id == "BARE_EXCEPT"]
    assert len(bare_hits) >= 1


def test_heuristics_detect_broad_except(sample_repo_with_patterns):
    hits = run_heuristics(sample_repo_with_patterns)
    broad_hits = [h for h in hits if h.pattern_id == "BROAD_EXCEPT"]
    assert len(broad_hits) >= 1


def test_heuristics_empty_repo(tmp_path):
    hits = run_heuristics(tmp_path)
    assert hits == []
