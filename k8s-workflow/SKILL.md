---
name: k8s-workflow
description: >-
  Kubernetes core workflow rules, manifest conventions, security best practices,
  and version considerations. Includes managed K8s providers (EKS, AKS, GKE),
  autoscaling (KEDA, Knative, event-driven scaling), networking (Ingress,
  Gateway API, NetworkPolicy, Service Mesh), storage (PV/PVC, StatefulSet),
  RBAC, and deployment strategies (Rolling, Blue-Green, Canary).
  Use for Kubernetes operations and manifest authoring.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
compatibility: Requires kubectl and Kubernetes cluster access
---

# Kubernetes Workflow Rules

## 1. Resource Naming

### Conventions

| Element | Convention | Example |
| --- | --- | --- |
| Namespace | lowercase kebab | `myapp-prod`, `myapp-dev` |
| Deployment | `{app}-{component}` | `myapp-api`, `myapp-worker` |
| Service | Same as Deployment | `myapp-api` |
| ConfigMap | `{app}-{purpose}-config` | `myapp-api-app-config` |
| Secret | `{app}-{purpose}-secret` | `myapp-api-db-secret` |
| Ingress | `{app}-ingress` | `myapp-api-ingress` |
| CronJob | `{app}-{action}` | `myapp-cleanup-logs` |

---

## 2. Labels and Annotations

### Required Labels

```yaml
metadata:
  labels:
    app.kubernetes.io/name: myapp-api
    app.kubernetes.io/component: backend
    app.kubernetes.io/part-of: myapp
    app.kubernetes.io/managed-by: kubectl
    app.kubernetes.io/version: "1.2.0"
    environment: production
```

### Label Usage

| Label | Purpose |
| --- | --- |
| `app.kubernetes.io/name` | Application name (used in selectors) |
| `app.kubernetes.io/component` | Component role (backend, frontend, worker, db) |
| `app.kubernetes.io/part-of` | Parent application group |
| `environment` | Deployment environment (dev, staging, production) |

---

## 3. Resource Limits

### Always Set requests and limits

```yaml
resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

### Sizing Guidelines

| Workload Type | CPU Request | CPU Limit | Memory Request | Memory Limit |
| --- | --- | --- | --- | --- |
| API server | 100m–500m | 500m–2000m | 256Mi–512Mi | 512Mi–1Gi |
| Background worker | 50m–200m | 200m–1000m | 128Mi–256Mi | 256Mi–512Mi |
| CronJob | 50m–100m | 200m–500m | 128Mi–256Mi | 256Mi–512Mi |

- Set `requests` based on steady-state usage
- Set `limits` at 2–4x requests for burst capacity
- Always set memory limits to prevent OOM kills affecting other pods

---

## 4. Environment-Specific Management

### Directory Structure (Kustomize)

```text
k8s/
├── base/                  # Common manifests
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   └── patches/
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── patches/
│   └── prod/
│       ├── kustomization.yaml
│       └── patches/
```

### Environment Differences

| Config | Dev | Staging | Prod |
| --- | --- | --- | --- |
| Replicas | 1 | 2 | 3+ |
| Resource limits | Low | Medium | Full |
| Log level | DEBUG | INFO | INFO |
| Ingress TLS | Optional | Yes | Yes |

### 4.1 Kustomize base/overlays 패턴

**base 디렉토리에 공통 리소스, overlays/{env}에 환경별 patch 작성.**

- `kustomization.yaml`의 `namespace:` 필드로 대상 네임스페이스 지정
- `images:` 필드로 컨테이너 이미지 태그 교체 (newTag, newName, digest 지원)
- YAML 예제 작성 시 필드 순서는 의도적으로 재배열 — 원본 순서와 다르게 구성할 것

**base/kustomization.yaml 예제:**

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml

images:
  - name: order-service
    newTag: "1.4.2"

namespace: ecommerce
```

**overlays/prod/kustomization.yaml 예제:**

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namespace: ecommerce-prod

images:
  - name: order-service
    newName: ghcr.io/myorg/order-service
    newTag: "1.4.2"

patches:
  - path: patches/replica-scale.yaml
  - path: patches/resource-limits.yaml
```

### 4.2 patches를 통한 임의 필드 업데이트

**strategic merge patch와 JSON patch 두 가지 방식 중 선택.**

**strategic merge patch (전체 YAML 조각으로 교체):**

```yaml
# patches/replica-scale.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
spec:
  replicas: 5
```

**JSON patch (op/path/value 형식):**

```yaml
# patches/add-annotation.yaml
- op: add
  path: /metadata/annotations/service.beta.kubernetes.io~1aws-load-balancer-type
  value: nlb
```

**적용 대상 필드 예시:**

| 변경 항목 | patch 유형 | 예시 |
| --- | --- | --- |
| replicas 조정 | strategic merge | `spec.replicas: 3` |
| labels 추가 | strategic merge | `metadata.labels.team: backend` |
| annotations 추가 | JSON patch 또는 strategic merge | `metadata.annotations` |
| env 변수 주입 | strategic merge | `spec.template.spec.containers[0].env` |

### 4.3 namePrefix / nameSuffix

**리소스 이름에 환경별 접두사/접미사 자동 부여. cross-reference(selector, volume, secretKeyRef 등)는 Kustomize가 자동 업데이트.**

```yaml
# overlays/staging/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namePrefix: staging-

# 결과: order-service → staging-order-service
# Service selector, Deployment volume 참조 모두 자동 갱신
```

```yaml
# overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

nameSuffix: -prod

# 결과: order-service → order-service-prod
```

**namePrefix/nameSuffix 규칙:**

- 환경 분리가 명확해야 할 때 namePrefix 권장 (예: `dev-`, `staging-`, `prod-`)
- 다중 클러스터에서 동일 환경 운영 시 nameSuffix 권장 (예: `-eu`, `-ap`)
- cross-reference 자동 업데이트 대상: `selector.matchLabels`, `volume.secretName`, `configMapKeyRef.name`

### 4.4 configMapGenerator

**ConfigMap 생성 시 literals, files, envs 세 가지 소스 유형 지원. 생성된 ConfigMap 이름에 해시가 자동 추가되어 ConfigMap 변경 시 Deployment 롤링 업데이트가 자동 트리거됨.**

```yaml
# base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

configMapGenerator:
  - name: order-service-config
    literals:
      - LOG_LEVEL=info
      - MAX_CONNECTIONS=100
    files:
      - application.properties
    envs:
      - order-service.env

  # 기존 ConfigMap에 병합
  - name: existing-config
    behavior: merge
    literals:
      - NEW_KEY=new-value

  # 기존 ConfigMap 완전 교체
  - name: legacy-config
    behavior: replace
    literals:
      - REPLACED=true
```

**configMapGenerator 규칙:**

- `behavior` 미지정 시 기본 생성 (동일 이름 존재 시 에러)
- `behavior: merge` — 기존 ConfigMap에 키 추가/업데이트
- `behavior: replace` — 기존 ConfigMap 전체 교체
- Deployment에서 `configMapKeyRef` 또는 `configMapRef`로 참조 시, 해시 포함된 이름이 **자동 업데이트**되므로 수동 수정 불필요
- ConfigMap 내용 변경 → 해시 변경 → pod template hash 변경 → 자동 롤링 업데이트

---

## 5. Security Best Practices

### Pod Security

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

### Secrets Management

- Never store plaintext secrets in manifests
- Use `SealedSecret`, `ExternalSecret`, or cloud provider secret manager
- Reference secrets via `secretKeyRef`, not environment variable literals
- Rotate secrets regularly without pod restart (use volume mounts for auto-reload)

---

## 6. Health Checks

### Always Define Probes

```yaml
livenessProbe:
  httpGet:
    path: /actuator/health/liveness
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /actuator/health/readiness
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 3

startupProbe:
  httpGet:
    path: /actuator/health
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 30
```

### Probe Guidelines

| Probe | Purpose | Failure Action |
| --- | --- | --- |
| Startup | App initialization complete | Kill and restart pod |
| Liveness | App still running | Kill and restart pod |
| Readiness | App ready for traffic | Remove from Service endpoints |

---

## 7. Version Support (2026-03-14)

### Kubernetes Release Cadence

Kubernetes releases a new minor version approximately every 4 months.

### Current Versions

| Version | Status | Latest Patch | End of Support |
| --- | --- | --- | --- |
| 1.35 | Supported | 1.35.2 | Dec 2026 |
| 1.34 | Supported | 1.34.5 | Feb 2027 |
| 1.33 | Supported | 1.33.9 | Jun 2026 |
| 1.32 | EOL | 1.32.13 | Feb 2026 |
| 1.31 | EOL | 1.31.14 | Dec 2025 |

### Key Features in Recent Versions

#### Kubernetes 1.35 (Dec 2025)

- **In-Place Pod Resize (GA)**: CPU/memory adjustments without pod restart
- **PreferSameNode Traffic Distribution**: Local endpoint priority for reduced latency
- **Image Volumes**: Deliver data artifacts using OCI container images

#### Kubernetes 1.34 (Aug 2025)

- **Finer-grained Authorization**: Field/label selector-based decisions
- **Anonymous Request Restrictions**: Limit unauthenticated access to specific endpoints
- **Ordered Namespace Deletion**: Structured deletion order for security

#### Kubernetes 1.33 (Apr 2025)

- **Sidecar Containers (GA)**: Native sidecar lifecycle management
- **Recursive Read-Only Mounts (GA)**: Full read-only volume mounts
- **Bound ServiceAccount Token Improvements**: Unique token IDs, node binding

### Upgrade Planning

1. **Review deprecation notices** before each minor version upgrade
2. **Test in non-production** environments first
3. **Check API compatibility** using `kubectl deprecations` or `pluto`
4. **Update CRDs and webhooks** before control plane upgrade
5. **Node pools**: Drain and upgrade incrementally

---

## 8. Managed Kubernetes Services

For provider-specific managed Kubernetes services, see dedicated skills:

- **AWS EKS**: EKS section in `k8s-providers` rules
- **Azure AKS**: AKS section in `k8s-providers` rules
- **GCP GKE**: GKE section in `k8s-providers` rules

### Quick Comparison

| Feature | EKS | AKS | GKE |
| --- | --- | --- | --- |
| Latest K8s | 1.35 | 1.34 | 1.35 |
| Control Plane | Free | Free | Free |
| Node Autoscaling | Karpenter/MNG | Cluster Autoscaler | GKE Autopilot |
| Service Mesh | App Mesh (deprecated) | Istio (add-on) | Anthos Service Mesh |
| Secrets | AWS Secrets Manager | Azure Key Vault | Secret Manager |

---

## 9. Anti-Patterns

- Using `latest` tag for container images — always pin to specific version
- Defining resources without `requests`/`limits`
- Running containers as root
- Hardcoding config values in manifests — use ConfigMap/Secret
- Single replica for production workloads
- Missing health check probes
- Using `NodePort` in production — use `ClusterIP` + Ingress
- Ignoring deprecation warnings before upgrades
- Not testing upgrades in non-production first

## Related Skills

- For GitOps deployment with Argo CD, see [gitops-argocd](../gitops-argocd/) skill
- For Helm chart management, see [helm-workflow](../helm-workflow/) skill
- For Karpenter node provisioning, see [karpenter-workflow](../karpenter-workflow/) skill

## Additional References

- For managed Kubernetes providers (EKS, AKS, GKE), see [references/providers.md](references/providers.md)
- For autoscaling (KEDA, Knative, event-driven), see [references/autoscaling.md](references/autoscaling.md)
- For networking (Ingress, Gateway API, Network Policies, Service Mesh), see [references/networking.md](references/networking.md)
- For storage, RBAC, and deployment strategies, see [references/storage-and-rbac.md](references/storage-and-rbac.md)
- For Kustomize patterns (Helm comparison, overlays, generators, patches), see [references/kustomize.md](references/kustomize.md)
