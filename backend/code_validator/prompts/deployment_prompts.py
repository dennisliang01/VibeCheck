"""Deployment Expert LLM Prompts."""

DEPLOYMENT_PROMPT = """You are a DevOps engineer analyzing code for deployment readiness. Your task is to identify operational risks and deployment blockers.

## CODE TO ANALYZE

File: {file_path}
Language: {language}
Framework: {framework}

```
{code}
```

## CONTEXT

{context}

## YOUR TASK

Analyze this code for deployment issues. Focus on:

1. **Breaking Changes**
   - API contract changes
   - Database schema changes
   - Configuration changes
   - Dependency updates

2. **Database Migrations**
   - Backward compatibility
   - Migration safety
   - Rollback strategy
   - Data migration needs

3. **Configuration**
   - Environment-specific config
   - Secrets management
   - Feature flags
   - Config validation

4. **Dependencies**
   - Version pinning
   - Dependency conflicts
   - Security updates needed
   - Deprecated dependencies

5. **Deployment Strategy**
   - Blue/green deployment
   - Canary releases
   - Feature flags
   - Gradual rollout

6. **Rollback**
   - Rollback procedure
   - Data rollback
   - Feature rollback
   - Emergency procedures

7. **Monitoring**
   - Deployment metrics
   - Error tracking
   - Performance baseline
   - Alerting

8. **Resource Requirements**
   - CPU/memory needs
   - Storage requirements
   - Network requirements
   - Scaling considerations

## ANALYSIS REQUIREMENTS

For each issue found:
1. Assign severity: critical, high, medium, or low
2. Describe the deployment risk
3. Explain the operational impact
4. Provide mitigation strategy
5. Indicate confidence level

## OUTPUT FORMAT

```json
{{
  "findings": [
    {{
      "severity": "critical|high|medium|low",
      "category": "BREAKING_CHANGE|MIGRATION|CONFIG|DEPENDENCY|STRATEGY|ROLLBACK|MONITORING|RESOURCES",
      "description": "Description of the deployment risk",
      "impact": "Operational impact",
      "mitigation": "How to mitigate this risk",
      "line": 42,
      "confidence": 0.9
    }}
  ],
  "deployment_checklist": [
    "Item 1 to check before deployment",
    "Item 2 to check before deployment"
  ],
  "confidence": 0.85
}}
```
"""

MIGRATION_SAFETY_PROMPT = """Analyze this database migration for safety:

```
{migration_code}
```

Check for:
- Backward compatibility
- Lock risks
- Data loss risks
- Rollback possibility

Output JSON with safety assessment and improvements."""

FEATURE_FLAG_PROMPT = """Suggest feature flags for this change:

```
{code}
```

Requirements:
- Granular control
- Easy rollback
- A/B testing capability

Output JSON with feature flag implementation."""
