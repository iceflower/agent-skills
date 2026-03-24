# Alerting Rules

Detailed alerting design guidelines, severity levels, and templates for production monitoring.

## Alert Severity Levels

| Level | Response Time | Example | Notification |
| --- | --- | --- | --- |
| Critical | Immediate | Service down, data loss risk | PagerDuty / on-call page |
| Warning | Within 1 hour | Degraded performance | Slack channel |
| Info | Next business day | Approaching threshold | Dashboard only |

## Alert Design Principles

- **Alert on symptoms, not causes**: Alert on error rate and latency, not CPU or memory directly. High CPU is not a problem if users are unaffected.
- **Every alert must be actionable**: If there is no runbook or clear action, it should not be an alert.
- **Avoid alert fatigue**: Too many alerts desensitize responders. Consolidate and deduplicate.
- **Use multi-window or burn-rate alerts**: Simple threshold alerts fire too often. SLO-based burn-rate alerts reduce noise.
- **Include context**: Alert messages must contain service name, environment, current metric value, threshold, and links to dashboards and runbooks.

## Alert Template

```text
[SEVERITY] Service: {service_name} | Env: {environment}
Metric: {metric_name} = {current_value} (threshold: {threshold})
Duration: {alert_duration}
Runbook: {runbook_url}
Dashboard: {dashboard_url}
```

## Prometheus Alerting Rule Example

```yaml
groups:
  - name: application_alerts
    rules:
      - alert: HighErrorRate
        expr: service:http_errors:ratio5m > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on {{ $labels.service }}"
          description: "Error rate is {{ $value | humanizePercentage }} (> 5%)"
          runbook_url: "https://runbooks.example.com/high-error-rate"

      - alert: HighLatency
        expr: service:http_latency:p99_5m > 1.0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High p99 latency on {{ $labels.service }}"
          description: "P99 latency is {{ $value | humanizeDuration }}"
          runbook_url: "https://runbooks.example.com/high-latency"
```

## Alert Rule Checklist

Before deploying an alert rule, verify:

- [ ] Has a `for` duration (avoids instant false positives)
- [ ] Has a `severity` label
- [ ] Has `summary` and `description` annotations
- [ ] Has a `runbook_url` annotation
- [ ] Expression uses `rate()` or `increase()` for counter metrics
- [ ] Threshold is based on measured baselines, not guesses
- [ ] Alert has been tested with synthetic data

## Resources

- [Prometheus Alerting Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Google SRE - Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)
