# Pipeline Patterns Reference

## Workspace Sharing Patterns

### PVC (PersistentVolumeClaim) — Cross-Run Persistence

Use PVC when data needs to persist across PipelineRuns or when builds produce large artifacts that benefit from caching.

```yaml
# Persistent workspace claim in PipelineRun
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: order-service-run-001
  namespace: ci-cd
spec:
  pipelineRef:
    name: order-service-pipeline
  workspaces:
    - name: shared-workspace
      volumeClaimTemplate:
        spec:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 1Gi
          storageClassName: standard
```

**When to use:**

- Maven/Gradle dependency caching across runs
- Large build artifacts reused between pipelines
- Build cache that should survive Pod rescheduling

**Trade-offs:**

- PVC provisioning adds latency on first use
- Storage costs accumulate if not cleaned up
- Requires storage provisioner in the cluster

### emptyDir — Temporary, In-Pipeline Data

Use `emptyDir` when data only needs to be shared within a single PipelineRun and can be discarded afterward.

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: order-service-run-002
  namespace: ci-cd
spec:
  pipelineRef:
    name: order-service-pipeline
  workspaces:
    - name: shared-workspace
      emptyDir: {}
```

**When to use:**

- Git source cloned in one Task, consumed by the next
- Build artifacts passed from compile to package step
- Temporary files that do not need persistence

**Trade-offs:**

- Data lost when Pod terminates
- No caching benefit across PipelineRuns
- Faster provisioning (no PV claim needed)

### Decision Matrix

| Requirement | Volume Type |
| --- | --- |
| Share data within one PipelineRun | `emptyDir` |
| Cache dependencies across runs | `PersistentVolumeClaim` |
| Inject read-only config | `ConfigMap` |
| Inject credentials | `Secret` |
| Large artifact storage (>10Gi) | `PersistentVolumeClaim` with appropriate storageClass |

### PVC Auto-Cleanup (v1.11+)

When using `volumeClaimTemplate` in PipelineRun, Tekton v1.11+ supports automatic PVC cleanup:

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: order-service-run-006
  annotations:
    tekton.dev/auto-cleanup-pvc: "true"
spec:
  pipelineRef:
    name: order-service-pipeline
  workspaces:
    - name: shared-workspace
      volumeClaimTemplate:
        spec:
          accessModes: [ReadWriteOnce]
          resources:
            requests:
              storage: 1Gi
```

- The `tekton.dev/auto-cleanup-pvc: "true"` annotation automatically deletes PVCs after PipelineRun completes
- Only applies to `volumeClaimTemplate`-created PVCs — user-provided PVCs are never deleted
- Prevents storage accumulation from ephemeral pipeline runs

---

## ServiceAccount Per-Task Patterns

### Pipeline-Level ServiceAccount

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: order-service-run-003
spec:
  pipelineRef:
    name: order-service-pipeline
  serviceAccountName: pipeline-sa
  workspaces:
    - name: shared-workspace
      emptyDir: {}
```

### Task-Specific ServiceAccount Override

Different Tasks may need different credentials. Use `taskRunSpecs` to override ServiceAccount per Task:

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: order-service-run-004
spec:
  pipelineRef:
    name: order-service-pipeline
  taskRunSpecs:
    - pipelineTaskName: build-image
      taskServiceAccountName: registry-push-sa
    - pipelineTaskName: deploy
      taskServiceAccountName: cluster-deploy-sa
    - pipelineTaskName: fetch-source
      taskServiceAccountName: git-clone-sa
  workspaces:
    - name: shared-workspace
      emptyDir: {}
```

### ServiceAccount Design

| ServiceAccount | Required Permissions | Used By |
| --- | --- | --- |
| `git-clone-sa` | Read access to git repositories (SSH key Secret) | Source fetch Tasks |
| `registry-push-sa` | Push access to container registry | Build/push Tasks |
| `cluster-deploy-sa` | `deploy` Role on target namespace | Deploy Tasks |
| `pipeline-sa` | Minimal — Triggers, EventListener binding | General pipeline execution |

**Security rules:**

- Never use the default ServiceAccount for registry or cluster operations
- Scope ServiceAccount RBAC to the minimum required namespace and verbs
- Use separate ServiceAccounts for read vs write operations
- Rotate registry credentials stored as Secrets

---

## PipelineRun Parameter Passing

### Defining and Passing Params

```yaml
# Pipeline definition with params
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: order-service-pipeline
spec:
  params:
    - name: REPO_URL
      type: string
    - name: IMAGE_TAG
      type: string
      default: latest
    - name: ENVIRONMENT
      type: string
      default: staging
    - name: ENABLE_TESTS
      type: string
      default: "true"

  tasks:
    - name: fetch-source
      taskRef:
        name: git-clone
      params:
        - name: url
          value: $(params.REPO_URL)
```

```yaml
# PipelineRun providing param values
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: order-service-run-005
spec:
  pipelineRef:
    name: order-service-pipeline
  params:
    - name: REPO_URL
      value: https://github.com/myorg/order-service.git
    - name: IMAGE_TAG
      value: v1.2.3
    - name: ENVIRONMENT
      value: production
```

### Array Params

```yaml
# Pipeline with array param
params:
  - name: TARGET_ENVIRONMENTS
    type: array
    default:
      - staging
      - production

tasks:
  - name: deploy-all
    taskRef:
      name: deploy-task
    params:
      - name: envs
        value: $(params.TARGET_ENVIRONMENTS)
```

---

## PipelineRun Rerun Patterns

### Manual Rerun via tkn

```bash
# Rerun the most recent PipelineRun
tkn pipeline start order-service-pipeline \
  --last \
  --namespace ci-cd

# Rerun with new param values
tkn pipeline start order-service-pipeline \
  --last \
  --param IMAGE_TAG=v1.2.4 \
  --namespace ci-cd
```

### Rerun via YAML

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: order-service-rerun-001
  namespace: ci-cd
spec:
  pipelineRef:
    name: order-service-pipeline
  # Copy params from the original run, modify as needed
  params:
    - name: REPO_URL
      value: https://github.com/myorg/order-service.git
    - name: IMAGE_TAG
      value: v1.2.3-hotfix
```

### Restart from Failed Task

Tekton does not natively support "resume from failed task." Common strategies:

1. **Rerun entire Pipeline** — simplest, but repeats successful steps
2. **Pipeline-level condition checks** — check if previous step artifacts exist, skip if present
3. **Separate Pipeline for retry** — create a deployment-only Pipeline that skips build/test

```yaml
# Pattern: skip build if image already exists
- name: build-image
  taskRef:
    name: buildah
  when:
    - input: "$(tasks.check-image.results.IMAGE_EXISTS)"
      operator: in
      values: ["false"]
```

### Automated Rerun on Failure

```yaml
# Using Tekton custom task or external controller
# Alternative: GitHub Actions wrapper that calls tkn on failure
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: order-service-run-with-retry
  annotations:
    pipeline.tekton.dev/timeout: "2h"   # Extended timeout for retries
spec:
  pipelineRef:
    name: order-service-pipeline
  timeout: "2h"
```

Set `timeout` at both Pipeline and PipelineRun level to control execution windows.
