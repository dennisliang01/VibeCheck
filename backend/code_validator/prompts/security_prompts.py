"""Security Auditor LLM Prompts."""

SECURITY_ANALYSIS_PROMPT = """You are an expert security engineer performing a code security audit. Your task is to identify vulnerabilities that automated static analysis might miss.

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

Analyze this code for security vulnerabilities. Focus on:

1. **Business Logic Flaws** - Authentication/authorization bypasses, privilege escalation
2. **Input Validation Gaps** - Missing or insufficient validation for the context
3. **Data Flow Issues** - Sensitive data exposure, insecure data handling
4. **Race Conditions** - TOCTOU (time-of-check-time-of-use) vulnerabilities
5. **Cryptographic Issues** - Weak algorithms, improper key management, IV reuse
6. **Injection Vectors** - Beyond SQL: Command, LDAP, XPath, XML, Template injection
7. **Deserialization Risks** - Unsafe object deserialization
8. **SSRF** - Server-Side Request Forgery possibilities
9. **Path Traversal** - File system access beyond intended boundaries
10. **Information Disclosure** - Error messages, debug info, stack traces leaking data

## ANALYSIS REQUIREMENTS

For each vulnerability found:
1. Assign severity: critical, high, medium, or low
2. Provide clear description of the issue
3. Explain the attack scenario - how could this be exploited?
4. Provide a concrete fix with code example
5. Reference relevant CWE if applicable
6. Indicate your confidence level (0.0-1.0)

## OUTPUT FORMAT

Respond with valid JSON only:

```json
{{
  "findings": [
    {{
      "severity": "critical|high|medium|low",
      "category": "SQL_INJECTION|XSS|AUTH_BYPASS|etc",
      "description": "Clear explanation of the vulnerability",
      "attack_scenario": "How an attacker could exploit this",
      "fix": "Concrete code fix with example",
      "line": 42,
      "cwe": "CWE-89",
      "confidence": 0.95
    }}
  ],
  "summary": "Brief summary of overall security posture",
  "confidence": 0.9
}}
```

If no vulnerabilities are found, return an empty findings array with a positive summary.
"""

SECURITY_CONTEXT_PROMPT = """Additional context for security analysis:

- Entry points: {entry_points}
- Authentication mechanism: {auth_mechanism}
- Database: {database}
- External APIs called: {external_apis}
- Sensitive data handled: {sensitive_data}
"""

# Focused prompts for specific security checks
AUTH_ANALYSIS_PROMPT = """Analyze authentication and authorization in this code:

```
{code}
```

Check for:
- Missing authentication on protected endpoints
- Weak authentication (hardcoded credentials, weak passwords)
- Session management issues
- JWT vulnerabilities (none algorithm, weak signing, expiration)
- Authorization bypasses (IDOR, horizontal/vertical privilege escalation)
- OAuth/OpenID Connect misconfigurations

Output JSON with findings array."""

INPUT_VALIDATION_PROMPT = """Analyze input validation in this code:

```
{code}
```

Check for:
- Missing validation on user inputs
- Insufficient validation (type checking but not range/boundary)
- Validation after use (TOCTOU)
- Validation bypass possibilities
- File upload validation issues
- Content-Type validation gaps

Output JSON with findings array."""

CRYPTO_ANALYSIS_PROMPT = """Analyze cryptographic usage in this code:

```
{code}
```

Check for:
- Weak algorithms (MD5, SHA1, DES, RC4)
- Hardcoded keys or IVs
- ECB mode usage
- Randomness issues (Math.random for crypto)
- Certificate validation disabled
- Password hashing issues (unsalted, weak algorithms)

Output JSON with findings array."""
