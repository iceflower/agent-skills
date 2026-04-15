---
name: tekton-workflow
description: >-
  Kubernetes-native CI/CD pipeline system including Task, Pipeline, Trigger CRDs,
  workspace sharing, Artifact Hub reuse, and CI/CD integration patterns.
  Use when building or reviewing Tekton pipelines on Kubernetes.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-04"
compatibility: Requires Tekton CLI (tkn) and Kubernetes cluster with Tekton installed
---

# Tekton Workflow Rules

## 1. Tekton Architecture

### Core CRDs

| CRD | Purpose | Scope |
| --- | --- | --- |
| `Task` | Reusable step definition (container sequence) | Namespace |
| `ClusterTask` | Cluster-wide reusable Task | Cluster |
| `TaskRun` | Single Task execution instance | Namespace |
| `Pipeline` | Ordered Task graph with params/workspaces | Namespace |
| `PipelineRun` | Single Pipeline execution instance | Namespace |
| `EventListener` | Webhook receiver that triggers pipelines | Namespace |
| `TriggerBinding` | Extracts event fields into params | Namespace |
| `TriggerTemplate` | Template for creating TaskRun/PipelineRun | Namespace |

### Execution Model

- Each `TaskRun` creates one Kubernetes Pod
- Each `step` inside a Task runs as a separate container within that Pod
- Steps execute **sequentially** by default
- Sidecars run in parallel with steps (same Pod, shared network/filesystem)
- Results flow through workspace files or `/tekton/results` directory

### Modular Installation

Tekton is installed in modular components:

```bash
# Core pipeline engine
kubectl apply -f https://storage.googleapis.com/tekton-releases/pipeline/latest/release.yaml

# Triggers (EventListener, webhook handling)
kubectl apply -f https://storage.googleapis.com/tekton-releases/triggers/latest/release.yaml

# Dashboard (optional UI)
kubectl apply -f https://storage.googleapis.com/tekton-releases/dashboard/latest/release.yaml
```

All components install into the `tekton-pipelines` namespace.

### Tekton CLI (`tkn`)

```bash
# View pipeline runs
tkn pipelinerun ls -n my-namespace

# View logs
tkn pipelinerun logs <pipeline-run-name> -f -n my-namespace

# Start pipeline manually
tkn pipeline start my-pipeline -n my-namespace
```

---

## 2. Task Authoring

### Task Structure

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: build-task
  namespace: ci-cd
spec:
  params:
    - name: IMAGE_URL
      type: string
      description: "Target container image URL"

  workspaces:
    - name: source
      description: "Source code workspace"
      mountPath: /workspace/source

  results:
    - name: IMAGE_DIGEST
      description: "Built image digest"

  steps:
    - name: build
      image: ghcr.io/containers/buildah:latest
      workingDir: $(workspaces.source.path)
      script: |
        buildah bud -t $(params.IMAGE_URL) .
        buildah push $(params.IMAGE_URL)
        RESULT=$(buildah inspect --format '{{.Digest}}' $(params.IMAGE_URL))
        echo -n "$RESULT" > $(results.IMAGE_DIGEST.path)
      securityContext:
        runAsNonRoot: false
        capabilities:
          add:
            - SETFCAP
```

### Key Fields

| Field | Purpose | Notes |
| --- | --- | --- |
| `params` | Input parameters | Supports `string` and `array` types |
| `workspaces` | Shared volume mounts | PVC, emptyDir, ConfigMap, Secret |
| `results` | Output values | Written to files, read by downstream Tasks |
| `steps` | Sequential containers | Order matters; exit code 0 = success |
| `stepTemplate` | Default config for all steps | Security context, env vars |
| `sidecars` | Parallel containers | Long-running services (dind, docker daemon) |
| `stepActions` | Reusable step definitions | **GA since v1.8** — no feature flag needed |

### StepActions (Reusable Steps)

`StepAction` lets you define reusable steps that can be referenced across multiple Tasks:

```yaml
# Define a reusable StepAction
apiVersion: tekton.dev/v1
kind: StepAction
metadata:
  name: build-image
spec:
  params:
    - name: IMAGE
      type: string
  image: ghcr.io/containers/buildah:latest
  script: |
    buildah bud -t $(params.IMAGE) .
    buildah push $(params.IMAGE)
```

```yaml
# Reference in a Task
steps:
  - name: build
    ref:
      name: build-image
    params:
      - name: IMAGE
        value: $(params.IMAGE_URL)
```

- StepActions are **stable (GA)** since Tekton Pipelines v1.8 — no `enable-step-actions` feature flag needed
- Use for common operations (build, test, scan) shared across multiple Tasks

### Params and Results

```yaml
# Using params in steps
env:
  - name: TARGET_VERSION
    value: $(params.VERSION)

script: |
  echo "Building version $(params.VERSION)"
  echo -n "output-value" > $(results.MY_RESULT.path)
```

### Workspace Types

| Volume Type | Use Case | Persistence |
| --- | --- | --- |
| `PersistentVolumeClaim` | Cross-Task data sharing | Survives Pod restart |
| `emptyDir` | Within-Pipeline temporary data | Deleted when Pod ends |
| `ConfigMap` | Read-only config injection | Static |
| `Secret` | Read-only secret injection | Static |

---

## 3. Pipeline Design

### Pipeline Structure

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: order-service-pipeline
  namespace: ci-cd
spec:
  params:
    - name: REPO_URL
      type: string
    - name: IMAGE_URL
      type: string
    - name: DEPLOY_ENV
      type: string
      default: "staging"

  workspaces:
    - name: shared-workspace
    - name: registry-credentials

  tasks:
    - name: fetch-source
      taskRef:
        name: git-clone
      workspaces:
        - name: output
          workspace: shared-workspace
      params:
        - name: url
          value: $(params.REPO_URL)

    - name: run-tests
      runAfter:
        - fetch-source
      taskRef:
        name: maven-test
      workspaces:
        - name: source
          workspace: shared-workspace

    - name: build-image
      runAfter:
        - run-tests
      taskRef:
        name: buildah
      workspaces:
        - name: source
          workspace: shared-workspace
        - name: dockerconfig
          workspace: registry-credentials
      params:
        - name: IMAGE
          value: $(params.IMAGE_URL)

    - name: deploy
      runAfter:
        - build-image
      taskRef:
        name: kubernetes-actions
      workspaces:
        - name: source
          workspace: shared-workspace
      params:
        - name: SCRIPT
          value: |
            kubectl set image deployment/order-service \
              order-service=$(params.IMAGE_URL) \
              -n $(params.DEPLOY_ENV)
```

### Design Principles

- Use `runAfter` to define explicit execution order (not implicit workspace dependency)
- Share workspaces across Tasks by referencing the same Pipeline workspace
- Pass params from Pipeline to Task via `$(params.NAME)` substitution
- Keep each Task single-responsibility — compose via Pipeline orchestration
- Use Pipeline-level params for values that multiple Tasks need

### Parallel Tasks

Tasks without `runAfter` dependencies run in parallel:

```yaml
tasks:
  - name: unit-test
    taskRef:
      name: maven-test
    runAfter:
      - fetch-source

  - name: lint
    taskRef:
      name: code-lint
    runAfter:
      - fetch-source

  - name: build
    runAfter:
      - unit-test
      - lint
    taskRef:
      name: build-image
```

---

## 4. Task Reuse (Artifact Hub)

> **Important**: The public Tekton Hub (`hub.tekton.dev`) was **shut down on January 8, 2026** and the repository was archived. Use Artifact Hub or self-hosted alternatives instead.

### Finding Tasks on Artifact Hub

```bash
# Browse tasks on Artifact Hub
# https://artifacthub.io/packages/search?kind=14

# Install from Tekton Catalog (manual YAML apply)
kubectl apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/git-clone/0.9/git-clone.yaml
```

### Common Catalog Tasks

| Task | Purpose | Source |
| --- | --- | --- |
| `git-clone` | Clone git repository | Tekton Catalog |
| `buildah` | Build and push container images | Tekton Catalog |
| `maven` | Maven build, test, package | Tekton Catalog |
| `kubernetes-actions` | kubectl operations | Tekton Catalog |
| `argocd-task-sync-and-wait` | Argo CD sync from pipeline | Tekton Catalog |

### Self-Hosted Hub

If your team needs a searchable Hub experience, deploy a self-hosted instance:

- [OpenShift Pipelines Hub](https://github.com/openshift-pipelines/hub) — forkable Tekton Hub implementation
- Catalog YAML files can be vendored into your own repository and applied via GitOps

### Using ClusterTasks

```yaml
# Reference a ClusterTask (available cluster-wide)
taskRef:
  name: git-clone
  kind: ClusterTask
  apiVersion: tekton.dev/v1

# Reference a namespace Task
taskRef:
  name: custom-build
  kind: Task
  apiVersion: tekton.dev/v1
```

### Reuse Over Rewrite

- Always check the [Tekton Catalog](https://github.com/tektoncd/catalog) before writing custom Tasks
- Catalog Tasks are maintained, tested, and follow best practices
- Extend Catalog Tasks via wrapper Tasks when customization is needed
- Vendor Catalog Task YAMLs into your own repo for version control

---

## 5. Triggers

### Trigger Components

| Component | Role |
| --- | --- |
| `EventListener` | HTTP endpoint that receives webhook events |
| `TriggerBinding` | Extracts JSON fields from event body → params |
| `TriggerTemplate` | Parametrized template for TaskRun/PipelineRun |
| `Interceptor` | Filters and modifies events before triggering |

### Basic Trigger Setup

```yaml
# TriggerBinding — extract params from webhook payload
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerBinding
metadata:
  name: order-service-binding
  namespace: ci-cd
spec:
  params:
    - name: git-revision
      value: $(body.head_commit.id)
    - name: git-repo-url
      value: $(body.repository.url)
    - name: git-repo-name
      value: $(body.repository.name)

---
# TriggerTemplate — define what to create
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerTemplate
metadata:
  name: order-service-template
  namespace: ci-cd
spec:
  params:
    - name: git-revision
    - name: git-repo-url
    - name: git-repo-name
  respecTemplates:
    - apiVersion: tekton.dev/v1
      kind: PipelineRun
      metadata:
        generateName: order-service-pipeline-run-
      spec:
        pipelineRef:
          name: order-service-pipeline
        params:
          - name: REPO_URL
            value: $(tt.params.git-repo-url)
          - name: GIT_REVISION
            value: $(tt.params.git-revision)

---
# EventListener — webhook endpoint
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: order-service-listener
  namespace: ci-cd
spec:
  serviceAccountName: tekton-triggers-sa
  triggers:
    - name: github-push
      bindings:
        - ref: order-service-binding
      template:
        ref: order-service-template
      interceptors:
        - ref:
            name: "github"
          params:
            - name: secretRef
              value:
                secretName: github-webhook-secret
                secretKey: secretToken
            - name: eventTypes
              value: ["push"]
```

For detailed trigger patterns including interceptors, multi-provider webhooks, and security configuration, see [references/triggers.md](references/triggers.md).

---

## 6. CI/CD Integration

### Tekton + Kustomize

Use `kubernetes-actions` or custom Task to run Kustomize builds within a pipeline:

```yaml
- name: deploy-kustomize
  taskRef:
    name: kubernetes-actions
  runAfter:
    - build-image
  workspaces:
    - name: source
      workspace: shared-workspace
  params:
    - name: SCRIPT
      value: |
        kustomize build ./k8s/overlays/$(params.ENVIRONMENT) | \
          kubectl apply -f -
```

> For detailed Kustomize patterns (overlay structure, patches, multi-env management), see [k8s-workflow](../k8s-workflow/) skill.

### Tekton + Helm

Deploy via Helm upgrade within a pipeline step:

```yaml
- name: deploy-helm
  taskRef:
    name: helm-upgrade
  runAfter:
    - build-image
  params:
    - name: CHART_PATH
      value: ./helm/order-service
    - name: RELEASE_NAME
      value: order-service
    - name: NAMESPACE
      value: $(params.DEPLOY_ENV)
    - name: VALUES
      value: |
        image:
          tag: $(tasks.build-image.results.IMAGE_TAG)
```

> For detailed Helm patterns (chart structure, values management, release lifecycle), see [helm-workflow](../helm-workflow/) skill.

### Tekton vs GitHub Actions — Selection Guide

| Criteria | Tekton | GitHub Actions |
| --- | --- | --- |
| Runtime | Kubernetes-native | GitHub-hosted runners |
| Portability | Any K8s cluster | GitHub ecosystem |
| Reuse | Tekton Hub + ClusterTask | Marketplace Actions |
| Triggers | Webhook (EventListener) | GitHub events |
| Best for | K8s-first teams, multi-cluster, custom infra | GitHub-hosted repos, simple CI/CD |
| Learning curve | Higher (K8s, CRDs, YAML) | Lower (workflow YAML) |

**Choose Tekton when:**

- Infrastructure is Kubernetes-centric
- Need multi-cluster or hybrid cloud CI/CD
- Want to reuse Tasks across teams via Tekton Hub
- Need fine-grained control over build environment

**Choose GitHub Actions when:**

- Code is on GitHub and CI needs are straightforward
- Want quick setup without managing build infrastructure
- Community Actions cover most needs

---

## 7. Related Skills

- For Kustomize overlay patterns and K8s manifest conventions, see [k8s-workflow](../k8s-workflow/) skill
- For Helm chart development and release management, see [helm-workflow](../helm-workflow/) skill
- For GitOps deployment with Argo CD, see [gitops-argocd](../gitops-argocd/) skill
- For GitHub Actions CI/CD patterns, see [ci-cd](../ci-cd/) skill
- For container image best practices, see [dockerfile](../dockerfile/) skill
- For secret management (ESO, Sealed Secrets), see [secrets-management](../secrets-management/) skill

## Additional References

- For workspace sharing, ServiceAccount patterns, and PipelineRun execution patterns, see [references/pipeline-patterns.md](references/pipeline-patterns.md)
- For EventListener setup, webhook integration, and interceptor patterns, see [references/triggers.md](references/triggers.md)

---

## 8. Anti-Patterns

- Running container image push without a ServiceAccount with proper registry credentials
- Attempting to share data between Tasks without defining a shared workspace
- Using hardcoded image tags in Pipeline definitions instead of params or results
- Manually creating PipelineRun repeatedly instead of using Triggers for automation
- Re-implementing tasks that already exist in Tekton Hub (always check Hub first)
- Using `latest` tag for Task step container images — pin to specific versions
- Defining excessive permissions in Task ServiceAccount — follow least privilege
- Not setting resource limits on Task pods — can starve cluster resources
- Mixing CI and CD concerns in a single Task — separate build, test, deploy responsibilities
- Ignoring Tekton version compatibility when referencing Hub Tasks across Tekton releases
