# Kotlin Coroutines In-Depth

## Dispatcher Selection

| Dispatcher                         | Thread Pool      | Use Case                              |
| ---------------------------------- | ---------------- | ------------------------------------- |
| `Dispatchers.Default`              | CPU core count   | CPU-bound computation                 |
| `Dispatchers.IO`                   | Up to 64 threads | Blocking I/O (JDBC, file, legacy SDK) |
| `Dispatchers.Main`                 | Main/UI thread   | Android UI updates                    |
| `Dispatchers.Unconfined`           | Caller's thread  | Testing only — never in production    |
| Custom `newFixedThreadPoolContext` | Configurable     | Isolated work for specific service    |

```kotlin
// CPU-bound work
withContext(Dispatchers.Default) {
    computeExpensiveResult()
}

// Blocking I/O
withContext(Dispatchers.IO) {
    jdbcTemplate.query("SELECT * FROM users")
}

// Custom limited dispatcher (throttle concurrency)
val dbDispatcher = Dispatchers.IO.limitedParallelism(10)
withContext(dbDispatcher) {
    repository.save(entity)
}
```

## Structured Concurrency

```kotlin
// coroutineScope — all-or-nothing: any child failure cancels all siblings
suspend fun fetchDashboard(userId: Long): Dashboard = coroutineScope {
    val profile = async { userService.getProfile(userId) }
    val orders = async { orderService.getRecentOrders(userId) }

    Dashboard(profile.await(), orders.await())
    // If either fails, the other is cancelled automatically
}

// supervisorScope — child failures do NOT cancel siblings
suspend fun fetchDashboardWithFallback(userId: Long): Dashboard = supervisorScope {
    val profile = async { userService.getProfile(userId) }
    val orders = async {
        try { orderService.getRecentOrders(userId) }
        catch (e: Exception) { emptyList() }  // Fallback — does not cancel profile
    }

    Dashboard(profile.await(), orders.await())
}
```

## Exception Propagation

```kotlin
// Launch: exceptions propagate to parent (crash scope)
scope.launch {
    throw RuntimeException("Crash")  // Parent scope is cancelled
}

// Async: exceptions are deferred to await()
val deferred = scope.async {
    throw RuntimeException("Deferred crash")
}
try {
    deferred.await()  // Exception thrown here
} catch (e: RuntimeException) {
    // Handle here
}
```

## Coroutine Exception Handler

```kotlin
// Top-level exception handler (last resort, not for recovery)
val handler = CoroutineExceptionHandler { _, exception ->
    log.error("Uncaught coroutine exception", exception)
}

val scope = CoroutineScope(SupervisorJob() + handler)
scope.launch {
    throw RuntimeException("Handled by CoroutineExceptionHandler")
}
```

## Cancellation Rules

```kotlin
// CancellationException is special — do NOT catch it
suspend fun process() {
    try {
        longRunningWork()
    } catch (e: CancellationException) {
        throw e  // Must rethrow — swallowing breaks structured concurrency
    } catch (e: Exception) {
        log.error("Processing failed", e)
    }
}

// Check for cancellation in CPU-bound loops
suspend fun computeHeavy(data: List<Item>) {
    for (item in data) {
        ensureActive()  // Throws CancellationException if cancelled
        process(item)
    }
}
```

## Coroutine Rules

- Never use `GlobalScope` — it breaks structured concurrency and causes memory leaks
- Never use `runBlocking` in request handlers — it blocks the calling thread
- Always use `supervisorScope` when child failures should be independent
- Always call `ensureActive()` or `yield()` in CPU-bound loops for cancellation support
- Use `withTimeout` for coroutine-level timeout, not `Thread.sleep`-based approaches