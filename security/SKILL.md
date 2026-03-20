---
name: security
description: >-
  Framework-agnostic security rules including input validation, auth principles,
  CORS, API headers, rate limiting, secret management, authentication patterns
  (JWT, OAuth2, session, MFA), and web protection (CSRF, XSS, injection defense, TLS).
  Use when implementing security-related code.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
compatibility:
  - OpenCode
  - Claude Code
  - Codex
  - Antigravity
---
# Security Rules

## 1. Input Validation Principles

| Rule                                  | Purpose                                  |
| ------------------------------------- | ---------------------------------------- |
| Validate at API boundary              | Reject bad input early                   |
| Whitelist over blacklist              | Allow known-good, reject everything else |
| Validate type, length, range, format  | Prevent injection and overflow           |
| Sanitize output, not just input       | Prevent XSS in responses                 |
| Never trust client-side validation    | Always re-validate server-side           |

---

## 2. Authentication and Authorization Principles

- Apply least privilege — grant minimum permissions needed
- Use role-based access control (RBAC) at endpoint level
- Apply defense in depth — check authorization in service layer, not just URL
- Use method-level security for fine-grained control
- Log all authentication failures and authorization denials
- Never rely on URL-based security alone

---

## 3. CORS Principles

- Never use wildcard (`*`) origins in production
- Explicitly list allowed origins, methods, and headers
- Set `maxAge` to reduce preflight requests
- Separate CORS config per environment (dev may be more permissive)

---

## 4. API Security Headers

| Header                       | Value                                 | Purpose                   |
| ---------------------------- | ------------------------------------- | ------------------------- |
| `X-Content-Type-Options`     | `nosniff`                             | Prevent MIME sniffing     |
| `X-Frame-Options`            | `DENY`                                | Prevent clickjacking      |
| `Strict-Transport-Security`  | `max-age=31536000; includeSubDomains` | Force HTTPS               |
| `Cache-Control`              | `no-store`                            | Prevent sensitive caching |
| `X-XSS-Protection`           | `0`                                   | Disable (use CSP instead) |

---

## 5. Rate Limiting Guidelines

### Recommended Limits

| Endpoint Type      | Limit    | Window     |
| ------------------ | -------- | ---------- |
| Public API         | 100 req  | Per minute |
| Authenticated API  | 1000 req | Per minute |
| Login/Auth         | 10 req   | Per minute |
| File upload        | 10 req   | Per hour   |

### Response Headers

- `X-RateLimit-Limit`: Maximum requests allowed in window
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Timestamp when the window resets

---

## 6. Sensitive Data in Responses

### Never Expose

- Password hashes
- Internal IDs when external IDs exist
- Stack traces or internal error details
- Database column names in error messages
- Server version or framework information

### Response Filtering

- Use dedicated response DTOs — never return entities directly
- Exclude internal fields (password, internal flags, audit metadata)
- Map entities to response objects at the API boundary

---

## 7. Secret Management Principles

- Store secrets in environment variables or secret manager (Vault, AWS SSM, etc.)
- Never commit secrets to version control
- Rotate secrets periodically (at least every 90 days)
- Use different secrets per environment
- Revoke and rotate immediately if any secret is exposed
- Never provide default values for secrets in configuration files

---

## 8. Anti-Patterns

- Hardcoding secrets in source code or config files
- Returning entities directly from API endpoints
- Using wildcard CORS in production
- Missing rate limiting on authentication endpoints
- Logging sensitive data (passwords, tokens, PII)
- Trusting client-side validation without server-side checks
- Exposing detailed error internals in API responses
- **Security by Obscurity**: Relying solely on hiding for security. Design systems to be secure even when exposed
- **Rolling Your Own Crypto**: Using unverified custom encryption algorithms. Use standard libraries (AES, RSA, bcrypt)
- **Excessive Permissions**: Violating the principle of least privilege. Grant only the minimum required permissions
- **Delayed Security Updates**: Postponing known CVE patches increases attack exposure. Apply patches immediately

---

## 9. OWASP Top 10 Awareness

[OWASP](https://owasp.org/) (Open Worldwide Application Security Project) publishes the industry-standard list of the most critical web application security risks. The [OWASP Top 10](https://owasp.org/www-project-top-ten/) is updated every 3-4 years (latest: 2021) and serves as the de facto security baseline for code reviews, audits, and compliance.

When writing code, be vigilant against all 10 categories:

| #   | Vulnerability                              | Prevention                                              |
| --- | ------------------------------------------ | ------------------------------------------------------- |
| A01 | Broken Access Control                      | Check authorization at service layer; deny by default   |
| A02 | Cryptographic Failures                     | Encrypt at rest and in transit; use strong algorithms   |
| A03 | Injection (SQL, Cmd, LDAP, XSS)            | Use parameterized queries; never concatenate user input |
| A04 | Insecure Design                            | Apply threat modeling; use secure design patterns       |
| A05 | Security Misconfiguration                  | No default credentials; disable debug in production     |
| A06 | Vulnerable and Outdated Components         | Keep dependencies updated; monitor CVE databases        |
| A07 | Identification and Authentication Failures | Use established auth libraries; enforce MFA             |
| A08 | Software and Data Integrity Failures       | Verify integrity of updates; use digital signatures     |
| A09 | Security Logging and Monitoring Failures   | Log security events; ensure logs are tamper-resistant   |
| A10 | Server-Side Request Forgery (SSRF)         | Validate and whitelist outbound URLs                    |

## Related Skills

- For secret lifecycle management (rotation, storage, detection), see [secrets-management](../secrets-management/) skill
- For Kubernetes security (RBAC, NetworkPolicy, Pod Security), see [k8s-workflow](../k8s-workflow/) skill

## Additional References

- For authentication and authorization implementation patterns, see [references/authentication.md](references/authentication.md)
- For web protection (CSRF, XSS, injection defense, TLS), see [references/web-protection.md](references/web-protection.md)
- For Spring Boot implementation patterns (SecurityFilterChain, Bean Validation), see `spring-framework` skill — [references/security.md](../spring-framework/references/security.md)
