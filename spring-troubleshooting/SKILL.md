---
name: spring-troubleshooting
description: >-
  Spring Boot troubleshooting including startup failures, JVM OOM diagnosis,
  HikariCP issues, and Spring-specific slow API debugging.
  Use when diagnosing Spring Boot application issues.
---

# Spring Boot Troubleshooting Rules

## 1. Spring Boot Startup Failure

### Diagnosis Order

1. Read the full stack trace — the root cause is usually at the bottom
2. Check for `BeanCreationException` → missing or conflicting beans
3. Check for `DataSourceAutoConfiguration` → database connection issue
4. Check for port conflict → `PortInUseException`
5. Check active profile → verify `spring.profiles.active` is set correctly

### Common Causes and Fixes

| Error                                        | Cause                        | Fix                                              |
| -------------------------------------------- | ---------------------------- | ------------------------------------------------ |
| `UnsatisfiedDependencyException`             | Missing bean or circular dep | Check `@Component` scan path, break circular dep |
| `HikariPool-1 - Connection is not available` | DB unreachable or creds wrong| Verify `spring.datasource.*` config and network  |
| `Port already in use`                        | Another process on same port | Kill the process or change `server.port`         |
| `NoSuchBeanDefinitionException`              | Bean not registered          | Check package scan, `@Configuration` class       |
| `Failed to configure a DataSource`           | Missing DB driver or URL     | Add `runtimeOnly` driver dep, set datasource URL |

### Circular Dependency Resolution

```kotlin
// Bad: A depends on B, B depends on A
@Service
class ServiceA(private val serviceB: ServiceB)

@Service
class ServiceB(private val serviceA: ServiceA) // Circular!

// Fix 1: Use @Lazy on one side
@Service
class ServiceB(@Lazy private val serviceA: ServiceA)

// Fix 2: Extract shared logic into a third service
@Service
class SharedService  // Contains the shared logic
```

### Bean Conflict Resolution

```kotlin
// Multiple beans of same type
// Fix: Use @Primary or @Qualifier
@Bean
@Primary
fun primaryDataSource(): DataSource = ...

@Bean("secondaryDs")
fun secondaryDataSource(): DataSource = ...
```

---

## 2. JVM OOM (OutOfMemoryError)

### OOM Types

| Type                            | Cause                        | Investigation                           |
| ------------------------------- | ---------------------------- | --------------------------------------- |
| `Java heap space`               | Heap exhaustion              | Heap dump analysis                      |
| `Metaspace`                     | Too many classes loaded      | Check dynamic class generation          |
| `GC overhead limit exceeded`    | 98%+ time spent in GC        | Heap dump + GC log analysis             |
| `unable to create native thread`| Thread limit reached         | Check thread count, ulimit settings     |
| `Direct buffer memory`          | NIO buffer exhaustion        | Check `-XX:MaxDirectMemorySize`         |

### Investigation Commands

```bash
# Check current JVM memory settings inside container
jcmd 1 VM.flags

# Generate heap dump on OOM (add to ENTRYPOINT)
-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp/heapdump.hprof

# Force heap dump from running process
jcmd 1 GC.heap_dump /tmp/heapdump.hprof

# Check GC activity
jstat -gcutil <pid> 1000 10

# Check thread count
jcmd 1 Thread.print | grep -c "tid="
```

### Common OOM Causes

| Cause                       | Symptom                          | Fix                                      |
| --------------------------- | -------------------------------- | ---------------------------------------- |
| Memory leak (unclosed)      | Gradual memory increase          | Fix resource cleanup, try-with-resources |
| Unbounded collection growth | Spike after specific request     | Add pagination, limit collection size    |
| Too many threads            | `unable to create native thread` | Use thread pools, reduce parallelism     |
| Container limit too low     | Immediate OOM on startup         | Increase container memory limit          |
| `MaxRAMPercentage` too high | No room for non-heap             | Set to 75% or lower                      |

### Container Memory Sizing

```bash
# Recommended JVM flags for containers
-XX:MaxRAMPercentage=75.0     # Leave 25% for non-heap
-XX:InitialRAMPercentage=50.0

# Check effective heap size inside container
jcmd 1 GC.heap_info
```

---

## 3. HikariCP Connection Pool Issues

### Diagnosis

```bash
# Enable HikariCP debug logging
logging.level.com.zaxxer.hikari=DEBUG
logging.level.com.zaxxer.hikari.pool.HikariPool=DEBUG
```

### Common Issues

| Symptom                              | Cause                            | Fix                                       |
| ------------------------------------ | -------------------------------- | ----------------------------------------- |
| `Connection is not available`        | Pool exhausted                   | Increase `maximum-pool-size` or fix leaks |
| `Connection timed out after 30000ms` | Slow queries holding connections | Optimize queries, add statement timeout   |
| `Connection reset`                   | Idle conn killed by DB/proxy     | Set `max-lifetime` below DB timeout       |
| Connections not returned             | Missing `@Transactional` close   | Ensure all connections are properly closed |

### Recommended Configuration

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 10       # Default: 10
      minimum-idle: 5             # Default: same as maximum
      connection-timeout: 30000   # 30s (default)
      idle-timeout: 600000        # 10min
      max-lifetime: 1800000       # 30min (must be < DB wait_timeout)
      leak-detection-threshold: 60000  # 60s — logs warning for leaked connections
```

---

## 4. Spring-Specific Slow API Response

### Profiling Approach

```kotlin
val startTime = System.currentTimeMillis()
val result = someOperation()
val duration = System.currentTimeMillis() - startTime
log.info("Operation completed", mapOf("durationMs" to duration))
```

### Spring-Specific Causes and Fixes

| Cause                                     | Diagnosis                    | Fix                                |
| ----------------------------------------- | ---------------------------- | ---------------------------------- |
| N+1 queries                               | Multiple similar SQL in logs | Use `JOIN FETCH` or `@EntityGraph` |
| JPA query logging off                     | Cannot see SQL               | Enable `spring.jpa.show-sql=true`  |
| No caching                                | Same query repeated          | Add `@Cacheable` or Redis cache    |
| HikariCP pool exhaustion                  | Pool warning in logs         | Increase pool size or optimize     |
| Missing `@Transactional(readOnly = true)` | Unnecessary write locks      | Add readOnly for read operations   |
| Lazy loading outside session              | `LazyInitializationException`| Use fetch join or DTO projection   |
| Large response serialization              | High CPU during response     | Use pagination, field selection    |

### SQL Logging Configuration

```yaml
# Development — show SQL with parameters
spring:
  jpa:
    show-sql: true
    properties:
      hibernate:
        format_sql: true
logging:
  level:
    org.hibernate.SQL: DEBUG
    org.hibernate.orm.jdbc.bind: TRACE
```

---

## 5. Actuator-Based Diagnostics

### Useful Actuator Endpoints

| Endpoint          | Purpose                               |
| ----------------- | ------------------------------------- |
| `/actuator/health`| Application and dependency health     |
| `/actuator/metrics`| JVM, HikariCP, HTTP metrics          |
| `/actuator/env`   | Effective configuration values        |
| `/actuator/beans` | All registered beans                  |
| `/actuator/conditions` | Auto-configuration report        |

### Key Metrics to Check

```bash
# HikariCP pool status
GET /actuator/metrics/hikaricp.connections.active
GET /actuator/metrics/hikaricp.connections.pending

# JVM memory
GET /actuator/metrics/jvm.memory.used
GET /actuator/metrics/jvm.gc.pause

# HTTP request latency
GET /actuator/metrics/http.server.requests
```

---

## Related Skills

- `troubleshooting` — Framework-agnostic debugging patterns (slow APIs, deployment rollback, connection issues)
- `jvm-performance` — GC tuning, profiling tools, heap dump analysis
- `spring-config` — Configuration properties, profile management, HikariCP setup
