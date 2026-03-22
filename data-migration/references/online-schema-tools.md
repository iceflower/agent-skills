# Online Schema Migration Tools

## 1. gh-ost (GitHub Online Schema Transmogrifier)

### gh-ost Overview

- MySQL online schema migration tool by GitHub
- Uses binlog streaming instead of triggers — minimal impact on the source table
- Supports throttling based on replication lag, system load, or custom queries

### gh-ost Mechanism

```text
1. Create ghost table with desired schema
2. Copy existing rows in chunks (controlled pace)
3. Stream binlog events to apply ongoing changes to ghost table
4. Cut-over: atomically rename tables
```

### gh-ost Basic Usage

```bash
gh-ost \
  --host=replica.example.com \
  --database=mydb \
  --table=users \
  --alter="ADD COLUMN phone VARCHAR(20)" \
  --execute
```

### gh-ost Key Flags

| Flag                           | Purpose                                         |
| ------------------------------ | ----------------------------------------------- |
| `--execute`                    | Actually run (without this, it is dry-run)      |
| `--initially-drop-ghost-table` | Drop ghost table if exists from a previous run  |
| `--chunk-size`                 | Rows per copy iteration (default: 1000)         |
| `--max-lag-millis`             | Pause if replica lag exceeds this               |
| `--throttle-query`             | Custom SQL query to control throttling          |
| `--critical-load`              | Abort if system load exceeds threshold          |
| `--exact-rowcount`             | Calculate exact row count for progress display  |
| `--assume-rbr`                 | Assume row-based replication (skip validation)  |
| `--allow-on-master`            | Connect directly to master (not recommended)    |

### gh-ost Throttling Configuration

```bash
# Throttle when replica lag exceeds 2 seconds
gh-ost --max-lag-millis=2000

# Throttle based on custom query (e.g., active threads)
gh-ost --throttle-query="SELECT IF(COUNT(*) > 50, 1, 0) FROM information_schema.processlist"

# Abort if load exceeds critical threshold
gh-ost --critical-load="Threads_running=100"
```

### gh-ost Limitations

- Foreign key support is limited — tables with foreign keys require extra planning
- Does not support `RENAME TABLE` on tables referenced by foreign keys
- Requires binlog in ROW format
- The cut-over briefly acquires a table lock

### gh-ost Best Practices

- Always run without `--execute` first to validate the operation
- Run against a replica, not the master, when possible
- Set `--max-lag-millis` appropriate for your SLO
- Monitor the ghost table size and disk usage during migration
- Test the migration on a staging environment with production-like data

---

## 2. pt-online-schema-change (Percona Toolkit)

### pt-osc Overview

- MySQL online schema change tool from Percona
- Uses triggers to capture changes during migration
- Better foreign key support than gh-ost

### pt-osc Mechanism

```text
1. Create new table with desired schema
2. Create INSERT/UPDATE/DELETE triggers on original table
3. Copy rows in chunks from original to new table
4. Triggers replicate ongoing changes
5. Atomically swap old and new tables
6. Drop old table
```

### pt-osc Basic Usage

```bash
pt-online-schema-change \
  --alter "ADD COLUMN phone VARCHAR(20)" \
  --execute \
  D=mydb,t=users
```

### pt-osc Key Flags

| Flag                          | Purpose                                              |
| ----------------------------- | ---------------------------------------------------- |
| `--execute`                   | Actually run (otherwise dry-run)                     |
| `--chunk-size`                | Rows per copy iteration (default: 1000)              |
| `--max-lag`                   | Pause if replica lag exceeds value (seconds)         |
| `--check-interval`            | How often to check replica lag (seconds)             |
| `--critical-load`             | Abort if load exceeds threshold                      |
| `--set-vars`                  | Set session variables during operation               |
| `--alter-foreign-keys-method` | How to handle FK references (auto, rebuild, drop)    |
| `--no-drop-old-table`         | Keep old table after swap                            |

### pt-osc Foreign Key Handling

```bash
# Automatically decide FK handling method
pt-online-schema-change \
  --alter "ADD COLUMN phone VARCHAR(20)" \
  --alter-foreign-keys-method=auto \
  --execute \
  D=mydb,t=users
```

Methods:

| Method | Description |
| --- | --- |
| `rebuild_constraints` | Rebuild FKs to point to new table |
| `drop_swap` | Drop FKs, swap, recreate FKs |
| `auto` | Auto-select method by table size |
| `none` | Skip FKs, handle manually |

### pt-osc Limitations

- Triggers add overhead to every write on the original table
- Three triggers (INSERT, UPDATE, DELETE) increase write amplification
- Cannot run multiple instances on the same table simultaneously
- Trigger-based approach may cause issues with existing triggers on the table

### pt-osc Best Practices

- Check for existing triggers on the table before running
- Monitor trigger overhead during migration (watch `Threads_running`)
- Use `--no-drop-old-table` for safety — drop manually after verification
- Set appropriate `--chunk-size` based on row size and network bandwidth
- Test on staging with production-like data volume and write patterns

---

## 3. Comparison: gh-ost vs. pt-online-schema-change

| Aspect            | gh-ost                | pt-online-schema-change         |
| ----------------- | --------------------- | ------------------------------- |
| Change capture    | Binlog streaming      | Triggers                        |
| Write overhead    | None on source table  | 3 triggers per DML              |
| Foreign keys      | Limited support       | Good support                    |
| Existing triggers | No conflict           | May conflict                    |
| Pause/resume      | Built-in (file-based) | Kill and restart from beginning |
| Testability       | Dry-run mode          | Dry-run mode                    |
| Replication lag   | Fine-grained          | Basic                           |
| Community         | GitHub-maintained     | Percona-maintained              |
| Cut-over lock     | Brief table lock      | Brief table lock                |

### Decision Guide

- **Choose gh-ost when**:
  - No foreign keys are involved
  - Fine-grained throttling control is needed
  - Minimizing write impact on the source is critical
  - You need pause/resume capability

- **Choose pt-online-schema-change when**:
  - Tables have foreign key relationships
  - The table already has triggers (evaluate carefully)
  - Simpler operational model is preferred
  - Foreign key handling is a requirement

---

## 4. pgroll (PostgreSQL)

### pgroll Overview

- PostgreSQL schema migration tool by Xata
- Uses a versioned schema approach — multiple schema versions coexist
- Enables zero-downtime migrations by serving old and new schema simultaneously

### pgroll Mechanism

```text
1. Define migration in JSON format
2. pgroll starts migration — creates new schema version
3. Old and new schema versions coexist (via views)
4. Application gradually migrates to new schema version
5. Complete migration — old version is dropped
```

### pgroll Migration Definition Example

```json
{
  "name": "add_phone_column",
  "operations": [
    {
      "add_column": {
        "table": "users",
        "column": {
          "name": "phone",
          "type": "varchar(20)",
          "nullable": true
        }
      }
    }
  ]
}
```

### pgroll Commands

```bash
# Start a migration (creates new schema version)
pgroll start migration.json

# Complete the migration (drop old schema version)
pgroll complete

# Roll back an in-progress migration
pgroll rollback
```

### pgroll Version-Based Schema Access

```sql
-- Application using old schema version
SET search_path TO 'schema_v1';
SELECT * FROM users;  -- sees old schema

-- Application using new schema version
SET search_path TO 'schema_v2';
SELECT * FROM users;  -- sees new schema with phone column
```

### pgroll Key Features

| Feature                | Description                                       |
| ---------------------- | ------------------------------------------------- |
| Version coexistence    | Old and new schema versions active simultaneously |
| Automatic backfill     | Data transformations applied during migration     |
| Built-in rollback      | Roll back to previous version with one command    |
| View-based abstraction | Applications see versioned views, not raw tables  |
| Lock-free operations   | No exclusive locks during migration               |

### pgroll Supported Operations

| Operation           | Description                          |
| ------------------- | ------------------------------------ |
| `add_column`        | Add a new column                     |
| `drop_column`       | Remove a column                      |
| `rename_column`     | Rename a column                      |
| `alter_column`      | Change column type, default, or null |
| `create_table`      | Create a new table                   |
| `drop_table`        | Drop a table                         |
| `add_index`         | Add an index                         |
| `create_constraint` | Add a constraint                     |

### pgroll Best Practices

- Define migrations as version-controlled JSON files
- Test migrations in staging with representative data
- Monitor view performance — views add minimal overhead but verify
- Use the rollback command rather than manual schema manipulation
- Coordinate `search_path` changes with application deployments

### pgroll Limitations

- PostgreSQL only
- Requires application awareness of schema versioning (search_path)
- Relatively newer tool — evaluate maturity for your use case
- Complex multi-table migrations may require careful orchestration

---

## 5. General Online Schema Migration Rules

### Pre-Migration Checks

- Verify sufficient disk space (2x table size for the copy phase)
- Check replication lag baseline before starting
- Ensure no other schema changes are running on the same table
- Review current table locks and long-running queries
- Verify binlog format is ROW for gh-ost

### Monitoring During Migration

- Monitor disk usage — ghost/shadow tables consume additional space
- Watch replication lag — throttle or pause if it exceeds thresholds
- Track progress percentage and estimated time remaining
- Keep an open channel for manual intervention (pause, abort)

### Post-Migration Verification

- Verify data integrity (row counts, checksums)
- Monitor query performance on the migrated table
- Check index usage on the new table structure
- Clean up old tables after the retention period
- Document the migration for future reference
