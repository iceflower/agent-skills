# Database Connection and Connection Pool Troubleshooting

## 1. Connection Pool Fundamentals

### Why Connection Pooling Matters

Database connections are expensive to create (TCP handshake, authentication, server-side resource allocation). Connection pools maintain a set of reusable connections to amortize this cost.

### HikariCP Pool Sizing

HikariCP is the default connection pool for Spring Boot and one of the most widely used pools in JVM applications.

#### Pool Size Formula

The optimal pool size is typically much smaller than expected. Based on PostgreSQL's recommendation:

```text
connections = (core_count * 2) + effective_spindle_count

Example for a 4-core server with SSD:
connections = (4 * 2) + 1 = 9
```

For most applications, a pool of **10-20 connections** is sufficient. Larger pools often cause performance degradation due to increased contention at the database level.

#### Key Configuration Parameters

| Parameter | Default | Description | Recommendation |
| --- | --- | --- | --- |
| `maximumPoolSize` | 10 | Max connections in the pool | `(core_count * 2) + spindle_count` |
| `minimumIdle` | same as max | Minimum idle connections | Set equal to `maximumPoolSize` for fixed pool |
| `connectionTimeout` | 30000ms | Max wait time for a connection from pool | 5000-10000ms for web apps |
| `idleTimeout` | 600000ms (10min) | Max idle time before connection is retired | Match with DB `wait_timeout` |
| `maxLifetime` | 1800000ms (30min) | Max lifetime of a connection | Set 2-3 minutes less than DB `wait_timeout` |
| `validationTimeout` | 5000ms | Max time to validate connection is alive | 3000-5000ms |
| `leakDetectionThreshold` | 0 (disabled) | Time before logging a potential connection leak | Set to 2x your longest query time |

#### Spring Boot Configuration Example

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 10
      minimum-idle: 10               # Fixed pool size (min = max)
      connection-timeout: 5000       # 5 seconds
      idle-timeout: 600000           # 10 minutes
      max-lifetime: 1740000          # 29 minutes (< DB wait_timeout)
      leak-detection-threshold: 30000  # 30 seconds
      pool-name: "MyAppPool"
      connection-test-query: "SELECT 1"  # Only if JDBC4 isValid() not supported
```

---

## 2. Connection Leak Detection

### Symptoms

| Symptom | Evidence |
| --- | --- |
| Pool exhaustion | `SQLTransientConnectionException: Connection is not available, request timed out after Xms` |
| Gradual degradation | Active connections grow over time, never return to idle |
| Periodic failures | Connections leak until pool is full, then fail until leaked connections time out |

### HikariCP Leak Detection

Enable HikariCP's built-in leak detection:

```yaml
spring:
  datasource:
    hikari:
      leak-detection-threshold: 30000  # 30 seconds — log warning if connection held longer
```

Log output when leak detected:

```text
WARN  com.zaxxer.hikari.pool.ProxyLeakTask - Connection leak detection triggered for connection com.mysql.cj.jdbc.ConnectionImpl@1a2b3c4d,
stack trace follows
java.lang.Exception: Apparent connection leak detected
    at com.example.service.UserService.findAll(UserService.java:42)
    at com.example.controller.UserController.list(UserController.java:28)
```

### Common Leak Causes

| Cause | Pattern | Fix |
| --- | --- | --- |
| Missing `try-with-resources` | Manual `Connection`/`Statement` without close | Use try-with-resources for all JDBC resources |
| Exception before close | Error thrown between open and close | Always close in `finally` or use try-with-resources |
| Long-running transaction | Transaction held open during external API call | Move external calls outside transaction boundary |
| N+1 in lazy loading | Hibernate opens connections for lazy fetch outside session | Use join fetch, or configure `open-in-view: false` |
| Manual `DataSource.getConnection()` | Direct connection use without returning to pool | Use `JdbcTemplate` or framework-managed connections |

### Monitoring Pool Metrics

```yaml
# Expose HikariCP metrics via Spring Boot Actuator + Micrometer
management:
  endpoints:
    web:
      exposure:
        include: health,metrics
  metrics:
    tags:
      application: ${spring.application.name}
```

Key metrics to monitor:

| Metric | Description | Alert Threshold |
| --- | --- | --- |
| `hikaricp.connections.active` | Currently in-use connections | >80% of max pool size |
| `hikaricp.connections.idle` | Available idle connections | <2 for sustained period |
| `hikaricp.connections.pending` | Threads waiting for a connection | >0 for sustained period |
| `hikaricp.connections.timeout` | Connection acquisition timeouts | Any occurrence |
| `hikaricp.connections.max` | Maximum pool size | Configuration reference |
| `hikaricp.connections.usage` | Connection usage duration | P99 > leak detection threshold |

---

## 3. Common Connection Issues

### Connection Timeout vs Pool Timeout

| Error | Meaning | Fix |
| --- | --- | --- |
| `Connection timed out` (TCP) | Cannot reach database server | Check network, firewall, DNS, DB status |
| `Connection is not available, request timed out` (Pool) | All pool connections in use | Check for leaks, increase pool size, optimize queries |

### Connection Dropped by Proxy/Load Balancer

Cloud environments often have network components (NAT gateways, load balancers, proxies) that silently drop idle connections.

```text
Problem: Connection sits idle → proxy drops it → app tries to use stale connection → error

Fix: Set maxLifetime shorter than proxy idle timeout

Common proxy timeouts:
  AWS RDS Proxy:         idle timeout configurable (1-3600s)
  AWS NAT Gateway:       350 seconds
  Azure SQL Gateway:     ~4 minutes
  GCP Cloud SQL Proxy:   managed automatically
  HAProxy:               configurable (default 50s client, 50s server)
```

```yaml
# If proxy drops idle connections after 350 seconds
spring:
  datasource:
    hikari:
      max-lifetime: 300000         # 5 minutes (< proxy timeout)
      idle-timeout: 240000         # 4 minutes
      keepalive-time: 120000       # 2 minutes — sends validation query to keep alive
```

### Database Max Connections Exceeded

```text
Problem: Multiple app instances share the same database
  - 5 instances x 20 connections = 100 connections
  - PostgreSQL default max_connections = 100
  - Result: "too many connections" error

Fix:
  1. Calculate total connections: (instances * pool_size) < db_max_connections
  2. Reserve ~20% of db_max_connections for admin/monitoring
  3. Reduce pool size per instance, or increase db_max_connections
  4. Consider PgBouncer or ProxySQL for connection multiplexing
```

### Connection Validation

```yaml
spring:
  datasource:
    hikari:
      # JDBC4+ drivers (most modern drivers): use isValid() — no test query needed
      # JDBC3 drivers: set connection-test-query
      connection-test-query: "SELECT 1"  # Only if isValid() not supported
```

---

## 4. Troubleshooting Decision Tree

```text
Connection Error
├── Cannot connect at all
│   ├── "Connection refused"
│   │   → Check: Is DB running? Is port correct? Firewall rules?
│   ├── "Connection timed out"
│   │   → Check: Network path, security groups, VPC peering, DNS
│   └── "Authentication failed"
│       → Check: Credentials, user permissions, pg_hba.conf / mysql user grants
│
├── Intermittent connection failures
│   ├── "Connection reset" / "Broken pipe"
│   │   → Check: Idle timeout mismatch between pool and proxy/DB
│   │   → Fix: Set maxLifetime < proxy/DB idle timeout, enable keepalive
│   ├── "Too many connections"
│   │   → Check: Total pool size across all instances vs DB max_connections
│   │   → Fix: Reduce pool size or add connection multiplexer (PgBouncer)
│   └── Periodic spikes in connection errors
│       → Check: Connection maxLifetime causing mass reconnection
│       → Fix: HikariCP randomizes maxLifetime by default (2.5% variance)
│
└── Pool exhaustion (no available connections)
    ├── Connection leak suspected
    │   → Enable leak-detection-threshold
    │   → Check for missing try-with-resources
    │   → Check for long-running transactions
    ├── Slow queries holding connections
    │   → Check slow query log
    │   → Add query timeout: spring.jpa.properties.jakarta.persistence.query.timeout
    └── Burst traffic exceeding pool capacity
        → Check if pool size is appropriate for load
        → Consider queue-based request handling for burst traffic
```
