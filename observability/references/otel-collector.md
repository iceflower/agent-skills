# OTel Collector Pipeline Configuration

Detailed configuration reference for OpenTelemetry Collector pipelines.

## Pipeline Architecture

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

## Deployment Patterns

### No Collector (Direct Export)

```text
[App + OTel SDK] → [Backend]
```

- Suitable for dev/test only
- No buffering, sampling, or routing capabilities
- Application bears the export overhead

### Agent Mode (Sidecar)

```text
[App] → [Collector Sidecar] → [Backend]
```

- Collector runs alongside each service instance
- Fast offloading from the application
- Local processing (attribute enrichment, filtering)
- Recommended for production

### Gateway Mode

```text
[App] → [Collector Agent] → [Collector Gateway] → [Backend]
```

- Centralized Collector cluster receives from multiple agents
- Cross-cluster aggregation and routing
- Tail sampling requires gateway mode (needs complete traces)

## Essential Processors

### batch

Buffer telemetry and send in batches to reduce network overhead.

```yaml
processors:
  batch:
    timeout: 5s           # Max wait time before sending
    send_batch_size: 8192  # Max items per batch
    send_batch_max_size: 0 # 0 = unlimited
```

### memory_limiter

Prevent Collector OOM. **Always configure this processor.**

```yaml
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 512        # ~80% of container memory
    spike_limit_mib: 128  # Additional buffer for spikes
```

### attributes

Add, update, delete, or hash span/metric/log attributes.

```yaml
processors:
  attributes:
    actions:
      - key: environment
        value: production
        action: upsert
      - key: internal.debug
        action: delete
      - key: user.email
        action: hash  # Hash PII for privacy
```

### filter

Drop unwanted telemetry to reduce storage costs.

```yaml
processors:
  filter:
    error_mode: ignore
    traces:
      span:
        - 'attributes["http.route"] == "/health"'
    metrics:
      metric:
        - 'name == "http.server.duration" and resource.attributes["service.name"] == "debug-service"'
```

### tail_sampling

Sample based on complete trace data (requires Gateway mode).

```yaml
processors:
  tail_sampling:
    decision_wait: 30s
    policies:
      - name: error-policy
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: slow-policy
        type: latency
        latency: { threshold_ms: 1000 }
      - name: default
        type: probabilistic
        probabilistic: { sampling_percentage: 10 }
```

## Processor Ordering

Order matters. Recommended pipeline order:

```text
memory_limiter → [attributes/filter/transform] → batch → exporter
```

- `memory_limiter` first: prevents OOM before any processing
- `batch` last (before exporter): maximizes batching efficiency

## Resources

- [OTel Collector Configuration](https://opentelemetry.io/docs/collector/configuration/)
- [Collector Processors](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor)
