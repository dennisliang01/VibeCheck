"""Logic Inspector LLM Prompts."""

LOGIC_ANALYSIS_PROMPT = """You are a senior developer analyzing code for logical bugs and anti-patterns. Your task is to find subtle bugs that static analysis might miss.

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

Analyze this code for logical issues. Focus on the following areas:

1. **Logical Errors** examples:
   - Off-by-one errors
   - Incorrect boolean logic
   - Wrong comparison operators
   - Incorrect loop bounds

2. **Infinite Loops** examples:
   - Missing increment/decrement
   - Wrong termination conditions
   - Unreachable break conditions

3. **Unreachable Code** examples:
   - Code after return/raise
   - Conditions that are always true/false
   - Dead branches

4. **Resource Leaks** examples:
   - Unclosed files
   - Unreleased locks
   - Database connection leaks

5. **Concurrency Bugs** examples:
   - Race conditions
   - Deadlocks
   - Atomicity violations

6. **State Management** examples:
   - Inconsistent state updates
   - Missing state initialization
   - State mutation in unexpected places

7. **Algorithm Logic** examples:
   - Incorrect sorting/comparison
   - Wrong data structure usage
   - Mathematical errors

8. **AI-Generated Code Red Flags**  
   - Verbose but empty code
   - Defensive if-cascades
   - Duplicated logic
   - Commented-out dead code

## ANALYSIS REQUIREMENTS

For each issue found:
1. Assign severity: critical, high, medium, or low
2. Describe the logical flaw
3. Explain what could go wrong
4. Provide corrected code
5. Indicate confidence level

## OUTPUT FORMAT

```json
{{
  "findings": [
    {{
      "severity": "critical|high|medium|low",
      "category": "LOGIC_ERROR|INFINITE_LOOP|UNREACHABLE|RESOURCE_LEAK|CONCURRENCY|STATE|ALGORITHM",
      "description": "Description of the logical issue",
      "consequence": "What could go wrong",
      "fix": "Corrected code",
      "line": 42,
      "confidence": 0.95
    }}
  ],
  "ai_red_flags": [
    "List any AI-generated code patterns detected"
  ],
  "confidence": 0.9
}}
```
"""

RACE_CONDITION_PROMPT = """Analyze this concurrent code for race conditions:

```
{code}
```

Check for:
- Read-modify-write races
- Check-then-act races
- Publication races
- Data races on shared state

Output JSON with race conditions found and fixes using proper synchronization."""

STATE_MACHINE_PROMPT = """Analyze this state machine implementation:

```
{code}
```

Check for:
- Invalid state transitions
- Missing states
- Unhandled states
- State inconsistency

Output JSON with state machine issues and corrections."""
