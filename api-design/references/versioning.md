# API Versioning

API는 서비스 간 계약 역할을 하며, 변경 시 기존 클라이언트가 영향을 받지 않도록 신중한 계획이 필요합니다.

## Version Identification Strategies

### URL Path Versioning

**Method**: Add version identifier prefix or query parameter to URL.

```text
https://api.example.com/v1/users
https://api.example.com/v2/users
https://api.example.com/users?version=1
```

**Pros**:

- Easy route branching
- URLs easy to share, save, email
- Can view version consumption via logs
- Users can see which version they're using at a glance

**Cons**:

- Same resource appears as different resources (serious issue in REST world)

### HTTP Header Versioning (Accept/Content-Type)

**Method**: Use `Accept` header for requests, `Content-Type` for responses.

```text
Accept: application/vnd.example.user.v1+json
Accept: application/vnd.example.user.v2+json
```

**Pros**:

- All stored URLs remain valid
- Clients can upgrade versions without changing paths

**Cons**:

- Can't identify version from URL alone
- Generic media types like `application/json` or `text/xml` don't help
- Clients must know special media types exist and their allowed range

### Custom Header Versioning

**Method**: Define application-specific header.

```text
api-version: 1
api-version: 2
```

**Pros**:

- Completely flexible
- Orthogonal to media types and URLs (no interference)

**Cons**:

- Need framework-specific route branching code
- Another piece of secret knowledge to share with service consumers

### Request Body Field Versioning

**Method**: Add field in request body to indicate intended version (PUT/POST only).

**Pros**:

- Simple for write operations

**Cons**:

- Only works for PUT/POST
- Not applicable for GET requests

## Compatibility Principles

### Postel's Robustness Principle

> "Be conservative in what you send, be liberal in what you accept."

- **Covariant requests**: Accept more than required
- **Contravariant responses**: Return less than or equal to promised

### Safe Changes (Always Compatible)

Changes that never break compatibility:

| Safe Change                                         | Example                                              |
| --------------------------------------------------- | ---------------------------------------------------- |
| Require a **subset** of previously required parameters | Made optional parameter required → now optional again |
| Accept a **superset** of previously accepted parameters | Add new optional parameter                          |
| Return a **superset** of previously returned values    | Add new response field                              |
| Require a **subset** of previous constraints           | Loosen validation rules                             |

### Breaking Changes (Never Compatible)

Changes that always break compatibility:

| Breaking Change                                    | Example                                                 |
| -------------------------------------------------- | ------------------------------------------------------- |
| Reject previously accepted optional information    | Was accepting `nickname`, now rejecting it              |
| Remove previously guaranteed response information  | Was returning `email`, now removing it                  |
| Require higher privilege level                     | Was allowing `user` role, now requiring `admin`         |

## Compatibility Problem Example

A service receives JSON with a URL field:

1. **Initial**: Accepts any string, stores in database without URL validation
2. **Change**: Adds regex-based URL validation
3. **Problem**: Previously valid requests now rejected → **Compatibility broken**

**Solution**:

- Use database migration to fix existing invalid URLs
- Or accept that some historical data doesn't meet new standards
- Version the validation rules if clients depend on old behavior

## Handling Breaking Changes

### Version Bump Strategy

When breaking changes are unavoidable:

1. **Create new version** (v2) alongside old version (v1)
2. **Both versions coexist** during transition period
3. **Deprecate old version** with clear timeline
4. **Remove old version** after transition period

### Version Lifecycle

```text
v1 Released → v1 Stable → v2 Released → v1 Deprecated → v1 Sunset → v1 Removed
                                     (6 months)        (3 months)    (EOL)
```

### Deprecation Notice

Include in API responses:

```http
HTTP/1.1 200 OK
Deprecation: true
Sunset: Sat, 01 Jul 2024 00:00:00 GMT
Link: </v2/users>; rel="successor-version"
```

## Contract Testing

Verify that both provider and consumer sides honor the API contract.

```text
┌─────────────────┐         ┌─────────────────┐
│   Consumer      │         │    Provider     │
│   Test Code     │         │   Test Code     │
└────────┬────────┘         └────────┬────────┘
         │                           │
         ▼                           ▼
┌─────────────────────────────────────────────┐
│              Contract (Pact)                 │
│         - Request expectations              │
│         - Response expectations             │
└─────────────────────────────────────────────┘
```

**Benefits**:

- Test without real external service calls
- Catch breaking changes before deployment
- Verify both sides independently

## Versioning Other Services

### When You're the Consumer

| Situation                                  | Response                         |
| ------------------------------------------ | -------------------------------- |
| External service announces deprecation     | Plan migration immediately       |
| External service breaks compatibility      | Have fallback strategies         |
| External service unavailable               | Circuit breakers, fallbacks      |

- Document all external service versions used
- Track deprecation timelines
- Maintain version compatibility matrix

## Versioning Checklist

### Before Making Changes

- [ ] Is this change backward compatible?
- [ ] If breaking, is a new version necessary?
- [ ] Have existing clients been notified?
- [ ] Is there a transition timeline?

### When Releasing New Version

- [ ] Old version still available during transition?
- [ ] Documentation updated for both versions?
- [ ] Deprecation notices included in responses?
- [ ] Migration guide provided for clients?

### When Removing Old Version

- [ ] All clients migrated?
- [ ] Sunset date passed?
- [ ] Monitoring shows no traffic to old version?