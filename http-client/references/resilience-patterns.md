# HTTP Client Resilience Patterns

Circuit breaker, retry, timeout, and bulkhead patterns for building resilient HTTP clients.

## Overview

HTTP clients in distributed systems must handle network failures, slow responses, and service outages gracefully. Resilience patterns prevent cascading failures and maintain system stability when downstream services are degraded or unavailable.

## Circuit Breaker

Prevents repeated calls to a failing service, allowing it time to recover.

### State Machine

```text
         success threshold met
┌────────────────────────────────────────────┐
│                                            │
▼         failure threshold          ┌───────┴──────┐
┌──────────┐   exceeded    ┌────────▶│  HALF-OPEN   │
│  CLOSED  │──────────────▶│  OPEN  │└──────────────┘
│(normal)  │               │(reject)│     │ failure
└──────────┘               │        │◀────┘
                           │        │
                           └────────┘
                        timeout expires
                         → try one request
```

### States

| State     | Behavior                                            |
| --------- | --------------------------------------------------- |
| CLOSED    | Requests pass through normally; failures counted    |
| OPEN      | Requests rejected immediately; no calls to service  |
| HALF-OPEN | One test request allowed; success closes, failure reopens |

### Resilience4j Configuration

```java
CircuitBreakerConfig config = CircuitBreakerConfig.custom()
    .failureRateThreshold(50)                     // Open at 50% failure rate
    .slowCallRateThreshold(80)                    // Open at 80% slow calls
    .slowCallDurationThreshold(Duration.ofSeconds(2))
    .waitDurationInOpenState(Duration.ofSeconds(30)) // Wait before half-open
    .permittedNumberOfCallsInHalfOpenState(3)     // Test requests in half-open
    .slidingWindowType(SlidingWindowType.COUNT_BASED)
    .slidingWindowSize(10)                        // Evaluate last 10 calls
    .minimumNumberOfCalls(5)                      // Min calls before evaluation
    .build();

CircuitBreaker circuitBreaker = CircuitBreaker.of("payment-service", config);
```

```java
// Usage with decorator
Supplier<PaymentResult> decorated = CircuitBreaker
    .decorateSupplier(circuitBreaker, () -> paymentClient.process(request));

try {
    PaymentResult result = decorated.get();
} catch (CallNotPermittedException e) {
    // Circuit is OPEN: return fallback
    return PaymentResult.pending("Service temporarily unavailable");
}
```

## Retry

Automatically retry failed requests for transient errors.

### Retry Strategy

```text
Request ──▶ Failure ──▶ Wait ──▶ Retry 1 ──▶ Failure ──▶ Wait ──▶ Retry 2 ──▶ Success
                        100ms                              200ms
```

### Configuration

```java
RetryConfig retryConfig = RetryConfig.custom()
    .maxAttempts(3)
    .waitDuration(Duration.ofMillis(500))
    .retryOnResult(response -> response.statusCode() == 503)
    .retryExceptions(IOException.class, TimeoutException.class)
    .ignoreExceptions(BusinessException.class)
    .intervalFunction(IntervalFunction.ofExponentialBackoff(
        Duration.ofMillis(500),  // initial interval
        2.0                       // multiplier
    ))
    .build();

Retry retry = Retry.of("payment-service", retryConfig);
```

### Backoff Strategies

| Strategy              | Formula                          | Use Case                    |
| --------------------- | -------------------------------- | --------------------------- |
| Fixed                 | `wait = constant`                | Predictable delays          |
| Exponential           | `wait = initial * 2^attempt`     | General purpose             |
| Exponential + jitter  | `wait = random(0, initial * 2^attempt)` | Avoid thundering herd |
| Linear                | `wait = initial * attempt`       | Gradual increase            |

```java
// Exponential backoff with jitter (recommended)
IntervalFunction.ofExponentialRandomBackoff(
    Duration.ofMillis(500),   // initial
    2.0,                       // multiplier
    Duration.ofSeconds(30)     // max interval
)
```

### Retry Safety

Only retry operations that are **idempotent** or where the server guarantees idempotency:

| HTTP Method | Safe to Retry | Notes                              |
| ----------- | ------------- | ---------------------------------- |
| GET         | Yes           | Idempotent by definition           |
| PUT         | Yes           | Idempotent (full replacement)      |
| DELETE      | Yes           | Idempotent                         |
| POST        | Caution       | Only with idempotency key          |
| PATCH       | Caution       | Depends on implementation          |

```java
// Idempotency key for POST retries
HttpRequest request = HttpRequest.newBuilder()
    .POST(body)
    .header("Idempotency-Key", UUID.randomUUID().toString())
    .build();
```

## Timeout

Prevent indefinite waiting for slow or unresponsive services.

### Timeout Types

```text
┌─────────────────────────────────────────────────┐
│              Total Request Timeout               │
│                                                   │
│  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Connection   │  │    Read/Response          │  │
│  │  Timeout      │  │    Timeout                │  │
│  │  (TCP setup)  │  │    (data transfer)        │  │
│  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

| Timeout Type       | Typical Value | Purpose                               |
| ------------------ | ------------- | ------------------------------------- |
| Connection timeout | 1-5 seconds   | TCP handshake completion              |
| Read timeout       | 5-30 seconds  | Waiting for response data             |
| Total timeout      | 10-60 seconds | End-to-end request deadline           |

### Configuration

```java
HttpClient httpClient = HttpClient.newBuilder()
    .connectTimeout(Duration.ofSeconds(3))
    .build();

HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("https://api.payment.com/charge"))
    .timeout(Duration.ofSeconds(10))  // Total timeout
    .build();
```

### Timeout Guidelines

- Set timeouts on every external call (never rely on defaults)
- Connection timeout should be shorter than read timeout
- Total timeout should account for retries: `total >= (read_timeout * max_retries)`
- Downstream timeout should be shorter than upstream timeout to avoid cascading

## Bulkhead

Isolate failures by limiting concurrent access to a resource.

### Semaphore Bulkhead

```java
BulkheadConfig config = BulkheadConfig.custom()
    .maxConcurrentCalls(10)           // Max 10 concurrent requests
    .maxWaitDuration(Duration.ofMillis(500))  // Wait for slot
    .build();

Bulkhead bulkhead = Bulkhead.of("payment-service", config);

Supplier<PaymentResult> decorated = Bulkhead
    .decorateSupplier(bulkhead, () -> paymentClient.process(request));
```

### Thread Pool Bulkhead

```java
ThreadPoolBulkheadConfig config = ThreadPoolBulkheadConfig.custom()
    .maxThreadPoolSize(10)
    .coreThreadPoolSize(5)
    .queueCapacity(20)
    .keepAliveDuration(Duration.ofMillis(100))
    .build();

ThreadPoolBulkhead bulkhead = ThreadPoolBulkhead.of("payment-service", config);
```

### Bulkhead per Service

```text
┌──────────────────────────────────────────────┐
│                Application                    │
│                                               │
│  ┌──────────────┐  ┌──────────────┐          │
│  │ Payment      │  │ Inventory    │          │
│  │ Bulkhead     │  │ Bulkhead     │          │
│  │ (10 threads) │  │ (5 threads)  │          │
│  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼─────────────────┘
          │                  │
          ▼                  ▼
   Payment Service    Inventory Service
```

If Payment Service is slow, only 10 threads are blocked. Inventory Service remains unaffected.

## Combining Patterns

The recommended order of wrapping (outermost to innermost):

```text
Bulkhead → CircuitBreaker → Retry → Timeout → HTTP Call

Bulkhead:       limits concurrent requests
CircuitBreaker: prevents calls to failing service
Retry:          retries transient failures
Timeout:        limits individual call duration
```

```java
// Resilience4j decoration chain
Supplier<Response> supplier = () -> httpClient.send(request);

Supplier<Response> resilient = Decorators.ofSupplier(supplier)
    .withBulkhead(bulkhead)
    .withCircuitBreaker(circuitBreaker)
    .withRetry(retry)
    .withFallback(List.of(
        CallNotPermittedException.class,
        BulkheadFullException.class
    ), e -> Response.fallback())
    .decorate();
```

## Monitoring

Track resilience metrics to tune configurations:

| Metric                          | Alert On                          |
| ------------------------------- | --------------------------------- |
| Circuit breaker state changes   | OPEN state transitions            |
| Retry rate                      | > 20% of requests retried         |
| Timeout rate                    | > 5% of requests timing out       |
| Bulkhead rejection rate         | > 10% of requests rejected        |
| Fallback activation rate        | Any sustained fallback usage       |
