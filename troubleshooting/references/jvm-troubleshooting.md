# JVM Troubleshooting Guide

## 1. Heap Dump Analysis

### Capturing Heap Dumps

```bash
# Automatic heap dump on OutOfMemoryError (recommended: always enable in production)
java -XX:+HeapDumpOnOutOfMemoryError \
     -XX:HeapDumpPath=/tmp/heapdump.hprof \
     -jar app.jar

# Manual heap dump via jmap
jmap -dump:live,format=b,file=/tmp/heapdump.hprof <PID>

# Manual heap dump via jcmd (preferred over jmap)
jcmd <PID> GC.heap_dump /tmp/heapdump.hprof

# In Kubernetes — dump to a mounted volume
kubectl exec <pod> -n <ns> -- jcmd 1 GC.heap_dump /tmp/heapdump.hprof
kubectl cp <ns>/<pod>:/tmp/heapdump.hprof ./heapdump.hprof
```

### Analyzing Heap Dumps

| Tool | Use Case | Command/Notes |
| --- | --- | --- |
| Eclipse MAT | Leak suspects, dominator tree | Open `.hprof` file in MAT GUI |
| VisualVM | Quick overview, class histogram | Open `.hprof` or attach to live process |
| `jhat` (deprecated) | Basic web-based analysis | `jhat heapdump.hprof` (port 7000) |
| `jcmd GC.class_histogram` | Quick class-level memory breakdown | `jcmd <PID> GC.class_histogram` |

### Common Memory Leak Patterns

| Pattern | Symptom | Fix |
| --- | --- | --- |
| Unbounded cache | HashMap/ConcurrentHashMap grows indefinitely | Use bounded cache (Caffeine, Guava with `maximumSize`) |
| Listener/callback leak | Objects not GC'd due to registered listeners | Deregister listeners on cleanup |
| Static collection | Static `List`/`Map` accumulates entries | Use weak references or bounded structure |
| Classloader leak | PermGen/Metaspace growth on redeploy | Fix classloader cleanup, avoid static references to classloader |
| ThreadLocal leak | Thread pool threads retain ThreadLocal values | Call `ThreadLocal.remove()` in `finally` block |
| Stream/connection not closed | File handles, DB connections accumulate | Use try-with-resources |

---

## 2. Thread Dump Analysis

### Capturing Thread Dumps

```bash
# Via jcmd (recommended)
jcmd <PID> Thread.print > /tmp/threaddump.txt

# Via jstack
jstack <PID> > /tmp/threaddump.txt

# Via kill signal (dumps to stdout/stderr)
kill -3 <PID>

# Multiple dumps for trend analysis (3 dumps, 10 seconds apart)
for i in 1 2 3; do
  jcmd <PID> Thread.print > /tmp/threaddump_$i.txt
  sleep 10
done
```

### Thread States

| State | Meaning | Common Cause |
| --- | --- | --- |
| `RUNNABLE` | Executing or ready to execute | Normal; check if CPU-bound |
| `BLOCKED` | Waiting for monitor lock | Contention on synchronized block |
| `WAITING` | Waiting indefinitely | `Object.wait()`, `Thread.join()`, `LockSupport.park()` |
| `TIMED_WAITING` | Waiting with timeout | `Thread.sleep()`, `Object.wait(timeout)` |

### Common Thread Issues

| Issue | Symptoms | Diagnosis | Fix |
| --- | --- | --- | --- |
| Deadlock | Two+ threads BLOCKED on each other | `jcmd <PID> Thread.print` shows deadlock | Fix lock ordering, use `tryLock` with timeout |
| Thread pool exhaustion | All threads WAITING/BLOCKED, new requests rejected | Count threads in BLOCKED state | Increase pool size, fix blocking calls |
| Thread leak | Thread count grows continuously | Monitor thread count over time | Fix thread creation, use bounded pools |
| Lock contention | Many threads BLOCKED on same monitor | Multiple threads waiting on same lock | Reduce lock scope, use concurrent data structures |

### Analyzing Thread Dumps

```text
1. Look for deadlocks first
   → Search for "Found one Java-level deadlock" in output

2. Count thread states
   → Group by RUNNABLE/BLOCKED/WAITING/TIMED_WAITING

3. Find hot locks
   → Search for "waiting to lock" and identify the most contended monitors

4. Check thread pool saturation
   → Count active vs idle threads in executor pools

5. Identify slow operations
   → Look for threads stuck in I/O, DB calls, or external API calls
```

---

## 3. GC Analysis

### GC Log Configuration

```bash
# Java 11+ unified logging
java -Xlog:gc*:file=/var/log/gc.log:time,uptime,level,tags:filecount=5,filesize=100m \
     -jar app.jar

# Key GC flags
-XX:+UseG1GC                          # G1 collector (default in Java 11+)
-XX:MaxGCPauseMillis=200              # Target max pause time
-XX:G1HeapRegionSize=16m              # Region size (1MB-32MB, power of 2)
-XX:InitiatingHeapOccupancyPercent=45 # When to start concurrent marking
```

### GC Collectors Comparison

| Collector | Best For | Pause Behavior | Flag |
| --- | --- | --- | --- |
| G1GC | General purpose, balanced | Low-pause, concurrent | `-XX:+UseG1GC` |
| ZGC | Ultra-low latency (<1ms) | Sub-millisecond pauses | `-XX:+UseZGC` |
| Shenandoah | Low latency (OpenJDK) | Concurrent compaction | `-XX:+UseShenandoahGC` |
| Parallel GC | Throughput-oriented batch | Stop-the-world, high throughput | `-XX:+UseParallelGC` |
| Serial GC | Single-core, small heap | Stop-the-world, single-threaded | `-XX:+UseSerialGC` |

### GC Problem Indicators

| Indicator | Threshold | Action |
| --- | --- | --- |
| GC pause time | >500ms for G1 | Tune `MaxGCPauseMillis`, check heap size |
| GC frequency | >10 GCs/minute | Increase heap or reduce allocation rate |
| GC overhead | >5% of CPU time | Check for memory pressure or allocation spikes |
| Full GC events | Any in steady state | Investigate memory leak, increase old gen |
| Promotion failure | Objects cannot be promoted | Increase old gen or tune region size |

### GC Log Analysis Tools

| Tool | Type | Notes |
| --- | --- | --- |
| GCEasy | Online | Upload GC log for visual analysis |
| GCViewer | Desktop | Open-source GUI tool |
| `jstat -gcutil` | CLI | Real-time GC statistics |

```bash
# Real-time GC monitoring
jstat -gcutil <PID> 1000    # Print GC stats every 1 second

# Output columns: S0% S1% E% O% M% CCS% YGC YGCT FGC FGCT CGC CGCT GCT
```

---

## 4. Diagnostic Tools Reference

| Tool | Purpose | Usage |
| --- | --- | --- |
| `jcmd` | Multi-purpose diagnostic | `jcmd <PID> help` for available commands |
| `jstack` | Thread dump | `jstack <PID>` |
| `jmap` | Heap dump, histogram | `jmap -dump:live,format=b,file=dump.hprof <PID>` |
| `jstat` | GC statistics | `jstat -gcutil <PID> 1000` |
| `jinfo` | JVM flags and properties | `jinfo <PID>` |
| `jfr` | Flight Recorder | `jcmd <PID> JFR.start duration=60s filename=rec.jfr` |
| `async-profiler` | CPU/allocation profiling | Low-overhead production profiling |
| VisualVM | GUI monitoring | Attach to local/remote JVM |
| Arthas | Online diagnostics | Interactive CLI for live JVM debugging |

### Java Flight Recorder (JFR)

```bash
# Start recording (production-safe, ~1% overhead)
jcmd <PID> JFR.start name=recording duration=60s filename=/tmp/recording.jfr

# Continuous recording with dump on demand
jcmd <PID> JFR.start name=continuous maxage=1h maxsize=250m disk=true

# Dump continuous recording
jcmd <PID> JFR.dump name=continuous filename=/tmp/dump.jfr

# Stop recording
jcmd <PID> JFR.stop name=recording
```

### Quick Diagnostic Checklist

```text
1. High CPU
   → thread dump (look for RUNNABLE threads)
   → async-profiler CPU flame graph
   → jstat -gcutil (check if GC is consuming CPU)

2. High Memory / OOM
   → jcmd GC.class_histogram (quick class breakdown)
   → heap dump + Eclipse MAT (leak suspects report)
   → jstat -gcutil (check old gen growth)

3. Slow Response
   → thread dump (look for BLOCKED/WAITING threads)
   → GC log analysis (long pauses?)
   → JFR recording for latency analysis

4. Application Hang
   → multiple thread dumps 10s apart (compare stuck threads)
   → look for deadlocks in thread dump
   → check connection pool metrics
```
