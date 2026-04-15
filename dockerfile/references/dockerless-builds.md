# Dockerless Build Tools

Build OCI container images without a Docker daemon or Dockerfile. Use when CI/CD environments lack Docker access, when running inside Kubernetes, or when you want automated layer optimization.

---

## §1 Jib (Google)

Build optimized Docker/OCI images for Java applications using Maven or Gradle plugins — no Docker daemon required.

### When to Use

- Java/Kotlin projects with Maven or Gradle
- CI/CD pipelines without Docker daemon access
- Automatic layer optimization (dependencies, resources, classes separated)
- Direct registry push without local image storage

### Layer Split Strategy

Jib automatically splits the application into multiple layers for optimal caching:

1. **Dependencies layer**: Third-party libraries (rebuilt only on dependency change)
2. **Resources layer**: Non-compiled resources (rebuilt on resource change)
3. **Classes layer**: Application classes (rebuilt on code change)

### Gradle Configuration

```kotlin
plugins {
    id("com.google.cloud.tools.jib") version "3.4.5"
}

jib {
    from {
        image = "eclipse-temurin:21-jre-alpine"
    }
    to {
        image = "ghcr.io/myorg/order-service"
        tags = setOf("latest", version.toString())
    }
    container {
        ports = listOf("8080")
        jvmFlags = listOf(
            "-XX:MaxRAMPercentage=75.0",
            "-Djava.security.egd=file:/dev/./urandom"
        )
    }
}
```

```bash
# Build and push to registry
./gradlew jib

# Build to local Docker daemon
./gradlew jibDockerBuild

# Build to local tar file
./gradlew jibBuildTar
```

### Maven Configuration

```xml
<plugin>
    <groupId>com.google.cloud.tools</groupId>
    <artifactId>jib-maven-plugin</artifactId>
    <version>3.4.5</version>
    <configuration>
        <from>
            <image>eclipse-temurin:21-jre-alpine</image>
        </from>
        <to>
            <image>ghcr.io/myorg/order-service</image>
            <tags>
                <tag>latest</tag>
                <tag>${project.version}</tag>
            </tags>
        </to>
        <container>
            <ports>
                <port>8080</port>
            </ports>
            <jvmFlags>
                <jvmFlag>-XX:MaxRAMPercentage=75.0</jvmFlag>
            </jvmFlags>
        </container>
    </configuration>
</plugin>
```

```bash
# Build and push to registry
mvn compile jib:build

# Build to local Docker daemon
mvn compile jib:dockerBuild
```

### Registry Authentication

- Use Docker credential helpers (`.docker/config.json`)
- Pass credentials via environment variables: `JIB_REGISTRY_USERNAME`, `JIB_REGISTRY_PASSWORD`
- Use CI/CD secret injection (GitHub Actions secrets, GitLab CI variables)

### Rules

- Always specify a pinned base image tag — never use `latest`
- Use JRE base images for production, not JDK
- Push directly to registry in CI; use `jibDockerBuild` only for local development
- Configure `.jib` ignore patterns if build artifacts should be excluded

---

## §2 Cloud Native Buildpacks

Transform source code into OCI images automatically using buildpacks — no Dockerfile needed.

### When to Use

- Polyglot projects with auto-detection needs
- Teams that want to avoid maintaining Dockerfiles
- Heroku-style "git push" deployment workflows
- Standardized builds across multiple languages

### How It Works

1. **Detect phase**: Buildpacks inspect source code to identify language, framework, and dependencies
2. **Analysis phase**: Reuse layers from previous builds for caching
3. **Build phase**: Compile source code, install dependencies, create OCI image layers
4. **Export phase**: Produce OCI-compliant image with metadata

### Installation

```bash
# macOS
brew install buildpacks/tap/pack

# Linux
curl -sSL "https://github.com/buildpacks/pack/releases/download/v0.36.2/pack-v0.36.2-linux.tgz" | sudo tar -xzf - -C /usr/local/bin pack
```

### Builder Selection

```bash
# List available builders
pack builder suggest

# Common builders:
# paketobuildpacks/builder-jammy-base    — Ubuntu Jammy, general purpose
# paketobuildpacks/builder-jammy-tiny    — Minimal Ubuntu Jammy
# paketobuildpacks/builder-jammy-full    — Full Ubuntu Jammy with debug tools
# heroku/builder:24                       — Heroku stack
```

### Build Commands

```bash
# Auto-detect and build with default builder
pack build ghcr.io/myorg/order-service \
  --builder paketobuildpacks/builder-jammy-base

# Build with specific buildpack
pack build ghcr.io/myorg/order-service \
  --builder paketobuildpacks/builder-jammy-base \
  --buildpack paketo-buildpacks/java

# Build with environment variables
pack build ghcr.io/myorg/order-service \
  --builder paketobuildpacks/builder-jammy-base \
  --env BP_JVM_VERSION=21 \
  --env BP_SPRING_CLOUD_BINDINGS_ENABLED=true
```

### Buildpack Groups (Java/Spring Boot)

| Buildpack                    | Purpose                         |
| ---------------------------- | ------------------------------- |
| `paketo-buildpacks/ca-certificates` | CA certificates injection    |
| `paketo-buildpacks/bellsoft-liberica` | JDK/JRE installation       |
| `paketo-buildpacks/gradle`   | Gradle build execution          |
| `paketo-buildpacks/maven`    | Maven build execution           |
| `paketo-buildpacks/executable-jar` | Fat JAR packaging            |
| `paketo-buildpacks/spring-boot` | Spring Boot layer extraction |
| `paketo-buildpacks/syft`     | SBOM generation                 |

### Rules

- Pin builder versions for reproducible builds
- Use `--env` to override auto-detected settings (JVM version, build profiles)
- Prefer `tiny` or `base` builders for production; use `full` only for debugging
- Verify SBOM output with `pack inspect <image>` for compliance requirements
- When auto-detection fails, specify buildpacks explicitly with `--buildpack`

---

## §3 Kaniko

Build container images from Dockerfile inside Kubernetes or any container runtime — without Docker daemon or root privileges.

### When to Use

- CI/CD running inside Kubernetes (Tekton, Argo Workflows, GitLab Runner)
- Environments where Docker daemon is unavailable or prohibited
- Dockerfile-based builds that need non-root execution
- Multi-stage Dockerfile support in restricted environments

### Key Characteristics

- Executes Dockerfile instructions in userspace
- Extracts filesystem layers sequentially
- No Docker daemon dependency
- No root privileges required (when using `--snapshot-mode=redo`)
- Full multi-stage build support

### Tekton Task Integration

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: kaniko-build
spec:
  params:
    - name: IMAGE
      type: string
    - name: DOCKERFILE
      type: string
      default: Dockerfile
    - name: CONTEXT
      type: string
      default: .
  workspaces:
    - name: source
  steps:
    - name: build-and-push
      image: gcr.io/kaniko-project/executor:v1.24.0
      args:
        - --dockerfile=$(params.DOCKERFILE)
        - --context=$(workspaces.source.path)/$(params.CONTEXT)
        - --destination=$(params.IMAGE)
        - --cache=true
        - --cache-dir=/workspace/cache
      volumeMounts:
        - name: kaniko-secret
          mountPath: /kaniko/.docker
          readOnly: true
  volumes:
    - name: kaniko-secret
      secret:
        secretName: registry-credentials
        items:
          - key: .dockerconfigjson
            path: config.json
```

### CLI Usage

```bash
# Build and push to registry
/kaniko/executor \
  --context /workspace/source \
  --dockerfile /workspace/source/Dockerfile \
  --destination ghcr.io/myorg/order-service:latest

# Build with build context from tarball
/kaniko/executor \
  --context tar:///path/to/context.tar.gz \
  --destination ghcr.io/myorg/order-service:latest

# Build without pushing (validate only)
/kaniko/executor \
  --context /workspace/source \
  --dockerfile /workspace/source/Dockerfile \
  --no-push
```

### Caching Strategy

- `--cache=true`: Enable layer caching
- `--cache-dir`: Specify cache directory (persistent volume recommended)
- `--cache-repo`: Use a separate repository for cached layers
- Reuse cached layers across pipeline runs by mounting persistent volumes

### Security Rules

- Run Kaniko executor as non-root user when possible
- Use `--snapshot-mode=redo` for reduced privilege requirements
- Mount registry credentials via Kubernetes Secret, never bake into image
- Scan output images with Trivy or equivalent before deployment
- Set resource limits to prevent unbounded memory usage during build

---

## §4 Shipwright

Kubernetes-native build abstraction that defines Build strategies and executes them as BuildRun custom resources.

### When to Use

- Platform teams providing self-service build capabilities
- Multi-strategy builds (Kaniko, Buildah, Buildpacks) through unified API
- GitOps-driven image build pipelines
- Teams already using Tekton for CI/CD orchestration

### Architecture

Shipwright operates on top of Tekton Pipelines and provides three core CRDs:

1. **ClusterBuildStrategy**: Defines how to build (Kaniko, Buildah, Buildpacks, etc.)
2. **Build**: Declarative build definition (source, strategy, output image)
3. **BuildRun**: Execution instance of a Build

### Installation

```bash
kubectl apply --filename https://github.com/shipwright-io/build/releases/latest/download/release.yaml
```

### ClusterBuildStrategy (Pre-installed)

| Strategy       | Description                         |
| -------------- | ----------------------------------- |
| `kaniko`       | Dockerfile-based build with Kaniko  |
| `buildah`      | Dockerfile-based build with Buildah |
| `buildpacks-v3`| Cloud Native Buildpacks integration |
| `ko`           | Go application build                |

### Build Definition Example

```yaml
apiVersion: shipwright.io/v1beta1
kind: Build
metadata:
  name: order-service-build
spec:
  source:
    url: https://github.com/myorg/order-service
    contextDir: /
    revision: main
  strategy:
    name: kaniko
    kind: ClusterBuildStrategy
  output:
    image: ghcr.io/myorg/order-service:latest
    credentials:
      name: registry-secret
  paramValues:
    - name: build-args
      value:
        - "SPRING_PROFILES_ACTIVE=production"
```

### BuildRun Execution

```yaml
apiVersion: shipwright.io/v1beta1
kind: BuildRun
metadata:
  generateName: order-service-build-run-
spec:
  build:
    name: order-service-build
```

```bash
# Trigger a new build run
kubectl create -f buildrun.yaml

# Check build status
kubectl get buildrun --sort-by=.metadata.creationTimestamp

# View build logs
kubectl logs -f buildrun/order-service-build-run-xxxxx
```

### Integration with CI/CD

- Trigger BuildRun via Kubernetes client from CI pipeline
- Use GitOps controllers (Argo CD, Flux) to manage Build definitions declaratively
- Combine with image update automation for GitOps image promotion workflows

### Rules

- Ensure Tekton Pipelines is installed before Shipwright
- Use ClusterBuildStrategy for cluster-wide build configurations
- Define Build resources declaratively and manage via GitOps
- Monitor BuildRun status for build success/failure
- Clean up completed BuildRuns to prevent resource accumulation

---

## §5 Tool Selection Guide

### Comparison Matrix

| Criterion              | Jib                          | Cloud Native Buildpacks      | Kaniko                       | Shipwright                   |
| ---------------------- | ---------------------------- | ---------------------------- | ---------------------------- | ---------------------------- |
| Dockerfile required    | No                           | No                           | Yes                          | Yes (Kaniko/Buildah), No (Buildpacks) |
| Docker daemon required | No                           | No                           | No                           | No                           |
| Supported languages    | Java/Kotlin only             | Polyglot (Java, Node, Go, Python, etc.) | Any (Dockerfile-based) | Any (strategy-dependent)     |
| CI/CD integration      | Maven/Gradle plugin          | `pack` CLI                   | Container in pipeline        | Kubernetes CRD + Tekton      |
| Layer optimization     | Automatic (deps/resources/classes) | Automatic (buildpack layers) | Dockerfile layer caching     | Strategy-dependent           |
| Kubernetes native      | No                           | No                           | Partial (runs in cluster)    | Yes (full CRD API)           |
| Learning curve         | Low (familiar build tools)   | Medium (builder concepts)    | Low (standard Dockerfile)    | High (Kubernetes + Tekton)   |
| Best for               | Java teams in CI without Docker | Polyglot teams wanting zero-config builds | Dockerfile builds in restricted environments | Platform teams building self-service PaaS |

### CI/CD Pipeline Integration Examples

#### GitHub Actions — Jib

```yaml
jobs:
  build-image:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "21"
      - name: Build and push with Jib
        run: ./gradlew jib
        env:
          JIB_TO_AUTH_USERNAME: ${{ secrets.REGISTRY_USERNAME }}
          JIB_TO_AUTH_PASSWORD: ${{ secrets.REGISTRY_PASSWORD }}
```

#### GitHub Actions — Buildpacks

```yaml
jobs:
  build-image:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install pack
        run: |
          curl -sSL "https://github.com/buildpacks/pack/releases/download/v0.36.2/pack-v0.36.2-linux.tgz" | sudo tar -xzf - -C /usr/local/bin pack
      - name: Build with Buildpacks
        run: |
          pack build ghcr.io/myorg/order-service:${{ github.sha }} \
            --builder paketobuildpacks/builder-jammy-base \
            --publish
        env:
          DOCKER_CONFIG: ${{ secrets.REGISTRY_AUTH }}
```

#### Tekton — Kaniko

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: build-pipeline-run-
spec:
  pipelineRef:
    name: kaniko-build-pipeline
  params:
    - name: IMAGE
      value: ghcr.io/myorg/order-service:$(tasks.git-clone.results.commit)
  workspaces:
    - name: source
      volumeClaimTemplate:
        spec:
          accessModes: [ReadWriteOnce]
          resources:
            requests:
              storage: 1Gi
```

### Comparison with Traditional Dockerfile Build

| Aspect                 | Traditional Docker Build       | Dockerless Alternatives         |
| ---------------------- | ------------------------------ | ------------------------------- |
| Build environment      | Requires Docker daemon         | No daemon needed                |
| Root privileges        | Often required                 | Optional or unnecessary         |
| Layer caching          | Manual (Dockerfile order)      | Automatic (Jib, Buildpacks)     |
| CI/CI portability      | Docker-dependent               | Runs anywhere                   |
| Dockerfile maintenance | Required                       | Optional or unnecessary         |
| Build reproducibility  | Depends on host state          | More deterministic              |
| Image size optimization| Manual multi-stage             | Automatic layer splitting       |

### Decision Flow

1. **Java/Kotlin project without Dockerfile?** → Jib
2. **Polyglot project, want zero-config builds?** → Cloud Native Buildpacks
3. **Existing Dockerfile, no Docker daemon in CI?** → Kaniko
4. **Platform team, multi-strategy, Kubernetes-native?** → Shipwright
5. **Need Docker daemon features (buildx, custom networks)?** → Stick with traditional Docker build
