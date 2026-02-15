"""Structural Architect LLM Prompts."""

ARCHITECTURE_ANALYSIS_PROMPT = """You are a software architect analyzing code for architectural quality and design patterns. Your task is to identify design issues and suggest improvements.

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

Analyze this code for architectural issues. Focus on:

1. **Single Responsibility Principle**
   - Classes/functions doing too much
   - Mixed abstraction levels
   - God classes/objects

2. **Coupling & Cohesion**
   - Tight coupling between modules
   - Circular dependencies
   - low cohesion within modules

3. **Layer Violations**
   - Business logic in presentation layer
   - Database access in domain layer
   - Infrastructure leaking into domain

4. **Dependency Management**
   - Dependency inversion violations
   - Concrete dependencies instead of abstractions
   - Missing dependency injection

5. **Design Patterns**
   - Missing appropriate patterns
   - Misapplied patterns
   - Pattern overuse

6. **Abstraction Level**
   - Over-engineering
   - Under-engineering
   - Inconsistent abstraction

7. **Module Boundaries**
   - Unclear module responsibilities
   - Leaky abstractions
   - Improper encapsulation

8. **Scalability Architecture**
   - Monolithic blocks that should be services
   - Missing async boundaries
   - Synchronous chains that should be async

## ANALYSIS REQUIREMENTS

For each issue found:
1. Assign severity: critical, high, medium, or low
2. Describe the architectural flaw
3. Explain the impact on maintainability/scalability
4. Suggest refactoring approach with example
5. Indicate confidence level

## OUTPUT FORMAT

```json
{{
  "findings": [
    {{
      "severity": "critical|high|medium|low",
      "category": "SRP|COUPLING|LAYER_VIOLATION|DEPENDENCY|PATTERN|ABSTRACTION|BOUNDARY",
      "description": "Description of the architectural issue",
      "impact": "Impact on the system",
      "refactoring": "Suggested refactoring approach",
      "example": "Code example of improved design",
      "line": 42,
      "confidence": 0.9
    }}
  ],
  "architecture_suggestion": "Overall architectural recommendation",
  "confidence": 0.85
}}
```
"""

CLEAN_ARCHITECTURE_PROMPT = """Analyze this code against Clean Architecture principles:

```
{code}
```

Check for:
- Dependency direction (inward only)
- Domain layer purity (no external deps)
- Use case boundaries
- Interface adapters
- Framework independence

Output JSON with violations and fixes."""

MICROSERVICE_BOUNDARY_PROMPT = """Analyze if this code should be split into microservices:

```
{code}
```

Context:
- Current deployment unit size
- Team structure
- Scaling requirements
- Data ownership

Output JSON with:
- Current issues with monolith
- Suggested service boundaries
- Migration strategy"""
