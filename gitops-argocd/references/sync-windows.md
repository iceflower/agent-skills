# Sync Windows: Time-Based Sync Control

Sync Windows restrict when applications can be synchronized by defining time-based allow/deny rules in AppProject.

## Core Concepts

| Concept | Description |
| --- | --- |
| `kind: allow` | Sync is **only** permitted during the defined window |
| `kind: deny` | Sync is **blocked** during the defined window |
| `schedule` | Cron expression that defines when the window starts |
| `duration` | How long the window remains active (e.g., `2h`, `30m`, `1d`) |
| `manualSync` | When `true`, allows manual sync to override a `deny` window |

## Cron Expression Format

Sync Windows use standard 5-field cron syntax:

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6, Sunday = 0)
│ │ │ │ │
* * * * *
```

## Setting Patterns

### Pattern 1: Nightly Deployment Window (Allow)

Permit sync only during weekday nights (22:00–02:00):

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  syncWindows:
    - kind: allow
      schedule: "0 22 * * 1-5"
      duration: 4h
      applications:
        - "prod-*"
      namespaces:
        - "prod-*"
      clusters:
        - "prod-cluster"
      manualSync: false
```

This means:
- Sync is **blocked** outside 22:00–02:00 on weekdays
- Auto-sync and manual sync are both restricted
- Applications matching `prod-*` are affected

### Pattern 2: Friday Change Freeze (Deny)

Block all deployments on Fridays for stability:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  syncWindows:
    - kind: deny
      schedule: "0 0 * * 5"
      duration: 24h
      applications:
        - "prod-*"
      manualSync: true
```

This means:
- Sync is **blocked** from Friday 00:00 to Saturday 00:00
- Manual sync is still allowed with `manualSync: true` (for emergency hotfixes)
- Auto-sync is fully blocked

### Pattern 3: Weekend Maintenance Window (Allow)

Permit sync only during Saturday maintenance window:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: platform
  namespace: argocd
spec:
  syncWindows:
    - kind: allow
      schedule: "0 6 * * 6"
      duration: 6h
      applications:
        - "infra-*"
        - "platform-*"
      manualSync: false
```

### Pattern 4: Multiple Windows

Combine allow and deny for complex schedules:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: payments
  namespace: argocd
spec:
  syncWindows:
    - kind: allow
      schedule: "0 22 * * 1-4"
      duration: 3h
      applications:
        - "payments-*"
    - kind: deny
      schedule: "0 12 * * 5"
      duration: 1h
      applications:
        - "payments-*"
```

This configuration:
- Allows sync Monday–Thursday 22:00–01:00
- Blocks sync Friday 12:00–13:00 (lunch-hour freeze)

### Pattern 5: Namespace-Specific Deny

Block sync for specific namespaces while allowing others:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: multi-tenant
  namespace: argocd
spec:
  syncWindows:
    - kind: deny
      schedule: "0 0 * * *"
      duration: 6h
      namespaces:
        - "critical-*"
      applications:
        - "*"
      manualSync: true
```

## Manual Sync Override

When `manualSync: true` is set on a `deny` window, operators can still trigger sync manually:

```bash
# Manual sync during a deny window (requires manualSync: true)
argocd app sync myapp-prod
```

If `manualSync: false` (or omitted), even manual sync is blocked during deny windows.

## AppProject Full Example

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: notification-service
  namespace: argocd
spec:
  description: "Notification service project with time-based sync control"
  sourceRepos:
    - "https://github.com/myorg/notification-service.git"
  destinations:
    - namespace: "notification-*"
      server: https://kubernetes.default.svc
  clusterResourceWhitelist:
    - group: ""
      kind: Namespace
  syncWindows:
    # Weekday nightly deployment window
    - kind: allow
      schedule: "0 22 * * 1-5"
      duration: 4h
      applications:
        - "notification-service-prod"
      manualSync: false
    # Friday change freeze with emergency override
    - kind: deny
      schedule: "0 0 * * 5"
      duration: 24h
      applications:
        - "notification-service-prod"
      manualSync: true
```

## Troubleshooting

| Symptom | Cause | Solution |
| --- | --- | --- |
| App shows "Sync Disabled" | Active deny window or outside allow window | Check `argocd proj windows <project>` |
| Manual sync fails during deny window | `manualSync` not set to `true` | Update AppProject with `manualSync: true` |
| Window not taking effect | Cron expression or duration misconfigured | Verify cron syntax and duration format |
| Auto-sync runs during deny window | App not matching the `applications` filter | Check application name glob pattern |
