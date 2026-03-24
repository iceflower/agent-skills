# Data Partition Patterns

3 patterns for data partitioning in distributed systems.

---

## Pattern 17: Fixed Partitions

Pre-create fixed number of partitions.

```text
Partitions: 0, 1, 2, 3, ..., 1023

Key → Partition = hash(key) % 1024
```

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
```

---

## Pattern 18: Key-Range Partition

Partition by key ranges.

```text
Partition 1: [a, f]
Partition 2: [g, m]
Partition 3: [n, s]
Partition 4: [t, z]
```

**Advantages**:

- Range queries efficient
- Ordered iteration possible

**Disadvantages**:

- Hot spots for sequential keys
- Rebalancing complex

---

## Pattern 19: Two-Phase Commit (2PC)

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
```

**Issues**:

- Blocking if coordinator fails
- Locks held during prepare phase
