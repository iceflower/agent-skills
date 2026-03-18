# Concurrency Testing

## Challenges

- Concurrent bugs are non-deterministic — they may not reproduce on every run
- Thread scheduling varies across runs, JVMs, and hardware
- A test passing 1000 times does not guarantee correctness

## Testing Strategies

| Strategy                 | Tool / Technique                   | Catches                         |
| ------------------------ | ---------------------------------- | ------------------------------- |
| Stress testing           | Multiple threads hitting same code | Race conditions under load      |
| Deterministic scheduling | `jcstress`, `Lincheck`             | All possible interleavings      |
| Static analysis          | SpotBugs, IntelliJ inspections     | Common concurrency antipatterns |
| Thread dump analysis     | `jstack`, `jcmd`                   | Deadlocks, thread starvation    |
| Assertions with latches  | `CountDownLatch`, `CyclicBarrier`  | Ordering violations             |

## JCStress Example

```java
@JCStressTest
@Outcome(id = "1, 1", expect = Expect.ACCEPTABLE, desc = "Both see update")
@Outcome(id = "0, 0", expect = Expect.ACCEPTABLE, desc = "Neither sees update")
@Outcome(id = "1, 0", expect = Expect.ACCEPTABLE, desc = "Only x seen")
@Outcome(id = "0, 1", expect = Expect.ACCEPTABLE_INTERESTING, desc = "Reordering observed")
@State
public class ReorderingTest {
    int x, y;

    @Actor
    public void writer() { x = 1; y = 1; }

    @Actor
    public void reader(II_Result r) { r.r1 = y; r.r2 = x; }
}
```

## Lincheck Example (Kotlin)

```kotlin
class ConcurrentMapTest {
    private val map = ConcurrentHashMap<Int, Int>()

    @Operation
    fun put(key: Int, value: Int) = map.put(key, value)

    @Operation
    fun get(key: Int) = map.get(key)

    @Test
    fun stressTest() = StressOptions().check(this::class)

    @Test
    fun modelCheckingTest() = ModelCheckingOptions().check(this::class)
}
```

## CountDownLatch Test Pattern

```java
@Test
void shouldBeThreadSafe() throws InterruptedException {
    int threadCount = 100;
    CountDownLatch startLatch = new CountDownLatch(1);
    CountDownLatch doneLatch = new CountDownLatch(threadCount);
    AtomicInteger errorCount = new AtomicInteger(0);

    for (int i = 0; i < threadCount; i++) {
        Thread.startVirtualThread(() -> {
            try {
                startLatch.await();  // All threads start simultaneously
                // Exercise the code under test
                service.process();
            } catch (Exception e) {
                errorCount.incrementAndGet();
            } finally {
                doneLatch.countDown();
            }
        });
    }

    startLatch.countDown();  // Release all threads at once
    doneLatch.await(10, TimeUnit.SECONDS);
    assertThat(errorCount.get()).isZero();
}
```

## Coroutine Testing

```kotlin
@Test
fun `concurrent access should be safe`() = runTest {
    val counter = AtomicInteger(0)
    val jobs = (1..1000).map {
        launch(Dispatchers.Default) {
            service.incrementSafely(counter)
        }
    }
    jobs.forEach { it.join() }
    assertThat(counter.get()).isEqualTo(1000)
}
```