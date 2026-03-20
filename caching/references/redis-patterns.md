# Redis Caching Patterns

Practical caching strategies with Redis, including cache-aside, write-through, TTL management, and eviction policies.

## Overview

Redis is an in-memory data store commonly used as a cache layer between applications and databases. Choosing the right caching pattern depends on read/write ratios, consistency requirements, and failure tolerance.

## Caching Strategies

### Cache-Aside (Lazy Loading)

The application manages the cache explicitly: read from cache first, fall back to database on miss, then populate cache.

```text
┌──────┐   1. GET   ┌───────┐
│ App  │───────────▶│ Cache │
│      │◀───────────│(Redis)│
│      │   2. HIT   └───────┘
│      │   or MISS
│      │            ┌───────┐
│      │   3. GET   │  DB   │  (only on cache miss)
│      │───────────▶│       │
│      │◀───────────│       │
│      │   4. result└───────┘
│      │
│      │   5. SET   ┌───────┐
│      │───────────▶│ Cache │  (populate on miss)
└──────┘            └───────┘
```

```java
public Product getProduct(String productId) {
    // 1. Check cache
    String cached = redis.get("product:" + productId);
    if (cached != null) {
        return deserialize(cached);
    }

    // 2. Cache miss: load from DB
    Product product = productRepository.findById(productId);

    // 3. Populate cache with TTL
    redis.setex("product:" + productId, 3600, serialize(product));

    return product;
}
```

**Pros**: Only caches data that is actually requested; cache failure is non-fatal
**Cons**: Cache miss penalty (extra round trip); potential stale data

### Write-Through

Every write goes to both cache and database synchronously.

```text
┌──────┐   1. WRITE  ┌───────┐   2. WRITE  ┌───────┐
│ App  │────────────▶│ Cache │────────────▶│  DB   │
└──────┘             │(Redis)│             └───────┘
                     └───────┘
```

```java
public void updateProduct(Product product) {
    // Write to database first
    productRepository.save(product);

    // Then update cache
    redis.setex("product:" + product.getId(), 3600, serialize(product));
}
```

**Pros**: Cache always consistent with database; no stale reads after writes
**Cons**: Write latency increases; cache may contain rarely-read data

### Write-Behind (Write-Back)

Writes go to cache immediately; database is updated asynchronously.

```text
┌──────┐   1. WRITE  ┌───────┐   2. ASYNC  ┌───────┐
│ App  │────────────▶│ Cache │ ─ ─ ─ ─ ─ ▶│  DB   │
└──────┘             │(Redis)│  (batched)  └───────┘
                     └───────┘
```

**Pros**: Low write latency; can batch database writes
**Cons**: Risk of data loss if cache fails before database sync; complex implementation

### Read-Through

Cache sits between application and database, loading data on miss automatically.

```java
// Spring Cache abstraction (read-through + write-through)
@Cacheable(value = "products", key = "#productId")
public Product getProduct(String productId) {
    return productRepository.findById(productId);
}

@CachePut(value = "products", key = "#product.id")
public Product updateProduct(Product product) {
    return productRepository.save(product);
}

@CacheEvict(value = "products", key = "#productId")
public void deleteProduct(String productId) {
    productRepository.deleteById(productId);
}
```

## TTL Strategies

### Static TTL

Fixed expiration time for all entries of a type.

```java
// Short TTL for frequently changing data
redis.setex("stock:" + productId, 60, stockCount);       // 1 minute

// Medium TTL for moderate change frequency
redis.setex("product:" + productId, 3600, productData);   // 1 hour

// Long TTL for rarely changing data
redis.setex("config:" + key, 86400, configValue);          // 24 hours
```

### TTL Guidelines by Data Type

| Data Type               | Recommended TTL    | Rationale                     |
| ----------------------- | ------------------ | ----------------------------- |
| Session data            | 30 minutes         | Security and freshness        |
| User profile            | 5-15 minutes       | Moderate change frequency     |
| Product catalog         | 1-4 hours          | Changes infrequently          |
| Configuration           | 12-24 hours        | Rarely changes                |
| Computed aggregations   | 5-30 minutes       | Balance freshness vs cost     |

### Jittered TTL (Prevent Stampede)

```java
// Add random jitter to prevent cache stampede
int baseTtl = 3600;
int jitter = ThreadLocalRandom.current().nextInt(0, 300); // 0-5 min jitter
redis.setex(key, baseTtl + jitter, value);
```

### Early Expiration (Probabilistic)

Refresh cache before TTL expires under load:

```java
public String getWithEarlyRefresh(String key, Supplier<String> loader) {
    CachedValue cached = redis.getWithMeta(key);

    if (cached == null) {
        // Cache miss
        return loadAndCache(key, loader);
    }

    // Probabilistic early refresh: increases as TTL approaches
    double remainingRatio = cached.remainingTtl() / (double) cached.originalTtl();
    if (Math.random() > remainingRatio) {
        // Refresh in background
        CompletableFuture.runAsync(() -> loadAndCache(key, loader));
    }

    return cached.value();
}
```

## Eviction Policies

Redis eviction policies control what happens when memory limit is reached.

| Policy              | Behavior                                           | Use Case                    |
| ------------------- | -------------------------------------------------- | --------------------------- |
| `noeviction`        | Return error on write when full                    | Critical data, no loss      |
| `allkeys-lru`       | Evict least recently used keys                     | General-purpose cache       |
| `allkeys-lfu`       | Evict least frequently used keys                   | Frequency-biased workloads  |
| `volatile-lru`      | LRU eviction only for keys with TTL                | Mix of cache + persistent   |
| `volatile-ttl`      | Evict keys with shortest remaining TTL             | Time-sensitive data         |
| `allkeys-random`    | Random eviction                                    | Uniform access patterns     |

```text
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lfu
```

**Recommendation**: Use `allkeys-lfu` for most caching workloads. It favors frequently accessed data.

## Cache Invalidation Patterns

### Event-Driven Invalidation

```java
@EventListener
public void onProductUpdated(ProductUpdated event) {
    redis.del("product:" + event.productId());
    redis.del("product-list:category:" + event.categoryId());
}
```

### Pattern-Based Invalidation

```java
// Delete all keys matching a pattern (use with caution in production)
// Better: maintain a set of related keys
redis.sadd("product-keys:" + categoryId, "product:" + productId);

// Invalidate all products in a category
Set<String> keys = redis.smembers("product-keys:" + categoryId);
if (!keys.isEmpty()) {
    redis.del(keys.toArray(new String[0]));
    redis.del("product-keys:" + categoryId);
}
```

## Cache Failure Handling

```java
public Product getProductWithFallback(String productId) {
    try {
        String cached = redis.get("product:" + productId);
        if (cached != null) {
            return deserialize(cached);
        }
    } catch (RedisException e) {
        log.warn("Cache unavailable, falling back to database", e);
        // Cache failure should not break the application
    }

    return productRepository.findById(productId);
}
```

**Key principle**: Cache is an optimization, not a dependency. The application must function (with degraded performance) when the cache is unavailable.
