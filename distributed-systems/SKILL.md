---
name: distributed-systems
description: >-
  Distributed systems design patterns including data replication, partitioning,
  distributed time, cluster management, and network communication.
  Use when designing or implementing distributed systems.
---

# Distributed Systems Patterns

30 patterns for building reliable distributed systems. Use when designing or implementing distributed databases, messaging systems, or microservices architectures.

> **Note**: Pattern names and concepts in this document are inspired by "Patterns of Distributed Systems" by Unmesh Joshi, with implementations and explanations written independently.

## Core Challenges

| Challenge         | Description                               |
|-------------------|-------------------------------------------|
| ----------------- | ----------------------------------------- |
| Network Latency   | Communication between nodes takes time    |
| Partial Failure   | Some nodes fail while others continue     |
| Clock Drift       | No synchronized clock across nodes        |
| Consistency       | Data may differ across replicas           |
| Concurrency       | Multiple operations on same data          |

---

## Part 1: Data Replication Patterns

### Pattern 1: Write-Ahead Log (WAL)

Persist operations before applying them.

```text
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│    WAL      │────▶│   State     │
│   Request   │     │  (append)   │     │  Machine    │
└─────────────┘     └─────────────┘     └─────────────┘
```text

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
```text

---

### Pattern 2: Segmented Log

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
```text

---

### Pattern 3: Low-Water Mark

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
```text

---

### Pattern 4: Leader-Follower

Single coordinator manages state machine cluster.

```text
        ┌──────────┐
        │  Leader  │
        └────┬─────┘
        ┌────┴────┐
   ┌────▼───┐ ┌───▼────┐
   │Follower│ │Follower│
   └────────┘ └────────┘
```text

**Leader Responsibilities**:

- Process all writes
- Replicate to followers
- Respond to clients

**Follower Responsibilities**:

- Accept replication from leader
- Respond to read requests (eventually consistent)

---

### Pattern 5: Heartbeat

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
```text

---

### Pattern 6: Quorum

Require majority agreement for decisions.

**Formula**: Quorum = (N / 2) + 1

**Why?** Ensures only one decision can be made.

| Cluster Size   | Quorum   | Tolerates Failures  |
|----------------|----------|---------------------|
| -------------- | -------- | ------------------- |
| 3              | 2        | 1                   |
| 5              | 3        | 2                   |
| 7              | 4        | 3                   |

**Elastic Quorum**: Adjust quorum during partial failures.

---

### Pattern 7: Generation Clock

Track leadership epochs to detect stale leaders.

```text
Generation = (term, nodeId)

Higher generation always wins.
Same generation → compare nodeId
```text

**Use Cases**:

- Leader election
- Detecting split-brain
- Preventing stale updates

---

### Pattern 8: High-Water Mark

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
```text

---

### Pattern 9: Paxos

Distributed consensus algorithm.

**Roles**:

- **Proposer**: Proposes values
- **Acceptor**: Votes on proposals
- **Learner**: Lears decided values

**Phases**:

1. **Prepare**: Proposer sends prepare(n) with unique number n
2. **Promise**: Acceptors promise not to accept < n
3. **Accept**: Proposer sends accept(n, value)
4. **Accepted**: Acceptors accept if n is highest seen

---

### Pattern 10: Replicated Log

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
```text

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

### Pattern 11: Single-Socket Channel

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
```text

---

### Pattern 12: Request Queue

Handle concurrent requests with ordering.

```text
┌──────────────────────────────────────────┐
│              Request Queue                │
│  ┌─────┬─────┬─────┬─────┬─────┬─────┐   │
│  │ r1  │ r2  │ r3  │ r4  │ r5  │ r6  │   │
│  └─────┴─────┴─────┴─────┴─────┴─────┘   │
│            pendingRequests               │
└──────────────────────────────────────────┘
```text

---

### Pattern 13: Idempotent Receiver

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
```text

---

### Pattern 14: Follower Read

Serve reads from followers to reduce leader load.

**Consistency Levels**:

- **Strong**: Read from leader only
- **Eventual**: Read from any follower
- **Read-your-writes**: Read from leader or followers caught up

---

### Pattern 15: Versioned Value

Store multiple versions per key.

```text
Key: "user:123"
┌─────────────────────────────────────┐
│ Version 1: {"name": "Alice"}        │
│ Version 2: {"name": "Alice Smith"}  │
│ Version 3: {"name": "Alice Jones"}  │
└─────────────────────────────────────┘
```text

**Use Cases**:

- MVCC (Multi-Version Concurrency Control)
- Snapshot isolation
- Time-travel queries

---

### Pattern 16: Version Vector

Track causality across replicas.

```text
Replica A: [A:3, B:2, C:1]
Replica B: [A:2, B:4, C:1]
Replica C: [A:2, B:2, C:3]
```text

**Comparison**:

- A dominates B if all A[i] >= B[i] and at least one A[i] > B[i]
- Concurrent if neither dominates

---

## Part 2: Data Partition Patterns

### Pattern 17: Fixed Partitions

Pre-create fixed number of partitions.

```text
Partitions: 0, 1, 2, 3, ..., 1023

Key → Partition = hash(key) % 1024
```text

**Advantages**:

- Simple mapping
- No partition splitting
- Predictable performance

**Mapping to Nodes**:

```java
class PartitionAssignment {
    private final List<Node> nodes;
    private final int partitionsPerNode = 100;
    
    public Node getNodeForPartition(int partitionId) {
        int nodeIndex = partitionId % nodes.size();
        return nodes.get(nodeIndex);
    }
}
```text

---

### Pattern 18: Key-Range Partition

Partition by key ranges.

```text
Partition 1: [a, f]
Partition 2: [g, m]
Partition 3: [n, s]
Partition 4: [t, z]
```text

**Advantages**:

- Range queries efficient
- Ordered iteration possible

**Disadvantages**:

- Hot spots for sequential keys
- Rebalancing complex

---

### Pattern 19: Two-Phase Commit (2PC)

Atomic commit across multiple partitions.

**Phase 1 - Prepare**:

1. Coordinator sends PREPARE to all participants
2. Participants lock resources, vote YES/NO
3. Wait for all votes

**Phase 2 - Commit/Abort**:

- If all YES: Send COMMIT
- If any NO: Send ABORT

```text
Coordinator          Participant A        Participant B
    │                     │                     │
    │───PREPARE──────────▶│                     │
    │                     │───PREPARE──────────▶│
    │◀──YES───────────────│                     │
    │                     │◀──YES───────────────│
    │───COMMIT───────────▶│                     │
    │                     │───COMMIT───────────▶│
    │◀──ACK───────────────│                     │
    │                     │◀──ACK───────────────│
```text

**Issues**:

- Blocking if coordinator fails
- Locks held during prepare phase

---

## Part 3: Distributed Time Patterns

### Pattern 20: Lamport Clock

Logical timestamps for ordering events.

```text
Each process maintains counter:
- On send: counter++, include in message
- On receive: counter = max(counter, received) + 1
- On local event: counter++
```text

```java
class LamportClock {
    private long time = 0;
    
    public synchronized long tick() {
        return ++time;
    }
    
    public synchronized long receive(long receivedTime) {
        time = Math.max(time, receivedTime) + 1;
        return time;
    }
}
```text

---

### Pattern 21: Hybrid Clock

Combine physical and logical clocks.

```text
Hybrid Timestamp = (physicalTime, logicalCount)

Uses physical time when possible,
logical count for ordering within same physical time.
```text

```java
class HybridClock {
    private long lastPhysicalTime = 0;
    private int logicalCount = 0;
    
    public synchronized HybridTimestamp now() {
        long physicalTime = System.currentTimeMillis();
        
        if (physicalTime > lastPhysicalTime) {
            lastPhysicalTime = physicalTime;
            logicalCount = 0;
        } else {
            logicalCount++;
        }
        
        return new HybridTimestamp(lastPhysicalTime, logicalCount);
    }
}
```text

---

### Pattern 22: Clock Bound Wait

Handle clock uncertainty in distributed systems.

**Problem**: Clocks not perfectly synchronized.

**Solution**: Add uncertainty margin when making time-based decisions.

```text
if (eventTime + clockUncertainty < deadline) {
    // Safe to proceed
}
```text

---

## Part 4: Cluster Management Patterns

### Pattern 23: Consistency Core

Centralized metadata management.

```text
┌──────────────────────────────────────────┐
│            Consistency Core               │
│  (etcd, ZooKeeper, Consul)               │
│                                           │
│  - Cluster membership                     │
│  - Leader election                        │
│  - Configuration                          │
└──────────────────────────────────────────┘
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
 Data      Data      Data
 Node 1    Node 2    Node 3
```text

---

### Pattern 24: Lease

Time-based exclusive access.

```java
class LeaseManager {
    private final Map<String, Lease> leases = new ConcurrentHashMap<>();
    
    public Lease acquireLease(String resourceId, Duration duration) {
        Lease lease = new Lease(resourceId, Instant.now().plus(duration));
        Lease existing = leases.putIfAbsent(resourceId, lease);
        
        if (existing != null && !existing.isExpired()) {
            throw new LeaseHeldException(resourceId);
        }
        
        return lease;
    }
    
    public void renewLease(Lease lease, Duration duration) {
        if (lease.isExpired()) {
            throw new LeaseExpiredException();
        }
        lease.extend(duration);
    }
}
```text

---

### Pattern 25: State Watch

React to state changes in cluster.

```java
interface StateWatcher {
    void onNodeAdded(Node node);
    void onNodeRemoved(Node node);
    void onLeaderChanged(Node newLeader);
}

class ClusterStateMonitor {
    private final List<StateWatcher> watchers = new ArrayList<>();
    
    public void registerWatcher(StateWatcher watcher) {
        watchers.add(watcher);
    }
    
    private void notifyNodeAdded(Node node) {
        watchers.forEach(w -> w.onNodeAdded(node));
    }
}
```text

---

### Pattern 26: Gossip Dissemination

Spread information through random peer communication.

```text
Round 1: Node A → Node B
Round 2: Node A → Node C, Node B → Node D
Round 3: Node A → Node E, Node B → Node F, ...
```text

**Properties**:

- O(log N) rounds to reach all nodes
- No single point of failure
- Eventually consistent

```java
class GossipProtocol {
    private final Set<Node> clusterNodes;
    private final Map<String, byte[]> state = new ConcurrentHashMap<>();
    private final Random random = new Random();
    
    public void gossip() {
        // Pick random peer
        Node peer = selectRandomPeer();
        
        // Send state digest
        Map<String, Long> digest = computeDigest();
        peer.sendGossip(digest);
    }
    
    public void receiveGossip(Map<String, Long> peerDigest) {
        // Compare versions, request missing
        for (Entry<String, Long> entry : peerDigest.entrySet()) {
            if (getVersion(entry.getKey()) < entry.getValue()) {
                requestUpdate(entry.getKey());
            }
        }
    }
}
```text

---

### Pattern 27: Emergent Leader

Decentralized leader election.

**Algorithm**:

1. Each node generates random delay
2. First node to wake up becomes leader candidate
3. Announces leadership
4. Other nodes accept if no conflict

---

## Part 5: Network Communication Patterns

### Pattern 28: Single-Socket Channel

Maintain single connection for ordering.

**Benefits**:

- Preserves request order
- Simple flow control
- No reordering logic needed

---

### Pattern 29: Batched Requests

Send multiple requests in single message.

```java
class BatchedRequest {
    private final List<Request> requests = new ArrayList<>();
    
    public void add(Request request) {
        requests.add(request);
        if (requests.size() >= BATCH_SIZE) {
            flush();
        }
    }
    
    public List<Response> flush() {
        if (requests.isEmpty()) return Collections.emptyList();
        
        List<Response> responses = sendBatch(requests);
        requests.clear();
        return responses;
    }
}
```text

**Trade-offs**:

- Lower network overhead
- Higher throughput
- Higher latency per request

---

### Pattern 30: Request Pipeline

Send multiple requests without waiting for responses.

```text
Client                                    Server
   │───────────Request 1───────────────────▶│
   │───────────Request 2───────────────────▶│
   │◀──────────Response 1──────────────────│
   │───────────Request 3───────────────────▶│
   │◀──────────Response 2──────────────────│
   │◀──────────Response 3──────────────────│
```text

**Pipeline Depth**: Max concurrent in-flight requests.

---

## Pattern Selection Guide

| Problem                      | Recommended Patterns            |
|------------------------------|---------------------------------|
| ---------                    | ---------------------           |
| Data persistence             | WAL, Segmented Log              |
| High availability            | Leader-Follower, Quorum         |
| Failure detection            | Heartbeat, Generation Clock     |
| Consistency                  | Paxos, Raft (Replicated Log)    |
| Read scalability             | Follower Read, Versioned Value  |
| Data partitioning            | Fixed Partitions, Key-Range     |
| Cross-partition transactions | 2PC                             |
| Time ordering                | Lamport Clock, Hybrid Clock     |
| Cluster coordination         | Consistency Core, Lease, Gossip |

---

## Related Skills

- **messaging**: Message broker patterns (Kafka, RabbitMQ)
- **spring-webflux**: Reactive distributed clients
- **caching**: Distributed cache patterns
- **k8s-workflow**: Container orchestration patterns

---

## References

- Patterns of Distributed Systems by Unmesh Joshi (pattern names and concepts)
- Designing Data-Intensive Applications by Martin Kleppmann
- Raft paper by Diego Ongaro and John Ousterhout
- Various distributed systems literature and documentation
