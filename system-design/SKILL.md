---
name: system-design
description: >-
  Large-scale system design patterns including database architecture, caching,
  CDN, stateless design, message queues, consistent hashing, and rate limiting.
  Covers CAP theorem, eventual consistency, sharding strategies, replication factor,
  read replica configuration, and system stability patterns (circuit breaker,
  bulkhead, backpressure).
  Use when designing scalable system architectures, evaluating consistency vs
  availability trade-offs, or planning data partitioning and replication strategies.
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

# System Design Interview Patterns

Large-scale system design principles and patterns. Use when designing scalable architectures, preparing for system design interviews, or evaluating system architecture.

> **Note**: This document synthesizes system design concepts from various sources including industry best practices, technical blogs, and community knowledge.

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
|------------|-----------------------|-------------------------|
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
|----------|-----------------|---------------------------|
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
|--------|-----------------------|----------------------|
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

## 7. Message Queue

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

## 8. System Design Components

### Latency Reference Numbers

> Source: Based on "Numbers Every Programmer Should Know" by Jeff Dean (Google). Actual values vary by hardware.

| Operation                 | Approximate Latency |
|---------------------------|---------------------|
| L1 cache reference        | ~1 ns               |
| L2 cache reference        | ~4 ns               |
| Mutex lock/unlock         | ~17 ns              |
| Main memory reference     | ~100 ns             |
| SSD random read           | ~16 μs              |
| Read 1MB from SSD         | ~50 μs              |
| Network round-trip same DC| ~500 μs             |
| Disk seek                 | ~3 ms               |

### Capacity Estimation Example

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

---

## 9. System Design Patterns Summary

| Problem                  | Pattern                               |
|--------------------------|---------------------------------------|
| Single server bottleneck | Load balancer + horizontal scaling    |
| Database overload        | Caching, read replicas                |
| Large dataset            | Sharding, partitioning                |
| Geographic latency       | CDN, multi-DC                         |
| Session management       | External session store                |
| Service coupling         | Message queue                         |
| Hot partitions           | Consistent hashing with virtual nodes |
| Traffic spikes           | Rate limiting, circuit breaker        |

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
- **distributed-systems**: Distributed patterns
- **messaging**: Message broker patterns
- **caching**: Cache implementation patterns

---

## References

- Designing Data-Intensive Applications by Martin Kleppmann
- Building Secure and Reliable Systems by Google
- Various technical blogs and community resources

## Additional References

- For system stability patterns, see [references/stability-patterns.md](references/stability-patterns.md)
