# Saga Pattern

Sagas manage distributed transactions across multiple microservices without two-phase commit.

## Overview

In a microservice architecture, a single business operation may span multiple services, each with its own database. The Saga pattern coordinates these steps as a sequence of local transactions, with compensating actions to undo completed steps on failure.

## Choreography vs Orchestration

### Choreography

Each service publishes events and reacts to events from other services. No central coordinator.

```text
┌──────────┐  OrderCreated  ┌──────────┐  PaymentProcessed  ┌──────────┐
│  Order   │───────────────▶│ Payment  │───────────────────▶│Inventory │
│ Service  │                │ Service  │                    │ Service  │
└──────────┘                └──────────┘                    └──────────┘
     ▲                                                           │
     └───────────────── InventoryReserved ───────────────────────┘
```

**Pros**:

- Simple for small flows (2-4 steps)
- Loose coupling between services
- No single point of failure

**Cons**:

- Hard to track overall transaction state
- Cyclic dependencies can emerge
- Difficult to understand with many participants

### Orchestration

A central orchestrator directs the saga, telling each participant what to do.

```text
                    ┌──────────────┐
                    │  Saga        │
            ┌──────│  Orchestrator│──────┐
            │      └──────┬───────┘      │
            │             │              │
            ▼             ▼              ▼
      ┌──────────┐ ┌──────────┐  ┌──────────┐
      │  Order   │ │ Payment  │  │Inventory │
      │ Service  │ │ Service  │  │ Service  │
      └──────────┘ └──────────┘  └──────────┘
```

**Pros**:

- Clear view of the entire flow
- Easier to manage complex workflows
- Centralized error handling and retries

**Cons**:

- Orchestrator can become a bottleneck
- Risk of coupling too much logic in the orchestrator
- Additional infrastructure component

### When to Choose

| Criteria            | Choreography           | Orchestration           |
| ------------------- | ---------------------- | ----------------------- |
| Number of steps     | 2-4 steps              | 5+ steps                |
| Flow complexity     | Linear                 | Branching/conditional   |
| Team autonomy       | High priority          | Acceptable tradeoff     |
| Observability needs | Basic                  | Important               |
| Error handling      | Simple compensations   | Complex rollback logic  |

## Compensation

When a saga step fails, all previously completed steps must be undone via compensating transactions.

### Compensation Design

```text
Forward Flow:
  Step 1: Create Order       → Compensate: Cancel Order
  Step 2: Reserve Inventory  → Compensate: Release Inventory
  Step 3: Process Payment    → Compensate: Refund Payment
  Step 4: Arrange Shipping   → (no compensation needed if last step)

Failure at Step 3:
  ✓ Step 1: Create Order
  ✓ Step 2: Reserve Inventory
  ✗ Step 3: Process Payment (FAILED)
  → Compensate Step 2: Release Inventory
  → Compensate Step 1: Cancel Order
```

### Implementation Example (Orchestrator)

```java
public class OrderSagaOrchestrator {
    private final OrderService orderService;
    private final PaymentService paymentService;
    private final InventoryService inventoryService;

    public SagaResult execute(CreateOrderCommand command) {
        SagaLog saga = SagaLog.start(command.sagaId());

        try {
            // Step 1: Create order
            OrderId orderId = orderService.createOrder(command);
            saga.recordStep("CREATE_ORDER", orderId);

            // Step 2: Reserve inventory
            ReservationId reservationId = inventoryService.reserve(command.items());
            saga.recordStep("RESERVE_INVENTORY", reservationId);

            // Step 3: Process payment
            PaymentId paymentId = paymentService.charge(command.paymentInfo());
            saga.recordStep("PROCESS_PAYMENT", paymentId);

            saga.complete();
            return SagaResult.success(orderId);

        } catch (SagaStepException e) {
            compensate(saga);
            return SagaResult.failure(e.getMessage());
        }
    }

    private void compensate(SagaLog saga) {
        List<SagaStep> completedSteps = saga.getCompletedSteps();
        Collections.reverse(completedSteps);

        for (SagaStep step : completedSteps) {
            try {
                switch (step.name()) {
                    case "PROCESS_PAYMENT" -> paymentService.refund(step.resourceId());
                    case "RESERVE_INVENTORY" -> inventoryService.release(step.resourceId());
                    case "CREATE_ORDER" -> orderService.cancel(step.resourceId());
                }
                saga.recordCompensation(step.name());
            } catch (Exception ex) {
                saga.recordCompensationFailure(step.name(), ex);
                // Alert for manual intervention
            }
        }
    }
}
```

## Failure Handling

### Failure Categories

| Failure Type        | Example                      | Strategy                          |
| ------------------- | ---------------------------- | --------------------------------- |
| Transient           | Network timeout              | Retry with backoff                |
| Business rule       | Insufficient funds           | Compensate immediately            |
| Infrastructure      | Service down                 | Retry + circuit breaker           |
| Compensation fails  | Refund service unreachable   | Dead letter queue + manual review |

### Retry Policies

```java
public class SagaRetryPolicy {
    private final int maxRetries = 3;
    private final Duration initialDelay = Duration.ofSeconds(1);

    public <T> T executeWithRetry(Supplier<T> step, String stepName) {
        int attempt = 0;
        while (true) {
            try {
                return step.get();
            } catch (TransientException e) {
                attempt++;
                if (attempt >= maxRetries) {
                    throw new SagaStepException(stepName, e);
                }
                sleep(initialDelay.multipliedBy((long) Math.pow(2, attempt - 1)));
            }
        }
    }
}
```

### Saga State Machine

```text
┌─────────┐    step success    ┌───────────┐    all done    ┌───────────┐
│ STARTED │───────────────────▶│ EXECUTING │──────────────▶│ COMPLETED │
└─────────┘                    └─────┬─────┘               └───────────┘
                                     │ step failure
                                     ▼
                              ┌──────────────┐   all compensated   ┌──────────┐
                              │ COMPENSATING │────────────────────▶│ ABORTED  │
                              └──────┬───────┘                     └──────────┘
                                     │ compensation failure
                                     ▼
                              ┌──────────────┐
                              │   FAILED     │  (requires manual intervention)
                              └──────────────┘
```

## Idempotency Requirements

Every saga step and compensation must be idempotent:

```java
public class InventoryService {

    public ReservationId reserve(SagaId sagaId, List<Item> items) {
        // Check if already reserved for this saga
        Optional<Reservation> existing = reservationRepo.findBySagaId(sagaId);
        if (existing.isPresent()) {
            return existing.get().getId(); // Idempotent
        }

        Reservation reservation = Reservation.create(sagaId, items);
        reservationRepo.save(reservation);
        return reservation.getId();
    }
}
```

## Observability

Track saga execution for debugging and monitoring:

- Log each step transition with saga ID, step name, and status
- Emit metrics: saga duration, failure rate, compensation frequency
- Store saga state persistently for recovery after crashes
- Alert on sagas stuck in COMPENSATING or FAILED states
