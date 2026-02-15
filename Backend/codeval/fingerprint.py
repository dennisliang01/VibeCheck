"""Repo fingerprinting: languages, frameworks, tests, entrypoints."""

from __future__ import annotations

import fnmatch
import json
import logging
from pathlib import Path

from codeval.schemas import CodebaseFingerprint

logger = logging.getLogger(__name__)

# Limits
MAX_FILES_SCANNED = 1000
MAX_FILE_SIZE_FINGERPRINT = 1 * 1024 * 1024  # 1MB
TOTAL_READ_CAP = 50 * 1024 * 1024  # 50MB
MAX_LANGUAGES = 10

# Skip these paths
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}

# Language extensions
LANG_EXTENSIONS: dict[str, list[str]] = {
    "python": [".py", ".pyi"],
    "javascript": [".js", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx"],
    "java": [".java"],
    "go": [".go"],
    "rust": [".rs"],
    "ruby": [".rb"],
    "php": [".php"],
    "csharp": [".cs"],
    "kotlin": [".kt"],
}

# Framework detection files
DEPENDENCY_FILES = [
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "pom.xml",
    "go.mod",
    "Cargo.toml",
    "Gemfile",
    "composer.json",
]

# Entrypoint patterns
ENTRYPOINT_PATTERNS = [
    "main.py",
    "__main__.py",
    "index.js",
    "index.ts",
    "app.py",
    "app.js",
    "app.ts",
    "main.go",
    "main.rs",
    "main.java",
    "Main.java",
    "server.py",
    "run.py",
]

# Test patterns
TEST_PATTERNS = [
    "*_test.py",
    "test_*.py",
    "*.test.js",
    "*.test.ts",
    "*.spec.js",
    "*.spec.ts",
    "*Test.java",
    "*_test.go",
]

# Binary magic bytes (first few bytes)
BINARY_SIGNATURES = [
    b"\x89PNG",
    b"\xff\xd8\xff",  # JPEG
    b"GIF8",
    b"PK\x03\x04",  # ZIP
    b"\x7fELF",  # ELF
    b"MZ",  # Windows PE
]


def _is_binary(path: Path) -> bool:
    """Check if file is likely binary."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(32)
        for sig in BINARY_SIGNATURES:
            if chunk.startswith(sig):
                return True
        # Check for null bytes
        if b"\x00" in chunk:
            return True
    except OSError:
        return True
    return False


def _read_safe(path: Path, max_size: int = MAX_FILE_SIZE_FINGERPRINT) -> str | None:
    """Read file safely, return None on decode error."""
    try:
        size = path.stat().st_size
        if size > max_size:
            return None
        with open(path, "r", encoding="utf-8", errors="strict") as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as e:
        logger.debug("Skip %s: %s", path, e)
        return None


def _is_test_file(path: Path) -> bool:
    """Check if path matches test patterns."""
    name = path.name
    parts = path.parts
    if "test" in parts or "tests" in parts:
        return True
    return (
        name.endswith("_test.py")
        or name.startswith("test_")
        or name.endswith(".test.js")
        or name.endswith(".test.ts")
        or name.endswith(".spec.js")
        or name.endswith(".spec.ts")
        or name.endswith("_test.go")
        or "Test" in name and name.endswith(".java")
    )


def _is_entrypoint(path: Path) -> bool:
    """Check if path is an entrypoint."""
    return path.name in ENTRYPOINT_PATTERNS


def _ext_to_lang(ext: str) -> str | None:
    """Map extension to language."""
    for lang, exts in LANG_EXTENSIONS.items():
        if ext in exts:
            return lang
    return None


def fingerprint_repo(
    path: str | Path,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> CodebaseFingerprint:
    """
    Fingerprint a repository: detect languages, frameworks, tests, entrypoints.

    Defensive: skip binary, symlinks, large files. Cap total bytes read.
    """
    root = Path(path).resolve()
    if not root.is_dir():
        return CodebaseFingerprint()

    languages: dict[str, int] = {}
    entrypoints: list[str] = []
    dependency_files: list[str] = []
    test_patterns: list[str] = []
    has_tests = False
    frameworks: list[str] = []
    total_bytes = 0
    files_scanned = 0

    def should_include(p: Path) -> bool:
        rel = p.relative_to(root).as_posix()
        if any(part in p.parts for part in SKIP_DIRS):
            return False
        if exclude_patterns:
            if any(fnmatch.fnmatch(rel, pat) for pat in exclude_patterns):
                return False
        if include_patterns:
            if not any(fnmatch.fnmatch(rel, pat) for pat in include_patterns):
                return False
        return True

    # Walk files
    for entry in root.rglob("*"):
        if files_scanned >= MAX_FILES_SCANNED or total_bytes >= TOTAL_READ_CAP:
            break
        if not entry.is_file():
            continue
        try:
            if entry.is_symlink():
                continue
        except OSError:
            continue

        rel = entry.relative_to(root).as_posix()
        if not should_include(entry):
            continue

        # Dependency files
        if entry.name in DEPENDENCY_FILES:
            dependency_files.append(rel)
            content = _read_safe(entry)
            if content and total_bytes < TOTAL_READ_CAP:
                total_bytes += len(content.encode("utf-8"))
                if entry.name == "package.json":
                    try:
                        data = json.loads(content)
                        deps = data.get("dependencies", {}) or {}
                        deps.update(data.get("devDependencies", {}) or {})
                        for dep in ["react", "vue", "express", "jest", "next"]:
                            if dep in deps:
                                frameworks.append(dep)
                    except json.JSONDecodeError:
                        pass
                elif entry.name == "requirements.txt":
                    frameworks.append("pip")
                elif entry.name == "pyproject.toml":
                    frameworks.append("pyproject")
                elif entry.name == "pom.xml":
                    frameworks.append("maven")
                elif entry.name == "go.mod":
                    frameworks.append("go")
                elif entry.name == "Cargo.toml":
                    frameworks.append("cargo")

        # Skip binary and large files for language scan
        if entry.stat().st_size > MAX_FILE_SIZE_FINGERPRINT:
            continue
        if _is_binary(entry):
            continue

        ext = entry.suffix.lower()
        if ext:
            lang = _ext_to_lang(ext)
            if lang:
                languages[lang] = languages.get(lang, 0) + 1
                files_scanned += 1

        if _is_entrypoint(entry):
            entrypoints.append(rel)

        if _is_test_file(entry):
            has_tests = True
            test_patterns.append(rel)

    # Dedupe frameworks
    frameworks = list(dict.fromkeys(frameworks))

    # Sort languages by count, take top N
    sorted_langs = sorted(languages.items(), key=lambda x: -x[1])[:MAX_LANGUAGES]
    languages = dict(sorted_langs)

    return CodebaseFingerprint(
        languages=languages,
        frameworks=frameworks,
        has_tests=has_tests,
        entrypoints=entrypoints,
        dependency_files=dependency_files,
        test_patterns=test_patterns[:50],
    )
