"""Code parsing and fragmentation module."""

import os
import re
import ast
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from core.models import CodeFragment, ValidationContext


class CodeParser:
    """Parses and fragments code into logical units."""

    SUPPORTED_LANGUAGES = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "jsx",
        ".tsx": "tsx",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".c": "c",
        ".swift": "swift",
        ".kt": "kotlin",
    }

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.fragments: List[CodeFragment] = []
        self.context = ValidationContext(
            language="",
            framework=None,
            user_story=None,
            entry_points=[],
            dependencies=[],
            test_files=[],
            config_files=[],
        )

    def parse_project(self) -> Tuple[List[CodeFragment], ValidationContext]:
        """Parse entire project and return fragments with context."""
        self._detect_language_and_framework()
        self._find_entry_points()
        self._find_dependencies()
        self._find_test_files()
        self._find_config_files()

        for file_path in self._get_source_files():
            self._parse_file(file_path)

        return self.fragments, self.context

    def _get_source_files(self) -> List[Path]:
        """Get all source code files in project."""
        source_files = []
        exclude_patterns = [
            "node_modules",
            "__pycache__",
            ".git",
            "dist",
            "build",
            "venv",
            ".venv",
            "env",
            ".env",
            "coverage",
            ".pytest_cache",
        ]

        for ext in self.SUPPORTED_LANGUAGES.keys():
            for file_path in self.project_path.rglob(f"*{ext}"):
                if not any(pattern in str(file_path) for pattern in exclude_patterns):
                    source_files.append(file_path)

        return source_files

    def _detect_language_and_framework(self):
        """Detect primary language and framework."""
        file_counts = {}

        for ext, lang in self.SUPPORTED_LANGUAGES.items():
            count = len(list(self.project_path.rglob(f"*{ext}")))
            if count > 0:
                file_counts[lang] = file_counts.get(lang, 0) + count

        if file_counts:
            self.context.language = max(file_counts, key=file_counts.get)

        # Detect framework
        self._detect_framework()

    def _detect_framework(self):
        """Detect framework based on config files."""
        framework_indicators = {
            "react": ["package.json", "react"],
            "vue": ["vue.config.js", "package.json"],
            "angular": ["angular.json", "package.json"],
            "express": ["package.json", "express"],
            "fastapi": ["requirements.txt", "fastapi"],
            "django": ["manage.py", "requirements.txt"],
            "flask": ["requirements.txt", "flask"],
            "spring": ["pom.xml", "build.gradle"],
            "laravel": ["composer.json", "artisan"],
            "rails": ["Gemfile", "rails"],
        }

        for framework, indicators in framework_indicators.items():
            if all(
                (
                    any(indicator in str(f) for f in self.project_path.rglob(indicator))
                    if "." in indicator
                    else any(
                        indicator in self._safe_read_file(f)
                        for f in self.project_path.rglob("*")
                        if f.is_file()
                    )
                )
                for indicator in indicators
            ):
                self.context.framework = framework
                break

    def _safe_read_file(self, file_path: Path) -> str:
        """Safely read a file, returning empty string if it can't be read."""
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except (UnicodeDecodeError, IOError, OSError):
            return ""

    def _find_entry_points(self):
        """Find application entry points."""
        common_entry_points = [
            "main.py",
            "app.py",
            "server.js",
            "index.js",
            "main.ts",
            "App.java",
            "main.go",
            "main.rs",
            "Program.cs",
            "src/index.js",
            "src/main.py",
            "src/app.ts",
        ]

        for entry in common_entry_points:
            path = self.project_path / entry
            if path.exists():
                self.context.entry_points.append(
                    str(path.relative_to(self.project_path))
                )

    def _find_dependencies(self):
        """Find dependency files."""
        dep_files = [
            "package.json",
            "requirements.txt",
            "Pipfile",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
            "Gemfile",
            "composer.json",
        ]

        for dep_file in dep_files:
            for path in self.project_path.rglob(dep_file):
                self.context.dependencies.append(
                    str(path.relative_to(self.project_path))
                )

    def _find_test_files(self):
        """Find test files."""
        test_patterns = [
            "*test*",
            "*spec*",
            "tests/**/*",
            "__tests__/**/*",
            "test/**/*",
        ]

        for pattern in test_patterns:
            for path in self.project_path.rglob(pattern):
                if path.is_file() and path.suffix in self.SUPPORTED_LANGUAGES:
                    self.context.test_files.append(
                        str(path.relative_to(self.project_path))
                    )

    def _find_config_files(self):
        """Find configuration files."""
        config_patterns = [
            "*.config.*",
            "*.json",
            "*.yaml",
            "*.yml",
            "*.toml",
            "*.ini",
            ".env*",
            "Dockerfile",
            "docker-compose*",
            "*.tf",
        ]

        for pattern in config_patterns:
            for path in self.project_path.rglob(pattern):
                if path.is_file():
                    self.context.config_files.append(
                        str(path.relative_to(self.project_path))
                    )

    def _parse_file(self, file_path: Path):
        """Parse a single file into fragments."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            language = self.SUPPORTED_LANGUAGES.get(file_path.suffix, "unknown")
            relative_path = str(file_path.relative_to(self.project_path))

            # Add module-level fragment
            self.fragments.append(
                CodeFragment(
                    file_path=relative_path,
                    content=content,
                    fragment_type="module",
                    start_line=1,
                    end_line=len(content.splitlines()),
                    language=language,
                    metadata={"size": len(content), "lines": len(content.splitlines())},
                )
            )

            # Parse language-specific constructs
            if language == "python":
                self._parse_python_file(relative_path, content, language)
            elif language in ["javascript", "typescript", "jsx", "tsx"]:
                self._parse_js_file(relative_path, content, language)
            elif language == "java":
                self._parse_java_file(relative_path, content, language)
            elif language == "go":
                self._parse_go_file(relative_path, content, language)

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

    def _parse_python_file(self, file_path: str, content: str, language: str):
        """Parse Python file into functions and classes."""
        try:
            tree = ast.parse(content)
            lines = content.splitlines()

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.fragments.append(
                        CodeFragment(
                            file_path=file_path,
                            content="\n".join(lines[node.lineno - 1 : node.end_lineno]),
                            fragment_type="function",
                            start_line=node.lineno,
                            end_line=node.end_lineno,
                            language=language,
                            metadata={
                                "name": node.name,
                                "is_async": isinstance(node, ast.AsyncFunctionDef),
                                "args": [arg.arg for arg in node.args.args],
                            },
                        )
                    )
                elif isinstance(node, ast.ClassDef):
                    self.fragments.append(
                        CodeFragment(
                            file_path=file_path,
                            content="\n".join(lines[node.lineno - 1 : node.end_lineno]),
                            fragment_type="class",
                            start_line=node.lineno,
                            end_line=node.end_lineno,
                            language=language,
                            metadata={
                                "name": node.name,
                                "bases": [
                                    base.id if isinstance(base, ast.Name) else str(base)
                                    for base in node.bases
                                ],
                            },
                        )
                    )
        except SyntaxError:
            pass

    def _parse_js_file(self, file_path: str, content: str, language: str):
        """Parse JavaScript/TypeScript file."""
        # Pattern for functions
        func_pattern = r"(export\s+)?(async\s+)?function\s+(\w+)\s*\([^)]*\)\s*\{"
        arrow_pattern = (
            r"(export\s+)?const\s+(\w+)\s*=\s*(async\s+)?\([^)]*\)\s*=>\s*\{"
        )
        class_pattern = r"class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{"

        lines = content.splitlines()

        for match in re.finditer(func_pattern, content):
            start_line = content[: match.start()].count("\n") + 1
            self.fragments.append(
                CodeFragment(
                    file_path=file_path,
                    content=lines[start_line - 1] if start_line <= len(lines) else "",
                    fragment_type="function",
                    start_line=start_line,
                    end_line=start_line,
                    language=language,
                    metadata={"name": match.group(3), "is_async": bool(match.group(2))},
                )
            )

        for match in re.finditer(class_pattern, content):
            start_line = content[: match.start()].count("\n") + 1
            self.fragments.append(
                CodeFragment(
                    file_path=file_path,
                    content=lines[start_line - 1] if start_line <= len(lines) else "",
                    fragment_type="class",
                    start_line=start_line,
                    end_line=start_line,
                    language=language,
                    metadata={"name": match.group(1), "extends": match.group(2)},
                )
            )

    def _parse_java_file(self, file_path: str, content: str, language: str):
        """Parse Java file."""
        method_pattern = (
            r"(public|private|protected)?\s*(static)?\s*(\w+)\s+(\w+)\s*\([^)]*\)\s*\{"
        )
        class_pattern = r"(public\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?"

        lines = content.splitlines()

        for match in re.finditer(method_pattern, content):
            start_line = content[: match.start()].count("\n") + 1
            self.fragments.append(
                CodeFragment(
                    file_path=file_path,
                    content=lines[start_line - 1] if start_line <= len(lines) else "",
                    fragment_type="method",
                    start_line=start_line,
                    end_line=start_line,
                    language=language,
                    metadata={"name": match.group(4), "return_type": match.group(3)},
                )
            )

        for match in re.finditer(class_pattern, content):
            start_line = content[: match.start()].count("\n") + 1
            self.fragments.append(
                CodeFragment(
                    file_path=file_path,
                    content=lines[start_line - 1] if start_line <= len(lines) else "",
                    fragment_type="class",
                    start_line=start_line,
                    end_line=start_line,
                    language=language,
                    metadata={"name": match.group(2), "extends": match.group(3)},
                )
            )

    def _parse_go_file(self, file_path: str, content: str, language: str):
        """Parse Go file."""
        func_pattern = r"func\s+(?:\([^)]*\)\s+)?(\w+)\s*\([^)]*\)"
        struct_pattern = r"type\s+(\w+)\s+struct"

        lines = content.splitlines()

        for match in re.finditer(func_pattern, content):
            start_line = content[: match.start()].count("\n") + 1
            self.fragments.append(
                CodeFragment(
                    file_path=file_path,
                    content=lines[start_line - 1] if start_line <= len(lines) else "",
                    fragment_type="function",
                    start_line=start_line,
                    end_line=start_line,
                    language=language,
                    metadata={"name": match.group(1)},
                )
            )

        for match in re.finditer(struct_pattern, content):
            start_line = content[: match.start()].count("\n") + 1
            self.fragments.append(
                CodeFragment(
                    file_path=file_path,
                    content=lines[start_line - 1] if start_line <= len(lines) else "",
                    fragment_type="struct",
                    start_line=start_line,
                    end_line=start_line,
                    language=language,
                    metadata={"name": match.group(1)},
                )
            )
