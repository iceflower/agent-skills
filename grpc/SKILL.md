---
name: grpc
description: >-
  gRPC and Protocol Buffers conventions for service-to-service communication
  including proto3 schema design, service definition patterns, streaming
  (unary, server, client, bidirectional), error handling with Status codes,
  interceptor patterns, deadline/timeout management, load balancing strategies,
  and service mesh integration (Istio, Envoy).
  Covers gRPC-Java, gRPC-Kotlin, and Spring Boot integration via grpc-spring.
  Use when designing or implementing gRPC services, writing proto files,
  configuring gRPC clients/servers, or integrating gRPC with microservices
  and service mesh environments.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
compatibility: Requires protoc (Protocol Buffers compiler)
---

# gRPC and Protocol Buffers Rules

## 1. Proto3 Schema Design

> See [references/proto-style-guide.md](references/proto-style-guide.md) for detailed naming conventions, versioning, and backward compatibility rules.

### Basic Rules

- Always use `syntax = "proto3";` — proto2 is legacy and should not be used for new services
- Define a `package` that mirrors the directory structure (e.g., `package com.example.order.v1;`)
- Set `option java_multiple_files = true;` to generate one Java/Kotlin class per message
- Set `option java_package` to match your project's package convention
- Use `google.protobuf` well-known types (`Timestamp`, `Duration`, `Empty`, `FieldMask`) instead of custom equivalents
- Keep `.proto` files in a shared, versioned repository or module accessible to both client and server

### Message Design

```protobuf
syntax = "proto3";

package com.example.order.v1;

import "google/protobuf/timestamp.proto";

option java_multiple_files = true;
option java_package = "com.example.order.v1";

message Order {
  string order_id = 1;
  string user_id = 2;
  OrderStatus status = 3;
  repeated OrderItem items = 4;
  google.protobuf.Timestamp created_at = 5;
  google.protobuf.Timestamp updated_at = 6;
}

message OrderItem {
  string product_id = 1;
  int32 quantity = 2;
  int64 price_cents = 3;  // Use smallest currency unit to avoid floating point
}

enum OrderStatus {
  ORDER_STATUS_UNSPECIFIED = 0;  // Always define zero value as UNSPECIFIED
  ORDER_STATUS_CREATED = 1;
  ORDER_STATUS_CONFIRMED = 2;
  ORDER_STATUS_SHIPPED = 3;
  ORDER_STATUS_DELIVERED = 4;
  ORDER_STATUS_CANCELLED = 5;
}
```

### Schema Design Rules

- Never reuse or reassign field numbers — deleted fields should use `reserved`
- Enum zero value must always be `UNSPECIFIED` or `UNKNOWN` — it is the default
- Prefix enum values with the enum name in UPPER_SNAKE_CASE (e.g., `ORDER_STATUS_CREATED`)
- Use `int64` or fixed-point integers for monetary values — never use `float` or `double`
- Use `repeated` for collections — it defaults to empty list, not null
- Use `oneof` for mutually exclusive fields
- Use `google.protobuf.FieldMask` for partial updates instead of nullable wrappers

---

## 2. Service Definition Patterns

### Communication Types

| Pattern          | Description                             | Use Case                           |
| ---------------- | --------------------------------------- | ---------------------------------- |
| Unary            | Single request, single response         | CRUD operations, lookups           |
| Server Streaming | Single request, stream of responses     | Real-time feeds, large result sets |
| Client Streaming | Stream of requests, single response     | File upload, batch processing      |
| Bidirectional    | Stream of requests, stream of responses | Chat, real-time collaboration      |

### Service Definition Example

```protobuf
service OrderService {
  // Unary — simple request/response
  rpc CreateOrder(CreateOrderRequest) returns (CreateOrderResponse);
  rpc GetOrder(GetOrderRequest) returns (Order);

  // Server streaming — server pushes multiple responses
  rpc ListOrders(ListOrdersRequest) returns (stream Order);

  // Client streaming — client sends multiple requests
  rpc BatchCreateOrders(stream CreateOrderRequest) returns (BatchCreateOrdersResponse);

  // Bidirectional streaming — both sides stream
  rpc OrderUpdates(stream OrderUpdateRequest) returns (stream OrderUpdateResponse);
}

message CreateOrderRequest {
  string user_id = 1;
  repeated OrderItem items = 2;
}

message CreateOrderResponse {
  Order order = 1;
}

message GetOrderRequest {
  string order_id = 1;
}

message ListOrdersRequest {
  string user_id = 1;
  int32 page_size = 2;
  string page_token = 3;  // Cursor-based pagination
}
```

### Service Definition Rules

- Use `Create`, `Get`, `List`, `Update`, `Delete` as standard method prefixes following Google API Design Guide conventions
- Request and response messages should be named `{MethodName}Request` and `{MethodName}Response`
- Use cursor-based pagination (`page_size` + `page_token`) for `List` methods
- Prefer unary RPCs unless streaming is genuinely needed — streaming adds complexity
- Use server streaming for large result sets or real-time push scenarios
- Use client streaming for batch ingestion or uploads
- Use bidirectional streaming only for true real-time bidirectional communication

---

## 3. gRPC Status Codes

### Status Code Usage Guide

| Code                  | Number | Meaning                               | When to Use                               |
| --------------------- | ------ | ------------------------------------- | ----------------------------------------- |
| `OK`                  | 0      | Success                               | Operation completed successfully          |
| `CANCELLED`           | 1      | Operation cancelled                   | Client cancelled the request              |
| `UNKNOWN`             | 2      | Unknown error                         | Unexpected errors, unhandled exceptions   |
| `INVALID_ARGUMENT`    | 3      | Invalid input                         | Validation failures, malformed requests   |
| `DEADLINE_EXCEEDED`   | 4      | Deadline expired                      | Operation took too long                   |
| `NOT_FOUND`           | 5      | Resource not found                    | Requested entity does not exist           |
| `ALREADY_EXISTS`      | 6      | Resource already exists               | Duplicate creation attempt                |
| `PERMISSION_DENIED`   | 7      | Insufficient permissions              | Authenticated but not authorized          |
| `RESOURCE_EXHAUSTED`  | 8      | Resource limit reached                | Rate limiting, quota exhaustion           |
| `FAILED_PRECONDITION` | 9      | System not in required state          | Operation rejected due to current state   |
| `ABORTED`             | 10     | Operation aborted                     | Concurrency conflict, transaction aborted |
| `OUT_OF_RANGE`        | 11     | Value out of valid range              | Pagination past end, invalid offset       |
| `UNIMPLEMENTED`       | 12     | Method not implemented                | Feature not yet available                 |
| `INTERNAL`            | 13     | Internal server error                 | Server-side bugs, invariant violations    |
| `UNAVAILABLE`         | 14     | Service temporarily unavailable       | Transient failures, service starting up   |
| `DATA_LOSS`           | 15     | Unrecoverable data loss or corruption | Critical data integrity failures          |
| `UNAUTHENTICATED`     | 16     | Missing or invalid authentication     | No valid credentials provided             |

### Status Code Rules

- Return `INVALID_ARGUMENT` for client input validation errors, not `INTERNAL`
- Return `NOT_FOUND` only when the resource is expected to exist — use `INVALID_ARGUMENT` for malformed identifiers
- Return `UNAVAILABLE` for transient failures that clients can retry — use `INTERNAL` for permanent server errors
- Return `FAILED_PRECONDITION` when the operation cannot proceed due to current system state
- Use `UNAUTHENTICATED` for missing/invalid credentials; use `PERMISSION_DENIED` for valid credentials with insufficient access
- Attach error details using `google.rpc.Status` with `google.rpc.ErrorInfo`, `google.rpc.BadRequest`, or `google.rpc.DebugInfo`
- Never expose stack traces or internal details in production error messages

> See [references/error-handling-retry.md](references/error-handling-retry.md) for rich error model implementation and retry/hedging JSON configuration examples.

---

## 4. Interceptor Patterns

### Common Interceptor Use Cases

| Interceptor Type     | Purpose                                    | Side   |
| -------------------- | ------------------------------------------ | ------ |
| Authentication       | Validate tokens, extract identity          | Server |
| Authorization        | Check permissions for the requested method | Server |
| Logging              | Log request/response metadata              | Both   |
| Metrics              | Record latency, error rates, throughput    | Both   |
| Tracing              | Propagate trace context (OpenTelemetry)    | Both   |
| Error Translation    | Convert exceptions to gRPC Status codes    | Server |
| Deadline Propagation | Forward remaining deadline to downstream   | Client |

> See [references/interceptor-patterns.md](references/interceptor-patterns.md) for server and client interceptor implementation examples (authentication, deadline propagation).

### Interceptor Rules

- Apply interceptors in a consistent order: authentication -> authorization -> logging -> metrics -> tracing
- Server interceptors should fail fast — reject unauthenticated requests before processing
- Client interceptors should propagate deadlines and trace context to downstream services
- Never log request/response payloads in production — log metadata only (method, status, duration)
- Use `Context` to pass interceptor-extracted values (e.g., principal) to service implementations
- Register interceptors globally on the server/channel, not per-method

---

## 5. Deadline and Timeout Management

> See [references/kotlin-conventions.md](references/kotlin-conventions.md) for deadline configuration code examples (client-side and server-side).

### Deadline vs Timeout

| Concept  | Description                                          | Propagation    |
| -------- | ---------------------------------------------------- | -------------- |
| Timeout  | Duration from when the call starts                   | Not propagated |
| Deadline | Absolute point in time by which the call must finish | Propagated     |

### Deadline Rules

- Always set deadlines on client calls — never allow unbounded calls
- Deadlines propagate automatically through the gRPC context across service hops
- Set downstream service deadlines shorter than the caller's remaining deadline
- Check `Context.current().isCancelled` before starting expensive operations
- Use a default deadline interceptor to ensure no call goes without a deadline
- Log deadline exceeded events — they indicate capacity or latency issues

### Recommended Timeout Strategy

| Call Type               | Recommended Timeout | Rationale                            |
| ----------------------- | ------------------- | ------------------------------------ |
| Internal unary          | 1-5 seconds         | Fast, within the same network        |
| External unary          | 5-30 seconds        | Network variability, third-party     |
| Server streaming        | 30-120 seconds      | Long-lived but bounded               |
| Bidirectional streaming | Minutes to hours    | Keep-alive required, reconnect logic |

---

## 6. Load Balancing Strategies

### Load Balancing Models

| Strategy             | Description                                   | Use Case                               |
| -------------------- | --------------------------------------------- | -------------------------------------- |
| Pick-First           | Connect to the first resolved address         | Development, single-instance services  |
| Round Robin          | Rotate across all resolved addresses          | Homogeneous backends, simple balancing |
| Weighted Round Robin | Distribute based on server-reported weights   | Heterogeneous backends                 |
| Look-Aside (xDS)     | External load balancer provides endpoint list | Service mesh, Envoy/Istio environments |
| Proxy-Based          | All traffic goes through a proxy (L4/L7)      | Traditional LB, API gateway            |

### Client-Side Load Balancing

```kotlin
// Round-robin load balancing with name resolver
val channel = ManagedChannelBuilder
    .forTarget("dns:///order-service:50051")
    .defaultLoadBalancingPolicy("round_robin")
    .usePlaintext()  // For development only — use TLS in production
    .build()
```

### Load Balancing Rules

- Use `round_robin` for Kubernetes headless services — it resolves all pod IPs
- Use proxy-based load balancing (e.g., Envoy) when client-side LB is not feasible
- In service mesh environments, delegate load balancing to the sidecar proxy
- Enable health checking on the client to avoid sending requests to unhealthy backends
- For gRPC, prefer L7 (HTTP/2-aware) load balancers over L4 — L4 balancers pin connections to one backend
- Configure `keepAliveTime` and `keepAliveTimeout` to detect dead connections

### Kubernetes Considerations

```yaml
# Headless service for client-side load balancing
apiVersion: v1
kind: Service
metadata:
  name: order-service
spec:
  clusterIP: None  # Headless — DNS returns all pod IPs
  selector:
    app: order-service
  ports:
    - port: 50051
      targetPort: 50051
      protocol: TCP
```

---

## 7. Error Handling and Retry Policy

### Retry Rules

- Only retry on transient status codes: `UNAVAILABLE`, `DEADLINE_EXCEEDED`, `ABORTED`
- Never retry `INVALID_ARGUMENT`, `NOT_FOUND`, `PERMISSION_DENIED`, or `UNAUTHENTICATED` — these are permanent failures
- Use exponential backoff with jitter to avoid thundering herd
- Set `maxAttempts` to 3-5 — more retries rarely help and increase load
- Ensure operations are idempotent before enabling retries — or use idempotency keys
- Use hedging (sending parallel requests) only for read-only operations with low cost
- gRPC built-in retry is configured via service config JSON — prefer it over application-level retry

---

## 8. gRPC-Java and gRPC-Kotlin Conventions

> See [references/kotlin-conventions.md](references/kotlin-conventions.md) for coroutine stub usage, extension patterns, and proto-to-domain mapping examples.

### Convention Rules

- Use `grpc-kotlin` coroutine stubs for Kotlin projects — avoid blocking stubs
- Keep proto-to-domain mapping in dedicated mapper files, not inside service implementations
- Use `Flow` for streaming responses in Kotlin — it integrates naturally with coroutines
- For Java projects, use `ListenableFuture` stubs or `StreamObserver` — avoid mixing blocking and async
- Never expose proto-generated classes in your domain layer — always map to domain models
- Use `buf` or `protoc` plugins for consistent code generation across projects

---

## 9. Spring Boot Integration (grpc-spring)

> See [references/spring-boot-integration.md](references/spring-boot-integration.md) for detailed server/client configuration, interceptor setup, and testing patterns.

### Quick Start

```kotlin
// build.gradle.kts
dependencies {
    implementation("net.devh:grpc-spring-boot-starter:3.1.0.RELEASE")
    implementation("io.grpc:grpc-kotlin-stub:1.4.1")
    implementation("io.grpc:grpc-protobuf:1.62.2")
    implementation("com.google.protobuf:protobuf-kotlin:3.25.3")
}
```

### Server Configuration

```kotlin
@GrpcService
class OrderGrpcService(
    private val orderService: OrderService
) : OrderServiceGrpcKt.OrderServiceCoroutineImplBase() {

    override suspend fun createOrder(request: CreateOrderRequest): CreateOrderResponse {
        val order = orderService.create(request.toCommand())
        return order.toCreateResponse()
    }

    override suspend fun getOrder(request: GetOrderRequest): Order {
        val order = orderService.findById(request.orderId)
            ?: throw Status.NOT_FOUND
                .withDescription("Order not found: ${request.orderId}")
                .asRuntimeException()
        return order.toProto()
    }
}
```

```yaml
# application.yml
grpc:
  server:
    port: 50051
    security:
      enabled: true
      certificate-chain: classpath:certs/server.crt
      private-key: classpath:certs/server.key
```

### Client Configuration

```kotlin
@Configuration
class GrpcClientConfig {

    @GrpcClient("order-service")
    lateinit var orderServiceStub: OrderServiceGrpcKt.OrderServiceCoroutineStub
}
```

```yaml
# application.yml
grpc:
  client:
    order-service:
      address: dns:///order-service:50051
      negotiation-type: tls
      enable-keep-alive: true
      keep-alive-time: 30s
      keep-alive-timeout: 5s
```

### Spring Integration Rules

- Use `@GrpcService` annotation for server-side service beans — it registers them with the gRPC server
- Use `@GrpcClient` for injecting client stubs — it manages channel lifecycle and load balancing
- Configure TLS in production — never use plaintext in production environments
- Use Spring's `@Transactional` carefully — gRPC calls are not part of Spring transactions
- Register interceptors as Spring beans with `@GrpcGlobalServerInterceptor` or `@GrpcGlobalClientInterceptor`
- Test gRPC services with `@GrpcSpringBootTest` and `grpc-spring-boot-starter-test`

---

## 10. Service Mesh Integration (Istio / Envoy)

> See [references/service-mesh-integration.md](references/service-mesh-integration.md) for detailed Istio/Envoy configuration examples, DestinationRule/VirtualService YAML, and gRPC health check implementation.

### Key Benefits

| Feature            | Without Mesh                    | With Service Mesh              |
| ------------------ | ------------------------------- | ------------------------------ |
| Load Balancing     | Client-side LB code required    | Automatic L7 balancing         |
| mTLS               | Manual certificate management   | Automatic certificate rotation |
| Retries            | Application-level configuration | Mesh-level policy              |
| Circuit Breaking   | Resilience4j or similar library | Envoy configuration            |
| Observability      | Manual instrumentation          | Automatic metrics and tracing  |
| Traffic Management | Custom routing logic            | VirtualService rules           |

### Service Mesh Integration Rules

- Use `h2UpgradePolicy: UPGRADE` in DestinationRule to ensure HTTP/2 for gRPC traffic
- Delegate mTLS, retries, and circuit breaking to the mesh when available — avoid duplicating in application code
- When using mesh-level retries, disable application-level retries to prevent retry amplification
- Configure `outlierDetection` for automatic ejection of unhealthy endpoints
- Use Istio `VirtualService` for canary deployments, traffic splitting, and fault injection
- Ensure gRPC health checking is configured — Envoy uses it for endpoint health status
- Use `grpc_health_v1.Health` service for standardized health checks

---

## 11. Related Skills

| Topic                      | Related Skill            | Relevance                                         |
| -------------------------- | ------------------------ | ------------------------------------------------- |
| Microservices architecture | `microservices` skill    | Service decomposition, communication patterns     |
| REST API design            | `api-design` skill       | Alternative protocol, API gateway patterns        |
| Messaging patterns         | `messaging` skill        | Async communication, event-driven alternatives    |
| Error handling             | `error-handling` skill   | Exception hierarchy, error propagation            |
| Monitoring                 | `observability` skill    | gRPC metrics, tracing, alerting                   |
| Security                   | `security` skill         | mTLS, authentication, authorization               |
| Kubernetes                 | `k8s-workflow` skill     | Service deployment, health checks, networking     |
| Spring Framework           | `spring-framework` skill | grpc-spring integration, dependency injection     |
| HTTP client                | `http-client` skill      | Timeout, retry, circuit breaker for REST fallback |

---

## Further Reading

- [gRPC Official Documentation](https://grpc.io/docs/) — Core concepts, guides, and API reference
- [Protocol Buffers Language Guide (proto3)](https://protobuf.dev/programming-guides/proto3/) — Proto3 syntax and features
- [Google API Design Guide](https://cloud.google.com/apis/design) — API design patterns applicable to gRPC
- [gRPC-Kotlin Documentation](https://grpc.io/docs/languages/kotlin/) — Kotlin-specific gRPC usage
- [grpc-spring (grpc-ecosystem)](https://grpc-ecosystem.github.io/grpc-spring/) — Spring Boot integration for gRPC
- [Envoy gRPC Support](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/other_protocols/grpc) — Envoy proxy gRPC features
- [Istio Traffic Management](https://istio.io/latest/docs/concepts/traffic-management/) — Service mesh traffic policies
