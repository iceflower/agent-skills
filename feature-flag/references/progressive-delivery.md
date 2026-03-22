# Progressive Delivery Strategies

## Overview

Progressive delivery extends continuous delivery by gradually rolling out changes to a subset of users or infrastructure, combining deployment strategies with feature flags for maximum control and minimal blast radius.

```text
Traditional:     Code → Build → Test → Deploy to ALL
Progressive:     Code → Build → Test → Deploy to FEW → Monitor → Expand → ALL
```

---

## 1. Canary Deployment with Feature Flags

### Architecture

```text
                    ┌─────────────────────┐
                    │    Load Balancer     │
                    └──────┬──────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
     ┌────────▼────────┐     ┌─────────▼─────────┐
     │  Stable (95%)   │     │  Canary (5%)       │
     │  v1.2.0         │     │  v1.3.0            │
     │                 │     │                    │
     │  Flag: OFF      │     │  Flag: ON (100%)   │
     │  (old behavior) │     │  (new behavior)    │
     └─────────────────┘     └────────────────────┘
```

### Two-Layer Control

Canary + feature flag provides two independent control layers:

| Layer | Controls | Rollback Speed | Granularity |
| --- | --- | --- | --- |
| Infrastructure (canary) | Which instances receive new code | Minutes (redeploy) | Per-instance |
| Feature flag | Which users see new behavior | Seconds (toggle) | Per-user |

### Deployment Flow

```text
Phase 1: Deploy canary (new code, flag OFF)
  └─▶ Verify deployment health (pod running, no crashes)

Phase 2: Enable flag for internal users on canary
  └─▶ Verify functionality with internal traffic

Phase 3: Enable flag for 5% of canary users
  └─▶ Monitor error rates, latency, business metrics

Phase 4: Enable flag for 100% of canary users
  └─▶ Canary carries 5% total traffic, all seeing new behavior

Phase 5: Expand canary to 25%, 50%, 100%
  └─▶ Gradually replace stable instances with new version

Phase 6: Enable flag globally (100% of all instances)
  └─▶ All users on new behavior, begin flag cleanup
```

### Rollback Scenarios

| Scenario | Action | Impact |
| --- | --- | --- |
| Bug in new code (crash, OOM) | Scale canary to 0, keep stable | 5% of users briefly affected |
| Bug in new feature logic | Disable feature flag | Instant, no redeployment needed |
| Performance degradation | Disable flag first, then investigate | Seconds to mitigate |
| Data corruption risk | Disable flag + scale down canary | Minimal blast radius |

### Kubernetes Canary with Argo Rollouts

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-service
spec:
  replicas: 10
  strategy:
    canary:
      steps:
        - setWeight: 5
        - pause: { duration: 10m }
        - analysis:
            templates:
              - templateName: success-rate
            args:
              - name: service-name
                value: my-service
        - setWeight: 25
        - pause: { duration: 10m }
        - analysis:
            templates:
              - templateName: success-rate
        - setWeight: 50
        - pause: { duration: 15m }
        - setWeight: 100
      canaryMetadata:
        labels:
          deployment: canary
      stableMetadata:
        labels:
          deployment: stable
```

### Analysis Template

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  args:
    - name: service-name
  metrics:
    - name: success-rate
      interval: 60s
      count: 5
      successCondition: result[0] >= 0.99
      failureLimit: 2
      provider:
        prometheus:
          address: http://prometheus.monitoring:9090
          query: |
            sum(rate(http_requests_total{
              service="{{args.service-name}}",
              status=~"2.."
            }[5m])) /
            sum(rate(http_requests_total{
              service="{{args.service-name}}"
            }[5m]))
```

---

## 2. Blue-Green Deployment with Feature Flags

### Blue-Green Architecture

```text
                    ┌─────────────────────┐
                    │    Load Balancer     │
                    │   (Traffic Switch)   │
                    └──────┬──────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
     ┌────────▼────────┐     ┌─────────▼─────────┐
     │   Blue (LIVE)   │     │   Green (IDLE)     │
     │   v1.2.0        │     │   v1.3.0           │
     │                 │     │                    │
     │  Flags: current │     │  Flags: new values │
     │  production     │     │  pre-configured    │
     └─────────────────┘     └────────────────────┘
```

### Blue-Green Deployment Flow

```text
Phase 1: Deploy to green environment
  └─▶ Green runs new code with feature flags pre-configured

Phase 2: Smoke test green environment
  └─▶ Run automated tests against green, flags enabled

Phase 3: Switch traffic (blue → green)
  └─▶ Load balancer points to green, blue becomes idle

Phase 4: Monitor green (now live)
  └─▶ Watch metrics, ready to switch back to blue

Phase 5: Gradual flag rollout on green
  └─▶ New features enabled progressively for users

Phase 6: Decommission blue
  └─▶ Blue environment available for next deployment
```

### Feature Flag Benefits in Blue-Green

| Without Flags | With Flags |
| --- | --- |
| All-or-nothing switch | Gradual feature enablement after switch |
| Rollback = switch back to blue | Rollback = disable flag (keep green live) |
| Test new features only in green | Test features independently of deployment |
| One release per switch | Multiple features released independently |

### Blue-Green with Feature Flags: Decision Matrix

| Situation | Approach |
| --- | --- |
| New infrastructure/dependency change | Blue-green switch (need new code running) |
| New user-facing feature | Feature flag (can deploy code anytime) |
| Both infra + feature change | Blue-green switch, then feature flag rollout |
| Urgent rollback needed | Disable feature flag first (seconds), then consider blue-green switch if code-level issue |

---

## 3. Percentage Rollout Strategy

### Consistent Hashing

Use consistent hashing to ensure users get a stable experience during percentage rollouts.

```text
User ID: "user-123"
Flag Key: "release.checkout.new-flow"

Hash = murmur3("user-123" + "release.checkout.new-flow") % 100
     = 42

If rollout percentage >= 42 → user sees new feature
If rollout percentage <  42 → user sees old feature
```

### Rollout Schedule Template

| Phase | Percentage | Duration | Gate Criteria |
| --- | --- | --- | --- |
| Smoke | 1% | 24 hours | No errors, no crashes |
| Early | 5% | 24-48 hours | Error rate < baseline + 0.1% |
| Expand | 10% | 48 hours | Latency p99 < baseline + 10% |
| Broad | 25% | 48 hours | Business metrics stable |
| Majority | 50% | 72 hours | All metrics within thresholds |
| Full | 100% | — | Begin flag cleanup |

### Automated Rollout with Metrics

```typescript
interface RolloutConfig {
  flag: string;
  schedule: RolloutPhase[];
  rollbackThresholds: {
    errorRateIncrease: number;    // e.g., 0.001 (0.1%)
    latencyP99Increase: number;   // e.g., 1.1 (10% increase)
    conversionDrop: number;       // e.g., 0.02 (2% drop)
  };
}

interface RolloutPhase {
  percentage: number;
  minDuration: string;            // e.g., "24h", "48h"
  gateMetrics: string[];          // Metrics to check before advancing
}

// Example configuration
const rolloutConfig: RolloutConfig = {
  flag: 'release.checkout.new-payment-flow',
  schedule: [
    { percentage: 1,   minDuration: '24h', gateMetrics: ['error_rate', 'crash_rate'] },
    { percentage: 5,   minDuration: '24h', gateMetrics: ['error_rate', 'latency_p99'] },
    { percentage: 10,  minDuration: '48h', gateMetrics: ['error_rate', 'latency_p99'] },
    { percentage: 25,  minDuration: '48h', gateMetrics: ['error_rate', 'latency_p99', 'conversion'] },
    { percentage: 50,  minDuration: '72h', gateMetrics: ['error_rate', 'latency_p99', 'conversion'] },
    { percentage: 100, minDuration: '0',   gateMetrics: [] },
  ],
  rollbackThresholds: {
    errorRateIncrease: 0.001,
    latencyP99Increase: 1.1,
    conversionDrop: 0.02,
  },
};
```

---

## 4. Ring-Based Deployment

### Ring Structure

```text
┌──────────────────────────────────────────────────────┐
│                     Ring 3: All Users                 │
│  ┌───────────────────────────────────────────────┐   │
│  │              Ring 2: Early Adopters            │   │
│  │  ┌────────────────────────────────────────┐   │   │
│  │  │         Ring 1: Beta Testers           │   │   │
│  │  │  ┌─────────────────────────────────┐   │   │   │
│  │  │  │    Ring 0: Internal / Canary    │   │   │   │
│  │  │  └─────────────────────────────────┘   │   │   │
│  │  └────────────────────────────────────────┘   │   │
│  └───────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

### Ring Definition

| Ring | Audience | Size | Purpose |
| --- | --- | --- | --- |
| Ring 0 | Internal team, dogfooding | < 1% | Catch obvious issues early |
| Ring 1 | Beta testers, opt-in users | 1-5% | Validate with engaged users |
| Ring 2 | Early adopters, specific regions | 5-25% | Broader validation |
| Ring 3 | All users | 100% | General availability |

### Feature Flag Mapping

```json
{
  "flag": "release.search.new-algorithm",
  "rings": {
    "ring-0": {
      "segment": "internal-staff",
      "percentage": 100,
      "promotion_criteria": {
        "min_duration": "24h",
        "error_rate_threshold": 0.001
      }
    },
    "ring-1": {
      "segment": "beta-testers",
      "percentage": 100,
      "promotion_criteria": {
        "min_duration": "48h",
        "error_rate_threshold": 0.001,
        "latency_p99_threshold_ms": 200
      }
    },
    "ring-2": {
      "segment": "early-adopters",
      "percentage": 100,
      "promotion_criteria": {
        "min_duration": "72h",
        "error_rate_threshold": 0.001,
        "business_metric_threshold": 0.98
      }
    },
    "ring-3": {
      "segment": "all-users",
      "percentage": 100
    }
  }
}
```

---

## 5. A/B Testing Integration

### Feature Flags for A/B Tests

```text
┌─────────────────┐
│  User Request    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  Flag Evaluation │────▶│  Variant A (50%) │──▶ Track: conversion_a
│  (experiment     │     └──────────────────┘
│   toggle)        │
│                  │     ┌──────────────────┐
│                  │────▶│  Variant B (50%) │──▶ Track: conversion_b
└─────────────────┘     └──────────────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │  Analytics        │
                        │  Statistical      │
                        │  Significance     │
                        └──────────────────┘
```

### A/B Test Flag Configuration

```json
{
  "flag": "experiment.checkout.button-color",
  "category": "experiment",
  "variants": {
    "control": { "value": "blue", "weight": 50 },
    "treatment": { "value": "green", "weight": 50 }
  },
  "metrics": {
    "primary": "checkout_conversion_rate",
    "secondary": ["click_through_rate", "time_to_checkout"],
    "guardrail": ["error_rate", "page_load_time"]
  },
  "experiment": {
    "hypothesis": "Green checkout button increases conversion by 5%",
    "minimum_sample_size": 10000,
    "significance_level": 0.05,
    "minimum_detectable_effect": 0.02,
    "start_date": "2026-03-15",
    "planned_end_date": "2026-04-15"
  }
}
```

### Rules for A/B Tests

- Define hypothesis and success criteria BEFORE starting the experiment
- Calculate minimum sample size before launch to ensure statistical power
- Use guardrail metrics to catch negative side effects
- Do not peek at results and make early decisions — wait for statistical significance
- Ensure consistent assignment (same user always sees same variant)
- Log every flag evaluation with the assigned variant for analytics
- After experiment conclusion, either promote the winner or remove the flag

---

## 6. Monitoring and Observability

### Key Metrics to Track

| Metric Category | Metrics | Alert Threshold |
| --- | --- | --- |
| Reliability | Error rate, crash rate | > baseline + 0.1% |
| Performance | Latency p50, p95, p99 | > baseline + 10% |
| Business | Conversion, revenue, engagement | < baseline - 2% |
| Flag health | Evaluation count, error count | Sudden drop or spike |

### Dashboard Layout

```text
┌─────────────────────────────────────────────────────────────┐
│  Feature Flag: release.checkout.new-payment-flow            │
│  Status: Rolling out (25%)  │  Owner: team-payments         │
├─────────────────────────────┬───────────────────────────────┤
│  Error Rate                 │  Latency P99                  │
│  ▁▁▁▁▁▁▁▁▂▁▁▁▁▁▁          │  ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁            │
│  Flag ON:  0.12%           │  Flag ON:  142ms              │
│  Flag OFF: 0.11%           │  Flag OFF: 138ms              │
├─────────────────────────────┼───────────────────────────────┤
│  Conversion Rate            │  Rollout Progress             │
│  ▁▁▁▂▂▂▂▂▃▃▃              │  ████████░░░░░░░░  25%       │
│  Flag ON:  3.4%            │  Phase: Expand                │
│  Flag OFF: 3.2%            │  Next gate: 48h remaining     │
├─────────────────────────────┴───────────────────────────────┤
│  Recent Events                                              │
│  [12:00] Rollout advanced from 10% to 25%                  │
│  [11:45] All gate metrics passed for 10% phase             │
│  [09:30] Rollout advanced from 5% to 10%                   │
└─────────────────────────────────────────────────────────────┘
```

### Automated Rollback Trigger

```yaml
# Example: Prometheus alerting rule for flag rollback
groups:
  - name: feature-flag-rollback
    rules:
      - alert: FeatureFlagErrorRateHigh
        expr: |
          (
            sum(rate(http_errors_total{feature_flag="on"}[5m]))
            /
            sum(rate(http_requests_total{feature_flag="on"}[5m]))
          ) > 1.1 * (
            sum(rate(http_errors_total{feature_flag="off"}[5m]))
            /
            sum(rate(http_requests_total{feature_flag="off"}[5m]))
          )
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Feature flag error rate exceeds baseline by 10%"
          action: "Disable feature flag or reduce rollout percentage"
```

---

## 7. Progressive Delivery Decision Framework

### When to Use Which Strategy

| Scenario | Recommended Strategy |
| --- | --- |
| New user-facing feature | Feature flag percentage rollout |
| Infrastructure change (DB, messaging) | Canary deployment |
| Major UI redesign | Feature flag + canary |
| Performance optimization | Canary with A/B comparison |
| Compliance/regulatory change | Blue-green (all-or-nothing required) |
| Multi-region rollout | Ring-based deployment |
| Pricing/monetization change | Feature flag with segment targeting |

### Risk Assessment Matrix

| Risk Level | Blast Radius | Strategy | Monitoring |
| --- | --- | --- | --- |
| Low | Single feature, non-critical | Flag percentage rollout | Standard metrics |
| Medium | Critical path, revenue-impacting | Canary + flag | Enhanced monitoring |
| High | Data model change, multi-service | Blue-green + flag + canary | Full observability |
| Critical | Payment, auth, compliance | Blue-green + manual gates | War room monitoring |
