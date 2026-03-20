---
name: database
description: >-
  Framework-agnostic database rules including migration conventions, query
  performance, transaction management, concurrency control (optimistic/pessimistic
  locking), backup strategies, replication patterns, connection pool tuning,
  and CDC. Includes MySQL and PostgreSQL specific guides.
  Use when writing SQL or designing database access.
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

# Database Rules

## 1. Migration File Conventions

### Naming Format

```text
V{version}__{description}.sql
```

| Element     | Rule                           | Example              |
| ----------- | ------------------------------ | -------------------- |
| Version     | Sequential number or timestamp | `V1`, `V20240115`    |
| Separator   | Double underscore `__`         | `V1__`               |
| Description | Snake_case, descriptive        | `create_users_table` |

### Migration Examples

```text
V1__create_users_table.sql
V2__add_email_index_to_users.sql
V3__create_orders_table.sql
V4__add_status_column_to_orders.sql
```

### Migration Rules

- Never modify a migration that has been applied to any environment
- Each migration must be idempotent where possible (use `IF NOT EXISTS`, `IF EXISTS`)
- Include both schema and essential seed data in migrations
- Test migrations against a copy of production data before applying

### Migration Safety Checklist

| Operation             | Risk   | Precaution                                     |
| --------------------- | ------ | ---------------------------------------------- |
| Add column (nullable) | Low    | Safe — no data rewrite needed                  |
| Add column (NOT NULL) | Medium | Requires default value or backfill             |
| Drop column           | High   | Ensure no application code references it       |
| Rename column         | High   | Use two-phase: add new → migrate → drop old    |
| Add index             | Medium | Use `CONCURRENTLY` on large tables (Postgres)  |
| Drop table            | High   | Verify no foreign keys or application refs     |
| Change column type    | High   | May require full table rewrite                 |

### Rollback Strategy

- Write corresponding rollback scripts for each migration
- For irreversible changes (drop column), document the decision and ensure backups exist
- Test rollback scripts in staging before production deployment

---

## 2. Query Performance

### Index Guidelines

- Add indexes on columns used in `WHERE`, `JOIN`, `ORDER BY`
- Use composite indexes for multi-column queries (column order matters)
- Avoid over-indexing — each index slows down writes
- Monitor slow query logs to identify missing indexes

### Composite Index Column Order

```text
Index (a, b, c) supports:
  ✅ WHERE a = ?
  ✅ WHERE a = ? AND b = ?
  ✅ WHERE a = ? AND b = ? AND c = ?
  ✅ WHERE a = ? ORDER BY b
  ❌ WHERE b = ?           (leftmost prefix not satisfied)
  ❌ WHERE b = ? AND c = ? (leftmost prefix not satisfied)
```

- Place equality columns before range columns
- Place high-selectivity columns first

### Query Best Practices

- Use pagination for list queries — never fetch unbounded result sets
- Avoid `SELECT *` — specify only needed columns for large tables
- Use `EXISTS` instead of `COUNT` for existence checks
- Avoid complex subqueries — prefer `JOIN` for readability and performance

### Pagination Patterns

| Pattern        | Pros                     | Cons                       | Best For            |
| -------------- | ------------------------ | -------------------------- | ------------------- |
| Offset-based   | Simple, page navigation  | Slow on large offsets      | Small datasets      |
| Cursor-based   | Consistent, fast         | No random page access      | Large datasets      |
| Keyset-based   | Fast, no offset overhead | Requires unique sort key   | Fixed sort order    |

```sql
-- Offset-based (simple but slow for large offsets)
SELECT * FROM users ORDER BY id LIMIT 20 OFFSET 100;

-- Cursor-based (fast and consistent)
SELECT * FROM users WHERE id > :last_seen_id ORDER BY id LIMIT 20;
```

### N+1 Query Detection

```text
Symptom: N similar queries in logs for a single operation

-- 1 query to fetch users
SELECT * FROM users WHERE status = 'ACTIVE';

-- N queries to fetch each user's orders (BAD)
SELECT * FROM orders WHERE user_id = 1;
SELECT * FROM orders WHERE user_id = 2;
...

-- Fix: single join query
SELECT u.*, o.* FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.status = 'ACTIVE';
```

---

## 3. Transaction Management Principles

### General Rules

| Rule                                      | Reason                              |
| ----------------------------------------- | ----------------------------------- |
| Keep transactions as short as possible    | Reduces lock contention             |
| No external API calls inside transactions | Prevents long-held locks on timeout |
| Use read-only transactions for reads      | Enables query optimizations         |
| Default to reusing existing transaction   | Avoids unnecessary overhead         |
| Use independent transactions sparingly    | Can cause deadlocks                 |

### Scope Example

```text
1. Read data (inside transaction or read-only)
2. Call external API (outside transaction)
3. Write result (separate transaction)
```

### Isolation Levels

| Level            | Dirty Read | Non-Repeatable Read | Phantom Read | Use Case                   |
| ---------------- | ---------- | ------------------- | ------------ | -------------------------- |
| READ UNCOMMITTED | Possible   | Possible            | Possible     | Almost never appropriate   |
| READ COMMITTED   | No         | Possible            | Possible     | Default for most databases |
| REPEATABLE READ  | No         | No                  | Possible     | Financial calculations     |
| SERIALIZABLE     | No         | No                  | No           | Critical consistency needs |

- Default to database's built-in isolation level (usually READ COMMITTED)
- Only increase isolation when business logic requires stronger guarantees
- Higher isolation = more locking = lower concurrency

### Deadlock Prevention

- Always acquire locks in a consistent, predictable order
- Keep lock scope as small as possible
- Set statement/query timeouts to avoid indefinite waits
- Log and monitor deadlock occurrences

---

## 4. Data Integrity

### Constraints

| Constraint    | Purpose                        | When to Use                          |
| ------------- | ------------------------------ | ------------------------------------ |
| PRIMARY KEY   | Unique row identity            | Every table                          |
| FOREIGN KEY   | Referential integrity          | Related tables                       |
| UNIQUE        | Prevent duplicate values       | Business-unique columns (email, etc.)|
| NOT NULL      | Prevent missing values         | Required fields                      |
| CHECK         | Validate value range/format    | Enum-like or bounded values          |
| DEFAULT       | Provide fallback value         | Optional fields with sensible default|

### Rules

- Enforce data integrity at the database level, not just application level
- Application validations may be bypassed; database constraints are the last line of defense
- Use `ON DELETE CASCADE` cautiously — prefer explicit application-level deletion

---

## 5. Anti-Patterns

- Unbounded queries without pagination
- `SELECT *` on large tables
- N+1 query patterns (loop of individual queries)
- Long-running transactions with external calls
- Missing indexes on frequently queried columns
- Modifying applied migration files
- No slow query monitoring
- Using database as a message queue
- Storing large blobs in relational tables without evaluating object storage
- Missing foreign key constraints on related tables
- Using `FLOAT`/`DOUBLE` for monetary values (use `DECIMAL`/`NUMERIC`)

## Additional References

- For MySQL-specific rules, see [references/mysql.md](references/mysql.md)
- For PostgreSQL-specific rules, see [references/postgresql.md](references/postgresql.md)
- For concurrency control and reliability patterns, see [references/concurrency-and-reliability.md](references/concurrency-and-reliability.md)
