"""File slicer: pick relevant files and extract snippets for agent context."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from codeval.schemas import CodebaseFingerprint, FileSnippet, HeuristicHit

MAX_FILE_SIZE = 100 * 1024  # 100KB
TOTAL_READ_CAP = 50 * 1024 * 1024  # 50MB
SNIPPET_CONTEXT_LINES = 5
SNIPPET_MAX_CHARS = 200
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}

# ── Patterns for relevance scoring ───────────────────────────────────

SECURITY_PATTERNS = [
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"shell\s*=\s*True",
    r"pickle\.loads",
    r"yaml\.unsafe_load",
    r"subprocess\.(call|run|Popen)",
    r"(execute|executemany)\s*\(",
    r"input\s*\(",
    r"raw_input\s*\(",
    r"auth|password|secret|token",
]
ERROR_HANDLING_PATTERNS = [
    r"\btry\s*:",
    r"\bexcept\s",
    r"\bfinally\s*:",
    r"raise\s",
]
PERFORMANCE_PATTERNS = [
    r"\.query\s*\(",
    r"\.execute\s*\(",
    r"for\s+\w+\s+in\s+",         # loops
    r"\.find\(|\.filter\(",
    r"requests\.(get|post|put)",
    r"urllib\.",
    r"fetch\(",
    r"\.all\(\)",                   # ORM: Model.objects.all()
    r"deepcopy",
    r"time\.sleep",
]
CONCURRENCY_PATTERNS = [
    r"\bthreading\b",
    r"\basyncio\b",
    r"\bmultiprocessing\b",
    r"concurrent\.futures",
    r"\bawait\s",
    r"async\s+def\b",
    r"\bLock\s*\(",
    r"\bSemaphore\s*\(",
    r"Thread\s*\(",
]
API_ROUTE_PATTERNS = [
    r"@app\.(route|get|post|put|delete|patch)",
    r"@router\.(get|post|put|delete|patch)",
    r"@api_view",
    r"@blueprint\.",
    r"app\.(use|get|post|put|delete)\s*\(",   # Express.js
    r"router\.(get|post|put|delete)\s*\(",
    r"@(Get|Post|Put|Delete|Patch|Controller)\(",   # NestJS/Spring
    r"@RequestMapping",
]
ARCHITECTURE_PATTERNS = [
    r"^import\s",
    r"^from\s+\S+\s+import\s",
    r"require\s*\(",
]

SECURITY_RE = re.compile("|".join(f"({p})" for p in SECURITY_PATTERNS), re.IGNORECASE)
ERROR_RE = re.compile("|".join(f"({p})" for p in ERROR_HANDLING_PATTERNS))
PERFORMANCE_RE = re.compile("|".join(f"({p})" for p in PERFORMANCE_PATTERNS), re.IGNORECASE)
CONCURRENCY_RE = re.compile("|".join(f"({p})" for p in CONCURRENCY_PATTERNS))
API_ROUTE_RE = re.compile("|".join(f"({p})" for p in API_ROUTE_PATTERNS), re.IGNORECASE)
ARCHITECTURE_RE = re.compile("|".join(f"({p})" for p in ARCHITECTURE_PATTERNS), re.MULTILINE)

# Dependency manifest filenames
DEPENDENCY_FILES = {
    "package.json", "requirements.txt", "Pipfile", "setup.py", "setup.cfg",
    "pyproject.toml", "go.mod", "Cargo.toml", "Gemfile", "composer.json",
    "pom.xml", "build.gradle",
}


def _read_safe(path: Path, max_size: int = MAX_FILE_SIZE) -> str | None:
    """Read file safely."""
    try:
        size = path.stat().st_size
        if size > max_size:
            return None
        with open(path, "r", encoding="utf-8", errors="strict") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
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


def _extract_snippet(content: str, line_num: int, max_chars: int = SNIPPET_MAX_CHARS) -> str:
    """Extract ±N lines around line_num, truncate to max_chars."""
    lines = content.split("\n")
    start = max(0, line_num - 1 - SNIPPET_CONTEXT_LINES)
    end = min(len(lines), line_num + SNIPPET_CONTEXT_LINES)
    snippet = "\n".join(lines[start:end])
    if len(snippet) > max_chars:
        snippet = snippet[: max_chars - 3] + "..."
    return snippet


def _score_file(
    path: Path,
    rel: str,
    content: str,
    fingerprint: CodebaseFingerprint,
    agent_type: str,
) -> float:
    """Score file relevance for given agent type."""
    score = 0.0
    entrypoints = {e.split("/")[-1] for e in fingerprint.entrypoints}
    test_patterns = set(fingerprint.test_patterns)

    # Entrypoints
    if path.name in entrypoints or rel in fingerprint.entrypoints:
        score += 2.0

    # Tests
    if "test" in path.parts or path.name.startswith("test_") or path.name.endswith("_test.py"):
        score += 2.0
    if any(t in rel for t in test_patterns):
        score += 1.5

    # Agent-specific scoring
    if agent_type == "functional":
        if path.name in entrypoints or rel in fingerprint.entrypoints:
            score += 1.0
        if "test" in path.parts:
            score += 1.0
    elif agent_type == "security":
        if SECURITY_RE.search(content):
            score += 1.5
    elif agent_type == "resilience":
        if ERROR_RE.search(content):
            score += 1.0
    elif agent_type == "performance":
        if PERFORMANCE_RE.search(content):
            score += 1.5
        # Boost larger files (more likely to have perf issues)
        if len(content) > 5000:
            score += 0.5
    elif agent_type == "quality":
        # Boost largest files (most likely to have quality issues)
        lines = content.count("\n")
        if lines > 200:
            score += 2.0
        elif lines > 100:
            score += 1.0
        elif lines > 50:
            score += 0.5
        # Boost files with many function definitions
        func_count = len(re.findall(r"\bdef\s+\w+|function\s+\w+|\w+\s*=\s*(?:async\s+)?(?:\([^)]*\)|)\s*=>", content))
        if func_count > 5:
            score += 1.0
    elif agent_type == "dependency":
        # Only interested in dependency manifest files
        if path.name in DEPENDENCY_FILES:
            score += 10.0  # Very high boost
        else:
            score -= 5.0  # Suppress non-dependency files
    elif agent_type == "documentation":
        # Boost entrypoints, public modules, README-like files
        if path.name in entrypoints or rel in fingerprint.entrypoints:
            score += 2.0
        if path.name.lower() in ("readme.md", "readme.rst", "readme.txt", "readme"):
            score += 5.0
        if path.name in ("__init__.py", "index.js", "index.ts", "mod.rs", "lib.rs"):
            score += 1.5
    elif agent_type == "architecture":
        # Boost files with many imports (coupling indicator)
        import_count = len(ARCHITECTURE_RE.findall(content))
        if import_count > 8:
            score += 2.0
        elif import_count > 4:
            score += 1.0
        # Boost large files (potential god objects)
        if len(content) > 10000:
            score += 1.5
    elif agent_type == "concurrency":
        if CONCURRENCY_RE.search(content):
            score += 2.0
    elif agent_type == "api_contract":
        if API_ROUTE_RE.search(content):
            score += 2.5
        # Boost controller/route/view files by name
        lower_name = path.name.lower()
        if any(kw in lower_name for kw in ("route", "controller", "view", "endpoint", "api", "handler")):
            score += 1.5

    return score


def slice_repo(
    path: str | Path,
    fingerprint: CodebaseFingerprint,
    agent_type: str,
    heuristic_hits: list[HeuristicHit],
    max_files: int = 50,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> list[FileSnippet]:
    """
    Pick top N relevant files for agent, extract snippets around patterns.

    agent_type: one of the 10 agent category names.
    """
    root = Path(path).resolve()
    if not root.is_dir():
        return []

    CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".php", ".cs"}
    # Extra file types for specific agents
    EXTRA_EXTS = {
        "dependency": {".json", ".toml", ".txt", ".cfg", ".lock", ".mod"},
        "documentation": {".md", ".rst", ".txt"},
    }
    allowed_extras = EXTRA_EXTS.get(agent_type, set())

    scored: list[tuple[Path, str, str, float]] = []
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

        ext = entry.suffix.lower()
        if ext not in CODE_EXTS and ext not in allowed_extras:
            # Special: always include dependency manifests for dependency agent
            if agent_type == "dependency" and entry.name in DEPENDENCY_FILES:
                pass  # Allow through
            else:
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
        score = _score_file(entry, rel, content, fingerprint, agent_type)

        # Boost score for files with heuristic hits for this agent's category
        # Map agent types to heuristic categories (new agents have no heuristics)
        heur_cat_map = {
            "functional": "functional",
            "security": "security",
            "resilience": "resilience",
        }
        cat = heur_cat_map.get(agent_type, "")
        if cat:
            for h in heuristic_hits:
                if h.file == rel and h.category == cat:
                    score += 1.0
                    break

        scored.append((entry, rel, content, score))

    # Sort by score desc, take top max_files
    scored.sort(key=lambda x: -x[3])
    top = scored[:max_files]

    snippets: list[FileSnippet] = []
    for entry, rel, content, score in top:
        # Collect line numbers for snippet extraction
        lines_to_extract: set[int] = set()

        for h in heuristic_hits:
            if h.file == rel:
                lines_to_extract.add(h.line)

        for m in SECURITY_RE.finditer(content):
            lines_to_extract.add(content[: m.start()].count("\n") + 1)
        for m in ERROR_RE.finditer(content):
            lines_to_extract.add(content[: m.start()].count("\n") + 1)

        if not lines_to_extract:
            lines_to_extract.add(1)

        # Build combined snippet from relevant line ranges
        lines_arr = content.split("\n")
        combined_lines: set[int] = set()
        for line_num in sorted(lines_to_extract)[:5]:
            start = max(0, line_num - 1 - SNIPPET_CONTEXT_LINES)
            end = min(len(lines_arr), line_num + SNIPPET_CONTEXT_LINES)
            for i in range(start, end):
                combined_lines.add(i)

        sorted_lines = sorted(combined_lines)
        if sorted_lines:
            start_idx = sorted_lines[0]
            end_idx = sorted_lines[-1]
            snip_content = "\n".join(lines_arr[start_idx : end_idx + 1])
            if len(snip_content) > 1500:
                snip_content = snip_content[:1500] + "\n..."
            snippets.append(
                FileSnippet(
                    path=rel,
                    content=snip_content,
                    relevance_score=score,
                    line_start=start_idx + 1,
                    line_end=end_idx + 1,
                )
            )

    return snippets[:max_files]
