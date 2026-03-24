# gRPC-Java and gRPC-Kotlin Conventions

## gRPC-Kotlin Coroutine Stubs

```kotlin
// Generated coroutine stub usage
class OrderServiceImpl(
    private val orderRepository: OrderRepository
) : OrderServiceGrpcKt.OrderServiceCoroutineImplBase() {

    override suspend fun createOrder(request: CreateOrderRequest): CreateOrderResponse {
        val order = orderRepository.save(request.toOrder())
        return CreateOrderResponse.newBuilder()
            .setOrder(order.toProto())
            .build()
    }

    override fun listOrders(request: ListOrdersRequest): Flow<Order> = flow {
        orderRepository.findByUserId(request.userId)
            .collect { order -> emit(order.toProto()) }
    }
}
```

## Kotlin Extension Patterns

```kotlin
// Proto to domain model mapping — keep in a separate mapper file
fun CreateOrderRequest.toOrder(): DomainOrder = DomainOrder(
    userId = this.userId,
    items = this.itemsList.map { it.toDomainItem() }
)

fun DomainOrder.toProto(): Order = Order.newBuilder()
    .setOrderId(this.id)
    .setUserId(this.userId)
    .setStatus(this.status.toProtoStatus())
    .addAllItems(this.items.map { it.toProto() })
    .build()
```

## Deadline Configuration Examples

```kotlin
// Client-side deadline
val response = orderServiceStub
    .withDeadlineAfter(3, TimeUnit.SECONDS)
    .getOrder(GetOrderRequest.newBuilder().setOrderId("order-123").build())

// Server-side deadline check
override fun getOrder(request: GetOrderRequest, responseObserver: StreamObserver<Order>) {
    if (Context.current().isCancelled) {
        responseObserver.onError(
            Status.CANCELLED.withDescription("Request already cancelled").asRuntimeException()
        )
        return
    }

    // Check remaining time before expensive operation
    val deadline = Context.current().deadline
    if (deadline != null && deadline.timeRemaining(TimeUnit.MILLISECONDS) < 100) {
        responseObserver.onError(
            Status.DEADLINE_EXCEEDED.withDescription("Insufficient time remaining").asRuntimeException()
        )
        return
    }

    // Process request...
}
```
