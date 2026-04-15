---
name: gitops-argocd
description: >-
  GitOps workflow with Argo CD including application management, sync strategies,
  secret management, multi-cluster deployment, rollback, notifications, and
  CI/CD integration. Covers ApplicationSet patterns and progressive delivery.
  Use when implementing GitOps workflows or managing Argo CD configurations.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
compatibility: Requires Argo CD CLI and Kubernetes cluster access
---

# GitOps with Argo CD Rules

## 1. GitOps Principles

| Principle | Description |
| --- | --- |
| Declarative desired state | All system state is described declaratively in Git |
| Version controlled | Git is the single source of truth for system state |
| Automated reconciliation | Approved changes are automatically applied to the system |
| Closed-loop control | Software agents continuously observe and correct drift |

### Key Rules

- All changes to the system MUST go through Git — no `kubectl apply` or `helm install` manually
- The Git repository state should always reflect what is deployed
- Drift detection should alert and optionally auto-correct
- Credentials and secrets are the exception — use sealed/external secret patterns

---

## 2. Repository Strategy

### Mono-Repo Structure

```text
gitops-repo/
├── apps/                    # Application manifests
│   ├── app-a/
│   │   ├── base/
│   │   └── overlays/
│   │       ├── dev/
│   │       ├── staging/
│   │       └── prod/
│   └── app-b/
├── infra/                   # Infrastructure components
│   ├── cert-manager/
│   ├── ingress-nginx/
│   └── monitoring/
├── clusters/                # Cluster-specific config
│   ├── dev-cluster/
│   ├── staging-cluster/
│   └── prod-cluster/
└── projects/                # Argo CD AppProject definitions
```

### Multi-Repo Structure

| Repository | Contents | Purpose |
| --- | --- | --- |
| `app-source` | Application source code | CI builds, Docker images |
| `app-config` | K8s manifests, Helm values | GitOps deployment config |
| `infra-config` | Platform components | Shared infrastructure |

### App-of-Apps Pattern

```yaml
# root-app.yaml — bootstraps all other applications
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/gitops-repo.git
    targetRevision: main
    path: apps
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      selfHeal: true
      prune: true
```

---

## 3. Application CRD

### Basic Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp-prod
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: myteam

  source:
    repoURL: https://github.com/org/gitops-repo.git
    targetRevision: main
    path: apps/myapp/overlays/prod

  destination:
    server: https://kubernetes.default.svc
    namespace: myapp-prod

  syncPolicy:
    automated:
      selfHeal: true
      prune: true
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - ApplyOutOfSyncOnly=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

### Helm Source

```yaml
source:
  repoURL: https://charts.example.com
  chart: myapp
  targetRevision: "1.2.0"
  helm:
    releaseName: myapp
    valueFiles:
      - values.yaml
      - values-prod.yaml
    parameters:
      - name: image.tag
        value: "3.4.1"
```

### Multi-Source Application

```yaml
sources:
  - repoURL: https://charts.example.com
    chart: myapp
    targetRevision: "1.2.0"
    helm:
      valueFiles:
        - $values/apps/myapp/values-prod.yaml
  - repoURL: https://github.com/org/gitops-repo.git
    targetRevision: main
    ref: values
```

---

## 4. Sync Strategies

### Auto-Sync vs Manual

| Strategy | When to Use | Risk Level |
| --- | --- | --- |
| Auto-sync + self-heal + prune | Dev, staging environments | Low |
| Auto-sync + self-heal (no prune) | Pre-production | Medium |
| Manual sync | Production (with approval) | Controlled |

### Sync Waves and Phases

```yaml
# Resources are synced in order: PreSync → Sync → PostSync
# Within each phase, sync-wave ordering applies (lower first)

# Phase: PreSync — runs before main sync
metadata:
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/sync-wave: "-1"

# Phase: Sync — default, main resources
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "0"    # Namespace, RBAC
---
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "1"    # ConfigMaps, Secrets
---
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "2"    # Deployments, Services
---
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "3"    # Ingress, HPA

# Phase: PostSync — runs after main sync
metadata:
  annotations:
    argocd.argoproj.io/hook: PostSync     # Smoke tests, notifications
```

### Sync Options Reference

| Option | Purpose |
| --- | --- |
| `CreateNamespace=true` | Auto-create target namespace |
| `PrunePropagationPolicy=foreground` | Wait for dependents before pruning |
| `ApplyOutOfSyncOnly=true` | Only sync changed resources (performance) |
| `ServerSideApply=true` | Use server-side apply for large resources |
| `PruneLast=true` | Prune after all other resources are synced |
| `Replace=true` | Use `kubectl replace` instead of `apply` |
| `FailOnSharedResource=true` | Fail if resource managed by another app |

### Default Resource Ordering

Argo CD syncs resources in a deterministic order based on Kubernetes API conventions:

1. **Namespace** — target namespace must exist first
2. **NetworkPolicy** — network rules before workloads
3. **RBAC** (Role, RoleBinding, ClusterRole, ClusterRoleBinding) — permissions before services
4. **Secrets / ConfigMaps** — configuration before consumers
5. **PV / PVC / StorageClass** — storage before stateful workloads
6. **CRDs** — custom resource definitions before CR instances
7. **ServiceAccount** — identity before deployments
8. **Deployment / StatefulSet / DaemonSet** — compute workloads
9. **Service** — internal networking
10. **Ingress / Gateway** — external traffic routing
11. **HPA** — scaling policies (after workloads exist)

### Hook Types

| Hook | Phase | Typical Use |
| --- | --- | --- |
| `PreSync` | Before main sync | DB migration, schema validation, backup |
| `Sync` | During main sync | Ordered resource creation (wave-based) |
| `PostSync` | After main sync | Smoke tests, notifications, cleanup |
| `SyncFail` | On sync failure | Alerting, rollback triggers, incident creation |
| `Skip` | Excluded from sync | Documentation, annotations — never applied |
| `PreDelete` | Before application deletion | Data export, finalizer cleanup (v2.10+) |
| `PostDelete` | After all resources deleted | External resource cleanup (v2.10+) |

> **PreDelete/PostDelete** (v2.10+): Only run during full application deletion, not during regular sync operations. Hook failure blocks the deletion process.

### Hook Delete Policies

| Policy | Behavior |
| --- | --- |
| `HookSucceeded` | Delete hook resource after successful execution |
| `HookFailed` | Delete hook resource only if it fails |
| `BeforeHookCreation` | Delete previous hook instance before creating new one (prevents conflicts on re-sync) |

```yaml
# Hook with delete-policy example
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
    argocd.argoproj.io/sync-wave: "-1"
spec:
  template:
    spec:
      containers:
        - name: migrate
          image: myorg/db-migrator:latest
      restartPolicy: Never
```

---

## 5. Sync Windows

Sync Windows restrict when applications can be synced, using cron-based schedules defined in AppProject.

### Core Fields

| Field | Purpose |
| --- | --- |
| `kind` | `allow` (sync only during window) or `deny` (block sync during window) |
| `schedule` | Cron expression defining when the window is active |
| `duration` | Window length (e.g., `4h`, `30m`) |
| `applications` | Glob pattern for application names (e.g., `["prod-*"]`) |
| `namespaces` | Target namespace filter |
| `clusters` | Cluster name filter |
| `manualSync` | `true` to allow manual sync even during a `deny` window |

### Example: Allow Nightly Deployments Only

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
      manualSync: false
```

### Example: Block Friday Deployments

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

For detailed Sync Windows patterns, see [references/sync-windows.md](references/sync-windows.md).

---

## 6. Progressive Delivery with Argo Rollouts

Argo Rollouts is a Kubernetes controller that replaces standard Deployments to enable advanced deployment strategies.

### Canary Deployment

Canary releases traffic gradually across weighted steps:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: notification-service
spec:
  replicas: 5
  strategy:
    canary:
      steps:
        - setWeight: 20
        - pause: { duration: 5m }
        - setWeight: 50
        - pause: { duration: 10m }
        - setWeight: 100
      canaryService: notification-service-canary
      stableService: notification-service-stable
```

### BlueGreen Deployment

BlueGreen switches traffic instantly between two full environments:

```yaml
strategy:
  blueGreen:
    activeService: notification-service-active
    previewService: notification-service-preview
    autoPromotionEnabled: false
    autoPromotionSeconds: 300
    scaleDownDelaySeconds: 60
```

### AnalysisTemplate for Auto-Rollback

AnalysisTemplates define Prometheus-based health checks that trigger automatic rollback:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate-check
spec:
  metrics:
    - name: success-rate
      interval: 1m
      successCondition: result[0] >= 0.95
      failureLimit: 3
      provider:
        prometheus:
          address: http://prometheus.monitoring.svc:9090
          query: |
            sum(rate(http_requests_total{service="notification-service", status=~"2.."}[1m]))
            /
            sum(rate(http_requests_total{service="notification-service"}[1m]))
```

### Argo CD Integration

Argo CD manages Rollout resources like any other Kubernetes resource. For detailed operations patterns including BlueGreen, AnalysisTemplate, and Argo CD + Rollouts integration, see [references/operations.md](references/operations.md).

---

## 7. Health Assessment

### Built-in Health Checks

Argo CD includes health checks for standard K8s resources. Custom health checks can be added via `argocd-cm` ConfigMap.

### Custom Health Check Example

```lua
-- Custom health check for a CRD (in argocd-cm)
hs = {}
if obj.status ~= nil then
  if obj.status.phase == "Running" then
    hs.status = "Healthy"
    hs.message = "Application is running"
  elseif obj.status.phase == "Failed" then
    hs.status = "Degraded"
    hs.message = obj.status.message or "Application failed"
  else
    hs.status = "Progressing"
    hs.message = "Application is starting"
  end
end
return hs
```

### Health Status Meanings

| Status | Meaning | Action |
| --- | --- | --- |
| Healthy | All resources are healthy | None |
| Progressing | Resources are being updated | Wait |
| Degraded | Some resources have errors | Investigate |
| Suspended | Paused (e.g., Rollout) | Manual resume or auto-promote |
| Missing | Resource does not exist | Sync to create |
| Unknown | Health cannot be determined | Check custom health scripts |

---

## 8. Secret Management Integration

### Option Comparison

| Solution | Encryption | K8s Native | GitOps Compatible | Complexity |
| --- | --- | --- | --- | --- |
| Sealed Secrets | Asymmetric (RSA) | CRD → Secret | Yes | Low |
| External Secrets (ESO) | Provider-managed | CRD → Secret | Yes | Medium |
| SOPS | Age/PGP/KMS | Decrypt in CI/CD | Yes | Medium |
| Vault + Sidecar | Vault-managed | Injected at runtime | Partial | High |

### External Secrets Operator (Recommended)

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: myapp-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: myapp-secrets
    creationPolicy: Owner
  data:
    - secretKey: db-password
      remoteRef:
        key: myapp/prod/db
        property: password
```

### Sealed Secrets

```bash
# Encrypt a secret for Git storage
kubeseal --format=yaml \
  --controller-name=sealed-secrets \
  --controller-namespace=kube-system \
  < secret.yaml > sealed-secret.yaml
```

---

## 9. Multi-Cluster Deployment

### Hub-Spoke Pattern

```text
Management Cluster (Hub)
├── Argo CD instance
├── ApplicationSets
└── Cluster secrets
    ├── dev-cluster
    ├── staging-cluster
    └── prod-cluster (spoke)
```

### Cluster Registration

```bash
# Add cluster to Argo CD
argocd cluster add <context-name> --name prod-cluster

# Verify
argocd cluster list
```

### ApplicationSet for Multi-Cluster

See [references/applicationset-patterns.md](references/applicationset-patterns.md) for detailed patterns.

---

## 10. Rollback and Disaster Recovery

### Rollback Commands

```bash
# View application history
argocd app history myapp-prod

# Rollback to specific revision
argocd app rollback myapp-prod <revision-id>

# Diff before sync
argocd app diff myapp-prod

# Hard refresh (clear cache)
argocd app get myapp-prod --hard-refresh
```

### Rollback Decision

| Scenario | Action |
| --- | --- |
| Bad config deployed | Revert Git commit → auto-sync corrects |
| Need immediate fix | `argocd app rollback` → then fix in Git |
| Drift detected | Enable self-heal or manual sync |
| Full cluster recovery | Re-bootstrap with app-of-apps from Git |

### Disaster Recovery

- Argo CD state is in Git — rebuild by pointing at the same repo
- Export Argo CD resources: `argocd admin export > backup.yaml`
- Store `argocd-cm`, `argocd-rbac-cm`, `argocd-secret` backups
- Document cluster registration steps for re-bootstrapping

---

## 11. Notifications, RBAC, and CI/CD

> See [references/operations.md](references/operations.md) for detailed patterns including notifications configuration, AppProject RBAC, image updater, and CI pipeline integration.
>
> For progressive delivery with Argo Rollouts (Canary, BlueGreen, AnalysisTemplate), see §6 above and [references/operations.md](references/operations.md).

---

## 12. Anti-Patterns

- Manually applying changes with `kubectl` — bypasses GitOps loop
- Storing plaintext secrets in Git — use sealed/external secrets
- Auto-sync with prune in production without approval gates
- Single monolithic Application covering all namespaces — use app-of-apps
- Not using sync waves — resources created in wrong order
- Ignoring health checks — unhealthy apps reported as synced
- No project isolation — teams can affect each other's deployments
- Using `targetRevision: HEAD` for production — pin to tags or specific commits
- Skipping diff review before manual sync — unexpected changes applied
- Not backing up Argo CD configuration — makes disaster recovery harder

## Related Skills

- For Helm chart development and best practices, see [helm-workflow](../helm-workflow/) skill
- For Kubernetes manifest conventions, see [k8s-workflow](../k8s-workflow/) skill
- For secret management patterns (ESO, Sealed Secrets), see [secrets-management](../secrets-management/) skill

## Additional References

- For ApplicationSet patterns and generators, see [references/applicationset-patterns.md](references/applicationset-patterns.md)
