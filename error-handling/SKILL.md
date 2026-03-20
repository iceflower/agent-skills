---
name: error-handling
description: >-
  Framework-agnostic error handling patterns including exception hierarchy,
  error classification, response format, and handling principles.
  Use when designing error handling strategies.
---
# Error Handling Rules

## 1. Exception Hierarchy

### Business vs System Exceptions

| Category           | Characteristics                    | HTTP Status Range | Log Level    |
| ------------------ | ---------------------------------- | ----------------- | ------------ |
| Business exception | Expected, recoverable by caller    | 4xx               | WARN or INFO |
| System exception   | Unexpected, programming bug or I/O | 5xx               | ERROR        |

### Error Classification

| Type           | Examples                             | Recommended Action              |
| -------------- | ------------------------------------ | ------------------------------- |
| Recoverable    | Invalid input, network timeout       | Signal to caller, allow retry   |
| Unrecoverable  | Programming bug, corrupted state     | Fail fast, log and alert        |
| External fault | Upstream API error, DNS failure      | Wrap in domain exception, retry |

---

## 2. Error Response Format

### Standard JSON Structure

```json
{
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "User not found: 42",
    "details": [
      {
        "field": "userId",
        "message": "No user exists with the given ID"
      }
    ]
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:45.123Z",
    "requestId": "abc-123-def"
  }
}
```

### Response Format Rules

- Use a consistent error envelope across all endpoints
- Include a machine-readable error code (not just HTTP status)
- Include a human-readable message for debugging
- Include field-level details for validation errors
- Include requestId/traceId for correlation

---

## 3. Exception Handling Principles

### Do

- Catch at the appropriate layer (controller for HTTP, service for business logic)
- Always include context in exception messages (entity name, ID, field)
- Log stack traces for system exceptions
- Use error code enums for consistent codes across the application
- Include traceId in error responses for debugging

### Do Not

- Catch exceptions broadly in service/repository layers
- Expose internal details (stack traces, SQL, class names) in API responses
- Use exceptions for flow control (e.g., throwing NotFoundException to check existence)
- Swallow exceptions silently (empty catch blocks)
- Log sensitive data in exception messages (passwords, tokens, PII)

---

## 4. Layer-Specific Guidelines

### Controller Layer

- Do not handle exceptions directly — delegate to a centralized exception handler
- Validate request inputs at the API boundary before passing to service layer

### Service Layer

- Throw business exception subtypes for business rule violations
- Wrap external API failures in domain-specific exceptions
- Use explicit try-catch only for recoverable operations

### Repository / Data Layer

- Let data access exceptions propagate to the service layer
- Do not catch data access exceptions unless specific recovery logic exists

---

## 5. External API Error Handling

### Principles

- Never let raw HTTP client exceptions propagate to callers
- Wrap in domain-specific exceptions (e.g., `PaymentApiException`)
- Log response status and body on errors (but mask sensitive data)
- Distinguish between retryable (network, 503) and non-retryable (400, 404) errors

### Error Wrapping Strategy

| Exception Source        | Cause               | Action                 |
| ----------------------- | ------------------- | ---------------------- |
| HTTP response error     | 4xx/5xx response    | Map to domain error    |
| Network/timeout error   | Connection failure  | Retry or circuit break |
| Parsing/decoding error  | Malformed response  | Log and fail           |

---

## 6. Anti-Patterns

- Catching generic `Exception` in every method
- Returning error details in success response fields
- Using HTTP 200 for all responses with error codes in body
- Inconsistent error response formats across endpoints
- Missing error codes (only HTTP status, no application code)
- Logging errors without stack traces
- Retrying on non-idempotent failures without safeguards
- **Pokemon Exception Handling**: 모든 예외를 잡는 catch-all 패턴. 구체적인 예외 타입으로 처리
- **에러 무시(Swallowing)**: 빈 catch 블록으로 에러를 삼키면 디버깅 불가능
- **에러를 흐름 제어로 사용**: 예외를 정상적인 프로그램 흐름 제어에 사용하면 성능 저하 및 가독성 하락

## Additional References

- [Microsoft Error Handling Best Practices](https://learn.microsoft.com/en-us/dotnet/standard/exceptions/best-practices-for-exceptions) - .NET 예외 처리 모범 사례
- [Effective Java - Exceptions](https://www.oreilly.com/library/view/effective-java/9780134686097/) - Java 예외 처리 가이드
- For Spring Boot implementation patterns (`@ControllerAdvice`, ErrorCode enum), see `spring-framework` skill — [references/error-handling.md](../spring-framework/references/error-handling.md)
