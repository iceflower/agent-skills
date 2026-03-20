# CompletableFuture Patterns

## Composition

```java
// Sequential: thenApply, thenCompose
CompletableFuture<UserProfile> profile = fetchUser(userId)
    .thenCompose(user -> fetchProfile(user.getProfileId()))
    .thenApply(this::enrichProfile);

// Parallel: allOf, anyOf
CompletableFuture<UserProfile> profileFuture = fetchProfile(userId);
CompletableFuture<List<Order>> ordersFuture = fetchOrders(userId);
CompletableFuture<Notifications> notifsFuture = fetchNotifications(userId);

CompletableFuture<Dashboard> dashboard = CompletableFuture
    .allOf(profileFuture, ordersFuture, notifsFuture)
    .thenApply(v -> new Dashboard(
        profileFuture.join(),
        ordersFuture.join(),
        notifsFuture.join()
    ));

// Combine two futures
CompletableFuture<Summary> summary = profileFuture
    .thenCombine(ordersFuture, (profile, orders) -> new Summary(profile, orders));
```

## Error Handling

```java
// exceptionally — recover from errors
CompletableFuture<User> user = fetchUser(userId)
    .exceptionally(ex -> {
        log.warn("Failed to fetch user, using fallback", ex);
        return User.fallback(userId);
    });

// handle — process both success and failure
CompletableFuture<Result> result = fetchData()
    .handle((data, ex) -> {
        if (ex != null) return Result.failure(ex);
        return Result.success(data);
    });

// whenComplete — side effect without changing result
fetchData()
    .whenComplete((data, ex) -> {
        if (ex != null) log.error("Fetch failed", ex);
        else log.info("Fetched: {}", data);
    });
```

## Timeout (Java 9+)

```java
CompletableFuture<Response> response = callExternalApi()
    .orTimeout(5, TimeUnit.SECONDS)                    // Fails with TimeoutException
    .exceptionally(ex -> Response.timeout());

CompletableFuture<Response> response = callExternalApi()
    .completeOnTimeout(Response.fallback(), 5, TimeUnit.SECONDS);  // Returns default
```

## Rules

- Always specify executor for async stages — default `ForkJoinPool.commonPool()` is shared globally
- Never call `join()` or `get()` on event loop or request-handling threads — causes blocking
- Use `thenCompose` (not `thenApply`) when the mapping function returns a `CompletableFuture`
- Handle exceptions at every stage that can fail — unhandled exceptions are silently swallowed
- Use `orTimeout` or `completeOnTimeout` — never wait indefinitely

```java
// Always provide executor for async operations
CompletableFuture<Data> data = CompletableFuture
    .supplyAsync(() -> fetchData(), ioExecutor)        // Explicit executor
    .thenApplyAsync(this::transform, computeExecutor); // Different pool for CPU work
```
