# Triggers Reference

## EventListener + TriggerBinding + TriggerTemplate

### Complete Combination Example

The three Trigger CRDs work together to convert external webhook events into PipelineRun executions:

```text
Webhook Event → EventListener → Interceptor (filter/validate)
    → TriggerBinding (extract params) → TriggerTemplate (create PipelineRun)
```

```yaml
# 1. TriggerBinding — maps webhook JSON fields to params
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerBinding
metadata:
  name: generic-binding
  namespace: ci-cd
spec:
  params:
    - name: git-revision
      value: $(body.head_commit.id)
    - name: git-repo-url
      value: $(body.repository.clone_url)
    - name: git-repo-name
      value: $(body.repository.name)
    - name: trigger-event
      value: $(body.action)

---
# 2. TriggerTemplate — defines the PipelineRun to create
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerTemplate
metadata:
  name: generic-template
  namespace: ci-cd
spec:
  params:
    - name: git-revision
    - name: git-repo-url
    - name: git-repo-name
    - name: trigger-event
  specTemplates:
    - apiVersion: tekton.dev/v1
      kind: PipelineRun
      metadata:
        generateName: $(tt.params.git-repo-name)-run-
      spec:
        pipelineRef:
          name: generic-pipeline
        params:
          - name: REPO_URL
            value: $(tt.params.git-repo-url)
          - name: GIT_REVISION
            value: $(tt.params.git-revision)
          - name: TRIGGER_EVENT
            value: $(tt.params.trigger-event)
        workspaces:
          - name: shared-workspace
            emptyDir: {}

---
# 3. EventListener — exposes HTTP endpoint
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: generic-listener
  namespace: ci-cd
spec:
  serviceAccountName: tekton-triggers-sa
  triggers:
    - name: main-trigger
      bindings:
        - ref: generic-binding
      template:
        ref: generic-template
```

### Multiple Triggers in One EventListener

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: multi-trigger-listener
  namespace: ci-cd
spec:
  serviceAccountName: tekton-triggers-sa
  triggers:
    - name: push-trigger
      bindings:
        - ref: push-binding
      template:
        ref: build-template
      interceptors:
        - ref:
            name: "cel"
          params:
            - name: filter
              value: "body.ref == 'refs/heads/main'"

    - name: pr-trigger
      bindings:
        - ref: pr-binding
      template:
        ref: pr-check-template
      interceptors:
        - ref:
            name: "cel"
          params:
            - name: filter
              value: "body.action == 'opened' || body.action == 'synchronize'"
```

---

## GitHub Webhook Integration

### EventListener with GitHub Interceptor

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: github-listener
  namespace: ci-cd
spec:
  serviceAccountName: tekton-triggers-sa
  triggers:
    - name: github-push
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
        - ref:
            name: "cel"
          params:
            - name: filter
              value: "body.ref == 'refs/heads/main'"
      bindings:
        - ref: github-binding
      template:
        ref: github-template
```

### Secret Validation

```yaml
# Create the webhook secret
apiVersion: v1
kind: Secret
metadata:
  name: github-webhook-secret
  namespace: ci-cd
type: Opaque
stringData:
  secretToken: "your-webhook-secret-here"
```

Configure the same secret in GitHub repository settings:

1. Go to **Settings → Webhooks → Add webhook**
2. Set Payload URL to `http://el-github-listener.ci-cd.svc.cluster.local:8080`
3. Set Content type to `application/json`
4. Set Secret to the same value as `secretToken`
5. Select events: **Push** (or specific events)

### GitHub Binding for Push Events

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerBinding
metadata:
  name: github-binding
  namespace: ci-cd
spec:
  params:
    - name: git-revision
      value: $(body.head_commit.id)
    - name: git-repo-url
      value: $(body.repository.clone_url)
    - name: git-repo-name
      value: $(body.repository.name)
    - name: git-branch
      value: $(body.ref)
```

---

## GitLab Webhook Integration

### EventListener with GitLab Interceptor

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: gitlab-listener
  namespace: ci-cd
spec:
  serviceAccountName: tekton-triggers-sa
  triggers:
    - name: gitlab-push
      interceptors:
        - ref:
            name: "gitlab"
          params:
            - name: secretRef
              value:
                secretName: gitlab-webhook-secret
                secretKey: secretToken
            - name: eventTypes
              value: ["Push Hook"]
      bindings:
        - ref: gitlab-binding
      template:
        ref: gitlab-template
```

### GitLab Binding

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerBinding
metadata:
  name: gitlab-binding
  namespace: ci-cd
spec:
  params:
    - name: git-revision
      value: $(body.checkout_sha)
    - name: git-repo-url
      value: $(body.repository.git_http_url)
    - name: git-repo-name
      value: $(body.project.name)
    - name: git-branch
      value: $(body.ref)
```

### GitLab Webhook Configuration

1. Go to **Settings → Webhooks**
2. Set URL to `http://el-gitlab-listener.ci-cd.svc.cluster.local:8080`
3. Set Secret Token to the same value as `secretToken`
4. Trigger: **Push events**
5. Enable SSL verification if using HTTPS

---

## CEL Interceptor — Event Filtering

### Branch Filter

Only trigger on pushes to the `main` branch:

```yaml
interceptors:
  - ref:
      name: "cel"
    params:
      - name: filter
        value: "body.ref == 'refs/heads/main'"
```

### Path Filter

Only trigger when changes occur in specific directories:

```yaml
interceptors:
  - ref:
      name: "cel"
    params:
      - name: filter
        value: >
          body.commits.exists(c,
            c.added.exists(p, p.startsWith('src/')) ||
            c.modified.exists(p, p.startsWith('src/'))
          )
```

### Multiple Conditions

Trigger only for push events to `main` AND from specific repositories:

```yaml
interceptors:
  - ref:
      name: "cel"
    params:
      - name: filter
        value: >
          body.ref == 'refs/heads/main' &&
          body.repository.full_name == 'myorg/order-service'
```

### Overwrite Values

Modify event data before passing to TriggerBinding:

```yaml
interceptors:
  - ref:
      name: "cel"
    params:
      - name: overlays
        value:
          - key: truncated_sha
            expression: "body.head_commit.id.substring(0, 7)"
          - key: deploy_target
            expression: >
              body.ref.contains('release') ? 'production' : 'staging'
```

```yaml
# Use the overwritten value in TriggerBinding
params:
  - name: SHORT_SHA
    value: $(body.truncated_sha)
  - name: ENVIRONMENT
    value: $(body.deploy_target)
```

---

## GitHub Interceptor — PR Event Handling

### PR Opened / Synchronize

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: github-pr-listener
  namespace: ci-cd
spec:
  serviceAccountName: tekton-triggers-sa
  triggers:
    - name: pr-check
      interceptors:
        - ref:
            name: "github"
          params:
            - name: secretRef
              value:
                secretName: github-webhook-secret
                secretKey: secretToken
            - name: eventTypes
              value: ["pull_request"]
        - ref:
            name: "cel"
          params:
            - name: filter
              value: >
                body.action == 'opened' ||
                body.action == 'synchronize' ||
                body.action == 'reopened'
      bindings:
        - ref: pr-binding
      template:
        ref: pr-check-template
```

### PR Binding

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerBinding
metadata:
  name: pr-binding
  namespace: ci-cd
spec:
  params:
    - name: git-revision
      value: $(body.pull_request.head.sha)
    - name: git-repo-url
      value: $(body.repository.clone_url)
    - name: pr-number
      value: $(body.pull_request.number)
    - name: pr-branch
      value: $(body.pull_request.head.ref)
    - name: pr-base
      value: $(body.pull_request.base.ref)
```

### PR Check Template

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerTemplate
metadata:
  name: pr-check-template
  namespace: ci-cd
spec:
  params:
    - name: git-revision
    - name: git-repo-url
    - name: pr-number
    - name: pr-branch
    - name: pr-base
  specTemplates:
    - apiVersion: tekton.dev/v1
      kind: PipelineRun
      metadata:
        generateName: pr-check-$(tt.params.pr-number)-
      spec:
        pipelineRef:
          name: pr-check-pipeline
        params:
          - name: REPO_URL
            value: $(tt.params.git-repo-url)
          - name: GIT_REVISION
            value: $(tt.params.git-revision)
          - name: PR_NUMBER
            value: $(tt.params.pr-number)
          - name: PR_BRANCH
            value: $(tt.params.pr-branch)
        workspaces:
          - name: shared-workspace
            emptyDir: {}
```

---

## Trigger ServiceAccount

### Minimal RBAC for EventListener

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tekton-triggers-sa
  namespace: ci-cd
secrets:
  - name: github-webhook-secret
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tekton-triggers-role
  namespace: ci-cd
rules:
  - apiGroups: ["tekton.dev"]
    resources: ["pipelineruns", "taskruns"]
    verbs: ["create", "get", "list", "watch"]
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tekton-triggers-binding
  namespace: ci-cd
subjects:
  - kind: ServiceAccount
    name: tekton-triggers-sa
    namespace: ci-cd
roleRef:
  apiGroups: ["rbac.authorization.k8s.io"]
  kind: Role
  name: tekton-triggers-role
```

---

## Exposing EventListener Externally

### Ingress Configuration

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tekton-triggers-ingress
  namespace: ci-cd
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - tekton-triggers.example.com
      secretName: tekton-triggers-tls
  rules:
    - host: tekton-triggers.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: el-github-listener
                port:
                  number: 8080
```
