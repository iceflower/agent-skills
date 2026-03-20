# Web Protection Patterns

## 1. CSRF Protection

### Attack Mechanism

```text
1. User logs into legitimate site (session cookie set)
2. User visits attacker's page
3. Attacker's page submits form to legitimate site
4. Browser includes session cookie automatically
5. Server processes request as authenticated user
```

### Defense Strategies

| Strategy | Mechanism | Recommended |
| --- | --- | --- |
| SameSite cookies | Browser blocks cross-origin cookie sending | Yes (primary) |
| Synchronizer Token | Server-generated token in form, validated on submit | Yes (defense in depth) |
| Double-Submit Cookie | Random token in cookie + request header, compare | Yes (stateless) |
| Custom request header | Require custom header (e.g., `X-Requested-With`) | Partial (CORS-dependent) |

### SameSite Cookie Configuration

| Value | Behavior | Use Case |
| --- | --- | --- |
| `Strict` | Never sent cross-site | High security (banking) |
| `Lax` | Sent on top-level navigation GET only | General use (recommended) |
| `None; Secure` | Always sent (requires Secure flag) | Cross-site APIs (OAuth) |

### Synchronizer Token Pattern

```text
1. Server generates random token, stores in session
2. Token included in form as hidden field
3. On submit, server compares form token with session token
4. Reject if missing or mismatched
```

- Generate per-session, not per-request (usability vs security trade-off)
- Use cryptographically random tokens (≥128 bits)
- Do NOT rely solely on Referer/Origin header checking

---

## 2. XSS Prevention

### XSS Types

| Type | Vector | Persistence |
| --- | --- | --- |
| Reflected | URL parameters, search queries | Non-persistent |
| Stored | Database content, user profiles | Persistent |
| DOM-based | Client-side JS processing URL/input | Client-side only |

### Output Encoding by Context

| Context | Encoding | Example |
| --- | --- | --- |
| HTML body | HTML entity encoding | `<` → `&lt;` |
| HTML attribute | Attribute encoding + quote | `"` → `&quot;` |
| JavaScript | JavaScript encoding | `'` → `\x27` |
| URL parameter | Percent encoding | `<` → `%3C` |
| CSS value | CSS encoding | `\3C` |

### Defense Layers

1. **Input validation** — reject unexpected characters at API boundary
2. **Output encoding** — encode data when inserting into HTML/JS/CSS/URL context
3. **Content-Security-Policy** — restrict script sources
4. **HttpOnly cookies** — prevent session theft via XSS

### Content-Security-Policy

```text
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'nonce-{random}';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  font-src 'self';
  connect-src 'self' https://api.example.com;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
  report-uri /csp-report;
```

### CSP Migration Strategy

1. Start with `Content-Security-Policy-Report-Only` to monitor violations
2. Fix violations (inline scripts → nonce-based, inline styles → classes)
3. Switch to enforcing `Content-Security-Policy`
4. Tighten directives over time

---

## 3. SQL Injection Defense

### Parameterized Queries

```kotlin
// SAFE — parameterized query
val users = jdbcTemplate.query(
    "SELECT * FROM users WHERE email = ? AND status = ?",
    arrayOf(email, status)
) { rs, _ -> mapUser(rs) }

// UNSAFE — string concatenation
val users = jdbcTemplate.query(
    "SELECT * FROM users WHERE email = '$email'"  // NEVER DO THIS
) { rs, _ -> mapUser(rs) }
```

### ORM Safety

```kotlin
// SAFE — JPA parameterized
@Query("SELECT u FROM User u WHERE u.email = :email")
fun findByEmail(@Param("email") email: String): User?

// SAFE — Exposed DSL (inherently parameterized)
Users.selectAll().where { Users.email eq email }

// UNSAFE — native query with concatenation
@Query("SELECT * FROM users WHERE email = '$email'", nativeQuery = true)  // NEVER
```

### Defense Rules

- Always use parameterized queries or ORM — never concatenate user input into SQL
- Validate input type and format at API boundary (reject unexpected characters)
- Use database accounts with least-privilege permissions
- Enable SQL query logging in non-production for detection
- Use Web Application Firewall (WAF) as additional layer

---

## 4. SSRF Prevention

### Attack Mechanism

```text
1. Application accepts URL as input (e.g., webhook URL, image URL)
2. Attacker provides internal URL (http://169.254.169.254/latest/meta-data/)
3. Server fetches the URL, exposing internal resources
```

### Defense Strategies

| Strategy | Implementation |
| --- | --- |
| URL allowlist | Only permit known-safe domains |
| IP denylist | Block private ranges, loopback, link-local, metadata endpoints |
| DNS resolution validation | Resolve DNS first, then check IP before connecting |
| Network segmentation | Outbound proxy with allowlisted destinations |
| Disable redirects | Prevent redirect to internal addresses |

### IP Ranges to Block

```text
# Private networks
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16

# Loopback
127.0.0.0/8

# Link-local
169.254.0.0/16

# Cloud metadata endpoints
169.254.169.254/32    # AWS, GCP, Azure (IMDS)
fd00:ec2::254/128      # AWS IMDSv2 IPv6
```

### Validation Pattern

```text
1. Parse URL — reject malformed URLs
2. Validate scheme — allow only https (and http if needed)
3. Resolve DNS — get IP address
4. Check IP against denylist — reject private/reserved ranges
5. Make request with timeout — prevent slow-loris
6. Validate response — check content type, size limits
```

---

## 5. TLS Configuration

### Minimum Requirements

| Setting | Requirement |
| --- | --- |
| TLS version | ≥ TLS 1.2 (prefer TLS 1.3) |
| Certificate key size | RSA ≥ 2048 bits, ECDSA ≥ 256 bits |
| Cipher suites | AEAD only (AES-GCM, ChaCha20-Poly1305) |
| Certificate transparency | Required for public certificates |
| OCSP stapling | Enabled for revocation checking |

### Recommended Cipher Suites

```text
# TLS 1.3 (all are strong — no configuration needed)
TLS_AES_256_GCM_SHA384
TLS_CHACHA20_POLY1305_SHA256
TLS_AES_128_GCM_SHA256

# TLS 1.2 (restrict to AEAD suites)
TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256
TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256
```

### HSTS Configuration

```text
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

- Set `max-age` to at least 1 year (31536000 seconds)
- Include `includeSubDomains` to protect all subdomains
- Add `preload` only after thorough testing — removal is difficult
- Submit to HSTS preload list for browser-level enforcement

---

## 6. Content Security Policy

### Directive Reference

| Directive | Purpose | Example |
| --- | --- | --- |
| `default-src` | Fallback for all resource types | `'self'` |
| `script-src` | JavaScript sources | `'self' 'nonce-abc123'` |
| `style-src` | CSS sources | `'self' 'unsafe-inline'` |
| `img-src` | Image sources | `'self' data: https:` |
| `connect-src` | XHR, WebSocket, fetch targets | `'self' https://api.example.com` |
| `font-src` | Font file sources | `'self'` |
| `frame-ancestors` | Pages that can embed this page | `'none'` (replaces X-Frame-Options) |
| `form-action` | Form submission targets | `'self'` |
| `base-uri` | Allowed `<base>` URLs | `'self'` |
| `upgrade-insecure-requests` | Upgrade HTTP to HTTPS | (no value needed) |
| `report-uri` / `report-to` | Violation reporting endpoint | `/csp-report` |

### Nonce-Based Script Allowlisting

```html
<!-- Server generates unique nonce per response -->
<script nonce="abc123">
  // This script is allowed
</script>

<!-- CSP header -->
Content-Security-Policy: script-src 'nonce-abc123'
```

- Generate cryptographically random nonce per response
- Never reuse nonces across responses
- Nonce-based is preferred over hash-based for dynamic content

### Report-Only Mode for Migration

```text
Content-Security-Policy-Report-Only:
  default-src 'self';
  script-src 'self';
  report-uri /csp-report;
```

- Deploy in report-only mode first to identify violations
- Fix violations: move inline scripts to external files, add nonces
- Monitor violation reports for 1-2 weeks
- Switch to enforcing mode after zero/minimal violations
