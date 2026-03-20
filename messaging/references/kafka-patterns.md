# Kafka Patterns

Practical patterns for Apache Kafka topic design, partitioning, consumer groups, and delivery guarantees.

## Overview

Apache Kafka is a distributed event streaming platform. Effective use requires careful design of topics, partitions, and consumer groups to balance throughput, ordering, and reliability.

## Topic Design

### Naming Conventions

Use a consistent, hierarchical naming scheme:

```text
<domain>.<entity>.<event-type>

Examples:
  order.order.created
  order.order.confirmed
  payment.transaction.completed
  inventory.stock.updated
```

### Topic Granularity

| Strategy              | When to Use                           | Example                          |
| --------------------- | ------------------------------------- | -------------------------------- |
| Event-per-topic       | Few event types, simple routing       | `order.created`, `order.shipped` |
| Entity-per-topic      | Many event types per entity           | `order.events` (all order events)|
| Domain-per-topic      | High-throughput, simpler ops          | `order.domain-events`            |

**Recommendation**: Start with entity-per-topic. Split later if needed.

### Topic Configuration

```properties
# Production defaults
num.partitions=12
replication.factor=3
min.insync.replicas=2

# Retention
retention.ms=604800000          # 7 days
retention.bytes=-1              # unlimited

# Performance
compression.type=lz4
max.message.bytes=1048576       # 1 MB
```

## Partitioning Strategies

Partitions determine parallelism and ordering guarantees.

### Key-Based Partitioning

Messages with the same key go to the same partition, guaranteeing order per key.

```java
// Order events keyed by orderId: all events for one order are ordered
producer.send(new ProducerRecord<>(
    "order.events",
    order.getId().toString(),   // partition key
    orderEvent.serialize()
));
```

### Partition Count Guidelines

| Factor                  | Guidance                                        |
| ----------------------- | ----------------------------------------------- |
| Consumer parallelism    | partitions >= max consumer instances             |
| Throughput target       | ~10 MB/s per partition (typical)                 |
| Key cardinality         | High cardinality keys distribute evenly          |
| Ordering needs          | More partitions = less per-partition ordering     |

**Warning**: Increasing partitions later changes key-to-partition mapping. Plan ahead.

### Handling Hot Partitions

When a few keys receive disproportionate traffic:

```java
// Add random suffix to spread hot keys across partitions
String partitionKey = isHotKey(orderId)
    ? orderId + "-" + ThreadLocalRandom.current().nextInt(10)
    : orderId;

// Trade-off: lose strict ordering for hot keys
```

## Consumer Groups

### Consumer Group Mechanics

```text
Topic: order.events (6 partitions)

Consumer Group: order-processor
  ┌────────────┐  ┌────────────┐  ┌────────────┐
  │ Consumer 1 │  │ Consumer 2 │  │ Consumer 3 │
  │ P0, P1     │  │ P2, P3     │  │ P4, P5     │
  └────────────┘  └────────────┘  └────────────┘
```

**Rules**:

- Each partition is consumed by exactly one consumer in a group
- Adding consumers (up to partition count) increases parallelism
- Consumers beyond partition count sit idle

### Offset Management

```java
// Manual offset commit for at-least-once delivery
consumer.subscribe(List.of("order.events"));

while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));

    for (ConsumerRecord<String, String> record : records) {
        processRecord(record);  // Process first
    }

    consumer.commitSync();  // Commit after successful processing
}
```

### Rebalancing Strategies

| Strategy                  | Behavior                                  |
| ------------------------- | ----------------------------------------- |
| Eager (default)           | Revoke all, reassign all                  |
| Cooperative Sticky        | Incremental rebalance, minimal disruption |
| Static Group Membership   | Fixed assignment, no rebalance on restart |

```properties
# Cooperative rebalancing (recommended)
partition.assignment.strategy=org.apache.kafka.clients.consumer.CooperativeStickyAssignor

# Static membership (for stateful consumers)
group.instance.id=consumer-1
session.timeout.ms=300000
```

## Delivery Guarantees

### At-Most-Once

Process before commit. Messages may be lost on failure.

```java
consumer.commitSync();      // Commit first
processRecord(record);      // Then process (may lose on crash)
```

### At-Least-Once

Commit after process. Messages may be reprocessed on failure.

```java
processRecord(record);      // Process first
consumer.commitSync();      // Then commit (may reprocess on crash)
```

### Exactly-Once Semantics (EOS)

Use Kafka transactions for exactly-once between Kafka topics:

```java
producer.initTransactions();

try {
    producer.beginTransaction();

    // Produce output records
    producer.send(new ProducerRecord<>("output-topic", key, value));

    // Commit consumer offsets within the same transaction
    producer.sendOffsetsToTransaction(
        offsets,
        new ConsumerGroupMetadata(groupId)
    );

    producer.commitTransaction();
} catch (Exception e) {
    producer.abortTransaction();
}
```

**Producer config for EOS**:

```properties
enable.idempotence=true
transactional.id=order-processor-1
acks=all
```

**Important**: EOS only works for Kafka-to-Kafka flows. For external systems, use the outbox pattern or idempotent consumers.

## Error Handling

### Dead Letter Topic

Route unprocessable messages to a dead letter topic for investigation:

```java
public void consumeWithDLT(ConsumerRecord<String, String> record) {
    try {
        processRecord(record);
    } catch (DeserializationException e) {
        // Permanent failure: send to DLT
        producer.send(new ProducerRecord<>(
            "order.events.DLT",
            record.key(),
            record.value()
        ));
    } catch (TransientException e) {
        // Retryable: send to retry topic with delay
        producer.send(new ProducerRecord<>(
            "order.events.retry",
            record.key(),
            record.value()
        ));
    }
}
```

### Retry Topic Pattern

```text
order.events → (failure) → order.events.retry-1 (1 min delay)
                          → order.events.retry-2 (5 min delay)
                          → order.events.retry-3 (30 min delay)
                          → order.events.DLT (permanent failure)
```

## Monitoring Essentials

Key metrics to track:

| Metric                          | Alert Threshold              |
| ------------------------------- | ---------------------------- |
| Consumer lag                    | > 10000 messages             |
| Under-replicated partitions     | > 0                          |
| Request latency (p99)           | > 500ms                      |
| ISR shrink rate                 | Any occurrence               |
| Disk usage per broker           | > 80%                        |
