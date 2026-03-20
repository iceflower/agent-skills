# Aggregates, Domain Events, and Specifications

## Aggregate Example

```kotlin
// Aggregate Root
class Order(
    val id: OrderId,
    private val customerId: CustomerId,
    private var status: OrderStatus,
    private val lines: MutableList<OrderLine> = mutableListOf()
) {
    // Business rule: max 10 items per order
    fun addLine(product: Product, quantity: Int) {
        require(lines.size < 10) { "Maximum 10 items per order" }
        require(quantity > 0) { "Quantity must be positive" }
        lines.add(OrderLine(product.id, product.price, quantity))
    }

    fun totalAmount(): Money {
        return lines.fold(Money.ZERO) { acc, line ->
            acc + line.subtotal()
        }
    }

    fun confirm() {
        require(lines.isNotEmpty()) { "Cannot confirm empty order" }
        status = OrderStatus.CONFIRMED
    }

    internal fun isConfirmed() = status == OrderStatus.CONFIRMED
}

// Entity within aggregate (no repository)
class OrderLine(
    val productId: ProductId,
    val unitPrice: Money,
    val quantity: Int
) {
    fun subtotal() = unitPrice.multiply(quantity)
}
```

## Factory Example

```kotlin
// Factory method on aggregate
class Order {
    companion object {
        fun create(
            customerId: CustomerId,
            product: Product,
            quantity: Int
        ): Order {
            require(quantity > 0) { "Quantity must be positive" }
            val order = Order(OrderId.generate(), customerId, OrderStatus.DRAFT)
            order.addLine(product, quantity)
            return order
        }
    }
}

// Separate factory class
interface OrderFactory {
    fun createFromCart(cart: Cart): Order
}

class DefaultOrderFactory : OrderFactory {
    override fun createFromCart(cart: Cart): Order {
        val order = Order(OrderId.generate(), cart.customerId, OrderStatus.DRAFT)
        cart.items.forEach { order.addLine(it.product, it.quantity) }
        return order
    }
}
```

## Specification Example

```kotlin
interface Specification<T> {
    fun isSatisfiedBy(candidate: T): Boolean
    fun and(other: Specification<T>): Specification<T> = AndSpecification(this, other)
    fun or(other: Specification<T>): Specification<T> = OrSpecification(this, other)
}

class ActiveCustomerSpecification : Specification<Customer> {
    override fun isSatisfiedBy(candidate: Customer): Boolean {
        return candidate.isActive &&
               candidate.lastOrderDate.isAfter(LocalDate.now().minusMonths(6))
    }
}

class PremiumCustomerSpecification : Specification<Customer> {
    override fun isSatisfiedBy(candidate: Customer): Boolean {
        return candidate.totalSpent >= Money.of(1000)
    }
}

// Usage
val specification = ActiveCustomerSpecification()
    .and(PremiumCustomerSpecification())

val eligibleCustomers = customers.filter { specification.isSatisfiedBy(it) }
```

## Domain Event Example

```kotlin
// Event definition
data class OrderConfirmed(
    val orderId: OrderId,
    val customerId: CustomerId,
    val confirmedAt: Instant
) : DomainEvent

// Publishing events
class Order {
    private val events = mutableListOf<DomainEvent>()

    fun confirm() {
        require(lines.isNotEmpty()) { "Cannot confirm empty order" }
        status = OrderStatus.CONFIRMED
        events.add(OrderConfirmed(id, customerId, Instant.now()))
    }

    fun pullEvents(): List<DomainEvent> {
        val result = events.toList()
        events.clear()
        return result
    }
}

// Event handler
class SendConfirmationEmailHandler(
    private val emailService: EmailService
) {
    fun handle(event: OrderConfirmed) {
        emailService.sendConfirmation(event.customerId, event.orderId)
    }
}
```

## Application Service Example

```text
// Application service — orchestrates use cases
class OrderApplicationService(
    private orderRepository: OrderRepository,
    private productRepository: ProductRepository,
    private eventPublisher: EventPublisher
) {
    // Transaction boundary
    fun createOrder(command: CreateOrderCommand): OrderId {
        val product = productRepository.findById(command.productId)
            ?: throw ProductNotFoundException(command.productId)

        val order = Order.create(
            customerId = command.customerId,
            product = product,
            quantity = command.quantity
        )

        orderRepository.save(order)

        order.pullEvents().forEach { eventPublisher.publish(it) }

        return order.id
    }

    // Transaction boundary
    fun confirmOrder(command: ConfirmOrderCommand) {
        val order = orderRepository.findById(command.orderId)
            ?: throw OrderNotFoundException(command.orderId)

        order.confirm()
        orderRepository.save(order)

        order.pullEvents().forEach { eventPublisher.publish(it) }
    }
}
```
