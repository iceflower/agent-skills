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
compatibility:
  - OpenCode
  - Claude Code
  - Codex
  - Antigravity
---

# Caching Rules

## 1. Cache Strategy Selection

### When to Cache

| Scenario                              | Cache? | Reason                          |
| ------------------------------------- | ------ | ------------------------------- |
| Frequently read, rarely written data  | Yes    | High read-to-write ratio        |
| Expensive computation results         | Yes    | Reduce CPU/DB load              |
| External API responses                | Yes    | Reduce latency and rate limits  |
| User session data                     | Yes    | Avoid repeated DB lookups       |
| Real-time data (stock prices, etc.)   | No     | Stale data is unacceptable      |
| Write-heavy data                      | No     | Cache invalidation too frequent |
| Security-critical data (permissions)  | Careful| Must invalidate on change       |

### Cache Placement

| Type          | Latency | Scope           | Use Case                      |
| ------------- | ------- | --------------- | ----------------------------- |
| Local (L1)    | ~1ms    | Single instance | Hot data, high read frequency |
| Distributed   | ~5ms    | All instances   | Shared state, session data    |
| HTTP cache    | Varies  | Client/CDN      | Static assets, public APIs    |
| Two-level     | ~1ms+   | L1 + distributed| Hot data across instances     |

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

| Strategy             | Description                                     | Trade-off                |
| -------------------- | ----------------------------------------------- | ------------------------ |
| Mutex/lock           | Only one request rebuilds, others wait           | Adds latency for waiters |
| Probabilistic expiry | Refresh before TTL expires with some probability | Slightly stale data      |
| Background refresh   | Async refresh before expiry                      | More complexity          |
| Stale-while-revalidate | Serve stale, refresh in background            | Brief staleness window   |

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

## Additional References

- For Spring Boot implementation patterns (Caffeine, Redis, `@Cacheable`), see `spring-framework` skill — [references/caching.md](../spring-framework/references/caching.md)
