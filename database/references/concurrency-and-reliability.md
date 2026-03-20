# Database Concurrency and Reliability

## 1. Optimistic Locking

### Version Column Pattern

```sql
-- Add version column
ALTER TABLE orders ADD COLUMN version INTEGER NOT NULL DEFAULT 0;

-- Update with version check
UPDATE orders
SET status = 'CONFIRMED', version = version + 1
WHERE id = 123 AND version = 5;

-- If affected rows = 0, someone else modified the row → retry or fail
```

### JPA @Version

```kotlin
@Entity
class Order(
    @Id @GeneratedValue
    val id: Long = 0,

    var status: OrderStatus,

    @Version
    val version: Int = 0
)

// JPA automatically checks version on update
// Throws OptimisticLockException if version mismatch
```

### Exposed ORM

```kotlin
object Orders : IntIdTable() {
    val status = enumerationByName<OrderStatus>("status", 20)
    val version = integer("version").default(0)
}

// Manual optimistic lock check
fun updateOrder(orderId: Int, newStatus: OrderStatus, expectedVersion: Int): Boolean {
    val updated = Orders.update({ (Orders.id eq orderId) and (Orders.version eq expectedVersion) }) {
        it[status] = newStatus
        it[version] = expectedVersion + 1
    }
    return updated > 0  // false = concurrent modification
}
```

### Retry Strategy

```kotlin
fun updateWithRetry(orderId: Int, action: (Order) -> Unit, maxRetries: Int = 3) {
    repeat(maxRetries) { attempt ->
        try {
            val order = orderRepository.findById(orderId)
            action(order)
            orderRepository.save(order)
            return
        } catch (e: OptimisticLockException) {
            if (attempt == maxRetries - 1) throw e
            // Exponential backoff to reduce contention under high load
            Thread.sleep(50L * (1L shl attempt))  // 50ms, 100ms, 200ms...
        }
    }
}
```

### When to Use Optimistic Locking

- Read-heavy workloads with infrequent conflicts
- Short transactions where conflicts are rare
- User-facing operations (edit forms, cart updates)

---

## 2. Pessimistic Locking

### SELECT FOR UPDATE

```sql
-- Lock row until transaction ends
SELECT * FROM orders WHERE id = 123 FOR UPDATE;

-- Other transactions wait until lock is released
UPDATE orders SET status = 'CONFIRMED' WHERE id = 123;
COMMIT;
```

### Lock Variants

| Variant | SQL | Behavior |
| --- | --- | --- |
| Exclusive lock | `FOR UPDATE` | Block reads and writes |
| Shared lock | `FOR SHARE` | Allow reads, block writes |
| No wait | `FOR UPDATE NOWAIT` | Fail immediately if locked |
| Skip locked | `FOR UPDATE SKIP LOCKED` | Skip locked rows (queue pattern) |

### SKIP LOCKED — Queue Pattern

```sql
-- Worker picks next available task (skips tasks being processed)
SELECT * FROM tasks
WHERE status = 'PENDING'
ORDER BY created_at
LIMIT 1
FOR UPDATE SKIP LOCKED;

-- Process and update
UPDATE tasks SET status = 'PROCESSING' WHERE id = ?;
```

### Deadlock Prevention

| Rule | Implementation |
| --- | --- |
| Consistent lock order | Always lock tables/rows in alphabetical or ID order |
| Minimize lock scope | Lock only necessary rows, keep transactions short |
| Set lock timeout | `SET lock_timeout = '5s'` (PostgreSQL) |
| Avoid nested locks | Do not acquire new locks while holding existing ones |
| Monitor deadlocks | Enable deadlock logging, alert on occurrence |

### When to Use Pessimistic Locking

- Write-heavy workloads with frequent conflicts
- Financial transactions requiring strict consistency
- Inventory management (prevent overselling)
- Queue processing (SKIP LOCKED pattern)

---

## 3. Advisory Locks

### PostgreSQL Advisory Locks

```sql
-- Session-level advisory lock (released on disconnect)
SELECT pg_advisory_lock(12345);
-- ... do work ...
SELECT pg_advisory_unlock(12345);

-- Transaction-level advisory lock (released on COMMIT/ROLLBACK)
SELECT pg_advisory_xact_lock(12345);

-- Try lock (non-blocking)
SELECT pg_try_advisory_lock(12345);  -- returns true/false
```

### Application-Level Distributed Locking

```kotlin
// Use advisory lock for cross-instance coordination
fun withAdvisoryLock(lockId: Long, action: () -> Unit) {
    transaction {
        val acquired = exec("SELECT pg_try_advisory_xact_lock($lockId)") {
            it.next(); it.getBoolean(1)
        } ?: false

        if (acquired) {
            action()
        } else {
            throw LockAcquisitionException("Could not acquire lock $lockId")
        }
        // Lock automatically released on transaction end
    }
}
```

### Use Cases

- Preventing concurrent execution of scheduled jobs across instances
- Coordinating schema migrations in multi-instance deployments
- Rate limiting or throttling per resource

---

## 4. Backup Strategies

### Strategy Comparison

| Strategy | Tool | Speed | Size | PITR | Downtime |
| --- | --- | --- | --- | --- | --- |
| Logical backup | pg_dump / mysqldump | Slow | Compressed | No | Read impact |
| Physical backup | pg_basebackup | Fast | Full disk | Yes (with WAL) | Minimal |
| Continuous archiving | WAL archiving | Continuous | Incremental | Yes | None |
| Snapshot | Cloud snapshot | Instant | Full disk | Limited | Minimal |

### PostgreSQL Backup Commands

```bash
# Logical backup (single database)
pg_dump -h localhost -U postgres -Fc -f backup.dump mydb

# Logical restore
pg_restore -h localhost -U postgres -d mydb backup.dump

# Physical backup (for PITR)
pg_basebackup -h localhost -U replication -D /backup/base -Fp -Xs -P

# WAL archiving (postgresql.conf)
archive_mode = on
archive_command = 'cp %p /backup/wal/%f'
```

### PITR (Point-in-Time Recovery)

```text
1. Restore base backup
2. Configure recovery target:
   recovery_target_time = '2024-01-15 14:30:00 UTC'
3. Replay WAL files up to target time
4. Verify data integrity
```

### Backup Rules

| Rule | Rationale |
| --- | --- |
| Daily full backup + continuous WAL archiving | PITR capability |
| Test restore monthly | Backup is useless if restore fails |
| Store backups in different region | Protect against regional failures |
| Encrypt backups at rest | Compliance and data protection |
| Monitor backup job completion | Alert on backup failures immediately |
| Retain backups per policy (e.g., 30 days) | Balance cost and recovery needs |

---

## 5. Replication Patterns

### Primary-Replica Architecture

```text
Primary (read/write)
  ├── Replica 1 (read-only) ── Application reads
  ├── Replica 2 (read-only) ── Reporting/analytics
  └── Replica 3 (read-only) ── Backup/disaster recovery
```

### Replication Types

| Type | Consistency | Latency | Data Loss Risk |
| --- | --- | --- | --- |
| Synchronous | Strong | Higher (waits for replica) | None |
| Asynchronous | Eventual | Lower | Possible (replication lag) |
| Semi-synchronous | Strong (1+ replica) | Medium | Minimal |

### Replication Lag Monitoring

```sql
-- PostgreSQL: check replication lag
SELECT
  client_addr,
  state,
  sent_lsn,
  write_lsn,
  flush_lsn,
  replay_lsn,
  pg_wal_lsn_diff(sent_lsn, replay_lsn) AS byte_lag
FROM pg_stat_replication;
```

### Application-Level Considerations

| Scenario | Solution |
| --- | --- |
| Read-after-write consistency | Route reads to primary after writes |
| Stale read tolerance | Route to replicas with acceptable lag |
| Failover handling | Use connection proxy (PgBouncer, ProxySQL) |
| Split brain prevention | Use consensus-based failover (Patroni, Orchestrator) |

---

## 6. Connection Pool Tuning

### HikariCP Configuration

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
      idle-timeout: 300000          # 5 minutes
      max-lifetime: 1800000         # 30 minutes
      connection-timeout: 30000     # 30 seconds
      leak-detection-threshold: 60000  # 1 minute
      validation-timeout: 5000
```

### Pool Sizing Formula

```text
Optimal pool size = (core_count * 2) + effective_spindle_count

Example: 4-core server with SSD (1 spindle)
  Pool size = (4 * 2) + 1 = 9 connections

For most applications: 10-20 connections is sufficient.
More connections ≠ more throughput — excessive connections cause contention.
```

### Monitoring Metrics

| Metric | Warning | Action |
| --- | --- | --- |
| Active connections > 80% pool | Approaching limit | Investigate slow queries, increase pool |
| Connection wait time > 1s | Starvation | Increase pool or optimize queries |
| Leak detection triggered | Connection leak | Fix code that doesn't close connections |
| Connection creation rate high | Pool too small or connections dying | Check max-lifetime, increase minimum-idle |

---

## 7. Change Data Capture (CDC)

### Debezium Architecture

```text
Source Database → Debezium Connector → Kafka → Consumers
  (PostgreSQL)     (reads WAL/binlog)   (topics)   (services)
```

### Outbox Pattern with CDC

```sql
-- Outbox table
CREATE TABLE outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR(255) NOT NULL,
    aggregate_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

```kotlin
// In the same transaction as the business operation
@Transactional
fun createOrder(command: CreateOrderCommand): Order {
    val order = orderRepository.save(Order.from(command))

    // Write to outbox in same transaction — guaranteed consistency
    outboxRepository.save(OutboxEvent(
        aggregateType = "Order",
        aggregateId = order.id.toString(),
        eventType = "OrderCreated",
        payload = objectMapper.valueToTree(OrderCreatedEvent(order))
    ))

    return order
}
// Debezium captures the outbox insert via CDC and publishes to Kafka
```

### CDC Use Cases

| Use Case | Pattern |
| --- | --- |
| Event-driven microservices | Outbox + CDC → Kafka → consumers |
| Cache invalidation | CDC → detect changes → invalidate cache |
| Search index sync | CDC → Elasticsearch/OpenSearch indexer |
| Data warehouse sync | CDC → ETL pipeline → analytics DB |
| Audit logging | CDC → immutable audit log |

### Schema Evolution with CDC

- Use a schema registry (Confluent, Apicurio) for Avro/Protobuf schemas
- Apply backward-compatible changes (add optional fields, not remove required ones)
- Version event schemas explicitly
- Test schema compatibility before deployment
