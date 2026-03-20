# Event System

## Publishing Events

```java
// Event class (record preferred for immutability)
public record OrderCreatedEvent(Long orderId, Long userId, BigDecimal amount) {}

// Publishing
@Service
public class OrderService {
    private final ApplicationEventPublisher eventPublisher;

    @Transactional
    public Order createOrder(CreateOrderRequest request) {
        Order order = orderRepository.save(Order.from(request));
        eventPublisher.publishEvent(new OrderCreatedEvent(
            order.getId(), order.getUserId(), order.getAmount()
        ));
        return order;
    }
}
```

## Consuming Events

```java
@Component
public class OrderEventHandler {

    // Synchronous listener — runs in publisher's thread and transaction
    @EventListener
    public void onOrderCreated(OrderCreatedEvent event) {
        log.info("Order created: {}", event.orderId());
    }

    // Async listener — runs in separate thread
    @Async
    @EventListener
    public void sendOrderNotification(OrderCreatedEvent event) {
        notificationService.send(event.userId(), "Order confirmed");
    }

    // Runs AFTER transaction commits — safe for side effects
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void afterOrderCommitted(OrderCreatedEvent event) {
        externalApi.notifyPartner(event.orderId());
    }
}
```

## Event Listener Types

| Listener Type                 | Transaction Context              | Use Case                        |
| ----------------------------- | -------------------------------- | ------------------------------- |
| `@EventListener`             | Same transaction as publisher    | In-process sync processing      |
| `@Async @EventListener`      | No transaction (new thread)      | Fire-and-forget side effects    |
| `@TransactionalEventListener` | Runs after tx phase (e.g., commit) | External calls after commit   |

## Event Rules

- Use `@TransactionalEventListener(AFTER_COMMIT)` for operations that must not execute if transaction rolls back
- `@TransactionalEventListener` events are NOT delivered if no transaction is active
- For cross-service events, use messaging (Kafka, NATS) instead of `ApplicationEvent`
