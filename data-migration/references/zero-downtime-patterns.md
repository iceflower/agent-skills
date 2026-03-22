# Zero-Downtime Migration Patterns

## 1. Dual-Write Pattern — Detailed Implementation

### Stage 1: Dark Write

Write to both old and new systems. Read exclusively from the old system.

```text
Application
  ├── Write → Old DB (primary)
  └── Write → New DB (async, best-effort)
  └── Read  ← Old DB
```

#### Dark Write Implementation Rules

- Use asynchronous writes to the new system to avoid latency impact
- Catch and log new-system write failures without failing the request
- Implement idempotent writes (use upsert or deduplication keys)
- Monitor write success rate to the new system

#### Dark Write Error Handling

```text
try:
    write_to_old_system(data)      # Must succeed
    write_to_new_system(data)      # Best-effort
except NewSystemError:
    log_error(data, error)         # Log but do not fail
    enqueue_for_retry(data)        # Retry queue
```

### Stage 2: Shadow Read

Read from both systems. Serve results from the old system. Compare results in the background.

```text
Application
  ├── Write → Old DB
  ├── Write → New DB
  ├── Read  ← Old DB (served to user)
  └── Read  ← New DB (comparison only)
```

#### Shadow Read Comparison Rules

- Compare results asynchronously — do not block the response
- Log all discrepancies with full context (query, old result, new result)
- Categorize discrepancies: data mismatch, missing record, extra record
- Track discrepancy rate over time — it should trend toward zero

#### Shadow Read Discrepancy Report Example

```text
Comparison Report — 2026-03-20
Total comparisons:   1,000,000
Matches:             999,985 (99.9985%)
Mismatches:          12 (0.0012%)
Missing in new:      3 (0.0003%)
Extra in new:        0

Decision: Discrepancy rate below 0.01% threshold — safe for cutover
```

### Stage 3: Cutover

Switch reads to the new system. Continue writing to both temporarily.

```text
Application
  ├── Write → Old DB (temporary)
  ├── Write → New DB (primary)
  └── Read  ← New DB (served to user)
```

#### Cutover Execution Rules

- Use feature flags to control the cutover — enable per-service or per-region
- Monitor error rates closely for the first 24-48 hours
- Keep the old system writable as a fallback
- Define rollback triggers (e.g., error rate > 1%, latency > 2x baseline)

#### Cutover Feature Flag Example

```text
migration.read_source=new      # Switch read to new system
migration.write_old=true       # Continue writing to old (fallback)
migration.write_new=true       # Primary writes to new
```

### Stage 4: Cleanup

Stop writing to the old system. Remove dual-write code. Decommission old system.

```text
Application
  ├── Write → New DB (only)
  └── Read  ← New DB (only)
```

#### Cleanup Execution Rules

- Wait at least one full release cycle after cutover before cleanup
- Remove feature flags and dual-write code in a dedicated cleanup deployment
- Archive old system data according to retention policies
- Update documentation, runbooks, and monitoring dashboards

---

## 2. Expand-and-Contract — Detailed Examples

### Example: Splitting a Column

Scenario: Split `address` into `street`, `city`, `state`, `zip`.

#### Column Split — Expand Phase

```sql
ALTER TABLE customers ADD COLUMN street VARCHAR(255);
ALTER TABLE customers ADD COLUMN city VARCHAR(100);
ALTER TABLE customers ADD COLUMN state VARCHAR(50);
ALTER TABLE customers ADD COLUMN zip VARCHAR(20);
```

Application changes: write to all five columns, read from new columns with fallback to `address`.

#### Column Split — Migrate Phase

```sql
-- Backfill in batches
UPDATE customers
SET street = parse_street(address),
    city = parse_city(address),
    state = parse_state(address),
    zip = parse_zip(address)
WHERE street IS NULL
LIMIT 10000;
```

- Run backfill in batches to avoid long locks
- Parse functions should handle edge cases gracefully
- Validate parsed data before writing

#### Column Split — Contract Phase

```sql
-- Only after verification
ALTER TABLE customers DROP COLUMN address;
```

- Verify all application code reads from new columns
- Confirm no queries reference the old `address` column
- Run validation queries comparing parsed data to original

### Example: Changing a Column Type

Scenario: Change `price` from `FLOAT` to `DECIMAL(10,2)`.

#### Type Change — Expand Phase

```sql
ALTER TABLE products ADD COLUMN price_decimal DECIMAL(10,2);
```

#### Type Change — Migrate Phase

```sql
UPDATE products SET price_decimal = CAST(price AS DECIMAL(10,2))
WHERE price_decimal IS NULL
LIMIT 10000;
```

Application writes to both `price` and `price_decimal`. Application reads from `price_decimal`.

#### Type Change — Contract Phase

```sql
ALTER TABLE products DROP COLUMN price;
ALTER TABLE products RENAME COLUMN price_decimal TO price;
```

---

## 3. Shadow Table Pattern — Detailed Implementation

### Step-by-Step Process

#### Step 1: Create Shadow Table

```sql
CREATE TABLE users_new (
    id BIGINT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),  -- new column
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_email (email)
);
```

#### Step 2: Set Up Replication

Option A — Trigger-based (MySQL):

```sql
DELIMITER //
CREATE TRIGGER users_insert_sync
AFTER INSERT ON users
FOR EACH ROW
BEGIN
    INSERT INTO users_new (id, email, full_name, created_at)
    VALUES (NEW.id, NEW.email, NEW.name, NEW.created_at)
    ON DUPLICATE KEY UPDATE email = NEW.email, full_name = NEW.name;
END //

CREATE TRIGGER users_update_sync
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    UPDATE users_new
    SET email = NEW.email, full_name = NEW.name
    WHERE id = NEW.id;
END //

CREATE TRIGGER users_delete_sync
AFTER DELETE ON users
FOR EACH ROW
BEGIN
    DELETE FROM users_new WHERE id = OLD.id;
END //
DELIMITER ;
```

Option B — CDC-based:

```text
Debezium connector → Kafka topic → Consumer → INSERT/UPDATE into users_new
```

#### Step 3: Backfill Historical Data

```sql
INSERT INTO users_new (id, email, full_name, created_at)
SELECT id, email, name, created_at FROM users
WHERE id NOT IN (SELECT id FROM users_new)
ORDER BY id
LIMIT 10000;
```

- Run in batches to avoid locking the source table
- Track progress using the last processed `id`

#### Step 4: Validate

```sql
-- Row count
SELECT
    (SELECT COUNT(*) FROM users) AS source_count,
    (SELECT COUNT(*) FROM users_new) AS target_count;

-- Sample checksum
SELECT COUNT(*) FROM users u
LEFT JOIN users_new un ON u.id = un.id
WHERE un.id IS NULL OR u.email != un.email;
```

#### Step 5: Atomic Swap

```sql
-- MySQL atomic rename
RENAME TABLE users TO users_old, users_new TO users;
```

For PostgreSQL:

```sql
BEGIN;
ALTER TABLE users RENAME TO users_old;
ALTER TABLE users_new RENAME TO users;
COMMIT;
```

#### Step 6: Cleanup

```sql
-- After verification period (e.g., 7 days)
DROP TRIGGER IF EXISTS users_insert_sync;
DROP TRIGGER IF EXISTS users_update_sync;
DROP TRIGGER IF EXISTS users_delete_sync;
DROP TABLE users_old;
```

---

## 4. Verification Strategy

### Multi-Level Verification

```text
Level 1 — Count verification:       Row counts match
Level 2 — Schema verification:      Column types and constraints match expectations
Level 3 — Data verification:        Checksums or hash comparisons on sample data
Level 4 — Application verification: Smoke tests pass against migrated data
Level 5 — Performance verification: Query performance within acceptable bounds
```

### Continuous Monitoring Post-Migration

| Metric                | Threshold     | Action if Exceeded              |
| --------------------- | ------------- | ------------------------------- |
| Error rate            | > 1% increase | Investigate, prepare rollback   |
| Query latency (p99)   | > 2x baseline | Check query plans, indexes      |
| Replication lag       | > 30 seconds  | Throttle migration writes       |
| Disk usage            | > 80% capacity| Expand storage proactively      |
| Connection pool usage | > 70% capacity| Scale or optimize queries       |

### Go/No-Go Decision Framework

```text
All MUST conditions met:
  Row counts match (100%)
  Checksum validation passes
  No critical discrepancies in shadow reads
  Application smoke tests pass
  Rollback procedure tested

All SHOULD conditions met:
  Performance within 10% of baseline
  No increase in error rates
  Stakeholder sign-off received

Decision: If all MUST conditions pass -> proceed with cutover
          If any MUST condition fails -> do not proceed
```
