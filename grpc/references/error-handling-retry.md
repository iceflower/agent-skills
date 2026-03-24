# gRPC Error Handling, Retry, and Hedging Configuration

## Rich Error Model

```kotlin
import io.grpc.protobuf.StatusProto
import com.google.rpc.Status
import com.google.rpc.BadRequest
import com.google.protobuf.Any

// Build rich error response
val fieldViolation = BadRequest.FieldViolation.newBuilder()
    .setField("email")
    .setDescription("Invalid email format")
    .build()

val badRequest = BadRequest.newBuilder()
    .addFieldViolations(fieldViolation)
    .build()

val status = Status.newBuilder()
    .setCode(com.google.rpc.Code.INVALID_ARGUMENT_VALUE)
    .setMessage("Request validation failed")
    .addDetails(Any.pack(badRequest))
    .build()

throw StatusProto.toStatusRuntimeException(status)
```

## Retry Configuration

```json
{
  "methodConfig": [
    {
      "name": [
        { "service": "com.example.order.v1.OrderService" }
      ],
      "timeout": "5s",
      "retryPolicy": {
        "maxAttempts": 3,
        "initialBackoff": "0.1s",
        "maxBackoff": "1s",
        "backoffMultiplier": 2,
        "retryableStatusCodes": [
          "UNAVAILABLE",
          "DEADLINE_EXCEEDED"
        ]
      }
    }
  ]
}
```

## Hedging Policy (Read-Only Operations)

```json
{
  "methodConfig": [
    {
      "name": [
        { "service": "com.example.order.v1.OrderService", "method": "GetOrder" }
      ],
      "hedgingPolicy": {
        "maxAttempts": 2,
        "hedgingDelay": "0.5s",
        "nonFatalStatusCodes": ["UNAVAILABLE"]
      }
    }
  ]
}
```
