# Data Transformation Between Layers

## Transformation Flow

```text
Request DTO -> Command -> Domain Entity -> Persistence Entity -> Database
Database -> Persistence Entity -> Domain Entity -> Result DTO -> Response DTO
```

## Layer-Specific Data Objects

| Layer          | Data Object           | Purpose               | Framework Coupling     |
| -------------- | --------------------- | --------------------- | ---------------------- |
| Presentation   | Request / Response    | API contract          | Validation, serializer |
| Application    | Command / Result      | Use case input/output | None                   |
| Domain         | Entity / Value Object | Business model        | None                   |
| Infrastructure | Persistence Entity    | Persistence mapping   | ORM annotations        |

## Mapping Examples

```text
// Presentation -> Application
fun toCommand(request: CreateOrderRequest): CreateOrderCommand {
    return CreateOrderCommand(
        customerId = CustomerId(request.customerId),
        productId = ProductId(request.productId),
        quantity = request.quantity
    )
}

// Application -> Presentation
fun toResponse(result: OrderDetailResult): OrderDetailResponse {
    return OrderDetailResponse(
        id = result.orderId.value,
        status = result.status.name,
        totalAmount = result.totalAmount.value,
        createdAt = result.createdAt
    )
}

// Infrastructure: Persistence Entity <-> Domain
// Mapper (infrastructure layer)
class OrderEntityMapper {
    fun toDomain(entity: OrderPersistenceEntity): Order {
        return Order(
            id = OrderId(entity.id),
            customerId = CustomerId(entity.customerId),
            status = entity.status,
            lines = entity.lines.map { toOrderLine(it) }
        )
    }

    fun toEntity(domain: Order): OrderPersistenceEntity {
        return OrderPersistenceEntity(
            id = domain.id.value,
            customerId = domain.customerId.value,
            status = domain.status,
            lines = domain.lines.map { toLineEntity(it) }
        )
    }
}
```

## Mapping Rules

- Each layer boundary has its own data objects -- never pass persistence entities to controllers
- Mapping logic lives at the boundary of the outer layer (adapter side)
- Domain objects never depend on DTO or persistence entity classes
- Use dedicated mapper classes or mapping functions for conversions
- Avoid deep nested mapping in a single function -- compose small mapping functions

## Use Case Implementation

```text
// Application service
class CreateOrderService implements CreateOrderUseCase {
    private orderRepository: OrderRepository
    private productRepository: ProductRepository
    private eventPublisher: EventPublisher

    // Transaction boundary
    fun execute(command: CreateOrderCommand): OrderId {
        // 1. Load domain objects
        val product = productRepository.findById(command.productId)
            ?: throw EntityNotFoundException("Product", command.productId)

        // 2. Execute domain logic (delegate to domain)
        val order = Order.create(
            customerId = command.customerId,
            product = product,
            quantity = command.quantity
        )

        // 3. Persist
        orderRepository.save(order)

        // 4. Publish domain events
        order.pullEvents().forEach { eventPublisher.publish(it) }

        // 5. Return result
        return order.id
    }
}
```

## Testability by Layer

### Domain Layer Test (No Dependencies)

```text
class OrderTest {
    fun test_should_add_line_to_order() {
        val order = Order.create(customerId, product, quantity = 2)

        // assert: order.totalAmount() equals Money.of(2000)
    }

    fun test_should_reject_more_than_10_items() {
        val order = Order.create(customerId, product, quantity = 1)
        repeat(9) { order.addLine(product, 1) }

        // assert: order.addLine(product, 1) throws IllegalArgumentException
    }
}
```

### Application Layer Test (Fake Ports)

```text
class CreateOrderServiceTest {
    private orderRepository = FakeOrderRepository()
    private productRepository = FakeProductRepository()
    private eventPublisher = FakeEventPublisher()

    private sut = CreateOrderService(orderRepository, productRepository, eventPublisher)

    fun test_should_create_order_and_publish_event() {
        productRepository.save(product)

        val orderId = sut.execute(CreateOrderCommand(customerId, productId, quantity = 2))

        // assert: orderRepository.findById(orderId) is not null
        // assert: eventPublisher.publishedEvents has size 1
    }
}

// Fake implementation for testing
class FakeOrderRepository implements OrderRepository {
    private store = Map<OrderId, Order>()

    fun findById(id: OrderId): Order? = store.get(id)
    fun save(order: Order) { store.put(order.id, order) }
    fun delete(id: OrderId) { store.remove(id) }
}
```
