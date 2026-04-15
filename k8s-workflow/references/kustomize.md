# Kustomize Patterns and Practices

## 1. Kustomize vs Helm 비교

### 핵심 비교 축

| 비교 항목 | Helm | Kustomize |
| --- | --- | --- |
| 파라미터화 방식 | Go 템플릿(values.yaml 기반) | 패치 기반 오버레이 |
| 패키징 | tar.gz 아카이브 배포 | 디렉토리 구조 그대로 사용 |
| 종속성 관리 | Chart.yaml dependencies 자동 설치 | 수동 참조(base/overlays) |
| 릴리스 추적 | helm history, helm rollback 내장 | Git 커밋 이력에 의존(GitOps) |
| 학습 곡선 | 높음(Go 템플릿 문법) | 낮음(순수 YAML 패치) |
| 적합한场景 | 외부 배포용 패키지, 복잡한 조건부 로직 | 사내 애플리케이션, 단순 환경 오버레이 |

### 선택 가이드

- **Helm 선택**: 서드파티에 차트 배포 필요, 조건부 리소스 생성 복잡, 라이프사이클 훅 활용, 릴리스 이력 관리 중요
- **Kustomize 선택**: 사내 전용 애플리케이션, 환경별 단순 차이만 존재, 템플릿 문법 유지 부담 최소화
- **하이브리드**: `helm template` 출력에 Kustomize 오버레이 적용 — 패키징과 환경 분리 동시 달성

> Helm vs Kustomize 상세 비교는 [helm-workflow §10](../../helm-workflow/SKILL.md#10-helm-vs-kustomize) 참조

---

## 2. 다중 환경 관리 전략

### base/overlays 구조

```text
k8s/
├── base/
│   ├── kustomization.yaml     # 공통 리소스 정의
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
└── overlays/
    ├── dev/
    │   ├── kustomization.yaml
    │   └── patches/
    │       └── dev-replicas.yaml
    ├── staging/
    │   ├── kustomization.yaml
    │   └── patches/
    │       └── staging-resources.yaml
    └── prod/
        ├── kustomization.yaml
        └── patches/
            ├── prod-replicas.yaml
            └── prod-resources.yaml
```

### 환경별 kustomization.yaml 작성 규칙

**base/kustomization.yaml:**

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
  - configmap.yaml

namespace: ecommerce
```

**overlays/dev/kustomization.yaml:**

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namespace: ecommerce-dev

namePrefix: dev-

patches:
  - path: patches/dev-replicas.yaml
```

**overlays/prod/kustomization.yaml:**

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namespace: ecommerce-prod

nameSuffix: -prod

images:
  - name: order-service
    newName: ghcr.io/myorg/order-service
    newTag: "1.5.0"

patches:
  - path: patches/prod-replicas.yaml
  - path: patches/prod-resources.yaml
```

### 빌드 및 적용

```bash
# dev 환경 렌더링
kustomize build k8s/overlays/dev | kubectl apply -f -

# prod 환경 렌더링
kustomize build k8s/overlays/prod | kubectl apply -f -

# kubectl 내장 Kustomize 지원
kubectl apply -k k8s/overlays/prod
```

---

## 3. ConfigMap / Secret 생성 패턴

### configMapGenerator 사용

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

configMapGenerator:
  # 리터럴 값으로 생성
  - name: order-service-config
    literals:
      - LOG_LEVEL=info
      - DB_HOST=postgres.ecommerce.svc.cluster.local
      - DB_PORT=5432

  # 파일에서 생성
  - name: order-service-nginx
    files:
      - nginx.conf

  # env 파일에서 생성
  - name: order-service-env
    envs:
      - order-service.env

  # 기존 ConfigMap에 병합
  - name: shared-config
    behavior: merge
    literals:
      - SHARED_KEY=shared-value
```

### Secret 생성 패턴

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

secretGenerator:
  - name: order-service-secret
    literals:
      - DB_PASSWORD=changeme
      - API_KEY=dev-key-12345
    type: Opaque

  # 파일 기반 Secret
  - name: tls-secret
    files:
      - tls.crt
      - tls.key
    type: kubernetes.io/tls
```

### ConfigMap/Secret 해시 기반 롤링 업데이트

- configMapGenerator로 생성된 ConfigMap 이름은 `<name>-<hash>` 형식
- ConfigMap 내용 변경 → 해시 변경 → 참조하는 Deployment pod template hash 변경 → 자동 롤링 업데이트
- SecretGenerator도 동일 패턴 적용

---

## 4. Patch 전략 선택 가이드

### strategic merge patch vs JSON patch

| 기준 | strategic merge patch | JSON patch (RFC 6902) |
| --- | --- | --- |
| 문법 | 전체 YAML 조각 | op/path/value 배열 |
| 가독성 | 높음(원본 YAML과 유사) | 낮음(경로 기반) |
| 리스트 조작 | 전체 교체(merge 전략) | add/remove/replace 정밀 제어 |
| 필드 추가 | 간단 | 경로 명시 필요 |
| 네임스페이스 내 리소스 선택 | apiVersion/kind/metadata.name으로 자동 매칭 | target 필드 명시 필요 |

### strategic merge patch 사용 시기

```yaml
# replicas 변경 — 단순 필드 교체
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
spec:
  replicas: 5
```

```yaml
# labels/annotations 추가
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
  labels:
    team: backend
    cost-center: engineering
```

```yaml
# env 변수 주입
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
spec:
  template:
    spec:
      containers:
        - name: order-service
          env:
            - name: FEATURE_FLAG
              value: "enabled"
```

### JSON patch 사용 시기

```yaml
# 리스트의 특정 인덱스에 항목 추가
- op: add
  path: /spec/template/spec/containers/0/env/-
  value:
    name: NEW_VAR
    value: new-value

# 특정 필드 교체
- op: replace
  path: /spec/replicas
  value: 10

# 필드 삭제
- op: remove
  path: /metadata/labels/deprecated-label
```

### target 기반 patch 선택 (kustomize v4+)

```yaml
patches:
  # target으로 리소스 지정
  - target:
      kind: Deployment
      labelSelector: "app=order-service"
    patch: |
      - op: replace
        path: /spec/replicas
        value: 3
```

---

## 5. namePrefix / nameSuffix 활용

### 사용 예시

```yaml
# staging 환경
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namePrefix: staging-

# prod 환경
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

nameSuffix: -eu
```

### 자동 업데이트 대상

Kustomize는 namePrefix/nameSuffix 적용 후 다음 참조를 자동으로 갱신:

| 참조 유형 | 예시 |
| --- | --- |
| Service selector | `selector: {app: order-service}` → `{app: staging-order-service}` |
| Volume ConfigMap | `configMap: {name: order-service-config}` → `{name: staging-order-service-config}` |
| Volume Secret | `secret: {secretName: order-service-secret}` → `{secretName: staging-order-service-secret}` |
| env valueFrom configMapKeyRef | `configMapKeyRef.name` 자동 갱신 |
| env valueFrom secretKeyRef | `secretKeyRef.name` 자동 갱신 |

### 주의사항

- namePrefix/nameSuffix는 모든 리소스에 일괄 적용
- 특정 리소스만 제외하려면 `namePrefix` 대신 patches 활용
- cross-reference가 없는 리소스(예: Namespace 자체)는 이름만 변경되고 다른 리소스에 영향 없음

---

## 6. images 필드 상세

### 이미지 교체 옵션

```yaml
images:
  # 태그만 변경
  - name: order-service
    newTag: "1.5.0"

  # 저장소 경로 변경
  - name: order-service
    newName: ghcr.io/myorg/order-service

  # 다이제스트로 고정
  - name: order-service
    newTag: "sha256:abc123..."

  # newName과 newTag 동시 적용
  - name: order-service
    newName: ghcr.io/myorg/order-service
    newTag: "1.5.0"
```

### images 필드 규칙

- `name`은 base manifest의 container.image.name과 정확히 일치해야 함
- `newName`은 전체 이미지 경로(레지스트리 포함)로 지정
- `newTag`는 태그 또는 다이제스트(`sha256:` 접두사)
- `digest` 필드는 deprecated — `newTag`에 `sha256:` 형식 사용 권장

---

## 7. 공통 모범 사례

### 리소스 순서

kustomization.yaml에서 필드 순서는 다음 권장 순서 따름:

1. `resources` — 기본 리소스 목록
2. `namespace` — 대상 네임스페이스
3. `namePrefix` / `nameSuffix` — 이름 변환
4. `commonLabels` / `commonAnnotations` — 공통 메타데이터
5. `images` — 이미지 태그 교체
6. `configMapGenerator` / `secretGenerator` — 생성기
7. `patches` — 환경별 패치

### 버전 고정

- production overlay에서는 `newTag`에 SHA 다이제스트 사용 권장
- dev/staging에서는 시맨틱 태그(`1.5.0`) 허용
- base에는 기본 태그 또는 latest 미사용

### 검증

```bash
# 렌더링 결과 확인
kustomize build k8s/overlays/prod

# diff 확인
kustomize build k8s/overlays/prod | kubectl diff -f -

# 적용
kustomize build k8s/overlays/prod | kubectl apply -f -
```
