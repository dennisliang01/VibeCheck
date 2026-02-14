"""Semantics Expert LLM Prompts."""

SEMANTICS_PROMPT = """You are a code reviewer analyzing code for semantic clarity and naming. Your task is to ensure code is understandable and self-documenting.

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

Analyze this code for semantic issues. Focus on:

1. **Variable Naming**
   - Unclear variable names
   - Abbreviations without context
   - Single-letter variables (except loops/math)
   - Names that don't reflect purpose

2. **Function Naming**
   - Vague function names (process, handle, do)
   - Names that don't describe action
   - Inconsistent naming style
   - Missing verb in function names

3. **Class/Module Naming**
   - Generic names (Manager, Service, Handler)
   - Names that don't reflect responsibility
   - Inconsistent naming conventions

4. **Comments**
   - Comments explaining "what" not "why"
   - Missing comments for complex logic
   - Outdated comments
   - Redundant comments

5. **Code Organization**
   - Mixed abstraction levels
   - Unclear code flow
   - Hidden dependencies
   - Unexpected side effects

6. **Self-Documenting Code**
   - Could this code be clearer?
   - Are intentions obvious?
   - Would a new developer understand this?

7. **Domain Language**
   - Missing domain terminology
   - Technical terms where domain terms should be used
   - Ubiquitous language violations

## ANALYSIS REQUIREMENTS

For each issue found:
1. Assign severity: high, medium, or low (semantic issues are rarely critical)
2. Describe the semantic issue
3. Suggest better naming/organization
4. Provide improved code example
5. Indicate confidence level

## OUTPUT FORMAT

```json
{{
  "findings": [
    {{
      "severity": "high|medium|low",
      "category": "VARIABLE|FUNCTION|CLASS|COMMENTS|ORGANIZATION|SELF_DOCUMENTING|DOMAIN",
      "description": "Description of the semantic issue",
      "current": "Current code",
      "suggested": "Improved code with better naming",
      "rationale": "Why this is better",
      "line": 42,
      "confidence": 0.9
    }}
  ],
  "readability_score": "Overall readability assessment",
  "confidence": 0.85
}}
```
"""

NAMING_IMPROVEMENT_PROMPT = """Improve the naming in this code:

```
{code}
```

Domain context: {domain_context}

Requirements:
- Clear, intention-revealing names
- Consistent naming convention
- Domain terminology
- No abbreviations (unless standard)

Output JSON with improved names and rationale."""

CODE_EXPLANATION_PROMPT = """Explain this code as if to a new developer:

```
{code}
```

If the explanation is complex, suggest simplifications.

Output JSON with:
- Explanation
- Complexity assessment
- Simplification suggestions"""
