# Scalability and Data Architecture Patterns

## Database Replication

```text
     Writes           Reads
        |                |
        v                v
+---------------+  +---------------+
| Master DB     |-->  Replica 1    |
| (Primary)     |  +---------------+
+---------------+  +---------------+
                   | Replica 2    |
                   +---------------+
```

**Benefits**:

- Better read performance
- Reliability (data copies)
- Availability (failover)

## Database Sharding

Partition data across multiple servers.

```text
+---------------------------------------------+
|                Sharding Key                 |
|                                             |
|  user_id % 3 = 0  ->  Shard 1               |
|  user_id % 3 = 1  ->  Shard 2               |
|  user_id % 3 = 2  ->  Shard 3               |
+---------------------------------------------+
```

**Sharding Strategies**:

- Hash-based: `shard = hash(key) % num_shards`
- Range-based: A-M -> Shard 1, N-Z -> Shard 2
- Directory-based: Lookup table for mapping

**Challenges**:

- Cross-shard joins
- Rebalancing
- Hot spots

## Cache Patterns

### Cache-Aside (Lazy Loading)

```text
1. Check cache
2. If miss, read from DB
3. Write to cache
4. Return data
```

```java
public Data getData(String key) {
    Data data = cache.get(key);
    if (data == null) {
        data = database.query(key);
        cache.set(key, data, ttl);
    }
    return data;
}
```

### Write-Through

```text
1. Write to cache
2. Write to database
3. Confirm only after both succeed
```

### Write-Back (Write-Behind)

```text
1. Write to cache
2. Acknowledge immediately
3. Async write to database
```

## CDN Workflow

```text
+------------------+
|    User          |
|  (Seoul)         |
+------+-----------+
       |
       v
+--------------+
|  Edge Server |  <- Cached content
|  (Seoul)     |
+--------------+
       | (cache miss)
       v
+--------------+
|   Origin     |
|  (US East)   |
+--------------+
```

1. User requests static content (image, CSS, JS)
2. CDN edge server checks cache
3. If cached -> return immediately
4. If not cached -> fetch from origin, cache, return

## Stateless Architecture

### Problem: Sticky Sessions

```text
User A always -> Server 1
User B always -> Server 2

If Server 1 fails -> User A loses session
```

### Solution: External Session Store

```text
+---------------------------------------------------+
|                  Web Servers                       |
|  +---------+  +---------+  +---------+            |
|  | Server 1|  | Server 2|  | Server 3|            |
|  +----+----+  +----+----+  +----+----+            |
|       |            |            |                  |
|       +------------+------------+                  |
|                    |                               |
|                    v                               |
|            +---------------+                       |
|            | Session Store |  <- Redis/Memcached   |
|            +---------------+                       |
+---------------------------------------------------+
```

## Data Center Architecture

### Multi-Data Center Setup

```text
+---------------------+    +---------------------+
|   Data Center 1     |    |   Data Center 2     |
|    (US East)        |    |    (US West)        |
|                     |    |                     |
|  +---------------+  |    |  +---------------+  |
|  | Load Balancer |  |    |  | Load Balancer |  |
|  +-------+-------+  |    |  +-------+-------+  |
|          |          |    |          |          |
|    +-----+-----+    |    |    +-----+-----+    |
|    v           v    |    |    v           v    |
| +-----+    +-----+  |    | +-----+    +-----+  |
| |Web 1|    |Web 2|  |    | |Web 1|    |Web 2|  |
| +-----+    +-----+  |    | +-----+    +-----+  |
+---------------------+    +---------------------+
```

### Failure Handling

- **Active-Active**: Both serve traffic
- **Active-Passive**: Standby takes over
- Failover time vs data consistency trade-off

## Consistent Hashing

### Problem: Rehashing

```text
With 4 servers: key -> server = hash(key) % 4
Add 1 server:   key -> server = hash(key) % 5
Result: Most keys need to move!
```

### Solution: Ring-based Hashing

```text
         0
        / \
   Server1  Server3
      /        \
   270        90
      \        /
   Server2  Server4
        \ /
        180

Key hashes to position on ring,
assigned to next clockwise server.
```

**Benefits**:

- Adding/removing server: Only K/N keys move
- Even distribution with virtual nodes

## Rate Limiting Implementation

### Token Bucket

```text
- Bucket holds tokens (max: capacity)
- Tokens added at fixed rate
- Each request consumes 1 token
- No tokens = reject
```

### Sliding Window

```text
- Track requests in time window
- New request: count requests in last N seconds
- If count > limit: reject
```

### Implementation Example

```java
class RateLimiter {
    private final int maxRequests;
    private final Duration window;
    private final Map<String, LinkedList<Long>> requests = new ConcurrentHashMap<>();

    public boolean allowRequest(String clientId) {
        long now = System.currentTimeMillis();
        LinkedList<Long> windowRequests = requests.computeIfAbsent(clientId, k -> new LinkedList<>());

        synchronized (windowRequests) {
            // Remove expired timestamps
            while (!windowRequests.isEmpty() &&
                   now - windowRequests.getFirst() > window.toMillis()) {
                windowRequests.removeFirst();
            }

            if (windowRequests.size() < maxRequests) {
                windowRequests.addLast(now);
                return true;
            }
            return false;
        }
    }
}
```

## Key-Value Store Architecture

```text
+---------------------------------------------------+
|                  Client                            |
+---------------------------+-----------------------+
                            |
                            v
+---------------------------------------------------+
|              Coordinator Service                   |
|  (Membership, Failure Detection, Routing)         |
+---------------------------+-----------------------+
                            |
        +-------------------+-------------------+
        v                   v                   v
+---------------+ +---------------+ +---------------+
|   Node 1      | |   Node 2      | |   Node 3      |
| (Partition 1) | | (Partition 2) | | (Partition 3) |
+---------------+ +---------------+ +---------------+
```

### Components

1. **Data Partitioning**: Consistent hashing
2. **Replication**: Leader-follower or quorum
3. **Consistency**: Tunable (R + W > N for strong)
4. **Failure Detection**: Heartbeats, gossip

## Unique ID Generation

### UUID

```text
128-bit: 32 hex chars
Pros: No coordination needed
Cons: Not ordered, large (36 chars)
```

### Snowflake (Twitter)

```text
64-bit ID structure:

Timestamp: milliseconds since epoch
Machine ID: up to 1024 machines
Sequence: up to 4096 IDs per ms per machine
```

```java
class SnowflakeIdGenerator {
    private final long machineId;
    private long lastTimestamp = -1L;
    private long sequence = 0L;

    public synchronized long nextId() {
        long timestamp = System.currentTimeMillis();

        if (timestamp == lastTimestamp) {
            sequence = (sequence + 1) & 0xFFF; // 12 bits
            if (sequence == 0) {
                timestamp = waitNextMillis(lastTimestamp);
            }
        } else {
            sequence = 0;
        }

        lastTimestamp = timestamp;
        return (timestamp << 22) | (machineId << 12) | sequence;
    }
}
```
