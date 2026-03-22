# Spring Boot gRPC Integration (grpc-spring)

## Dependencies

### Gradle (Kotlin DSL)

```kotlin
plugins {
    id("com.google.protobuf") version "0.9.4"
}

dependencies {
    // grpc-spring-boot-starter (server + client)
    implementation("net.devh:grpc-spring-boot-starter:3.1.0.RELEASE")

    // gRPC and Protobuf
    implementation("io.grpc:grpc-kotlin-stub:1.4.1")
    implementation("io.grpc:grpc-protobuf:1.62.2")
    implementation("io.grpc:grpc-netty-shaded:1.62.2")
    implementation("com.google.protobuf:protobuf-kotlin:3.25.3")

    // Testing
    testImplementation("net.devh:grpc-spring-boot-starter-test:3.1.0.RELEASE")
    testImplementation("io.grpc:grpc-testing:1.62.2")
}

protobuf {
    protoc {
        artifact = "com.google.protobuf:protoc:3.25.3"
    }
    plugins {
        create("grpc") {
            artifact = "io.grpc:protoc-gen-grpc-java:1.62.2"
        }
        create("grpckt") {
            artifact = "io.grpc:protoc-gen-grpc-kotlin:1.4.1:jdk8@jar"
        }
    }
    generateProtoTasks {
        all().forEach { task ->
            task.plugins {
                create("grpc")
                create("grpckt")
            }
            task.builtins {
                create("kotlin")
            }
        }
    }
}
```

### Server-Only or Client-Only

```kotlin
// Server only
implementation("net.devh:grpc-server-spring-boot-starter:3.1.0.RELEASE")

// Client only
implementation("net.devh:grpc-client-spring-boot-starter:3.1.0.RELEASE")
```

---

## Server Configuration

### Service Implementation

```kotlin
@GrpcService
class OrderGrpcService(
    private val orderService: OrderService
) : OrderServiceGrpcKt.OrderServiceCoroutineImplBase() {

    override suspend fun createOrder(request: CreateOrderRequest): CreateOrderResponse {
        val command = CreateOrderCommand(
            userId = request.userId,
            items = request.itemsList.map { it.toDomainItem() }
        )
        val order = orderService.create(command)
        return CreateOrderResponse.newBuilder()
            .setOrder(order.toProto())
            .build()
    }

    override suspend fun getOrder(request: GetOrderRequest): Order {
        val order = orderService.findById(request.orderId)
            ?: throw Status.NOT_FOUND
                .withDescription("Order not found: ${request.orderId}")
                .asRuntimeException()
        return order.toProto()
    }

    override fun listOrders(request: ListOrdersRequest): Flow<Order> = flow {
        orderService.findByUserId(request.userId, request.pageSize, request.pageToken)
            .collect { order -> emit(order.toProto()) }
    }
}
```

### Server Properties

```yaml
grpc:
  server:
    port: 50051
    # Security (TLS)
    security:
      enabled: true
      certificate-chain: classpath:certs/server.crt
      private-key: classpath:certs/server.key
      client-auth: OPTIONAL  # NONE, OPTIONAL, REQUIRE
      trust-certificate-collection: classpath:certs/ca.crt
    # Connection settings
    max-inbound-message-size: 4MB
    max-inbound-metadata-size: 8KB
    keep-alive-time: 2h
    keep-alive-timeout: 20s
    permit-keep-alive-time: 5m
    permit-keep-alive-without-calls: false
    # Health service (for Kubernetes/mesh probes)
    health-service-enabled: true
    # Reflection (for development tools like grpcurl)
    reflection-service-enabled: true
```

### Server Port Configuration

| Profile     | Port  | Purpose                                      |
| ----------- | ----- | -------------------------------------------- |
| Development | 50051 | Standard gRPC port                           |
| Testing     | 0     | Random port (use `@LocalGrpcPort`)           |
| Production  | 50051 | Behind load balancer or service mesh sidecar |

```yaml
# Test profile
spring:
  config:
    activate:
      on-profile: test

grpc:
  server:
    port: 0  # Random port for testing
    security:
      enabled: false
```

---

## Client Configuration

### Stub Injection

```kotlin
@Service
class OrderClient(
    @GrpcClient("order-service")
    private val orderStub: OrderServiceGrpcKt.OrderServiceCoroutineStub
) {
    suspend fun getOrder(orderId: String): Order {
        val request = GetOrderRequest.newBuilder()
            .setOrderId(orderId)
            .build()
        return orderStub.getOrder(request)
    }

    suspend fun createOrder(userId: String, items: List<OrderItemDto>): Order {
        val request = CreateOrderRequest.newBuilder()
            .setUserId(userId)
            .addAllItems(items.map { it.toProto() })
            .build()
        val response = orderStub.createOrder(request)
        return response.order
    }
}
```

### Client Properties

```yaml
grpc:
  client:
    order-service:
      address: dns:///order-service:50051
      negotiation-type: tls  # PLAINTEXT for dev, TLS for prod
      # Load balancing
      default-load-balancing-policy: round_robin
      # Connection pool
      enable-keep-alive: true
      keep-alive-time: 30s
      keep-alive-timeout: 5s
      keep-alive-without-calls: false
      # Message limits
      max-inbound-message-size: 4MB
      # Deadlines (applied to all calls on this channel)
      deadline-after: 5s
      # TLS
      security:
        certificate-chain: classpath:certs/client.crt
        private-key: classpath:certs/client.key
        trust-certificate-collection: classpath:certs/ca.crt

    # In-process channel for testing
    payment-service:
      address: in-process:test
      negotiation-type: plaintext
```

### Client Address Formats

| Format                           | Description                    | Use Case                     |
| -------------------------------- | ------------------------------ | ---------------------------- |
| `static://host1:port,host2:port` | Fixed list of addresses        | Known backend hosts          |
| `dns:///service-name:port`       | DNS-based discovery            | Kubernetes headless services |
| `discovery:///service-name`      | Spring Cloud discovery         | Eureka, Consul integration   |
| `in-process:name`                | In-process server (no network) | Integration testing          |
| `unix:///path/to/socket`         | Unix domain socket             | Same-host communication      |

---

## Interceptors

### Global Server Interceptor

```kotlin
@GrpcGlobalServerInterceptor
class LoggingServerInterceptor : ServerInterceptor {

    private val log = LoggerFactory.getLogger(javaClass)

    override fun <ReqT, RespT> interceptCall(
        call: ServerCall<ReqT, RespT>,
        headers: Metadata,
        next: ServerCallHandler<ReqT, RespT>
    ): ServerCall.Listener<ReqT> {
        val methodName = call.methodDescriptor.fullMethodName
        val startTime = System.nanoTime()

        log.info("gRPC call started: {}", methodName)

        val wrappedCall = object : ForwardingServerCall.SimpleForwardingServerCall<ReqT, RespT>(call) {
            override fun close(status: Status, trailers: Metadata) {
                val durationMs = (System.nanoTime() - startTime) / 1_000_000
                log.info("gRPC call completed: {} status={} duration={}ms",
                    methodName, status.code, durationMs)
                super.close(status, trailers)
            }
        }

        return next.startCall(wrappedCall, headers)
    }
}
```

### Global Client Interceptor

```kotlin
@GrpcGlobalClientInterceptor
class MetadataPropagationInterceptor : ClientInterceptor {

    override fun <ReqT, RespT> interceptCall(
        method: MethodDescriptor<ReqT, RespT>,
        callOptions: CallOptions,
        next: Channel
    ): ClientCall<ReqT, RespT> {
        return object : ForwardingClientCall.SimpleForwardingClientCall<ReqT, RespT>(
            next.newCall(method, callOptions)
        ) {
            override fun start(responseListener: Listener<RespT>, headers: Metadata) {
                // Propagate trace context
                val traceId = MDC.get("traceId")
                if (traceId != null) {
                    headers.put(
                        Metadata.Key.of("x-trace-id", Metadata.ASCII_STRING_MARSHALLER),
                        traceId
                    )
                }
                super.start(responseListener, headers)
            }
        }
    }
}
```

### Per-Client Interceptor

```kotlin
@Configuration
class GrpcInterceptorConfig {

    @Bean
    fun orderServiceInterceptors(): List<ClientInterceptor> {
        return listOf(
            DeadlinePropagationInterceptor(defaultDeadlineMs = 3000),
            RetryInterceptor(maxRetries = 3)
        )
    }
}
```

```yaml
# Apply interceptors to specific clients
grpc:
  client:
    order-service:
      address: dns:///order-service:50051
      # Per-client interceptors are registered via @GrpcClient(interceptors = [...])
      # or globally via @GrpcGlobalClientInterceptor
```

### Interceptor Ordering

```kotlin
// Use @Order annotation to control interceptor execution order
@GrpcGlobalServerInterceptor
@Order(10)
class AuthenticationInterceptor : ServerInterceptor { /* ... */ }

@GrpcGlobalServerInterceptor
@Order(20)
class AuthorizationInterceptor : ServerInterceptor { /* ... */ }

@GrpcGlobalServerInterceptor
@Order(30)
class LoggingInterceptor : ServerInterceptor { /* ... */ }
```

---

## Exception Handling

### Global Exception Handler

```kotlin
@GrpcAdvice
class GrpcExceptionHandler {

    @GrpcExceptionHandler(IllegalArgumentException::class)
    fun handleInvalidArgument(e: IllegalArgumentException): StatusRuntimeException {
        return Status.INVALID_ARGUMENT
            .withDescription(e.message)
            .withCause(e)
            .asRuntimeException()
    }

    @GrpcExceptionHandler(EntityNotFoundException::class)
    fun handleNotFound(e: EntityNotFoundException): StatusRuntimeException {
        return Status.NOT_FOUND
            .withDescription(e.message)
            .withCause(e)
            .asRuntimeException()
    }

    @GrpcExceptionHandler(AccessDeniedException::class)
    fun handleAccessDenied(e: AccessDeniedException): StatusRuntimeException {
        return Status.PERMISSION_DENIED
            .withDescription("Access denied")
            .asRuntimeException()
    }

    @GrpcExceptionHandler(Exception::class)
    fun handleGenericException(e: Exception): StatusRuntimeException {
        // Do not expose internal details in production
        return Status.INTERNAL
            .withDescription("Internal server error")
            .withCause(e)
            .asRuntimeException()
    }
}
```

### Domain Exception Mapping

| Domain Exception           | gRPC Status Code    | Description              |
| -------------------------- | ------------------- | ------------------------ |
| `IllegalArgumentException` | `INVALID_ARGUMENT`  | Invalid input            |
| `EntityNotFoundException`  | `NOT_FOUND`         | Resource not found       |
| `AccessDeniedException`    | `PERMISSION_DENIED` | Insufficient permissions |
| `DuplicateKeyException`    | `ALREADY_EXISTS`    | Duplicate resource       |
| `OptimisticLockException`  | `ABORTED`           | Concurrency conflict     |
| `TimeoutException`         | `DEADLINE_EXCEEDED` | Operation timed out      |
| `Exception` (generic)      | `INTERNAL`          | Unexpected error         |

---

## Testing

### Integration Test Setup

```kotlin
@SpringBootTest
@GrpcSpringBootTest
class OrderGrpcServiceTest {

    @GrpcClient("inProcess")
    lateinit var orderStub: OrderServiceGrpcKt.OrderServiceCoroutineStub

    @MockBean
    lateinit var orderService: OrderService

    @Test
    fun `should create order successfully`() = runBlocking {
        // Given
        val expectedOrder = DomainOrder(
            id = "order-123",
            userId = "user-456",
            items = listOf(DomainOrderItem("product-1", 2, 1000))
        )
        whenever(orderService.create(any())).thenReturn(expectedOrder)

        // When
        val request = CreateOrderRequest.newBuilder()
            .setUserId("user-456")
            .addItems(OrderItem.newBuilder()
                .setProductId("product-1")
                .setQuantity(2)
                .setPriceCents(1000))
            .build()
        val response = orderStub.createOrder(request)

        // Then
        assertThat(response.order.orderId).isEqualTo("order-123")
        assertThat(response.order.userId).isEqualTo("user-456")
    }

    @Test
    fun `should return NOT_FOUND when order does not exist`() = runBlocking {
        // Given
        whenever(orderService.findById("nonexistent")).thenReturn(null)

        // When / Then
        val exception = assertThrows<StatusRuntimeException> {
            orderStub.getOrder(
                GetOrderRequest.newBuilder()
                    .setOrderId("nonexistent")
                    .build()
            )
        }
        assertThat(exception.status.code).isEqualTo(Status.Code.NOT_FOUND)
    }
}
```

### Test Configuration

```yaml
# application-test.yml
grpc:
  server:
    port: 0
    in-process-name: test
    security:
      enabled: false
  client:
    inProcess:
      address: in-process:test
      negotiation-type: plaintext
```

### Testing Rules

- Use `in-process` transport for unit/integration tests — no network overhead
- Mock domain services, not gRPC stubs — test the gRPC layer as a thin adapter
- Test all status code mappings — verify correct gRPC status for each error scenario
- Test streaming endpoints with `Flow` collectors — verify ordering and completeness
- Use `@GrpcSpringBootTest` instead of manual server setup — it manages the lifecycle

### Testing Interceptors

```kotlin
@SpringBootTest
@GrpcSpringBootTest
class AuthenticationInterceptorTest {

    @GrpcClient("inProcess")
    lateinit var orderStub: OrderServiceGrpcKt.OrderServiceCoroutineStub

    @Test
    fun `should reject request without authentication token`() = runBlocking {
        val exception = assertThrows<StatusRuntimeException> {
            orderStub.getOrder(
                GetOrderRequest.newBuilder()
                    .setOrderId("order-123")
                    .build()
            )
        }
        assertThat(exception.status.code).isEqualTo(Status.Code.UNAUTHENTICATED)
    }

    @Test
    fun `should accept request with valid token`() = runBlocking {
        // Create stub with authentication metadata
        val metadata = Metadata().apply {
            put(
                Metadata.Key.of("authorization", Metadata.ASCII_STRING_MARSHALLER),
                "Bearer valid-token"
            )
        }
        val authenticatedStub = MetadataUtils.attachHeaders(orderStub, metadata)

        // Should not throw UNAUTHENTICATED
        val response = authenticatedStub.getOrder(
            GetOrderRequest.newBuilder()
                .setOrderId("order-123")
                .build()
        )
        assertThat(response.orderId).isEqualTo("order-123")
    }
}
```

---

## Monitoring and Health

### Actuator Integration

```yaml
# Expose gRPC server info alongside Spring Actuator
management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics, prometheus
  health:
    grpc:
      enabled: true
```

### Metrics

grpc-spring automatically exposes metrics when Micrometer is on the classpath:

| Metric                            | Type    | Description                     |
| --------------------------------- | ------- | ------------------------------- |
| `grpc.server.processing.duration` | Timer   | Server-side call duration       |
| `grpc.client.processing.duration` | Timer   | Client-side call duration       |
| `grpc.server.requests`            | Counter | Total server requests by status |
| `grpc.client.requests`            | Counter | Total client requests by status |

### Health Check Configuration

```kotlin
@Component
class GrpcHealthIndicator(
    private val orderService: OrderService
) : AbstractHealthIndicator() {

    override fun doHealthCheck(builder: Health.Builder) {
        try {
            orderService.healthCheck()
            builder.up()
                .withDetail("grpcServer", "running")
                .withDetail("port", 50051)
        } catch (e: Exception) {
            builder.down(e)
        }
    }
}
```

---

## Production Checklist

### Security

- [ ] TLS enabled for all gRPC channels (`negotiation-type: tls`)
- [ ] Client certificate validation configured (mTLS) for internal services
- [ ] Authentication interceptor registered globally
- [ ] Sensitive data excluded from logs and error messages

### Reliability

- [ ] Deadlines configured on all client channels
- [ ] Keep-alive settings tuned for the deployment environment
- [ ] Health service enabled for load balancer and mesh probes
- [ ] Max message size limits set to prevent memory exhaustion

### Observability

- [ ] Logging interceptor captures method, status, and duration
- [ ] Metrics exported to monitoring system (Prometheus/Micrometer)
- [ ] Distributed tracing propagated via interceptors (OpenTelemetry)
- [ ] Reflection service disabled in production (or restricted)

### Deployment

- [ ] gRPC server port exposed in Kubernetes service definition
- [ ] Readiness and liveness probes configured with gRPC health check
- [ ] Resource limits set for gRPC server pods
- [ ] Horizontal Pod Autoscaler configured based on gRPC metrics
