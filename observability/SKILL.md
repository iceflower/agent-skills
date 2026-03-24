---
name: observability
description: >-
  Modern observability patterns centered on OpenTelemetry (OTel).
  Covers OTel SDK architecture, OTLP protocol, distributed tracing with
  W3C Trace Context, metrics (Counter, Histogram, Gauge, Exemplars),
  log correlation, OTel Collector pipelines, Semantic Conventions,
  and backend integration (Jaeger, Grafana Tempo, Loki, Prometheus).
  Use when implementing distributed tracing, setting up OTel instrumentation,
  configuring Collector pipelines, or integrating observability backends.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# Observability Rules (OpenTelemetry)

## 1. Core Concepts

OpenTelemetry provides a unified standard for collecting telemetry data.

### Three Pillars + Context

| Signal | Purpose | Example |
| --- | --- | --- |
| **Traces** | Request flow across services | HTTP request → DB query → cache lookup |
| **Metrics** | Aggregated measurements | Request count, latency histogram |
| **Logs** | Discrete events | Error messages, audit records |
| **Context** | Correlates all signals | trace ID, span ID propagated across services |

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

### Rules

- Use structured logging (JSON) for machine readability
- Let OTel SDK inject trace context automatically
- Do not call the Logs Bridge API directly from application code
- Configure log appenders for your framework (Logback, Log4j2, Python logging)

## 5. OTel Collector

### Pipeline Architecture

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 5s
    send_batch_size: 8192
  memory_limiter:
    check_interval: 1s
    limit_mib: 512
  attributes:
    actions:
      - key: environment
        value: production
        action: upsert

exporters:
  otlp/tempo:
    endpoint: tempo:4317
    tls:
      insecure: true
  prometheusremotewrite:
    endpoint: http://prometheus:9090/api/v1/write
  otlphttp/loki:
    endpoint: http://loki:3100/otlp

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/tempo]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheusremotewrite]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch, attributes]
      exporters: [otlphttp/loki]
```

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

### HTTP

| Attribute | Example |
| --- | --- |
| `http.request.method` | `GET`, `POST` |
| `http.response.status_code` | `200`, `500` |
| `url.scheme` | `https` |
| `url.path` | `/api/users` |
| `server.address` | `api.example.com` |
| `http.route` | `/api/users/{id}` (auto-set by Spring `@RequestMapping`, Express route patterns) |

### Database

| Attribute | Example |
| --- | --- |
| `db.system` | `postgresql`, `mysql`, `redis` |
| `db.operation.name` | `SELECT`, `INSERT` |
| `db.collection.name` | `users` |
| `server.address` | `db.example.com` |
| `server.port` | `5432` |

### Messaging

| Attribute | Example |
| --- | --- |
| `messaging.system` | `kafka`, `rabbitmq` |
| `messaging.operation.type` | `publish`, `receive` |
| `messaging.destination.name` | `orders-topic` |

For the full convention list, see
[references/semantic-conventions.md](references/semantic-conventions.md).

## 7. SDK Patterns by Language

For detailed setup examples, see
[references/otel-sdk-patterns.md](references/otel-sdk-patterns.md).

### Java (Spring Boot)

- **Zero-code**: `-javaagent:opentelemetry-javaagent.jar`
- **Spring Boot Starter**: `spring-boot-starter-opentelemetry` (Boot 4.0+)
- Use Java agent for broader coverage; Starter for Native Image or Spring-integrated config

### Node.js

```typescript
import { NodeSDK } from "@opentelemetry/sdk-node";
const sdk = new NodeSDK({ /* config */ });
sdk.start();
```

### Python

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
trace.set_tracer_provider(TracerProvider())
```

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

## 9. Common Anti-Patterns

| Anti-Pattern | Problem | Fix |
| --- | --- | --- |
| No sampling in production | Storage explosion | Use head or tail sampling |
| High-cardinality attributes (e.g., user ID, request ID in metrics) | Metric/index explosion (traces can tolerate high cardinality; metrics cannot) | Limit metric attribute values, use Views to filter |
| Sensitive data in spans | Security/compliance risk | Redact PII with attribute processor |
| Skipping Collector | No buffering, sampling, or routing | Deploy Collector in Agent mode |
| Ignoring Semantic Conventions | Inconsistent dashboards/alerts | Follow OTel standard names |
| No `memory_limiter` processor | Collector OOM | Always configure memory limits |
| Manual trace propagation | Broken traces, missing context | Use SDK auto-propagation |
| Logging trace ID manually | Duplicate/inconsistent IDs | Let OTel SDK inject automatically |
