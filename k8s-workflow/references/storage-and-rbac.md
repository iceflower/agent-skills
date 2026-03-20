# Storage, RBAC, and Deployment Strategies

## 1. Persistent Volumes

### PV / PVC / StorageClass

```yaml
# StorageClass — defines how storage is provisioned
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
---
# PersistentVolumeClaim — requests storage
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: myapp-data
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: fast-ssd
  resources:
    requests:
      storage: 20Gi
```

### Access Modes

| Mode | Abbreviation | Description | Use Case |
| --- | --- | --- | --- |
| ReadWriteOnce | RWO | Single node read/write | Database volumes |
| ReadOnlyMany | ROX | Many nodes read-only | Shared config, static assets |
| ReadWriteMany | RWX | Many nodes read/write | Shared file storage (NFS, EFS) |
| ReadWriteOncePod | RWOP | Single pod read/write | Exclusive access guarantee |

### Reclaim Policies

| Policy | Behavior | Use Case |
| --- | --- | --- |
| Delete | PV deleted when PVC is deleted | Dynamic provisioning (default) |
| Retain | PV kept after PVC deletion | Production data, manual cleanup |

---

## 2. Volume Types

| Type | Persistence | Use Case |
| --- | --- | --- |
| emptyDir | Pod lifetime | Temp files, cache, inter-container sharing |
| hostPath | Node lifetime | Development only (never production) |
| configMap | Cluster | Configuration files (read-only) |
| secret | Cluster | Credentials, certificates |
| persistentVolumeClaim | Beyond pod | Database, stateful applications |
| projected | Cluster | Combine multiple sources in one mount |
| CSI | Beyond pod | Cloud provider storage (EBS, Disk, PD) |

### Volume Mount Best Practices

```yaml
volumes:
  - name: data
    persistentVolumeClaim:
      claimName: myapp-data
  - name: config
    configMap:
      name: myapp-config
  - name: secrets
    secret:
      secretName: myapp-secrets
      defaultMode: 0400  # Read-only for owner
  - name: tmp
    emptyDir:
      sizeLimit: 100Mi

containers:
  - name: app
    volumeMounts:
      - name: data
        mountPath: /data
      - name: config
        mountPath: /etc/myapp
        readOnly: true
      - name: secrets
        mountPath: /etc/secrets
        readOnly: true
      - name: tmp
        mountPath: /tmp
```

---

## 3. StatefulSet Patterns

### StatefulSet with VolumeClaimTemplate

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres
  replicas: 3
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:16-alpine
          ports:
            - containerPort: 5432
          volumeMounts:
            - name: pgdata
              mountPath: /var/lib/postgresql/data
          env:
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
  volumeClaimTemplates:
    - metadata:
        name: pgdata
      spec:
        accessModes: [ReadWriteOnce]
        storageClassName: fast-ssd
        resources:
          requests:
            storage: 50Gi
```

### StatefulSet Guarantees

| Property | Guarantee |
| --- | --- |
| Stable network identity | `pod-name-{0,1,2}.service-name` |
| Ordered deployment | Pods created sequentially (0 → 1 → 2) |
| Ordered termination | Pods deleted in reverse order (2 → 1 → 0) |
| Stable storage | Each pod gets its own PVC, retained on reschedule |

### Production Database Consideration

For production database workloads on Kubernetes, prefer database-specific Operators over raw StatefulSets:

| Database | Operator | Benefit |
| --- | --- | --- |
| PostgreSQL | CloudNativePG, CrunchyData PGO | Automated failover, backup, monitoring |
| MySQL | MySQL Operator, Percona XtraDB | Cluster management, automated recovery |
| MongoDB | MongoDB Community Operator | ReplicaSet management, scaling |
| Redis | Redis Operator | Sentinel/Cluster mode, auto-failover |

Operators handle complex lifecycle tasks (failover, backup, restore, scaling) that raw StatefulSets do not provide.

---

## 4. RBAC

### Resource Hierarchy

```text
ClusterRole ──── ClusterRoleBinding ──── Subject (User/Group/ServiceAccount)
    │                                         (cluster-wide)
    │
Role ──────── RoleBinding ──────────── Subject (User/Group/ServiceAccount)
                                           (namespace-scoped)
```

### Least-Privilege ServiceAccount

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
  namespace: myapp
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: myapp-role
  namespace: myapp
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: myapp-binding
  namespace: myapp
subjects:
  - kind: ServiceAccount
    name: myapp-sa
    namespace: myapp
roleRef:
  kind: Role
  name: myapp-role
  apiGroup: rbac.authorization.k8s.io
```

### RBAC Rules

- Every workload should use a dedicated ServiceAccount (not `default`)
- Grant minimum required permissions — start with nothing, add as needed
- Prefer namespace-scoped Roles over ClusterRoles
- Avoid wildcard verbs (`*`) and resources (`*`)
- Audit RBAC permissions regularly — `kubectl auth can-i --list --as=system:serviceaccount:myapp:myapp-sa`

---

## 5. Namespace Strategy

### Organization Patterns

| Pattern | Structure | Best For |
| --- | --- | --- |
| Per-environment | `myapp-dev`, `myapp-prod` | Single-team, multiple environments |
| Per-team | `team-backend`, `team-frontend` | Multi-team, shared cluster |
| Per-service | `user-service`, `order-service` | Microservices, strong isolation |
| Hybrid | `team-backend-prod`, `team-backend-dev` | Large organizations |

### Resource Quotas

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-quota
  namespace: team-backend
spec:
  hard:
    requests.cpu: "20"
    requests.memory: 40Gi
    limits.cpu: "40"
    limits.memory: 80Gi
    pods: "100"
    services: "20"
    persistentvolumeclaims: "30"
```

### Limit Ranges

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: team-backend
spec:
  limits:
    - type: Container
      default:
        cpu: 500m
        memory: 512Mi
      defaultRequest:
        cpu: 100m
        memory: 256Mi
      max:
        cpu: "4"
        memory: 8Gi
      min:
        cpu: 50m
        memory: 64Mi
```

---

## 6. Deployment Strategies

### Strategy Comparison

| Strategy | Zero Downtime | Rollback Speed | Resource Cost | Risk |
| --- | --- | --- | --- | --- |
| Rolling Update | Yes | Medium (rollback) | Low (gradual) | Medium |
| Blue-Green | Yes | Fast (switch) | High (2x resources) | Low |
| Canary | Yes | Fast (abort) | Low (% traffic) | Lowest |
| Recreate | No (downtime) | Medium | Low | High |

### Rolling Update Configuration

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%          # Max pods above desired count
      maxUnavailable: 0       # Zero downtime — always maintain full capacity
  minReadySeconds: 30         # Wait before marking pod as available
```

### Canary with Argo Rollouts

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  replicas: 10
  strategy:
    canary:
      steps:
        - setWeight: 10          # 10% traffic to canary
        - pause: { duration: 5m } # Monitor
        - setWeight: 30
        - pause: { duration: 5m }
        - setWeight: 50
        - pause: { duration: 10m }
      analysis:
        templates:
          - templateName: success-rate
        startingStep: 1
        args:
          - name: service-name
            value: myapp
      canaryService: myapp-canary
      stableService: myapp-stable
```

### Blue-Green with Argo Rollouts

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  replicas: 5
  strategy:
    blueGreen:
      activeService: myapp-active
      previewService: myapp-preview
      autoPromotionEnabled: false
      prePromotionAnalysis:
        templates:
          - templateName: smoke-test
      scaleDownDelaySeconds: 300
```

### Strategy Selection Guide

| Scenario | Recommended Strategy |
| --- | --- |
| Simple stateless app, low risk | Rolling Update |
| Critical service, need instant rollback | Blue-Green |
| High-traffic service, gradual confidence | Canary |
| Database migration with breaking changes | Recreate (with maintenance window) |
| First deployment of new service | Rolling Update (simplest) |
