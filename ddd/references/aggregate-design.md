# Aggregate Design Patterns

Aggregate is the fundamental building block for transactional consistency in Domain-Driven Design.

## Overview

An Aggregate is a cluster of domain objects treated as a single unit for data changes. Every Aggregate has a root entity (the Aggregate Root) that controls access to its internals and enforces invariants.

## Aggregate Root Responsibilities

The Aggregate Root is the single entry point for all modifications:

- Enforce all invariants within the Aggregate boundary
- Control access to child entities and value objects
- Publish domain events when state changes occur
- Serve as the identity reference for external objects

```java
public class Order {
    private OrderId id;
    private CustomerId customerId;
    private List<OrderLine> lines = new ArrayList<>();
    private OrderStatus status;
    private Money totalAmount;

    public void addLine(Product product, Quantity quantity) {
        if (status != OrderStatus.DRAFT) {
            throw new IllegalStateException("Cannot modify a confirmed order");
        }
        OrderLine line = new OrderLine(product.getId(), product.getPrice(), quantity);
        lines.add(line);
        recalculateTotal();
    }

    public void confirm() {
        if (lines.isEmpty()) {
            throw new DomainException("Cannot confirm an empty order");
        }
        status = OrderStatus.CONFIRMED;
        registerEvent(new OrderConfirmed(id, customerId, totalAmount));
    }

    private void recalculateTotal() {
        totalAmount = lines.stream()
            .map(OrderLine::lineTotal)
            .reduce(Money.ZERO, Money::add);
    }
}
```

## Consistency Boundaries

### Transactional Consistency (Within Aggregate)

All invariants within an Aggregate are enforced synchronously in a single transaction.

```text
┌─────────────────────────────────────────┐
│            Order (Aggregate)            │
│                                         │
│  ┌──────────┐   ┌──────────────────┐   │
│  │ OrderId  │   │   OrderStatus    │   │
│  └──────────┘   └──────────────────┘   │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │       OrderLine (Entity)        │   │
│  │  productId, price, quantity     │   │
│  └──────────────────────────────────┘   │
│                                         │
│  Invariant: total == sum(line totals)   │
│  Invariant: confirmed => lines > 0     │
└─────────────────────────────────────────┘
```

### Eventual Consistency (Between Aggregates)

Cross-aggregate invariants are maintained through domain events and eventual consistency.

```text
┌──────────┐   OrderConfirmed   ┌──────────────┐
│  Order   │ ──────────────────▶│  Inventory   │
│          │    (domain event)  │  (reserve)   │
└──────────┘                    └──────────────┘
```

**Rule**: Only one Aggregate is modified per transaction. Other Aggregates react asynchronously via domain events.

## Aggregate Size Guidelines

### Keep Aggregates Small

Large Aggregates cause contention and performance issues.

| Symptom                    | Cause                     | Solution                            |
| -------------------------- | ------------------------- | ----------------------------------- |
| Frequent optimistic locks  | Aggregate too large       | Split into smaller Aggregates       |
| Slow load times            | Too many child entities   | Move collections to own Aggregates  |
| Complex invariant checking | Mixed responsibilities    | Separate bounded contexts           |

### Reference by Identity

Do not hold direct object references to other Aggregates. Use identity references instead.

```java
// Bad: direct reference creates implicit coupling
public class Order {
    private Customer customer; // direct reference
}

// Good: reference by identity
public class Order {
    private CustomerId customerId; // identity reference
}
```

### Collection Sizing

When an Aggregate contains a collection, consider the maximum expected size:

- **Small collections (< 20 items)**: Safe to keep inside the Aggregate
- **Medium collections (20-100)**: Consider lazy loading or pagination
- **Large collections (100+)**: Extract to a separate Aggregate

## Design Heuristics

### Invariant-Driven Boundaries

Group entities that must change together to maintain a business rule:

1. List all invariants in the domain
2. Identify which entities participate in each invariant
3. Group co-dependent entities into the same Aggregate
4. Keep unrelated entities in separate Aggregates

### Command-Per-Aggregate

Each command should target exactly one Aggregate:

```text
AddOrderLine      → Order Aggregate
ConfirmOrder      → Order Aggregate
UpdateInventory   → Inventory Aggregate  (triggered by event, not by Order)
```

### Anti-Patterns to Avoid

- **God Aggregate**: One Aggregate containing everything
- **Anemic Aggregate**: Aggregate with only getters/setters, no behavior
- **Cross-Aggregate Transactions**: Modifying multiple Aggregates in one transaction
- **Aggregate Envy**: Business logic placed outside the Aggregate that owns the data

## Testing Aggregates

```java
@Test
void confirmOrder_withLines_publishesEvent() {
    Order order = new Order(OrderId.generate(), customerId);
    order.addLine(product, Quantity.of(2));

    order.confirm();

    assertThat(order.getStatus()).isEqualTo(OrderStatus.CONFIRMED);
    assertThat(order.domainEvents())
        .hasSize(1)
        .first()
        .isInstanceOf(OrderConfirmed.class);
}

@Test
void confirmOrder_withoutLines_throwsException() {
    Order order = new Order(OrderId.generate(), customerId);

    assertThatThrownBy(() -> order.confirm())
        .isInstanceOf(DomainException.class)
        .hasMessageContaining("empty order");
}
```
