---
name: caching
description: >-
  Framework-agnostic caching strategies including cache selection, TTL design,
  invalidation patterns, stampede prevention, and anti-patterns.
  Use when designing or reviewing cache logic.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# Caching Rules

## 1. Cache Strategy Selection

### When to Cache

| Scenario                              | Cache?  | Reason                          |
| ------------------------------------- | ------- | ------------------------------- |
| Frequently read, rarely written data  | Yes     | High read-to-write ratio        |
| Expensive computation results         | Yes     | Reduce CPU/DB load              |
| External API responses                | Yes     | Reduce latency and rate limits  |
| User session data                     | Yes     | Avoid repeated DB lookups       |
| Real-time data (stock prices, etc.)   | No      | Stale data is unacceptable      |
| Write-heavy data                      | No      | Cache invalidation too frequent |
| Security-critical data (permissions)  | Careful | Must invalidate on change       |

### Cache Placement

| Type          | Latency | Scope            | Use Case                      |
| ------------- | ------- | ---------------- | ----------------------------- |
| Local (L1)    | ~1ms    | Single instance  | Hot data, high read frequency |
| Distributed   | ~5ms    | All instances    | Shared state, session data    |
| HTTP cache    | Varies  | Client/CDN       | Static assets, public APIs    |
| Two-level     | ~1ms+   | L1 + distributed | Hot data across instances     |

### Two-Level Cache Pattern

```text
Request → L1 (local) → L2 (distributed) → Data source
             ↑ miss         ↑ miss              │
             └──────────────┴───── populate ─────┘
```

- L1 (Caffeine, Guava): sub-millisecond, per-instance
- L2 (Redis, Memcached): single-digit ms, shared
- On L1 miss, check L2 before hitting the data source
- Invalidate both levels on writes

---

## 2. TTL Design Guidelines

### Recommended TTL by Data Type

| Data Type               | Recommended TTL  | Rationale                   |
| ----------------------- | ---------------- | --------------------------- |
| Static config           | 1-24 hours       | Rarely changes              |
| User profile            | 15-30 minutes    | Moderate change frequency   |
| Search results          | 5-10 minutes     | Freshness matters           |
| API rate limit counters | 1 minute window  | Must be accurate            |
| Session data            | 30 min - 2 hours | Balance UX and security     |
| Product catalog         | 1-6 hours        | Changes infrequently        |
| Dashboard aggregations  | 1-5 minutes      | Near-real-time acceptable   |

### TTL Rules

- Always set a TTL — never cache indefinitely
- Shorter TTL for data that affects user experience when stale
- Longer TTL for reference data that changes infrequently
- Use explicit eviction on writes in addition to TTL
- Consider TTL jitter to avoid cache stampede

### TTL Jitter

```text
Effective TTL = base_ttl + random(0, jitter_range)

Example: base 10min, jitter 2min → actual TTL between 10-12min
```

Without jitter, cached entries expire simultaneously, causing a thundering herd to the data source.

---

## 3. Cache Key Design

### Key Structure

```text
<namespace>:<entity>:<identifier>[:<variant>]

Examples:
  user:profile:12345
  product:detail:SKU-001:v2
  search:results:shoes:page=1:size=20
```

### Key Design Rules

| Rule                        | Reason                                  |
| --------------------------- | --------------------------------------- |
| Include type prefix         | Prevents key collisions across entities |
| Include version if needed   | Supports cache-friendly schema changes  |
| Keep keys short             | Saves memory in distributed cache       |
| Avoid user input in keys    | Prevents cache poisoning attacks        |
| Normalize key components    | Ensures consistent lookups              |

---

## 4. Cache Invalidation Patterns

### Write-Through

Update the cache entry simultaneously when writing to the data store. Ensures cache is always consistent but adds write latency.

```text
Write request → Update DB → Update cache → Return
```

### Evict on Write (Cache-Aside)

Evict the cache entry on write and let the next read repopulate it. Simpler to implement and avoids stale data from failed cache updates.

```text
Write: Write request → Update DB → Evict cache → Return
Read:  Read request → Cache miss → Read DB → Populate cache → Return
```

### Write-Behind (Write-Back)

Write to cache first, then asynchronously persist to the data store. Lowest write latency but risks data loss.

```text
Write request → Update cache → Return (async persist to DB)
```

### Event-Based Invalidation

Invalidate cache entries via events (message queue, application events) for cross-service consistency. Best for distributed systems where multiple services share cached data.

### Invalidation Rules

- Prefer explicit eviction over TTL-only for mutable data
- Invalidate on all write paths (update, delete, bulk operations)
- Use event-based invalidation for cross-service cache consistency
- Test cache invalidation paths — stale cache bugs are hard to diagnose

---

## 5. Cache Stampede Prevention

A cache stampede occurs when many requests simultaneously miss the cache and hit the data source.

### Prevention Strategies

| Strategy               | Description                                        | Trade-off                |
| ---------------------- | -------------------------------------------------- | ------------------------ |
| Mutex/lock             | Only one request rebuilds, others wait             | Adds latency for waiters |
| Probabilistic expiry   | Refresh before TTL expires with some probability   | Slightly stale data      |
| Background refresh     | Async refresh before expiry                        | More complexity          |
| Stale-while-revalidate | Serve stale, refresh in background                 | Brief staleness window   |

### Probabilistic Early Recomputation

Instead of waiting for exact expiry, each request probabilistically decides whether to recompute. As TTL approaches, the probability of recomputation increases.

```text
should_recompute = (current_time - (expiry - ttl * beta * log(rand()))) > 0

beta: tuning factor (typically 1.0)
rand(): uniform random in (0, 1]
```

- When `beta = 1.0`, roughly 1 request recomputes before expiry under normal load
- Higher beta increases early recomputation probability
- No coordination overhead — purely probabilistic, no locks required
- Best suited for high-throughput keys where occasional early recomputation is acceptable

### Locking Strategy Details

```text
1. Thread A: cache miss → acquire lock → recompute → populate cache → release lock
2. Thread B: cache miss → lock unavailable → wait or return stale value
```

- **Blocking lock**: waiters block until the lock holder populates the cache; simple but increases tail latency
- **Try-lock with stale fallback**: if lock is unavailable, serve the stale value; requires keeping the expired entry accessible
- **Distributed lock** (e.g., Redis `SET NX EX`): required when multiple instances share the cache; set a short lock TTL to avoid deadlocks

### Request Coalescing (Singleflight)

Multiple concurrent requests for the same key are collapsed into a single data-source call. Only the first request triggers computation; subsequent requests wait for and share the result.

```text
Request A ─┐
Request B ──┼─→ single fetch → result shared to all
Request C ─┘
```

- Eliminates redundant calls entirely, not probabilistically
- Must be implemented in the application layer (e.g., Go `singleflight`, custom deduplication map)
- Scope is per-instance; combine with distributed locking for multi-instance protection

---

## 6. Cache Warming

### When to Warm

- Application startup with predictable hot data
- After cache flush or failover
- Before traffic spike (scheduled events, promotions)

### Warming Rules

- Warm only high-frequency keys — not the entire dataset
- Stagger warming to avoid overwhelming the data source
- Set shorter TTL for warmed entries if staleness risk is high

---

## 7. Anti-Patterns

- Caching without TTL (memory leak risk)
- Caching mutable objects (caller modifies cached reference)
- Cache key collisions (using only entity ID without type prefix)
- Caching null values without explicit handling
- Ignoring cache in delete/update paths (stale reads)
- Over-caching (caching everything "just in case")
- No monitoring of cache hit/miss rates
- Using distributed cache for data that only needs local caching
- Cache-aside without stampede protection on hot keys
- Storing large objects (> 1MB) in distributed cache without compression

## 8. Cache Patterns Comparison

Sections 1 and 4 introduce individual patterns. This section provides a systematic comparison to guide pattern selection.

### Read Patterns

| Pattern      | How It Works                                              | Pros                                        | Cons                                                | Best For                                     |
| ------------ | --------------------------------------------------------- | ------------------------------------------- | --------------------------------------------------- | -------------------------------------------- |
| Cache-Aside  | App checks cache; on miss, reads DB, then populates cache | Simple, app controls cache logic            | Possible stale data until TTL or explicit eviction  | General-purpose read-heavy workloads         |
| Read-Through | Cache itself fetches from DB on miss (transparent to app) | Cleaner app code, cache handles data source | Cache library must support loader integration       | When cache layer can encapsulate data access |

### Write Patterns

| Pattern       | How It Works                                           | Pros                                    | Cons                                                | Best For                                        |
| ------------- | ------------------------------------------------------ | --------------------------------------- | --------------------------------------------------- | ----------------------------------------------- |
| Write-Through | Writes go to cache and DB synchronously                | Strong consistency between cache and DB | Higher write latency (two synchronous writes)       | Read-heavy with strict consistency needs        |
| Write-Behind  | Writes go to cache first; DB is updated asynchronously | Lowest write latency                    | Risk of data loss if cache fails before DB persist  | Write-heavy with tolerance for eventual persist |

### Pattern Selection Guide

```text
Read-heavy, simple setup?           → Cache-Aside
Read-heavy, want transparent cache? → Read-Through
Need write consistency?             → Write-Through
Need fast writes, tolerate risk?    → Write-Behind
High read + high write?             → Write-Behind + Read-Through
```

### Combining Read and Write Patterns

- **Read-Through + Write-Through**: full cache transparency with strong consistency; higher write latency
- **Read-Through + Write-Behind**: full cache transparency with fast writes; eventual consistency for writes
- **Cache-Aside + Write-Through**: app controls reads, cache stays consistent on writes; most common combination

---

## 9. Distributed Cache Patterns

### Consistent Hashing

Maps cache keys to nodes on a hash ring. When a node is added or removed, only a fraction of keys are remapped.

```text
Hash Ring:

    Node A (0°)
       ╱          ╲
  Node D (270°)    Node B (90°)
       ╲          ╱
    Node C (180°)

Key "user:123" hashes to 110° → assigned to Node C (next node clockwise)
Node B removed → only keys between A and B remap to C
```

- **Virtual nodes**: each physical node maps to multiple points on the ring, improving key distribution
- Without virtual nodes, adding/removing nodes causes uneven load
- Commonly used by Redis Cluster, Memcached client libraries, and application-level sharding

### Near Cache (L1/L2 Architecture)

Extends the two-level cache concept (Section 1) with consistency mechanisms for distributed environments.

| Aspect                | L1 (Near / Local)                     | L2 (Remote / Distributed)            |
| --------------------- | ------------------------------------- | ------------------------------------ |
| Location              | Application heap                      | External cache cluster               |
| Latency               | Sub-millisecond                       | Single-digit milliseconds            |
| Scope                 | Per-instance                          | Cluster-wide                         |
| Consistency           | Eventually consistent with L2         | Source of truth for cached data      |
| Size                  | Small (hundreds to thousands of keys) | Large (millions of keys)             |

#### Consistency Strategies for Near Cache

- **Invalidation events**: L2 publishes invalidation messages (e.g., Redis Pub/Sub); L1 evicts on receive
- **Short L1 TTL**: keep L1 TTL short (seconds) to limit staleness window without events
- **Version check**: L1 stores version tag; on read, compare with L2 version before serving

### Cache Replication vs Partitioning

| Aspect           | Replication                             | Partitioning (Sharding)                |
| ---------------- | --------------------------------------- | -------------------------------------- |
| Data model       | Every node holds a full copy            | Each node holds a subset of keys       |
| Read scalability | Excellent (any node can serve any read) | Good (reads routed to owning node)     |
| Write cost       | High (must propagate to all replicas)   | Low (write to one node)                |
| Capacity         | Limited by single node memory           | Scales horizontally with nodes         |
| Fault tolerance  | High (any replica can serve)            | Needs rebalancing on node failure      |
| Best for         | Read-heavy, small dataset               | Large dataset, write-heavy             |

- **Hybrid approach**: partition data across shards, replicate each shard (e.g., Redis Cluster with replicas)
- Replication lag causes temporary inconsistency; design reads to tolerate this

---

## 10. Cache Sizing and Monitoring

### Cache Sizing Guidelines

| Factor              | Guidance                                                                    |
| ------------------- | --------------------------------------------------------------------------- |
| Working set size    | Estimate the number of unique keys accessed within one TTL window           |
| Object size         | Measure serialized size; set max entry size limits                          |
| Memory budget       | Allocate based on infra capacity; leave headroom for eviction overhead      |
| Hit rate target     | 80-95% hit rate is typical; diminishing returns above 95%                   |
| Eviction headroom   | Keep 10-20% free to avoid constant eviction churn                           |

### Sizing Formula

```text
Required memory ≈ working_set_count × avg_serialized_size × (1 + overhead_factor)

overhead_factor: ~0.1–0.3 depending on data structure and cache implementation
```

- Start with a conservative estimate, then adjust based on actual hit rate and eviction metrics
- For distributed caches, divide by partition count to get per-node sizing

### Key Metrics to Monitor

| Metric              | What It Tells You                          | Alert Threshold (Typical)        |
| ------------------- | ------------------------------------------ | -------------------------------- |
| Hit rate            | Cache effectiveness                        | Below 80% warrants investigation |
| Miss rate           | Uncached or expired requests               | Inverse of hit rate              |
| Eviction rate       | Cache is too small or TTL too long         | Sustained increase is a warning  |
| Latency (p50, p99)  | Cache performance                          | p99 > 10ms for distributed cache |
| Memory usage        | Capacity utilization                       | Above 80% of allocated memory    |
| Connection count    | Client pressure on cache cluster           | Near max connections limit       |
| Key count           | Total entries stored                       | Unexpected growth may be a leak  |

### Monitoring Rules

- Track hit rate per cache region or namespace, not just globally
- Set up alerts for hit rate drops — they often indicate a bug, not a capacity issue
- Monitor eviction rate alongside memory usage; high eviction with low memory means the cache is undersized
- Track latency percentiles (p50, p95, p99), not just averages
- Log cache misses for hot keys to identify stampede candidates

---

## Additional References

- For Redis caching strategies, cache-aside, write-through, TTL management, and eviction policies, see [references/redis-patterns.md](references/redis-patterns.md)
- For Spring Boot implementation patterns (Caffeine, Redis, `@Cacheable`), see `spring-framework` skill — [references/caching.md](../spring-framework/references/caching.md)
