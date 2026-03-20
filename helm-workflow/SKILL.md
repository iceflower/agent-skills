---
name: helm-workflow
description: >-
  Helm chart development and release management including chart structure,
  values design, template best practices, hooks, dependency management,
  testing, and repository management. Covers Helm vs Kustomize selection.
  Use when creating, reviewing, or managing Helm charts.
---

# Helm Workflow Rules

## 1. Chart Structure

### Standard Directory Layout

```text
mychart/
├── Chart.yaml          # Chart metadata (required)
├── Chart.lock          # Dependency lock file (auto-generated)
├── values.yaml         # Default configuration values
├── values.schema.json  # JSON Schema for values validation
├── .helmignore         # Patterns to ignore when packaging
├── templates/          # Template files
│   ├── _helpers.tpl    # Named template definitions
│   ├── NOTES.txt       # Post-install usage notes
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── serviceaccount.yaml
│   ├── hpa.yaml
│   └── tests/
│       └── test-connection.yaml
├── charts/             # Dependency charts (auto-populated)
└── crds/               # Custom Resource Definitions
```

### Chart.yaml Conventions

```yaml
apiVersion: v2
name: myapp
description: A Helm chart for MyApp
type: application          # application or library
version: 1.2.0             # Chart version (SemVer)
appVersion: "3.4.1"        # Application version
kubeVersion: ">=1.28.0"    # Required K8s version constraint

maintainers:
  - name: team-platform
    email: platform@example.com

dependencies:
  - name: postgresql
    version: "~15.x"
    repository: "oci://registry-1.docker.io/bitnamicharts"
    condition: postgresql.enabled
```

| Field | Rule |
| --- | --- |
| `version` | SemVer — bump on every chart change |
| `appVersion` | Match the deployed application version |
| `kubeVersion` | Set minimum K8s version constraint |
| `type` | Use `library` for shared templates only |

---

## 2. Values Design

### Organization Principles

```yaml
# Group by component, not by K8s resource type
replicaCount: 2

image:
  repository: myapp
  tag: "3.4.1"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8080

ingress:
  enabled: false
  className: nginx
  hosts:
    - host: myapp.example.com
      paths:
        - path: /
          pathType: Prefix

resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi

# Sub-chart toggle
postgresql:
  enabled: true
```

### Naming Conventions

| Pattern | Example | Purpose |
| --- | --- | --- |
| Boolean toggle | `ingress.enabled` | Enable/disable features |
| camelCase keys | `replicaCount` | Helm convention |
| Nested objects | `image.repository` | Group related config |
| Resource presets | `resources.requests.cpu` | Standard K8s structure |

### Values Schema Validation

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["image", "service"],
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 1
    },
    "image": {
      "type": "object",
      "required": ["repository"],
      "properties": {
        "repository": { "type": "string" },
        "tag": { "type": "string" }
      }
    }
  }
}
```

### Environment-Specific Values

```text
values/
├── values.yaml            # Defaults
├── values-dev.yaml        # Dev overrides
├── values-staging.yaml    # Staging overrides
└── values-prod.yaml       # Production overrides
```

```bash
helm upgrade myapp ./mychart \
  -f values.yaml \
  -f values-prod.yaml \
  --namespace production
```

---

## 3. Template Best Practices

### Helper Templates (_helpers.tpl)

```yaml
{{/* Generate standard labels */}}
{{- define "mychart.labels" -}}
helm.sh/chart: {{ include "mychart.chart" . }}
app.kubernetes.io/name: {{ include "mychart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/* Generate selector labels */}}
{{- define "mychart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mychart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* Fullname with 63 char limit */}}
{{- define "mychart.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
```

### Template Functions

| Function | Usage | Purpose |
| --- | --- | --- |
| `include` | `{{ include "mychart.labels" . }}` | Render named template as string |
| `tpl` | `{{ tpl .Values.config . }}` | Render string as template |
| `toYaml` | `{{ toYaml .Values.resources \| nindent 4 }}` | Convert to YAML with indent |
| `required` | `{{ required "image.tag is required" .Values.image.tag }}` | Fail if value missing |
| `default` | `{{ default "ClusterIP" .Values.service.type }}` | Provide fallback value |
| `quote` | `{{ .Values.name \| quote }}` | Wrap in double quotes |

### Whitespace Control

```yaml
# Use {{- and -}} to trim whitespace
metadata:
  labels:
    {{- include "mychart.labels" . | nindent 4 }}

# Conditional blocks — trim leading/trailing whitespace
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
{{- end }}
```

### NOTES.txt

```text
Thank you for installing {{ .Chart.Name }}.

Your release is named {{ .Release.Name }}.

To access the application:
{{- if .Values.ingress.enabled }}
  Visit: http{{ if .Values.ingress.tls }}s{{ end }}://{{ (index .Values.ingress.hosts 0).host }}
{{- else }}
  kubectl port-forward svc/{{ include "mychart.fullname" . }} {{ .Values.service.port }}:{{ .Values.service.port }}
{{- end }}
```

---

## 4. Release Management

### Naming Conventions

| Element | Convention | Example |
| --- | --- | --- |
| Release name | `{app}-{env}` or `{app}` | `myapp-prod`, `myapp` |
| Namespace | Match environment | `production`, `staging` |
| Chart version | SemVer, bump on change | `1.2.0` → `1.3.0` |

### Install and Upgrade Commands

```bash
# Install with atomic (auto-rollback on failure)
helm install myapp ./mychart \
  --namespace production \
  --create-namespace \
  --atomic \
  --timeout 5m \
  -f values-prod.yaml

# Upgrade with wait (wait for pods ready)
helm upgrade myapp ./mychart \
  --namespace production \
  --atomic \
  --timeout 5m \
  --cleanup-on-fail \
  -f values-prod.yaml

# Install or upgrade (idempotent)
helm upgrade --install myapp ./mychart \
  --namespace production \
  --create-namespace \
  --atomic \
  --timeout 5m \
  -f values-prod.yaml
```

### Rollback

```bash
# View history
helm history myapp -n production

# Rollback to previous revision
helm rollback myapp 0 -n production --wait

# Rollback to specific revision
helm rollback myapp 3 -n production --wait
```

---

## 5. Hook Lifecycle

### Available Hooks

| Hook | Timing | Use Case |
| --- | --- | --- |
| `pre-install` | Before resources created | DB migration, prerequisite check |
| `post-install` | After resources created | Seed data, notifications |
| `pre-upgrade` | Before upgrade starts | DB migration, backup |
| `post-upgrade` | After upgrade completes | Cache warm-up, verification |
| `pre-delete` | Before release deleted | Data export, cleanup |
| `post-delete` | After release deleted | External resource cleanup |
| `pre-rollback` | Before rollback | Backup current state |
| `post-rollback` | After rollback | Verify rollback success |

### Hook Definition

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "mychart.fullname" . }}-db-migrate
  annotations:
    "helm.sh/hook": pre-upgrade,pre-install
    "helm.sh/hook-weight": "-5"          # Lower runs first
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  backoffLimit: 3
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          command: ["./migrate", "up"]
```

### Hook Delete Policies

| Policy | Behavior |
| --- | --- |
| `before-hook-creation` | Delete previous hook resource before new one |
| `hook-succeeded` | Delete after hook succeeds |
| `hook-failed` | Delete after hook fails |

---

## 6. Dependency Management

### Declaring Dependencies

```yaml
# Chart.yaml
dependencies:
  - name: postgresql
    version: "~15.5"
    repository: "oci://registry-1.docker.io/bitnamicharts"
    condition: postgresql.enabled
    alias: db

  - name: redis
    version: "~19.x"
    repository: "oci://registry-1.docker.io/bitnamicharts"
    tags:
      - cache
    import-values:
      - child: master.service
        parent: redis.service
```

### Commands

```bash
# Download dependencies
helm dependency update ./mychart

# Rebuild Chart.lock
helm dependency build ./mychart

# List dependencies
helm dependency list ./mychart
```

### Sub-Chart Value Override

```yaml
# values.yaml — override sub-chart values by chart name
postgresql:
  enabled: true
  auth:
    database: myapp
    username: myapp

# Using alias
db:
  enabled: true
```

---

## 7. Testing

### Helm Built-in Testing

```yaml
# templates/tests/test-connection.yaml
apiVersion: v1
kind: Pod
metadata:
  name: "{{ include "mychart.fullname" . }}-test"
  annotations:
    "helm.sh/hook": test
spec:
  restartPolicy: Never
  containers:
    - name: test
      image: busybox
      command: ['wget', '-qO-', 'http://{{ include "mychart.fullname" . }}:{{ .Values.service.port }}']
```

```bash
helm test myapp -n production
```

### Validation Pipeline

| Tool | Purpose | Command |
| --- | --- | --- |
| `helm lint` | Syntax and best practice check | `helm lint ./mychart` |
| `helm template` | Render templates locally | `helm template myapp ./mychart -f values-prod.yaml` |
| `helm template \| kubectl apply --dry-run` | K8s API validation | `helm template myapp ./mychart \| kubectl apply --dry-run=server -f -` |
| `ct lint` | Chart-testing lint (CI) | `ct lint --chart-dirs charts/` |
| `ct install` | Chart-testing install (CI) | `ct install --chart-dirs charts/` |
| `kubeval` / `kubeconform` | Schema validation | `helm template . \| kubeconform -strict` |
| `helm-unittest` | Unit test templates | `helm unittest ./mychart` |

### helm-unittest Example

```yaml
# tests/deployment_test.yaml
suite: deployment tests
templates:
  - deployment.yaml
tests:
  - it: should set replica count
    set:
      replicaCount: 3
    asserts:
      - equal:
          path: spec.replicas
          value: 3

  - it: should use correct image
    set:
      image.repository: myapp
      image.tag: "1.0.0"
    asserts:
      - equal:
          path: spec.template.spec.containers[0].image
          value: "myapp:1.0.0"
```

---

## 8. Security

### Chart Signing

```bash
# Package and sign
helm package ./mychart --sign --key "my-key" --keyring ~/.gnupg/pubring.gpg

# Verify signature
helm verify mychart-1.2.0.tgz --keyring ~/.gnupg/pubring.gpg

# Install with verification
helm install myapp mychart-1.2.0.tgz --verify --keyring ~/.gnupg/pubring.gpg
```

### RBAC Templates

```yaml
{{- if .Values.serviceAccount.create }}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "mychart.fullname" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
  {{- with .Values.serviceAccount.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
{{- end }}
```

### Secrets Handling

- Never store plaintext secrets in `values.yaml`
- Use `--set` or external secret managers for sensitive values
- Template secrets from references, not hardcoded values
- Consider `ExternalSecret` or `SealedSecret` CRDs instead of Helm-managed secrets

---

## 9. Repository Management

### OCI Registry (Recommended)

```bash
# Login to OCI registry
helm registry login ghcr.io -u USERNAME

# Push chart
helm push mychart-1.2.0.tgz oci://ghcr.io/org/charts

# Pull chart
helm pull oci://ghcr.io/org/charts/mychart --version 1.2.0

# Install from OCI
helm install myapp oci://ghcr.io/org/charts/mychart --version 1.2.0
```

### Versioning Strategy

| Change Type | Version Bump | Example |
| --- | --- | --- |
| Breaking changes | Major | `1.2.0` → `2.0.0` |
| New features, non-breaking | Minor | `1.2.0` → `1.3.0` |
| Bug fixes, doc updates | Patch | `1.2.0` → `1.2.1` |

- Always bump `version` when chart content changes
- `appVersion` tracks the deployed application version independently

---

## 10. Helm vs Kustomize

| Criteria | Helm | Kustomize |
| --- | --- | --- |
| Parameterization | Values-based templating | Patch-based overlays |
| Packaging | Distributable chart archives | Directory-based |
| Dependency management | Built-in | Manual |
| Release tracking | Built-in (helm history) | External (GitOps) |
| Learning curve | Higher (Go templates) | Lower (YAML patches) |
| Best for | Reusable packages, complex logic | Simple overlays, in-house apps |

### When to Use Each

- **Helm**: Distributing charts to others, complex conditional logic, lifecycle hooks, release management
- **Kustomize**: Internal applications, simple environment overlays, no templating needed
- **Hybrid**: Use Helm for packaging + Kustomize for environment overlays (`helm template | kustomize`)

---

## 11. Anti-Patterns

- Using `helm install` without `--atomic` in CI/CD — leaves failed releases behind
- Hardcoding values in templates instead of using `values.yaml`
- Not setting `kubeVersion` constraint — chart may deploy to incompatible clusters
- Skipping `values.schema.json` — no validation on user-supplied values
- Using `lookup` function without fallback — breaks `helm template`
- Not bumping chart `version` on changes — cache serves stale charts
- Storing secrets in `values.yaml` committed to VCS
- Deeply nested values without documentation — users cannot discover options
- Using `helm install` instead of `helm upgrade --install` — not idempotent
- Ignoring `helm lint` and `helm template` in CI — catches errors too late
