# Virtual Threads (Java 21+)

## When to Use Virtual Threads

| Scenario                         | Virtual Threads | Platform Threads |
| -------------------------------- | --------------- | ---------------- |
| I/O-bound (HTTP calls, DB, file) | Yes             |                  |
| CPU-bound computation            |                 | Yes              |
| High concurrency (10K+ tasks)    | Yes             |                  |
| Legacy code with `synchronized`  | Caution         | Yes              |
| Thread-per-request web server    | Yes             |                  |

## Basic Usage

```java
// Create virtual thread
Thread.startVirtualThread(() -> handleRequest(request));

// Executor for virtual threads — one thread per task, no pooling
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (Request req : requests) {
        executor.submit(() -> handleRequest(req));
    }
}

// For framework-specific virtual thread integration (e.g., Spring Boot),
// see the relevant framework skill
```

## Virtual Thread Caveats

```java
// Caveat 1: synchronized pins the carrier thread (Java 21-23)
// Fixed in Java 24+ (JEP 491)
synchronized (lock) {
    blockingIoCall();  // Pins carrier thread — avoid on Java 21-23
}

// Fix: use ReentrantLock instead (Java 21-23)
ReentrantLock lock = new ReentrantLock();
lock.lock();
try {
    blockingIoCall();  // Does NOT pin carrier thread
} finally {
    lock.unlock();
}

// Caveat 2: Do NOT pool virtual threads — they are cheap, create per task
// Bad: pooling virtual threads defeats their purpose
ExecutorService pool = Executors.newFixedThreadPool(10,
    Thread.ofVirtual().factory());  // Wrong — do not pool

// Good: one virtual thread per task
ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();

// Caveat 3: ThreadLocal overhead — each virtual thread has its own copy
// Millions of virtual threads = millions of ThreadLocal copies
// Use ScopedValue (preview) instead for large-scale virtual thread workloads
```

## Virtual Thread Rules

- Virtual threads are cheap — create per task, never pool them
- Blocking operations (JDBC, `Thread.sleep`, file I/O) are fine on virtual threads
- Avoid `synchronized` on Java 21-23 — use `ReentrantLock` (fixed in Java 24+)
- Avoid `ThreadLocal` with large objects — prefer `ScopedValue` (preview)
- Virtual threads do NOT speed up CPU-bound work — they optimize I/O concurrency
- Do not set thread priority on virtual threads — it has no effect
- Do not use `Thread.yield()` — virtual threads yield automatically on blocking
