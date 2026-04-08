# SLO/SLI Design and Business Metrics Modeling

## 1. SLO/SLI Foundation

### Definitions

| Term | Definition | Example |
| --- | --- | --- |
| **SLI** (Service Level Indicator) | Quantitative measure of service behavior | Request latency p99, error rate, availability |
| **SLO** (Service Level Objective) | Target value or range for an SLI | p99 latency < 500ms, 99.9% availability |
| **SLA** (Service Level Agreement) | Contractual consequence of missing SLOs | Financial penalty, service credits |

### Relationship

```text
SLI (measure) → SLO (target) → SLA (contract)
   │                  │                │
   "What to measure"  "What to aim for"  "What happens if we miss"
```

### Why SLOs Matter

- **Shared understanding**: Align engineering, product, and business on reliability targets
- **Error budgets**: Quantify how much unreliability is acceptable before prioritizing reliability over features
- **Data-driven decisions**: Replace "it feels slow" with "SLO burn rate exceeded"
- **Blameless incident classification**: SLO violations indicate systemic issues, not individual failures

---

## 2. SLI Selection Framework

### SLI Categories by Service Type

#### Web/API Services (Request-Driven)

| SLI Category | SLI Definition | Good SLO Target | Measurement |
| --- | --- | --- | --- |
| Availability | % of requests returning non-5xx | 99.9% | `1 - (5xx_requests / total_requests)` |
| Latency | % of requests faster than threshold | 99% < 200ms, 95% < 100ms | Histogram percentiles |
| Correctness | % of responses with correct data | 99.99% | Business logic validation |

#### Batch/Job Services

| SLI Category | SLI Definition | Good SLO Target | Measurement |
| --- | --- | --- | --- |
| Completion | % of jobs completing successfully | 99.5% | `successful_jobs / total_jobs` |
| Freshness | % of jobs completing within deadline | 99% within SLA window | Job duration vs. deadline |
| Coverage | % of expected data processed | 99.9% | Records processed vs. expected |

#### Stream Processing

| SLI Category | SLI Definition | Good SLO Target | Measurement |
| --- | --- | --- | --- |
| Processing lag | % of events processed within threshold | 99% < 5 min behind | Consumer lag metric |
| Delivery | % of events delivered to downstream | 99.99% | Delivered vs. produced |
| Ordering | % of events in correct order | 99.9% | Out-of-order detection |

#### Frontend/User-Facing

| SLI Category | SLI Definition | Good SLO Target | Measurement |
| --- | --- | --- | --- |
| Page Load | % of page loads < threshold | 95% < 3s (LCP) | Core Web Vitals |
| Interaction | % of interactions < threshold | 95% < 200ms (INP) | Core Web Vitals |
| Error Rate | % of user sessions without JS errors | 99% | Error tracking (Sentry) |

### SLI Selection Rules

- **Measure what users experience**: Latency from the client perspective, not server processing time
- **Use proportional SLIs**: "Percentage of requests that..." not "average latency is..."
- **Limit SLIs per service**: 3-5 SLIs per service — too many dilute focus
- **Prioritize by user impact**: Availability > Latency > Correctness (in order of user visibility)

---

## 3. SLO Design Process

### User Journey Mapping

```text
1. Identify critical user journeys
   Example: "User adds item to cart and checks out"

2. Map journey to service dependencies
   Cart Service → Inventory Service → Payment Service → Order Service

3. Define SLIs for each step in the journey
   Cart: availability, latency
   Inventory: correctness (stock check accuracy)
   Payment: availability (payment gateway success)
   Order: completion (order created)

4. Set SLOs based on user expectations and business requirements
   Checkout journey: 99.5% availability, p95 < 1s

5. Calculate composite SLO for the journey
   Composite = SLI_1 × SLI_2 × ... × SLI_n
   0.999 × 0.999 × 0.9995 = 0.9975 (99.75%)
```

### Critical Path Identification

| Priority | Service | Why Critical | SLIs to Define |
| --- | --- | --- | --- |
| P0 | Authentication | Blocks all actions | Availability, Latency |
| P0 | Payment | Direct revenue impact | Availability, Correctness |
| P1 | Product catalog | Browse before buy | Availability, Latency |
| P1 | Search | Primary discovery mechanism | Latency, Relevance |
| P2 | Recommendations | Nice-to-have | Latency (soft SLO) |

### SLO Threshold Setting

```text
Step 1: Measure historical performance (last 30 days)
  p50 = 45ms, p95 = 180ms, p99 = 520ms

Step 2: Apply user-centric reasoning
  "Is 520ms acceptable for users?" → Depends on endpoint
  Search: 520ms is too slow → SLO: p99 < 300ms
  Batch report: 520ms is fine → SLO: p99 < 2s

Step 3: Add safety margin
  Historical p99 = 520ms, target = 300ms
  SLO: p99 < 400ms (allows 33% headroom for variance)

Step 4: Document rationale
  "SLO p99 < 400ms based on: UX research shows >500ms perceived as slow,
   historical p99 is 520ms (needs optimization), 400ms is achievable per benchmark"
```

### Seasonality Considerations

- **Traffic patterns**: Black Friday, end-of-month batch processing, seasonal peaks
- **Set separate SLOs for peak vs. off-peak** if performance differs significantly
- **Use rolling windows**: 30-day rolling windows smooth out daily variance better than fixed windows
- **Review quarterly**: SLOs should evolve as user expectations and system capabilities change

---

## 4. Error Budget Policy

### Error Budget Calculation

```text
Error Budget = 1 - SLO

Example: SLO = 99.9% availability
Error Budget = 0.1% = 43.2 minutes/month = 8.7 hours/year

For 100,000 requests/day:
Daily error budget = 100,000 × 0.001 = 100 failed requests/day
```

### Budget Burn Rate

| Burn Rate | Time to Exhaust (30-day budget) | Severity |
| --- | --- | --- |
| 1x | 30 days | Normal consumption |
| 2x | 15 days | Watch |
| 6x | 5 days | Warning — post incident review |
| 14.4x | 2 days | Critical — stop deploys, all hands on reliability |
| 43.2x | 16.6 hours | Emergency — page on-call immediately |

### Error Budget Policy Template

```markdown
## Error Budget Policy for [Service Name]

### SLO: [99.9% availability / p99 < 400ms]

### Budget Allocation
- 80% for planned changes (deployments, migrations)
- 20% for unplanned incidents

### Actions by Budget Remaining

| Budget Remaining | Action |
| --- | --- |
| > 50% | Normal operations, feature development continues |
| 25-50% | Postmortem for recent violations, review in weekly standup |
| 10-25% | Pause non-critical deployments, assign reliability tasks |
| < 10% | Freeze feature deployments, all engineers on reliability |
| 0% (exhausted) | Incident mode, revert recent changes if needed |

### Budget Reset
- Monthly (calendar month)
- Or after SLO violation postmortem with corrective actions documented
```

### Multi-Window Burn Rate Alerts

```yaml
# Prometheus alerting rule for error budget burn rate
groups:
  - name: slo-burn-rate
    rules:
      # Fast burn: 14.4x rate over 1 hour (consumes 2% budget in 1 hour)
      - alert: HighErrorBudgetBurnRate
        expr: |
          (
            sum(rate(http_requests_total{code=~"5.."}[1h]))
            /
            sum(rate(http_requests_total[1h]))
          )
          >
          (14.4 * (1 - 0.999))
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error budget burning at 14.4x rate"
          description: >
            The error rate over the last 1 hour is consuming the error budget
            at 14.4x the normal rate. If this continues, the monthly budget
            will be exhausted in approximately 2 days.
            Current 1h error rate: {{ $value | printf "%.4f" }}
            SLO threshold (annualized): {{ 1 - 0.999 | printf "%.4f" }}

      # Slow burn: 6x rate over 6 hours (consumes 5% budget in 6 hours)
      - alert: ModerateErrorBudgetBurnRate
        expr: |
          (
            sum(rate(http_requests_total{code=~"5.."}[6h]))
            /
            sum(rate(http_requests_total[6h]))
          )
          >
          (6 * (1 - 0.999))
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Error budget burning at 6x rate"
```

---

## 5. Multi-Window Multi-Burn-Rate Alerting

### Google SRE Approach

The key insight: use **two windows** together to detect both fast and slow burns.

| Alert Type | Short Window | Long Window | Burn Rate | Budget Consumed |
| --- | --- | --- | --- | --- |
| Critical (page) | 1h | 5m | 14.4x | 2% in 1h |
| Warning (ticket) | 6h | 30m | 6x | 5% in 6h |
| Notice (ticket) | 1d | 2h | 3x | 5% in 1d |
| Slow drain | 3d | 6h | 1x | 10% in 3d |

### Why Two Windows

- **Short window**: Detects the issue quickly (fast reaction)
- **Long window**: Confirms the issue is sustained (reduces false positives)
- **Both must be true**: Alert fires only when both windows show elevated error rate

### Implementation

```yaml
groups:
  - name: slo-multi-window
    rules:
      # Page: 14.4x burn rate (1h short / 5m long)
      - alert: SLOErrorBudgetCritical
        expr: |
          (
            sum(rate(http_requests_total{code=~"5.."}[1h])) OR vector(0)
            /
            sum(rate(http_requests_total[1h]))
          ) > (1 - 0.999) * 14.4
          and
          (
            sum(rate(http_requests_total{code=~"5.."}[5m])) OR vector(0)
            /
            sum(rate(http_requests_total[5m]))
          ) > (1 - 0.999) * 14.4
        for: 2m
        labels:
          severity: critical
          slo_window: 1h
          slo_burn_rate: "14.4"
        annotations:
          summary: "SLO burn rate critical (14.4x)"
          runbook: "https://wiki/slo-runbook#critical"

      # Ticket: 6x burn rate (6h short / 30m long)
      - alert: SLOErrorBudgetWarning
        expr: |
          (
            sum(rate(http_requests_total{code=~"5.."}[6h])) OR vector(0)
            /
            sum(rate(http_requests_total[6h]))
          ) > (1 - 0.999) * 6
          and
          (
            sum(rate(http_requests_total{code=~"5.."}[30m])) OR vector(0)
            /
            sum(rate(http_requests_total[30m]))
          ) > (1 - 0.999) * 6
        for: 15m
        labels:
          severity: warning
          slo_window: 6h
          slo_burn_rate: "6"
        annotations:
          summary: "SLO burn rate elevated (6x)"
          runbook: "https://wiki/slo-runbook#warning"
```

---

## 6. Business Metrics Modeling

### Identifying Business-Critical Metrics

| Business Outcome | Technical SLI | Correlation | Monitoring |
| --- | --- | --- | --- |
| Revenue per transaction | Payment API latency | Direct: >2s = 7% drop-off | Track alongside checkout funnel |
| User retention | Search result latency | Indirect: slow search = lower engagement | A/B test latency impact on 7d retention |
| Customer satisfaction (CSAT) | p95 API latency | Correlated: CSAT drops when p95 > 500ms | Survey scores vs. latency by cohort |
| Support ticket volume | Error rate | Direct: 5xx spikes → ticket spikes within 24h | Alert on error rate before tickets arrive |
| Conversion rate | Page load time | Direct: 100ms delay = 1% conversion drop | Split by geography and device |

### Correlating Technical SLIs with Business Outcomes

```promql
# Revenue impact of errors
# Estimate: each 5xx on payment endpoint costs $X in lost revenue
sum(rate(http_requests_total{endpoint="/api/payments", code=~"5.."}[1h]))
* 3600  # requests per hour
* 45    # average order value in USD

# User minutes lost to latency
# If p99 > SLO threshold, estimate user impact
count(http_request_duration_seconds_bucket{le="0.5"}) / count(http_request_duration_seconds_bucket)
* active_users_count

# Error budget remaining as business risk
(1 - (
  sum(rate(http_requests_total{code=~"5.."}[30d]))
  /
  sum(rate(http_requests_total[30d]))
)) / (1 - 0.999) * 100
# Returns % of error budget remaining
# < 20% = elevated business risk
```

### Revenue-Impacting Metrics Dashboard

```yaml
# Grafana dashboard JSON (simplified)
dashboard:
  title: "Business Impact Dashboard"
  panels:
    - title: "Revenue at Risk"
      type: stat
      targets:
        - expr: |
            sum(rate(http_requests_total{endpoint="/checkout", code=~"5.."}[1h]))
            * 3600 * 45
      thresholds:
        - value: 0
          color: green
        - value: 100
          color: yellow
        - value: 500
          color: red

    - title: "Error Budget Remaining"
      type: gauge
      targets:
        - expr: |
            (1 - sum(rate(http_requests_total{code=~"5.."}[30d])) / sum(rate(http_requests_total[30d])))
            / (1 - 0.999) * 100
      thresholds:
        - value: 0
          color: red
        - value: 20
          color: yellow
        - value: 50
          color: green

    - title: "Checkout Funnel by Latency Bucket"
      type: barchart
      targets:
        - expr: |
            sum by (le) (http_request_duration_seconds_bucket{endpoint="/checkout"})
```

### Business Metric Rules

- **Quantify revenue impact**: Translate technical SLIs into dollar amounts for executives
- **Track funnel metrics**: Monitor conversion at each step (browse → cart → checkout → payment)
- **Segment by geography and device**: Latency impact differs by region — SLOs may vary
- **Correlate incidents with business impact**: Postmortems must include revenue/user impact numbers
- **Set business-level SLOs**: "Checkout success rate > 99.95%" is more meaningful than "payment API availability > 99.9%"

---

## 7. SLO Dashboard Design

### RED Method (Request-Driven Services)

| Metric | Definition | Prometheus Query Pattern |
| --- | --- | --- |
| **Rate** | Requests per second | `sum(rate(http_requests_total[5m]))` |
| **Errors** | Failed requests per second | `sum(rate(http_requests_total{code=~"5.."}[5m]))` |
| **Duration** | Latency distribution | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))` |

### USE Method (Infrastructure Resources)

| Metric | Definition | Prometheus Query Pattern |
| --- | --- | --- |
| **Utilization** | % of resource capacity in use | `1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)` |
| **Saturation** | Queue depth or backlog | `node_load5 / count(node_cpu_seconds_total mode="idle") without(cpu)` |
| **Errors** | Error events per second | `rate(node_network_drop_total[5m])` |

### SLO Dashboard Template

```text
┌──────────────────────────────────────────────────────────┐
│  Service: [name]  │  SLO: [99.9%]  │  Window: [30d]     │
├──────────────────────────────────────────────────────────┤
│  Error Budget Remaining: [87.3%]  ████████░░░           │
│  Budget Exhausted At: [2026-05-15 at current rate]       │
├──────────────┬──────────────┬────────────────────────────┤
│  Availability │   Latency    │   Throughput               │
│  99.93% ✅   │  p99: 387ms │  1,247 req/s              │
│  SLO: 99.9%  │  SLO: <500ms │                            │
├──────────────┴──────────────┴────────────────────────────┤
│  [30-day latency heatmap]                                │
│  [Error budget burn rate trend]                          │
│  [Top 5 error endpoints by budget consumption]           │
└──────────────────────────────────────────────────────────┘
```

### Key Dashboard Queries

```promql
# SLO compliance over 30 days
100 * (1 -
  sum(rate(http_requests_total{code=~"5.."}[30d]))
  /
  sum(rate(http_requests_total[30d]))
)

# Error budget remaining (percentage)
100 * (1 -
  (
    sum(increase(http_requests_total{code=~"5.."}[30d]))
    /
    sum(increase(http_requests_total[30d]))
  )
  /
  (1 - 0.999)
)

# Top 5 error endpoints by budget consumption
topk(5,
  sum by (endpoint) (
    increase(http_requests_total{code=~"5.."}[7d])
  )
  /
  sum by (endpoint) (
    increase(http_requests_total[7d])
  )
)
```

---

## 8. SLO Review Process

### SLO Review Cadence

| Activity | Frequency | Participants | Output |
| --- | --- | --- | --- |
| SLO dashboard review | Weekly | On-call + tech lead | Incident trends, budget status |
| Error budget review | Monthly | Engineering + product | Feature vs. reliability prioritization |
| SLO target revision | Quarterly | Engineering + product + leadership | Updated SLO targets, new SLIs |
| SLA compliance audit | Annually | Legal + engineering + finance | SLA compliance report |

### Postmortem Integration

```markdown
## SLO Violation Postmortem Template

### SLO Violated
- SLI: [e.g., API availability]
- SLO Target: [e.g., 99.9%]
- Actual: [e.g., 99.7%]
- Duration: [e.g., 2h 15m]

### Error Budget Impact
- Budget consumed: [e.g., 23% of monthly budget in 2 hours]
- Budget remaining: [e.g., 12%]

### Business Impact
- Users affected: [estimated count]
- Revenue impact: [estimated dollar amount]
- Support tickets created: [count]

### Root Cause
[5 Whys analysis]

### Corrective Actions
1. [Action item] — Owner: [name] — Due: [date]
2. [Action item] — Owner: [name] — Due: [date]

### SLO Adjustment Needed?
- [ ] Current SLO is appropriate (no change)
- [ ] SLO should be tightened (system can support higher target)
- [ ] SLO should be relaxed (user expectation or system constraint changed)
```

### SLO Revision Triggers

- **Consistently achieving 100%**: SLO is too loose — tighten to create meaningful error budget
- **Consistently missing SLO**: SLO may be too aggressive, or systemic reliability issues need investment
- **User expectations changed**: Mobile users expect faster responses than desktop
- **Architecture changed**: Migration to new infrastructure may change achievable targets
- **Business requirements changed**: New revenue stream requires higher availability

---

## 9. Anti-Patterns

- **Setting 100% as SLO**: Impossible to achieve — 99.99% is the practical maximum, and even that needs careful SLI selection
- **Too many SLIs per service**: More than 5 SLIs dilutes focus — prioritize the ones that matter most to users
- **Averaging latency**: Averages hide tail latency — always use percentiles (p95, p99)
- **Ignoring error budget**: SLOs without consequence are aspirational, not operational — enforce budget policy
- **Copy-pasting SLOs across services**: Each service has different criticality — payment SLOs should be stricter than search
- **Measuring server-side latency only**: Users experience client-side latency — include network and rendering time
- **Not having separate SLOs for critical vs. non-critical paths**: Checkout must be more reliable than recommendations
- **Alerting on budget exhaustion, not burn rate**: By the time budget is exhausted, it is too late — alert on burn rate
- **Never reviewing SLOs**: SLOs should evolve — quarterly review minimum
- **Confusing SLI with SLO**: SLI is the metric, SLO is the target — "latency" is an SLI, "p99 < 500ms" is an SLO
- **Setting SLOs without historical data**: Guessing SLOs leads to unachievable targets — measure first, then set
