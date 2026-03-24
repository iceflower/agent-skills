# Data Replication Patterns

16 patterns for reliable data replication in distributed systems.

> **Note**: Pattern names and concepts are inspired by "Patterns of Distributed Systems" by Unmesh Joshi.

---

## Pattern 1: Write-Ahead Log (WAL)

Persist operations before applying them.

```text
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│    WAL      │────▶│   State     │
│   Request   │     │  (append)   │     │  Machine    │
└─────────────┘     └─────────────┘     └─────────────┘
```

**Problem**: System crash loses in-memory state changes.

**Solution**:

1. Append operation to log file
2. Acknowledge after durable write
3. Apply operation to state
4. Use log for crash recovery

**Implementation**:

```java
class WriteAheadLog {
    private final File logFile;

    public long append(LogEntry entry) {
        long index = logFile.length();
        logFile.seek(index);
        logFile.write(entry.serialize());
        logFile.fsync(); // Durability
        return index;
    }

    public List<LogEntry> readAll() {
        return logFile.readLines()
            .map(LogEntry::deserialize)
            .collect(Collectors.toList());
    }
}
```

---

## Pattern 2: Segmented Log

Split log into multiple files for manageability.

**Problem**: Single log file grows unbounded; hard to manage.

**Solution**:

- Split log into fixed-size segments
- New segment when current reaches size limit
- Old segments can be archived/deleted

```text
log/
├── segment_0001.log (closed)
├── segment_0002.log (closed)
└── segment_0003.log (active)
```

---

## Pattern 3: Low-Water Mark

Track minimum log index needed for recovery.

**Purpose**: Know which log entries can be safely deleted.

**Types**:

- **Snapshot-based**: Log index at snapshot time
- **Time-based**: Entries older than threshold

```java
class LowWaterMark {
    private volatile long mark = 0;

    public void updateFromSnapshot(long snapshotIndex) {
        this.mark = Math.max(this.mark, snapshotIndex);
    }

    public boolean canDelete(long logIndex) {
        return logIndex < mark;
    }
}
```

---

## Pattern 4: Leader-Follower

Single coordinator manages state machine cluster.

```text
        ┌──────────┐
        │  Leader  │
        └────┬─────┘
        ┌────┴────┐
   ┌────▼───┐ ┌───▼────┐
   │Follower│ │Follower│
   └────────┘ └────────┘
```

**Leader Responsibilities**:

- Process all writes
- Replicate to followers
- Respond to clients

**Follower Responsibilities**:

- Accept replication from leader
- Respond to read requests (eventually consistent)

---

## Pattern 5: Heartbeat

Detect node failures in cluster.

**Implementation**:

```java
class HeartbeatMonitor {
    private final Map<NodeId, Long> lastHeartbeat = new ConcurrentHashMap<>();
    private final long heartbeatInterval = 5000; // ms
    private final long failureThreshold = 15000; // ms

    public void recordHeartbeat(NodeId nodeId) {
        lastHeartbeat.put(nodeId, System.currentTimeMillis());
    }

    public Set<NodeId> detectFailedNodes() {
        long now = System.currentTimeMillis();
        return lastHeartbeat.entrySet().stream()
            .filter(e -> now - e.getValue() > failureThreshold)
            .map(Map.Entry::getKey)
            .collect(Collectors.toSet());
    }
}
```

---

## Pattern 6: Quorum

Require majority agreement for decisions.

**Formula**: Quorum = (N / 2) + 1

**Why?** Ensures only one decision can be made.

| Cluster Size | Quorum | Tolerates Failures |
| ------------ | ------ | ------------------ |
| 3            | 2      | 1                  |
| 5            | 3      | 2                  |
| 7            | 4      | 3                  |

**Elastic Quorum**: Adjust quorum during partial failures.

---

## Pattern 7: Generation Clock

Track leadership epochs to detect stale leaders.

```text
Generation = (term, nodeId)

Higher generation always wins.
Same generation → compare nodeId
```

**Use Cases**:

- Leader election
- Detecting split-brain
- Preventing stale updates

---

## Pattern 8: High-Water Mark

Track maximum replicated log index.

**Purpose**:

- Know when entries are safely replicated
- Allow followers to serve consistent reads

```java
class HighWaterMark {
    private final int quorum;
    private final Map<Integer, Long> replicationIndexes = new ConcurrentHashMap<>();

    public void updateReplicaIndex(int replicaId, long index) {
        replicationIndexes.put(replicaId, index);
    }

    public long computeHighWaterMark() {
        return replicationIndexes.values().stream()
            .sorted(Comparator.reverseOrder())
            .limit(quorum)
            .skip(quorum - 1)
            .findFirst()
            .orElse(0L);
    }
}
```

---

## Pattern 9: Paxos

Distributed consensus algorithm.

**Roles**:

- **Proposer**: Proposes values
- **Acceptor**: Votes on proposals
- **Learner**: Learns decided values

**Phases**:

1. **Prepare**: Proposer sends prepare(n) with unique number n
2. **Promise**: Acceptors promise not to accept < n
3. **Accept**: Proposer sends accept(n, value)
4. **Accepted**: Acceptors accept if n is highest seen

---

## Pattern 10: Replicated Log

Consensus-based log replication (Raft-style).

```text
┌─────────────────────────────────────────────────────┐
│                    Leader                            │
│  ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐    │
│  │ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │ 7 │ 8 │ 9 │10 │11 │    │
│  └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘    │
│              commitIndex=5                           │
└──────────────┬──────────────┬───────────────────────┘
               │              │
        ┌──────▼──────┐ ┌─────▼──────┐
        │  Follower   │ │  Follower  │
        │ matchIndex=7│ │matchIndex=5│
        └─────────────┘ └────────────┘
```

**Leader Election**:

1. Follower times out → becomes candidate
2. Increments term, requests votes
3. Wins election with majority votes
4. Starts sending AppendEntries

**Log Replication**:

1. Leader receives client request
2. Appends to local log
3. Sends AppendEntries to followers
4. Commits when majority acknowledge
5. Applies to state machine

---

## Pattern 11: Single-Socket Channel

Process requests sequentially per connection.

**Problem**: Out-of-order responses confuse clients.

**Solution**: One request at a time per socket.

```java
class SingleSocketChannel {
    private final Socket socket;
    private final Object lock = new Object();

    public Response sendRequest(Request request) {
        synchronized (lock) {
            socket.write(request.serialize());
            return Response.deserialize(socket.read());
        }
    }
}
```

---

## Pattern 12: Request Queue

Handle concurrent requests with ordering.

```text
┌──────────────────────────────────────────┐
│              Request Queue                │
│  ┌─────┬─────┬─────┬─────┬─────┬─────┐   │
│  │ r1  │ r2  │ r3  │ r4  │ r5  │ r6  │   │
│  └─────┴─────┴─────┴─────┴─────┴─────┘   │
│            pendingRequests               │
└──────────────────────────────────────────┘
```

---

## Pattern 13: Idempotent Receiver

Handle duplicate requests safely.

**Implementation**:

```java
class IdempotentReceiver {
    private final Map<RequestId, Response> processedRequests = new ConcurrentHashMap<>();

    public Response handleRequest(Request request) {
        // Check if already processed
        if (processedRequests.containsKey(request.getId())) {
            return processedRequests.get(request.getId());
        }

        // Process request
        Response response = processRequest(request);

        // Cache response
        processedRequests.put(request.getId(), response);

        return response;
    }
}
```

---

## Pattern 14: Follower Read

Serve reads from followers to reduce leader load.

**Consistency Levels**:

- **Strong**: Read from leader only
- **Eventual**: Read from any follower
- **Read-your-writes**: Read from leader or followers caught up

---

## Pattern 15: Versioned Value

Store multiple versions per key.

```text
Key: "user:123"
┌─────────────────────────────────────┐
│ Version 1: {"name": "Alice"}        │
│ Version 2: {"name": "Alice Smith"}  │
│ Version 3: {"name": "Alice Jones"}  │
└─────────────────────────────────────┘
```

**Use Cases**:

- MVCC (Multi-Version Concurrency Control)
- Snapshot isolation
- Time-travel queries

---

## Pattern 16: Version Vector

Track causality across replicas.

```text
Replica A: [A:3, B:2, C:1]
Replica B: [A:2, B:4, C:1]
Replica C: [A:2, B:2, C:3]
```

**Comparison**:

- A dominates B if all A[i] >= B[i] and at least one A[i] > B[i]
- Concurrent if neither dominates
