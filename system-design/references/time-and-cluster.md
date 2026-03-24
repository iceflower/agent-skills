# Distributed Time and Cluster Management Patterns

8 patterns for distributed time ordering and cluster management.

---

## Part 1: Distributed Time Patterns

### Pattern 20: Lamport Clock

Logical timestamps for ordering events.

```text
Each process maintains counter:
- On send: counter++, include in message
- On receive: counter = max(counter, received) + 1
- On local event: counter++
```

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
```

---

### Pattern 21: Hybrid Clock

Combine physical and logical clocks.

```text
Hybrid Timestamp = (physicalTime, logicalCount)

Uses physical time when possible,
logical count for ordering within same physical time.
```

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
```

---

### Pattern 22: Clock Bound Wait

Handle clock uncertainty in distributed systems.

**Problem**: Clocks not perfectly synchronized.

**Solution**: Add uncertainty margin when making time-based decisions.

```text
if (eventTime + clockUncertainty < deadline) {
    // Safe to proceed
}
```

---

## Part 2: Cluster Management Patterns

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
```

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
```

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
```

---

### Pattern 26: Gossip Dissemination

Spread information through random peer communication.

```text
Round 1: Node A → Node B
Round 2: Node A → Node C, Node B → Node D
Round 3: Node A → Node E, Node B → Node F, ...
```

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
```

---

### Pattern 27: Emergent Leader

Decentralized leader election.

**Algorithm**:

1. Each node generates random delay
2. First node to wake up becomes leader candidate
3. Announces leadership
4. Other nodes accept if no conflict
