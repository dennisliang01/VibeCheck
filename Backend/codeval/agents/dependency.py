"""Dependency / Supply Chain Agent: checks for CVEs, outdated deps, pinning issues."""

from __future__ import annotations

import logging

from codeval.agents.base import BaseAgent
from codeval.llm import complete
from codeval.osv import PackageInfo, VulnResult, parse_dependencies, query_osv
from codeval.schemas import (
    AgentFinding,
    AgentReport,
    CodebaseFingerprint,
    Evidence,
    FileSnippet,
    HeuristicHit,
    SeveritySummary,
)

logger = logging.getLogger(__name__)

DEPENDENCY_SYSTEM = """You are a dependency and supply chain security expert. Analyze the dependency
information for:
- Known CVEs / vulnerabilities (already queried for you, listed below)
- Unpinned or loosely pinned dependencies (using * or no version constraint)
- Outdated major versions that may have known issues
- Unnecessary or suspicious dependencies
- License concerns (if detectable from package names)
- Development dependencies in production bundles
- Dependency duplication (same functionality from multiple packages)

Severity guidelines:
- critical: known CVEs with high CVSS score, actively exploited vulnerabilities
- high: known CVEs with medium CVSS, completely unpinned dependencies
- medium: loosely pinned deps, outdated major versions, dev deps in production
- low: minor version lag, license concerns, dependency duplication

Return JSON only. Use this exact schema:
{
  "agent": "dependency",
  "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
  "findings": [
    {
      "id": "unique-id",
      "severity": "critical|high|medium|low",
      "confidence": 0.0-1.0,
      "title": "short title",
      "evidence": {"file": "dependency-file-path", "lines": [1], "snippet": "package@version"},
      "impact": "description of supply chain risk",
      "recommendation": "what to do (upgrade, replace, pin)",
      "patch_hint": "optional version to upgrade to",
      "test_hint": "optional",
      "source": "dependency"
    }
  ],
  "questions": []
}"""


class DependencyAgent(BaseAgent):
    """Reviews dependencies: CVEs via OSV.dev, pinning, outdated versions."""

    name = "dependency"

    async def run(
        self,
        fingerprint: CodebaseFingerprint,
        files: list[FileSnippet],
        heuristics: list[HeuristicHit],
        llm_enabled: bool,
    ) -> AgentReport:
        # This agent works differently: it reads dependency files directly
        # and queries OSV.dev for CVEs, regardless of file slicing
        root = self.root_path
        if root is None:
            logger.warning("DependencyAgent: no root_path set, skipping")
            return AgentReport(agent=self.name)

        packages = parse_dependencies(root, fingerprint.dependency_files)
        vulns = await query_osv(packages)

        # Convert CVE results to findings
        vuln_findings = self._vulns_to_findings(vulns)

        if not llm_enabled:
            return self._build_report(vuln_findings, llm_ok=True)

        # Build context for LLM to do deeper analysis
        context = _build_dep_context(fingerprint, packages, vulns, files)
        user_prompt = f"""Dependency analysis context:
{context}

Known CVE scan results are included above. Analyze the dependency landscape
for additional concerns: unpinned versions, outdated packages, suspicious deps.
Return JSON with findings. Do NOT duplicate the CVE findings already listed."""

        llm_report = await complete(DEPENDENCY_SYSTEM, user_prompt, AgentReport)

        all_findings = list(vuln_findings)
        if llm_report and llm_report.findings:
            for f in llm_report.findings:
                f.source = self.name
                all_findings.append(f)

        return self._build_report(all_findings, llm_ok=bool(llm_report))

    def _vulns_to_findings(self, vulns: list[VulnResult]) -> list[AgentFinding]:
        """Convert OSV vulnerability results to AgentFinding objects."""
        findings: list[AgentFinding] = []
        for i, v in enumerate(vulns):
            aliases_str = ", ".join(v.aliases) if v.aliases else ""
            findings.append(
                AgentFinding(
                    id=f"dep-cve-{i:03d}-{v.vuln_id}",
                    severity=v.severity,
                    confidence=0.95,
                    title=f"Known vulnerability {v.vuln_id} in {v.package_name}@{v.package_version}",
                    evidence=Evidence(
                        file=v.source_file,
                        lines=(1,),
                        snippet=f"{v.package_name}@{v.package_version} ({v.ecosystem})",
                    ),
                    impact=f"{v.summary}" + (f" Aliases: {aliases_str}" if aliases_str else ""),
                    recommendation=f"Upgrade {v.package_name} to a patched version or find an alternative",
                    source=self.name,
                )
            )
        return findings

    def _build_report(self, findings: list[AgentFinding], *, llm_ok: bool = True) -> AgentReport:
        """Build agent report from findings."""
        summary = SeveritySummary()
        for f in findings:
            setattr(summary, f.severity, getattr(summary, f.severity) + 1)
        return AgentReport(agent=self.name, summary=summary, findings=findings, analyzed=llm_ok)


def _build_dep_context(
    fingerprint: CodebaseFingerprint,
    packages: list[PackageInfo],
    vulns: list[VulnResult],
    files: list[FileSnippet],
) -> str:
    """Build context string for LLM analysis."""
    lines = [
        f"Languages: {fingerprint.languages}",
        f"Frameworks: {fingerprint.frameworks}",
        f"Dependency files: {fingerprint.dependency_files}",
        "",
        f"## Parsed packages ({len(packages)} total):",
    ]
    for pkg in packages[:50]:
        lines.append(f"  - {pkg.name}@{pkg.version} ({pkg.ecosystem}, from {pkg.source_file})")

    lines.append(f"\n## OSV CVE scan results ({len(vulns)} vulnerabilities found):")
    if vulns:
        for v in vulns[:20]:
            lines.append(f"  - {v.vuln_id}: {v.package_name}@{v.package_version} [{v.severity}] {v.summary[:100]}")
    else:
        lines.append("  No known vulnerabilities found.")

    # Include dependency file snippets
    dep_snippets = [f for f in files if any(d in f.path for d in ("package.json", "requirements", "Pipfile", "go.mod", "Cargo.toml"))]
    if dep_snippets:
        lines.append("\n## Dependency file contents:")
        for s in dep_snippets[:5]:
            lines.append(f"\n--- {s.path} ---\n{s.content[:1000]}")

    return "\n".join(lines)
