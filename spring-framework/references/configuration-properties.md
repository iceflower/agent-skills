# Configuration Properties

## Preferred Pattern (Kotlin)

```kotlin
@ConfigurationProperties(prefix = "app.feature")
data class FeatureProperties(
    val enabled: Boolean = false,
    val maxRetries: Int = 3,
    val timeout: Duration = Duration.ofSeconds(30),
    val allowedOrigins: List<String> = emptyList()
)
```

## Preferred Pattern (Java)

```java
@ConfigurationProperties(prefix = "app.feature")
public record FeatureProperties(
    boolean enabled,
    int maxRetries,
    Duration timeout,
    List<String> allowedOrigins
) {
    public FeatureProperties {
        if (maxRetries < 0) throw new IllegalArgumentException("maxRetries must be >= 0");
        if (timeout == null) timeout = Duration.ofSeconds(30);
        if (allowedOrigins == null) allowedOrigins = List.of();
    }
}
```

## Registration

```java
@Configuration
@EnableConfigurationProperties(FeatureProperties.class)
public class AppConfig {}
```

```kotlin
@Configuration
@EnableConfigurationProperties(FeatureProperties::class)
class AppConfig
```

## Configuration Properties Rules

- Always use `@ConfigurationProperties` over `@Value` for grouped config
- Use `data class` (Kotlin) or `record` (Java) for immutable configuration binding
- Provide sensible defaults for all properties
- Use `Duration`, `DataSize` types instead of raw numbers
- Validate with `@Validated` and JSR-303 annotations when needed

```kotlin
@Validated
@ConfigurationProperties(prefix = "app.http-client")
data class HttpClientProperties(
    val connectTimeout: Duration = Duration.ofSeconds(5),
    val readTimeout: Duration = Duration.ofSeconds(30),
    @field:Min(1) @field:Max(100)
    val maxConnections: Int = 20
)
```

## Environment Variable Binding

| YAML key                | Environment variable              |
| ----------------------- | --------------------------------- |
| `app.feature.enabled`   | `APP_FEATURE_ENABLED`             |
| `app.db.pool-size`      | `APP_DB_POOL_SIZE`                |
| `spring.datasource.url` | `SPRING_DATASOURCE_URL`           |

- Use `${ENV_VAR:default}` syntax for all environment-specific values
- Kebab-case in YAML, SCREAMING_SNAKE in env vars
- Always provide defaults for non-secret values
- Never provide defaults for secrets (force explicit configuration)

## Secret Management

```yaml
# Do
spring:
  datasource:
    url: ${DB_URL}
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}

jwt:
  secret: ${JWT_SECRET}
```

- Secrets must come from environment variables or secret managers
- No default values for secrets — fail fast if missing
- Use Kubernetes Secrets or cloud provider secret managers in production

## Connection Pool Configuration (HikariCP)

```yaml
spring:
  datasource:
    hikari:
      minimum-idle: ${DB_POOL_MIN_IDLE:5}
      maximum-pool-size: ${DB_POOL_MAX_SIZE:10}
      idle-timeout: ${DB_POOL_IDLE_TIMEOUT:300000}
      max-lifetime: ${DB_POOL_MAX_LIFETIME:1800000}
      connection-timeout: ${DB_POOL_CONNECTION_TIMEOUT:30000}
      pool-name: app-hikari-pool
```

| Environment | Min Idle | Max Pool | Rationale                  |
| ----------- | -------- | -------- | -------------------------- |
| Local       | 2        | 5        | Minimal resources          |
| Dev         | 3        | 10       | Moderate concurrency       |
| Staging     | 5        | 15       | Near-production load       |
| Production  | 5        | 20       | Handle peak traffic        |

- Formula: `max_pool_size = (core_count * 2) + disk_spindles`
- Always set `max-lifetime` below database connection timeout

## Actuator Configuration

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
      base-path: /actuator
  endpoint:
    health:
      show-details: when-authorized
      probes:
        enabled: true
  health:
    livenessState:
      enabled: true
    readinessState:
      enabled: true
```

- Never expose all actuator endpoints in production
- Protect sensitive endpoints (env, configprops, beans) behind authentication