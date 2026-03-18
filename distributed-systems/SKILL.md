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

> **See [references/replication-patterns.md](references/replication-patterns.md) for detailed patterns including:**
> - Write-Ahead Log (WAL), Segmented Log, Low-Water Mark
> - Leader-Follower, Heartbeat, Quorum, Generation Clock
> - High-Water Mark, Paxos, Replicated Log
> - Single-Socket Channel, Request Queue, Idempotent Receiver
> - Follower Read, Versioned Value, Version Vector

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
