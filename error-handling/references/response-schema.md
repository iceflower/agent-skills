# Error Response Schema

Standardized error response formats, RFC 7807 Problem Details, and error code design guidelines.

## Overview

Consistent error responses are essential for API consumers to handle failures programmatically. This reference covers industry-standard error response formats, with emphasis on RFC 7807 (Problem Details for HTTP APIs) and practical error code design.

## RFC 7807: Problem Details for HTTP APIs

RFC 7807 defines a standard format for conveying machine-readable error details in HTTP responses.

### Standard Fields

```json
{
  "type": "https://api.example.com/problems/insufficient-funds",
  "title": "Insufficient Funds",
  "status": 422,
  "detail": "Account balance of $30.00 is insufficient for the $50.00 transaction.",
  "instance": "/transactions/abc-123"
}
```

| Field      | Type   | Required | Description                                         |
| ---------- | ------ | -------- | --------------------------------------------------- |
| `type`     | URI    | Yes      | URI identifying the problem type (use as error ID)  |
| `title`    | String | Yes      | Short, human-readable summary (same for all instances)|
| `status`   | Number | Yes      | HTTP status code                                    |
| `detail`   | String | No       | Human-readable explanation specific to this instance|
| `instance` | URI    | No       | URI reference to the specific occurrence             |

### Content Type

```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/problem+json

{
  "type": "https://api.example.com/problems/insufficient-funds",
  "title": "Insufficient Funds",
  "status": 422,
  "detail": "Account balance of $30.00 is insufficient for the $50.00 transaction."
}
```

### Extension Fields

RFC 7807 allows custom fields for additional context:

```json
{
  "type": "https://api.example.com/problems/validation-error",
  "title": "Validation Error",
  "status": 400,
  "detail": "The request contains invalid fields.",
  "errors": [
    {
      "field": "email",
      "code": "INVALID_FORMAT",
      "message": "Must be a valid email address"
    },
    {
      "field": "age",
      "code": "OUT_OF_RANGE",
      "message": "Must be between 18 and 120"
    }
  ]
}
```

## Implementation

### Spring Boot (RFC 7807)

Spring Framework 6+ has built-in RFC 7807 support:

```java
@RestControllerAdvice
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    @ExceptionHandler(InsufficientFundsException.class)
    public ProblemDetail handleInsufficientFunds(InsufficientFundsException ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
            HttpStatus.UNPROCESSABLE_ENTITY,
            ex.getMessage()
        );
        problem.setType(URI.create("https://api.example.com/problems/insufficient-funds"));
        problem.setTitle("Insufficient Funds");
        problem.setProperty("balance", ex.getBalance());
        problem.setProperty("required", ex.getRequired());
        return problem;
    }

    @ExceptionHandler(ResourceNotFoundException.class)
    public ProblemDetail handleNotFound(ResourceNotFoundException ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
            HttpStatus.NOT_FOUND,
            ex.getMessage()
        );
        problem.setType(URI.create("https://api.example.com/problems/resource-not-found"));
        problem.setTitle("Resource Not Found");
        return problem;
    }

    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex,
            HttpHeaders headers,
            HttpStatusCode status,
            WebRequest request) {

        ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.BAD_REQUEST);
        problem.setType(URI.create("https://api.example.com/problems/validation-error"));
        problem.setTitle("Validation Error");

        List<Map<String, String>> errors = ex.getBindingResult()
            .getFieldErrors().stream()
            .map(err -> Map.of(
                "field", err.getField(),
                "message", err.getDefaultMessage()
            ))
            .toList();

        problem.setProperty("errors", errors);
        return ResponseEntity.badRequest().body(problem);
    }
}
```

## Error Code Design

### Code Structure

Use a hierarchical, namespaced error code system:

```text
Format: <DOMAIN>-<CATEGORY>-<SPECIFIC>

Examples:
  ORDER-VALIDATION-INVALID_QUANTITY
  ORDER-PROCESSING-INSUFFICIENT_STOCK
  PAYMENT-AUTH-CARD_DECLINED
  PAYMENT-AUTH-EXPIRED_CARD
  AUTH-TOKEN-EXPIRED
  AUTH-TOKEN-INVALID_SCOPE
```

### Error Code Registry

Maintain a centralized registry of all error codes:

```java
public enum ErrorCode {
    // Order domain
    ORDER_NOT_FOUND("ORDER-001", "Order not found", HttpStatus.NOT_FOUND),
    ORDER_INVALID_STATUS("ORDER-002", "Invalid order status transition", HttpStatus.CONFLICT),
    ORDER_LINE_LIMIT("ORDER-003", "Maximum order line count exceeded", HttpStatus.BAD_REQUEST),

    // Payment domain
    PAYMENT_DECLINED("PAYMENT-001", "Payment declined", HttpStatus.PAYMENT_REQUIRED),
    PAYMENT_TIMEOUT("PAYMENT-002", "Payment processing timeout", HttpStatus.GATEWAY_TIMEOUT),

    // Auth domain
    AUTH_TOKEN_EXPIRED("AUTH-001", "Authentication token expired", HttpStatus.UNAUTHORIZED),
    AUTH_INSUFFICIENT_SCOPE("AUTH-002", "Insufficient permissions", HttpStatus.FORBIDDEN);

    private final String code;
    private final String defaultMessage;
    private final HttpStatus httpStatus;
}
```

## Common HTTP Status Code Mapping

| Status | Meaning                | When to Use                                     |
| ------ | ---------------------- | ----------------------------------------------- |
| 400    | Bad Request            | Malformed syntax, invalid parameters             |
| 401    | Unauthorized           | Missing or invalid authentication                |
| 403    | Forbidden              | Authenticated but insufficient permissions       |
| 404    | Not Found              | Resource does not exist                          |
| 409    | Conflict               | State conflict (duplicate, concurrent update)    |
| 422    | Unprocessable Entity   | Valid syntax but business rule violation          |
| 429    | Too Many Requests      | Rate limit exceeded                              |
| 500    | Internal Server Error  | Unexpected server error                          |
| 502    | Bad Gateway            | Upstream service failure                         |
| 503    | Service Unavailable    | Temporary overload or maintenance                |
| 504    | Gateway Timeout        | Upstream service timeout                         |

## Security Considerations

### Information Exposure

Never expose internal details in error responses:

```json
// BAD: Leaks internal information
{
  "error": "SQL Error: SELECT * FROM users WHERE id = '1; DROP TABLE users'"
}

// GOOD: Safe, actionable error
{
  "type": "https://api.example.com/problems/invalid-request",
  "title": "Invalid Request",
  "status": 400,
  "detail": "The provided user ID format is invalid."
}
```

### Error Response Checklist

- [ ] No stack traces in production responses
- [ ] No SQL queries or database details
- [ ] No internal class names or file paths
- [ ] No server infrastructure details
- [ ] No third-party service names or endpoints
- [ ] Rate-limited error responses to prevent enumeration attacks
- [ ] Consistent format for both 4xx and 5xx errors

## Client-Side Error Handling

```java
// Client consuming RFC 7807 responses
public <T> T executeRequest(HttpRequest request, Class<T> responseType) {
    HttpResponse<String> response = httpClient.send(request, BodyHandlers.ofString());

    if (response.statusCode() >= 400) {
        ProblemDetail problem = objectMapper.readValue(
            response.body(), ProblemDetail.class
        );

        return switch (response.statusCode()) {
            case 401, 403 -> throw new AuthenticationException(problem);
            case 404 -> throw new ResourceNotFoundException(problem);
            case 429 -> throw new RateLimitException(problem, getRetryAfter(response));
            case int s when s >= 500 -> throw new ServerException(problem);
            default -> throw new ApiException(problem);
        };
    }

    return objectMapper.readValue(response.body(), responseType);
}
```
