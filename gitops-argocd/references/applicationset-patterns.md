# ApplicationSet Patterns

## 1. Generator Types

### List Generator

Deploy to explicitly listed targets.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: myapp
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - cluster: dev
            url: https://dev-cluster.example.com
            namespace: myapp-dev
          - cluster: staging
            url: https://staging-cluster.example.com
            namespace: myapp-staging
          - cluster: prod
            url: https://prod-cluster.example.com
            namespace: myapp-prod
  template:
    metadata:
      name: "myapp-{{cluster}}"
    spec:
      project: default
      source:
        repoURL: https://github.com/org/gitops-repo.git
        targetRevision: main
        path: "apps/myapp/overlays/{{cluster}}"
      destination:
        server: "{{url}}"
        namespace: "{{namespace}}"
```

### Cluster Generator

Auto-discover registered clusters.

```yaml
generators:
  - clusters:
      selector:
        matchLabels:
          env: production
          region: us-east
```

### Git Directory Generator

Create Applications from directory structure.

```yaml
generators:
  - git:
      repoURL: https://github.com/org/gitops-repo.git
      revision: main
      directories:
        - path: "apps/*"
        - path: "apps/excluded-app"
          exclude: true
```

### Git File Generator

Create Applications from JSON/YAML files in Git.

```yaml
generators:
  - git:
      repoURL: https://github.com/org/gitops-repo.git
      revision: main
      files:
        - path: "clusters/*/config.json"
```

```json
{
  "cluster": "prod-us",
  "server": "https://prod-us.example.com",
  "values": {
    "replicas": 3,
    "region": "us-east-1"
  }
}
```

### Pull Request Generator

Create ephemeral environments for PRs.

```yaml
generators:
  - pullRequest:
      github:
        owner: org
        repo: myapp
        tokenRef:
          secretName: github-token
          key: token
        labels:
          - preview
      requeueAfterSeconds: 60
template:
  metadata:
    name: "myapp-pr-{{number}}"
  spec:
    source:
      repoURL: https://github.com/org/myapp.git
      targetRevision: "{{branch}}"
      path: k8s/overlays/preview
    destination:
      server: https://kubernetes.default.svc
      namespace: "preview-{{number}}"
```

---

## 2. Combining Generators

### Matrix Generator

Cartesian product of two generators.

```yaml
generators:
  - matrix:
      generators:
        - git:
            repoURL: https://github.com/org/gitops-repo.git
            revision: main
            directories:
              - path: "apps/*"
        - clusters:
            selector:
              matchLabels:
                env: production
template:
  metadata:
    name: "{{path.basename}}-{{name}}"
  spec:
    source:
      path: "{{path}}"
    destination:
      server: "{{server}}"
```

### Merge Generator

Merge parameters from multiple generators (override with priority).

```yaml
generators:
  - merge:
      mergeKeys:
        - cluster
      generators:
        # Base parameters
        - list:
            elements:
              - cluster: dev
                replicas: "1"
              - cluster: staging
                replicas: "2"
              - cluster: prod
                replicas: "3"
        # Override specific clusters
        - list:
            elements:
              - cluster: prod
                replicas: "5"       # Overrides "3"
```

---

## 3. Template Overrides

### Per-Element Template Override

```yaml
generators:
  - list:
      elements:
        - cluster: dev
          url: https://dev.example.com
        - cluster: prod
          url: https://prod.example.com
      template:
        # This template applies only to this generator's output
        # and merges with the top-level template
        spec:
          syncPolicy:
            automated:
              selfHeal: true
template:
  metadata:
    name: "myapp-{{cluster}}"
  spec:
    project: default
    source:
      repoURL: https://github.com/org/gitops-repo.git
      path: "apps/myapp/overlays/{{cluster}}"
    destination:
      server: "{{url}}"
```

---

## 4. Sync Policy per Generator

### Environment-Based Sync Policies

```yaml
generators:
  - list:
      elements:
        - cluster: dev
          autoSync: "true"
          prune: "true"
        - cluster: prod
          autoSync: "false"
          prune: "false"
template:
  spec:
    syncPolicy:
      automated:
        selfHeal: {{autoSync}}
        prune: {{prune}}
```

---

## 5. Progressive Rollout with ApplicationSet

### Ordered Deployment Strategy

```yaml
# Use sync waves + list generator for ordered multi-cluster rollout
generators:
  - list:
      elements:
        - cluster: canary
          wave: "0"
        - cluster: prod-us-east
          wave: "1"
        - cluster: prod-us-west
          wave: "2"
        - cluster: prod-eu
          wave: "3"
template:
  metadata:
    name: "myapp-{{cluster}}"
    annotations:
      argocd.argoproj.io/sync-wave: "{{wave}}"
```

### Rolling Update Strategy

Use the `rollingSync` strategy (Argo CD 2.12+):

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: myapp-progressive
spec:
  strategy:
    type: RollingSync
    rollingSync:
      steps:
        - matchExpressions:
            - key: env
              operator: In
              values: [canary]
        - matchExpressions:
            - key: env
              operator: In
              values: [production]
          maxUpdate: "25%"
```

---

## 6. Best Practices

| Practice | Rationale |
| --- | --- |
| Use `goTemplate: true` | More powerful templating than default |
| Set `preserveResourcesOnDeletion: true` for infra | Prevent accidental resource deletion |
| Use label selectors on cluster generator | Avoid deploying to unintended clusters |
| Pin `targetRevision` for production | Prevent unexpected updates |
| Use `requeueAfterSeconds` on PR generator | Clean up stale preview environments |
| Limit generator output with `selector` | Prevent Application sprawl |

### Go Template Mode

```yaml
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  template:
    metadata:
      name: "myapp-{{ .cluster }}"
    spec:
      source:
        path: "apps/myapp/overlays/{{ .cluster }}"
```
