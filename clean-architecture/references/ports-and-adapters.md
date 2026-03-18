# Ports and Adapters Pattern

## Inbound Ports (Driving Side)

Inbound ports define what the application can do. They are interfaces that the application layer exposes and the presentation layer invokes.

```kotlin
// Inbound port — defines a use case
interface CreateOrderUseCase {
    fun execute(command: CreateOrderCommand): OrderId
}

interface GetOrderQuery {
    fun execute(orderId: OrderId): OrderDetailResult
}
```

## Outbound Ports (Driven Side)

Outbound ports define what the application needs from the outside world. They are interfaces defined in the application or domain layer and implemented in the infrastructure layer.

```kotlin
// Outbound port — defined in domain layer
interface OrderRepository {
    fun findById(id: OrderId): Order?
    fun save(order: Order)
    fun delete(id: OrderId)
}

// Outbound port — defined in application layer
interface PaymentGateway {
    fun charge(orderId: OrderId, amount: Money): PaymentResult
}

// Outbound port — defined in application layer
interface NotificationSender {
    fun sendOrderConfirmation(customerId: CustomerId, orderId: OrderId)
}
```

## Inbound Adapters

Inbound adapters translate external requests into use case invocations.

```kotlin
// REST adapter (inbound)
@RestController
@RequestMapping("/api/v1/orders")
class OrderController(
    private val createOrderUseCase: CreateOrderUseCase,
    private val getOrderQuery: GetOrderQuery
) {
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    fun createOrder(@Valid @RequestBody request: CreateOrderRequest): CreateOrderResponse {
        val command = request.toCommand()
        val orderId = createOrderUseCase.execute(command)
        return CreateOrderResponse(orderId.value)
    }

    @GetMapping("/{id}")
    fun getOrder(@PathVariable id: Long): OrderDetailResponse {
        val result = getOrderQuery.execute(OrderId(id))
        return result.toResponse()
    }
}

// Message listener adapter (inbound)
@Component
class PaymentEventListener(
    private val handlePaymentResultUseCase: HandlePaymentResultUseCase
) {
    @KafkaListener(topics = ["payment-results"])
    fun onPaymentResult(event: PaymentResultEvent) {
        val command = event.toCommand()
        handlePaymentResultUseCase.execute(command)
    }
}
```

## Outbound Adapters

Outbound adapters implement outbound ports with specific technology.

```kotlin
// JPA adapter (outbound)
@Repository
class JpaOrderRepository(
    private val jpaRepository: OrderJpaRepository,
    private val mapper: OrderEntityMapper
) : OrderRepository {

    override fun findById(id: OrderId): Order? {
        return jpaRepository.findByIdOrNull(id.value)?.let { mapper.toDomain(it) }
    }

    override fun save(order: Order) {
        val entity = mapper.toEntity(order)
        jpaRepository.save(entity)
    }

    override fun delete(id: OrderId) {
        jpaRepository.deleteById(id.value)
    }
}

// External API adapter (outbound)
@Component
class StripePaymentGateway(
    private val restClient: RestClient
) : PaymentGateway {

    override fun charge(orderId: OrderId, amount: Money): PaymentResult {
        val response = restClient.post()
            .uri("/charges")
            .body(StripeChargeRequest(orderId.value, amount.value))
            .retrieve()
            .body(StripeChargeResponse::class.java)
            ?: throw PaymentGatewayException("Empty response from payment gateway")

        return response.toDomain()
    }
}
```

## Port and Adapter Summary

| Type             | Defined In           | Implemented In | Example              |
| ---------------- | -------------------- | -------------- | -------------------- |
| Inbound port     | Application          | Application    | `CreateOrderUseCase` |
| Inbound adapter  | Presentation         | Presentation   | `OrderController`    |
| Outbound port    | Domain / Application | Infrastructure | `OrderRepository`    |
| Outbound adapter | Infrastructure       | Infrastructure | `JpaOrderRepository` |