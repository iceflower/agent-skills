---
name: http-client
description: >-
  Framework-agnostic external API integration patterns including timeouts,
  error handling, retry strategy, circuit breaker, and response mapping.
  Use when writing or reviewing HTTP client code.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---
# External API Client Rules

## 1. Timeout Configuration Principles

### Recommended Defaults

| Setting          | Default | Description                |
| ---------------- | ------- | -------------------------- |
| Connect timeout  | 3s      | TCP connection setup       |
| Read timeout     | 10s     | Waiting for response body  |
| Write timeout    | 10s     | Sending request body       |
| Connection pool  | 20      | Max concurrent connections |
| Idle timeout     | 60s     | Idle connection lifetime   |

### Timeout Types Explained

| Timeout | What It Measures | Too Low | Too High |
| --- | --- | --- | --- |
| Connect timeout | TCP handshake + TLS negotiation | Fails on slow networks or cold starts | Threads blocked on unreachable hosts |
| Read timeout | Time to receive first/full response body | Fails on legitimate slow responses | Threads held waiting for hung services |
| Write timeout | Time to send request body | Fails on large uploads over slow links | Usually less critical than read timeout |

### Timeout Rules

- Always set explicit timeouts — never rely on defaults (which may be infinite)
- Set read timeout based on the slowest expected response from upstream
- Set connect timeout shorter than read timeout (connection should be fast; 1-5s typical)
- Write timeout matters primarily for large request bodies (file uploads, bulk data)
- Use shorter timeouts for non-critical calls
- Log timeout values at startup for debugging
- For downstream SLA compliance: set total timeout (connect + read) below your own SLA budget minus processing time

---

## 2. Error Handling Strategy

### Error Classification

| Exception Source        | Cause               | Action                 |
| ----------------------- | ------------------- | ---------------------- |
| HTTP response error     | 4xx/5xx response    | Map to domain error    |
| Network/timeout error   | Connection failure  | Retry or circuit break |
| Parsing/decoding error  | Malformed response  | Log and fail           |

### Error Handling Rules

- Never let raw HTTP client exceptions propagate to callers
- Wrap in domain-specific exceptions (e.g., `PaymentApiException`)
- Log response status and body on errors (but mask sensitive data)
- Distinguish between retryable (network, 503) and non-retryable (400, 404) errors

---

## 3. Retry Strategy

### Retry Decision Table

| Scenario           | Retry | Max Attempts | Backoff              |
| ------------------ | ----- | ------------ | -------------------- |
| Network timeout    | Yes   | 3            | Exponential 2x       |
| Connection refused | Yes   | 3            | Exponential 2x       |
| HTTP 429           | Yes   | 3            | Respect Retry-After  |
| HTTP 503           | Yes   | 3            | Exponential 2x       |
| HTTP 4xx (not 429) | No    | -            | -                    |
| Parsing error      | No    | -            | -                    |

### Exponential Backoff with Jitter

Exponential backoff prevents overwhelming a recovering service. Jitter prevents synchronized retry storms (thundering herd).

```text
Base formula:
  delay = min(base * 2^attempt, max_delay)

Full jitter (recommended — distributes retries evenly):
  delay = random(0, min(base * 2^attempt, max_delay))

Equal jitter (balanced between spread and minimum wait):
  temp = min(base * 2^attempt, max_delay)
  delay = temp/2 + random(0, temp/2)

Example with base=1s, max=30s:
  Attempt 1: random(0, 2s)
  Attempt 2: random(0, 4s)
  Attempt 3: random(0, 8s)
```

Reference: AWS Architecture Blog — [Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)

### Retry Principles

- Always use exponential backoff with jitter to avoid thundering herd
- Prefer full jitter over equal jitter or decorrelated jitter for most use cases
- Set a maximum retry count — never retry indefinitely
- Set a retry budget (e.g., max 20% of requests can be retries) to prevent retry amplification across service layers
- Do not retry inside a database transaction — retry at the outermost layer
- Do not retry non-idempotent requests without an idempotency key
- Ensure retried requests are safe: check that the upstream API is idempotent or use idempotency keys

---

## 4. Circuit Breaker Pattern

### When to Use

- External APIs with unpredictable latency or availability
- Non-critical dependencies where degraded operation is acceptable
- High-throughput paths where cascading failures are a risk

### Key Parameters

| Parameter                    | Description                              | Typical Value |
| ---------------------------- | ---------------------------------------- | ------------- |
| Sliding window size          | Number of calls to evaluate              | 10            |
| Failure rate threshold       | Percentage to open circuit               | 50%           |
| Wait duration in open state  | Cooldown before half-open                | 30s           |
| Half-open permitted calls    | Test calls before closing                | 3             |
| Slow call duration threshold | What counts as "slow"                    | 5s            |
| Slow call rate threshold     | Percentage of slow calls to open circuit | 80%           |

---

## 5. Response Mapping Principles

### DTO Separation

- Never expose external API DTOs to internal service layers
- Map external responses to domain models at the client boundary
- Handle missing/null fields defensively in external DTOs

### Mapping Example

```text
External API Response (their naming)     Domain Model (our naming)
─────────────────────────────────────    ──────────────────────────
user_id: String                    →     id: String
full_name: String                  →     name: String
email_address: String              →     email: String
```

---

## 6. Connection Pooling

### Why Connection Pooling Matters

Creating a new TCP connection (and TLS handshake) for every request adds 50-200ms of latency. Connection pools maintain reusable connections to amortize this cost.

### Pool Configuration Parameters

| Parameter | Description | Recommendation |
| --- | --- | --- |
| Max connections per host | Max concurrent connections to a single destination | 20-50 (match downstream capacity) |
| Max total connections | Total connections across all hosts | 100-200 for multi-host clients |
| Idle timeout | How long an idle connection is kept alive | 60-90s (match server/LB keep-alive) |
| Max connection lifetime | Max age of a connection regardless of activity | 5-10 minutes |
| Connection acquisition timeout | Max wait time when pool is exhausted | 5s (fail fast) |

### Connection Pool Pitfalls

| Pitfall | Consequence | Fix |
| --- | --- | --- |
| Pool too small for traffic | Requests queue up waiting for connections | Size pool based on peak concurrent requests per host |
| Pool too large | Wastes server resources, may exceed upstream connection limits | Right-size based on actual concurrency needs |
| No idle timeout | Stale connections cause errors | Set idle timeout shorter than server keep-alive |
| No max lifetime | DNS changes not picked up | Set max lifetime to force periodic reconnection |
| One pool for all APIs | Slow API exhausts pool, blocking fast APIs | Use separate pools (or separate clients) per downstream API |
| Ignoring keep-alive | Server closes connection but client reuses it | Respect `Connection: close` header, match keep-alive settings |

### Sizing Guidelines

```text
Pool size per host = peak_concurrent_requests_to_that_host * 1.5

Example:
  - Your service handles 1000 req/s
  - 30% of requests call Payment API (300 req/s)
  - Payment API avg response time: 200ms
  - Concurrent connections needed: 300 * 0.2 = 60
  - Pool size: 60 * 1.5 = 90
```

---

## 7. Anti-Patterns

- No timeout configuration (risk of thread exhaustion)
- Retrying non-idempotent requests (POST without idempotency key)
- Logging full response bodies in production (performance + data leak)
- Sharing a single HTTP client instance for unrelated APIs with different latency profiles
- Calling external APIs inside database transactions
- Ignoring rate limit headers from upstream APIs
- No circuit breaker on critical external dependencies
- Not setting connection pool idle/max lifetime (stale connections, DNS caching issues)
- Retry amplification across service layers (service A retries 3x, calls service B which retries 3x = 9 attempts)

## 8. Related Skills

- `error-handling`: HTTP error response handling strategies
- `monitoring`: HTTP client metrics collection and monitoring
- `security`: API authentication, TLS, header security
- `caching`: HTTP response caching strategies

## Additional References

- For circuit breaker, retry, timeout, and bulkhead resilience patterns, see [references/resilience-patterns.md](references/resilience-patterns.md)
- For Spring Boot implementation patterns (RestClient, Spring Retry, Resilience4j), see `spring-framework` skill — [references/http-client.md](../spring-framework/references/http-client.md)
