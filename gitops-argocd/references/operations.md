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

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  replicas: 5
  strategy:
    canary:
      steps:
        - setWeight: 20
        - pause: { duration: 5m }
        - setWeight: 50
        - pause: { duration: 5m }
        - setWeight: 100
      canaryService: myapp-canary
      stableService: myapp-stable
      trafficRouting:
        nginx:
          stableIngress: myapp-ingress
```
