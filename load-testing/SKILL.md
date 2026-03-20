---
name: load-testing
description: >-
  Load and performance testing patterns with k6 and Gatling including
  test design, metrics, thresholds, and CI integration.
  Use when designing or running performance tests.
---

# Load and Performance Testing Rules

## 1. Test Types

### Load Test

- Validates system behavior under **expected** concurrent load
- Ramp up gradually to target load, sustain, then ramp down
- Use as the baseline test run before every release

```text
Stages:
  [0-2min]  Ramp up from 0 to 100 VUs
  [2-10min] Sustain 100 VUs
  [10-12min] Ramp down to 0
```

### Stress Test

- Pushes the system **beyond** normal capacity to find the breaking point
- Increase load in steps until errors or degradation appear
- Identifies the maximum capacity and failure modes

```text
Stages:
  [0-2min]   Ramp up to 100 VUs
  [2-5min]   Sustain 100 VUs
  [5-7min]   Ramp up to 200 VUs
  [7-10min]  Sustain 200 VUs
  [10-12min] Ramp up to 400 VUs
  [12-15min] Sustain 400 VUs
  [15-17min] Ramp down to 0
```

### Spike Test

- Simulates sudden, extreme load increases
- Tests auto-scaling behavior and graceful degradation
- Short duration; focus on recovery time after the spike

```text
Stages:
  [0-1min]  Ramp up to 10 VUs (baseline)
  [1-2min]  Spike to 500 VUs
  [2-3min]  Drop to 10 VUs
  [3-5min]  Monitor recovery
```

### Soak Test (Endurance)

- Runs at moderate load for an **extended period** (hours)
- Detects memory leaks, connection pool exhaustion, and resource degradation
- Typically run overnight or during low-traffic windows

```text
Stages:
  [0-5min]    Ramp up to 80 VUs
  [5min-4hr]  Sustain 80 VUs
  [4hr-4h5m]  Ramp down to 0
```

## 2. k6 Script Patterns

### Basic Script Structure

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const loginDuration = new Trend('login_duration');

export const options = {
  stages: [
    { duration: '2m', target: 50 },
    { duration: '5m', target: 50 },
    { duration: '2m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1500'],
    http_req_failed: ['rate<0.01'],
    errors: ['rate<0.05'],
  },
};

export default function () {
  const res = http.get('https://api.example.com/users');

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
    'body contains users': (r) => r.json().users !== undefined,
  });

  errorRate.add(res.status !== 200);
  sleep(1);
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
        { duration: '2m', target: 100 },
        { duration: '5m', target: 100 },
        { duration: '2m', target: 0 },
      ],
      exec: 'browseProducts',
    },
    purchase: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 50,
      maxVUs: 100,
      exec: 'purchaseFlow',
    },
  },
};

export function browseProducts() {
  const res = http.get('https://api.example.com/products');
  check(res, { 'browse OK': (r) => r.status === 200 });
  sleep(Math.random() * 3 + 1);
}

export function purchaseFlow() {
  // Step 1: Add to cart
  const cartRes = http.post(
    'https://api.example.com/cart',
    JSON.stringify({ productId: 'prod-001', quantity: 1 }),
    { headers: { 'Content-Type': 'application/json' } },
  );
  check(cartRes, { 'added to cart': (r) => r.status === 201 });

  sleep(1);

  // Step 2: Checkout
  const checkoutRes = http.post('https://api.example.com/checkout');
  check(checkoutRes, { 'checkout OK': (r) => r.status === 200 });
}
```

### Data Parameterization

```javascript
import { SharedArray } from 'k6/data';
import papaparse from 'https://jslib.k6.io/papaparse/5.1.1/index.js';

// Load test data once and share across VUs
const users = new SharedArray('users', function () {
  const data = papaparse.parse(open('./testdata/users.csv'), {
    header: true,
  });
  return data.data;
});

export default function () {
  const user = users[__VU % users.length];
  const res = http.post(
    'https://api.example.com/login',
    JSON.stringify({ email: user.email, password: user.password }),
    { headers: { 'Content-Type': 'application/json' } },
  );
  check(res, { 'login successful': (r) => r.status === 200 });
}
```

## 3. Gatling Script Patterns

### Basic Simulation

```scala
import io.gatling.core.Predef._
import io.gatling.http.Predef._
import scala.concurrent.duration._

class BasicSimulation extends Simulation {
  val httpProtocol = http
    .baseUrl("https://api.example.com")
    .acceptHeader("application/json")
    .contentTypeHeader("application/json")

  val scn = scenario("Browse Products")
    .exec(
      http("List Products")
        .get("/products")
        .check(status.is(200))
        .check(jsonPath("$.products").exists)
    )
    .pause(1, 3)
    .exec(
      http("Product Detail")
        .get("/products/#{productId}")
        .check(status.is(200))
        .check(jsonPath("$.name").saveAs("productName"))
    )

  setUp(
    scn.inject(
      rampUsers(100).during(2.minutes),
      constantUsersPerSec(20).during(5.minutes),
      rampUsers(0).during(1.minute)
    )
  ).protocols(httpProtocol)
    .assertions(
      global.responseTime.percentile(95).lt(500),
      global.successfulRequests.percent.gt(99)
    )
}
```

### Feeder for Test Data

```scala
class DataDrivenSimulation extends Simulation {
  // CSV feeder
  val userFeeder = csv("testdata/users.csv").random

  // JSON feeder
  val productFeeder = jsonFile("testdata/products.json").circular

  val scn = scenario("User Journey")
    .feed(userFeeder)
    .exec(
      http("Login")
        .post("/auth/login")
        .body(StringBody("""{"email":"#{email}","password":"#{password}"}"""))
        .check(status.is(200))
        .check(jsonPath("$.token").saveAs("authToken"))
    )
    .feed(productFeeder)
    .exec(
      http("View Product")
        .get("/products/#{productId}")
        .header("Authorization", "Bearer #{authToken}")
        .check(status.is(200))
    )

  setUp(
    scn.inject(rampUsers(50).during(2.minutes))
  ).protocols(httpProtocol)
}
```

## 4. Key Metrics

### Response Time Metrics

| Metric            | Description                            | Typical Threshold      |
| ----------------- | -------------------------------------- | ---------------------- |
| p50 (median)      | 50th percentile response time          | < 200ms (API)         |
| p95               | 95th percentile response time          | < 500ms (API)         |
| p99               | 99th percentile response time          | < 1500ms (API)        |
| max               | Maximum observed response time         | Monitor, no hard limit |
| avg               | Average response time                  | Use p50 instead       |

### Throughput Metrics

| Metric            | Description                            | Notes                       |
| ----------------- | -------------------------------------- | --------------------------- |
| requests/sec      | Total requests per second              | Primary throughput metric    |
| iterations/sec    | Complete scenario iterations per sec   | k6-specific                  |
| data received     | Bytes received per second              | Network bandwidth indicator  |
| data sent         | Bytes sent per second                  | Upload bandwidth indicator   |

### Error Metrics

| Metric                | Description                     | Typical Threshold |
| --------------------- | ------------------------------- | ----------------- |
| error rate            | Percentage of failed requests   | < 1%             |
| http_req_failed       | HTTP request failure rate       | < 0.1%           |
| timeout rate          | Requests that timed out         | < 0.5%           |

### Why Percentiles Over Averages

- Averages hide tail latency; a few slow requests raise the average silently
- p95 captures the experience of 95% of users
- p99 catches outliers that may indicate resource contention
- Always report **p50, p95, and p99** together for a complete picture

## 5. Threshold Design

### Setting Thresholds

- Base thresholds on **SLOs** (Service Level Objectives), not arbitrary values
- Differentiate thresholds by endpoint criticality (payment vs. search)
- Start conservative; tighten after establishing baselines
- Separate read (GET) and write (POST/PUT) thresholds

```javascript
// k6 threshold examples
export const options = {
  thresholds: {
    // Global thresholds
    http_req_duration: ['p(95)<500', 'p(99)<1500'],
    http_req_failed: ['rate<0.01'],

    // Per-endpoint thresholds using tags
    'http_req_duration{name:login}': ['p(95)<1000'],
    'http_req_duration{name:search}': ['p(95)<300'],
    'http_req_duration{name:checkout}': ['p(95)<2000'],

    // Custom metric thresholds
    errors: ['rate<0.05'],
    login_duration: ['p(95)<800', 'avg<400'],
  },
};
```

### Threshold Escalation

- **Warning**: p95 > baseline * 1.5 (alert, no block)
- **Failure**: p95 > SLO threshold (block deployment)
- **Critical**: error rate > 5% or p99 > 5s (immediate investigation)

## 6. CI/CD Integration

### GitHub Actions with k6

```yaml
name: Performance Tests
on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1-5'  # weekdays at 2 AM

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install k6
        run: |
          sudo gpg -k
          sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
            --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D68
          echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
            | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update && sudo apt-get install -y k6

      - name: Run load test
        run: k6 run tests/performance/load-test.js --out json=results.json
        env:
          K6_TARGET_URL: ${{ secrets.STAGING_URL }}
          CLIENT_ID: ${{ secrets.PERF_CLIENT_ID }}
          CLIENT_SECRET: ${{ secrets.PERF_CLIENT_SECRET }}

      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: k6-results
          path: results.json
```

### Pipeline Integration Best Practices

- Run **smoke tests** (minimal load, short duration) on every PR
- Run **full load tests** on merge to main or on a nightly schedule
- Store results as artifacts for trend analysis
- Set pipeline to **fail** when thresholds are breached
- Use dedicated infrastructure for load testing; never test against production without approval

```text
PR Pipeline:
  smoke test → 10 VUs, 1 min → pass/fail gate

Main Pipeline:
  load test → 100 VUs, 10 min → performance report + pass/fail gate

Nightly:
  soak test → 50 VUs, 2 hours → trend dashboard + alerts
```

## 7. Anti-Patterns

### Test Design Anti-Patterns

- Do not test against production without explicit approval and traffic controls
- Do not use fixed sleep values; add randomness to simulate real user behavior
- Do not skip warm-up; always ramp up gradually
- Do not ignore DNS and connection reuse settings (they affect measured latency)
- Do not test a single endpoint in isolation; test realistic user journeys

### Metric Anti-Patterns

- Do not rely on **average** response time alone; always use percentiles
- Do not set thresholds based on gut feeling; derive from SLOs
- Do not ignore error rate when response times look acceptable
- Do not compare results from different environments or configurations

### CI Anti-Patterns

- Do not run load tests on shared CI runners (noisy neighbor effect)
- Do not hardcode absolute thresholds without baseline measurement
- Do not skip performance tests for "small" changes (regressions hide in small changes)
- Do not run soak tests on every PR (too slow); use smoke tests instead

## 8. Related Skills

- `ci-cd` - CI/CD pipeline design and integration patterns
- `monitoring` - Production monitoring and alerting
- `k8s-workflow` - Kubernetes scaling and resource management
- `api-design` - API design patterns that affect performance characteristics
