"""Technical Debt Hunter LLM Prompts."""

TECHNICAL_DEBT_PROMPT = """You are a code quality expert analyzing for technical debt and code smells. Your task is to identify code that needs refactoring.

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

Analyze this code for technical debt. Focus on:

1. **Code Duplication**
   - Copy-pasted code blocks
   - Near-duplicates that should be unified
   - Violations of DRY principle

2. **Long Methods/Functions**
   - Methods doing too much
   - Deep nesting
   - Multiple responsibilities

3. **Large Classes**
   - God classes
   - Classes with too many methods
   - Mixed responsibilities

4. **Comment Quality**
   - Comments explaining "what" not "why"
   - Outdated comments
   - Redundant comments
   - Missing critical comments

5. **Naming Issues**
   - Unclear variable names
   - Inconsistent naming conventions
   - Abbreviations without context

6. **Magic Numbers/Strings**
   - Unnamed constants
   - Repeated literals

7. **Dead Code**
   - Unused methods
   - Unreachable code
   - Commented-out code

8. **Complexity**
   - Deep nesting
   - Too many parameters
   - Complex conditionals

9. **Outdated Practices**
   - Deprecated API usage
   - Old language features
   - Anti-patterns

## ANALYSIS REQUIREMENTS

For each issue found:
1. Assign severity: critical, high, medium, or low
2. Describe the technical debt
3. Estimate refactoring effort
4. Provide refactored code example
5. Indicate confidence level

## OUTPUT FORMAT

```json
{{
  "findings": [
    {{
      "severity": "critical|high|medium|low",
      "category": "DUPLICATION|LONG_METHOD|LARGE_CLASS|COMMENTS|NAMING|MAGIC|DEAD_CODE|COMPLEXITY|OUTDATED",
      "description": "Description of the technical debt",
      "effort": "Small|medium|Large refactoring effort",
      "refactoring": "Refactored code example",
      "line": 42,
      "confidence": 0.9
    }}
  ],
  "debt_estimate": "Overall technical debt assessment",
  "confidence": 0.85
}}
```
"""

REFACTORING_SUGGESTION_PROMPT = """Suggest specific refactorings for this code:

```
{code}
```

Consider:
- Extract Method
- Extract Class
- Rename
- Introduce Parameter Object
- Replace Conditional with Polymorphism

Output JSON with specific refactorings and improved code."""
