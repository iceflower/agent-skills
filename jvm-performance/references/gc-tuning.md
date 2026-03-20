# GC Tuning and Memory Analysis

## Garbage Collection Algorithms

### Mark-and-Sweep

**Phases**:

1. **Mark**: Identify reachable objects from GC roots
2. **Sweep**: Reclaim unmarked objects

**Issues**:

- Fragmentation
- Long pause times
- No compaction

### Generational Collection

```text
Young GC (Minor GC):
1. Eden full -> copy live objects to Survivor
2. Swap Survivor roles
3. Objects with age > threshold -> Old

Old GC (Major/Full GC):
1. Mark all reachable objects
2. Compact (optional)
```

### Stop-the-World (STW) Pauses

All application threads stopped during GC phases.

**Causes**:

- Safepoint required for heap modification
- Ensures consistent object graph

## JVM Tuning Parameters

### Memory Settings

```bash
# Heap size
-Xms4g                          # Initial heap
-Xmx4g                          # Max heap (same as Xms recommended)

# Young generation
-Xmn1g                          # Young gen size
-XX:NewRatio=2                  # Old:Young ratio

# Survivor spaces
-XX:SurvivorRatio=8             # Eden:Survivor ratio

# Metaspace
-XX:MetaspaceSize=256m
-XX:MaxMetaspaceSize=512m
```

### GC Tuning

```bash
# G1 specific
-XX:MaxGCPauseMillis=200        # Target pause time
-XX:G1HeapRegionSize=16m        # Region size
-XX:InitiatingHeapOccupancyPercent=45  # Trigger concurrent cycle

# ZGC specific
-XX:ZAllocationSpikeTolerance=2
-XX:ZCollectionInterval=0       # Only when needed

# Common
-XX:+ExplicitGCInvokesConcurrent
-XX:+DisableExplicitGC          # Block System.gc()
```

### Thread Settings

```bash
-XX:ParallelGCThreads=8         # Parallel GC threads
-XX:ConcGCThreads=2             # Concurrent GC threads
```

## Memory Analysis

### Heap Dump Analysis

```bash
# Trigger heap dump
jcmd <pid> GC.heap_dump /tmp/heap.hprof

# Or on OOM
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/tmp/heap.hprof
```

**Tools**:

- Eclipse MAT
- VisualVM
- IntelliJ Profiler

### Memory Leak Patterns

| Pattern               | Symptoms             | Cause                                |
|-----------------------|----------------------|--------------------------------------|
| Static collections    | Growing Old gen      | Unbounded static maps/lists          |
| Unclosed resources    | Native memory growth | Missing close() calls                |
| Listener accumulation | Slow memory growth   | Missing deregistration               |
| ThreadLocal leaks     | Memory after request | Thread pool threads retaining values |
| Class loader leaks    | Metaspace growth     | Dynamic class creation               |

### Allocation Hotspots

Find objects created frequently:

```bash
# JFR allocation profiling
jcmd <pid> JFR.start settings=profile

# async-profiler
./profiler.sh -e alloc -d 60 <pid>
```

## JIT Compilation

### HotSpot Compilation Tiers

```text
Interpreter -> C1 (Client) -> C2 (Server)
                  |
            Profile-guided optimization
```

### JIT Flags

```bash
# Print JIT compilation
-XX:+PrintCompilation

# Disable tiered compilation (use C2 only)
-XX:-TieredCompilation

# JIT log
-XX:LogFile=jit.log
```

### Inlining

Key optimization for performance.

```bash
# Control inlining
-XX:MaxInlineSize=35        # Max bytecode size for inline
-XX:FreqInlineSize=325      # Max for hot methods
```
