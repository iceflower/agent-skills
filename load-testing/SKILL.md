---
name: load-testing
description: >-
  Load and performance testing best practices with k6 and Gatling including
  test design, metrics, thresholds, CI integration, and result analysis.
  Use when designing or implementing performance tests.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
compatibility: Requires k6 or Gatling
---

# Load Testing Rules

## 1. Core Principles

### Test Design Fundamentals

- Define clear performance objectives before writing tests
  (response time targets, throughput goals, error rate limits)
- Model realistic user behavior — not just raw endpoint hammering
- Test against a production-like environment with representative data
- Run baseline tests before making changes, then compare

### Performance Test Types

| Type       | Purpose                           | Duration  | Load Shape            |
| ---------- | --------------------------------- | --------- | --------------------- |
| Smoke      | Verify script works               | 1-2 min   | 1-5 VUs               |
| Load       | Validate under expected load      | 10-30 min | Ramp to target VUs    |
| Stress     | Find breaking point               | 15-45 min | Ramp beyond target    |
| Spike      | Test sudden traffic surge         | 5-15 min  | Sharp VU increase     |
| Soak       | Detect memory leaks / degradation | 1-4 hours | Steady at target VUs  |
| Breakpoint | Find maximum capacity             | Variable  | Step-up until failure |

### Test Order

1. **Smoke test** — verify the script runs correctly
2. **Load test** — validate normal conditions
3. **Stress test** — find upper limits
4. **Soak test** — verify long-running stability

---

## 2. k6 Test Patterns

### Basic Load Test Structure

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 50 },   // ramp up
    { duration: '5m', target: 50 },   // steady state
    { duration: '2m', target: 0 },    // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
    checks: ['rate>0.99'],
  },
};

export default function () {
  const res = http.get('https://api.example.com/users');

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
    'body contains data': (r) => r.json().data !== undefined,
  });

  sleep(1); // think time between requests
}
```

### Realistic User Scenario

```javascript
import http from 'k6/http';
import { check, group, sleep } from 'k6';

export default function () {
  group('User Login Flow', () => {
    // Step 1: Login
    const loginRes = http.post(
      'https://api.example.com/auth/login',
      JSON.stringify({ email: 'user@test.com', password: 'test' }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    check(loginRes, { 'login succeeded': (r) => r.status === 200 });

    const token = loginRes.json().token;
    const authHeaders = { Authorization: `Bearer ${token}` };

    sleep(2); // think time

    // Step 2: Browse products
    const productsRes = http.get(
      'https://api.example.com/products',
      { headers: authHeaders }
    );
    check(productsRes, { 'products loaded': (r) => r.status === 200 });

    sleep(3);

    // Step 3: View product detail
    const productId = productsRes.json().data[0].id;
    const detailRes = http.get(
      `https://api.example.com/products/${productId}`,
      { headers: authHeaders }
    );
    check(detailRes, { 'detail loaded': (r) => r.status === 200 });
  });
}
```

### Custom Metrics

```javascript
import { Trend, Counter, Rate } from 'k6/metrics';

const loginDuration = new Trend('login_duration');
const orderErrors = new Counter('order_errors');
const checkoutSuccess = new Rate('checkout_success');

export default function () {
  const start = Date.now();
  const res = http.post('https://api.example.com/auth/login', payload);
  loginDuration.add(Date.now() - start);

  if (res.status !== 200) {
    orderErrors.add(1);
    checkoutSuccess.add(false);
  } else {
    checkoutSuccess.add(true);
  }
}
```

---

## 3. Gatling Test Patterns

### Basic Simulation Structure

```scala
import io.gatling.core.Predef._
import io.gatling.http.Predef._
import scala.concurrent.duration._

class BasicSimulation extends Simulation {

  val httpProtocol = http
    .baseUrl("https://api.example.com")
    .acceptHeader("application/json")
    .contentTypeHeader("application/json")

  val scn = scenario("User Browse Flow")
    .exec(
      http("List Users")
        .get("/users")
        .check(status.is(200))
        .check(jsonPath("$.data").exists)
    )
    .pause(2)
    .exec(
      http("Get User Detail")
        .get("/users/1")
        .check(status.is(200))
        .check(responseTimeInMillis.lte(500))
    )

  setUp(
    scn.inject(
      rampUsers(50).during(2.minutes),
      constantUsersPerSec(10).during(5.minutes),
      rampUsers(0).during(2.minutes)
    )
  ).protocols(httpProtocol)
    .assertions(
      global.responseTime.percentile3.lt(500),
      global.successfulRequests.percent.gt(99.0)
    )
}
```

### Data-Driven Tests

```scala
val csvFeeder = csv("users.csv").random

val scn = scenario("Data Driven Test")
  .feed(csvFeeder)
  .exec(
    http("Login")
      .post("/auth/login")
      .body(StringBody("""{"email":"${email}","password":"${password}"}"""))
      .check(jsonPath("$.token").saveAs("authToken"))
  )
  .exec(
    http("Profile")
      .get("/users/me")
      .header("Authorization", "Bearer ${authToken}")
      .check(status.is(200))
  )
```

---

## 4. Key Metrics and Thresholds

### Core Metrics

| Metric              | Description                    | Typical Target      |
| ------------------- | ------------------------------ | ------------------- |
| Response Time (p50) | Median response time           | < 200ms             |
| Response Time (p95) | 95th percentile                | < 500ms             |
| Response Time (p99) | 99th percentile                | < 1000ms            |
| Throughput (RPS)    | Requests per second            | Varies by system    |
| Error Rate          | Percentage of failed requests  | < 1%                |
| Virtual Users (VUs) | Concurrent simulated users     | Match expected load |
| Data Transfer Rate  | Bytes sent/received per second | Monitor for limits  |

### Threshold Definition Guidelines

- Set thresholds based on SLO/SLA requirements, not arbitrary numbers
- Use percentile-based thresholds (p95, p99) — not averages
- Averages hide tail latency problems
- Define separate thresholds for critical and non-critical endpoints
- Thresholds must cause test failure in CI when breached

```javascript
// k6 threshold examples
export const options = {
  thresholds: {
    // Global thresholds
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],

    // Per-endpoint thresholds using tags
    'http_req_duration{name:login}': ['p(95)<300'],
    'http_req_duration{name:search}': ['p(95)<1000'],

    // Custom metric thresholds
    checkout_success: ['rate>0.99'],
  },
};
```

---

## 5. Test Data Management

### Principles

- Use realistic data volumes and distributions
- Generate test data programmatically — do not rely on production data
- Isolate test data from other environments
- Clean up test data after each run

### Data Strategies

| Strategy         | Pros                    | Cons                     |
| ---------------- | ----------------------- | ------------------------ |
| CSV/JSON feeders | Simple, reproducible    | Static, limited variety  |
| Generated data   | High variety, scalable  | Requires setup           |
| Shared pool      | Realistic contention    | Complex coordination     |
| Per-VU unique    | No contention           | Large data volume needed |

### Think Time

- Always include realistic think time (pauses) between requests
- Randomize think time to avoid artificial synchronization
- Typical ranges: 1-5 seconds for API flows, 5-30 seconds for UI flows
- Use `sleep(Math.random() * 3 + 1)` for 1-4 second random pauses in k6

---

## 6. CI/CD Integration

### Pipeline Integration

```yaml
# GitHub Actions example
performance-test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Run k6 smoke test
      uses: grafana/k6-action@v0.3.1
      with:
        filename: tests/performance/smoke.js

    - name: Run k6 load test
      if: github.ref == 'refs/heads/main'
      uses: grafana/k6-action@v0.3.1
      with:
        filename: tests/performance/load.js
      env:
        K6_CLOUD_TOKEN: ${{ secrets.K6_CLOUD_TOKEN }}
```

### CI Integration Rules

- Run smoke tests on every PR
- Run full load tests on main branch merges or scheduled
- Store results as CI artifacts for trend analysis
- Fail the pipeline when thresholds are breached
- Never run load tests against production from CI

### Result Storage

- Export results to a time-series database (InfluxDB, Prometheus)
  for trend tracking
- Keep at least 30 days of historical results for comparison
- Tag results with commit hash, branch, and environment
- Generate comparison reports between runs automatically

---

## 7. Result Analysis

### Analysis Checklist

1. Check error rate first — errors invalidate other metrics
2. Review response time percentiles (p50, p95, p99)
3. Look for degradation patterns during ramp-up
4. Check if throughput plateaus (saturation point)
5. Correlate with server metrics (CPU, memory, DB connections)

### Common Bottleneck Indicators

| Symptom                           | Likely Cause               |
| --------------------------------- | -------------------------- |
| Latency increases with VUs        | Resource saturation        |
| Sudden error spike                | Connection pool exhaustion |
| Flat throughput despite more VUs  | Backend bottleneck         |
| Gradual latency increase          | Memory leak or GC pressure |
| Timeout errors only               | Downstream service issue   |

### Reporting

- Include request/response time distribution charts
- Show throughput over time with concurrent user count overlay
- Highlight any threshold breaches with context
- Compare against baseline or previous run
- Include environment details (instance type, replicas, config)

---

## 8. Anti-Patterns

- Testing without defined performance targets or SLOs
- Using average response time as the primary metric —
  use percentiles instead
- Running load tests against production without safeguards
- Omitting think time (creating unrealistic thundering herd)
- Using a single endpoint test to represent full system performance
- Ignoring test environment differences from production
  (fewer replicas, smaller DB)
- Running load tests from a single machine
  that becomes the bottleneck itself
- Not cleaning up test data between runs
- Skipping smoke tests and going straight to full load tests
- Treating load testing as a one-time activity
  instead of continuous practice

---

## 9. Related Skills

- **monitoring**: Correlate load test results with system metrics
- **ci-cd**: Pipeline integration for automated performance testing
- **k8s-workflow**: Kubernetes-specific performance considerations

## 10. Additional References

- [k6 Documentation](https://grafana.com/docs/k6/latest/) — Official k6 documentation
- [Gatling Documentation](https://docs.gatling.io/) — Official Gatling documentation
- [Google SRE Book - Load Balancing](https://sre.google/sre-book/load-balancing-frontend/) — Production load testing principles
