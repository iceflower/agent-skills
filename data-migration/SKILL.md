---
name: data-migration
description: >-
  Data migration and ETL patterns including zero-downtime migration strategies
  (dual-write, shadow table, expand-and-contract), online schema migration
  tools (gh-ost, pt-online-schema-change, pgroll), large-scale data migration
  planning, ETL/ELT pipeline design, CDC (Change Data Capture), backward
  compatible schema changes, data validation and reconciliation, and rollback
  strategies.
  Use when planning database migrations, implementing zero-downtime schema
  changes, designing ETL/ELT pipelines, or performing large-scale data
  movement between systems.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# Data Migration and ETL Patterns

## 1. Zero-Downtime Migration Principles

### Core Rules

- Never perform destructive schema changes in a single step
- Always maintain backward compatibility during the transition period
- Deploy application changes before (or simultaneously with) schema changes
- Validate data integrity at every phase before proceeding to the next
- Have a tested rollback plan before starting any migration

### Migration Strategy Selection

| Strategy            | Complexity | Best For                         | Risk Level |
| ------------------- | ---------- | -------------------------------- | ---------- |
| Expand-and-Contract | Medium     | Column renames, type changes     | Low        |
| Dual-Write          | High       | Table splits, system migrations  | Medium     |
| Shadow Table        | Medium     | Large table restructuring        | Low        |
| Blue-Green Database | Very High  | Full database engine replacement | High       |

### Risk Assessment Before Migration

| Factor              | Low Risk                 | High Risk                           |
| ------------------- | ------------------------ | ----------------------------------- |
| Table size          | < 1M rows                | > 100M rows                         |
| Write frequency     | < 100 writes/sec         | > 1000 writes/sec                   |
| Downtime tolerance  | Minutes acceptable       | Zero tolerance                      |
| Rollback complexity | Simple reverse migration | Requires data reconciliation        |
| Dependencies        | Single application       | Multiple services share the table   |

---

## 2. Expand-and-Contract Pattern (Parallel Change)

A three-phase approach to safely evolve database schemas.

### Phase Overview

```text
Phase 1 — Expand:   Add new column/table alongside the old one
Phase 2 — Migrate:  Backfill data, update application to use new structure
Phase 3 — Contract: Remove old column/table after verification
```

### Example: Renaming a Column

```sql
-- Phase 1: Expand — add new column
ALTER TABLE users ADD COLUMN full_name VARCHAR(255);

-- Phase 2: Migrate — backfill data
UPDATE users SET full_name = name WHERE full_name IS NULL;

-- Application deploys: write to both columns, read from full_name

-- Phase 3: Contract — remove old column (after verification period)
ALTER TABLE users DROP COLUMN name;
```

### Expand-and-Contract Execution Rules

- Each phase must be a separate deployment
- Allow a stabilization period between phases (at least one full release cycle)
- Monitor error rates and query performance between phases
- Never skip the verification step before the contract phase

---

## 3. Dual-Write Pattern

### Four Stages

```text
Stage 1 — Dark Write:    Write to new system, but do not read from it
Stage 2 — Shadow Read:   Read from both systems, compare results, serve old
Stage 3 — Cutover:       Read from new system, stop writing to old
Stage 4 — Cleanup:       Remove old system references
```

### Implementation Guidelines

- The old system remains the source of truth until Stage 3
- Log all discrepancies found during Shadow Read without failing requests
- Set a discrepancy threshold (e.g., < 0.01%) before allowing cutover
- Implement circuit breakers to fall back to the old system if the new system fails

### Consistency Considerations

- Dual writes are not atomic — handle partial failures explicitly
- Use idempotent writes to safely retry on failure
- Consider using an outbox pattern or CDC to keep systems in sync
- Monitor write lag between systems during the transition

For detailed implementation guides, see [references/zero-downtime-patterns.md](references/zero-downtime-patterns.md).

---

## 4. Shadow Table Pattern

### Process

```text
1. Create new table with desired schema
2. Set up triggers or CDC to replicate ongoing changes
3. Backfill historical data
4. Validate data consistency
5. Swap table names atomically (RENAME TABLE)
6. Drop old table after verification period
```

### Shadow Table Execution Rules

- Trigger-based replication adds overhead to every write — monitor performance
- Backfill in batches to avoid long-running transactions
- During the swap, briefly acquire an exclusive lock — plan for this
- Keep the old table for a defined retention period before dropping

---

## 5. Online Schema Migration Tools

| Feature              | gh-ost           | pt-osc           | pgroll               |
| -------------------- | ---------------- | ---------------- | -------------------- |
| Database             | MySQL            | MySQL            | PostgreSQL           |
| Mechanism            | Binlog streaming | Triggers         | Version-based schema |
| Lock-free            | Yes              | Mostly           | Yes                  |
| Throttle support     | Yes (built-in)   | Yes (built-in)   | N/A                  |
| FK support           | Limited          | Yes              | Yes                  |
| Replication-friendly | Yes              | Requires caution | N/A                  |

### Tool Selection Guide

- **gh-ost**: Preferred for MySQL when replication lag sensitivity is critical
- **pt-online-schema-change**: Use when foreign key support is required on MySQL
- **pgroll**: Use for PostgreSQL version-based schema migrations with rollback

For detailed tool comparison and usage, see [references/online-schema-tools.md](references/online-schema-tools.md).

---

## 6. Backward-Compatible Schema Changes

### Safe Changes (Additive-Only)

| Operation               | Safe | Notes                                    |
| ----------------------- | ---- | ---------------------------------------- |
| Add nullable column     | Yes  | No existing code breaks                  |
| Add table               | Yes  | No existing code breaks                  |
| Add index               | Yes  | Use `CONCURRENTLY` on large tables (PG)  |
| Add column with default | Yes  | Safe on modern MySQL 8.0+ and PostgreSQL |
| Widen column type       | Yes  | e.g., `VARCHAR(50)` to `VARCHAR(100)`    |

### Unsafe Changes (Require Expand-and-Contract)

| Operation                 | Risk   | Required Approach                            |
| ------------------------- | ------ | -------------------------------------------- |
| Drop column               | High   | Remove app references first, then drop       |
| Rename column             | High   | Add new, migrate, then drop old              |
| Narrow column type        | High   | May truncate data                            |
| Change column to NOT NULL | Medium | Backfill defaults first, then add constraint |
| Drop table                | High   | Verify no references, keep backup            |

### Schema Change Compatibility Rules

- All schema changes in production must be additive-only in the first deployment
- Destructive changes happen in subsequent deployments after verification
- Every migration must be reviewed for backward compatibility before merge

---

## 7. Data Validation and Reconciliation

### Validation Stages

```text
Pre-migration:  Snapshot source data counts and checksums
During:         Monitor migration progress and error rates
Post-migration: Compare source vs. target data
```

### Reconciliation Checklist

- Row count comparison between source and target
- Checksum or hash comparison on critical columns
- Referential integrity verification on the target
- Boundary value and edge case spot checks
- Application-level smoke tests against the new data

### Automated Validation Query Example

```sql
-- Row count comparison
SELECT 'source' AS system, COUNT(*) AS row_count FROM old_table
UNION ALL
SELECT 'target' AS system, COUNT(*) AS row_count FROM new_table;

-- Checksum comparison on critical columns
SELECT MD5(GROUP_CONCAT(CONCAT(id, email, status) ORDER BY id)) AS checksum
FROM old_table;

SELECT MD5(GROUP_CONCAT(CONCAT(id, email, status) ORDER BY id)) AS checksum
FROM new_table;
```

### Validation Acceptance Rules

- Never skip post-migration validation, even for small migrations
- Define acceptance criteria (e.g., 100% row match, checksum match) before starting
- Keep source data accessible for at least one release cycle after migration

---

## 8. ETL vs. ELT Pattern Selection

### Comparison

| Aspect             | ETL                              | ELT                                 |
| ------------------ | -------------------------------- | ----------------------------------- |
| Transform location | Staging/middleware               | Target system (data warehouse)      |
| Best for           | Structured, well-defined schemas | Exploratory analytics, raw storage  |
| Latency            | Higher (transform before load)   | Lower (load first, transform later) |
| Scalability        | Limited by middleware compute    | Leverages target system compute     |
| Data quality       | Enforced before loading          | Enforced after loading              |

### Selection Guide

- Use **ETL** when data quality must be guaranteed before loading
- Use **ELT** when the target system has strong compute capability (e.g., BigQuery, Snowflake)
- Use **ETL** for compliance-sensitive data that must be masked before storage
- Use **ELT** when schema is evolving and raw data preservation is important

### Pipeline Design Guidelines

- Make every pipeline step idempotent and re-runnable
- Use watermark or checkpoint-based incremental loading
- Implement dead-letter queues for records that fail transformation
- Log and alert on data quality metric degradation
- Version pipeline configurations alongside application code

---

## 9. CDC (Change Data Capture)

### Pattern Overview

```text
Source DB → Change Log (binlog/WAL) → CDC Connector → Target System
```

### CDC Approaches

| Approach        | Mechanism                    | Latency         | Impact on Source |
| --------------- | ---------------------------- | --------------- | ---------------- |
| Log-based       | Read DB transaction log      | Near real-time  | Minimal          |
| Trigger-based   | Database triggers            | Real-time       | Moderate         |
| Poll-based      | Periodic SELECT queries      | Seconds-minutes | Low-Moderate     |
| Timestamp-based | Query by `updated_at` column | Seconds-minutes | Low              |

### CDC Implementation Rules

- Prefer log-based CDC (e.g., Debezium) for minimal source impact
- Ensure CDC consumers handle out-of-order and duplicate events
- Include schema change handling in CDC pipeline design
- Monitor CDC lag — alert if lag exceeds acceptable thresholds
- Handle DDL changes in the CDC stream (add column, drop column)

### Common Tools

| Tool     | Source Support     | Sink Support              |
| -------- | ------------------ | ------------------------- |
| Debezium | MySQL, PG, MongoDB | Kafka, any Kafka consumer |
| AWS DMS  | Most RDBMS, MongoDB| S3, RDS, Redshift, etc.   |
| Airbyte  | 300+ connectors    | Data warehouses, lakes    |
| Fivetran | SaaS, RDBMS        | Data warehouses           |

---

## 10. Rollback Strategies

### Rollback Approach by Migration Type

| Migration Type           | Rollback Strategy                                   |
| ------------------------ | --------------------------------------------------- |
| Add column               | Drop column (safe if no code references it yet)     |
| Rename column (expanded) | Revert app to read old column, drop new column      |
| Data backfill            | No rollback needed if old column is still populated |
| Table split (dual-write) | Revert to old system reads, stop new system writes  |
| System migration         | Circuit breaker fallback to old system              |

### Rollback Execution Rules

- Every migration must have a documented rollback procedure
- Test rollback procedures in staging before production deployment
- Set a point-of-no-return threshold — define when rollback is no longer safe
- Maintain data backups taken before migration for at least one release cycle
- Rollback must not cause data loss for writes that occurred during migration

---

## 11. Large-Scale Migration Checklist

### Pre-Migration

- [ ] Document current schema and data volumes
- [ ] Identify all applications and services that access the affected tables
- [ ] Estimate migration duration based on data volume and write rate
- [ ] Create and test rollback procedures
- [ ] Set up monitoring for migration progress, error rates, and performance
- [ ] Take a consistent backup of the source data
- [ ] Communicate migration schedule to stakeholders

### During Migration

- [ ] Monitor replication lag and system resource usage
- [ ] Watch for lock contention and long-running queries
- [ ] Track migration progress (rows processed, estimated time remaining)
- [ ] Verify application error rates remain within acceptable bounds
- [ ] Keep the rollback plan ready for immediate execution

### Post-Migration

- [ ] Run data validation and reconciliation checks
- [ ] Verify application functionality with smoke tests
- [ ] Monitor performance metrics for regressions
- [ ] Update documentation and runbooks
- [ ] Schedule cleanup of deprecated schemas (contract phase)
- [ ] Conduct a post-mortem review

## Additional References

- For zero-downtime pattern details, see [references/zero-downtime-patterns.md](references/zero-downtime-patterns.md)
- For online schema tool comparison, see [references/online-schema-tools.md](references/online-schema-tools.md)
