# Saga Pattern Details

## Choreography vs Orchestration

| Aspect                  | Choreography                      | Orchestration                     |
| ----------------------- | --------------------------------- | --------------------------------- |
| Coordination            | Each service listens and reacts   | Central orchestrator directs flow |
| Coupling                | Low (event-driven)                | Medium (orchestrator knows steps) |
| Complexity              | Grows with number of participants | Centralized, easier to trace      |
| Debugging               | Hard to follow event chain        | Single point to observe flow      |
| Single point of failure | None                              | Orchestrator                      |
| Best for                | Simple flows (2-4 services)       | Complex flows (5+ services)       |

## Choreography Example

```text
Order Service -> [OrderCreated] -> Payment Service
Payment Service -> [PaymentCompleted] -> Inventory Service
Inventory Service -> [InventoryReserved] -> Shipping Service

On failure:
Inventory Service -> [ReservationFailed] -> Payment Service (refund)
Payment Service -> [PaymentRefunded] -> Order Service (cancel)
```

## Orchestration Example

```kotlin
class OrderSagaOrchestrator(
    private val paymentClient: PaymentClient,
    private val inventoryClient: InventoryClient,
    private val shippingClient: ShippingClient,
    private val orderRepository: OrderRepository
) {
    suspend fun execute(order: Order) {
        try {
            val payment = paymentClient.charge(order.toPaymentRequest())
            val reservation = inventoryClient.reserve(order.toReservationRequest())
            shippingClient.schedule(order.toShippingRequest())
            orderRepository.updateStatus(order.id, OrderStatus.CONFIRMED)
        } catch (e: PaymentException) {
            orderRepository.updateStatus(order.id, OrderStatus.CANCELLED)
        } catch (e: InventoryException) {
            paymentClient.refund(order.paymentId)
            orderRepository.updateStatus(order.id, OrderStatus.CANCELLED)
        } catch (e: ShippingException) {
            inventoryClient.release(order.reservationId)
            paymentClient.refund(order.paymentId)
            orderRepository.updateStatus(order.id, OrderStatus.CANCELLED)
        }
    }
}
```

## Compensating Transactions

| Forward Action    | Compensating Action |
| ----------------- | ------------------- |
| Charge payment    | Refund payment      |
| Reserve inventory | Release inventory   |
| Schedule shipment | Cancel shipment     |
| Create order      | Cancel order        |
