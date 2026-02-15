"""Tests for slicer module."""

import pytest

from codeval.fingerprint import fingerprint_repo
from codeval.heuristics import run_heuristics
from codeval.schemas import CodebaseFingerprint
from codeval.slicer import slice_repo


def test_slicer_returns_files(sample_repo_with_patterns):
    fp = fingerprint_repo(sample_repo_with_patterns)
    heuristics = run_heuristics(sample_repo_with_patterns)
    snippets = slice_repo(
        sample_repo_with_patterns,
        fp,
        "security",
        heuristics,
        max_files=10,
    )
    assert len(snippets) > 0
    assert any("danger" in s.path for s in snippets)


def test_slicer_security_prioritizes_dangerous_files(sample_repo_with_patterns):
    fp = fingerprint_repo(sample_repo_with_patterns)
    heuristics = run_heuristics(sample_repo_with_patterns)
    snippets = slice_repo(
        sample_repo_with_patterns,
        fp,
        "security",
        heuristics,
        max_files=10,
    )
    # danger.py has eval, shell=True - should be included
    paths = [s.path for s in snippets]
    assert any("danger" in p for p in paths)


def test_slicer_resilience_prioritizes_error_handling(sample_repo_with_patterns):
    fp = fingerprint_repo(sample_repo_with_patterns)
    heuristics = run_heuristics(sample_repo_with_patterns)
    snippets = slice_repo(
        sample_repo_with_patterns,
        fp,
        "resilience",
        heuristics,
        max_files=10,
    )
    assert any("resilient" in s.path for s in snippets)


def test_slicer_respects_max_files(sample_repo):
    fp = fingerprint_repo(sample_repo)
    heuristics = run_heuristics(sample_repo)
    snippets = slice_repo(
        sample_repo,
        fp,
        "functional",
        heuristics,
        max_files=2,
    )
    assert len(snippets) <= 2


def test_slicer_empty_repo(tmp_path):
    fp = CodebaseFingerprint()
    snippets = slice_repo(tmp_path, fp, "functional", [], max_files=10)
    assert snippets == []
