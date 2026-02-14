"""Performance Expert LLM Prompts."""

PERFORMANCE_ANALYSIS_PROMPT = """You are a senior performance engineer analyzing code for scalability issues. Your task is to identify performance bottlenecks that static analysis might miss.

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

Analyze this code for performance issues. Focus on:

1. **Algorithmic Inefficiencies**
   - Hidden O(n²) or worse patterns
   - Inefficient data structure choices
   - Unnecessary computations

2. **Memory Management**
   - Memory leaks (circular references, unclosed resources)
   - Excessive memory allocation
   - Large object retention
   - Garbage collection pressure

3. **Concurrency Issues**
   - Lock contention
   - Thread pool exhaustion
   - Blocking operations in async code
   - Race conditions affecting performance

4. **I/O Bottlenecks**
   - Synchronous I/O in hot paths
   - Unbuffered I/O
   - Excessive system calls

5. **Database Performance**
   - Missing indexes (implied by query patterns)
   - Inefficient query patterns
   - Connection pool issues

6. **Caching Opportunities**
   - Expensive computations that could be cached
   - Cache stampede risks
   - Inappropriate cache keys

7. **Network Efficiency**
   - Chatty APIs
   - Large payload sizes
   - Missing compression

## ANALYSIS REQUIREMENTS

For each issue found:
1. Assign severity: critical, high, medium, or low
2. Describe the performance impact
3. Estimate when this becomes a problem (load/volume)
4. Provide concrete optimization with code example
5. Estimate performance improvement
6. Indicate confidence level

## OUTPUT FORMAT

```json
{{
  "findings": [
    {{
      "severity": "critical|high|medium|low",
      "category": "ALGORITHM|MEMORY|CONCURRENCY|IO|DATABASE|CACHE|NETWORK",
      "description": "Description of the performance issue",
      "impact": "What happens under load",
      "breaking_point": "At what scale this becomes critical",
      "fix": "Optimized code example",
      "estimated_improvement": "10x faster, 50% less memory, etc.",
      "line": 42,
      "confidence": 0.9
    }}
  ],
  "scalability_assessment": "How well this code will scale",
  "confidence": 0.85
}}
```
"""

SCALABILITY_PREDICTION_PROMPT = """Predict the scalability limits of this code:

```
{code}
```

Context:
- Expected QPS: {expected_qps}
- Data volume: {data_volume}
- Concurrency: {concurrency_level}

Analyze:
1. What will be the first bottleneck?
2. At what load will it occur?
3. What's the maximum sustainable load?

Output JSON with predictions."""

MEMORY_ANALYSIS_PROMPT = """Analyze memory usage patterns in this code:

```
{code}
```

Check for:
- Memory leaks (unclosed resources, circular refs)
- Large allocations in loops
- Object retention (caches growing unbounded)
- String concatenation in loops
- Inefficient data structures

Output JSON with findings and heap impact estimates."""
