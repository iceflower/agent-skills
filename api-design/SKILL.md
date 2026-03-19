---
name: api-design
description: >-
  REST API design principles including URL design, HTTP methods, status codes,
  pagination, versioning, security, and OpenAPI documentation.
  Use when designing or implementing REST APIs.
---

# REST API Design Rules

## 1. URL Design

### Basic Principles

- Use **nouns**, not verbs, to represent resources
- Use **plural forms** instead of singular
- Use **kebab-case** for URL paths (lowercase with hyphens)
- Represent **hierarchical relationships** in the URL structure

### URL Patterns

```text
# Resource collection
GET    /users                  # List users
POST   /users                  # Create user

# Specific resource
GET    /users/{id}             # Get specific user
PUT    /users/{id}             # Full update
PATCH  /users/{id}             # Partial update
DELETE /users/{id}             # Delete user

# Sub-resources
GET    /users/{id}/orders      # List user's orders
POST   /users/{id}/orders      # Create order for user
GET    /users/{id}/orders/{orderId}  # Get specific order

# Actions (when noun representation is difficult)
POST   /users/{id}/password-reset   # Reset password
POST   /orders/{id}/cancel          # Cancel order
```

### Anti-Patterns

```text
# Bad examples
GET    /getUsers
POST   /createUser
DELETE /deleteUser/123
GET    /user              # singular form
GET    /Users             # uppercase
GET    /user_orders       # snake_case

# Good examples
GET    /users
POST   /users
DELETE /users/123
```

---

## 2. HTTP Methods

### Method Usage

| Method  | Purpose         | Idempotent | Safe | Request Body |
| ------- | --------------- | ---------- | ---- | ------------ |
| GET     | Retrieve        | Yes        | Yes  | No           |
| POST    | Create          | No         | No   | Yes          |
| PUT     | Full Update     | Yes        | No   | Yes          |
| PATCH   | Partial Update  | No         | No   | Yes          |
| DELETE  | Remove          | Yes        | No   | No           |

### Idempotency

- **Idempotent**: Multiple identical requests produce the same result
- GET, PUT, DELETE must guarantee idempotency
- POST is not idempotent → duplicate creation prevention logic required

---

## 3. HTTP Status Codes

### Success (2xx)

| Code | Meaning       | Use Case                       |
| ---- | ------------- | ------------------------------ |
| 200  | OK            | General success                |
| 201  | Created       | Resource created successfully  |
| 202  | Accepted      | Async processing started       |
| 204  | No Content    | Success with no response body  |

### Redirection (3xx)

| Code | Meaning             | Use Case                      |
| ---- | ------------------- | ----------------------------- |
| 301  | Moved Permanently   | Resource permanently moved    |
| 302  | Found               | Temporary redirect            |
| 304  | Not Modified        | Cached resource unchanged     |

### Client Errors (4xx)

| Code | Meaning               | Use Case                |
| ---- | --------------------- | ----------------------- |
| 400  | Bad Request           | Invalid request format  |
| 401  | Unauthorized          | Authentication required |
| 403  | Forbidden             | No permission           |
| 404  | Not Found             | Resource not found      |
| 409  | Conflict              | Resource conflict       |
| 422  | Unprocessable Entity  | Validation failed       |
| 429  | Too Many Requests     | Rate limit exceeded     |

### Server Errors (5xx)

| Code | Meaning               | Use Case                  |
| ---- | --------------------- | ------------------------- |
| 500  | Internal Server Error | Server internal error     |
| 502  | Bad Gateway           | Upstream server error     |
| 503  | Service Unavailable   | Service temporarily down  |
| 504  | Gateway Timeout       | Upstream server timeout   |

---

## 4. Request/Response Format

### Request Headers

```http
Content-Type: application/json
Accept: application/json
Authorization: Bearer <token>
X-Request-ID: <uuid>
```

### Response Format - Success

```json
{
  "data": {
    "id": "user-001",
    "email": "user@example.com",
    "name": "John Doe"
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:45.123Z",
    "requestId": "abc-123"
  }
}
```

### Response Format - List

```json
{
  "data": [
    { "id": "user-001", "name": "John Doe" },
    { "id": "user-002", "name": "Jane Doe" }
  ],
  "meta": {
    "total": 100,
    "page": 1,
    "perPage": 20,
    "totalPages": 5
  }
}
```

### Response Format - Error

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:45.123Z",
    "requestId": "abc-123"
  }
}
```

---

## 5. Pagination

### Pagination Strategy Selection

| Method | Pros                      | Cons                    | Best For          |
| ------ | ------------------------- | ----------------------- | ----------------- |
| Offset | Simple, easy page nav     | Slow on large datasets  | Small datasets    |
| Cursor | Fast, consistent          | No page navigation      | Large datasets    |
| Keyset | Fast                      | Fixed sort key          | Fixed sort order  |

---

## 6. Filtering, Sorting, Field Selection

```text
# Filtering
GET /users?status=active&role=admin

# Sorting
GET /users?sort=-createdAt         # descending
GET /users?sort=name,-createdAt    # multiple sort

# Field Selection
GET /users?fields=id,name,email
```

---

## 7. API Versioning

> **See [references/versioning.md](references/versioning.md) for detailed patterns including:**
> - Version identification strategies (URL, Header, Custom)
> - Compatibility principles (safe vs breaking changes)
> - Handling breaking changes and deprecation

---

## 8. Security

- All APIs must be served over HTTPS only
- Never include sensitive data in URLs — use request body
- Implement rate limiting with `X-RateLimit-*` headers

---

## 9. Documentation

> **See [references/documentation.md](references/documentation.md) for detailed patterns including:**
> - OpenAPI specification structure
> - Schema and parameter documentation
> - Error response documentation
> - Authentication documentation

---

## 10. References

- [Semantic Versioning Specification](https://semver.org/) — Industry standard for version numbering
- [RFC 7231 (HTTP/1.1 Semantics and Content)](https://datatracker.ietf.org/doc/html/rfc7231) — HTTP methods and content negotiation
- [RFC 8594 (The Sunset HTTP Header Field)](https://datatracker.ietf.org/doc/html/rfc8594) — API deprecation notification standard
- [Microsoft REST API Guidelines - Versioning](https://github.com/microsoft/api-guidelines/blob/vNext/Guidelines.md) — Large-scale API versioning practices
- [Google Cloud API Design Guide](https://cloud.google.com/apis/design) — API compatibility and versioning guide
- [Pact Contract Testing](https://docs.pact.io/) — Consumer-Driven Contract Testing framework
