"""Static heuristics: pattern detection for grounding LLM findings."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Literal

from codeval.schemas import HeuristicHit

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 100 * 1024  # 100KB
TOTAL_READ_CAP = 50 * 1024 * 1024  # 50MB
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}

# (pattern_id, regex, category)
HEURISTIC_PATTERNS: list[tuple[str, str, Literal["functional", "security", "resilience"]]] = [
    ("TODO_FIXME", r"#\s*(TODO|FIXME)", "functional"),
    ("BARE_EXCEPT", r"\bexcept\s*:", "resilience"),
    ("BROAD_EXCEPT", r"\bexcept\s+(Exception|BaseException)\s*:", "resilience"),
    ("EVAL_EXEC", r"\b(eval|exec)\s*\(", "security"),
    ("SHELL_TRUE", r"shell\s*=\s*True", "security"),
    ("SQL_CONCAT", r"(execute|executemany|raw)\s*\([^)]*%s|format\s*\([^)]*\)\s*\)\s*\)|f['\"].*SELECT|f['\"].*INSERT|f['\"].*UPDATE|f['\"].*DELETE", "security"),
    ("UNSAFE_DESERIALIZE", r"(pickle\.loads|yaml\.unsafe_load|marshal\.loads)\s*\(", "security"),
    ("MISSING_TIMEOUT", r"(requests\.(get|post|put|delete|patch)|socket\.create_connection|urllib\.request\.urlopen)\s*\([^)]*(?!timeout)", "resilience"),
]

# SQL concat: f-strings or % with SQL keywords, or execute(+ var)
SQL_CONCAT_SIMPLE = re.compile(
    r"f['\"].*(?:SELECT|INSERT|UPDATE|DELETE)|"
    r"['\"].*%(?:s|d).*(?:SELECT|INSERT|UPDATE|DELETE)|"
    r"(?:execute|executemany)\s*\([^)]*\+",
    re.IGNORECASE,
)

# Simpler missing timeout - we look for requests/socket without timeout in same line
MISSING_TIMEOUT_PATTERN = re.compile(
    r"(requests\.(?:get|post|put|delete|patch)|socket\.create_connection|urllib\.request\.urlopen)\s*\(",
    re.IGNORECASE,
)


def _read_safe(path: Path, max_size: int = MAX_FILE_SIZE) -> str | None:
    """Read file safely."""
    try:
        size = path.stat().st_size
        if size > max_size:
            return None
        with open(path, "r", encoding="utf-8", errors="strict") as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as e:
        logger.debug("Skip %s: %s", path, e)
        return None


def _is_binary(path: Path) -> bool:
    """Check if file is likely binary."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(32)
        if b"\x00" in chunk and b"\n" not in chunk[:20]:
            return True
        for sig in [b"\x89PNG", b"\xff\xd8\xff", b"GIF8", b"PK\x03\x04", b"\x7fELF", b"MZ"]:
            if chunk.startswith(sig):
                return True
    except OSError:
        return True
    return False


def run_heuristics(
    path: str | Path,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> list[HeuristicHit]:
    """
    Run static heuristics on codebase. Return list of HeuristicHit.
    """
    root = Path(path).resolve()
    if not root.is_dir():
        return []

    import fnmatch

    hits: list[HeuristicHit] = []
    total_bytes = 0

    def should_include(p: Path) -> bool:
        rel = p.relative_to(root).as_posix()
        if any(part in p.parts for part in SKIP_DIRS):
            return False
        if exclude_patterns and any(fnmatch.fnmatch(rel, pat) for pat in exclude_patterns):
            return False
        if include_patterns and not any(fnmatch.fnmatch(rel, pat) for pat in include_patterns):
            return False
        return True

    # Only scan code-like extensions
    CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".php", ".cs"}

    for entry in root.rglob("*"):
        if total_bytes >= TOTAL_READ_CAP:
            break
        if not entry.is_file():
            continue
        try:
            if entry.is_symlink():
                continue
        except OSError:
            continue

        if entry.suffix.lower() not in CODE_EXTS:
            continue
        if not should_include(entry):
            continue
        if _is_binary(entry):
            continue

        content = _read_safe(entry)
        if content is None:
            continue
        total_bytes += len(content.encode("utf-8"))

        rel = entry.relative_to(root).as_posix()

        # TODO_FIXME
        for m in re.finditer(r"#\s*(TODO|FIXME)", content, re.IGNORECASE):
            line_num = content[: m.start()].count("\n") + 1
            line_content = content.split("\n")[line_num - 1].strip()[:200]
            hits.append(
                HeuristicHit(
                    file=rel,
                    line=line_num,
                    pattern_id="TODO_FIXME",
                    snippet=line_content,
                    category="functional",
                )
            )

        # BARE_EXCEPT
        for m in re.finditer(r"\bexcept\s*:", content):
            line_num = content[: m.start()].count("\n") + 1
            line_content = content.split("\n")[line_num - 1].strip()[:200]
            hits.append(
                HeuristicHit(
                    file=rel,
                    line=line_num,
                    pattern_id="BARE_EXCEPT",
                    snippet=line_content,
                    category="resilience",
                )
            )

        # BROAD_EXCEPT (allow "as e" etc.)
        for m in re.finditer(r"\bexcept\s+(Exception|BaseException)(?:\s+as\s+\w+)?\s*:", content):
            line_num = content[: m.start()].count("\n") + 1
            line_content = content.split("\n")[line_num - 1].strip()[:200]
            hits.append(
                HeuristicHit(
                    file=rel,
                    line=line_num,
                    pattern_id="BROAD_EXCEPT",
                    snippet=line_content,
                    category="resilience",
                )
            )

        # EVAL_EXEC
        for m in re.finditer(r"\b(eval|exec)\s*\(", content):
            line_num = content[: m.start()].count("\n") + 1
            line_content = content.split("\n")[line_num - 1].strip()[:200]
            hits.append(
                HeuristicHit(
                    file=rel,
                    line=line_num,
                    pattern_id="EVAL_EXEC",
                    snippet=line_content,
                    category="security",
                )
            )

        # SHELL_TRUE
        for m in re.finditer(r"shell\s*=\s*True", content, re.IGNORECASE):
            line_num = content[: m.start()].count("\n") + 1
            line_content = content.split("\n")[line_num - 1].strip()[:200]
            hits.append(
                HeuristicHit(
                    file=rel,
                    line=line_num,
                    pattern_id="SHELL_TRUE",
                    snippet=line_content,
                    category="security",
                )
            )

        # SQL_CONCAT (simplified)
        for m in SQL_CONCAT_SIMPLE.finditer(content):
            line_num = content[: m.start()].count("\n") + 1
            line_content = content.split("\n")[line_num - 1].strip()[:200]
            hits.append(
                HeuristicHit(
                    file=rel,
                    line=line_num,
                    pattern_id="SQL_CONCAT",
                    snippet=line_content,
                    category="security",
                )
            )

        # UNSAFE_DESERIALIZE
        for m in re.finditer(r"(pickle\.loads|yaml\.unsafe_load|marshal\.loads)\s*\(", content):
            line_num = content[: m.start()].count("\n") + 1
            line_content = content.split("\n")[line_num - 1].strip()[:200]
            hits.append(
                HeuristicHit(
                    file=rel,
                    line=line_num,
                    pattern_id="UNSAFE_DESERIALIZE",
                    snippet=line_content,
                    category="security",
                )
            )

        # MISSING_TIMEOUT - check if timeout is in the same line
        for m in MISSING_TIMEOUT_PATTERN.finditer(content):
            line_num = content[: m.start()].count("\n") + 1
            lines = content.split("\n")
            line_content = lines[line_num - 1].strip()
            if "timeout" not in line_content.lower():
                hits.append(
                    HeuristicHit(
                        file=rel,
                        line=line_num,
                        pattern_id="MISSING_TIMEOUT",
                        snippet=line_content[:200],
                        category="resilience",
                    )
                )

    return hits
