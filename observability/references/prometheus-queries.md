# Prometheus Queries (PromQL)

Practical PromQL examples, recording rules, and common query patterns for application and infrastructure monitoring.

## Overview

PromQL is the query language for Prometheus. It enables selecting, aggregating, and transforming time-series data collected from instrumented applications and infrastructure.

## PromQL Fundamentals

### Selectors

```promql
# Instant vector: current value
http_requests_total{method="GET", status="200"}

# Range vector: values over time window
http_requests_total{method="GET"}[5m]

# Regex matching
http_requests_total{status=~"5.."}       # all 5xx
http_requests_total{path!~"/health.*"}   # exclude health checks
```

### Common Functions

```promql
# Rate: per-second average over time window (use with counters)
rate(http_requests_total[5m])

# Increase: total increase over time window
increase(http_requests_total[1h])

# Histogram quantile
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# Aggregation
sum(rate(http_requests_total[5m])) by (service)
avg(node_cpu_seconds_total{mode="idle"}) by (instance)
topk(5, rate(http_requests_total[5m]))
```

## Application Monitoring Queries

### RED Method (Rate, Errors, Duration)

```promql
# Request Rate (per second)
sum(rate(http_server_requests_seconds_count[5m])) by (service)

# Error Rate (percentage)
sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m]))
/
sum(rate(http_server_requests_seconds_count[5m]))

# Duration (p50, p95, p99)
histogram_quantile(0.50, sum(rate(http_server_requests_seconds_bucket[5m])) by (le, service))
histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket[5m])) by (le, service))
histogram_quantile(0.99, sum(rate(http_server_requests_seconds_bucket[5m])) by (le, service))
```

### USE Method (Utilization, Saturation, Errors) for Resources

```promql
# CPU Utilization
1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) by (instance)

# Memory Utilization
1 - (node_memory_AvailableBytes / node_memory_MemTotalBytes)

# Disk I/O Saturation
rate(node_disk_io_time_weighted_seconds_total[5m])

# Network Errors
rate(node_network_receive_errs_total[5m])
rate(node_network_transmit_errs_total[5m])
```

### JVM Application Metrics

```promql
# Heap memory usage
jvm_memory_used_bytes{area="heap"}
/ jvm_memory_max_bytes{area="heap"}

# GC pause time (p99)
histogram_quantile(0.99, rate(jvm_gc_pause_seconds_bucket[5m]))

# GC frequency
rate(jvm_gc_pause_seconds_count[5m])

# Thread count
jvm_threads_live_threads

# Connection pool usage
hikaricp_connections_active / hikaricp_connections_max
```

## Infrastructure Queries

### Kubernetes

```promql
# Pod CPU usage
sum(rate(container_cpu_usage_seconds_total{namespace="production"}[5m])) by (pod)

# Pod memory usage
sum(container_memory_working_set_bytes{namespace="production"}) by (pod)

# Pod restart count
increase(kube_pod_container_status_restarts_total[1h])

# Node resource pressure
kube_node_status_condition{condition="MemoryPressure", status="true"}
kube_node_status_condition{condition="DiskPressure", status="true"}

# Deployment replica mismatch
kube_deployment_spec_replicas - kube_deployment_status_ready_replicas > 0
```

### Database

```promql
# Active connections
pg_stat_activity_count{state="active"}

# Connection pool utilization
pg_stat_activity_count / pg_settings_max_connections

# Slow queries (> 1 second)
rate(pg_stat_activity_max_tx_duration{state="active"}[5m])

# Replication lag
pg_replication_lag_seconds
```

## Recording Rules

Pre-compute expensive queries for dashboard performance and alerting.

```yaml
groups:
  - name: http_recording_rules
    interval: 30s
    rules:
      # Request rate by service
      - record: service:http_requests:rate5m
        expr: sum(rate(http_server_requests_seconds_count[5m])) by (service)

      # Error rate by service
      - record: service:http_errors:ratio5m
        expr: |
          sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m])) by (service)
          /
          sum(rate(http_server_requests_seconds_count[5m])) by (service)

      # P99 latency by service
      - record: service:http_latency:p99_5m
        expr: |
          histogram_quantile(0.99,
            sum(rate(http_server_requests_seconds_bucket[5m])) by (le, service)
          )

  - name: resource_recording_rules
    interval: 60s
    rules:
      # CPU utilization by instance
      - record: instance:cpu:utilization5m
        expr: 1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) by (instance)

      # Memory utilization by instance
      - record: instance:memory:utilization
        expr: 1 - (node_memory_AvailableBytes / node_memory_MemTotalBytes)
```

## Alerting Rules

```yaml
groups:
  - name: application_alerts
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: service:http_errors:ratio5m > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on {{ $labels.service }}"
          description: "Error rate is {{ $value | humanizePercentage }} (> 5%)"

      # High latency
      - alert: HighLatency
        expr: service:http_latency:p99_5m > 1.0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High p99 latency on {{ $labels.service }}"
          description: "P99 latency is {{ $value | humanizeDuration }}"

      # Pod crash looping
      - alert: PodCrashLooping
        expr: increase(kube_pod_container_status_restarts_total[1h]) > 3
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Pod {{ $labels.pod }} is crash looping"
```

## Query Optimization Tips

| Problem | Solution |
| --- | --- |
| Slow dashboard loading | Use recording rules for complex aggregations |
| High cardinality labels | Avoid labels with unbounded values (user IDs) |
| `rate()` returns nothing | Ensure range window > 2x scrape interval |
| Missing data points | Check `up` metric and scrape config |
| Counter resets on restart | Use `rate()` or `increase()`, not raw values |

### Range Window Selection

```text
Scrape interval: 15s

Minimum range window: 4 * scrape_interval = 60s
Recommended for rate(): [5m] (covers at least 2 samples even with missed scrapes)
```
