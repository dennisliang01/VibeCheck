"""Functional Validator LLM Prompts."""

FUNCTIONAL_ANALYSIS_PROMPT = """You are a QA engineer analyzing code for functional correctness and test coverage. Your task is to identify gaps in functionality and testing.

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

Analyze this code for functional issues. Focus on:

1. **Missing Test Coverage**
   - Functions without corresponding tests
   - Edge cases not covered
   - Error paths not tested
   - Boundary conditions

2. **Input Validation Gaps**
   - Missing null/undefined checks
   - No empty string validation
   - Missing range checks
   - No type validation

3. **Edge Cases**
   - Empty collections
   - Single element collections
   - Maximum size inputs
   - Special characters
   - Unicode handling

4. **Error Handling**
   - Silent failures
   - Generic error messages
   - Missing error recovery
   - Resource cleanup on error

5. **Business Logic**
   - Requirements not implemented
   - Incorrect calculations
   - State machine issues
   - Race conditions in business logic

6. **Test Quality**
   - Tests that don't actually verify behavior
   - Brittle tests (over-mocking)
   - Tests with side effects
   - Missing assertions

## ANALYSIS REQUIREMENTS

For each issue found:
1. Assign severity: critical, high, medium, or low
2. Describe the functional gap
3. Provide test case example that should be added
4. Suggest fix for the code if applicable
5. Indicate confidence level

## OUTPUT FORMAT

```json
{{
  "findings": [
    {{
      "severity": "critical|high|medium|low",
      "category": "MISSING_TEST|EDGE_CASE|ERROR_HANDLING|BUSINESS_LOGIC",
      "description": "Description of the functional gap",
      "test_example": "Example test that should be added",
      "fix": "Code fix if applicable",
      "line": 42,
      "confidence": 0.9
    }}
  ],
  "test_coverage_gaps": [
    "Function X has no tests",
    "Edge case Y not covered"
  ],
  "confidence": 0.85
}}
```
"""

EDGE_CASE_ANALYSIS_PROMPT = """Identify all edge cases that should be tested for this function:

```
{code}
```

Consider:
- Null/undefined inputs
- Empty collections
- Boundary values (0, -1, MAX_INT)
- Special characters
- Very large inputs
- Concurrent access

Output JSON with edge cases and suggested test implementations."""

TEST_QUALITY_PROMPT = """Analyze the quality of these tests:

```
{test_code}
```

For the function:
```
{function_code}
```

Check for:
- Meaningful assertions
- Appropriate mocking
- Test independence
- Coverage of branches
- Clear test names

Output JSON with findings and improvement suggestions."""
