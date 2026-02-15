"""OSV.dev API helper: batch-query packages for known vulnerabilities."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

OSV_API_URL = "https://api.osv.dev/v1/query"
OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"

# Ecosystem mapping
ECOSYSTEM_MAP = {
    "package.json": "npm",
    "requirements.txt": "PyPI",
    "Pipfile": "PyPI",
    "setup.py": "PyPI",
    "setup.cfg": "PyPI",
    "pyproject.toml": "PyPI",
    "go.mod": "Go",
    "Cargo.toml": "crates.io",
    "Gemfile": "RubyGems",
    "composer.json": "Packagist",
    "pom.xml": "Maven",
    "build.gradle": "Maven",
}


@dataclass
class PackageInfo:
    """A parsed dependency with name, version, and ecosystem."""

    name: str
    version: str
    ecosystem: str
    source_file: str


@dataclass
class VulnResult:
    """A known vulnerability found for a package."""

    package_name: str
    package_version: str
    ecosystem: str
    vuln_id: str
    summary: str
    severity: str = "medium"
    aliases: list[str] = field(default_factory=list)
    source_file: str = ""


def parse_dependencies(root: Path, dep_files: list[str]) -> list[PackageInfo]:
    """Parse dependency files and extract package names + versions."""
    packages: list[PackageInfo] = []

    for dep_file in dep_files:
        full_path = root / dep_file
        if not full_path.exists():
            continue

        filename = Path(dep_file).name
        ecosystem = ECOSYSTEM_MAP.get(filename, "")
        if not ecosystem:
            continue

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if filename == "package.json":
            packages.extend(_parse_package_json(content, dep_file))
        elif filename == "requirements.txt":
            packages.extend(_parse_requirements_txt(content, dep_file))
        elif filename == "Pipfile":
            packages.extend(_parse_pipfile(content, dep_file))
        elif filename == "go.mod":
            packages.extend(_parse_go_mod(content, dep_file))
        elif filename == "Cargo.toml":
            packages.extend(_parse_cargo_toml(content, dep_file))
        elif filename in ("pyproject.toml", "setup.cfg"):
            packages.extend(_parse_requirements_txt(content, dep_file))

    return packages


def _parse_package_json(content: str, source: str) -> list[PackageInfo]:
    """Parse package.json dependencies."""
    pkgs: list[PackageInfo] = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return pkgs

    for section in ("dependencies", "devDependencies", "peerDependencies"):
        deps = data.get(section, {})
        if isinstance(deps, dict):
            for name, version in deps.items():
                # Strip version prefixes: ^, ~, >=, etc.
                clean = re.sub(r"^[\^~>=<]*", "", str(version)).strip()
                if clean and clean != "*":
                    pkgs.append(PackageInfo(name=name, version=clean, ecosystem="npm", source_file=source))
    return pkgs


def _parse_requirements_txt(content: str, source: str) -> list[PackageInfo]:
    """Parse requirements.txt or similar pip format."""
    pkgs: list[PackageInfo] = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Match: package==1.0, package>=1.0, package~=1.0
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*[=~><!]+\s*([0-9][A-Za-z0-9._-]*)", line)
        if m:
            pkgs.append(PackageInfo(name=m.group(1), version=m.group(2), ecosystem="PyPI", source_file=source))
    return pkgs


def _parse_pipfile(content: str, source: str) -> list[PackageInfo]:
    """Parse Pipfile (simplified TOML-like)."""
    pkgs: list[PackageInfo] = []
    in_packages = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped in ("[packages]", "[dev-packages]"):
            in_packages = True
            continue
        if stripped.startswith("["):
            in_packages = False
            continue
        if in_packages and "=" in stripped:
            name, _, ver = stripped.partition("=")
            name = name.strip().strip('"')
            ver = ver.strip().strip('"').strip("'").lstrip("=~>< ")
            if name and ver and ver != "*":
                pkgs.append(PackageInfo(name=name, version=ver, ecosystem="PyPI", source_file=source))
    return pkgs


def _parse_go_mod(content: str, source: str) -> list[PackageInfo]:
    """Parse go.mod require block."""
    pkgs: list[PackageInfo] = []
    in_require = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_require = True
            continue
        if in_require and stripped == ")":
            in_require = False
            continue
        if in_require:
            parts = stripped.split()
            if len(parts) >= 2:
                pkgs.append(PackageInfo(name=parts[0], version=parts[1].lstrip("v"), ecosystem="Go", source_file=source))
    return pkgs


def _parse_cargo_toml(content: str, source: str) -> list[PackageInfo]:
    """Parse Cargo.toml dependencies (simplified)."""
    pkgs: list[PackageInfo] = []
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped in ("[dependencies]", "[dev-dependencies]", "[build-dependencies]"):
            in_deps = True
            continue
        if stripped.startswith("["):
            in_deps = False
            continue
        if in_deps and "=" in stripped:
            name, _, ver = stripped.partition("=")
            name = name.strip()
            ver = ver.strip().strip('"').strip("'")
            # Handle inline table: { version = "1.0", features = [...] }
            if ver.startswith("{"):
                m = re.search(r'version\s*=\s*"([^"]+)"', ver)
                ver = m.group(1) if m else ""
            if name and ver:
                pkgs.append(PackageInfo(name=name, version=ver, ecosystem="crates.io", source_file=source))
    return pkgs


async def query_osv(packages: list[PackageInfo]) -> list[VulnResult]:
    """Query OSV.dev API for known vulnerabilities in batch."""
    if not packages:
        return []

    # Build batch queries
    queries = []
    for pkg in packages:
        queries.append({
            "package": {"name": pkg.name, "ecosystem": pkg.ecosystem},
            "version": pkg.version,
        })

    results: list[VulnResult] = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # OSV batch endpoint
            resp = await client.post(
                OSV_BATCH_URL,
                json={"queries": queries},
            )
            resp.raise_for_status()
            data = resp.json()

            batch_results = data.get("results", [])
            for i, result_set in enumerate(batch_results):
                if i >= len(packages):
                    break
                pkg = packages[i]
                vulns = result_set.get("vulns", [])
                for vuln in vulns:
                    severity = _extract_severity(vuln)
                    results.append(
                        VulnResult(
                            package_name=pkg.name,
                            package_version=pkg.version,
                            ecosystem=pkg.ecosystem,
                            vuln_id=vuln.get("id", "unknown"),
                            summary=vuln.get("summary", "No summary available")[:200],
                            severity=severity,
                            aliases=vuln.get("aliases", [])[:5],
                            source_file=pkg.source_file,
                        )
                    )
    except Exception as e:
        logger.warning("OSV API error: %s", e)

    return results


def _extract_severity(vuln: dict) -> str:
    """Extract severity from OSV vulnerability data."""
    # Check database_specific or severity field
    severity_list = vuln.get("severity", [])
    for s in severity_list:
        score_str = s.get("score", "")
        if score_str:
            try:
                score = float(score_str)
                if score >= 9.0:
                    return "critical"
                elif score >= 7.0:
                    return "high"
                elif score >= 4.0:
                    return "medium"
                else:
                    return "low"
            except ValueError:
                pass

    # Fallback: check aliases for CVE severity hints
    aliases = vuln.get("aliases", [])
    if any("CVE" in a for a in aliases):
        return "high"  # Default CVE to high if no score

    return "medium"
