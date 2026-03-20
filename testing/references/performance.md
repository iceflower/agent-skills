# Performance Testing

## 1. Performance Testing Types

| Type | Purpose | Duration | Load Pattern |
| --- | --- | --- | --- |
| Load Test | Validate under expected load | 15-60 min | Steady at target RPS |
| Stress Test | Find breaking point | 15-30 min | Ramp until failure |
| Soak/Endurance | Detect memory leaks, degradation | 4-24 hours | Steady moderate load |
| Spike Test | Validate sudden traffic burst | 10-20 min | Sudden spike and drop |
| Capacity Test | Determine maximum capacity | 30-60 min | Step-up increments |

### When to Use Each

```text
New feature launch     → Load test + Spike test
Before production release → Load test + Soak test
Capacity planning      → Capacity test
Architecture validation → Stress test
Memory leak suspicion  → Soak test
```

---

## 2. Key Metrics

### Primary Metrics

| Metric | Definition | Healthy Target |
| --- | --- | --- |
| Throughput (RPS) | Requests per second | Meets or exceeds SLO |
| Latency p50 | Median response time | <200ms (API) |
| Latency p95 | 95th percentile | <500ms (API) |
| Latency p99 | 99th percentile | <1s (API) |
| Error rate | % of failed requests | <0.1% |

### Resource Metrics

| Metric | Warning Threshold | Critical Threshold |
| --- | --- | --- |
| CPU utilization | >70% sustained | >90% |
| Memory utilization | >80% | >90% |
| Connection pool usage | >70% | >90% |
| Thread pool saturation | >80% | Queue growing |
| Disk I/O wait | >20% | >40% |
| Network bandwidth | >70% capacity | >90% |

### Derived Metrics

| Metric | Calculation | Purpose |
| --- | --- | --- |
| Apdex Score | (Satisfied + Tolerating/2) / Total | User satisfaction index |
| Requests per Error | Total / Errors | Reliability ratio |
| Throughput per Instance | Total RPS / Instance count | Scaling efficiency |

---

## 3. Tool Selection

| Tool | Language | Protocol | Strengths | Weaknesses |
| --- | --- | --- | --- | --- |
| k6 | JavaScript | HTTP, gRPC, WebSocket | Developer-friendly, CI native, cloud option | Single-threaded per VU |
| Gatling | Scala/Java | HTTP, WebSocket | Rich reports, DSL, JVM ecosystem | Steeper learning curve |
| JMeter | Java (GUI) | HTTP, JDBC, JMS | GUI, plugin ecosystem, protocol variety | Resource heavy, verbose XML |
| Locust | Python | HTTP | Easy scripting, distributed | Python GIL limits throughput |
| wrk2 | C | HTTP | Coordinated omission fix, very fast | No scripting, basic output |
| hey | Go | HTTP | Simple, fast installation | Basic, no scenarios |

### Recommendation

- **CI/CD integration, developer-owned**: k6
- **JVM project, detailed reports**: Gatling
- **Quick ad-hoc benchmarks**: wrk2 or hey
- **Complex protocols (JDBC, JMS)**: JMeter

---

## 4. k6 Patterns

### Basic Script Structure

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiDuration = new Trend('api_duration', true);

export const options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp up
    { duration: '5m', target: 50 },   // Steady state
    { duration: '2m', target: 100 },  // Peak load
    { duration: '5m', target: 100 },  // Sustained peak
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
    errors: ['rate<0.05'],
  },
};

export default function () {
  const res = http.get('http://api.example.com/users');

  apiDuration.add(res.timings.duration);
  errorRate.add(res.status !== 200);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
    'has valid body': (r) => r.json().length > 0,
  });

  sleep(1); // Think time between requests
}
```

### Scenario-Based Testing

```javascript
export const options = {
  scenarios: {
    browse: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '5m', target: 100 },
        { duration: '10m', target: 100 },
      ],
      exec: 'browseProducts',
    },
    purchase: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '15m',
      preAllocatedVUs: 50,
      exec: 'purchaseFlow',
    },
  },
};

export function browseProducts() {
  http.get('http://api.example.com/products');
  sleep(Math.random() * 3 + 1);
}

export function purchaseFlow() {
  const products = http.get('http://api.example.com/products').json();
  sleep(1);
  http.post('http://api.example.com/cart', JSON.stringify({
    productId: products[0].id,
  }), { headers: { 'Content-Type': 'application/json' } });
  sleep(2);
  http.post('http://api.example.com/checkout');
}
```

### Data Parameterization

```javascript
import { SharedArray } from 'k6/data';
import papaparse from 'https://jslib.k6.io/papaparse/5.1.1/index.js';

const users = new SharedArray('users', function () {
  return papaparse.parse(open('./users.csv'), { header: true }).data;
});

export default function () {
  const user = users[__VU % users.length];
  http.post('http://api.example.com/login', JSON.stringify({
    username: user.username,
    password: user.password,
  }));
}
```

---

## 5. Gatling Patterns

### Simulation Structure (Kotlin DSL)

```kotlin
class UserSimulation : Simulation() {

    val httpProtocol = http
        .baseUrl("http://api.example.com")
        .acceptHeader("application/json")
        .contentTypeHeader("application/json")

    val feeder = csv("users.csv").random()

    val browseScenario = scenario("Browse Products")
        .exec(
            http("List Products")
                .get("/products")
                .check(status().`is`(200))
                .check(jsonPath("$[0].id").saveAs("productId"))
        )
        .pause(1, 3)
        .exec(
            http("Get Product Detail")
                .get("/products/#{productId}")
                .check(status().`is`(200))
        )

    val purchaseScenario = scenario("Purchase Flow")
        .feed(feeder)
        .exec(
            http("Login")
                .post("/auth/login")
                .body(StringBody("""{"username":"#{username}","password":"#{password}"}"""))
                .check(jsonPath("$.token").saveAs("token"))
        )
        .exec(
            http("Add to Cart")
                .post("/cart")
                .header("Authorization", "Bearer #{token}")
                .body(StringBody("""{"productId":1,"quantity":1}"""))
        )

    init {
        setUp(
            browseScenario.injectOpen(
                rampUsers(100).during(120),
                constantUsersPerSec(20.0).during(300),
            ),
            purchaseScenario.injectOpen(
                rampUsers(50).during(120),
                constantUsersPerSec(5.0).during(300),
            )
        ).protocols(httpProtocol)
            .assertions(
                global().responseTime().percentile3().lt(500),
                global().successfulRequests().percent().gt(99.0),
            )
    }
}
```

### Injection Profiles

| Profile | Method | Use Case |
| --- | --- | --- |
| `rampUsers(n).during(d)` | Linear ramp | Gradual load increase |
| `constantUsersPerSec(r).during(d)` | Constant arrival rate | Sustained load |
| `stressPeakUsers(n).during(d)` | Bell curve | Peak simulation |
| `nothingFor(d)` | Pause | Wait between phases |
| `atOnceUsers(n)` | Instant spike | Spike testing |

---

## 6. Test Design

### Realistic Scenario Design

| Element | Rule |
| --- | --- |
| User journey | Model real user workflows, not isolated endpoints |
| Think time | Add realistic pauses between requests (1-5s) |
| Data variety | Use parameterized data, not hardcoded values |
| Session handling | Maintain auth tokens, cookies across requests |
| Error scenarios | Include 4xx/5xx handling in the scenario |

### Warm-Up Period

- Always include a ramp-up phase (2-5 minutes minimum)
- Exclude warm-up data from final results
- JVM-based services need JIT compilation warm-up
- Database connection pools need time to initialize

### Correlation and Dynamic Data

```text
1. Login → Extract auth token
2. List resources → Extract resource ID
3. Get resource detail → Use extracted ID
4. Update resource → Use extracted ID + token
```

---

## 7. CI/CD Integration

### GitHub Actions Example (k6)

```yaml
name: Performance Test

on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly Monday 2 AM
  workflow_dispatch:

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install k6
        run: |
          sudo gpg -k
          sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D68
          echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update && sudo apt-get install k6

      - name: Run load test
        run: k6 run --out json=results.json tests/load-test.js

      - name: Check thresholds
        run: |
          if k6 run --no-summary tests/load-test.js; then
            echo "Performance thresholds passed"
          else
            echo "Performance thresholds FAILED"
            exit 1
          fi

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: k6-results
          path: results.json
```

### Performance Gates

| Metric | Gate Condition | Action on Failure |
| --- | --- | --- |
| p95 latency | < baseline × 1.2 | Block deployment |
| Error rate | < 0.1% | Block deployment |
| Throughput | > baseline × 0.9 | Warn, manual review |
| Memory usage | < baseline × 1.5 | Warn, investigate |

### Baseline Management

- Establish baselines on main branch after each release
- Compare feature branch results against main baseline
- Allow configurable tolerance (e.g., ±10%)
- Store historical results for trend analysis

---

## 8. Environment Considerations

| Factor | Requirement |
| --- | --- |
| Infrastructure | Production-like sizing (CPU, memory, network) |
| Data volume | Representative dataset (not empty DB) |
| Network | Similar latency to production (same region if possible) |
| Dependencies | Real or high-fidelity stubs (not simple mocks) |
| Monitoring | Same observability stack as production |
| Isolation | Dedicated environment (no shared traffic) |

### Data Preparation

- Generate realistic volume (millions of rows for large-table queries)
- Include edge cases (large records, unicode, null values)
- Use anonymized production data snapshots when possible
- Reset data between test runs for consistency

---

## 9. Results Analysis

### Bottleneck Identification

```text
High latency + Low CPU → I/O bound (DB queries, external APIs)
High latency + High CPU → CPU bound (computation, serialization)
High latency + Thread pool saturated → Concurrency issue
Increasing latency over time → Memory leak or resource exhaustion
Sudden latency spike → GC pause, connection pool exhaustion
Error rate increases with load → Capacity limit reached
```

### Profiling Correlation

| Symptom | Profiling Tool | What to Check |
| --- | --- | --- |
| High CPU | async-profiler, JFR | Hot methods, GC overhead |
| High memory | Heap dump, JFR | Object allocation, leaks |
| Slow queries | Query analyzer, APM | Execution plans, lock waits |
| Thread contention | Thread dump | Lock contention, deadlocks |
| Connection issues | APM, pool metrics | Pool exhaustion, leak detection |

### Reporting Template

```markdown
## Performance Test Report — [Date]

### Test Configuration
- **Environment**: [staging/perf]
- **Duration**: [X minutes]
- **Peak VUs**: [N virtual users]
- **Target RPS**: [N requests/second]

### Results Summary
| Metric | Target | Actual | Status |
| --- | --- | --- | --- |
| p50 latency | <200ms | Xms | ✅/❌ |
| p95 latency | <500ms | Xms | ✅/❌ |
| p99 latency | <1s | Xms | ✅/❌ |
| Error rate | <0.1% | X% | ✅/❌ |
| Throughput | >N RPS | X RPS | ✅/❌ |

### Bottlenecks Identified
1. [Description + evidence]

### Recommendations
1. [Action item]

### Comparison with Baseline
| Metric | Baseline | Current | Delta |
| --- | --- | --- | --- |
```

---

## 10. Anti-Patterns

- Running performance tests against localhost — network and infra behavior differ completely
- No warm-up phase — JIT, connection pools, and caches give misleading cold-start results
- Testing without baselines — cannot distinguish regression from normal variance
- Single-metric focus (only average latency) — p99 and error rate tell the real story
- Unrealistic scenarios — single endpoint hammering does not represent real user behavior
- Ignoring think time — zero-delay requests create unrealistic concurrency
- Testing with empty databases — query performance depends on data volume
- Not correlating with APM/profiling — performance tests find symptoms, profiling finds causes
- Running performance tests only before release — trends over time catch gradual degradation
- Sharing performance test environment with other workloads — noisy neighbor ruins results
