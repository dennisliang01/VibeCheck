"""Agent 10: Deployment Expert - Anticipates operational impact."""

import re
from typing import List, Dict, Any
from agents.base_agent import BaseAgent
from core.models import CodeFragment, AgentResult, AgentType, ValidationContext


class DeploymentExpert(BaseAgent):
    """Anticipates l'impact operationnel."""

    def __init__(self):
        super().__init__(AgentType.DEPLOYMENT)

    def analyze(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Analyze code for deployment risks."""
        self.reset()

        # Check 1: Breaking changes in API
        self._check_api_breaking_changes(fragments, context)

        # Check 2: Deployment strategy
        self._check_deployment_strategy(fragments, context)

        # Check 3: Database backward compatibility
        self._check_db_compatibility(fragments)

        # Check 4: Dependency version pinning
        self._check_dependency_pinning(fragments, context)

        # Check 5: Data migration needs
        self._check_migration_needs(fragments)

        # Check 6: Rollback possibility
        self._check_rollback(fragments, context)

        score = self.calculate_score()

        return AgentResult(
            agent_type=self.agent_type,
            score=score,
            gaps=self.gaps,
            findings=self.findings,
            examples=self.examples,
            raw_analysis={
                "deployment_risks": len(
                    [f for f in self.findings if f["severity"] in ["critical", "high"]]
                ),
                "migration_needed": self._migration_needed(fragments),
                "rollback_possible": self._rollback_possible(fragments),
            },
        )

    def _check_api_breaking_changes(
        self, fragments: List[CodeFragment], context: ValidationContext
    ):
        """Check for breaking changes in API."""
        # Look for API endpoint definitions
        api_patterns = [
            r"@app\.route",
            r"app\.(get|post|put|delete|patch)",
            r"router\.(get|post|put|delete|patch)",
            r"@RequestMapping",
            r"@GetMapping",
            r"@PostMapping",
        ]

        # Check for version indicators
        version_patterns = [
            r"/v\d+/",
            r"/api/v\d+",
            r"@version",
            r"Version\s*=",
        ]

        has_api = any(re.search(p, f.content) for f in fragments for p in api_patterns)

        has_versioning = any(
            re.search(p, f.content) for f in fragments for p in version_patterns
        )

        if has_api and not has_versioning:
            self.add_finding(
                description="API endpoints without versioning",
                severity="medium",
                suggestion="Add API versioning to allow non-breaking changes",
            )

            self.add_example(
                title="API Versioning",
                code="""
# Instead of:
@app.route('/users')
def get_users():
    pass

# Use:
@app.route('/api/v1/users')
def get_users_v1():
    pass

# Or header-based versioning:
@app.route('/users')
def get_users():
    version = request.headers.get('API-Version', '1')
    if version == '1':
        return get_users_v1()
    elif version == '2':
        return get_users_v2()
""",
                explanation="Versioning allows evolving APIs without breaking existing clients",
            )

    def _check_deployment_strategy(
        self, fragments: List[CodeFragment], context: ValidationContext
    ):
        """Check for deployment strategy indicators."""
        strategy_patterns = [
            r"feature.?flag",
            r"feature_flag",
            r"launch.?darkly",
            r"canary",
            r"blue.?green",
            r"rolling",
            r"gradual",
            r"percentage",
            r"rollout",
        ]

        has_strategy = any(
            re.search(p, f.content, re.IGNORECASE)
            for f in fragments
            for p in strategy_patterns
        )

        if not has_strategy:
            # Check if this is a significant service
            service_indicators = [
                r"app\.listen",
                r"server\.listen",
                r"createServer",
                r"uvicorn",
                r"gunicorn",
                r"wsgi",
            ]

            is_service = any(
                re.search(p, f.content) for f in fragments for p in service_indicators
            )

            if is_service:
                self.add_finding(
                    description="No deployment strategy (feature flags, canary) detected",
                    severity="medium",
                    suggestion="Consider feature flags for safer deployments",
                )

    def _check_db_compatibility(self, fragments: List[CodeFragment]):
        """Check for database backward compatibility."""
        migration_patterns = [
            r"migration",
            r"migrate",
            r"alembic",
            r"sequelize",
            r"db\.migrate",
            r"knex",
            r"flyway",
            r"liquibase",
        ]

        schema_patterns = [
            r"schema",
            r"model",
            r"@Entity",
            r"class.*Model",
            r"define\s*\(",
            r"Sequelize\.",
            r" mongoose\.",
        ]

        has_migrations = any(
            re.search(p, f.content, re.IGNORECASE)
            for f in fragments
            for p in migration_patterns
        )

        has_schema = any(
            re.search(p, f.content, re.IGNORECASE)
            for f in fragments
            for p in schema_patterns
        )

        if has_schema and not has_migrations:
            self.add_finding(
                description="Database schema without migration system",
                severity="high",
                suggestion="Add database migrations for safe schema evolution",
            )

        # Check for destructive operations
        destructive_patterns = [
            r"DROP\s+(TABLE|COLUMN)",
            r"drop\s*\(",
            r"\.drop\s*\(",
            r"REMOVE\s+COLUMN",
            r"delete.*column",
        ]

        for fragment in fragments:
            for pattern in destructive_patterns:
                if re.search(pattern, fragment.content, re.IGNORECASE):
                    self.add_finding(
                        description="Destructive database operation detected",
                        severity="critical",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Destructive changes should be done in multiple deployments: add new -> migrate data -> remove old",
                    )

    def _check_dependency_pinning(
        self, fragments: List[CodeFragment], context: ValidationContext
    ):
        """Check for dependency version pinning."""
        dep_files = {
            "package.json": r'"[@\w/-]+"\s*:\s*"[\^~]',
            "requirements.txt": r"^[\w-]+\s*(>|>=|<|<=)",
            "Pipfile": r'[\w-]+\s*=\s*"\*"',
            "Cargo.toml": r'[\w-]+\s*=\s*"\*"',
        }

        for fragment in fragments:
            filename = fragment.file_path.split("/")[-1]
            if filename in dep_files:
                pattern = dep_files[filename]
                loose_deps = re.findall(pattern, fragment.content)

                if loose_deps:
                    self.add_finding(
                        description=f"Loose version constraints in {filename} - may cause reproducibility issues",
                        severity="medium",
                        file=fragment.file_path,
                        suggestion="Pin exact versions or use lock files (package-lock.json, Pipfile.lock, Cargo.lock)",
                    )

    def _check_migration_needs(self, fragments: List[CodeFragment]):
        """Check if data migration is needed."""
        # Look for data transformation patterns
        transform_patterns = [
            r"rename",
            r"migrate",
            r"transform",
            r"convert",
            r"deprecat",
            r"legacy",
            r"v1.*v2",
            r"old.*new",
        ]

        has_transforms = any(
            re.search(p, f.content, re.IGNORECASE)
            for f in fragments
            for p in transform_patterns
        )

        if has_transforms:
            self.add_finding(
                description="Data transformation patterns detected - migration may be needed",
                severity="medium",
                suggestion="Document migration plan and test on staging data",
            )

    def _check_rollback(
        self, fragments: List[CodeFragment], context: ValidationContext
    ):
        """Check if rollback is possible."""
        rollback_indicators = [
            r"rollback",
            r"revert",
            r"undo",
            r"backup",
            r"down\s*\(",
            r"downgrade",
            r"migrate.*down",
        ]

        has_rollback = any(
            re.search(p, f.content, re.IGNORECASE)
            for f in fragments
            for p in rollback_indicators
        )

        # Check for infrastructure that supports rollback
        infra_patterns = [
            r"kubernetes",
            r"k8s",
            r"docker",
            r"terraform",
            r"cloudformation",
            r"pulumi",
        ]

        has_infra = any(
            re.search(p, f.content, re.IGNORECASE)
            for f in fragments
            for p in infra_patterns
        )

        if has_infra and not has_rollback:
            self.add_finding(
                description="Infrastructure code without explicit rollback strategy",
                severity="medium",
                suggestion="Document rollback procedure and test it regularly",
            )

    def _migration_needed(self, fragments: List[CodeFragment]) -> bool:
        """Check if data migration is needed."""
        migration_patterns = [
            r"migration",
            r"migrate",
            r"schema.*change",
            r"ALTER\s+TABLE",
            r"add_column",
            r"remove_column",
        ]

        return any(
            re.search(p, f.content, re.IGNORECASE)
            for f in fragments
            for p in migration_patterns
        )

    def _rollback_possible(self, fragments: List[CodeFragment]) -> str:
        """Assess if rollback is possible."""
        rollback_patterns = [
            r"rollback",
            r"downgrade",
            r"revert",
            r"undo",
            r"blue.?green",
            r"canary",
        ]

        has_rollback = any(
            re.search(p, f.content, re.IGNORECASE)
            for f in fragments
            for p in rollback_patterns
        )

        return "yes" if has_rollback else "unclear"
