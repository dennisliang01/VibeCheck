"""Resilience Manager LLM Prompts."""

RESILIENCE_PROMPT = """You are a reliability engineer analyzing code for resilience and fault tolerance. Your task is to identify failure modes and suggest resilience patterns.

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

Analyze this code for resilience gaps. Focus on:

1. **Error Handling**
   - Missing error handling
   - Generic catch blocks
   - Swallowed exceptions
   - No error recovery

2. **Retry Logic**
   - Missing retries for transient failures
   - No exponential backoff
   - Retry storms
   - Non-idempotent retries

3. **Circuit Breakers**
   - No circuit breaking for external calls
   - Missing fallback strategies
   - Cascade failure risks

4. **Timeouts**
   - Missing timeouts on I/O
   - Infinite waits
   - No timeout handling

5. **Resource Management**
   - Resource leaks
   - No resource limits
   - Unbounded queues
   - Memory leaks

6. **Graceful Degradation**
   - No fallback mechanisms
   - All-or-nothing behavior
   - Missing feature flags

7. **Bulkheads**
   - No isolation between components
   - Shared resource exhaustion
   - No rate limiting

8. **Idempotency**
   - Non-idempotent operations
   - Duplicate request handling
   - No deduplication

9. **State Consistency**
   - Partial state updates
   - Missing transactions
   - Inconsistent state on failure

## ANALYSIS REQUIREMENTS

For each issue found:
1. Assign severity: critical, high, medium, or low
2. Describe the resilience gap
3. Explain the failure scenario
4. Provide resilience pattern implementation
5. Indicate confidence level

## OUTPUT FORMAT

```json
{{
  "findings": [
    {{
      "severity": "critical|high|medium|low",
      "category": "ERROR_HANDLING|RETRY|CIRCUIT_BREAKER|TIMEOUT|RESOURCE|DEGRADATION|BULKHEAD|IDEMPOTENCY|CONSISTENCY",
      "description": "Description of the resilience gap",
      "failure_scenario": "What happens when this fails",
      "pattern": "Resilience pattern to apply",
      "implementation": "Code example of resilient implementation",
      "line": 42,
      "confidence": 0.9
    }}
  ],
  "resilience_assessment": "Overall resilience assessment",
  "confidence": 0.85
}}
```
"""

CIRCUIT_BREAKER_PROMPT = """Add circuit breaker pattern to this external call:

```
{code}
```

Requirements:
- Failure threshold
- Recovery timeout
- Half-open state
- Fallback strategy

Output JSON with circuit breaker implementation."""

RETRY_PATTERN_PROMPT = """Add proper retry logic to this code:

```
{code}
```

Requirements:
- Exponential backoff
- Max retry attempts
- Jitter
- Idempotency check

Output JSON with retry implementation."""
