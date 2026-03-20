# Authentication and Authorization Patterns

## 1. Token-Based Authentication

### JWT Structure

```text
Header.Payload.Signature

Header:  { "alg": "RS256", "typ": "JWT", "kid": "key-id-1" }
Payload: { "sub": "user-123", "iss": "auth.example.com", "exp": 1700000000, "roles": ["user"] }
Signature: RS256(base64(header) + "." + base64(payload), privateKey)
```

### Signing Algorithm Selection

| Algorithm | Type | Key | Use Case |
| --- | --- | --- | --- |
| RS256 | Asymmetric | RSA 2048+ | Multi-service verification (recommended) |
| ES256 | Asymmetric | ECDSA P-256 | Smaller tokens, modern systems |
| HS256 | Symmetric | Shared secret | Single-service, simple setups |
| EdDSA | Asymmetric | Ed25519 | High performance, modern systems |

- **Prefer asymmetric** (RS256, ES256) — provider signs, consumers verify with public key
- **Avoid HS256** in distributed systems — shared secret increases attack surface
- Always set `kid` (Key ID) header for key rotation support

### Token Validation Checklist

1. Verify signature with trusted public key
2. Check `exp` (expiration) — reject expired tokens
3. Check `iss` (issuer) — match expected issuer
4. Check `aud` (audience) — match expected audience
5. Check `nbf` (not before) — reject tokens not yet valid
6. Validate required claims for business logic (roles, scopes)

### Refresh Token Rotation

```text
1. Client authenticates → receives access token (15min) + refresh token (7d)
2. Access token expires → client sends refresh token
3. Server issues new access token + NEW refresh token
4. Old refresh token is invalidated (one-time use)
5. If old refresh token is reused → revoke entire token family (breach detected)
```

### Token Revocation Strategies

| Strategy | Latency | Complexity | Best For |
| --- | --- | --- | --- |
| Short-lived tokens (5-15min) | Eventual | Low | Most APIs |
| Token blacklist (Redis) | Immediate | Medium | Logout, compromised tokens |
| Token versioning (user-level) | Immediate | Medium | Password change, account lock |
| Introspection endpoint | Real-time | High | High-security applications |

---

## 2. OAuth 2.0 Flows

### Flow Selection

| Flow | Client Type | Use Case |
| --- | --- | --- |
| Authorization Code + PKCE | SPA, mobile, server-side | User-facing apps (recommended) |
| Client Credentials | Machine-to-machine | Service accounts, batch jobs |
| Device Authorization | Smart TV, IoT, CLI | Limited input devices |

### Authorization Code + PKCE

```text
1. Client generates code_verifier (random string) and code_challenge (SHA256 hash)
2. Client redirects user to authorization server with code_challenge
3. User authenticates and authorizes
4. Authorization server returns authorization code
5. Client exchanges code + code_verifier for tokens
6. Server verifies SHA256(code_verifier) == code_challenge
```

### Security Considerations

| Concern | Mitigation |
| --- | --- |
| Token interception | Use HTTPS everywhere, short-lived tokens |
| CSRF | Use `state` parameter, validate on callback |
| Open redirect | Validate redirect_uri against registered URIs |
| Token leakage | Store tokens in memory (SPA) or secure httpOnly cookies |
| Scope escalation | Request minimum scopes, validate server-side |

---

## 3. Session Management

### Session Security Rules

| Rule | Implementation |
| --- | --- |
| Secure session ID generation | Cryptographically random, ≥128 bits entropy |
| Transport security | `Secure` flag on cookies (HTTPS only) |
| Script protection | `HttpOnly` flag (no JavaScript access) |
| CSRF protection | `SameSite=Lax` or `SameSite=Strict` |
| Absolute timeout | Max session lifetime (e.g., 8 hours) |
| Idle timeout | Expire after inactivity (e.g., 30 minutes) |
| Session fixation prevention | Regenerate session ID after authentication |

### Cookie Configuration

```text
Set-Cookie: session_id=<value>;
  Path=/;
  Secure;
  HttpOnly;
  SameSite=Lax;
  Max-Age=28800;
  Domain=.example.com
```

### Concurrent Session Control

- Define maximum concurrent sessions per user (e.g., 5)
- On limit exceeded: deny new session or terminate oldest
- Provide users visibility into active sessions
- Force logout from all sessions on password change

---

## 4. Multi-Factor Authentication

### Method Comparison

| Method | Security | UX | Phishing Resistant |
| --- | --- | --- | --- |
| WebAuthn/FIDO2 | Very High | Good | Yes |
| TOTP (Authenticator app) | High | Medium | No |
| SMS OTP | Medium | Easy | No |
| Email OTP | Medium | Easy | No |
| Push notification | High | Good | Partial |

### Implementation Rules

- Offer WebAuthn/FIDO2 as primary MFA method
- TOTP as fallback for devices without biometric support
- Avoid SMS as sole MFA — SIM swap attacks
- Generate recovery codes (10 single-use codes) during MFA setup
- Store recovery codes hashed (same as passwords)
- Rate limit MFA attempts (5 failures → temporary lockout)

---

## 5. Password Security

### Hashing Algorithm Selection

| Algorithm | Recommended | Memory | CPU Cost | Notes |
| --- | --- | --- | --- | --- |
| Argon2id | Yes (preferred) | Configurable | Configurable | Resistant to GPU/ASIC attacks |
| bcrypt | Yes | 4 KB | Configurable | Widely supported, 72-byte limit |
| scrypt | Yes | Configurable | Configurable | Good GPU resistance |
| PBKDF2 | Acceptable | Low | Configurable | FIPS-140 compliant |
| SHA-256/MD5 | Never | — | — | No key stretching |

### Work Factor Guidelines

| Algorithm | Recommended Parameters |
| --- | --- |
| Argon2id | `m=65536, t=3, p=4` (64MB, 3 iterations, 4 threads) |
| bcrypt | Cost factor 12 (adjust for ~250ms hash time) |
| scrypt | `N=2^15, r=8, p=1` |

### Password Policy

- Minimum 8 characters, no maximum (allow passphrases)
- Check against breached password lists (Have I Been Pwned API)
- Do NOT enforce composition rules (uppercase, symbols) — NIST 800-63B
- Allow all Unicode characters and spaces
- Show password strength meter (zxcvbn or similar)

---

## 6. API Authentication

### Method Comparison

| Method | Security | Complexity | Use Case |
| --- | --- | --- | --- |
| OAuth2 Bearer Token | High | Medium | User-context API calls |
| API Key (header) | Medium | Low | Service-to-service, public APIs |
| mTLS | Very High | High | Service mesh, zero-trust |
| HMAC Signature | High | Medium | Webhooks, AWS-style signing |

### API Key Best Practices

- Prefix keys for identification: `sk_live_`, `pk_test_`
- Hash stored keys (SHA-256) — never store plaintext
- Support multiple active keys per account (for rotation)
- Include key metadata: created date, last used, scopes
- Log key usage for audit trail
- Rate limit per key, not just per IP

### mTLS Pattern

```text
1. Both client and server have TLS certificates
2. During TLS handshake, server verifies client certificate
3. Client certificate maps to service identity
4. Authorization based on service identity (not network location)
```

- Use in service mesh (Istio, Linkerd) for automatic mTLS
- For manual mTLS: use internal CA, rotate certificates regularly
- Validate certificate chain, check revocation (CRL/OCSP)
