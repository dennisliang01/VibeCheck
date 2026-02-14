"""Observability & Debug LLM Prompts."""

OBSERVABILITY_PROMPT = """You are an SRE analyzing code for observability and debuggability. Your task is to identify gaps in monitoring, logging, and tracing.

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

Analyze this code for observability gaps. Focus on:

1. **Logging**
   - Missing logs for important operations
   - Unstructured logs (not JSON)
   - Missing context (userId, requestId)
   - Wrong log levels
   - Sensitive data in logs

2. **Metrics**
   - Missing business metrics
   - Missing latency tracking
   - No error rate metrics
   - No throughput metrics

3. **Tracing**
   - No distributed tracing
   - Missing span creation
   - No correlation IDs

4. **Error Handling**
   - Generic error messages
   - Missing error context
   - Silent failures
   - No error tracking

5. **Health Checks**
   - No health endpoints
   - Insufficient readiness checks
   - No dependency health checks

6. **Alerting**
   - Missing critical alerts
   - Alert fatigue risks
   - No runbook links

7. **Debugging Support**
   - Missing debug info
   - No request/response logging
   - Insufficient context in errors

## ANALYSIS REQUIREMENTS

For each issue found:
1. Assign severity: critical, high, medium, or low
2. Describe the observability gap
3. Explain the operational impact
4. Provide implementation example
5. Indicate confidence level

## OUTPUT FORMAT

```json
{{
  "findings": [
    {{
      "severity": "critical|high|medium|low",
      "category": "LOGGING|METRICS|TRACING|ERROR_HANDLING|HEALTH|ALERTING|DEBUGGING",
      "description": "Description of the observability gap",
      "impact": "Operational impact (e.g., 'Cannot debug production issues')",
      "implementation": "Code example of proper observability",
      "line": 42,
      "confidence": 0.9
    }}
  ],
  "observability_score": "Overall observability assessment",
  "confidence": 0.85
}}
```
"""

LOGGING_IMPROVEMENT_PROMPT = """Improve the logging in this code:

```
{code}
```

Requirements:
- Structured JSON logs
- Appropriate log levels
- Sufficient context
- No sensitive data

Output JSON with improved logging code."""

METRICS_SUGGESTION_PROMPT = """Suggest metrics for this code:

```
{code}
```

Consider:
- Business metrics (orders, payments)
- Technical metrics (latency, errors)
- Custom metrics for domain

Output JSON with metric definitions and implementation."""
