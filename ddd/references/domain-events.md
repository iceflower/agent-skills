# Domain Events

Domain events capture meaningful occurrences in the business domain as first-class objects.

## Overview

A domain event represents something that happened in the domain that domain experts care about. Events are immutable facts about the past, named in past tense, and carry all data needed to describe what occurred.

## Event Structure

### Naming Conventions

Events are named as past-tense descriptions of what happened:

| Good (Past Tense)          | Bad (Command-Style)       |
| -------------------------- | ------------------------- |
| `OrderPlaced`              | `PlaceOrder`              |
| `PaymentReceived`          | `ProcessPayment`          |
| `InventoryReserved`        | `ReserveInventory`        |
| `ShipmentDispatched`       | `DispatchShipment`        |

### Event Anatomy

```java
public record OrderPlaced(
    EventId eventId,
    Instant occurredAt,
    OrderId orderId,
    CustomerId customerId,
    Money totalAmount,
    List<OrderLineSnapshot> lines
) implements DomainEvent {

    public OrderPlaced {
        Objects.requireNonNull(eventId);
        Objects.requireNonNull(occurredAt);
        Objects.requireNonNull(orderId);
    }
}
```

**Essential fields**:

- `eventId`: Unique identifier for idempotency
- `occurredAt`: When the event happened
- Business-specific data needed by consumers

## Publishing Events

### Collect-Then-Publish Pattern

Aggregate collects events internally; the application layer publishes them after persistence.

```java
public abstract class AggregateRoot {
    private final List<DomainEvent> domainEvents = new ArrayList<>();

    protected void registerEvent(DomainEvent event) {
        domainEvents.add(event);
    }

    public List<DomainEvent> collectDomainEvents() {
        List<DomainEvent> events = List.copyOf(domainEvents);
        domainEvents.clear();
        return events;
    }
}
```

```java
@Transactional
public void placeOrder(PlaceOrderCommand command) {
    Order order = orderFactory.create(command);
    orderRepository.save(order);

    // Publish after successful persistence
    order.collectDomainEvents()
        .forEach(eventPublisher::publish);
}
```

### Outbox Pattern

Store events in the same transaction as the Aggregate change to guarantee delivery.

```text
┌──────────────────────────────────────────┐
│           Single Transaction             │
│                                          │
│  ┌─────────────┐   ┌─────────────────┐  │
│  │ Order Table  │   │  Outbox Table   │  │
│  │ (updated)    │   │  (event added)  │  │
│  └─────────────┘   └─────────────────┘  │
└──────────────────────────────────────────┘
                       │
              Relay Process (CDC / polling)
                       │
                       ▼
              ┌─────────────────┐
              │  Message Broker  │
              └─────────────────┘
```

```sql
CREATE TABLE outbox_events (
    id          UUID PRIMARY KEY,
    aggregate_type  VARCHAR(255) NOT NULL,
    aggregate_id    VARCHAR(255) NOT NULL,
    event_type      VARCHAR(255) NOT NULL,
    payload         JSONB NOT NULL,
    occurred_at     TIMESTAMPTZ NOT NULL,
    published_at    TIMESTAMPTZ
);
```

## Event Handling Patterns

### In-Process Event Handler

```java
@Component
public class OrderPlacedHandler {

    @EventListener
    public void handle(OrderPlaced event) {
        // Update read model, send notification, etc.
    }

    @TransactionalEventListener(phase = AFTER_COMMIT)
    public void handleAfterCommit(OrderPlaced event) {
        // Actions that should only run after successful commit
    }
}
```

### Idempotent Consumers

Events may be delivered more than once. Consumers must handle duplicates.

```java
@Component
public class IdempotentEventHandler {
    private final ProcessedEventRepository processedEvents;

    public void handle(DomainEvent event) {
        if (processedEvents.exists(event.eventId())) {
            return; // Already processed
        }

        doHandle(event);
        processedEvents.save(event.eventId());
    }
}
```

## Event Sourcing Basics

Instead of storing current state, store the full history of events.

```text
Event Store:
┌─────────────────────────────────────────────┐
│ OrderCreated(orderId=1, customer="Alice")    │
│ OrderLineAdded(orderId=1, product="Book")    │
│ OrderLineAdded(orderId=1, product="Pen")     │
│ OrderConfirmed(orderId=1, total=25.00)       │
│ OrderShipped(orderId=1, trackingId="T123")   │
└─────────────────────────────────────────────┘
         │
         ▼  Replay events
┌─────────────────────────┐
│  Current State (Order)  │
│  status: SHIPPED        │
│  lines: [Book, Pen]     │
│  total: 25.00           │
└─────────────────────────┘
```

### Rebuilding State

```java
public class Order extends EventSourcedAggregate {

    public static Order reconstitute(List<DomainEvent> history) {
        Order order = new Order();
        history.forEach(order::apply);
        return order;
    }

    private void apply(DomainEvent event) {
        switch (event) {
            case OrderCreated e -> {
                this.id = e.orderId();
                this.status = OrderStatus.DRAFT;
            }
            case OrderLineAdded e -> {
                this.lines.add(new OrderLine(e.productId(), e.price(), e.quantity()));
            }
            case OrderConfirmed e -> {
                this.status = OrderStatus.CONFIRMED;
            }
            default -> throw new UnsupportedEventException(event);
        }
    }
}
```

### Snapshots

Optimize replay for Aggregates with many events:

```text
Snapshot at event #1000:  { state: ... }
Events #1001 - #1050:     [event, event, ...]

Rebuild = load snapshot + replay 50 events (instead of 1050)
```

## Event Versioning

### Schema Evolution Strategies

| Strategy          | Description                              | Use When                        |
| ----------------- | ---------------------------------------- | ------------------------------- |
| Upcasting         | Transform old event to new format        | Adding/renaming fields          |
| Weak schema       | Consumers ignore unknown fields          | Adding optional fields          |
| New event type    | Create versioned event type              | Structural changes              |
| Copy-transform    | Migrate entire event store               | Last resort for major changes   |

### Upcasting Example

```java
public class OrderPlacedV1ToV2Upcaster implements Upcaster {

    public DomainEvent upcast(DomainEvent event) {
        if (event instanceof OrderPlacedV1 v1) {
            return new OrderPlacedV2(
                v1.eventId(),
                v1.occurredAt(),
                v1.orderId(),
                v1.customerId(),
                v1.totalAmount(),
                Currency.USD  // default for v1 events
            );
        }
        return event;
    }
}
```
