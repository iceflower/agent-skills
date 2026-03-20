# Template Best Practices

## Helper Templates (_helpers.tpl)

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

## Template Functions

| Function | Usage | Purpose |
| --- | --- | --- |
| `include` | `{{ include "mychart.labels" . }}` | Render named template as string |
| `tpl` | `{{ tpl .Values.config . }}` | Render string as template |
| `toYaml` | `{{ toYaml .Values.resources \| nindent 4 }}` | Convert to YAML with indent |
| `required` | `{{ required "image.tag is required" .Values.image.tag }}` | Fail if value missing |
| `default` | `{{ default "ClusterIP" .Values.service.type }}` | Provide fallback value |
| `quote` | `{{ .Values.name \| quote }}` | Wrap in double quotes |

## Whitespace Control

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

## NOTES.txt

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

## Testing

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
