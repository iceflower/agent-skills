# Twelve-Factor App: Detailed Reference

This document provides in-depth explanations, modern interpretations, and implementation guidance for each of the twelve factors.

---

## Factor 1: Codebase — One Codebase, Many Deploys

### Codebase Principle

A twelve-factor app is always tracked in a version control system (Git, Mercurial). There is a one-to-one correlation between the codebase and the app. If there are multiple codebases, it is a distributed system, not a single app.

### Codebase Rules

- One repository per application (or one directory in a monorepo with clear boundaries)
- Multiple deploys are produced from the same codebase with different configuration
- Code shared between applications must be extracted into versioned libraries

### Codebase Modern Interpretation

- Monorepos are acceptable when each application has a clear boundary and independent build pipeline
- Feature flags enable different behavior per deploy without separate codebases
- Git branching strategies (trunk-based, GitFlow) determine how the single codebase supports parallel development

### Codebase Implementation Examples

```text
# Correct: Single codebase, multiple deploys via config
my-app/
  src/
  Dockerfile
  deploy/
    staging.env      # Not committed -- loaded at deploy time
    production.env   # Not committed -- loaded at deploy time

# Incorrect: Separate codebases per environment
my-app-staging/
my-app-production/
```

### Codebase Common Violations

| Violation              | Impact                         | Fix                                   |
| ---------------------- | ------------------------------ | ------------------------------------- |
| Fork per customer      | Diverging features, merge hell | Use feature flags and config          |
| Copy-paste shared code | Inconsistency, duplicated bugs | Extract into a versioned library      |
| Branch-per-environment | Config drift, merge conflicts  | Single branch, config via environment |

---

## Factor 2: Dependencies — Explicitly Declare and Isolate

### Dependencies Principle

A twelve-factor app never relies on implicit existence of system-wide packages. It declares all dependencies completely and exactly via a dependency declaration manifest.

### Dependencies Rules

- Use a language-appropriate dependency manifest:

| Language    | Manifest           | Lockfile            |
| ----------- | ------------------ | ------------------- |
| Node.js     | `package.json`     | `package-lock.json` |
| Python      | `pyproject.toml`   | `poetry.lock`       |
| Java/Kotlin | `build.gradle.kts` | `gradle.lockfile`   |
| Go          | `go.mod`           | `go.sum`            |
| Rust        | `Cargo.toml`       | `Cargo.lock`        |

- Always commit lockfiles for applications (not for libraries)
- Use isolation tools to sandbox runtime dependencies:
  - Containers (Docker)
  - Virtual environments (Python venv)
  - Sandboxed runtimes (Deno)

### Dependencies Modern Interpretation

- Container images serve as the ultimate dependency isolation boundary
- Multi-stage builds separate build-time and runtime dependencies
- Software Bill of Materials (SBOM) generation is increasingly expected for supply chain security
- Dependency scanning (Dependabot, Snyk, Trivy) must be part of the CI pipeline

### Dependencies Common Violations

| Violation                         | Impact                         | Fix                                 |
| --------------------------------- | ------------------------------ | ----------------------------------- |
| `apt-get install` in entrypoint   | Runtime dependency on registry | Install in Dockerfile build stage   |
| No lockfile committed             | Non-reproducible builds        | Commit lockfile, use `--frozen`     |
| Using `latest` tag for base image | Unpredictable base changes     | Pin to specific digest or version   |

---

## Factor 3: Config — Store Config in the Environment

### Config Principle

Configuration that varies between deploys (staging, production, developer environments) should be stored in environment variables. This includes resource handles to databases, credentials for backing services, and per-deploy values such as the canonical hostname.

### Config Rules

- Environment variables are the canonical mechanism for runtime configuration
- Config must be strictly separated from code
- Group related config values with a common prefix (e.g., `DB_HOST`, `DB_PORT`, `DB_NAME`)
- Provide sensible defaults for development to reduce onboarding friction

### Config Modern Interpretation

- Environment variables remain the standard, but structured config stores are preferred at scale:
  - AWS Systems Manager Parameter Store / Secrets Manager
  - HashiCorp Vault
  - Kubernetes ConfigMaps and Secrets
  - GCP Secret Manager / Azure Key Vault
- Config validation at startup: fail fast if required config is missing or malformed
- Typed configuration classes that parse and validate env vars at application boot

### What Is and Is Not Config

| Config (externalize)        | Not Config (keep in code)             |
| --------------------------- | ------------------------------------- |
| Database connection URL     | Internal routing rules                |
| API keys and secrets        | Dependency injection wiring           |
| Feature flag values         | Default HTTP timeout (code constant)  |
| Log level per environment   | Application thread pool size defaults |
| Service discovery endpoints | Retry policy constants                |

### Config Implementation Example

```text
# Application startup pseudocode
class AppConfig {
    dbUrl:    String = requireEnv("DATABASE_URL")
    apiKey:   String = requireEnv("API_KEY")
    logLevel: String = env("LOG_LEVEL", default = "INFO")
    port:     Int    = env("PORT", default = "8080").toInt()

    fun validate() {
        if (dbUrl.isBlank()) throw ConfigError("DATABASE_URL is required")
        if (port !in 1..65535) throw ConfigError("PORT must be 1-65535")
    }
}
```

---

## Factor 4: Backing Services — Treat as Attached Resources

### Backing Services Principle

A backing service is any service the app consumes over the network as part of its normal operation: databases, message queues, SMTP services, caching systems.

### Backing Services Rules

- Access all backing services via URLs or connection strings stored in config
- The application code makes no distinction between local and third-party services
- Swapping a backing service (e.g., self-hosted PostgreSQL to AWS RDS) requires only a config change

### Backing Services Modern Interpretation

- Cloud managed services (RDS, Cloud SQL, ElastiCache, SQS) are the primary backing services
- Service mesh and service discovery replace static connection strings in dynamic environments
- Connection pooling and health-checking are essential for reliable backing service access

### Backing Service Categories

| Category       | Examples                        | Access Mechanism             |
| -------------- | ------------------------------- | ---------------------------- |
| Data Store     | PostgreSQL, MongoDB, DynamoDB   | Connection string via config |
| Message Broker | Kafka, RabbitMQ, SQS, Pub/Sub   | Broker URL via config        |
| Cache          | Redis, Memcached                | Connection string via config |
| Object Storage | S3, GCS, Azure Blob             | SDK with config credentials  |
| Email/SMS      | SendGrid, Twilio, SES           | API key via config           |
| Search         | Elasticsearch, OpenSearch       | URL via config               |
| Monitoring     | Datadog, CloudWatch, Prometheus | Agent config or endpoint URL |

---

## Factor 5: Build, Release, Run — Strict Separation

### Build/Release/Run Principle

The twelve-factor app uses strict separation between the build, release, and run stages.

### Build/Release/Run Rules

- **Build stage**: Compile code, resolve dependencies, produce an artifact (binary, container image)
- **Release stage**: Combine the build artifact with deploy-specific config
- **Run stage**: Execute the release in the target environment
- Releases are immutable -- once created, a release cannot be mutated
- Every release has a unique, sortable ID (semantic version, commit hash, timestamp)

### Build/Release/Run Modern Interpretation

- Container images are the standard build artifact
- Container registries (ECR, GCR, Docker Hub) store versioned build artifacts
- GitOps treats a Git commit as the release identifier
- Helm charts, Kustomize overlays, or Terraform variables combine artifact + config at release time

### Build/Release/Run Pipeline Mapping

```text
┌─────────┐     ┌──────────┐     ┌─────────┐
│  Build   │ ──► │ Release  │ ──► │   Run   │
│          │     │          │     │         │
│ Compile  │     │ Image +  │     │ Deploy  │
│ Test     │     │ Config   │     │ Execute │
│ Package  │     │ Tag      │     │ Monitor │
└─────────┘     └──────────┘     └─────────┘
   CI               CD              Runtime
```

---

## Factor 6: Processes — Stateless and Share-Nothing

### Processes Principle

Twelve-factor processes are stateless and share-nothing. Any data that needs to persist must be stored in a stateful backing service.

### Processes Rules

- Processes do not store persistent state in memory or on the local filesystem
- In-memory caches are acceptable for short-lived, per-request data only
- File uploads go directly to object storage, not to local disk
- Session data goes to a distributed store (Redis, database), not in-process memory

### Processes Modern Interpretation

- Kubernetes pods are ephemeral -- local storage is destroyed on restart
- Serverless functions enforce statelessness by design
- Distributed caches (Redis, Memcached) replace in-process caching for shared state
- Content Delivery Networks (CDNs) handle static asset serving

### State Management Strategies

| State Type     | Wrong Approach         | Correct Approach                      |
| -------------- | ---------------------- | ------------------------------------- |
| User sessions  | In-memory HashMap      | Redis, database-backed sessions       |
| File uploads   | Local `/tmp` directory | S3, GCS, Azure Blob                   |
| Computed cache | In-process cache       | Redis, Memcached (shared)             |
| Job progress   | In-memory variable     | Database record, message queue status |
| Temporary data | Local file             | Object storage with TTL               |

---

## Factor 7: Port Binding — Self-Contained Services

### Port Binding Principle

The twelve-factor app is completely self-contained and exports HTTP (or other protocols) as a service by binding to a port.

### Port Binding Rules

- The application includes its own web server (embedded Tomcat, Netty, Express, Uvicorn)
- The app does not depend on a separate web server container (no WAR deployment into an external Tomcat)
- The port is configurable via environment variable (typically `PORT`)
- One service per port binding

### Port Binding Modern Interpretation

- Container port mapping (`EXPOSE` in Dockerfile, `-p` in Docker, `containerPort` in Kubernetes) makes this natural
- Service meshes (Istio, Linkerd) add protocol-level features (mTLS, load balancing) transparently
- gRPC and WebSocket services also follow port binding

---

## Factor 8: Concurrency — Scale via Process Model

### Concurrency Principle

In the twelve-factor app, processes are a first-class citizen. The developer can architect the app to handle diverse workloads by assigning each type of work to a process type.

### Concurrency Rules

- Scale horizontally by adding process instances (replicas), not by increasing process size
- Different workload types run as different process types:

| Process Type | Responsibility          | Scaling Strategy                   |
| ------------ | ----------------------- | ---------------------------------- |
| web          | Handle HTTP requests    | Scale by request volume            |
| worker       | Process background jobs | Scale by queue depth               |
| scheduler    | Run periodic tasks      | Single instance or leader election |
| consumer     | Process event streams   | Scale by partition count           |

- The process manager (Kubernetes, systemd, Procfile) handles process lifecycle

### Concurrency Modern Interpretation

- Kubernetes Deployments, HPA (Horizontal Pod Autoscaler), and KEDA enable automatic process scaling
- Serverless platforms (Lambda, Cloud Functions) scale individual function invocations
- Event-driven autoscaling (KEDA) bridges queue depth to process count

---

## Factor 9: Disposability — Fast Startup, Graceful Shutdown

### Disposability Principle

Twelve-factor app processes are disposable, meaning they can be started or stopped at a moment's notice. This facilitates fast elastic scaling, rapid deployment of code or config changes, and robustness of production deploys.

### Disposability Rules

- Startup time should be measured in seconds
- On receiving SIGTERM, the process:
  1. Stops accepting new requests
  2. Completes in-flight requests (within a deadline)
  3. Releases resources (database connections, file handles)
  4. Exits cleanly
- Workers return incomplete jobs to the queue on shutdown
- All operations should be idempotent to handle crash recovery safely

### Disposability Modern Interpretation

- Kubernetes `terminationGracePeriodSeconds` defines the shutdown deadline
- Pre-stop hooks perform final cleanup before SIGTERM
- Readiness probes prevent traffic from reaching pods that are still starting
- Init containers handle pre-startup initialization

### Graceful Shutdown Sequence

```text
1. SIGTERM received
2. Stop accepting new connections
3. Return 503 for new health check requests
4. Wait for in-flight requests (up to grace period)
5. Close database connection pools
6. Flush log buffers
7. Exit with code 0
```

---

## Factor 10: Dev/Prod Parity — Minimize Divergence

### Dev/Prod Parity Principle

The twelve-factor app is designed for continuous deployment by keeping the gap between development and production small.

### Dev/Prod Parity Rules

- Use the same backing service type and version across all environments
- Deploy frequently (hours or days, not weeks or months)
- The developer who wrote the code should be closely involved in deploying it

### Dev/Prod Parity Modern Interpretation

- Docker Compose replicates production backing services locally
- Testcontainers spin up real dependencies in CI
- Infrastructure as Code (Terraform, Pulumi) ensures consistent environments
- Feature flags replace long-lived environment branches

### Parity Matrix

| Aspect         | Anti-Pattern                        | Correct Approach                    |
| -------------- | ----------------------------------- | ----------------------------------- |
| Database       | SQLite in dev, PostgreSQL in prod   | PostgreSQL everywhere (containers)  |
| Cache          | In-memory in dev, Redis in prod     | Redis everywhere (containers)       |
| Queue          | Synchronous in dev, Kafka in prod   | Kafka everywhere (containers)       |
| Object Storage | Local filesystem in dev, S3 in prod | MinIO in dev, S3 in prod            |
| Auth           | Disabled in dev, OAuth in prod      | Same OAuth provider (test tenant)   |

---

## Factor 11: Logs — Event Streams

### Logs Principle

A twelve-factor app never concerns itself with routing or storage of its output stream. It writes its event stream, unbuffered, to stdout.

### Logs Rules

- Write all log output to stdout (and stderr for errors)
- Never write to log files within the application
- Never manage log rotation from application code
- Use structured logging (JSON format preferred)
- Include correlation IDs for request tracing

### Logs Modern Interpretation

- Container runtimes capture stdout/stderr automatically
- Log aggregation platforms (ELK, Loki, CloudWatch Logs, Datadog) consume log streams
- Structured logging enables filtering, alerting, and dashboards
- OpenTelemetry provides a unified approach to logs, metrics, and traces

### Structured Log Example

```json
{
  "timestamp": "2025-01-15T10:30:00.123Z",
  "level": "INFO",
  "service": "order-service",
  "trace_id": "abc123def456",
  "span_id": "789ghi",
  "message": "Order created",
  "order_id": "ORD-001",
  "customer_id": "CUST-042",
  "total_amount": 99.99
}
```

---

## Factor 12: Admin Processes — One-Off Tasks

### Admin Processes Principle

One-off admin processes should be run in an identical environment as the regular long-running processes of the app. They run against a release, using the same codebase and config as any process run against that release.

### Admin Processes Rules

- Admin tasks (migrations, data fixes, REPL sessions) run as one-off processes, not baked into startup
- Admin code is shipped with the application to prevent drift
- Admin processes use the same dependency and config isolation as the app
- Prefer idempotent migrations that can be safely re-run

### Admin Processes Modern Interpretation

- Kubernetes Jobs and CronJobs for admin tasks
- Database migration tools (Flyway, Liquibase, Alembic, Prisma) run as init containers or separate Jobs
- CLI commands packaged in the same container image
- Never run admin tasks directly on production databases -- use the application's admin interface

### Admin Task Patterns

| Task               | Mechanism                        | Scheduling       |
| ------------------ | -------------------------------- | ---------------- |
| Database migration | Init container or Kubernetes Job | Once per release |
| Data backfill      | Kubernetes Job                   | On-demand        |
| Cache warm-up      | Init container                   | On startup       |
| Report generation  | CronJob                          | Periodic         |
| REPL / debug       | `kubectl exec` into running pod  | Ad-hoc           |
