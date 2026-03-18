# Garbage Collectors

## Serial GC

Single-threaded collector.

```bash
-XX:+UseSerialGC
```

**Characteristics**:

- Simple, low memory overhead
- Long STW pauses
- Suitable for small heaps (< 100MB)

## Parallel GC (Throughput Collector)

Multi-threaded young generation collection.

```bash
-XX:+UseParallelGC
-XX:ParallelGCThreads=N
```

**Characteristics**:

- High throughput
- Longer pauses than Serial
- Default in Java 8

## G1 GC (Garbage First)

Region-based, incremental collector.

```bash
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200
-XX:G1HeapRegionSize=4m
```

**Heap Layout**:

```text
┌────┬────┬────┬────┬────┬────┬────┬────┐
│ E  │ E  │ S  │ O  │ O  │ H  │ E  │ O  │
└────┴────┴────┴────┴────┴────┴────┴────┘
E = Eden, S = Survivor, O = Old, H = Humongous
```

**Phases**:

1. Young collection (STW)
2. Mixed collection (Young + some Old regions)
3. Concurrent marking (identifies garbage)
4. Cleanup

**Advantages**:

- Predictable pause times
- No Full GC in normal operation
- Handles large heaps well

## ZGC (Z Garbage Collector)

Low-latency, scalable collector (Java 15+).

```bash
-XX:+UseZGC
-XX:ZCollectionInterval=N  (ms)
```

**Characteristics**:

- Pause times < 10ms (typically < 1ms)
- Handles multi-TB heaps
- Concurrent marking and relocation

**How It Works**:

1. Marking without STW (colored pointers)
2. Concurrent relocation
3. Load barriers for reference updates

## Shenandoah

Another low-latency collector.

```bash
-XX:+UseShenandoahGC
```

**Characteristics**:

- Pause times < 10ms
- Concurrent compaction
- Brooks pointers for forwarding