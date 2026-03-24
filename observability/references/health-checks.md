# Health Checks

Detailed health check patterns for application lifecycle management in container orchestrators.

## Probe Types

| Probe | Check | External Dependencies | Failure Action |
| --- | --- | --- | --- |
| Liveness | App is running | No | Container restart |
| Readiness | App can serve traffic | Yes (DB, cache) | Remove from load balancer |
| Startup | App initialization done | Yes | Block liveness/readiness until ready |

## Probe Configuration (Kubernetes)

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 15
  periodSeconds: 10
  timeoutSeconds: 3
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3

startupProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 0
  periodSeconds: 5
  failureThreshold: 30  # 30 * 5s = 150s max startup time
```

## Health Check Rules

### Liveness Probe

- Must be lightweight — no external dependency checks
- Check only internal process health (e.g., thread deadlock, event loop alive)
- Never include database, cache, or external service checks
- Never put slow checks in liveness probes (causes unnecessary restarts)
- Return quickly (< 100ms)

### Readiness Probe

- Should verify critical dependencies (database connections, cache availability)
- Failing readiness removes the pod from the Service's endpoint list
- Use for graceful degradation during dependency outages
- Include connection pool health but not individual query tests

### Startup Probe

- Use for applications with slow initialization (loading caches, warming models)
- Once startup probe succeeds, liveness and readiness probes begin
- Set `failureThreshold * periodSeconds` to cover maximum expected startup time

## Health Check Response Format

```json
{
  "status": "UP",
  "components": {
    "db": { "status": "UP", "details": { "database": "PostgreSQL" } },
    "cache": { "status": "UP", "details": { "type": "Redis" } },
    "diskSpace": { "status": "UP", "details": { "free": "10GB" } }
  }
}
```

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
| --- | --- | --- |
| DB check in liveness probe | DB outage restarts all pods | Move to readiness probe |
| No startup probe for slow apps | Liveness kills pod during init | Add startup probe |
| Health check with side effects | Writes or external calls on probe | Make probes read-only |
| Same endpoint for all probes | Cannot tune failure behavior | Separate `/healthz`, `/ready` |
| No timeout on health check | Slow check blocks probe | Set explicit timeout |
