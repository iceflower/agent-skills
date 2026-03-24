---
name: api-versioning
description: >-
  API versioning strategies and lifecycle management including URL path,
  header, and content negotiation versioning, breaking change classification,
  deprecation policies (RFC 9745, RFC 8594), API lifecycle stages,
  evolution patterns (expand-and-contract, tolerant reader), and
  API gateway version routing.
  Use when designing API versioning strategies, managing breaking changes,
  planning deprecation timelines, or implementing version routing.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# API Versioning Rules

## 1. Versioning Strategy Selection

### Strategy Comparison

| Strategy | Caching | Routing | Gateway Support | Example |
| --- | --- | --- | --- | --- |
| URL path | Excellent (URL-based key) | Simple | All gateways | `/v1/users` |
| Query parameter | Needs care (cache key) | Simple | Most gateways | `/users?version=1` |
| Custom header | Good (Vary header) | Medium | Config needed | `Api-Version: 2` |
| Content negotiation | Good (Vary: Accept) | Complex | Limited | `Accept: application/vnd.api.v1+json` |
| Date-based | Good | Medium | Config needed | `Stripe-Version: 2024-09-30` |

### Decision Guide

- **Default choice**: URL path versioning — simplest, most widely understood
- **When to use header versioning**: Same resource, multiple representations;
  fine-grained version control needed; internal APIs
- **When to use date-based**: Frequent incremental changes; need account-level
  version pinning (like Stripe)
- **When to use content negotiation**: Strict REST/HATEOAS; limited use cases

### Rules

- Expose only major version externally (e.g., `/v1/`, `/v2/`)
- Minor/patch versions are internal — transparent to clients
- Never run more than 2-3 major versions concurrently
- Set a sunset date when releasing a new major version

## 2. Breaking vs Compatible Changes

### Breaking Changes (require new major version)

| Category | Examples |
| --- | --- |
| Removal | Remove field, endpoint, enum value, HTTP method |
| Type change | Change field type (string → int), rename field |
| Constraint tightening | Make optional field required, reduce allowed values |
| Semantic change | Change meaning/algorithm of existing field |
| Auth escalation | Require higher permissions for existing endpoint |
| Default value change | Change default behavior clients depend on |

### Grey Area (may be breaking depending on clients)

| Change | Risk | Mitigation |
| --- | --- | --- |
| Add new enum value | Breaks exhaustive switch | Document enums as extensible |
| Change error codes | Breaks error handling | Version error responses |
| Change sort order | Breaks position-dependent clients | Document ordering contract |
| Add required header | Breaks existing integrations | Make optional with fallback first |
| Add required field to request body | Existing clients get 400 errors | Make optional with default, or new version |

### Backward Compatible Changes (safe without version bump)

- Add new endpoint
- Add optional request parameter
- Add field to response body (requires Tolerant Reader clients)
- Add new HTTP method to existing resource
- Relax validation rules
- Add optional header

## 3. Deprecation Policy

### HTTP Headers (RFC 9745 + RFC 8594)

```http
HTTP/1.1 200 OK
Deprecation: @1688169599
Sunset: Sun, 30 Jun 2024 23:59:59 GMT
Link: <https://api.example.com/v2/migration>; rel="successor-version"
Link: <https://api.example.com/deprecation-policy>; rel="deprecation"
```

| Header | RFC | Format | Purpose |
| --- | --- | --- | --- |
| `Deprecation` | RFC 9745 | Unix timestamp (`@1688169599`) | When deprecated |
| `Sunset` | RFC 8594 | HTTP-date | When it will stop working |
| `Link` rel="successor-version" | — | URL | Where to migrate |
| `Link` rel="deprecation" | RFC 9745 | URL | Deprecation details |

- Sunset date MUST NOT be earlier than Deprecation date
- Past Deprecation date = already deprecated
- Future Deprecation date = advance notice

### Deprecation Timeline

| Phase | Timing | Action |
| --- | --- | --- |
| Announce | D-12 months | Docs, email, dashboard notification |
| Deprecation header | D-6 months | Add `Deprecation` header to responses |
| Migration guide | D-6 months | Publish migration documentation |
| Usage monitoring | D-3 months | Track old version usage, contact lagging consumers |
| Sunset header | D-3 months | Add `Sunset` header with final date |
| Rate limiting | D-1 month | Gradually reduce rate limits (optional) |
| Retirement | D-day | Return `410 Gone` or `301 Redirect` |

### Deprecation Rules

- Never remove an API version without the full deprecation process
- Minimum deprecation period: 6 months for public APIs, 3 months for internal
- Monitor usage metrics before retirement — contact active consumers
- Provide machine-readable deprecation info (headers) alongside human-readable (docs)

## 4. API Lifecycle

| Stage | Stability | Breaking Changes | SLA | Production Use |
| --- | --- | --- | --- | --- |
| **Alpha** | None | Anytime | No support | Not recommended |
| **Beta** | Limited | With notice | Limited | Conditional |
| **GA** | Full | Major version only | Full SLA | Recommended |
| **Deprecated** | Frozen | None (frozen) | Maintenance only | Migrate away |
| **Retired** | None | N/A | No support | Unavailable (410) |

### Stage Transition Requirements

- **Alpha → Beta**: Design review complete, basic documentation
- **Beta → GA**: Compatibility policy defined, performance tested, SLA defined
- **GA → Deprecated**: Successor exists, migration guide provided, 6-12 month notice
- **Deprecated → Retired**: Usage below threshold, sunset date passed

## 5. API Evolution Patterns

### Expand-and-Contract

Safely introduce breaking changes in three phases:

1. **Expand**: Add new field/endpoint alongside existing one (both work)
2. **Migrate**: Clients switch to new field/endpoint (monitor progress)
3. **Contract**: Remove old field/endpoint (after all clients migrated)

```text
# Example: Split fullName into firstName + lastName

Phase 1 (Expand):
  { "fullName": "John Doe", "firstName": "John", "lastName": "Doe" }

Phase 2 (Migrate):
  Clients switch to firstName/lastName. Monitor fullName usage → 0.

Phase 3 (Contract):
  { "firstName": "John", "lastName": "Doe" }
```

### Tolerant Reader

Client-side defensive design:

- Ignore unknown fields (never fail on extra data)
- Use defaults for missing fields
- Do not depend on field ordering
- Use lenient deserialization (e.g., `@JsonIgnoreProperties(ignoreUnknown = true)`)

### Additive-Only Strategy

- Add new features as new fields/endpoints only
- Never remove or modify existing fields
- Avoids major version bumps for extended periods
- Trade-off: API surface grows over time

## 6. Implementation Patterns

For detailed implementation examples, see
[references/implementation-patterns.md](references/implementation-patterns.md).

### Spring Framework 7 / Spring Boot 4+

> Note: Requires Spring Boot 4.0+ (Spring Framework 7). Not available in Boot 3.x.

```java
@Configuration
public class WebConfig implements WebMvcConfigurer {
    @Override
    public void configureApiVersioning(ApiVersionConfigurer configurer) {
        configurer.useRequestHeader("Api-Version");
    }
}

@RestController
@RequestMapping("/accounts")
public class AccountController {
    @GetMapping(path = "/{id}", version = "1")
    public AccountV1 getV1(@PathVariable Long id) { /* ... */ }

    @GetMapping(path = "/{id}", version = "2")
    public AccountV2 getV2(@PathVariable Long id) { /* ... */ }
}
```

### Express.js

```javascript
app.use("/api/v1", v1Router);
app.use("/api/v2", v2Router);
```

## 7. API Gateway Version Routing

Route versions at the gateway layer to decouple backend services.

```text
Client → API Gateway → /v1/* → Backend v1 (port 8081)
                     → /v2/* → Backend v2 (port 8082)
```

### Benefits

- Backend services don't need version routing logic
- Independent deployment and scaling per version
- Combine with canary deployment for gradual version transitions
- Centralized rate limiting and monitoring per version

### Gateway-Specific Patterns

| Gateway | Versioning Approach |
| --- | --- |
| Kong | Route objects with path/header matching |
| AWS API Gateway | Stages + resource paths, canary support |
| Nginx | Location blocks with proxy_pass |
| Envoy | Route match rules, weighted clusters |

## 8. Common Anti-Patterns

| Anti-Pattern | Problem | Fix |
| --- | --- | --- |
| No versioning at all | Any change risks breaking clients | Version from day one |
| Too many concurrent versions | Maintenance burden | Max 2-3 active versions |
| Breaking change without version bump | Client breakage | Follow breaking change rules |
| Skipping deprecation process | Surprise removal | Full deprecation timeline |
| Version in every URL segment | `/v1/users/v2/orders` | Single version at API root |
| Over-versioning (new version for minor changes) | Unnecessary migrations | Use additive changes |
| Client-specific versions | Unmaintainable | Use feature flags instead |
| No usage monitoring before retirement | Active consumers cut off | Track and notify |
