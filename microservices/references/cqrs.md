# CQRS (Command Query Responsibility Segregation)

Separate the read (query) and write (command) sides of an application into distinct models.

## Overview

CQRS splits a single data model into two: a write model optimized for processing commands and enforcing invariants, and a read model optimized for serving queries. This separation allows each side to be scaled, optimized, and evolved independently.

```text
┌──────────────┐                    ┌──────────────┐
│   Command    │                    │    Query     │
│   (Write)    │                    │   (Read)     │
│              │                    │              │
│  ┌────────┐  │   Domain Events   │  ┌────────┐  │
│  │ Domain │  │───────────────────▶│  │  Read  │  │
│  │ Model  │  │                    │  │ Model  │  │
│  └───┬────┘  │                    │  └───┬────┘  │
│      │       │                    │      │       │
│  ┌───▼────┐  │                    │  ┌───▼────┐  │
│  │Write DB│  │                    │  │Read DB │  │
│  └────────┘  │                    │  └────────┘  │
└──────────────┘                    └──────────────┘
```

## Command Side

Commands represent intentions to change state. They are imperative and may be rejected.

### Command Design

```java
// Command: imperative, may fail
public record PlaceOrderCommand(
    CustomerId customerId,
    List<OrderItemRequest> items,
    ShippingAddress address
) {}

// Command handler: validates, executes, persists
@Component
public class PlaceOrderCommandHandler {
    private final OrderRepository orderRepository;
    private final EventPublisher eventPublisher;

    public OrderId handle(PlaceOrderCommand command) {
        // Validate business rules
        Order order = Order.create(
            command.customerId(),
            command.items(),
            command.address()
        );

        // Persist write model
        orderRepository.save(order);

        // Publish events for read model updates
        order.collectDomainEvents()
            .forEach(eventPublisher::publish);

        return order.getId();
    }
}
```

### Command Validation Layers

```text
┌───────────────────────────────────────────┐
│  Layer 1: Input validation (format, type) │  ← Controller / DTO
├───────────────────────────────────────────┤
│  Layer 2: Authorization (permissions)     │  ← Security filter
├───────────────────────────────────────────┤
│  Layer 3: Business rules (invariants)     │  ← Domain model
└───────────────────────────────────────────┘
```

## Query Side (Read Models)

Read models are denormalized views optimized for specific query patterns.

### Projection Design

```java
// Read model: flat, denormalized, query-optimized
public record OrderSummaryView(
    String orderId,
    String customerName,
    String status,
    BigDecimal totalAmount,
    int itemCount,
    Instant placedAt
) {}

// Projector: builds read model from events
@Component
public class OrderSummaryProjector {

    @EventHandler
    public void on(OrderPlaced event) {
        OrderSummaryView view = new OrderSummaryView(
            event.orderId().value(),
            event.customerName(),
            "PLACED",
            event.totalAmount().value(),
            event.lineCount(),
            event.occurredAt()
        );
        readStore.save(view);
    }

    @EventHandler
    public void on(OrderShipped event) {
        readStore.updateStatus(event.orderId().value(), "SHIPPED");
    }
}
```

### Multiple Read Models

Different queries may need different read models from the same events:

```text
                              ┌──────────────────┐
                         ┌───▶│ Order Summary    │  (list page)
                         │    │ (PostgreSQL)     │
  ┌───────────────┐      │    └──────────────────┘
  │ Domain Events │──────┤
  │               │      │    ┌──────────────────┐
  └───────────────┘      ├───▶│ Order Search     │  (full-text search)
                         │    │ (Elasticsearch)  │
                         │    └──────────────────┘
                         │
                         │    ┌──────────────────┐
                         └───▶│ Order Analytics  │  (dashboard)
                              │ (ClickHouse)     │
                              └──────────────────┘
```

## Eventual Consistency

With separate read and write stores, the read model is eventually consistent with the write model.

### Consistency Timeline

```text
Time ──────────────────────────────────────────────────▶

Write DB:   [Order Created] ────────────────────────────
Read DB:    ─────────────── [Projection Updated] ──────
                            ▲
                            │ Propagation delay
                            │ (typically ms to seconds)
```

### Handling Stale Reads

| Strategy                  | Implementation                                     |
| ------------------------- | -------------------------------------------------- |
| Read-your-writes          | After command, query write DB directly for that user|
| Version check             | Client sends last-known version, server waits      |
| Polling                   | Client retries until read model catches up          |
| Subscription              | Push updates via WebSocket/SSE                     |

```java
// Read-your-writes: query write model after own command
@GetMapping("/orders/{id}")
public OrderDetailView getOrder(
    @PathVariable String id,
    @RequestParam(required = false) Long afterVersion
) {
    if (afterVersion != null) {
        // Wait for read model to catch up to expected version
        return readStore.findByIdWithMinVersion(id, afterVersion, Duration.ofSeconds(5));
    }
    return readStore.findById(id);
}
```

## When to Use CQRS

### Good Fit

- Read and write workloads have significantly different characteristics
- Complex domain logic on write side, simple queries on read side
- Read and write sides need different scaling
- Event Sourcing is used (CQRS is a natural complement)
- Multiple, distinct query patterns exist

### Poor Fit

- Simple CRUD with no complex business logic
- Read and write patterns are similar
- Strong consistency is always required
- Small team without experience in distributed systems

## Simplified CQRS (Single Database)

CQRS does not require separate databases. Start simple with separate models in one database:

```java
// Write side: rich domain model
@Entity
@Table(name = "orders")
public class Order {
    @Id private UUID id;
    @OneToMany(cascade = ALL) private List<OrderLine> lines;
    @Embedded private Money total;
    // Business logic, invariants...
}

// Read side: database view or query-specific repository
@Query("SELECT new OrderListItem(o.id, o.status, o.total, o.createdAt) " +
       "FROM Order o WHERE o.customerId = :customerId")
List<OrderListItem> findOrderSummaries(@Param("customerId") UUID customerId);
```

This gives the benefits of model separation without the complexity of separate databases and eventual consistency.

## Testing CQRS

```java
// Test command side: behavior and invariants
@Test
void placeOrder_withValidItems_createsOrderAndPublishesEvent() {
    PlaceOrderCommand command = new PlaceOrderCommand(customerId, items, address);

    OrderId result = handler.handle(command);

    assertThat(orderRepository.findById(result)).isPresent();
    assertThat(publishedEvents).contains(instanceOf(OrderPlaced.class));
}

// Test read side: projection correctness
@Test
void orderSummaryProjection_onOrderPlaced_createsView() {
    OrderPlaced event = new OrderPlaced(orderId, "Alice", money(100), 3, now());

    projector.on(event);

    OrderSummaryView view = readStore.findById(orderId.value());
    assertThat(view.customerName()).isEqualTo("Alice");
    assertThat(view.itemCount()).isEqualTo(3);
}
```
