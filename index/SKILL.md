---
name: index
description: >-
  Meta-skill for routing to appropriate domain-specific skills.
  Provides a categorized routing map to help agents discover relevant skills
  by keyword, technology, or task type.
  Use when you need to discover which skill to use for a given task or context.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
compatibility:
  - OpenCode
  - Claude Code
  - Codex
  - Antigravity
---

# Skill Routing Index

This meta-skill helps agents discover the right skill for a given task. Use the routing tables below to find skills by category, keyword, or technology.

For detailed routing by domain, see `references/by-domain.md`.
For task-oriented routing (combining multiple skills), see `references/by-task.md`.

## 1. Language and Conventions

| Keyword / Situation                                    | Recommended Skill        |
| ------------------------------------------------------ | ------------------------ |
| Java code, Java idioms, Java version migration         | java-convention          |
| Kotlin code, Kotlin idioms, coroutines style           | kotlin-convention        |
| TypeScript code, strict mode, utility types            | typescript-convention    |
| React, Next.js, hooks, component patterns              | react-convention         |
| Java-Kotlin mixed project, JSpecify, interop           | java-kotlin-interop      |
| Gradle build, version catalog, multi-module            | gradle-convention        |

## 2. Spring and Spring Boot

| Keyword / Situation                                    | Recommended Skill        |
| ------------------------------------------------------ | ------------------------ |
| Spring DI, AOP, WebMVC, WebFlux, JPA, scheduling       | spring-framework         |
| Exposed ORM, Kotlin DSL/DAO, table definition          | exposed                  |
| Spring Security, OAuth2, JWT in Spring context         | security                 |

## 3. Architecture and Design

| Keyword / Situation                                    | Recommended Skill        |
| ------------------------------------------------------ | ------------------------ |
| Clean Architecture, Hexagonal, Ports & Adapters        | clean-architecture       |
| DDD, aggregates, bounded contexts, domain events       | ddd                      |
| Microservices, Saga, CQRS, event sourcing, API gateway | microservices            |
| Large-scale system design, CDN, rate limiting          | system-design            |
| Distributed systems, replication, partitioning         | distributed-systems      |
| SOLID principles, class hierarchy, OOP patterns        | object-oriented-design   |

## 4. Infrastructure and Deployment

| Keyword / Situation                                    | Recommended Skill        |
| ------------------------------------------------------ | ------------------------ |
| Kubernetes manifests, pods, services, networking       | k8s-workflow             |
| Helm charts, values, templates, hooks                  | helm-workflow            |
| Terraform, IaC, state management, modules              | terraform-workflow       |
| Dockerfile, multi-stage builds, container security     | dockerfile               |
| GitOps, Argo CD, ApplicationSet, sync strategies       | gitops-argocd            |
| CI/CD, GitHub Actions, deployment pipelines            | ci-cd                    |
| Karpenter, NodePool, autoscaling, spot instances       | karpenter-workflow       |

## 5. Database

| Keyword / Situation                                    | Recommended Skill        |
| ------------------------------------------------------ | ------------------------ |
| Database design, migration, query optimization         | database                 |
| Exposed ORM queries, Kotlin DB access                  | exposed                  |
| Optimistic/pessimistic locking, DB concurrency         | concurrency              |

## 6. Operations and Monitoring

| Keyword / Situation                                    | Recommended Skill        |
| ------------------------------------------------------ | ------------------------ |
| Metrics, Prometheus, Grafana, alerting, health checks  | monitoring               |
| Log levels, structured logging, sensitive data in logs | logging                  |
| Incident management, severity, postmortem, runbooks    | incident-response        |
| Debugging, slow API, OOMKilled, CrashLoopBackOff       | troubleshooting          |
| Chaos testing, failure injection, game days            | chaos-engineering        |

## 7. Security

| Keyword / Situation                                    | Recommended Skill        |
| ------------------------------------------------------ | ------------------------ |
| Input validation, auth, CORS, XSS, CSRF, TLS           | security                 |
| Secret rotation, Vault, ESO, Sealed Secrets            | secrets-management       |

## 8. Testing and Quality

| Keyword / Situation                                    | Recommended Skill        |
| ------------------------------------------------------ | ------------------------ |
| Unit tests, integration tests, BDD, contract testing   | testing                  |
| Load testing, k6, Gatling, performance metrics         | load-testing             |
| Code review, PR review checklist                       | code-review              |
| Code smells, refactoring, design principles            | code-quality             |

## 9. API and Communication

| Keyword / Situation                                    | Recommended Skill        |
| ------------------------------------------------------ | ------------------------ |
| REST API design, URL design, HTTP methods, pagination  | api-design               |
| OpenAPI spec, schema design, code generation           | openapi-spec             |
| HTTP client, timeouts, retry, circuit breaker          | http-client              |
| Kafka, RabbitMQ, async messaging, event-driven         | messaging                |

## 10. Miscellaneous

| Keyword / Situation                                    | Recommended Skill        |
| ------------------------------------------------------ | ------------------------ |
| Git commit conventions, branch strategy                | git-workflow             |
| Cache strategy, TTL, invalidation, Redis               | caching                  |
| JVM tuning, GC, heap analysis, profiling               | jvm-performance          |
| Thread safety, virtual threads, CompletableFuture      | concurrency              |
| Prompt design, LLM patterns, structured output         | prompt-engineering       |
| Technical writing, documentation guide                 | technical-documentation  |
| PDF reading, content extraction                        | pdf-handling             |
| Exception hierarchy, error response format             | error-handling           |
| Weather, air quality, KMA, AccuWeather                 | weather                  |
| Developer resume, STAR method, portfolio               | resume-writing           |
