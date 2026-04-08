# Container and Supply Chain Security

## 1. Container Security Overview

### Defense-in-Depth Model

```text
Image Build → Registry Storage → Deployment → Runtime
     │              │               │            │
  Scan sign      Verify policy   Admission    Enforce
     │              │            control       seccomp
  Minimize       Trust chain    (Kyverno)     AppArmor
  base image     (Cosign)                    cap-drop
```

### Core Principles

- **Minimal attack surface**: Use the smallest possible image — distroless or Alpine when feasible
- **Never run as root**: All containers must run as non-root user
- **Immutable infrastructure**: Containers should be ephemeral and reproducible — no SSH, no shell access
- **Zero trust for images**: Verify signatures before running, never trust unsigned images
- **Shift left**: Catch vulnerabilities in CI, not in production

---

## 2. Image Security

### Base Image Selection

| Base Image | Size | Shell | Use Case |
| --- | --- | --- | --- |
| `scratch` | 0 MB | None | Static binaries (Go, Rust) |
| `distroless` | ~2 MB | None | JVM, Python apps (no shell attack surface) |
| `alpine` | ~5 MB | BusyBox | Need shell for debugging, small footprint |
| `debian-slim` | ~80 MB | bash | Compatibility with Debian packages |
| `ubuntu` | ~70 MB | bash | Full glibc, broad package support |

### Multi-Stage Build for Minimal Image

```dockerfile
# Build stage
FROM gradle:8-jdk21 AS builder
WORKDIR /app
COPY . .
RUN gradle bootJar --no-daemon

# Runtime stage (distroless)
FROM gcr.io/distroless/java21-debian12:non-root
COPY --from=builder /app/build/libs/*.jar /app/application.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/application.jar"]
```

### Vulnerability Scanning

| Tool | License | Registry Integration | CI Integration |
| --- | --- | --- | --- |
| Trivy | Apache 2.0 | Yes (server mode) | GitHub Actions, GitLab CI |
| Grype | Apache 2.0 | No | GitHub Actions |
| Snyk Container | Commercial | Yes | Native CI plugins |
| Docker Scout | Commercial | Docker Hub | GitHub Actions |

### Trivy Configuration

```bash
# Scan local image
trivy image --severity HIGH,CRITICAL myapp:latest

# Scan with exit code for CI
trivy image --exit-code 1 --severity HIGH,CRITICAL myapp:latest

# Ignore specific CVEs (temporary)
trivy image --ignorefile .trivyignore.json myapp:latest
```

```json
{
  "vulnerabilities": [
    { "id": "CVE-2024-12345", "status": "will_not_fix", "reason": "Not applicable to our usage" }
  ]
}
```

### Image Security Rules

- Pin image digest, not just tag: `FROM node:20.11.0-alpine@sha256:abc123...`
- Never use `latest` tag in production — pin to specific version
- Run vulnerability scan in CI pipeline, block deployment on HIGH/CRITICAL CVEs
- Rebuild images regularly to pick up base image security patches
- Use `.dockerignore` to exclude sensitive files: `.env`, `.git`, `*.key`, `credentials*`

---

## 3. Runtime Security

### Security Context (Kubernetes)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: app
      image: myapp:1.0.0
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop:
            - ALL
      volumeMounts:
        - name: tmp
          mountPath: /tmp
  volumes:
    - name: tmp
      emptyDir: {}
```

### Runtime Security Rules

| Rule | Why | How |
| --- | --- | --- |
| Run as non-root | Root in container = root on host (without user namespaces) | `runAsNonRoot: true`, `runAsUser: 1000` |
| Drop all capabilities | Linux capabilities grant host-level privileges | `capabilities.drop: [ALL]` |
| Read-only filesystem | Prevents runtime binary injection | `readOnlyRootFilesystem: true` |
| No privilege escalation | Prevents `setuid` binaries from gaining root | `allowPrivilegeEscalation: false` |
| Seccomp profile | Restricts available system calls | `seccompProfile: RuntimeDefault` |
| No privileged mode | Bypasses all container isolation | Never set `privileged: true` |

### Seccomp and AppArmor

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": ["SCMP_ARCH_X86_64"],
  "syscalls": [
    { "names": ["read", "write", "open", "close", "mmap", "brk"], "action": "SCMP_ACT_ALLOW" }
  ]
}
```

- **Seccomp**: Whitelist system calls — blocks unexpected kernel interaction
- **AppArmor**: File-level access control — restricts which files a process can read/write/execute
- Always use `RuntimeDefault` seccomp profile at minimum
- Custom profiles require extensive testing — start with default and iterate

---

## 4. Kubernetes Pod Security

### Pod Security Standards

| Level | Description | Use Case |
| --- | --- | --- |
| **Privileged** | No restrictions | System pods, node exporters |
| **Baseline** | Prevents known privilege escalations | Most workloads |
| **Restricted** | All security options hardened | Security-sensitive workloads |

### Pod Security Admission

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### Kyverno Policy Enforcement

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-image-registries
spec:
  validationFailureAction: Enforce
  rules:
    - name: validate-registry
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Images must come from approved registries"
        pattern:
          spec:
            containers:
              - image: "registry.example.com/*"
---
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-non-root
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-runasnonroot
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Containers must run as non-root"
        pattern:
          spec:
            securityContext:
              runAsNonRoot: true
```

---

## 5. Software Supply Chain Security

### SBOM (Software Bill of Materials)

#### SBOM Generation with Syft

```bash
# Generate SBOM from image
syft myapp:1.0.0 -o spdx-json > sbom.spdx.json

# Generate SBOM from directory
syft ./build -o cyclonedx-json > sbom.cyclone.json

# Generate and attach to image (OCI)
syft myapp:1.0.0 -o attestation-oci --attach --key cosign.key
```

#### SBOM Formats

| Format | Standard | Use Case |
| --- | --- | --- |
| SPDX | ISO/IEC 5962 | Interoperability, compliance |
| CycloneDX | OWASP | Securityfocus, vulnerability correlation |
| in-toto | CNCF | Attestation chain, build provenance |

### Image Signing with Cosign

```bash
# Generate key pair
cosign generate-key-pair

# Sign image
cosign sign --key cosign.key myapp:1.0.0

# Verify signature
cosign verify --key cosign.pub myapp:1.0.0

# Sign with GitHub OIDC (keyless)
cosign sign --yes myapp:1.0.0

# Verify keyless signature
cosign verify \
  --certificate-identity https://github.com/myorg/myrepo/.github/workflows/deploy.yml@refs/heads/main \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  myapp:1.0.0
```

### Keyless Signing in GitHub Actions

```yaml
name: Build and Sign

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Log in to registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          push: true
          tags: ghcr.io/myorg/myapp:${{ github.sha }}

      - name: Sign image with Cosign
        uses: sigstore/cosign-installer@v3
      - run: |
          cosign sign --yes ghcr.io/myorg/myapp:${{ github.sha }}
```

### SLSA Framework

| Level | Requirements | Guarantee |
| --- | --- | --- |
| SLSA 1 | Provenance exists | Documented build process |
| SLSA 2 | Hosted build platform, authenticated provenance | Build platform attests to build |
| SLSA 3 | Hardened build platform | Build platform is hardened against tampering |
| SLSA 4 | Hermetic + reproducible, two-party review | Highest confidence in build integrity |

### SLSA Provenance Example

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [
    { "name": "myapp", "digest": { "sha256": "abc123..." } }
  ],
  "predicateType": "https://slsa.dev/provenance/v1",
  "predicate": {
    "buildDefinition": {
      "buildType": "https://github.com/actions/workflow",
      "externalParameters": {
        "repository": "https://github.com/myorg/myapp",
        "ref": "refs/heads/main"
      }
    },
    "runDetails": {
      "builder": {
        "id": "https://github.com/actions"
      }
    }
  }
}
```

---

## 6. CI/CD Supply Chain Hardening

### Dependency Pinning

```yaml
# GitHub Actions: Pin action versions by SHA
steps:
  - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
  - uses: actions/setup-node@1d0ff469b7ec7b3cb9d8673fde0c81c44821de2a # v4.0.0
```

### Dependency Review

```yaml
name: Dependency Review

on:
  pull_request:
    paths:
      - 'package-lock.json'
      - 'yarn.lock'
      - '**/build.gradle*'

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: high
          deny-licenses: GPL-3.0, AGPL-3.0
```

### Build Provenance

```yaml
name: Build with Provenance

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      attestations: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Build artifact
        run: ./build.sh

      - name: Generate build provenance
        uses: actions/attest-build-provenance@v1
        with:
          subject-path: ./dist/app.jar
```

### Verified Commits

- Require signed commits on protected branches (GPG or SSH signing)
- Enforce via branch protection rules: "Require signed commits"
- Verify with `git log --show-signature`

---

## 7. Container Registry Security

### Admission Controllers for Image Verification

```yaml
# Kyverno: Verify Cosign signature before deployment
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signature
spec:
  validationFailureAction: Enforce
  background: false
  rules:
    - name: verify-cosign-signature
      match:
        any:
          - resources:
              kinds:
                - Pod
      verifyImages:
        - imageReferences:
            - "ghcr.io/myorg/*"
          attestors:
            - entries:
                - keys:
                    publicKeys: |-
                      -----BEGIN PUBLIC KEY-----
                      MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
                      -----END PUBLIC KEY-----
```

### OPA Gatekeeper Policy

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8sallowedrepos
spec:
  crd:
    spec:
      names:
        kind: K8sAllowedRepos
      validation:
        openAPIV3Schema:
          type: object
          properties:
            repos:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sallowedrepos
        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          satisfied := [good | repo = input.parameters.repos[_] ; good = startswith(container.image, repo)]
          not any(satisfied)
          msg := sprintf("container <%v> has an invalid image repo <%v>, allowed repos are %v", [container.name, container.image, input.parameters.repos])
        }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sAllowedRepos
metadata:
  name: repos-allowed
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
  parameters:
    repos:
      - "ghcr.io/myorg/"
      - "registry.example.com/"
```

---

## 8. Secret Scanning in Containers

### Detecting Secrets in Images

```bash
# Scan image for hardcoded secrets
trivy image --scanners secret myapp:1.0.0

# Scan with custom rules
trivy image --secret-config trivy-secret.yaml myapp:1.0.0
```

### .dockerignore for Secret Prevention

```text
# Secrets and credentials
.env
.env.*
*.pem
*.key
*.p12
*.jks
*credentials*.json
*secret*.*
id_rsa*

# Version control
.git
.gitignore

# CI/CD
.github/
.gitlab-ci.yml

# IDE
.idea/
.vscode/

# Build artifacts (not needed in image)
node_modules/
build/
dist/
```

### Pre-commit Hook for Secret Detection

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/trufflesecurity/trufflehog
    rev: v3.80.0
    hooks:
      - id: trufflehog
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks
```

### GitOps Secret Management

- Never store plaintext secrets in Git repositories
- Use Sealed Secrets, External Secrets Operator (ESO), or SOPS for GitOps workflows
- Reference the `secrets-management` skill for detailed patterns

---

## 9. Anti-Patterns

- **Running containers as root**: The most common and dangerous anti-pattern — always set `runAsNonRoot: true`
- **Using `latest` tag in production**: Non-reproducible, cannot roll back — pin to specific version or digest
- **Skipping vulnerability scanning**: Unknown vulnerabilities accumulate — scan in CI and block on HIGH/CRITICAL
- **Not signing images**: Cannot verify image authenticity — use Cosign to sign and verify
- **Ignoring SBOMs**: Cannot track what is inside your images — generate and store SBOMs with every build
- **Allowing privileged containers**: Bypasses all container isolation — never use `privileged: true`
- **Not enforcing admission policies**: Any image can run in the cluster — use Kyverno or OPA Gatekeeper
- **Hardcoding secrets in Dockerfiles**: Visible in image layers — use multi-stage builds and `.dockerignore`
- **Skipping dependency pinning**: Supply chain attacks target unpinned actions/packages — pin by SHA
- **Not rotating base images**: Old base images accumulate CVEs — schedule regular rebuilds (weekly)
- **Ignoring SLSA levels**: No guarantee of build integrity — aim for SLSA 3+ for production images
