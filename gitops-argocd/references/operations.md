# Argo CD Operations: Notifications, RBAC, and CI/CD

## Notifications Configuration

```yaml
# argocd-notifications-cm ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
data:
  trigger.on-sync-succeeded: |
    - when: app.status.sync.status == 'Synced'
      send: [app-sync-succeeded]

  trigger.on-health-degraded: |
    - when: app.status.health.status == 'Degraded'
      send: [app-health-degraded]

  template.app-sync-succeeded: |
    message: |
      Application {{.app.metadata.name}} has been synced.
      Revision: {{.app.status.sync.revision}}

  template.app-health-degraded: |
    message: |
      Application {{.app.metadata.name}} is degraded.
      Health: {{.app.status.health.status}}
```

### Application Annotation

```yaml
metadata:
  annotations:
    notifications.argoproj.io/subscribe.on-sync-succeeded.slack: deploy-notifications
    notifications.argoproj.io/subscribe.on-health-degraded.slack: alerts-channel
```

## RBAC and Multi-Tenancy

### AppProject Isolation

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: myteam
  namespace: argocd
spec:
  description: "MyTeam project"
  sourceRepos:
    - "https://github.com/org/myteam-*"
  destinations:
    - namespace: "myteam-*"
      server: https://kubernetes.default.svc
  clusterResourceWhitelist:
    - group: ""
      kind: Namespace
  namespaceResourceBlacklist:
    - group: ""
      kind: ResourceQuota
  roles:
    - name: developer
      description: "Developer access"
      policies:
        - p, proj:myteam:developer, applications, get, myteam/*, allow
        - p, proj:myteam:developer, applications, sync, myteam/*, allow
      groups:
        - myteam-developers
```

### RBAC Policy

```csv
# argocd-rbac-cm
p, role:team-lead, applications, *, myteam/*, allow
p, role:developer, applications, get, myteam/*, allow
p, role:developer, applications, sync, myteam/*, allow
p, role:developer, applications, action/*, myteam/*, allow
g, team-lead-group, role:team-lead
g, dev-group, role:developer
```

## CI/CD Integration

### Image Updater

```yaml
# Annotation-based image update
metadata:
  annotations:
    argocd-image-updater.argoproj.io/image-list: myapp=ghcr.io/org/myapp
    argocd-image-updater.argoproj.io/myapp.update-strategy: semver
    argocd-image-updater.argoproj.io/myapp.allow-tags: "regexp:^\\d+\\.\\d+\\.\\d+$"
    argocd-image-updater.argoproj.io/write-back-method: git
```

### CI Pipeline Integration

```yaml
# GitHub Actions — update image tag in gitops repo
- name: Update image tag
  run: |
    cd gitops-repo/apps/myapp/overlays/prod
    kustomize edit set image myapp=ghcr.io/org/myapp:${{ github.sha }}
    git add .
    git commit -m "chore: update myapp to ${{ github.sha }}"
    git push
```

### Progressive Delivery with Argo Rollouts

#### Canary Deployment

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: order-service-canary
  namespace: payments
spec:
  replicas: 5
  revisionHistoryLimit: 5
  strategy:
    canary:
      steps:
        - setWeight: 10
        - pause: { duration: 3m }
        - setWeight: 30
        - pause: { duration: 5m }
        - setWeight: 50
        - pause: { duration: 10m }
        - setWeight: 100
      canaryService: order-service-canary
      stableService: order-service-stable
      trafficRouting:
        nginx:
          stableIngress: order-service-ingress
```

#### BlueGreen Deployment

BlueGreen maintains two identical environments and switches traffic instantly:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: order-service-bluegreen
  namespace: payments
spec:
  replicas: 3
  revisionHistoryLimit: 5
  strategy:
    blueGreen:
      activeService: order-service-active
      previewService: order-service-preview
      autoPromotionEnabled: false
      autoPromotionSeconds: 300
      scaleDownDelaySeconds: 60
      scaleDownDelayRevisionLimit: 2
      abortScaleDownDelaySeconds: 30
      previewReplicaCount: 1
---
apiVersion: v1
kind: Service
metadata:
  name: order-service-active
spec:
  selector:
    app: order-service
  ports:
    - port: 80
      targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: order-service-preview
spec:
  selector:
    app: order-service
  ports:
    - port: 80
      targetPort: 8080
```

Key BlueGreen fields:

| Field | Purpose |
| --- | --- |
| `activeService` | Service receiving production traffic |
| `previewService` | Service for testing the new version before promotion |
| `autoPromotionEnabled` | `false` requires manual promotion; `true` promotes automatically |
| `autoPromotionSeconds` | Auto-promote after N seconds if `autoPromotionEnabled: false` |
| `scaleDownDelaySeconds` | How long to keep the old ReplicaSet after switch (default: 30s) |
| `previewReplicaCount` | Number of replicas for preview (useful for cost control) |

#### AnalysisTemplate for Auto-Rollback

AnalysisTemplates define metric-based checks that trigger automatic rollback when thresholds are breached:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate-check
  namespace: payments
spec:
  args:
    - name: service-name
      value: order-service
  metrics:
    - name: success-rate
      interval: 1m
      successCondition: result[0] >= 0.95
      failureLimit: 3
      provider:
        prometheus:
          address: http://prometheus.monitoring.svc:9090
          query: |
            sum(rate(http_requests_total{service="{{args.service-name}}", status=~"2.."}[1m]))
            /
            sum(rate(http_requests_total{service="{{args.service-name}}"}[1m]))
    - name: error-rate
      interval: 1m
      failureCondition: result[0] > 0.05
      failureLimit: 2
      provider:
        prometheus:
          address: http://prometheus.monitoring.svc:9090
          query: |
            sum(rate(http_requests_total{service="{{args.service-name}}", status=~"5.."}[1m]))
            /
            sum(rate(http_requests_total{service="{{args.service-name}}"}[1m]))
    - name: p99-latency
      interval: 1m
      successCondition: result[0] <= 500
      failureLimit: 2
      provider:
        prometheus:
          address: http://prometheus.monitoring.svc:9090
          query: |
            histogram_quantile(0.99,
              sum(rate(http_request_duration_seconds_bucket{service="{{args.service-name}}"}[1m]))
              by (le))
```

#### Rollout with Analysis Integration

Attach AnalysisTemplate to Canary steps for automated promotion/rollback:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: order-service-canary
  namespace: payments
spec:
  replicas: 5
  strategy:
    canary:
      steps:
        - setWeight: 20
        - pause: { duration: 2m }
        - analysis:
            templates:
              - templateName: success-rate-check
            args:
              - name: service-name
                value: order-service
        - setWeight: 50
        - pause: { duration: 5m }
        - setWeight: 100
      canaryService: order-service-canary
      stableService: order-service-stable
      trafficRouting:
        nginx:
          stableIngress: order-service-ingress
```

#### Argo CD + Argo Rollouts Integration

Argo CD natively manages Rollout resources. Key integration points:

1. **Health Check**: Argo CD includes built-in health assessment for Rollout CRD. Status mapping:
   - `Healthy` → Rollout is fully promoted
   - `Progressing` → Canary step in progress or paused
   - `Degraded` → Analysis failed, rollback triggered
   - `Suspended` → Rollout paused awaiting manual approval

2. **Sync Policy**: Rollouts work with both auto-sync and manual sync:

```yaml
syncPolicy:
  automated:
    selfHeal: true
    prune: true
  syncOptions:
    - CreateNamespace=true
```

3. **Manual Promotion via Argo CD CLI**:

```bash
# Promote a paused BlueGreen rollout
argocd app set order-service-bluegreen --parameter promote=true

# Resume a paused canary step
kubectl argo rollouts promote order-service-canary -n payments

# Abort current rollout (triggers rollback)
kubectl argo rollouts abort order-service-canary -n payments
```

4. **AnalysisRun Lifecycle**: AnalysisRuns are created as child resources of Rollouts. Argo CD tracks them as part of the application tree and reports overall health based on analysis results.
