# Backend Performance Reference

Detailed backend performance optimization techniques and patterns.

## Database Query Optimization

### EXPLAIN ANALYZE

Always verify query plans before and after optimization.

```sql
-- PostgreSQL
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT * FROM orders WHERE user_id = 42;

-- MySQL
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 42;
```

**What to look for:**

- `Seq Scan` on large tables → needs index
- `Nested Loop` with high row counts → consider `Hash Join`
- `Sort` with high cost → add index matching ORDER BY
- `Buffers: shared read` high → data not cached, check `shared_buffers`

### Index Design Rules

**Composite Index Column Order:**

```sql
-- Query: WHERE status = 'active' AND created_at > '2024-01-01' ORDER BY created_at
-- Index should match: equality columns first, then range/sort columns
CREATE INDEX idx_orders_status_created ON orders (status, created_at);
```

**Covering Index (Index-Only Scan):**

```sql
-- Query only needs these columns
CREATE INDEX idx_orders_covering ON orders (user_id, status) INCLUDE (total, created_at);
```

**Partial Index (PostgreSQL):**

```sql
-- Only index active orders (smaller index, faster queries)
CREATE INDEX idx_active_orders ON orders (created_at) WHERE status = 'active';
```

### N+1 Detection and Resolution

**Detection:**

- Enable query logging in development
- JPA/Hibernate: `spring.jpa.properties.hibernate.generate_statistics=true`
- Django: `django-debug-toolbar`
- Node.js: log query count per request

**Resolution by ORM:**

```java
// JPA: @EntityGraph
@EntityGraph(attributePaths = {"orders", "orders.items"})
List<User> findAll();

// JPA: JPQL JOIN FETCH
@Query("SELECT u FROM User u JOIN FETCH u.orders WHERE u.id = :id")
User findByIdWithOrders(@Param("id") Long id);
```

```python
# Django
User.objects.select_related("profile").prefetch_related("orders")
```

```javascript
// Prisma
const users = await prisma.user.findMany({
  include: { orders: true },
});
```

### Pagination

**Offset-based (simple but slow for large offsets):**

```sql
SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 1000;
-- Scans and discards 1000 rows
```

**Cursor-based (consistent performance):**

```sql
SELECT * FROM orders WHERE id > :last_seen_id ORDER BY id LIMIT 20;
-- Uses index directly, no wasted scan
```

## Connection Pool Configuration

### HikariCP (Java/Spring Boot)

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 10        # CPU cores × 2 + 1
      minimum-idle: 5
      idle-timeout: 300000         # 5 minutes
      max-lifetime: 1800000        # 30 minutes
      connection-timeout: 30000    # 30 seconds
      validation-timeout: 5000
      leak-detection-threshold: 60000  # 1 minute
```

### PgBouncer (External Pooler)

```ini
[pgbouncer]
pool_mode = transaction          # Best for web apps
default_pool_size = 20
max_client_conn = 1000
reserve_pool_size = 5
reserve_pool_timeout = 3
server_idle_timeout = 600
```

**Pool modes:**

| Mode | Description | Use Case |
| --- | --- | --- |
| `session` | Connection held for entire client session | Legacy apps, prepared statements |
| `transaction` | Connection returned after each transaction | Web applications (recommended) |
| `statement` | Connection returned after each statement | Simple queries only |

## Response Optimization

### Compression Configuration

**Nginx:**

```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript
           text/xml application/xml image/svg+xml;

# Brotli (requires ngx_brotli module)
brotli on;
brotli_comp_level 6;
brotli_types text/plain text/css application/json application/javascript
             text/xml application/xml image/svg+xml;
```

**Spring Boot:**

```yaml
server:
  compression:
    enabled: true
    min-response-size: 1024
    mime-types: text/html,text/css,application/json,application/javascript
```

### Server-Timing Header

```java
// Spring Boot example
@GetMapping("/api/users")
public ResponseEntity<List<User>> getUsers(HttpServletResponse response) {
    long dbStart = System.nanoTime();
    List<User> users = userRepository.findAll();
    long dbDuration = (System.nanoTime() - dbStart) / 1_000_000;

    response.setHeader("Server-Timing",
        String.format("db;dur=%d, total;dur=%d", dbDuration, totalDuration));
    return ResponseEntity.ok(users);
}
```

### Async Processing

Move non-critical work off the request path:

- **Message queues**: Kafka, RabbitMQ for background processing
- **Event-driven**: Emit events, process asynchronously
- **Scheduled tasks**: Batch operations off-peak

## Caching Layers

| Layer | Tool | TTL | Use Case |
| --- | --- | --- | --- |
| HTTP cache | CDN + Cache-Control | Minutes to years | Static assets, API responses |
| Application cache | Redis, Memcached | Seconds to hours | Computed results, session data |
| Query cache | ORM second-level cache | Seconds to minutes | Frequently read, rarely written data |
| Local cache | In-process (Caffeine, Guava) | Seconds | Hot data, config, feature flags |

**Cache invalidation strategies:**

- **TTL-based**: Simple, eventual consistency
- **Event-based**: Invalidate on write (pub/sub)
- **Write-through**: Update cache on every write
- **Cache-aside**: Application manages cache explicitly

For detailed caching patterns, see the [caching skill](../caching/SKILL.md).

## Resources

- [PostgreSQL Performance Tips](https://www.postgresql.org/docs/current/performance-tips.html)
- [HikariCP Configuration](https://github.com/brettwooldridge/HikariCP#gear-configuration-knobs-baby)
- [PgBouncer Documentation](https://www.pgbouncer.org/config.html)
- [Nginx Compression](https://nginx.org/en/docs/http/ngx_http_gzip_module.html)
