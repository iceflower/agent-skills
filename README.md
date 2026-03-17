# Agent Skills

[Agent Skills 오픈 표준](https://agentskills.io) 기반의 AI 코딩 에이전트용 스킬 컬렉션입니다.

## 개요

이 저장소는 Java, Kotlin, Spring, Kubernetes, Terraform 등 다양한 기술 스택에 대한 **62개 스킬**을 포함하고 있습니다. 각 스킬은 AI 코딩 에이전트가 특정 작업을 수행할 때 따라야 할 규칙과 가이드라인을 정의합니다.

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
| [spring-framework](./spring-framework/) | Spring Framework 핵심 (IoC/DI, AOP, @Transactional, 이벤트, MVC) |
| [spring-framework-migration](./spring-framework-migration/) | Spring Framework 버전 마이그레이션 (5.x → 6.x → 7.0) |
| [spring-boot-migration](./spring-boot-migration/) | Spring Boot 버전 마이그레이션 (2.7 → 3.x → 4.0) |
| [spring-jpa](./spring-jpa/) | Spring Data JPA (N+1 방지, @Transactional, 엔티티 컨벤션) |
| [spring-webflux](./spring-webflux/) | Spring WebFlux & Kotlin Coroutines (R2DBC, Flow, WebClient, SSE) |
| [spring-config](./spring-config/) | Spring Boot 설정 관리 (@ConfigurationProperties, 프로파일, HikariCP) |
| [spring-security](./spring-security/) | Spring Security 구현 (SecurityFilterChain, Bean Validation, Rate Limiting) |
| [spring-caching](./spring-caching/) | Spring Boot 캐시 구현 (Caffeine, Redis, @Cacheable) |
| [spring-monitoring](./spring-monitoring/) | Spring Boot 모니터링 (Actuator, Micrometer, 분산 트레이싱) |
| [spring-error-handling](./spring-error-handling/) | Spring Boot 에러 처리 (@ControllerAdvice, ErrorCode enum) |
| [spring-http-client](./spring-http-client/) | Spring Boot API 클라이언트 (RestClient, Spring Retry, Resilience4j) |
| [spring-troubleshooting](./spring-troubleshooting/) | Spring Boot 트러블슈팅 (시작 실패, JVM OOM, HikariCP) |

### Java & Kotlin

| 스킬 | 설명 |
|------|------|
| [java-convention](./java-convention/) | Java 코딩 컨벤션 (Records, Sealed Classes, 패턴 매칭, 가상 스레드) |
| [java-migration](./java-migration/) | Java 버전 마이그레이션 가이드 (8 → 11 → 17 → 21 → 25) |
| [kotlin-convention](./kotlin-convention/) | Kotlin 코딩 컨벤션 (Null Safety, 확장 함수, 코루틴) |
| [kotlin-migration](./kotlin-migration/) | Kotlin 버전 마이그레이션 가이드 (1.4 → 2.3) |
| [java-kotlin-interop](./java-kotlin-interop/) | Java-Kotlin 상호 운용 가이드 (JSpecify, JVM 어노테이션, 코루틴 브릿지) |
| [jvm-performance](./jvm-performance/) | JVM 성능 튜닝 (GC 알고리즘, 힙 분석, 프로파일링) |
| [concurrency](./concurrency/) | JVM 동시성 (스레드 안전, Executor, CompletableFuture, 코루틴, 가상 스레드) |

### 데이터베이스

| 스킬 | 설명 |
|------|------|
| [database](./database/) | 데이터베이스 공통 규칙 (마이그레이션, 쿼리 성능, 트랜잭션 관리) |
| [mysql](./mysql/) | MySQL 규칙 (스토리지 엔진, 인덱스, 쿼리 최적화, 파티셔닝) |
| [postgresql](./postgresql/) | PostgreSQL 규칙 (JSONB, GIN 인덱스, CTE, 파티셔닝, 확장) |
| [exposed](./exposed/) | JetBrains Exposed ORM (DSL, DAO, 테이블 정의, Spring Boot 통합) |

### 인프라 & 클라우드

| 스킬 | 설명 |
|------|------|
| [terraform-workflow](./terraform-workflow/) | Terraform 핵심 워크플로우 (상태 관리, 모듈 설계, 버전 관리) |
| [terraform-aws-provider](./terraform-aws-provider/) | AWS Terraform Provider v6.x (Breaking Changes, 베스트 프랙티스) |
| [terraform-azure-provider](./terraform-azure-provider/) | Azure Terraform Provider v4.x (Breaking Changes, 베스트 프랙티스) |
| [terraform-gcp-provider](./terraform-gcp-provider/) | GCP Terraform Provider v6.x (Breaking Changes, 베스트 프랙티스) |
| [k8s-workflow](./k8s-workflow/) | Kubernetes 매니페스트 작성 규칙 및 운영 가이드 |
| [k8s-providers](./k8s-providers/) | 관리형 Kubernetes 서비스 비교 (EKS, AKS, GKE) |
| [k8s-autoscaling](./k8s-autoscaling/) | Kubernetes 오토스케일링 (KEDA, Knative, 이벤트 기반 스케일링) |
| [karpenter-workflow](./karpenter-workflow/) | Karpenter 노드 오토스케일링 워크플로우 |
| [karpenter-providers](./karpenter-providers/) | Karpenter 클라우드 프로바이더별 설정 (AWS, Azure, GKE) |
| [dockerfile](./dockerfile/) | Dockerfile 작성 규칙 (멀티스테이지 빌드, JVM/Spring Boot 패턴) |
| [ci-cd](./ci-cd/) | GitHub Actions 기반 CI/CD 파이프라인 패턴 |

### 아키텍처 & 설계

| 스킬 | 설명 |
|------|------|
| [clean-architecture](./clean-architecture/) | 클린 아키텍처 / 헥사고날 아키텍처 (포트 & 어댑터) 패턴 |
| [microservices](./microservices/) | 마이크로서비스 아키텍처 (서비스 분해, Saga, CQRS, API Gateway) |
| [ddd](./ddd/) | 도메인 주도 설계 (엔티티, 애그리거트, 값 객체, 바운디드 컨텍스트) |
| [object-oriented-design](./object-oriented-design/) | 객체지향 설계 원칙 (SOLID, Tell Don't Ask, 합성 우선) |
| [system-design](./system-design/) | 대규모 시스템 설계 패턴 (샤딩, 캐싱, CDN, 메시지 큐) |
| [system-stability-patterns](./system-stability-patterns/) | 시스템 안정성 패턴 (Circuit Breaker, Bulkhead, Backpressure) |
| [distributed-systems](./distributed-systems/) | 분산 시스템 패턴 (데이터 복제, 파티셔닝, 합의 알고리즘, 클러스터 관리) |
| [refactoring](./refactoring/) | 리팩토링 기법 (코드 스멜, 추출/인라인, 조건문 단순화) |

### 코드 품질 & 테스트

| 스킬 | 설명 |
|------|------|
| [code-quality](./code-quality/) | 코드 품질 6대 원칙 (가독성, 예측성, 오용 방지, 모듈성, 재사용성, 테스트 용이성) |
| [code-review](./code-review/) | 코드 리뷰 체크리스트 및 코멘트 작성 가이드 |
| [testing-unit](./testing-unit/) | BDD 스타일 단위 테스트 (Describe-Context-It, 테스트 더블) |
| [testing-integration](./testing-integration/) | 통합 테스트 패턴 (Testcontainers, Mock 서버, 테스트 데이터) |
| [error-handling](./error-handling/) | 에러 처리 패턴 (예외 계층, 에러 분류, 응답 포맷) |

### 운영 & 모니터링

| 스킬 | 설명 |
|------|------|
| [logging](./logging/) | 로깅 표준 (로그 레벨, 구조화 로깅, 민감 데이터 마스킹) |
| [monitoring](./monitoring/) | 옵저버빌리티 패턴 (메트릭, 로깅, 트레이싱, 알림 규칙) |
| [caching](./caching/) | 캐시 전략 선택, TTL 설계, 무효화 패턴, 안티패턴 |
| [messaging](./messaging/) | 비동기 메시징 패턴 (Kafka, RabbitMQ, NATS, Pulsar) |
| [troubleshooting](./troubleshooting/) | 트러블슈팅 가이드 (느린 API, 롤백, 연결 문제, 디버깅 원칙) |
| [chaos-engineering](./chaos-engineering/) | 카오스 엔지니어링 실험 설계, 장애 주입, Game Day 운영 |

### 기타

| 스킬 | 설명 |
|------|------|
| [git-workflow](./git-workflow/) | Git 커밋 컨벤션 및 브랜치 전략 |
| [gradle-convention](./gradle-convention/) | Gradle 빌드 컨벤션 (멀티모듈, 버전 카탈로그, Convention 플러그인) |
| [http-client](./http-client/) | 외부 API 클라이언트 규칙 (타임아웃, 재시도, Circuit Breaker) |
| [security](./security/) | 보안 규칙 (입력 검증, 인증/인가, CORS, Rate Limiting, 시크릿 관리) |
| [api-design](./api-design/) | REST API 설계 원칙 (URL 설계, HTTP 메서드, 상태 코드, 페이지네이션, 버전 관리) |
| [resume](./resume/) | 개발자 이력서 작성 가이드 (STAR 메서드, 스킬 정리, 프로젝트 기술) |
| [pdf-handling](./pdf-handling/) | PDF 파일 읽기 및 처리 규칙 (pdftoppm 변환) |
| [accuweather](./accuweather/) | AccuWeather 기반 날씨 정보 조회 규칙 (일기예보, 미세먼지, 자외선 지수 등) |
| [technical-documentation](./technical-documentation/) | 기술 문서 작성 가이드 (사용자 리서치, 품질 측정, 배포) |

## 디렉토리 구조

```text
<skill-name>/
├── SKILL.md    # 스킬 정의 (필수)
└── README.md   # 스킬 설명
```

각 `SKILL.md`는 YAML frontmatter(`name`, `description`)와 마크다운 본문으로 구성됩니다.

## 라이선스

MIT License
