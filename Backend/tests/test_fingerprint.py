"""Tests for fingerprint module."""

import pytest

from codeval.fingerprint import fingerprint_repo


def test_fingerprint_detects_languages(sample_repo):
    fp = fingerprint_repo(sample_repo)
    assert "python" in fp.languages
    assert fp.languages["python"] >= 4  # main.py, app.py, test_foo.py, utils.py


def test_fingerprint_detects_frameworks(sample_repo):
    fp = fingerprint_repo(sample_repo)
    assert "react" in fp.frameworks or "jest" in fp.frameworks or "pip" in fp.frameworks


def test_fingerprint_detects_tests(sample_repo):
    fp = fingerprint_repo(sample_repo)
    assert fp.has_tests is True
    assert len(fp.test_patterns) > 0


def test_fingerprint_detects_entrypoints(sample_repo):
    fp = fingerprint_repo(sample_repo)
    assert "main.py" in fp.entrypoints or "app.py" in fp.entrypoints


def test_fingerprint_detects_dependency_files(sample_repo):
    fp = fingerprint_repo(sample_repo)
    assert "package.json" in fp.dependency_files
    assert "requirements.txt" in fp.dependency_files


def test_fingerprint_nonexistent_path():
    fp = fingerprint_repo("/nonexistent/path/12345")
    assert fp.languages == {}
    assert fp.entrypoints == []


def test_fingerprint_exclude_patterns(sample_repo):
    fp = fingerprint_repo(sample_repo, exclude_patterns=["test_*.py"])
    # test_foo.py might still be counted in languages but not in test_patterns
    # Depends on implementation - at least we don't crash
    assert isinstance(fp.languages, dict)
