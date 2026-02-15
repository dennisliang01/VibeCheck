"""Pytest fixtures."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Create a sample repo with main.py, package.json, test_foo.py."""
    (tmp_path / "main.py").write_text("print('hello')\n")
    (tmp_path / "app.py").write_text("from flask import Flask\napp = Flask(__name__)\n")
    (tmp_path / "test_foo.py").write_text("def test_foo():\n    assert True\n")
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"react": "^18.0.0"}, "devDependencies": {"jest": "^29.0.0"}}'
    )
    (tmp_path / "requirements.txt").write_text("flask>=2.0\n")
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src" / "utils.py").write_text("def util():\n    pass\n")
    return tmp_path


@pytest.fixture
def sample_repo_with_patterns(tmp_path: Path) -> Path:
    """Repo with eval, except:, shell=True for slicer/heuristics tests."""
    (tmp_path / "danger.py").write_text(
        "x = eval(user_input)\n"
        "import subprocess\n"
        "subprocess.run('ls', shell=True)\n"
    )
    (tmp_path / "resilient.py").write_text(
        "try:\n"
        "    do_thing()\n"
        "except:\n"
        "    pass\n"
        "except Exception as e:\n"
        "    log(e)\n"
    )
    return tmp_path
