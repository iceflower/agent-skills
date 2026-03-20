# Advanced Dockerfile Patterns

## 1. BuildKit Features

### Enable BuildKit

```bash
# Set environment variable
export DOCKER_BUILDKIT=1

# Or use buildx (BuildKit always enabled)
docker buildx build -t myapp .
```

### Syntax Directive

```dockerfile
# syntax=docker/dockerfile:1
FROM eclipse-temurin:21-jre-alpine
```

### Cache Mounts

```dockerfile
# Cache Gradle dependencies across builds
FROM gradle:8-jdk21 AS build
WORKDIR /app
COPY build.gradle.kts settings.gradle.kts ./
COPY gradle ./gradle
RUN --mount=type=cache,target=/home/gradle/.gradle/caches \
    gradle dependencies --no-daemon
COPY src ./src
RUN --mount=type=cache,target=/home/gradle/.gradle/caches \
    gradle bootJar --no-daemon -x test
```

### Secret Mounts

```dockerfile
# Mount secret at build time without embedding in image
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm install --production

# Usage: docker build --secret id=npmrc,src=$HOME/.npmrc .
```

### SSH Mounts

```dockerfile
# Use SSH key for private Git dependencies
RUN --mount=type=ssh \
    git clone git@github.com:org/private-lib.git

# Usage: docker build --ssh default=$SSH_AUTH_SOCK .
```

### Inline Cache Export/Import

```dockerfile
# Build with cache export
docker buildx build \
  --cache-to type=registry,ref=ghcr.io/org/myapp:cache \
  --cache-from type=registry,ref=ghcr.io/org/myapp:cache \
  -t myapp .
```

---

## 2. Multi-Architecture Builds

### Using docker buildx

```bash
# Create multi-arch builder
docker buildx create --name multiarch --use

# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --push \
  -t ghcr.io/org/myapp:1.0.0 .
```

### Platform-Specific Instructions

```dockerfile
FROM --platform=$BUILDPLATFORM gradle:8-jdk21 AS build
ARG TARGETPLATFORM
ARG BUILDPLATFORM
WORKDIR /app
COPY . .
RUN gradle bootJar --no-daemon -x test

FROM --platform=$TARGETPLATFORM eclipse-temurin:21-jre-alpine
COPY --from=build /app/build/libs/*.jar app.jar
ENTRYPOINT ["java", "-jar", "app.jar"]
```

### CI/CD Multi-Arch Pipeline

```yaml
# GitHub Actions
- name: Set up QEMU
  uses: docker/setup-qemu-action@v3

- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

- name: Build and push
  uses: docker/build-push-action@v6
  with:
    platforms: linux/amd64,linux/arm64
    push: true
    tags: ghcr.io/org/myapp:${{ github.sha }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

---

## 3. Signal Handling

### ENTRYPOINT Exec Form vs Shell Form

```dockerfile
# CORRECT — exec form: process receives signals directly
ENTRYPOINT ["java", "-jar", "app.jar"]

# WRONG — shell form: sh -c wraps process, signals go to shell
ENTRYPOINT java -jar app.jar
```

### SIGTERM Propagation

```text
Docker stop → sends SIGTERM → waits grace period (default 10s) → sends SIGKILL

exec form:  SIGTERM → java process → graceful shutdown
shell form: SIGTERM → /bin/sh → sh may not forward to java → SIGKILL after timeout
```

### Using tini as Init Process

```dockerfile
# Install tini for proper signal handling and zombie process reaping
RUN apk add --no-cache tini
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["java", "-jar", "app.jar"]
```

### Graceful Shutdown Configuration

```dockerfile
# Set stop signal (default is SIGTERM)
STOPSIGNAL SIGTERM

# Set stop grace period in docker-compose or K8s
# docker-compose: stop_grace_period: 30s
# K8s: terminationGracePeriodSeconds: 30
```

### Spring Boot Graceful Shutdown

```yaml
# application.yml
server:
  shutdown: graceful
spring:
  lifecycle:
    timeout-per-shutdown-phase: 20s
```

---

## 4. Health Check Patterns

### Dockerfile HEALTHCHECK

```dockerfile
# HTTP health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
  CMD wget -qO- http://localhost:8080/actuator/health || exit 1

# TCP health check (for non-HTTP services)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD nc -z localhost 5432 || exit 1
```

### Health Check Parameters

| Parameter | Default | Recommendation |
| --- | --- | --- |
| `--interval` | 30s | 10-30s depending on app |
| `--timeout` | 30s | 3-5s |
| `--start-period` | 0s | Match app startup time |
| `--retries` | 3 | 2-5 |

### Dependency Health Check Script

```bash
#!/bin/sh
# healthcheck.sh — check app and critical dependencies
set -e

# Check app is responding
wget -qO- http://localhost:8080/actuator/health || exit 1

# Optional: check critical dependency
# wget -qO- http://localhost:8080/actuator/health/db || exit 1
```

---

## 5. Build Optimization

### .dockerignore Best Practices

```text
# VCS
.git
.gitignore

# Build outputs
build/
out/
target/
dist/
node_modules/

# IDE
.idea/
.vscode/
*.iml

# Docker
Dockerfile*
docker-compose*.yml
.dockerignore

# Secrets and environment
.env*
*.pem
*.key

# Documentation and tests
*.md
docs/
tests/
__tests__/

# Logs
*.log
```

### Layer Analysis

```bash
# Analyze image layers
docker history myapp:latest --no-trunc

# Use dive for interactive analysis
dive myapp:latest
```

### Reducing Image Size

| Technique | Impact |
| --- | --- |
| Multi-stage build | Removes build tools and source |
| Alpine/distroless base | Smaller OS footprint |
| `.dockerignore` | Excludes unnecessary build context |
| Combine RUN commands | Reduces layer count |
| Remove package caches | `apk add --no-cache` or `rm -rf /var/cache/apt/*` |
| Use JRE instead of JDK | ~300MB reduction for Java apps |

---

## 6. Development vs Production

### Dev Image with Hot Reload

```dockerfile
# Development Dockerfile
FROM eclipse-temurin:21-jdk AS dev
WORKDIR /app
COPY build.gradle.kts settings.gradle.kts ./
COPY gradle ./gradle
RUN gradle dependencies --no-daemon
# Source code mounted as volume for hot reload
EXPOSE 8080
EXPOSE 5005
ENTRYPOINT ["gradle", "bootRun", "--no-daemon", \
  "-Dspring-boot.run.jvmArguments=-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005"]
```

### docker-compose Override Pattern

```yaml
# docker-compose.yml (production defaults)
services:
  app:
    build:
      context: .
      target: runtime
    ports:
      - "8080:8080"

# docker-compose.override.yml (dev overrides, auto-loaded)
services:
  app:
    build:
      target: dev
    volumes:
      - ./src:/app/src
    ports:
      - "8080:8080"
      - "5005:5005"  # Debug port
    environment:
      - SPRING_PROFILES_ACTIVE=dev
```

---

## 7. Image Provenance

### Signing with cosign

```bash
# Generate key pair
cosign generate-key-pair

# Sign image
cosign sign --key cosign.key ghcr.io/org/myapp:1.0.0

# Verify signature
cosign verify --key cosign.pub ghcr.io/org/myapp:1.0.0
```

### Keyless Signing (OIDC)

```bash
# Sign using OIDC identity (GitHub Actions, Google, etc.)
cosign sign ghcr.io/org/myapp:1.0.0

# Verify with identity
cosign verify \
  --certificate-identity=https://github.com/org/myapp/.github/workflows/build.yml@refs/heads/main \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  ghcr.io/org/myapp:1.0.0
```

### SBOM Generation

```bash
# Generate SBOM with syft
syft ghcr.io/org/myapp:1.0.0 -o spdx-json > sbom.json

# Attach SBOM to image
cosign attach sbom --sbom sbom.json ghcr.io/org/myapp:1.0.0
```

### Vulnerability Scanning Pipeline

```yaml
# GitHub Actions
- name: Scan image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ghcr.io/org/myapp:${{ github.sha }}
    format: sarif
    output: trivy-results.sarif
    severity: CRITICAL,HIGH
    exit-code: 1  # Fail pipeline on critical/high vulnerabilities

- name: Upload scan results
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: trivy-results.sarif
```

### Image Policy

| Rule | Implementation |
| --- | --- |
| Only signed images in production | Admission controller (Kyverno, OPA Gatekeeper) |
| No critical CVEs | Scanning gate in CI/CD pipeline |
| Known base images only | Allowlist of approved base images |
| SBOM attached | Required for compliance and audit |
| Provenance attestation | SLSA framework compliance |
