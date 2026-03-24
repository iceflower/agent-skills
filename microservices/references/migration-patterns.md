# Monolith to Microservices Migration Patterns

## Branch by Abstraction

```kotlin
// Step 1: Introduce abstraction layer in monolith
interface NotificationSender {
    fun send(userId: String, message: String)
}

// Step 2: Old implementation (still in monolith)
class MonolithNotificationSender : NotificationSender {
    override fun send(userId: String, message: String) {
        // Direct DB call within monolith
    }
}

// Step 3: New implementation (calls extracted service)
class MicroserviceNotificationSender(
    private val notificationClient: NotificationClient
) : NotificationSender {
    override fun send(userId: String, message: String) {
        notificationClient.send(SendRequest(userId, message))
    }
}

// Step 4: Feature toggle to switch implementations
// Wired via dependency injection with feature toggle
fun notificationSender(
    enabled: Boolean,  // from configuration: feature.notification-service.enabled
    notificationClient: NotificationClient
): NotificationSender =
    if (enabled) MicroserviceNotificationSender(notificationClient)
    else MonolithNotificationSender()
```

## Strangler Fig Pattern

```text
Phase 1: Route all traffic through new gateway
┌──────────┐     ┌──────────────┐
│  Gateway  │────→│  Monolith    │
└──────────┘     └──────────────┘

Phase 2: Extract one service, route specific paths to it
┌──────────┐     ┌──────────────┐
│  Gateway  │──┬─→│  Monolith    │  (remaining features)
└──────────┘  │  └──────────────┘
              │  ┌──────────────┐
              └─→│  Order Svc   │  (extracted feature)
                 └──────────────┘

Phase 3: Repeat until monolith is empty
```

## Resilience Configuration Example

```kotlin
class PaymentService(
    private val paymentClient: PaymentClient
) {
    // Apply: circuit breaker → retry → bulkhead (via framework or library config)
    fun processPayment(request: PaymentRequest): PaymentResponse {
        return paymentClient.charge(request)
    }

    // Fallback when circuit breaker is open
    fun paymentFallback(request: PaymentRequest, e: Exception): PaymentResponse {
        log.warn("Payment service unavailable, queuing for retry", e)
        pendingPaymentQueue.enqueue(request)
        return PaymentResponse.pending(request.orderId)
    }
}
```

```yaml
# Resilience4j configuration (Spring Boot application.yml format shown;
# standalone usage configures via code or resilience4j.yml)
resilience4j:
  circuitbreaker:
    instances:
      paymentApi:
        sliding-window-size: 10
        failure-rate-threshold: 50
        wait-duration-in-open-state: 30s
        permitted-number-of-calls-in-half-open-state: 3
  retry:
    instances:
      paymentApi:
        max-attempts: 3
        wait-duration: 1s
        exponential-backoff-multiplier: 2
        retry-exceptions:
          - java.net.ConnectException
          - java.net.SocketTimeoutException
  bulkhead:
    instances:
      paymentApi:
        max-concurrent-calls: 10
        max-wait-duration: 500ms
```
