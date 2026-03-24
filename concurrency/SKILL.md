---
name: concurrency
description: >-
  JVM concurrency rules including thread safety, synchronization tools,
  Executor framework, CompletableFuture, Kotlin coroutines, and virtual threads.
  Use when writing concurrent or parallel code.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# JVM Concurrency Rules

## 1. Thread Safety Principles

### Core Rule: Minimize Shared Mutable State

| Strategy                 | Risk Level | Use Case                                |
| ------------------------ | ---------- | --------------------------------------- |
| Immutable objects        | Lowest     | Default choice for all shared data      |
| Thread-local confinement | Low        | Per-thread state (request context)      |
| Concurrent collections   | Medium     | Shared read-write data structures       |
| Explicit synchronization | High       | Complex invariants across multiple vars |

### Immutability First

```java
// Java — immutable record (thread-safe by design)
public record OrderSnapshot(
    Long orderId,
    BigDecimal amount,
    OrderStatus status,
    List<String> itemIds  // Must also be immutable
) {
    public OrderSnapshot {
        itemIds = List.copyOf(itemIds);  // Defensive copy
    }
}
```

```kotlin
// Kotlin — data class with val properties
data class OrderSnapshot(
    val orderId: Long,
    val amount: BigDecimal,
    val status: OrderStatus,
    val itemIds: List<String>  // Kotlin List is read-only
)
```

### Thread Safety Design Rules

- Make fields `final` / `val` by default — mutable fields require explicit justification
- Return unmodifiable collections from shared objects — never expose internal mutable state
- If a class is designed to be shared across threads, document it explicitly
- If a class is NOT thread-safe, document that too — do not leave ambiguity

---

## 2. JVM Memory Model Essentials

### Happens-Before Relationships

The Java Memory Model (JMM) defines **happens-before** as the guarantee that memory writes by one thread are visible to reads by another thread.

| Action A                       | Happens-Before Action B                |
| ------------------------------ | -------------------------------------- |
| `synchronized` block exit      | `synchronized` block entry (same lock) |
| `volatile` write               | `volatile` read (same variable)        |
| `Thread.start()` call          | First action in started thread         |
| Thread termination             | `Thread.join()` return                 |
| `Executor.submit()`            | Task execution start                   |
| `CountDownLatch.countDown()`   | `CountDownLatch.await()` return        |
| `CompletableFuture.complete()` | Dependent stage execution              |

### Visibility

```java
// Bad: no visibility guarantee — reader may never see updated value
class Broken {
    private boolean running = true;  // Not volatile, not synchronized
    void stop() { running = false; }
    void run() { while (running) { /* may loop forever */ } }
}

// Good: volatile guarantees visibility
class Fixed {
    private volatile boolean running = true;
    void stop() { running = false; }
    void run() { while (running) { /* sees update */ } }
}
```

### Atomicity

- Single reads/writes of `int`, `float`, `boolean`, references are atomic
- `long` and `double` are NOT atomic on 32-bit JVMs unless `volatile`
- Compound operations (`check-then-act`, `read-modify-write`) are NEVER atomic without synchronization

```java
// Bad: compound operation is not atomic
if (!map.containsKey(key)) {
    map.put(key, value);  // Race condition: another thread may insert between check and put
}

// Good: use atomic operation
map.putIfAbsent(key, value);
```

### Publication and Safe Construction

```java
// Bad: publishing reference before construction completes
class UnsafePublish {
    private static UnsafePublish instance;
    private final int value;

    public UnsafePublish() {
        instance = this;  // Escaping 'this' before constructor finishes
        value = 42;       // Another thread may see value = 0
    }
}

// Good: safe publication via volatile or final field
class SafePublish {
    private static volatile SafePublish instance;
    private final int value;

    public SafePublish() {
        value = 42;
        // Do not publish 'this' during construction
    }
}
```

---

## 3. Synchronization Tool Selection

### Decision Guide

| Requirement                        | Recommended Tool                                    |
| ---------------------------------- | --------------------------------------------------- |
| Simple mutual exclusion            | `synchronized` (Java) / `Mutex` (Kotlin coroutines) |
| Need tryLock, timed lock, fairness | `ReentrantLock`                                     |
| Read-heavy, write-rare             | `ReentrantReadWriteLock` or `StampedLock`           |
| Single atomic counter/flag         | `AtomicInteger`, `AtomicBoolean`, etc.              |
| Atomic reference swap              | `AtomicReference`, `VarHandle`                      |
| Multiple variables as single state | `synchronized` block or immutable snapshot          |
| High-contention counter            | `LongAdder` (not `AtomicLong`)                      |
| Thread-safe map                    | `ConcurrentHashMap`                                 |
| Thread-safe queue                  | `ConcurrentLinkedQueue`, `LinkedBlockingQueue`      |
| Coordinating threads               | `CountDownLatch`, `CyclicBarrier`, `Phaser`         |
| Semaphore-based access control     | `Semaphore`                                         |

### synchronized vs ReentrantLock

| Feature                 | `synchronized`       | `ReentrantLock`         |
| ----------------------- | -------------------- | ----------------------- |
| Automatic release       | Yes (block exit)     | No (must use `finally`) |
| Try-lock (non-blocking) | No                   | Yes (`tryLock()`)       |
| Timed lock              | No                   | Yes (`tryLock(time)`)   |
| Fairness policy         | No                   | Yes (constructor param) |
| Multiple conditions     | No (single wait set) | Yes (`newCondition()`)  |
| Virtual thread pinning  | Yes (Java 21-23)     | No                      |
| Performance             | Optimized by JVM     | Slightly more overhead  |

```java
// synchronized — simple, automatic release
synchronized (lock) {
    balance += amount;
}

// ReentrantLock — always use try-finally
ReentrantLock lock = new ReentrantLock();
lock.lock();
try {
    balance += amount;
} finally {
    lock.unlock();  // Must always unlock
}
```

### Concurrent Collections

| Collection              | Thread-Safe Alternative         | Notes                           |
| ----------------------- | ------------------------------- | ------------------------------- |
| `HashMap`               | `ConcurrentHashMap`             | Lock striping, high concurrency |
| `TreeMap`               | `ConcurrentSkipListMap`         | Sorted, concurrent              |
| `ArrayList`             | `CopyOnWriteArrayList`          | Read-heavy, rare writes         |
| `HashSet`               | `ConcurrentHashMap.newKeySet()` | Concurrent set                  |
| `LinkedList` (as queue) | `ConcurrentLinkedQueue`         | Non-blocking queue              |
| `PriorityQueue`         | `PriorityBlockingQueue`         | Blocking priority queue         |

### Atomic Classes

```java
// AtomicInteger — lock-free counter
private final AtomicInteger requestCount = new AtomicInteger(0);
requestCount.incrementAndGet();

// LongAdder — better than AtomicLong under high contention
private final LongAdder totalBytes = new LongAdder();
totalBytes.add(bytesReceived);
long total = totalBytes.sum();

// AtomicReference — lock-free reference swap
private final AtomicReference<Config> config = new AtomicReference<>(initialConfig);
config.compareAndSet(oldConfig, newConfig);
```

---

## 4. Executor Framework

### ThreadPoolExecutor Configuration

```java
// Core parameters
ThreadPoolExecutor executor = new ThreadPoolExecutor(
    corePoolSize,       // Threads kept alive even when idle
    maximumPoolSize,    // Maximum threads allowed
    keepAliveTime,      // Idle time before non-core threads terminate
    TimeUnit.SECONDS,
    workQueue,          // Queue for tasks when all core threads are busy
    threadFactory,      // Custom thread naming
    rejectionHandler    // Policy when pool and queue are full
);
```

### Pool Sizing Guidelines

| Workload Type | Formula                              | Rationale                       |
| ------------- | ------------------------------------ | ------------------------------- |
| CPU-bound     | `N_threads = N_cpu + 1`              | Minimal context switching       |
| I/O-bound     | `N_threads = N_cpu * (1 + W/C)`      | W = wait time, C = compute time |
| Mixed         | Separate pools for CPU and I/O tasks | Prevents I/O blocking CPU work  |

- `N_cpu = Runtime.getRuntime().availableProcessors()`
- For typical web applications (I/O-bound): 2x-4x CPU core count
- Always benchmark with realistic load — formulas are starting points

### Work Queue Selection

| Queue Type              | Behavior                        | Use Case                       |
| ----------------------- | ------------------------------- | ------------------------------ |
| `SynchronousQueue`      | No buffering, direct handoff    | Cached thread pool             |
| `LinkedBlockingQueue`   | Unbounded (or bounded) FIFO     | Fixed thread pool              |
| `ArrayBlockingQueue`    | Bounded FIFO, contiguous memory | Bounded pool with backpressure |
| `PriorityBlockingQueue` | Priority ordering               | Priority-based scheduling      |

### Rejection Policies

| Policy                | Behavior                           | Use Case                        |
| --------------------- | ---------------------------------- | ------------------------------- |
| `AbortPolicy`         | Throw `RejectedExecutionException` | Default, fail-fast              |
| `CallerRunsPolicy`    | Execute in caller's thread         | Natural backpressure            |
| `DiscardPolicy`       | Silently discard                   | Lossy is acceptable             |
| `DiscardOldestPolicy` | Discard oldest queued task         | Newest task has higher priority |

### Executor Best Practices

```java
// Named thread factory for debugging
ThreadFactory factory = Thread.ofPlatform()
    .name("order-processor-", 0)
    .daemon(true)
    .factory();

// Graceful shutdown
executor.shutdown();
if (!executor.awaitTermination(30, TimeUnit.SECONDS)) {
    executor.shutdownNow();
}
```

- Always name threads — unnamed threads are impossible to debug in thread dumps
- Always shut down executors — leaked executors prevent JVM shutdown
- Never use `Executors.newCachedThreadPool()` with unbounded task submission — can create thousands of threads
- Never use `Executors.newFixedThreadPool()` with unbounded queue for latency-sensitive work — queue grows without bound

---

## 5. CompletableFuture Patterns

> See [references/completable-future.md](references/completable-future.md) for detailed patterns including composition, error handling, and timeout.

### Key Rules

- Always specify executor for async stages — default `ForkJoinPool.commonPool()` is shared globally
- Never call `join()` or `get()` on event loop or request-handling threads — causes blocking
- Use `thenCompose` (not `thenApply`) when the mapping function returns a `CompletableFuture`
- Handle exceptions at every stage that can fail — unhandled exceptions are silently swallowed
- Use `orTimeout` or `completeOnTimeout` — never wait indefinitely

---

## 6. Kotlin Coroutines In-Depth

> **See [references/kotlin-coroutines.md](references/kotlin-coroutines.md) for detailed patterns including:**
> - Dispatcher selection (Default, IO, Main, custom)
> - Structured concurrency (coroutineScope vs supervisorScope)
> - Exception propagation and handling
> - Cancellation rules

---

## 7. Virtual Threads (Java 21+)

> See [references/virtual-threads.md](references/virtual-threads.md) for detailed patterns including usage examples, caveats, and pinning issues.

### Key Rules

- Virtual threads are cheap — create per task, never pool them
- Blocking operations (JDBC, `Thread.sleep`, file I/O) are fine on virtual threads
- Avoid `synchronized` on Java 21-23 — use `ReentrantLock` (fixed in Java 24+)
- Avoid `ThreadLocal` with large objects — prefer `ScopedValue` (preview)
- Virtual threads do NOT speed up CPU-bound work — they optimize I/O concurrency

---

## 8. Concurrency Bug Patterns

### Race Condition

```java
// Bug: check-then-act without synchronization
if (map.containsKey(key)) {
    return map.get(key);  // Another thread may remove between check and get
}

// Fix: use atomic operation
return map.computeIfAbsent(key, k -> createValue(k));
```

### Deadlock

```java
// Bug: inconsistent lock ordering
// Thread 1: lock(A) → lock(B)
// Thread 2: lock(B) → lock(A)
synchronized (accountA) {
    synchronized (accountB) {
        transfer(accountA, accountB, amount);
    }
}

// Fix: always acquire locks in consistent global order
Account first = accountA.getId() < accountB.getId() ? accountA : accountB;
Account second = accountA.getId() < accountB.getId() ? accountB : accountA;
synchronized (first) {
    synchronized (second) {
        transfer(accountA, accountB, amount);
    }
}
```

### Starvation

```java
// Bug: unfair lock with long-holding writer starves readers
// Readers never get lock because writers keep acquiring it

// Fix: use fair lock or ReadWriteLock
ReentrantReadWriteLock rwLock = new ReentrantReadWriteLock(true);  // fair = true
```

### Livelock

```java
// Bug: two threads keep yielding to each other without progress
// Thread 1: "I see Thread 2 is working, I'll back off"
// Thread 2: "I see Thread 1 is working, I'll back off"

// Fix: add randomized backoff to break symmetry
Thread.sleep(ThreadLocalRandom.current().nextInt(10, 100));
```

### Data Race vs Race Condition

| Term           | Definition                                                              | Example                             |
| -------------- | ----------------------------------------------------------------------- | ----------------------------------- |
| Data race      | Two threads access same memory, at least one writes, no synchronization | Reading `long` while another writes |
| Race condition | Correctness depends on execution order                                  | Check-then-act on shared state      |

- Data races are always bugs — they violate the JMM
- Race conditions are logic bugs — they may work most of the time but fail under contention
- Fixing data races (adding `volatile` / `synchronized`) does NOT always fix race conditions

---

## 9. Concurrency Testing

> **See [references/testing.md](references/testing.md) for detailed patterns including:**
> - Testing strategies (stress testing, deterministic scheduling)
> - JCStress and Lincheck examples
> - CountDownLatch test pattern
> - Coroutine testing

---

## 10. Anti-Patterns

### Synchronization Anti-Patterns

```java
// Bad: synchronizing on mutable field
private Object lock = new Object();  // Can be reassigned
synchronized (lock) { ... }

// Good: use final lock object
private final Object lock = new Object();

// Bad: synchronizing on boxed primitive (shared instance)
synchronized (Integer.valueOf(42)) { ... }  // Shared across JVM

// Bad: synchronizing on String literal (interned, shared)
synchronized ("lock") { ... }

// Good: dedicated private lock object
private final Object lock = new Object();
synchronized (lock) { ... }
```

### Thread Pool Anti-Patterns

```java
// Bad: creating thread per task without limit
new Thread(() -> handleRequest(req)).start();  // Unbounded thread creation

// Bad: unbounded cached pool for unpredictable workload
Executors.newCachedThreadPool();  // Can create Integer.MAX_VALUE threads

// Good: bounded pool with rejection policy
new ThreadPoolExecutor(
    10, 50, 60L, TimeUnit.SECONDS,
    new ArrayBlockingQueue<>(100),
    new ThreadPoolExecutor.CallerRunsPolicy()
);
```

### Other Anti-Patterns

| Anti-Pattern                                       | Problem                                      | Fix                                                     |
| -------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------- |
| `synchronized` everywhere                          | Reduces concurrency, risk of deadlock        | Use concurrent collections or atomic types              |
| Double-checked locking without `volatile`          | Broken under JMM — partially constructed obj | Add `volatile` or use `Lazy` / holder                   |
| `Thread.stop()` / `Thread.suspend()`               | Deprecated — corrupts state                  | Use interrupt-based cancellation                        |
| `ThreadLocal` with thread pools                    | Values leak across tasks if not cleaned      | Always `remove()` in `finally`                          |
| `ThreadLocal` with virtual threads                 | Millions of copies — memory waste            | Use `ScopedValue` (preview)                             |
| Catching `InterruptedException` silently           | Breaks cancellation protocol                 | Restore interrupt: `Thread.currentThread().interrupt()` |
| `synchronized` in virtual thread code (Java 21-23) | Pins carrier thread                          | Use `ReentrantLock` (fixed in Java 24+)                 |
| `runBlocking` in request handlers                  | Blocks calling thread entirely               | Use `suspend fun` or `CompletableFuture`                |
| `GlobalScope.launch`                               | No structured concurrency, memory leaks      | Use `coroutineScope` or `supervisorScope`               |
| Polling with `Thread.sleep` in a loop              | Wastes thread, delays response               | Use `wait/notify`, `Condition`, or async                |
| Ignoring `Future.get()` exceptions                 | Swallowed failures, silent data loss         | Always handle or propagate exceptions                   |

---

## 11. Related Rules

- **Java conventions**: see `java-convention` skill (virtual threads, sealed classes, records)
- **Kotlin conventions**: see `kotlin-convention` skill (coroutines basics, extension functions)
- **Spring WebFlux and Coroutines**: see `spring-framework` skill (non-blocking, Flow, R2DBC)
- **JVM performance**: see `jvm-performance` skill (GC tuning, profiling, memory layout)
- **Spring Framework**: see `spring-framework` skill (`@Async`, `@Scheduled`, event system)

---

## 12. Further Reading

| Topic                    | Resource                                                  |
| ------------------------ | --------------------------------------------------------- |
| JVM memory model         | JSR-133 FAQ, JLS Chapter 17                               |
| Concurrency fundamentals | *Java Concurrency in Practice* (Goetz et al.)             |
| Virtual threads          | JEP 444, JEP 491 (synchronized pinning fix)               |
| Kotlin coroutines        | kotlinx.coroutines guide (official)                       |
| Lock-free algorithms     | *The Art of Multiprocessor Programming* (Herlihy, Shavit) |
| Concurrency testing      | jcstress (OpenJDK), Lincheck (JetBrains)                  |
| Structured concurrency   | JEP 453 (Java preview), Kotlin coroutines documentation   |
