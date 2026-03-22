# Routing by Domain

Detailed routing information for each skill, including core coverage and relationships with other skills.

## Language and Conventions

### java-convention

- **Core coverage**: Java coding conventions, modern idioms, version migration (8 to 25)
- **Related skills**: java-kotlin-interop (mixed projects), gradle-convention (build), spring-framework (Spring-based Java)

### kotlin-convention

- **Core coverage**: Kotlin coding conventions and idioms
- **Related skills**: java-kotlin-interop (mixed projects), gradle-convention (build), exposed (Kotlin ORM)

### typescript-convention

- **Core coverage**: TypeScript type system, strict mode, utility types, error handling, project organization
- **Related skills**: react-convention (React/Next.js with TypeScript)

### react-convention

- **Core coverage**: React and Next.js component patterns, hooks, state management, performance optimization
- **Related skills**: typescript-convention (TypeScript fundamentals)

### java-kotlin-interop

- **Core coverage**: Platform types, null safety (JSpecify), JVM annotations, collection interop, coroutine-Java bridging, SAM conversion
- **Related skills**: java-convention, kotlin-convention, gradle-convention (mixed build setup)

### gradle-convention

- **Core coverage**: Gradle build conventions for Kotlin/JVM multi-module projects, version catalogs
- **Related skills**: java-convention, kotlin-convention, java-kotlin-interop

## Spring and Spring Boot

### spring-framework

- **Core coverage**: IoC/DI, AOP, transaction management, event system, bean lifecycle, WebMVC, WebFlux, validation, scheduling, configuration, JPA
- **Related skills**: security (Spring Security integration), testing (Spring test), database (JPA patterns), exposed (alternative ORM)

### exposed

- **Core coverage**: Jetbrains Exposed ORM DSL/DAO, table definition, query patterns, transaction management, schema migration
- **Related skills**: database (general DB patterns), kotlin-convention (Kotlin idioms), spring-framework (Spring integration)

## Architecture and Design

### clean-architecture

- **Core coverage**: Clean Architecture, Hexagonal Architecture (Ports & Adapters), layer boundaries, data transformation
- **Related skills**: ddd (domain modeling), object-oriented-design (SOLID), microservices (service boundaries)

### ddd

- **Core coverage**: Entities, value objects, aggregates, repositories, domain services, domain events, bounded contexts
- **Related skills**: clean-architecture (layer structure), microservices (bounded context decomposition), database (repository patterns)

### microservices

- **Core coverage**: Service decomposition, sync/async communication, gRPC, API gateway, Saga, CQRS, event sourcing, transactional outbox, fault isolation
- **Related skills**: messaging (async communication), api-design (API contracts), distributed-systems (distributed patterns), monitoring (observability)

### system-design

- **Core coverage**: Database architecture, caching, CDN, stateless design, message queues, consistent hashing, rate limiting, circuit breaker, bulkhead, backpressure
- **Related skills**: distributed-systems (distributed patterns), caching (cache strategies), monitoring (system health)

### distributed-systems

- **Core coverage**: Data replication, partitioning, distributed time, cluster management, network communication
- **Related skills**: system-design (system-level patterns), microservices (service architecture), database (replication)

### object-oriented-design

- **Core coverage**: SOLID principles with practical examples, class hierarchy design
- **Related skills**: clean-architecture (architectural patterns), code-quality (design principles), ddd (domain modeling)

## Infrastructure and Deployment

### k8s-workflow

- **Core coverage**: Kubernetes manifests, security, managed K8s (EKS, AKS, GKE), autoscaling (KEDA, Knative), networking (Ingress, service mesh)
- **Related skills**: helm-workflow (chart packaging), karpenter-workflow (node autoscaling), dockerfile (container images), gitops-argocd (deployment)

### helm-workflow

- **Core coverage**: Chart structure, values design, template best practices, hooks, dependency management, testing, repository management
- **Related skills**: k8s-workflow (Kubernetes fundamentals), gitops-argocd (GitOps deployment)

### terraform-workflow

- **Core coverage**: Core workflow, state management, module design, provider-specific guides (AWS, Azure, GCP)
- **Related skills**: k8s-workflow (infrastructure for K8s), secrets-management (secret handling in IaC)

### dockerfile

- **Core coverage**: Multi-stage builds, layer caching, security, JVM/Spring Boot containerization, BuildKit features, multi-arch builds, signal handling
- **Related skills**: k8s-workflow (deployment targets), ci-cd (build pipelines), jvm-performance (JVM container tuning)

### gitops-argocd

- **Core coverage**: Argo CD application management, sync strategies, secret management, multi-cluster deployment, rollback, notifications, ApplicationSet, progressive delivery
- **Related skills**: helm-workflow (Helm-based deployments), k8s-workflow (Kubernetes targets), ci-cd (CI/CD integration)

### ci-cd

- **Core coverage**: CI/CD pipeline patterns with GitHub Actions, deployment pipelines, branch protection
- **Related skills**: gitops-argocd (CD with ArgoCD), dockerfile (container builds), testing (test stages)

### karpenter-workflow

- **Core coverage**: NodePool configuration, autoscaling patterns, cloud provider configs (AWS, Azure, GCP), troubleshooting
- **Related skills**: k8s-workflow (Kubernetes cluster management), terraform-workflow (infrastructure provisioning)

## Database

### database

- **Core coverage**: Migration conventions, query performance, transaction management, concurrency control, backup, replication, connection pool tuning
- **Related skills**: exposed (Kotlin ORM), spring-framework (JPA), concurrency (DB-level locking)

### concurrency

- **Core coverage**: JVM concurrency, thread safety, synchronization, Executor framework, CompletableFuture, Kotlin coroutines, virtual threads
- **Related skills**: kotlin-convention (coroutines style), java-convention (Java concurrency), jvm-performance (performance tuning), database (DB locking)

## Operations and Monitoring

### monitoring

- **Core coverage**: Metrics (Prometheus, Micrometer), logging, distributed tracing (OpenTelemetry), alerting rules, health checks
- **Related skills**: logging (log standards), incident-response (alerting workflow), troubleshooting (diagnostic data)

### logging

- **Core coverage**: Logging standards, sensitive data handling in logs
- **Related skills**: monitoring (observability stack), security (data protection in logs)

### incident-response

- **Core coverage**: Severity classification, communication protocols, triage, mitigation, runbooks, postmortem, on-call, MTTD/MTTA/MTTR metrics
- **Related skills**: monitoring (alerting triggers), troubleshooting (diagnosis), chaos-engineering (proactive resilience)

### troubleshooting

- **Core coverage**: Debugging slow APIs, deployment rollback, connection issues, OOMKilled, CrashLoopBackOff, debugging principles
- **Related skills**: monitoring (diagnostic data), logging (log analysis), k8s-workflow (K8s-specific issues)

### chaos-engineering

- **Core coverage**: Chaos principles, failure injection, game days, resilience testing
- **Related skills**: incident-response (incident preparedness), monitoring (observing experiments), k8s-workflow (K8s chaos tools)

## Security

### security

- **Core coverage**: Input validation, auth (JWT, OAuth2, session, MFA), CORS, API headers, rate limiting, CSRF, XSS, injection defense, TLS
- **Related skills**: secrets-management (secret handling), spring-framework (Spring Security), api-design (API security)

### secrets-management

- **Core coverage**: Secret lifecycle, storage solutions, rotation policies, Kubernetes patterns (ESO, Sealed Secrets, CSI), CI/CD secrets, certificate management, detection/prevention
- **Related skills**: security (security fundamentals), terraform-workflow (IaC secrets), k8s-workflow (K8s secret patterns)

## Testing and Quality

### testing

- **Core coverage**: BDD-style tests, unit testing, integration testing (Testcontainers), contract testing (Pact, Spring Cloud Contract), performance testing (k6, Gatling)
- **Related skills**: load-testing (dedicated performance testing), code-review (review practices), spring-framework (Spring test support)

### load-testing

- **Core coverage**: k6 and Gatling, test design, metrics, thresholds, CI integration, result analysis
- **Related skills**: testing (general test strategy), monitoring (performance metrics), ci-cd (CI integration)

### code-review

- **Core coverage**: Code review checklist, comment guidelines for PR reviews
- **Related skills**: code-quality (design principles), git-workflow (PR workflow)

### code-quality

- **Core coverage**: Design principles, refactoring techniques, code smell identification, safe refactoring workflows
- **Related skills**: object-oriented-design (SOLID), code-review (review practices), clean-architecture (structural quality)

## API and Communication

### api-design

- **Core coverage**: REST API design, URL design, HTTP methods, status codes, pagination, versioning, security, OpenAPI documentation
- **Related skills**: openapi-spec (specification details), security (API security), error-handling (error responses)

### openapi-spec

- **Core coverage**: OpenAPI specification, schema design, documentation generation, validation, versioning, code generation
- **Related skills**: api-design (API design principles), technical-documentation (documentation practices)

### http-client

- **Core coverage**: External API integration, timeouts, error handling, retry strategy, circuit breaker, response mapping
- **Related skills**: api-design (API contracts), error-handling (error patterns), microservices (inter-service communication)

### messaging

- **Core coverage**: Async messaging, broker selection, message design, producer/consumer patterns, schema evolution, monitoring
- **Related skills**: microservices (event-driven architecture), monitoring (message queue monitoring), distributed-systems (async patterns)

## Miscellaneous

### git-workflow

- **Core coverage**: Git commit conventions, branch strategy
- **Related skills**: code-review (PR workflow), ci-cd (branch protection)

### caching

- **Core coverage**: Cache selection, TTL design, invalidation patterns, stampede prevention, anti-patterns, Redis patterns
- **Related skills**: system-design (caching in architecture), database (query caching), monitoring (cache metrics)

### jvm-performance

- **Core coverage**: GC algorithms, GC selection, heap analysis, profiling tools, cloud-native JVM considerations
- **Related skills**: concurrency (thread/coroutine performance), dockerfile (JVM container tuning), monitoring (JVM metrics)

### prompt-engineering

- **Core coverage**: Prompt design patterns for LLM applications, structured output, evaluation, safety, cost optimization
- **Related skills**: technical-documentation (writing clarity)

### technical-documentation

- **Core coverage**: Technical documentation guide, writing principles, user research, deployment process, quality measurement
- **Related skills**: api-design (API documentation), openapi-spec (spec documentation)

### pdf-handling

- **Core coverage**: PDF file reading and content extraction
- **Related skills**: technical-documentation (document processing)

### error-handling

- **Core coverage**: Exception hierarchy, error classification, response format, handling principles
- **Related skills**: api-design (error responses), http-client (client-side error handling), spring-framework (Spring exception handling)

### weather

- **Core coverage**: Weather and air quality lookup using KMA, AirKorea, and AccuWeather
- **Related skills**: (standalone skill)

### resume-writing

- **Core coverage**: Developer resume structure, STAR method, technical skills organization, project description
- **Related skills**: (standalone skill)
