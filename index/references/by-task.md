# Routing by Task Type

Skill combinations recommended for common task types. Primary skills should be loaded first; secondary skills provide supplementary guidance.

## Code Writing

### Writing new Java/Kotlin code

- **Primary**: java-convention or kotlin-convention
- **Secondary**: code-quality, error-handling
- **If Spring project**: spring-framework
- **If mixed project**: java-kotlin-interop, gradle-convention

### Writing new TypeScript/React code

- **Primary**: typescript-convention or react-convention
- **Secondary**: code-quality, error-handling

### Writing database access code

- **Primary**: database
- **If Kotlin + Exposed**: exposed
- **If Spring + JPA**: spring-framework
- **Secondary**: concurrency (for locking strategies)

### Writing concurrent/parallel code

- **Primary**: concurrency
- **Secondary**: jvm-performance (for tuning), error-handling

## Code Review

### Reviewing a pull request

- **Primary**: code-review
- **Secondary**: code-quality
- **Language-specific**: java-convention, kotlin-convention, typescript-convention, or react-convention
- **If security-related changes**: security

### Reviewing architecture decisions

- **Primary**: clean-architecture or microservices
- **Secondary**: ddd, object-oriented-design, system-design

## API Development

### Designing a new REST API

- **Primary**: api-design
- **Secondary**: openapi-spec, error-handling, security
- **If microservices**: microservices

### Writing OpenAPI specification

- **Primary**: openapi-spec
- **Secondary**: api-design

### Integrating with external APIs

- **Primary**: http-client
- **Secondary**: error-handling, monitoring (for tracking external calls)

## Architecture and Design

### Designing a new service/module

- **Primary**: clean-architecture, ddd
- **Secondary**: object-oriented-design, code-quality

### Designing microservice architecture

- **Primary**: microservices
- **Secondary**: distributed-systems, messaging, api-design, system-design

### Large-scale system design

- **Primary**: system-design
- **Secondary**: distributed-systems, caching, monitoring, database

## Infrastructure

### Setting up Kubernetes deployment

- **Primary**: k8s-workflow
- **Secondary**: helm-workflow, dockerfile
- **If GitOps**: gitops-argocd
- **If autoscaling**: karpenter-workflow

### Writing Terraform infrastructure

- **Primary**: terraform-workflow
- **Secondary**: secrets-management (for secret handling in IaC)

### Building container images

- **Primary**: dockerfile
- **Secondary**: ci-cd (for build pipeline), security (for image security)

### Setting up CI/CD pipeline

- **Primary**: ci-cd
- **Secondary**: testing (test stages), dockerfile (build stages), gitops-argocd (CD)

### GitOps deployment setup

- **Primary**: gitops-argocd
- **Secondary**: helm-workflow, k8s-workflow, ci-cd

## Testing

### Writing unit/integration tests

- **Primary**: testing
- **Secondary**: code-quality (testable design)
- **If Spring**: spring-framework (Spring test support)

### Designing load tests

- **Primary**: load-testing
- **Secondary**: monitoring (metrics collection), ci-cd (CI integration)

### Setting up chaos experiments

- **Primary**: chaos-engineering
- **Secondary**: monitoring, incident-response, k8s-workflow

## Security

### Implementing authentication/authorization

- **Primary**: security
- **If Spring**: spring-framework (Spring Security)
- **Secondary**: api-design (API-level security)

### Managing secrets and credentials

- **Primary**: secrets-management
- **Secondary**: security, k8s-workflow (K8s secrets), terraform-workflow (IaC secrets)

## Operations

### Incident response

- **Primary**: incident-response
- **Secondary**: monitoring, troubleshooting, logging

### Debugging production issues

- **Primary**: troubleshooting
- **Secondary**: monitoring (diagnostic data), logging (log analysis)
- **If K8s**: k8s-workflow
- **If JVM**: jvm-performance

### Setting up observability

- **Primary**: monitoring
- **Secondary**: logging, incident-response (alerting rules)

### JVM performance tuning

- **Primary**: jvm-performance
- **Secondary**: monitoring (JVM metrics), concurrency (thread tuning), dockerfile (container JVM settings)

## Communication and Messaging

### Implementing event-driven architecture

- **Primary**: messaging
- **Secondary**: microservices, distributed-systems, monitoring

### Setting up async messaging (Kafka/RabbitMQ)

- **Primary**: messaging
- **Secondary**: monitoring (queue monitoring), error-handling

## Documentation and Workflow

### Writing technical documentation

- **Primary**: technical-documentation
- **Secondary**: api-design (API docs), openapi-spec (spec docs)

### Git workflow and commit conventions

- **Primary**: git-workflow
- **Secondary**: code-review (PR workflow), ci-cd (branch protection)

### Writing a developer resume

- **Primary**: resume-writing

### Designing cache strategy

- **Primary**: caching
- **Secondary**: system-design, database, monitoring

### Working with PDF files

- **Primary**: pdf-handling

### Checking weather/air quality

- **Primary**: weather

### Designing LLM prompts

- **Primary**: prompt-engineering
