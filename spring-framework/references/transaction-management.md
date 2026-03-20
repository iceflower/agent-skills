# Transaction Management

## @Transactional Behavior

```java
@Service
public class OrderService {
    private final OrderRepository orderRepository;
    private final PaymentService paymentService;

    // Read-write transaction (default)
    @Transactional
    public Order createOrder(CreateOrderRequest request) {
        Order order = Order.from(request);
        return orderRepository.save(order);
    }

    // Read-only transaction — enables optimizations
    @Transactional(readOnly = true)
    public Order findById(Long id) {
        return orderRepository.findById(id)
            .orElseThrow(() -> new EntityNotFoundException("Order", id));
    }
}
```

## Propagation Levels

| Propagation      | Behavior                                          | Use Case                         |
| ---------------- | ------------------------------------------------- | -------------------------------- |
| `REQUIRED`       | Join existing or create new (default)             | Most business operations         |
| `REQUIRES_NEW`   | Always create new, suspend existing               | Audit logging, independent ops   |
| `SUPPORTS`       | Join existing or run non-transactional             | Read-only queries                |
| `NOT_SUPPORTED`  | Suspend existing, run non-transactional            | Non-critical operations          |
| `MANDATORY`      | Must run in existing transaction, else exception   | Operations requiring caller tx   |
| `NEVER`          | Must NOT run in transaction, else exception        | Operations that must not be tx   |
| `NESTED`         | Nested transaction with savepoint                  | Partial rollback scenarios       |

## Rollback Rules

```java
// Default: rollback on unchecked exceptions (RuntimeException), NOT on checked
@Transactional
public void process() {
    // RuntimeException → rollback
    // IOException (checked) → commit (NOT rolled back)
}

// Explicit rollback for checked exceptions
@Transactional(rollbackFor = IOException.class)
public void processFile() throws IOException { ... }

// No rollback for specific runtime exceptions
@Transactional(noRollbackFor = BusinessValidationException.class)
public void validate() { ... }
```

## Transaction Pitfalls

- **Self-invocation**: `@Transactional` on method B called from method A in the same class does NOT create transaction (proxy bypass)
- **Private methods**: `@Transactional` on private methods is silently ignored
- **Exception swallowed**: Catching exception inside `@Transactional` prevents rollback
- **Long transactions**: Never call external APIs inside `@Transactional` — hold locks too long

```java
// Bad: exception caught inside transaction — no rollback
@Transactional
public void riskyOperation() {
    try {
        repository.save(entity);
        externalApi.call(); // Fails
    } catch (Exception e) {
        log.error("Failed", e); // Transaction commits despite failure
    }
}

// Good: let exception propagate
@Transactional
public void riskyOperation() {
    repository.save(entity);
    // External API call should be outside @Transactional
}
```
