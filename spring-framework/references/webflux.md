# Spring WebFlux and Coroutines

## WebFlux vs MVC Selection

| Scenario                                    | WebFlux | MVC  |
| ------------------------------------------- | ------- | ---- |
| High concurrency with I/O-bound workloads   | Yes     |      |
| Streaming data (SSE, WebSocket)             | Yes     |      |
| CPU-bound workloads                         |         | Yes  |
| Blocking libraries (JDBC, legacy SDK)       |         | Yes  |
| Team unfamiliar with reactive programming   |         | Yes  |
| Microservice gateway or proxy               | Yes     |      |
| Simple CRUD with moderate traffic           |         | Yes  |

### Key Constraint

- WebFlux runs on a small, fixed thread pool (event loop)
- **Never block the event loop** — blocking calls (JDBC, `Thread.sleep`, synchronized) will starve all requests
- If you must use blocking libraries, use `Dispatchers.IO` or `Schedulers.boundedElastic()`

## Kotlin Coroutines with WebFlux

### Controller Layer

```kotlin
@RestController
@RequestMapping("/api/v1/users")
class UserController(
    private val userService: UserService
) {
    // suspend fun for single result
    @GetMapping("/{id}")
    suspend fun getUser(@PathVariable id: Long): UserResponse =
        userService.findById(id)

    // Flow for streaming results
    @GetMapping
    fun listUsers(): Flow<UserResponse> =
        userService.findAll()

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    suspend fun createUser(
        @Valid @RequestBody request: CreateUserRequest
    ): UserResponse =
        userService.create(request)
}
```

### Service Layer

```kotlin
@Service
class UserService(
    private val userRepository: UserRepository,
    private val notificationClient: NotificationClient
) {
    suspend fun findById(id: Long): UserResponse =
        userRepository.findById(id)
            ?.toResponse()
            ?: throw EntityNotFoundException("User", id)

    fun findAll(): Flow<UserResponse> =
        userRepository.findAll().map { it.toResponse() }

    suspend fun create(request: CreateUserRequest): UserResponse {
        val user = userRepository.save(request.toEntity())
        notificationClient.sendWelcome(user.id)
        return user.toResponse()
    }
}
```

### Repository Layer (R2DBC)

```kotlin
interface UserRepository : CoroutineCrudRepository<User, Long> {
    suspend fun findByEmail(email: String): User?
    fun findByStatus(status: UserStatus): Flow<User>

    @Query("SELECT * FROM users WHERE name LIKE :keyword%")
    fun searchByNamePrefix(keyword: String): Flow<User>
}
```

### Coroutine Rules

- Controller: `suspend fun` for single results, `Flow<T>` return for streaming
- Service: `suspend fun` for business logic, `Flow<T>` for collection operations
- Repository: Use `CoroutineCrudRepository` (not `ReactiveCrudRepository`)
- Never use `runBlocking` in request-handling code — it blocks the event loop
- Use `coroutineScope` for structured parallel operations

## Parallel Execution

### Structured Concurrency

```kotlin
// All-or-nothing: any failure cancels siblings
suspend fun getDashboard(userId: Long): DashboardResponse = coroutineScope {
    val profile = async { userService.findById(userId) }
    val orders = async { orderService.findRecentByUserId(userId) }
    val notifications = async { notificationService.findUnread(userId) }

    DashboardResponse(
        profile = profile.await(),
        orders = orders.await(),
        notifications = notifications.await()
    )
}

// Independent failures: child failure does not cancel siblings
suspend fun getDashboardWithFallback(userId: Long): DashboardResponse = supervisorScope {
    val profile = async { userService.findById(userId) }
    val orders = async {
        try { orderService.findRecentByUserId(userId) }
        catch (e: Exception) { emptyList() }
    }

    DashboardResponse(profile.await(), orders.await())
}
```

### Rules

- Always use `coroutineScope` or `supervisorScope` — never `GlobalScope`
- Use `async` + `await` for parallel I/O operations
- Use `supervisorScope` when child failures should not cancel siblings

## Flow Patterns

### Flow Operators

```kotlin
// Transform and filter
fun findActiveUsers(): Flow<UserResponse> =
    userRepository.findAll()
        .filter { it.status == UserStatus.ACTIVE }
        .map { it.toResponse() }

// Batch processing
suspend fun batchProcess(items: Flow<Item>) {
    items.toList()
        .chunked(100)
        .forEach { batch -> processBatch(batch) }
}

// Error handling
fun fetchData(): Flow<Data> =
    dataRepository.findAll()
        .catch { e ->
            log.error("Failed to fetch data", e)
            emit(Data.fallback())
        }
        .onCompletion { cause ->
            if (cause != null) log.warn("Flow completed with error", cause)
        }

// FlatMap for nested flows
fun getUserOrders(): Flow<OrderResponse> =
    userRepository.findAll()
        .flatMapMerge { user -> orderService.findByUserId(user.id) }

// Rate limiting
fun fetchWithRateLimit(): Flow<Data> =
    dataRepository.findAll()
        .onEach { delay(100) } // 100ms between items
```

### Flow vs List

| Use Case                         | Recommended |
| -------------------------------- | ----------- |
| Large result set (1000+ items)   | `Flow`      |
| Need all items before processing | `List`      |
| Streaming to client (SSE)        | `Flow`      |
| Small, bounded collection        | `List`      |
| Intermediate pipeline operations | `Flow`      |

### Flow Rules

- Prefer `Flow` over `List` for database queries that may return large result sets
- `Flow` is cold — collection does not start until terminal operator
- Never collect a `Flow` inside another `Flow.map` — use `flatMapConcat` or `flatMapMerge`
- Use `flowOn(Dispatchers.IO)` to shift blocking operations off the event loop

## WebClient (HTTP Client)

### Configuration

```kotlin
@Configuration
class WebClientConfig(
    private val props: HttpClientProperties
) {
    @Bean
    fun externalApiWebClient(): WebClient =
        WebClient.builder()
            .baseUrl(props.baseUrl)
            .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .clientConnector(
                ReactorClientHttpConnector(
                    HttpClient.create()
                        .responseTimeout(props.readTimeout)
                        .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, props.connectTimeout.toMillis().toInt())
                )
            )
            .build()
}
```

### Coroutine-Style Usage

```kotlin
@Component
class PaymentClient(
    private val webClient: WebClient
) {
    suspend fun getPayment(paymentId: String): PaymentResponse =
        webClient.get()
            .uri("/payments/{id}", paymentId)
            .retrieve()
            .awaitBody()

    suspend fun createPayment(request: PaymentRequest): PaymentResponse =
        webClient.post()
            .uri("/payments")
            .bodyValue(request)
            .retrieve()
            .onStatus(HttpStatusCode::is4xxClientError) { response ->
                Mono.error(PaymentValidationException("Payment validation failed"))
            }
            .awaitBody()

    suspend fun listPayments(): List<PaymentResponse> =
        webClient.get()
            .uri("/payments")
            .retrieve()
            .bodyToFlow<PaymentResponse>()
            .toList()
}
```

### Streaming Response

```kotlin
suspend fun streamEvents(): Flow<Event> =
    webClient.get()
        .uri("/events/stream")
        .retrieve()
        .bodyToFlow<Event>()

// SSE streaming
suspend fun streamSSE(): Flow<ServerSentEvent<Data>> =
    webClient.get()
        .uri("/events")
        .accept(MediaType.TEXT_EVENT_STREAM)
        .retrieve()
        .bodyToFlow<ServerSentEvent<Data>>()
```

### WebClient Rules

- Use `awaitBody()`, `awaitExchange()` for coroutine integration
- Never use `block()` — it defeats the purpose of non-blocking
- Configure timeouts explicitly — WebClient defaults may be infinite
- Use `onStatus` for HTTP error mapping before `awaitBody()`
- Use `bodyToFlow()` for streaming responses

## R2DBC Database Access

### Dependencies

```kotlin
// build.gradle.kts
implementation("org.springframework.boot:spring-boot-starter-data-r2dbc")
runtimeOnly("org.postgresql:r2dbc-postgresql")
// Or: runtimeOnly("io.asyncer:r2dbc-mysql")
```

### Configuration

```yaml
spring:
  r2dbc:
    url: r2dbc:postgresql://${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME}
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}
    pool:
      initial-size: ${R2DBC_POOL_INITIAL:5}
      max-size: ${R2DBC_POOL_MAX:20}
      max-idle-time: ${R2DBC_POOL_MAX_IDLE:30m}
```

### Entity Mapping

```kotlin
@Table("users")
data class User(
    @Id
    val id: Long? = null,
    val name: String,
    val email: String,
    val status: UserStatus = UserStatus.ACTIVE,
    val createdAt: Instant = Instant.now(),
    val updatedAt: Instant = Instant.now()
)
```

### Custom Repository Methods

```kotlin
interface UserRepository : CoroutineCrudRepository<User, Long> {
    suspend fun findByEmail(email: String): User?
    fun findByStatus(status: UserStatus): Flow<User>

    @Query("SELECT * FROM users WHERE name LIKE :keyword% ORDER BY name")
    fun searchByNamePrefix(keyword: String): Flow<User>

    @Query("SELECT u.* FROM users u JOIN orders o ON u.id = o.user_id WHERE o.id = :orderId")
    suspend fun findByOrderId(orderId: Long): User?
}

// Using DatabaseClient for complex queries
@Repository
class CustomUserRepository(
    private val databaseClient: DatabaseClient
) {
    suspend fun findWithOrderCount(userId: Long): UserWithOrderCount? =
        databaseClient.sql("""
            SELECT u.*, COUNT(o.id) as order_count
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            WHERE u.id = :userId
            GROUP BY u.id
        """)
            .bind("userId", userId)
            .map { row ->
                UserWithOrderCount(
                    id = row.get("id", Long::class.java)!!,
                    name = row.get("name", String::class.java)!!,
                    orderCount = row.get("order_count", Long::class.java) ?: 0L
                )
            }
            .awaitSingleOrNull()
}
```

### R2DBC Rules

- R2DBC does not support lazy loading or JPA relationships — fetch joins manually
- Use `@Query` with SQL for join queries — no JPQL support
- Use `DatabaseClient` for complex queries that `CoroutineCrudRepository` cannot express
- Schema migration still uses Flyway/Liquibase (blocking at startup is acceptable)

## Server-Sent Events (SSE)

### Server Side

```kotlin
@GetMapping("/stream", produces = [MediaType.TEXT_EVENT_STREAM_VALUE])
fun streamEvents(): Flow<ServerSentEvent<EventData>> =
    eventService.subscribe()
        .map { event ->
            ServerSentEvent.builder(event)
                .id(event.id)
                .event(event.type)
                .build()
        }

// With keepalive
@GetMapping("/events")
fun streamWithKeepalive(): Flow<ServerSentEvent<Any>> = flow {
    while (currentCoroutineContext().isActive) {
        val event = eventQueue.receiveOrNull() ?: HeartbeatEvent()
        emit(ServerSentEvent.builder<Any>()
            .event(event.type)
            .data(event)
            .build())
    }
}
```

### Client Side (WebClient)

```kotlin
suspend fun subscribeToEvents(): Flow<Event> =
    webClient.get()
        .uri("/events")
        .accept(MediaType.TEXT_EVENT_STREAM)
        .retrieve()
        .bodyToFlow<ServerSentEvent<Event>>()
        .mapNotNull { it.data() }
```

## Error Handling

### Global Exception Handler

```kotlin
@RestControllerAdvice
class GlobalExceptionHandler {

    @ExceptionHandler(EntityNotFoundException::class)
    suspend fun handleNotFound(e: EntityNotFoundException): ResponseEntity<ErrorResponse> {
        log.warn("Entity not found: ${e.message}")
        return ResponseEntity
            .status(HttpStatus.NOT_FOUND)
            .body(ErrorResponse(
                code = "ENTITY_NOT_FOUND",
                message = e.message ?: "Entity not found"
            ))
    }

    @ExceptionHandler(WebClientResponseException::class)
    suspend fun handleWebClientException(e: WebClientResponseException): ResponseEntity<ErrorResponse> {
        log.error("External API error: ${e.statusCode}", e)
        return ResponseEntity
            .status(HttpStatus.BAD_GATEWAY)
            .body(ErrorResponse(
                code = "EXTERNAL_API_ERROR",
                message = "External service error"
            ))
    }

    @ExceptionHandler(TimeoutCancellationException::class)
    suspend fun handleTimeout(e: TimeoutCancellationException): ResponseEntity<ErrorResponse> {
        log.warn("Request timeout", e)
        return ResponseEntity
            .status(HttpStatus.GATEWAY_TIMEOUT)
            .body(ErrorResponse(
                code = "TIMEOUT",
                message = "Request timed out"
            ))
    }
}
```

### Timeout Handling

```kotlin
suspend fun fetchWithTimeout(): Data =
    withTimeout(5000L) {
        externalClient.fetchData()
    }

// With fallback
suspend fun fetchSafely(): Data? =
    try {
        withTimeout(5000L) { externalClient.fetchData() }
    } catch (e: TimeoutCancellationException) {
        log.warn("External API timeout", e)
        null
    }
```

## Testing

### Controller Test

```kotlin
@WebFluxTest(UserController::class)
@Import(TestSecurityConfig::class)
class UserControllerTest(
    @Autowired private val webTestClient: WebTestClient,
    @MockkBean private val userService: UserService
) {
    @Test
    fun `should return user by id`() {
        coEvery { userService.findById(1L) } returns userResponse

        webTestClient.get()
            .uri("/api/v1/users/1")
            .exchange()
            .expectStatus().isOk
            .expectBody<UserResponse>()
            .isEqualTo(userResponse)
    }

    @Test
    fun `should create user`() {
        coEvery { userService.create(any()) } returns userResponse

        webTestClient.post()
            .uri("/api/v1/users")
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(createRequest)
            .exchange()
            .expectStatus().isCreated
            .expectBody<UserResponse>()
            .isEqualTo(userResponse)
    }
}
```

### Service Test

```kotlin
@ExtendWith(MockKExtension::class)
class UserServiceTest {
    @MockK
    private lateinit var userRepository: UserRepository

    @InjectMockKs
    private lateinit var userService: UserService

    @Test
    fun `should find user by id`() = runTest {
        coEvery { userRepository.findById(1L) } returns user

        val result = userService.findById(1L)

        assertThat(result).isEqualTo(userResponse)
        coVerify { userRepository.findById(1L) }
    }

    @Test
    fun `should throw when user not found`() = runTest {
        coEvery { userRepository.findById(999L) } returns null

        assertThrows<EntityNotFoundException> {
            userService.findById(999L)
        }
    }
}
```

### Flow Test (Turbine)

```kotlin
@Test
fun `should stream users`() = runTest {
    every { userRepository.findAll() } returns flowOf(user1, user2, user3)

    userService.findAll()
        .test {
            assertThat(awaitItem()).isEqualTo(user1.toResponse())
            assertThat(awaitItem()).isEqualTo(user2.toResponse())
            assertThat(awaitItem()).isEqualTo(user3.toResponse())
            awaitComplete()
        }
}
```

## Blocking Code Integration

### When Blocking is Unavoidable

```kotlin
// Shift blocking call to IO dispatcher
suspend fun legacyOperation(): Result =
    withContext(Dispatchers.IO) {
        legacyBlockingClient.call()
    }

// In Flow pipeline — flowOn affects operators ABOVE it
fun processWithBlocking(): Flow<Data> =
    sourceFlow
        .map { blockingTransform(it) }
        .flowOn(Dispatchers.IO)

// Bounded elastic for limited concurrency
val boundedDispatcher = Dispatchers.IO.limitedParallelism(10)
suspend fun limitedBlocking(): Result =
    withContext(boundedDispatcher) {
        blockingCall()
    }
```

### Rules

- Use `Dispatchers.IO` for JDBC, file I/O, or legacy blocking SDK calls
- Never call blocking code on `Dispatchers.Default` or the event loop
- If most of the application is blocking, use Spring MVC instead of WebFlux
- Use `limitedParallelism` to prevent thread pool exhaustion

## WebFlux Anti-Patterns

- Using `runBlocking` in request handlers (blocks event loop)
- Using `block()` on Mono/Flux (defeats non-blocking purpose)
- Mixing Reactor API (`Mono`, `Flux`) with Coroutines without bridge functions
- Using `GlobalScope.launch` (unstructured concurrency, memory leaks)
- Catching `CancellationException` without rethrowing (breaks structured concurrency)
- Using JDBC/JPA with WebFlux (blocking drivers on non-blocking runtime)
- Creating unbounded `Flow` without backpressure consideration
- Using `Thread.sleep()` instead of `delay()` in coroutine context
- Calling `toList()` on large Flows (defeats streaming purpose)
- Not configuring WebClient timeouts (may hang indefinitely)