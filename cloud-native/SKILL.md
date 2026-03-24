---
name: cloud-native
description: >-
  Cloud native application design principles based on the Twelve-Factor App
  methodology and CNCF patterns including codebase management, dependency
  isolation, config externalization, backing services, build-release-run
  separation, stateless processes, port binding, concurrency via process model,
  disposability, dev/prod parity, log streaming, and admin processes.
  Extends to 15-Factor with API-first design, telemetry, and security.
  Covers AWS/GCP/Azure Well-Architected frameworks.
  Use when designing cloud native applications, reviewing application
  architecture for cloud readiness, or applying twelve-factor principles
  to existing applications.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# Cloud Native / Twelve-Factor App Rules

## 1. Twelve-Factor App Principles

The Twelve-Factor App methodology defines a set of principles for building modern, portable, and scalable applications. Each factor addresses a specific aspect of application design and deployment.

### Factor Overview

| #  | Factor            | Core Rule                                          |
| -- | ----------------- | -------------------------------------------------- |
| 1  | Codebase          | One codebase tracked in VCS, many deploys          |
| 2  | Dependencies      | Explicitly declare and isolate dependencies        |
| 3  | Config            | Store config in the environment                    |
| 4  | Backing Services  | Treat backing services as attached resources       |
| 5  | Build/Release/Run | Strictly separate build and run stages             |
| 6  | Processes         | Execute the app as one or more stateless processes |
| 7  | Port Binding      | Export services via port binding                   |
| 8  | Concurrency       | Scale out via the process model                    |
| 9  | Disposability     | Maximize robustness with fast startup and shutdown |
| 10 | Dev/Prod Parity   | Keep development, staging, and production similar  |
| 11 | Logs              | Treat logs as event streams                        |
| 12 | Admin Processes   | Run admin/management tasks as one-off processes    |

> For detailed explanations, modern interpretations, and implementation examples of each factor, see `references/twelve-factor-details.md`.

---

### Factor 1: Codebase

- One application = one codebase in version control
- Multiple deploys (staging, production, developer environments) come from the same codebase
- Shared code must be extracted into libraries included via dependency management
- Never maintain separate codebases for the same application across environments

### Factor 2: Dependencies

- Explicitly declare all dependencies using a manifest (e.g., `package.json`, `build.gradle`, `requirements.txt`, `go.mod`)
- Use dependency isolation tools (e.g., virtual environments, containers) to prevent implicit system-wide dependencies
- Never rely on system-level packages being pre-installed
- Pin dependency versions for reproducible builds

### Factor 3: Config

- Store all environment-specific configuration in environment variables
- Configuration includes: database URLs, credentials, per-deploy values, feature flags
- Configuration does NOT include: internal application wiring, routing, or compile-time constants
- Never commit credentials or environment-specific config to the codebase
- The codebase should be open-sourceable at any time without exposing secrets

### Factor 4: Backing Services

- Treat all backing services (databases, message queues, caches, SMTP, object storage) as attached resources
- Access via URL or locator stored in config -- no code change needed to swap a service
- A deploy should be able to switch from a local database to a managed cloud database by changing config alone
- No distinction between local and third-party services in the application code

### Factor 5: Build, Release, Run

- **Build**: Convert code into an executable artifact (compile, bundle assets, resolve dependencies)
- **Release**: Combine the build artifact with environment config
- **Run**: Launch the release in the execution environment
- Every release must have a unique identifier (timestamp, version number, commit hash)
- Builds must not depend on runtime config; runtime must not depend on build tools
- Never modify code at runtime -- changes go through the build pipeline

### Factor 6: Processes

- Application processes are stateless and share-nothing
- Any data that must persist is stored in a backing service (database, object storage)
- Never assume in-memory state (sessions, caches) survives across requests or process restarts
- Sticky sessions are a violation -- use a distributed session store if session state is needed

### Factor 7: Port Binding

- The application is self-contained and exports services by binding to a port
- The application does not rely on runtime injection of a web server (e.g., deploying a WAR into Tomcat)
- One application can become a backing service for another via its URL

### Factor 8: Concurrency

- Scale by running multiple processes, not by growing a single process (scale out, not up)
- Assign different process types for different workloads (web, worker, scheduler)
- Processes should never daemonize or manage their own PID files -- delegate to the platform

### Factor 9: Disposability

- Processes start quickly (seconds, not minutes)
- Processes shut down gracefully on SIGTERM
- Workers use reentrant, idempotent job designs so interrupted work can be safely retried
- Handle crash recovery without data corruption

### Factor 10: Dev/Prod Parity

- Minimize gaps between development and production:

| Gap       | Traditional App          | Twelve-Factor App                 |
| --------- | ------------------------ | --------------------------------- |
| Time      | Weeks between deploys    | Hours between deploys             |
| Personnel | Devs write, ops deploy   | Same team writes and deploys      |
| Tools     | Different stacks per env | Same backing services in all envs |

- Use the same type and version of backing services in all environments
- Avoid "lightweight" substitutes in development (e.g., SQLite in dev, PostgreSQL in prod)

### Factor 11: Logs

- Treat logs as unbuffered event streams written to stdout
- Never manage log files, rotation, or routing within the application
- The execution environment captures, aggregates, routes, and archives log streams
- Use structured logging (JSON) for machine-parseable output

### Factor 12: Admin Processes

- Run one-off tasks (database migrations, console REPL, data fixes) as processes in the same environment
- Admin code ships with the application code to prevent version drift
- Admin processes use the same config and dependency isolation as the application
- Prefer idempotent admin tasks that can be safely re-run

---

## 2. Beyond Twelve-Factor: 15-Factor Principles

Modern cloud native applications extend the original twelve factors with three additional principles.

### Factor 13: API First

- Design APIs before writing implementation code
- APIs are the primary interface contract between services
- Use machine-readable API specifications (OpenAPI, AsyncAPI, gRPC proto files)
- API versioning strategy must be decided and documented upfront
- Internal and external APIs follow the same contract-first process

### Factor 14: Telemetry

- Every service must emit three pillars of observability:

| Pillar         | Purpose                          | Examples                          |
| -------------- | -------------------------------- | --------------------------------- |
| Metrics        | Quantitative health indicators   | Request rate, error rate, latency |
| Logs           | Discrete event records           | Structured JSON to stdout         |
| Traces         | Distributed request flow         | OpenTelemetry spans               |

- Health check endpoints are mandatory (`/health`, `/ready`)
- Application performance monitoring (APM) must be built in, not bolted on
- Correlation IDs must propagate across all service boundaries

### Factor 15: Security

- Authentication and authorization are infrastructure concerns, not afterthoughts
- Apply zero-trust networking: verify every request regardless of source
- Encrypt data in transit (TLS) and at rest
- Manage secrets via secret management services, never in environment variables as plaintext files
- Dependencies must be regularly scanned for known vulnerabilities
- Apply principle of least privilege to all service accounts and IAM roles

---

## 3. Cloud Native Design Principles

### CNCF Cloud Native Characteristics

| Characteristic         | Description                                                    |
| ---------------------- | -------------------------------------------------------------- |
| Container-Packaged     | Applications are packaged as lightweight containers            |
| Dynamically Managed    | Orchestrated by a central scheduler (e.g., Kubernetes)         |
| Microservices-Oriented | Composed of loosely coupled, independently deployable services |
| Automation-Centric     | CI/CD, infrastructure as code, auto-scaling                    |
| Observable             | Built-in metrics, logging, tracing                             |
| Resilient              | Designed to handle failure gracefully                          |

### Cloud Native Design Rules

- Design for failure: assume any component can fail at any time
- Prefer horizontal scaling over vertical scaling
- Use service meshes for cross-cutting concerns (mTLS, retries, circuit breaking)
- Externalize state to managed services; compute layer must be stateless
- Automate everything: deployment, scaling, recovery, security patching
- Use declarative configuration over imperative scripts
- Treat infrastructure as cattle, not pets -- replace, never repair

### Resilience Patterns

| Pattern          | Purpose                                                | When to Apply                          |
| ---------------- | ------------------------------------------------------ | -------------------------------------- |
| Circuit Breaker  | Prevent cascading failures                             | Remote service calls                   |
| Retry + Backoff  | Handle transient failures                              | Network calls, external APIs           |
| Bulkhead         | Isolate failures to a subset of resources              | Thread pools, connection pools         |
| Timeout          | Prevent indefinite blocking                            | All remote calls                       |
| Fallback         | Provide degraded functionality when a service is down  | Non-critical feature dependencies      |
| Health Check     | Detect unhealthy instances for replacement             | Every service, every container         |

### Container Design Rules

- One process per container (single concern)
- Build immutable images -- never patch running containers
- Use multi-stage builds to minimize image size and attack surface
- Include health check instructions in the container definition
- Run as non-root user
- Do not store data inside the container filesystem

---

## 4. Well-Architected Framework Alignment

Cloud providers define Well-Architected frameworks that complement twelve-factor principles. The core pillars are consistent across providers.

| Pillar                 | AWS                      | GCP                        | Azure                    |
| ---------------------- | ------------------------ | -------------------------- | ------------------------ |
| Operational Excellence | Automate operations, IaC | Automate operations        | DevOps practices         |
| Security               | Defense in depth, IAM    | BeyondCorp, IAM            | Zero Trust, RBAC         |
| Reliability            | Auto-recovery, multi-AZ  | Regional redundancy        | Availability Zones, DR   |
| Performance Efficiency | Right-sizing, caching    | Right-sizing, CDN          | Autoscale, CDN           |
| Cost Optimization      | Right-sizing, reserved   | Committed use, preemptible | Reserved, spot instances |
| Sustainability         | Resource efficiency      | Carbon-aware scheduling    | Carbon optimization      |

> For detailed comparisons and pillar-specific guidance, see `references/well-architected-frameworks.md`.

---

## 5. Anti-Patterns

### Configuration Anti-Patterns

- **Hardcoded config**: Database URLs, API keys, or feature flags embedded in source code
- **Config files per environment**: Maintaining `config.prod.json`, `config.dev.json` in the codebase instead of using environment variables
- **Secrets in environment variables as files committed to VCS**: `.env` files checked into version control

### Statefulness Anti-Patterns

- **Local disk state**: Writing user uploads, session data, or temp files to local disk and expecting persistence
- **In-memory session state**: Storing sessions in process memory without a distributed store
- **Sticky sessions**: Routing users to specific instances, preventing horizontal scaling

### Deployment Anti-Patterns

- **Snowflake servers**: Manually configured servers that cannot be reproduced
- **Mutable deployments**: Patching running instances instead of deploying new releases
- **Missing build/release separation**: Building artifacts on production servers
- **No rollback capability**: Releases that cannot be reverted to a previous version

### Observability Anti-Patterns

- **Log files on disk**: Writing logs to local files instead of stdout
- **No structured logging**: Freeform log messages that cannot be parsed or queried
- **Missing health checks**: Services without liveness or readiness probes
- **No distributed tracing**: Inability to follow a request across service boundaries

### Dependency Anti-Patterns

- **Implicit dependencies**: Relying on system packages or globally installed tools
- **Unpinned versions**: Using `latest` tags or version ranges that can break builds
- **Vendoring without lockfiles**: Copying dependencies without tracking exact versions

---

## 6. Implementation Checklist

Use this checklist when reviewing an application for cloud native readiness.

### Essential (Must Have)

- [ ] Single codebase in version control with CI/CD pipeline
- [ ] All dependencies declared in a manifest with pinned versions
- [ ] Configuration stored in environment variables or external config service
- [ ] Backing services accessed via config-driven connection strings
- [ ] Stateless processes with external state storage
- [ ] Structured logging to stdout
- [ ] Health check endpoints (`/health`, `/ready`)
- [ ] Graceful shutdown on SIGTERM
- [ ] Container image with non-root user
- [ ] Secrets managed via secret manager (not in code or config files)

### Recommended (Should Have)

- [ ] API-first design with machine-readable specification
- [ ] Distributed tracing with correlation ID propagation
- [ ] Circuit breakers on all external service calls
- [ ] Dev/prod parity for backing services
- [ ] Immutable releases with unique identifiers
- [ ] Horizontal scaling via process model
- [ ] Automated rollback capability

---

## 7. Related Skills

| Related Skill            | When to Reference                                                    |
| ------------------------ | -------------------------------------------------------------------- |
| `microservices` skill    | Service decomposition, communication patterns, saga, CQRS            |
| `clean-architecture`     | Layered architecture, ports and adapters, dependency inversion       |
| `dockerfile` skill       | Container image best practices, multi-stage builds                   |
| `k8s-workflow` skill     | Kubernetes deployment, health checks, resource management            |
| `helm-workflow` skill    | Helm chart design for cloud native applications                      |
| `terraform-workflow`     | Infrastructure as code for cloud resource provisioning               |
| `gitops-argocd` skill    | GitOps-based continuous deployment                                   |
| `monitoring` skill       | Metrics, alerting, dashboards, SLI/SLO                               |
| `logging` skill          | Structured logging, log aggregation, log levels                      |
| `secrets-management`     | Secret storage, rotation, access control                             |
| `security` skill         | OWASP Top 10, secure coding, vulnerability scanning                  |
| `api-design` skill       | API-first design, versioning, contract testing                       |
| `distributed-systems`    | CAP theorem, consistency patterns, distributed consensus             |
| `ci-cd` skill            | Build/release/run pipeline design and automation                     |

---

## Additional Resources

- Adam Wiggins, "The Twelve-Factor App" (12factor.net, 2011)
- Kevin Hoffman, "Beyond the Twelve-Factor App" (O'Reilly, 2016)
- CNCF, "Cloud Native Definition v1.0" (github.com/cncf/toc)
- AWS Well-Architected Framework documentation
- Google Cloud Architecture Framework documentation
- Microsoft Azure Well-Architected Framework documentation
- Cornelia Davis, "Cloud Native Patterns" (Manning, 2019)
- Bilgin Ibryam & Roland Huss, "Kubernetes Patterns" (O'Reilly, 2019)
