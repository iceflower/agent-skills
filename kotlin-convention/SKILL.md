---
name: kotlin-convention
description: >-
  Kotlin coding conventions, idioms, and language-specific best practices.
  Covers null safety, data class, sealed class, enum class, extension functions,
  coroutines, Flow, when expression, scope functions (let, run, apply, also),
  collection operations, and Kotlin DSL patterns.
  Use when writing or reviewing Kotlin code, designing domain models with
  sealed hierarchies, or implementing asynchronous logic with coroutines and Flow.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# Kotlin Convention Rules

## 1. Null Safety

### Preferred Patterns

```kotlin
// Use safe call + Elvis for default values
val name = user?.name ?: "Unknown"

// Use requireNotNull for preconditions (throws IllegalArgumentException)
val userId = requireNotNull(request.userId) { "userId must not be null" }

// Use checkNotNull for state validation (throws IllegalStateException)
val session = checkNotNull(currentSession) { "Session not initialized" }

// Use let for null-conditional execution
user?.let { sendNotification(it) }
```

### Null Anti-Patterns

```kotlin
// Never use !! in production code
val name = user!!.name  // Bad: crashes with NPE

// Avoid unnecessary null types
fun getUser(): User? // Bad if it never returns null
fun getUser(): User  // Good: non-null return when guaranteed
```

---

## 2. Data Class vs Class

| Use | When |
| --- | --- |
| `data class` | DTOs, request/response objects, value objects, config properties |
| `class` | Services, repositories, entities with mutable state, classes with complex behavior |
| `value class` | Single-field wrappers for type safety (IDs, amounts) |
| `sealed class` | Restricted type hierarchies (states, results, error types) |
| `object` | Singletons, utility collections, companion factories |

```kotlin
// Value class for type-safe IDs
@JvmInline
value class UserId(val value: Long)

// Sealed class for result types
sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Failure(val error: ErrorCode) : Result<Nothing>()
}
```

---

## 3. Extension Functions

### Good Use Cases

```kotlin
// Converting between layers (Entity ↔ DTO)
fun User.toResponse() = UserResponse(id = id, name = name, email = email)

// Adding domain-specific utility
fun String.toSlug() = lowercase().replace(Regex("[^a-z0-9]+"), "-").trim('-')

// Scoping to specific contexts (narrowing extension to a domain type)
fun ApiResponse<User>.orThrow(): User =
    if (isSuccess) data else throw ApiException(errorCode, errorMessage)
```

### Extension Anti-Patterns

- Extension functions that access private/internal state of the receiver
- Extension functions that modify mutable state
- Overusing extensions where a regular method on the class is more appropriate

---

## 4. Collection Operations

### Prefer Kotlin Standard Library

```kotlin
// Transforming
val names = users.map { it.name }
val activeUsers = users.filter { it.isActive }
val userMap = users.associateBy { it.id }

// Aggregating
val totalAmount = orders.sumOf { it.amount }
val grouped = orders.groupBy { it.status }

// Null-safe collections
val firstActive = users.firstOrNull { it.isActive }
val nicknames = users.mapNotNull { it.nickname }
```

### Performance Considerations

- Use `asSequence()` for chains of 3+ operations on large collections
- Use `buildList` / `buildMap` for constructing collections conditionally
- Avoid `flatMap` inside loops — prefer restructuring

---

## 5. Coroutines

### Structured Concurrency

```kotlin
// Use coroutineScope for parallel operations that must all succeed
suspend fun fetchDashboard(userId: Long): Dashboard = coroutineScope {
    val profile = async { userService.getProfile(userId) }
    val orders = async { orderService.getRecentOrders(userId) }
    Dashboard(profile.await(), orders.await())
}
```

### CoroutineScope Design

| Scenario | Scope Strategy |
| --- | --- |
| ViewModel / UI layer | `viewModelScope` (auto-cancelled on clear) |
| Service with managed lifecycle | Custom `CoroutineScope(SupervisorJob() + dispatcher)` — cancel in `close()` |
| One-shot suspend call | `coroutineScope { }` — no custom scope needed |
| Background work surviving caller | `CoroutineScope` tied to component lifecycle |

### suspend Function Rules

- Mark a function `suspend` only if it actually calls other suspend functions or uses `delay`
- Never wrap blocking I/O in `suspend` without switching dispatcher — use `withContext(Dispatchers.IO)`
- Keep suspend functions main-safe: callers should not need to know which dispatcher to use

```kotlin
// Good: dispatcher switching is the callee's responsibility
suspend fun loadUser(id: Long): User = withContext(Dispatchers.IO) {
    userRepository.findById(id) ?: throw UserNotFoundException(id)
}
```

### Exception Handling

| Pattern | Use When |
| --- | --- |
| `coroutineScope` | All children must succeed — one failure cancels siblings |
| `supervisorScope` | Children are independent — one failure should not cancel others |
| `SupervisorJob()` in scope | Long-lived scope where launched jobs are independent |
| `CoroutineExceptionHandler` | Top-level last-resort logging for uncaught exceptions |

```kotlin
// SupervisorJob for independent child jobs
private val scope = CoroutineScope(
    SupervisorJob() + Dispatchers.Default + exceptionHandler
)
```

### Spring Integration

- For Spring-specific coroutine and WebFlux patterns, see `spring-framework` skill
- For detailed coroutine examples, see [references/coroutines-and-flow.md](references/coroutines-and-flow.md)

---

## 6. Flow

### StateFlow vs SharedFlow

| Criteria | `StateFlow` | `SharedFlow` |
| --- | --- | --- |
| Has current value | Yes (`.value`) | No |
| Replay | Always 1 (latest) | Configurable (`replay` param) |
| Equality check | Skips duplicate values | Emits all values |
| Use case | UI state, current status | Events, notifications, commands |

```kotlin
// StateFlow: always has a current value, skips duplicates
private val _state = MutableStateFlow(UiState.Loading)
val state: StateFlow<UiState> = _state.asStateFlow()

// SharedFlow: fire-and-forget events, no initial value
private val _events = MutableSharedFlow<UiEvent>(extraBufferCapacity = 64)
val events: SharedFlow<UiEvent> = _events.asSharedFlow()
```

### Cold vs Hot Flow

| Type | Examples | Behavior |
| --- | --- | --- |
| Cold | `flow { }`, `channelFlow { }` | Starts on collection, each collector gets independent stream |
| Hot | `StateFlow`, `SharedFlow` | Active regardless of collectors, shared among subscribers |

### Flow Operator Essentials

```kotlin
repository.observeAll()
    .map { items -> items.filter { it.isActive } }   // transform
    .distinctUntilChanged()                            // skip duplicates
    .catch { e -> emit(emptyList()) }                  // handle upstream errors
    .onEach { items -> logger.debug("Got ${items.size} items") }
    .flowOn(Dispatchers.IO)                            // upstream dispatcher
```

### Flow Testing (with Turbine)

```kotlin
@Test
fun `should emit active users only`() = runTest {
    sut.observeActiveUsers().test {
        val result = awaitItem()
        assertThat(result).allMatch { it.isActive }
        awaitComplete()
    }
}
```

- For extended Flow examples and patterns, see [references/coroutines-and-flow.md](references/coroutines-and-flow.md)

---

## 7. Scope Functions

### Selection Guide

| Function | Object ref | Return value | Use case |
| --- | --- | --- | --- |
| `let` | `it` | Lambda result | Null-check execution, mapping |
| `run` | `this` | Lambda result | Object config + compute result |
| `apply` | `this` | Object itself | Object initialization / builder |
| `also` | `it` | Object itself | Side effects (logging, validation) |
| `with` | `this` | Lambda result | Calling multiple methods on an object |

### Chaining Rules

- Maximum **2 scope functions** chained — beyond that, extract to local variables
- Never nest scope functions more than 1 level deep
- Prefer `?.let` only for **null-conditional** logic — do not use `let` on non-null values without reason

```kotlin
// Good: clear scope function usage
val user = userRepository.findById(id)?.also {
    logger.info("Found user: ${it.name}")
}

// Good: apply for initialization
val config = ServerConfig().apply {
    host = "0.0.0.0"
    port = 8080
}

// Bad: unnecessary nesting
user?.let { u -> u.address?.let { a -> a.city?.let { println(it) } } }
// Good: flatten with safe calls
val city = user?.address?.city ?: return
println(city)
```

- For scope function anti-patterns, see [references/scope-functions-and-dsl.md](references/scope-functions-and-dsl.md)

---

## 8. Kotlin DSL

### Type-Safe Builder Pattern

Use `@DslMarker` to prevent accidental access to outer receiver scopes:

```kotlin
@DslMarker
annotation class ConfigDsl

@ConfigDsl
class ServerConfigBuilder {
    var host: String = "localhost"
    var port: Int = 8080

    fun database(block: DatabaseConfigBuilder.() -> Unit) { /* ... */ }
}

fun serverConfig(block: ServerConfigBuilder.() -> Unit): ServerConfig =
    ServerConfigBuilder().apply(block).build()
```

### DSL Design Rules

- Always annotate builder classes with a `@DslMarker` annotation to enforce scope control
- Provide a top-level entry function (e.g., `html { }`, `serverConfig { }`) that returns the built object
- Keep DSL blocks focused — each builder handles one concern
- Make required properties fail-fast with clear error messages (not silent defaults)

- For detailed DSL examples, see [references/scope-functions-and-dsl.md](references/scope-functions-and-dsl.md)

---

## 9. Naming Conventions

| Element | Convention | Example |
| --- | --- | --- |
| Class | PascalCase | `UserService`, `OrderResponse` |
| Function | camelCase | `findByEmail`, `calculateTotal` |
| Property | camelCase | `userName`, `isActive` |
| Constant | SCREAMING_SNAKE | `MAX_RETRY_COUNT`, `DEFAULT_PAGE_SIZE` |
| Package | lowercase dot-separated | `com.example.app` |
| Enum value | SCREAMING_SNAKE | `PENDING`, `IN_PROGRESS` |

---

## Additional References

- For Kotlin version migration (1.4 → 2.3), see [references/migration.md](references/migration.md)
- For coroutine and Flow detailed examples, see [references/coroutines-and-flow.md](references/coroutines-and-flow.md)
- For scope function anti-patterns and DSL examples, see [references/scope-functions-and-dsl.md](references/scope-functions-and-dsl.md)

## Related Skills

- For TypeScript coding conventions, see `typescript-convention` skill
