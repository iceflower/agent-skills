# Spring Boot + Exposed Integration Rules

Exposed ORM의 일반 규칙(DSL vs DAO, 테이블 정의, 쿼리 패턴, 트랜잭션 관리)은 `exposed` 스킬 참조.

이 문서는 Spring Boot와 Exposed의 통합 패턴만 다룹니다.

### Dependency Setup

```kotlin
// build.gradle.kts
dependencies {
    implementation("org.jetbrains.exposed:exposed-spring-boot-starter:${exposedVersion}")
    implementation("org.jetbrains.exposed:exposed-core:${exposedVersion}")
    implementation("org.jetbrains.exposed:exposed-dao:${exposedVersion}")
    implementation("org.jetbrains.exposed:exposed-kotlin-datetime:${exposedVersion}")
    implementation("org.jetbrains.exposed:exposed-json:${exposedVersion}")
}
```

### Spring Configuration

```yaml
# application.yml
spring:
  datasource:
    url: ${DB_URL}
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}

exposed:
  generate-ddl: false
  show-sql: ${EXPOSED_SHOW_SQL:false}
```

### Spring Transaction Integration

```kotlin
@Service
class UserService(
    private val database: Database
) {
    @Transactional(readOnly = true)
    fun findActiveUsers(): List<UserResponse> = transaction {
        Users.selectAll()
            .where { Users.status eq UserStatus.ACTIVE }
            .map { it.toUserResponse() }
    }

    @Transactional
    fun createUser(request: CreateUserRequest): Long = transaction {
        Users.insertAndGetId {
            it[name] = request.name
            it[email] = request.email
            it[status] = UserStatus.ACTIVE
        }.value
    }
}
```

### Spring Integration Rules

- Use `exposed-spring-boot-starter` for auto-configuration
- Spring `@Transactional` and Exposed `transaction` can coexist — Spring manages the outer transaction
- Set `exposed.generate-ddl=false` in production — use migration tools instead
- Use `exposed-kotlin-datetime` for `kotlinx.datetime` type support
