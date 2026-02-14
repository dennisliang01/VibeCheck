"""Agent 3: Structural Architect - Validates architectural quality and design."""

import re
from collections import defaultdict
from typing import List, Dict, Any, Set
from agents.base_agent import BaseAgent
from core.models import CodeFragment, AgentResult, AgentType, ValidationContext


class StructuralArchitect(BaseAgent):
    """Validates architectural quality and design."""

    def __init__(self):
        super().__init__(AgentType.ARCHITECTURE)
        self.file_responsibilities = {}
        self.dependencies = defaultdict(set)

    def analyze(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Analyze code for architectural quality."""
        self.reset()

        # Check 1: Single Responsibility Principle
        self._check_single_responsibility(fragments)

        # Check 2: File naming
        self._check_file_naming(fragments)

        # Check 3: God files / utils trap
        self._check_god_files(fragments)

        # Check 4: Coupling analysis
        self._check_coupling(fragments)

        # Check 5: Boundary respect (Clean Architecture)
        self._check_architecture_boundaries(fragments, context)

        # Check 6: Dependency inversion
        self._check_dependency_inversion(fragments)

        # Check 7: Abstraction level
        self._check_abstraction_level(fragments)

        # Check 8: Modification test
        self._check_modification_impact(fragments)

        score = self.calculate_score()

        return AgentResult(
            agent_type=self.agent_type,
            score=score,
            gaps=self.gaps,
            findings=self.findings,
            examples=self.examples,
            raw_analysis={
                "files_analyzed": len(set(f.file_path for f in fragments)),
                "coupling_graph": dict(self.dependencies),
                "architecture_suggestion": self._suggest_architecture(
                    fragments, context
                ),
            },
        )

    def _check_single_responsibility(self, fragments: List[CodeFragment]):
        """Check if each file has a single clear responsibility."""
        file_fragments = defaultdict(list)
        for f in fragments:
            file_fragments[f.file_path].append(f)

        for file_path, frags in file_fragments.items():
            types = set(f.fragment_type for f in frags)

            # A file should primarily contain one type of construct
            if len(types) > 3:
                self.add_finding(
                    description=f"File '{file_path}' contains {len(types)} different construct types",
                    severity="medium",
                    file=file_path,
                    suggestion="Consider splitting into separate files by responsibility",
                )

            # Count exports/definitions
            definition_count = len(
                [f for f in frags if f.fragment_type in ["function", "class", "method"]]
            )
            if definition_count > 10:
                self.add_finding(
                    description=f"File '{file_path}' has {definition_count} definitions - possible god file",
                    severity="high",
                    file=file_path,
                    suggestion="Split large files into smaller, focused modules",
                )

    def _check_file_naming(self, fragments: List[CodeFragment]):
        """Check if file names describe their role."""
        generic_names = [
            "utils",
            "helpers",
            "misc",
            "common",
            "shared",
            "base",
            "index",
            "main",
            "app",
            "service",
            "manager",
            "handler",
        ]

        file_paths = set(f.file_path for f in fragments)

        for file_path in file_paths:
            filename = file_path.split("/")[-1].split(".")[0].lower()

            if filename in generic_names:
                self.add_finding(
                    description=f"Generic filename '{filename}' doesn't describe its specific role",
                    severity="medium",
                    file=file_path,
                    suggestion=f"Rename to something more descriptive, e.g., '{filename}_specific_purpose'",
                )

    def _check_god_files(self, fragments: List[CodeFragment]):
        """Check for god files and utils trap."""
        utils_files = [
            f
            for f in fragments
            if "util" in f.file_path.lower() or "helper" in f.file_path.lower()
        ]

        if utils_files:
            by_file = defaultdict(list)
            for f in utils_files:
                by_file[f.file_path].append(f)

            for file_path, frags in by_file.items():
                if len(frags) > 15:
                    self.add_finding(
                        description=f"Utils file '{file_path}' has become a dumping ground ({len(frags)} functions)",
                        severity="high",
                        file=file_path,
                        suggestion="Extract related functions into domain-specific modules",
                    )

                    self.add_example(
                        title="Refactor utils trap",
                        code=f"""
# Instead of:
# utils.py (50 unrelated functions)

# Consider:
# string_utils.py
# date_utils.py
# validation_utils.py
# api_utils.py
""",
                        explanation="Group related utilities by domain",
                    )

    def _check_coupling(self, fragments: List[CodeFragment]):
        """Check coupling between files."""
        import_patterns = [
            r"import\s+(\w+)",  # Python/JS
            r"from\s+\S+\s+import\s+(\w+)",  # Python
            r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',  # JS
            r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',  # ES6
        ]

        for fragment in fragments:
            if fragment.fragment_type == "module":
                for pattern in import_patterns:
                    imports = re.findall(pattern, fragment.content)
                    for imp in imports:
                        self.dependencies[fragment.file_path].add(imp)

        # Check for files with too many dependencies
        for file_path, deps in self.dependencies.items():
            if len(deps) > 15:
                self.add_finding(
                    description=f"File '{file_path}' has {len(deps)} dependencies - high coupling",
                    severity="medium",
                    file=file_path,
                    suggestion="Reduce dependencies by extracting common interfaces or using dependency injection",
                )

    def _check_architecture_boundaries(
        self, fragments: List[CodeFragment], context: ValidationContext
    ):
        """Check if Clean Architecture boundaries are respected."""
        # Look for layer indicators
        layer_patterns = {
            "domain": ["entity", "model", "domain", "business"],
            "application": ["service", "usecase", "interactor", "application"],
            "infrastructure": ["repository", "db", "database", "api", "http", "infra"],
            "presentation": ["controller", "view", "component", "presenter", "ui"],
        }

        file_layers = {}
        for fragment in fragments:
            file_path_lower = fragment.file_path.lower()
            for layer, indicators in layer_patterns.items():
                if any(ind in file_path_lower for ind in indicators):
                    file_layers[fragment.file_path] = layer
                    break

        # Check for violations (infrastructure leaking into domain)
        infra_in_domain = []
        for fragment in fragments:
            if file_layers.get(fragment.file_path) in ["domain", "application"]:
                infra_patterns = [
                    r"import.*db",
                    r"import.*http",
                    r"fetch\(",
                    r"axios",
                    r"requests\.",
                ]
                for pattern in infra_patterns:
                    if re.search(pattern, fragment.content):
                        infra_in_domain.append(fragment.file_path)

        if infra_in_domain:
            self.add_finding(
                description=f"Infrastructure dependencies found in domain/application layer: {len(set(infra_in_domain))} files",
                severity="high",
                suggestion="Apply Dependency Inversion Principle - domain should not depend on infrastructure",
            )

            self.add_example(
                title="Clean Architecture layers",
                code="""
# Layer dependency rule:
# Presentation -> Application -> Domain <- Infrastructure
#
# Domain (entities, business rules) - NO external dependencies
# Application (use cases) - depends only on Domain
# Infrastructure (DB, HTTP, external APIs) - implements Domain interfaces
# Presentation (UI, Controllers) - depends on Application
""",
                explanation="Dependencies should point inward toward the domain",
            )

    def _check_dependency_inversion(self, fragments: List[CodeFragment]):
        """Check for dependency inversion principle violations."""
        # Look for direct instantiation of concrete classes
        concrete_patterns = [
            r"new\s+\w+Repository",  # JS/Java
            r"new\s+\w+Service",
            r"new\s+\w+Client",
            r"=\s*\w+\(\)",  # Function calls that might be constructors
        ]

        for fragment in fragments:
            for pattern in concrete_patterns:
                matches = re.findall(pattern, fragment.content)
                if len(matches) > 5:
                    self.add_finding(
                        description=f"Multiple concrete instantiations in '{fragment.file_path}' - DIP violation",
                        severity="medium",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Use dependency injection or factory patterns",
                    )
                    break

    def _check_abstraction_level(self, fragments: List[CodeFragment]):
        """Check for consistent abstraction level."""
        for fragment in fragments:
            if fragment.fragment_type == "function":
                lines = fragment.content.split("\n")

                # Check mixing high and low level operations
                high_level = ["process", "handle", "manage", "orchestrate"]
                low_level = [
                    "append",
                    "push",
                    "slice",
                    "substring",
                    "charAt",
                    "indexOf",
                ]

                has_high = any(h in line for line in lines for h in high_level)
                has_low = any(l in line for line in lines for l in low_level)

                if has_high and has_low:
                    # This might be mixing abstraction levels
                    low_level_count = sum(
                        1 for line in lines for l in low_level if l in line
                    )
                    if low_level_count > 5:
                        self.add_finding(
                            description=f"Function '{fragment.metadata.get('name')}' mixes abstraction levels",
                            severity="low",
                            file=fragment.file_path,
                            line=fragment.start_line,
                            suggestion="Extract low-level operations into helper functions",
                        )

    def _check_modification_impact(self, fragments: List[CodeFragment]):
        """Estimate impact of feature changes."""
        # Group files by feature/domain
        file_groups = defaultdict(list)
        for f in fragments:
            parts = f.file_path.split("/")
            if len(parts) > 1:
                feature = (
                    parts[0]
                    if parts[0] not in ["src", "lib", "app"]
                    else (parts[1] if len(parts) > 1 else parts[0])
                )
                file_groups[feature].append(f.file_path)

        # Check for features touching many files
        for feature, files in file_groups.items():
            unique_files = len(set(files))
            if unique_files > 10:
                self.add_finding(
                    description=f"Feature '{feature}' spans {unique_files} files - high modification impact",
                    severity="medium",
                    suggestion="Consider consolidating related functionality to reduce blast radius",
                )

    def _suggest_architecture(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> str:
        """Suggest an architecture diagram."""
        if context.framework in ["react", "vue", "angular"]:
            return "Component-based architecture with containers/presenters separation"
        elif context.framework in ["django", "flask", "fastapi"]:
            return "Layered architecture: routes -> services -> repositories -> models"
        elif context.framework in ["express", "nestjs"]:
            return "Controller-Service-Repository pattern with middleware layer"
        elif context.framework in ["spring"]:
            return "Spring Boot layered: Controller -> Service -> Repository -> Entity"
        else:
            return "Consider Clean Architecture or Hexagonal Architecture for better separation of concerns"
