# CQRS and Event Sourcing

## CQRS (Command Query Responsibility Segregation)

```text
Client -> Command API -> Write Model -> Event Store
Client -> Query API  -> Read Model  <- Projection (from events)
```

## When to Use CQRS

| Use CQRS                                      | Avoid CQRS                         |
| --------------------------------------------- | ---------------------------------- |
| Read and write workloads differ significantly | Simple CRUD with uniform access    |
| Complex domain with rich business rules       | Small team or early-stage project  |
| Need different read models for different UIs  | Data consistency must be immediate |
| High read-to-write ratio                      | Domain model is straightforward    |

## Event Sourcing

```kotlin
// Event as the source of truth
sealed class OrderEvent {
    data class Created(val orderId: String, val items: List<Item>) : OrderEvent()
    data class ItemAdded(val orderId: String, val item: Item) : OrderEvent()
    data class Confirmed(val orderId: String, val confirmedAt: Instant) : OrderEvent()
    data class Cancelled(val orderId: String, val reason: String) : OrderEvent()
}

// Rebuild state from events
fun Order.Companion.fromEvents(events: List<OrderEvent>): Order {
    return events.fold(Order.empty()) { state, event ->
        when (event) {
            is OrderEvent.Created -> state.copy(id = event.orderId, items = event.items)
            is OrderEvent.ItemAdded -> state.copy(items = state.items + event.item)
            is OrderEvent.Confirmed -> state.copy(status = OrderStatus.CONFIRMED)
            is OrderEvent.Cancelled -> state.copy(status = OrderStatus.CANCELLED)
        }
    }
}
```

## Event Sourcing Trade-Offs

| Advantage                            | Disadvantage                        |
| ------------------------------------ | ----------------------------------- |
| Complete audit trail                 | Increased storage requirements      |
| Temporal queries (state at any time) | Complex event schema evolution      |
| Natural fit for event-driven arch    | Eventually consistent read models   |
| Debugging via event replay           | Learning curve for development team |
