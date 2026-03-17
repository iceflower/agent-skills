# Agent Skills

[Agent Skills 오픈 표준](https://agentskills.io) 기반의 AI 코딩 에이전트용 스킬 컬렉션입니다.

## 개요

이 저장소는 Java, Kotlin, Spring, Kubernetes, Terraform 등 다양한 기술 스택에 대한 **40개 스킬**을 포함하고 있습니다. 관련 스킬은 `references/` 하위 디렉토리를 활용하여 하나의 스킬로 통합되어 있습니다.

## 호환 도구

| 도구 | 전역 경로 | 프로젝트 경로 |
|------|-----------|---------------|
| **OpenCode** | `~/.agents/skills/` | `.agents/skills/` |
| **Codex** | `~/.agents/skills/` | `.agents/skills/` |
| **Claude Code** | `~/.claude/skills/` | `.claude/skills/` |
| **Antigravity** | `~/.gemini/antigravity/skills/` | `.agents/skills/` |

## 설치

### 전역 설치 (모든 프로젝트에서 사용)

```bash
# 표준 경로에 클론
git clone https://github.com/iceflower/agent-skills.git ~/.agents/skills

# Claude Code용 심볼릭 링크 (필요시)
ln -s ~/.agents/skills ~/.claude/skills

# Antigravity용 심볼릭 링크 (필요시)
mkdir -p ~/.gemini/antigravity
ln -s ~/.agents/skills ~/.gemini/antigravity/skills
```

### 프로젝트 설치 (특정 프로젝트에서만 사용)

```bash
# 프로젝트 루트에서
git clone https://github.com/iceflower/agent-skills.git .agents/skills
```

## 스킬 목록

### Spring & Spring Boot

| 스킬 | 설명 |
|------|------|
| [spring-framework](./spring-framework/) | Spring Framework 핵심 + Framework/Boot 버전 마이그레이션 가이드 |
| [spring-jpa](./spring-jpa/) | Spring Data JPA (N+1 방지, @Transactional, 엔티티 컨벤션) |
| [spring-webflux](./spring-webflux/) | Spring WebFlux & Kotlin Coroutines (R2DBC, Flow, WebClient, SSE) |
| [spring-config](./spring-config/) | Spring Boot 설정 관리 (@ConfigurationProperties, 프로파일, HikariCP) |

### Java & Kotlin

| 스킬 | 설명 |
|------|------|
| [java-convention](./java-convention/) | Java 코딩 컨벤션 + 버전 마이그레이션 가이드 (8 → 25) |
| [kotlin-convention](./kotlin-convention/) | Kotlin 코딩 컨벤션 + 버전 마이그레이션 가이드 (1.4 → 2.3) |
| [java-kotlin-interop](./java-kotlin-interop/) | Java-Kotlin 상호 운용 가이드 (JSpecify, JVM 어노테이션) |
| [jvm-performance](./jvm-performance/) | JVM 성능 튜닝 (GC 알고리즘, 힙 분석, 프로파일링) |
| [concurrency](./concurrency/) | JVM 동시성 (스레드 안전, Executor, CompletableFuture, 코루틴) |

### 데이터베이스

| 스킬 | 설명 |
|------|------|
| [database](./database/) | 데이터베이스 공통 규칙 + MySQL/PostgreSQL 특화 가이드 |
| [exposed](./exposed/) | JetBrains Exposed ORM (DSL, DAO, Spring Boot 통합) |

### 인프라 & 클라우드

| 스킬 | 설명 |
|------|------|
| [terraform-workflow](./terraform-workflow/) | Terraform 워크플로우 + AWS/Azure/GCP 프로바이더 가이드 |
| [k8s-workflow](./k8s-workflow/) | Kubernetes 매니페스트 + 관리형 K8s + 오토스케일링 |
| [karpenter-workflow](./karpenter-workflow/) | Karpenter 워크플로우 + 클라우드 프로바이더별 설정 |
| [dockerfile](./dockerfile/) | Dockerfile 작성 규칙 (멀티스테이지, JVM/Spring Boot) |
| [ci-cd](./ci-cd/) | GitHub Actions 기반 CI/CD 파이프라인 패턴 |

### 아키텍처 & 설계

| 스킬 | 설명 |
|------|------|
| [clean-architecture](./clean-architecture/) | 클린 아키텍처 / 헥사고날 아키텍처 (포트 & 어댑터) |
| [microservices](./microservices/) | 마이크로서비스 (서비스 분해, Saga, CQRS, API Gateway) |
| [ddd](./ddd/) | 도메인 주도 설계 (엔티티, 애그리거트, 바운디드 컨텍스트) |
| [object-oriented-design](./object-oriented-design/) | 객체지향 설계 원칙 (SOLID, 합성 우선) |
| [system-design](./system-design/) | 대규모 시스템 설계 + 안정성 패턴 (Circuit Breaker, Bulkhead) |
| [distributed-systems](./distributed-systems/) | 분산 시스템 (복제, 파티셔닝, 합의 알고리즘) |

### 코드 품질 & 테스트

| 스킬 | 설명 |
|------|------|
| [code-quality](./code-quality/) | 코드 품질 6대 원칙 + 리팩토링 기법 |
| [code-review](./code-review/) | 코드 리뷰 체크리스트 및 코멘트 가이드 |
| [testing-unit](./testing-unit/) | BDD 단위 테스트 + 통합 테스트 (Testcontainers) |
| [error-handling](./error-handling/) | 에러 처리 패턴 + Spring Boot 구현 |

### 운영 & 모니터링

| 스킬 | 설명 |
|------|------|
| [logging](./logging/) | 로깅 표준 (로그 레벨, 구조화 로깅, 민감 데이터 마스킹) |
| [monitoring](./monitoring/) | 옵저버빌리티 패턴 + Spring Boot 구현 (Actuator, Micrometer) |
| [caching](./caching/) | 캐시 전략 + Spring Boot 구현 (Caffeine, Redis) |
| [messaging](./messaging/) | 비동기 메시징 (Kafka, RabbitMQ, NATS, Pulsar) |
| [troubleshooting](./troubleshooting/) | 트러블슈팅 가이드 + Spring Boot 트러블슈팅 |
| [chaos-engineering](./chaos-engineering/) | 카오스 엔지니어링 (장애 주입, Game Day) |

### 기타

| 스킬 | 설명 |
|------|------|
| [git-workflow](./git-workflow/) | Git 커밋 컨벤션 및 브랜치 전략 |
| [gradle-convention](./gradle-convention/) | Gradle 빌드 컨벤션 (멀티모듈, 버전 카탈로그) |
| [http-client](./http-client/) | 외부 API 클라이언트 + Spring Boot 구현 (RestClient, Resilience4j) |
| [security](./security/) | 보안 규칙 + Spring Boot 구현 (SecurityFilterChain) |
| [api-design](./api-design/) | REST API 설계 원칙 (URL, 상태 코드, 버전 관리) |
| [resume](./resume/) | 개발자 이력서 작성 가이드 (STAR 메서드) |
| [pdf-handling](./pdf-handling/) | PDF 파일 읽기 및 처리 규칙 |
| [accuweather](./accuweather/) | AccuWeather 기반 날씨 정보 조회 |
| [technical-documentation](./technical-documentation/) | 기술 문서 작성 가이드 (품질 측정, 배포) |

## 디렉토리 구조

```text
<skill-name>/
├── SKILL.md           # 스킬 정의 (필수)
├── README.md          # 스킬 설명
└── references/        # 관련 참조 문서 (선택)
    ├── spring.md
    ├── migration.md
    └── ...
```

각 `SKILL.md`는 YAML frontmatter(`name`, `description`)와 마크다운 본문으로 구성됩니다. `references/` 디렉토리에는 관련된 세부 가이드가 포함됩니다.

## 라이선스

MIT License
