---
name: observability
description: >-
  Modern observability and monitoring patterns centered on OpenTelemetry (OTel).
  Covers the three pillars (traces, metrics, logs) with context propagation,
  OTel SDK architecture, OTLP protocol, distributed tracing with W3C Trace Context,
  metric instrument types (Counter, Histogram, Gauge, Timer, Exemplars),
  key metrics to monitor (application, business, infrastructure),
  metric naming conventions, log correlation, OTel Collector pipelines,
  Semantic Conventions, backend integration (Jaeger, Grafana Tempo, Loki, Prometheus),
  alerting rules, and health check patterns (liveness, readiness, startup).
  Use when implementing distributed tracing, setting up OTel instrumentation,
  configuring Collector pipelines, designing alerting strategies,
  implementing health checks, or integrating observability backends.
license: MIT
metadata:
  author: iceflower
  version: "2.0"
  last-reviewed: "2026-03"
---

# Observability Rules (OpenTelemetry)

## 1. Core Concepts

OpenTelemetry provides a unified standard for collecting telemetry data.

### Three Pillars + Context

| Signal | Purpose | Role in Debugging |
| --- | --- | --- |
| **Traces** | Request flow across services | Where it went wrong (which service/span) |
| **Metrics** | Aggregated measurements over time | Something is wrong (alert trigger) |
| **Logs** | Discrete event records | What went wrong (error details) |
| **Context** | Correlates all signals via trace ID, span ID | Connect all three for correlated debugging |

### Architecture

```text
[Application + OTel SDK]
    |-- API (instrumentation interface)
    |-- SDK (implementation: sampling, batching, export)
    |-- Auto-instrumentation (zero-code)
         |
    [OTel Collector] (optional but recommended)
    |-- Receivers  → Processors → Exporters
         |
    [Backends: Jaeger, Tempo, Prometheus, Loki]
```

### OTLP Protocol

| Transport | Port | Use Case |
| --- | --- | --- |
| gRPC | 4317 | Default, binary protobuf |
| HTTP | 4318 | Firewalls, load balancers |

Endpoints: `/v1/traces`, `/v1/metrics`, `/v1/logs`

## 2. Distributed Tracing

### Span Structure

A span represents a unit of work with:

- **Span Context**: trace ID, span ID, trace flags (immutable)
- **Attributes**: key-value metadata (`http.request.method`, `db.system`)
- **Events**: timestamped annotations within the span
- **Links**: causal relationships to other spans (async flows)
- **Status**: Unset (default), Error, Ok

### SpanKind

| Kind | Direction | Example |
| --- | --- | --- |
| Client | Outbound sync | HTTP client, DB client |
| Server | Inbound sync | HTTP server handler |
| Internal | In-process | Business logic |
| Producer | Outbound async | Queue publish |
| Consumer | Inbound async | Queue consume |

### W3C Trace Context Propagation

```text
traceparent: 00-<trace-id>-<span-id>-<trace-flags>
tracestate:  vendor-specific data
```

- Default propagator in OTel
- Inject on outgoing requests, extract on incoming
- Never propagate internal trace data to untrusted external services
- Never put sensitive data in Baggage

### Instrumentation Approaches

| Approach | Effort | Coverage |
| --- | --- | --- |
| Auto (zero-code) | None | Frameworks, HTTP, DB, messaging |
| Manual (code-based) | Medium | Custom business logic spans |
| Library instrumentation | Low | Third-party library support |

**Rule**: Start with auto-instrumentation, add manual spans only for
business-critical operations that auto-instrumentation doesn't cover.

## 3. Metrics

### Instrument Types

| Type | Monotonic | Sync | Use Case |
| --- | --- | --- | --- |
| Counter | Yes | Sync | Request count, bytes sent |
| UpDownCounter | No | Sync | Queue size, active connections |
| Histogram | N/A | Sync | Request duration, response size |
| Gauge | N/A | Sync | CPU temperature, memory usage |
| Observable* | Varies | Async | Collected once per export cycle |

> **Timer note**: Some frameworks (e.g., Micrometer) provide a Timer type
> that combines duration measurement with count. In OTel, use a Histogram
> instrument for the same purpose (e.g., `http.server.request.duration`).

### Exemplars

Link metrics to traces for drill-down from aggregated data to individual requests.

- Attach trace ID / span ID to metric measurements
- Configure with `TraceBased` exemplar filter
- Visualized as diamond markers in Grafana
- Enables: "This p99 latency spike → show me the exact trace"

### Views

Customize metric processing per instrument:

- Select which instruments to process
- Override aggregation strategy (e.g., explicit bucket histogram)
- Filter or rename attributes
- Set aggregation temporality

### Metric Naming Convention

```text
# OTel standard: dot-separated, lowercase, include unit
http.server.request.duration
db.client.operation.duration

# Domain-specific pattern: <domain>.<entity>.<action>
orders.created.total
payments.processing.duration
users.active.count
cache.hits.total
```

Use standard units: `s` (seconds), `By` (bytes), `{request}` (count).

### Key Metrics to Monitor

#### Application Metrics

| Metric | Alert Threshold | Severity |
| --- | --- | --- |
| HTTP error rate (5xx) | > 1% of requests | Critical |
| HTTP P99 latency | > 3x baseline | Warning |
| Heap/memory usage | > 85% | Warning |
| GC pause time | > 500ms | Warning |
| Thread pool active threads | > 90% capacity | Warning |
| DB connection pool exhaustion | > 90% used | Critical |

#### Business Metrics

| Metric | Purpose |
| --- | --- |
| Orders per minute | Business throughput |
| Payment success rate | Revenue impact |
| User login rate | Traffic pattern |
| API call count by endpoint | Usage analytics |

#### Infrastructure Metrics

| Metric | Alert Threshold |
| --- | --- |
| CPU usage | > 80% sustained |
| Memory usage | > 85% |
| Disk I/O | > 80% utilization |
| Pod restart count | > 0 unexpected |

## 4. Logs

OTel does not replace existing logging frameworks. It bridges them.

### Integration Pattern

```text
[Application Code]
    → [Logging Framework (Logback, Log4j, winston)]
        → [OTel Log Appender/Bridge]
            → [OTel SDK LogRecordProcessor]
                → [OTel Collector or Backend]
```

### Log-Trace Correlation

When OTel SDK is active, trace ID and span ID are automatically injected
into log records. No code changes required.

```json
{
  "timestamp": "2026-03-24T10:30:00Z",
  "severity": "ERROR",
  "body": "Payment processing failed",
  "traceId": "abc123...",
  "spanId": "def456...",
  "attributes": {
    "user.id": "42",
    "order.id": "ORD-789"
  }
}
```

### Log Rules

- Use structured logging (JSON) for machine readability
- Let OTel SDK inject trace context automatically
- Do not call the Logs Bridge API directly from application code
- Configure log appenders for your framework (Logback, Log4j2, Python logging)

## 5. OTel Collector

The Collector is a vendor-agnostic proxy that receives, processes, and exports
telemetry data. For detailed pipeline configuration, see
[references/otel-collector.md](references/otel-collector.md).

### Deployment Patterns

| Pattern | Description | When to Use |
| --- | --- | --- |
| No Collector | App exports directly to backend | Dev/test only |
| Agent (sidecar) | Collector beside each service | Fast offloading, local processing |
| Gateway | Centralized Collector cluster | Multi-source collection, routing |

**Recommendation**: Use Agent mode in production for reliability. Gateway mode
for cross-cluster aggregation and routing.

### Essential Processors

| Processor | Purpose |
| --- | --- |
| `batch` | Buffer and send in batches (reduces network overhead) |
| `memory_limiter` | Prevent OOM (always configure — set `limit_mib` to ~80% of container memory) |
| `attributes` | Add, update, delete, hash attributes |
| `filter` | Drop unwanted telemetry |
| `tail_sampling` | Sample based on complete trace (Collector only) |
| `resource` | Add resource attributes |

## 6. Semantic Conventions

Use standard attribute names for interoperability across tools and dashboards.
For the full convention list, see
[references/semantic-conventions.md](references/semantic-conventions.md).

### Key Conventions (Summary)

| Domain | Key Attributes |
| --- | --- |
| HTTP | `http.request.method`, `http.response.status_code`, `url.path`, `http.route` |
| Database | `db.system`, `db.operation.name`, `db.collection.name` |
| Messaging | `messaging.system`, `messaging.operation.type`, `messaging.destination.name` |
| RPC | `rpc.system`, `rpc.service`, `rpc.method` |

## 7. SDK Patterns

For detailed setup examples by language (Java, Node.js, Python), see
[references/otel-sdk-patterns.md](references/otel-sdk-patterns.md).

### Quick Reference

| Language | Zero-Code | Manual |
| --- | --- | --- |
| Java | `-javaagent:opentelemetry-javaagent.jar` | `GlobalOpenTelemetry.getTracer()` |
| Java (Spring Boot 4.0+) | `spring-boot-starter-opentelemetry` | Spring-integrated config |
| Node.js | `@opentelemetry/auto-instrumentations-node` | `trace.getTracer()` |
| Python | `opentelemetry-instrument` CLI | `trace.get_tracer()` |

## 8. Backend Integration

### Recommended Stack (Grafana)

```text
Traces  → Grafana Tempo  (OTLP native)
Metrics → Prometheus      (OTLP receiver or remote write)
Logs    → Grafana Loki    (OTLP native, Loki 3.0+)
UI      → Grafana         (unified query across all signals)
```

### Jaeger

- Jaeger v2 uses OTel Collector as its core pipeline
- OTLP endpoints: gRPC `4317`, HTTP `4318`
- `jaegertracing/all-in-one` Docker image for dev

### Prometheus OTLP

```bash
# Enable OTLP receiver
prometheus --web.enable-otlp-receiver
```

```bash
# OTel SDK environment variables
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://localhost:9090/api/v1/otlp/v1/metrics
```

## 9. Alerting

Design alerts around symptoms, not causes. For detailed alerting rules,
severity levels, and templates, see
[references/alerting-rules.md](references/alerting-rules.md).

### Key Principles

- Alert on symptoms (error rate, latency), not causes (CPU, memory)
- Every alert must have a runbook or action item
- Avoid alert fatigue — only alert on actionable conditions
- Use multi-window or burn-rate alerts over simple thresholds
- Include context in alert messages (service, environment, metric value)

### Alert Severity Summary

| Level | Response Time | Example |
| --- | --- | --- |
| Critical | Immediate | Service down, data loss risk |
| Warning | Within 1 hour | Degraded performance |
| Info | Next business day | Approaching threshold |

## 10. Health Checks

Health checks enable orchestrators (Kubernetes, load balancers) to manage
application lifecycle. For detailed probe configuration and rules, see
[references/health-checks.md](references/health-checks.md).

### Probe Types

| Probe | Check | External Dependencies |
| --- | --- | --- |
| Liveness | App is running | No |
| Readiness | App can serve traffic | Yes (DB, cache) |
| Startup | App initialization done | Yes |

### Key Rules

- Liveness probes must be lightweight — no external dependency checks
- Readiness probes should verify critical dependencies
- Never put slow checks in liveness probes (causes unnecessary restarts)
- Health checks must not cause side effects (writes, external calls)

## 11. Common Anti-Patterns

| Anti-Pattern | Problem | Fix |
| --- | --- | --- |
| No sampling in production | Storage explosion | Use head or tail sampling |
| High-cardinality attributes in metrics | Metric/index explosion | Limit metric attribute values, use Views to filter |
| Sensitive data in spans | Security/compliance risk | Redact PII with attribute processor |
| Skipping Collector | No buffering, sampling, or routing | Deploy Collector in Agent mode |
| Ignoring Semantic Conventions | Inconsistent dashboards/alerts | Follow OTel standard names |
| No `memory_limiter` processor | Collector OOM | Always configure memory limits |
| Manual trace propagation | Broken traces, missing context | Use SDK auto-propagation |
| Logging trace ID manually | Duplicate/inconsistent IDs | Let OTel SDK inject automatically |
| Alerting on every error | Alert fatigue | Alert on error rate instead |
| Missing traceId in logs | Breaks correlation | Enable OTel log bridge |
| Dashboard with 50+ panels | Information overload | Focus on key signals per dashboard |
| No baseline metrics | Cannot detect regressions | Establish baselines before alerting |
| Monitoring only infra, not business | Miss revenue-impacting issues | Add business metrics |

## 12. Related Skills

- `logging`: Structured logging and monitoring integration
- `incident-response`: Alert-driven incident response processes
- `troubleshooting`: Monitoring data-driven problem diagnosis
- `spring-framework`: Spring Boot Actuator and Micrometer metrics
- `slo`: Service level objectives and error budgets

## Additional References

- For PromQL examples, recording rules, and common query patterns, see [references/prometheus-queries.md](references/prometheus-queries.md)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/) - Official OpenTelemetry documentation
- [Prometheus Documentation](https://prometheus.io/docs/) - Official Prometheus documentation
- [Google SRE Book - Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/) - Monitoring distributed systems
- For Spring Boot implementation patterns (Actuator, Micrometer, distributed tracing), see `spring-framework` skill — [references/monitoring.md](../spring-framework/references/monitoring.md)
