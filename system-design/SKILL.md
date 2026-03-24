---
name: system-design
description: >-
  Large-scale system design patterns including database architecture, caching,
  CDN, stateless design, message queues, consistent hashing, and rate limiting.
  Covers CAP theorem, eventual consistency, sharding strategies, replication factor,
  read replica configuration, and system stability patterns (circuit breaker,
  bulkhead, backpressure).
  Includes distributed systems patterns: data replication, partitioning, consensus,
  distributed time (Lamport clock, hybrid clock), cluster management (lease, gossip,
  state watch), and network communication patterns.
  Use when designing scalable system architectures, evaluating consistency vs
  availability trade-offs, planning data partitioning and replication strategies,
  or implementing distributed systems patterns.
license: MIT
metadata:
  author: iceflower
  version: "2.0"
  last-reviewed: "2026-03"
---

# System Design Patterns

Large-scale system design principles and distributed systems patterns. Use when designing scalable architectures, preparing for system design interviews, evaluating system architecture, or implementing distributed systems.

> **Note**: This document synthesizes system design concepts from various sources including industry best practices, technical blogs, community knowledge, and "Patterns of Distributed Systems" by Unmesh Joshi.

## Design Discussion Framework

### General Approach

When approaching a system design problem:

1. **Understand Requirements**
   - Clarify functional requirements
   - Define scope and constraints
   - Identify non-functional requirements (scale, latency)

2. **Create High-Level Design**
   - Sketch core components
   - Show data flow between components
   - Discuss key decisions

3. **Detail Components**
   - Deep dive on critical components
   - Discuss trade-offs
   - Handle edge cases

4. **Review and Improve**
   - Identify bottlenecks
   - Suggest optimizations
   - Consider failure scenarios

---

## 1. Scalability Fundamentals

### Vertical vs Horizontal Scaling

| Aspect     | Vertical (Scale Up)   | Horizontal (Scale Out)  |
| ---------- | --------------------- | ----------------------- |
| Approach   | Bigger server         | More servers            |
| Limit      | Hardware max          | Theoretically unlimited |
| Cost       | Expensive at high end | Linear growth           |
| Complexity | Simple                | Requires load balancing |
| Failure    | Single point          | Graceful degradation    |

### Load Balancer

Distribute traffic across servers.

```text
         ┌──────────────┐
         │Load Balancer │
         │  (Public IP) │
         └──────┬───────┘
          ┌─────┼─────┐
          ▼     ▼     ▼
      ┌─────┐ ┌─────┐ ┌─────┐
      │ Svr1│ │ Svr2│ │ Svr3│
      └─────┘ └─────┘ └─────┘
```

**Algorithms**:

- Round-robin
- Weighted round-robin
- Least connections
- IP hash
- Health-check based

**Layer Selection**:

- Layer 4 (Transport): TCP/UDP routing
- Layer 7 (Application): HTTP path/header routing

---

## 2. Database Architecture

### RDBMS vs NoSQL

| Feature  | RDBMS           | NoSQL                     |
| -------- | --------------- | ------------------------- |
| Schema   | Fixed           | Flexible                  |
| Scaling  | Vertical        | Horizontal                |
| ACID     | Full            | Varies                    |
| Joins    | Native          | Limited                   |
| Use Case | Structured data | Unstructured, high volume |

> See [references/scalability-and-data.md](references/scalability-and-data.md) for detailed replication, sharding, caching, CDN, stateless architecture, data center, consistent hashing, rate limiting, key-value store, and ID generation patterns.

---

## 3. Caching Strategies

### Cache Eviction Policies

| Policy | Description           | Use Case             |
| ------ | --------------------- | -------------------- |
| LRU    | Least Recently Used   | General purpose      |
| LFU    | Least Frequently Used | Popular items matter |
| FIFO   | First In First Out    | Simple needs         |
| TTL    | Time To Live          | Freshness matters    |

### Cache Considerations

- **Consistency**: Cache may be stale
- **TTL**: Balance freshness vs load
- **Penetration**: Handle missing keys
- **Avalanche**: Stagger expirations
- **Breakdown**: Lock hot keys

---

## 4. Message Queue

Decouple components with async messaging.

```text
Producer                 Queue                   Consumer
   │                      │                        │
   │─── Message ─────────▶│                        │
   │                      │─── Message ───────────▶│
   │                      │                        │
   │                      │─── Message ───────────▶│
   │─── Message ─────────▶│                        │
```

### Message Queue Benefits

- Decoupling: Producer doesn't need consumer details
- Buffering: Handle traffic spikes
- Scalability: Add more consumers
- Reliability: Persistent messages

### Use Cases

- Async processing
- Background jobs
- Event notification
- Log aggregation

---

## 5. Distributed Systems Core Challenges

| Challenge       | Description                            |
| --------------- | -------------------------------------- |
| Network Latency | Communication between nodes takes time |
| Partial Failure | Some nodes fail while others continue  |
| Clock Drift     | No synchronized clock across nodes     |
| Consistency     | Data may differ across replicas        |
| Concurrency     | Multiple operations on same data       |

---

## 6. Distributed Systems Patterns Overview

30 patterns organized in 5 categories. See referenced files for detailed descriptions and code examples.

### Replication Patterns (16 patterns)

> See [references/replication-patterns.md](references/replication-patterns.md) for full details.

| #  | Pattern              | Purpose                                   |
| -- | -------------------- | ----------------------------------------- |
| 1  | Write-Ahead Log      | Persist operations before applying        |
| 2  | Segmented Log        | Split log into manageable segments        |
| 3  | Low-Water Mark       | Track minimum log index for recovery      |
| 4  | Leader-Follower      | Single coordinator manages cluster        |
| 5  | Heartbeat            | Detect node failures                      |
| 6  | Quorum               | Require majority agreement                |
| 7  | Generation Clock     | Track leadership epochs                   |
| 8  | High-Water Mark      | Track max replicated log index            |
| 9  | Paxos                | Distributed consensus                     |
| 10 | Replicated Log       | Consensus-based log replication (Raft)    |
| 11 | Single-Socket Channel| Sequential request processing             |
| 12 | Request Queue        | Concurrent requests with ordering         |
| 13 | Idempotent Receiver  | Handle duplicate requests safely          |
| 14 | Follower Read        | Serve reads from followers                |
| 15 | Versioned Value      | Store multiple versions per key           |
| 16 | Version Vector       | Track causality across replicas           |

### Partition Patterns (3 patterns)

> See [references/partition-patterns.md](references/partition-patterns.md) for full details.

| #  | Pattern            | Purpose                              |
| -- | ------------------ | ------------------------------------ |
| 17 | Fixed Partitions   | Pre-create fixed number of partitions|
| 18 | Key-Range Partition| Partition by key ranges              |
| 19 | Two-Phase Commit   | Atomic commit across partitions      |

### Time Patterns (3 patterns)

> See [references/time-and-cluster.md](references/time-and-cluster.md) for full details.

| #  | Pattern          | Purpose                            |
| -- | ---------------- | ---------------------------------- |
| 20 | Lamport Clock    | Logical timestamps for ordering    |
| 21 | Hybrid Clock     | Combine physical and logical clocks|
| 22 | Clock Bound Wait | Handle clock uncertainty           |

### Cluster Management Patterns (5 patterns)

> See [references/time-and-cluster.md](references/time-and-cluster.md) for full details.

| #  | Pattern              | Purpose                               |
| -- | -------------------- | ------------------------------------- |
| 23 | Consistency Core     | Centralized metadata management       |
| 24 | Lease                | Time-based exclusive access           |
| 25 | State Watch          | React to state changes in cluster     |
| 26 | Gossip Dissemination | Spread info via random peer comm      |
| 27 | Emergent Leader      | Decentralized leader election         |

### Network Communication Patterns (3 patterns)

> See [references/network-patterns.md](references/network-patterns.md) for full details.

| #  | Pattern           | Purpose                                  |
| -- | ----------------- | ---------------------------------------- |
| 28 | Single-Socket Ch. | Maintain single connection for ordering  |
| 29 | Batched Requests  | Send multiple requests in single message |
| 30 | Request Pipeline  | Send requests without waiting responses  |

---

## 7. Latency Reference Numbers

> Source: Based on "Numbers Every Programmer Should Know" by Jeff Dean (Google). Actual values vary by hardware.

| Operation                  | Approximate Latency |
| -------------------------- | ------------------- |
| L1 cache reference         | ~1 ns               |
| L2 cache reference         | ~4 ns               |
| Mutex lock/unlock          | ~17 ns              |
| Main memory reference      | ~100 ns             |
| SSD random read            | ~16 us              |
| Read 1MB from SSD          | ~50 us              |
| Network round-trip same DC | ~500 us             |
| Disk seek                  | ~3 ms               |

---

## 8. Capacity Estimation Example

```text
Example calculation (adjust numbers for your use case):

Daily Active Users: 500K
Requests per user: 80/day
QPS = 500K * 80 / 86400 ≈ 460 QPS
Peak QPS = QPS * 2-3 ≈ 1,400 QPS

Storage:
Per user: 500KB/day
Daily: 500K * 500KB = 250GB
With replication (3x): 750GB/day
```

---

## 9. System Design Patterns Summary

| Problem                      | Pattern                               |
| ---------------------------- | ------------------------------------- |
| Single server bottleneck     | Load balancer + horizontal scaling    |
| Database overload            | Caching, read replicas                |
| Large dataset                | Sharding, partitioning                |
| Geographic latency           | CDN, multi-DC                         |
| Session management           | External session store                |
| Service coupling             | Message queue                         |
| Hot partitions               | Consistent hashing with virtual nodes |
| Traffic spikes               | Rate limiting, circuit breaker        |
| Data persistence             | WAL, Segmented Log                    |
| High availability            | Leader-Follower, Quorum               |
| Failure detection            | Heartbeat, Generation Clock           |
| Consistency                  | Paxos, Raft (Replicated Log)          |
| Read scalability             | Follower Read, Versioned Value        |
| Data partitioning            | Fixed Partitions, Key-Range           |
| Cross-partition transactions | 2PC                                   |
| Time ordering                | Lamport Clock, Hybrid Clock           |
| Cluster coordination         | Consistency Core, Lease, Gossip       |

---

## 10. Design Discussion Checklist

### Clarify Requirements

- [ ] Functional requirements
- [ ] Non-functional requirements (scale, latency)
- [ ] Out of scope items

### Define Constraints

- [ ] Traffic estimates (QPS)
- [ ] Storage estimates
- [ ] Bandwidth estimates

### Design Components

- [ ] Client → API layer
- [ ] API layer → Service layer
- [ ] Service layer → Data layer
- [ ] Cache strategy
- [ ] Async processing (if needed)

### Deep Dive Topics

- [ ] Database schema
- [ ] API design
- [ ] Scalability approach
- [ ] Failure handling
- [ ] Monitoring/logging

---

## Related Skills

- **api-design**: REST API design principles
- **messaging**: Message broker patterns (Kafka, RabbitMQ)
- **caching**: Cache implementation patterns, distributed cache patterns
- **spring-framework**: Reactive distributed clients (WebFlux)
- **k8s-workflow**: Container orchestration patterns

---

## References

- Designing Data-Intensive Applications by Martin Kleppmann
- Patterns of Distributed Systems by Unmesh Joshi
- Building Secure and Reliable Systems by Google
- Raft paper by Diego Ongaro and John Ousterhout
- Various technical blogs, distributed systems literature, and community resources
- For system stability patterns, see [references/stability-patterns.md](references/stability-patterns.md)
