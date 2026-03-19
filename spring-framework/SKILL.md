---
name: spring-framework
description: >-
  Spring Framework core conventions including IoC/DI, AOP, transaction management,
  event system, bean lifecycle, WebMVC, WebFlux, validation, scheduling,
  configuration management, and JPA/data access patterns.
  Includes Spring Boot implementation patterns for caching, error handling, HTTP client,
  monitoring, security, troubleshooting, and integration with Exposed ORM and Kotlin interop.
  Includes migration guides for Framework (5.x → 7.0) and Boot (2.7 → 4.0).
  Use when working with Spring Framework or Spring Boot features.
---

# Spring Framework Core Rules

## 1. IoC and Dependency Injection

### Constructor Injection (Preferred)

```java
@Service
public class OrderService {
    private final UserRepository userRepository;
    private final PaymentGateway paymentGateway;
    private final ApplicationEventPublisher eventPublisher;

    // Single constructor — no @Autowired needed
    public OrderService(UserRepository userRepository,
                        PaymentGateway paymentGateway,
                        ApplicationEventPublisher eventPublisher) {
        this.userRepository = userRepository;
        this.paymentGateway = paymentGateway;
        this.eventPublisher = eventPublisher;
    }
}
```

```kotlin
// Kotlin — primary constructor injection
@Service
class OrderService(
    private val userRepository: UserRepository,
    private val paymentGateway: PaymentGateway,
    private val eventPublisher: ApplicationEventPublisher
)
```

### Injection Anti-Patterns

```java
// Bad: field injection — hides dependencies, untestable without reflection
@Autowired
private UserRepository userRepository;

// Bad: setter injection — mutable dependency, easy to forget
@Autowired
public void setUserRepository(UserRepository repo) { ... }

// Bad: multiple constructors without @Autowired — ambiguous
public OrderService(UserRepository repo) { ... }
public OrderService(UserRepository repo, PaymentGateway gw) { ... }
```

### Bean Scope

| Scope       | Lifecycle                        | Use Case                         |
| ----------- | -------------------------------- | -------------------------------- |
| `singleton` | One instance per ApplicationContext (default) | Stateless services, repositories |
| `prototype` | New instance per injection/request | Stateful, short-lived objects    |
| `request`   | One per HTTP request             | Request-scoped data              |
| `session`   | One per HTTP session             | Session-scoped data              |

- Default is `singleton` — do not store mutable state in singleton beans
- Injecting `prototype` into `singleton` does NOT create new instances — use `ObjectProvider<T>` or `@Lookup`

### Conditional Bean Registration

```java
@Configuration
public class InfraConfig {
    @Bean
    @Profile("production")
    public DataSource productionDataSource() { ... }

    @Bean
    @Profile("local")
    public DataSource localDataSource() { ... }

    @Bean
    @ConditionalOnProperty(name = "app.cache.enabled", havingValue = "true")
    public CacheManager cacheManager() { ... }
}
```

---

## 2. AOP (Aspect-Oriented Programming)

### Aspect Definition

```java
@Aspect
@Component
public class LoggingAspect {

    @Around("@annotation(Loggable)")
    public Object logExecution(ProceedingJoinPoint joinPoint) throws Throwable {
        String method = joinPoint.getSignature().toShortString();
        log.info("Entering: {}", method);

        long start = System.currentTimeMillis();
        try {
            Object result = joinPoint.proceed();
            log.info("Exiting: {} ({}ms)", method, System.currentTimeMillis() - start);
            return result;
        } catch (Exception e) {
            log.error("Exception in: {}", method, e);
            throw e;
        }
    }
}

// Custom annotation for marking methods
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Loggable {}
```

### Pointcut Expressions

| Expression                                      | Matches                                 |
| ----------------------------------------------- | --------------------------------------- |
| `execution(* com.example.service.*.*(..))`      | All methods in service package          |
| `@annotation(com.example.Loggable)`             | Methods annotated with @Loggable        |
| `@within(org.springframework.stereotype.Service)` | All methods in @Service classes       |
| `bean(userService)`                             | All methods on bean named userService   |

### Proxy Mechanism Rules

- Spring AOP uses **JDK dynamic proxy** (interface-based) or **CGLIB proxy** (class-based)
- **Self-invocation does NOT trigger AOP** — calling `this.method()` bypasses the proxy

```java
@Service
public class UserService {
    @Transactional
    public void createUser(User user) {
        userRepository.save(user);
        this.sendWelcomeEmail(user); // AOP NOT applied — self-invocation
    }

    @Async
    public void sendWelcomeEmail(User user) { ... } // Will NOT run async
}

// Fix: extract to separate bean or use self-injection
@Service
public class UserService {
    private final EmailService emailService; // Separate bean

    @Transactional
    public void createUser(User user) {
        userRepository.save(user);
        emailService.sendWelcomeEmail(user); // AOP applied correctly
    }
}
```

### AOP Rules

- Use `@Around` for timing, logging, retry — use `@Before`/`@After` for simpler cross-cutting
- Never put business logic in aspects — only cross-cutting concerns
- Self-invocation bypasses proxy — extract to separate bean when AOP is needed
- AOP adds runtime overhead — avoid on hot paths with millions of calls/sec

---

## 3. Transaction Management

### @Transactional Behavior

```java
@Service
public class OrderService {
    private final OrderRepository orderRepository;
    private final PaymentService paymentService;

    // Read-write transaction (default)
    @Transactional
    public Order createOrder(CreateOrderRequest request) {
        Order order = Order.from(request);
        return orderRepository.save(order);
    }

    // Read-only transaction — enables optimizations
    @Transactional(readOnly = true)
    public Order findById(Long id) {
        return orderRepository.findById(id)
            .orElseThrow(() -> new EntityNotFoundException("Order", id));
    }
}
```

### Propagation Levels

| Propagation      | Behavior                                          | Use Case                         |
| ---------------- | ------------------------------------------------- | -------------------------------- |
| `REQUIRED`       | Join existing or create new (default)             | Most business operations         |
| `REQUIRES_NEW`   | Always create new, suspend existing               | Audit logging, independent ops   |
| `SUPPORTS`       | Join existing or run non-transactional             | Read-only queries                |
| `NOT_SUPPORTED`  | Suspend existing, run non-transactional            | Non-critical operations          |
| `MANDATORY`      | Must run in existing transaction, else exception   | Operations requiring caller tx   |
| `NEVER`          | Must NOT run in transaction, else exception        | Operations that must not be tx   |
| `NESTED`         | Nested transaction with savepoint                  | Partial rollback scenarios       |

### Rollback Rules

```java
// Default: rollback on unchecked exceptions (RuntimeException), NOT on checked
@Transactional
public void process() {
    // RuntimeException → rollback
    // IOException (checked) → commit (NOT rolled back)
}

// Explicit rollback for checked exceptions
@Transactional(rollbackFor = IOException.class)
public void processFile() throws IOException { ... }

// No rollback for specific runtime exceptions
@Transactional(noRollbackFor = BusinessValidationException.class)
public void validate() { ... }
```

### Transaction Pitfalls

- **Self-invocation**: `@Transactional` on method B called from method A in the same class does NOT create transaction (proxy bypass)
- **Private methods**: `@Transactional` on private methods is silently ignored
- **Exception swallowed**: Catching exception inside `@Transactional` prevents rollback
- **Long transactions**: Never call external APIs inside `@Transactional` — hold locks too long

```java
// Bad: exception caught inside transaction — no rollback
@Transactional
public void riskyOperation() {
    try {
        repository.save(entity);
        externalApi.call(); // Fails
    } catch (Exception e) {
        log.error("Failed", e); // Transaction commits despite failure
    }
}

// Good: let exception propagate
@Transactional
public void riskyOperation() {
    repository.save(entity);
    // External API call should be outside @Transactional
}
```

---

## 4. Event System

### Publishing Events

```java
// Event class (record preferred for immutability)
public record OrderCreatedEvent(Long orderId, Long userId, BigDecimal amount) {}

// Publishing
@Service
public class OrderService {
    private final ApplicationEventPublisher eventPublisher;

    @Transactional
    public Order createOrder(CreateOrderRequest request) {
        Order order = orderRepository.save(Order.from(request));
        eventPublisher.publishEvent(new OrderCreatedEvent(
            order.getId(), order.getUserId(), order.getAmount()
        ));
        return order;
    }
}
```

### Consuming Events

```java
@Component
public class OrderEventHandler {

    // Synchronous listener — runs in publisher's thread and transaction
    @EventListener
    public void onOrderCreated(OrderCreatedEvent event) {
        log.info("Order created: {}", event.orderId());
    }

    // Async listener — runs in separate thread
    @Async
    @EventListener
    public void sendOrderNotification(OrderCreatedEvent event) {
        notificationService.send(event.userId(), "Order confirmed");
    }

    // Runs AFTER transaction commits — safe for side effects
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void afterOrderCommitted(OrderCreatedEvent event) {
        externalApi.notifyPartner(event.orderId());
    }
}
```

### Event Rules

| Listener Type                 | Transaction Context              | Use Case                        |
| ----------------------------- | -------------------------------- | ------------------------------- |
| `@EventListener`             | Same transaction as publisher    | In-process sync processing      |
| `@Async @EventListener`      | No transaction (new thread)      | Fire-and-forget side effects    |
| `@TransactionalEventListener` | Runs after tx phase (e.g., commit) | External calls after commit   |

- Use `@TransactionalEventListener(AFTER_COMMIT)` for operations that must not execute if transaction rolls back
- `@TransactionalEventListener` events are NOT delivered if no transaction is active
- For cross-service events, use messaging (Kafka, NATS) instead of `ApplicationEvent`

---

## 5. Bean Lifecycle

### Lifecycle Callbacks

```java
@Component
public class CacheWarmer {

    @PostConstruct
    public void init() {
        // Called after dependency injection is complete
        // Use for initialization logic
        loadCache();
    }

    @PreDestroy
    public void cleanup() {
        // Called before bean destruction
        // Use for cleanup (close connections, flush buffers)
        clearCache();
    }
}
```

### Lifecycle Order

```text
1. Constructor called
2. Dependencies injected
3. @PostConstruct
4. ApplicationContext ready
5. ... (application runs) ...
6. @PreDestroy
7. Bean destroyed
```

### Rules

- Prefer `@PostConstruct` over `InitializingBean.afterPropertiesSet()`
- `@PostConstruct` runs once — do not put retry logic here
- Keep `@PostConstruct` fast — slow initialization delays application startup
- Use `ApplicationRunner` or `CommandLineRunner` for Boot-specific startup tasks

---

## 6. Spring WebMVC

> **See [references/webmvc.md](references/webmvc.md) for detailed patterns including:**
> - REST Controller patterns (CRUD, pagination, binding)
> - Exception handling (`@RestControllerAdvice`)
> - Filter vs Interceptor usage
> - CORS configuration
> - File upload/download
> - ResponseEntity patterns

### Filter vs Interceptor vs AOP

| Mechanism      | Level             | Access To                    | Use Case                       |
| -------------- | ----------------- | ---------------------------- | ------------------------------ |
| `Filter`       | Servlet           | Request/Response only        | Authentication, CORS, logging  |
| `Interceptor`  | Spring MVC        | Handler method info          | Request timing, authorization  |
| `AOP`          | Spring bean       | Method args, return value    | Business cross-cutting concerns|

---

## 7. Spring WebFlux

> **See [references/webflux.md](references/webflux.md) for detailed patterns including:**
> - Kotlin Coroutines integration (suspend functions, Flow)
> - R2DBC database access
> - WebClient configuration and usage
> - Parallel execution with coroutineScope
> - SSE streaming
> - Error handling and timeouts

### WebFlux vs MVC Selection

| Scenario                                    | WebFlux | MVC  |
| ------------------------------------------- | ------- | ---- |
| High concurrency with I/O-bound workloads   | Yes     |      |
| Streaming data (SSE, WebSocket)             | Yes     |      |
| CPU-bound workloads                         |         | Yes  |
| Blocking libraries (JDBC, legacy SDK)       |         | Yes  |

### Key Constraint

- WebFlux runs on a small, fixed thread pool (event loop)
- **Never block the event loop** — use `Dispatchers.IO` for blocking calls

---

## 8. Validation

### Bean Validation with Custom Validators

```java
// Custom constraint annotation
@Target({ElementType.FIELD, ElementType.PARAMETER})
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = PhoneNumberValidator.class)
public @interface ValidPhoneNumber {
    String message() default "Invalid phone number format";
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}

// Validator implementation
public class PhoneNumberValidator
    implements ConstraintValidator<ValidPhoneNumber, String> {

    private static final Pattern PHONE_PATTERN =
        Pattern.compile("^\\d{2,3}-\\d{3,4}-\\d{4}$");

    @Override
    public boolean isValid(String value, ConstraintValidatorContext context) {
        if (value == null) return true; // Use @NotNull for null checks
        return PHONE_PATTERN.matcher(value).matches();
    }
}
```

### Validation Groups

```java
// Define groups
public interface OnCreate {}
public interface OnUpdate {}

// Use groups on fields
public record UserRequest(
    @Null(groups = OnCreate.class)
    @NotNull(groups = OnUpdate.class)
    Long id,

    @NotBlank(groups = {OnCreate.class, OnUpdate.class})
    String name
) {}

// Apply group in controller
@PostMapping
public UserResponse create(@Validated(OnCreate.class) @RequestBody UserRequest req) { ... }

@PutMapping("/{id}")
public UserResponse update(@Validated(OnUpdate.class) @RequestBody UserRequest req) { ... }
```

### Validation Rules

- Validate at API boundaries — do not trust input from controllers
- Use `@Validated` (Spring) over `@Valid` (Jakarta) when validation groups are needed
- Custom validators should be stateless and thread-safe
- Return `true` for `null` values — let `@NotNull` handle null checking separately

---

## 9. Task Scheduling

### @Scheduled

```java
@Configuration
@EnableScheduling
public class SchedulingConfig {}

@Component
public class CleanupTask {

    @Scheduled(fixedDelay = 60_000) // 60s after previous completion
    public void cleanExpiredSessions() {
        sessionRepository.deleteExpired();
    }

    @Scheduled(cron = "0 0 2 * * *") // Daily at 2:00 AM
    public void generateDailyReport() {
        reportService.generateDaily();
    }

    @Scheduled(fixedRate = 30_000) // Every 30s regardless of previous
    public void refreshCache() {
        cacheService.refresh();
    }
}
```

### @Async

```java
@Configuration
@EnableAsync
public class AsyncConfig {}

@Service
public class NotificationService {

    @Async
    public CompletableFuture<Void> sendEmail(String to, String body) {
        emailClient.send(to, body);
        return CompletableFuture.completedFuture(null);
    }
}
```

### Scheduling Rules

| Parameter    | Behavior                                    |
| ------------ | ------------------------------------------- |
| `fixedDelay` | Wait N ms after previous execution finishes |
| `fixedRate`  | Execute every N ms (may overlap if slow)    |
| `cron`       | Cron expression for calendar-based schedule |

- `@Scheduled` methods must return `void` and take no parameters
- `@Async` methods must return `void` or `CompletableFuture`
- `@Async` on self-invoked methods does NOT work (proxy bypass) — same as `@Transactional`
- Default executor is single-threaded — configure `TaskScheduler` for parallel scheduled tasks

---

## 10. Configuration Management

### Profile Structure

```text
src/main/resources/
├── application.yml              # Common settings (all profiles)
├── application-local.yml        # Local development
├── application-dev.yml          # Dev environment
├── application-staging.yml      # Staging environment
└── application-prod.yml         # Production environment
```

### Profile Activation

```yaml
# application.yml — default profile
spring:
  profiles:
    active: ${SPRING_PROFILES_ACTIVE:local}
```

### Profile Separation Rules

| Setting              | Common | Local | Dev | Staging | Prod |
| -------------------- | ------ | ----- | --- | ------- | ---- |
| Server port          | Yes    |       |     |         |      |
| DB URL               |        | Yes   | Yes | Yes     | Yes  |
| Log level            |        | Yes   | Yes | Yes     | Yes  |
| Feature flags        |        |       | Yes | Yes     | Yes  |
| Connection pool size |        |       | Yes | Yes     | Yes  |
| CORS origins         |        |       | Yes | Yes     | Yes  |

- Common settings go in `application.yml`
- Environment-specific overrides go in profile files
- Never put secrets in any yml file — use environment variables

---

## 11. @ConfigurationProperties

> **See [references/configuration-properties.md](references/configuration-properties.md) for detailed patterns including:**
> - Kotlin data class and Java record patterns
> - Environment variable binding and secret management
> - HikariCP connection pool configuration
> - Actuator configuration

---

## 12. JPA and Data Access

> **See [references/jpa-patterns.md](references/jpa-patterns.md) for detailed patterns including:**
> - N+1 problem prevention (fetch join, EntityGraph)
> - JPA entity conventions and design rules
> - Spring Data repository patterns

---

## 13. Anti-Patterns

### IoC and AOP

- Field injection with `@Autowired` — use constructor injection
- Storing mutable state in singleton beans — causes concurrency bugs
- Self-invocation expecting AOP/proxy behavior (`@Transactional`, `@Async`, `@Cacheable`)
- Heavy initialization in `@PostConstruct` — delays startup

### Transaction Management

- Calling external APIs inside `@Transactional` — holds DB locks
- Catching exceptions inside `@Transactional` — prevents rollback
- `@Transactional` on private methods — silently ignored
- Ignoring `@TransactionalEventListener` phase — side effects may execute before commit

### Event System

- Using `ApplicationEvent` for cross-service communication — use messaging

### Scheduling

- Using `@Scheduled(fixedRate)` for long-running tasks without overlap protection

### Configuration

- Hardcoding environment-specific values in `application.yml`
- Using `@Value` for complex or grouped configuration
- Putting secrets with default values in config files
- Duplicating common settings across profile files
- Missing validation on configuration properties
- Exposing all actuator endpoints without access control

### JPA and Data Access

- Returning JPA entities directly from controllers — use response DTOs
- N+1 queries — use fetch join or `@EntityGraph`
- Using `EnumType.ORDINAL` for enums — use `EnumType.STRING`
- Missing pagination on large result sets

## Additional References

### Migration Guides

- For Spring Framework migration (5.x → 6.x → 7.0), see [references/framework-migration.md](references/framework-migration.md)
- For Spring Boot migration (2.7 → 3.x → 4.0), see [references/boot-migration.md](references/boot-migration.md)

### Spring Boot Implementation Patterns

These references provide Spring Boot-specific implementation for cross-cutting concerns whose general principles are covered in dedicated framework-agnostic skills.

- **Caching** (Caffeine, Redis, `@Cacheable`): [references/caching.md](references/caching.md) — general principles in `caching` skill
- **Error Handling** (`@ControllerAdvice`, ErrorCode enum): [references/error-handling.md](references/error-handling.md) — general principles in `error-handling` skill
- **HTTP Client** (RestClient, Spring Retry, Resilience4j): [references/http-client.md](references/http-client.md) — general principles in `http-client` skill
- **Monitoring** (Actuator, Micrometer, distributed tracing): [references/monitoring.md](references/monitoring.md) — general principles in `monitoring` skill
- **Security** (SecurityFilterChain, Bean Validation): [references/security.md](references/security.md) — general principles in `security` skill
- **Troubleshooting** (startup failures, JVM OOM, HikariCP): [references/troubleshooting.md](references/troubleshooting.md) — general principles in `troubleshooting` skill

### Integration Patterns

- **Exposed ORM** integration: [references/exposed-integration.md](references/exposed-integration.md) — general Exposed rules in `exposed` skill
- **Kotlin interop** (JSpecify, `@Configuration`, JPA entities): [references/kotlin-interop.md](references/kotlin-interop.md) — general interop rules in `java-kotlin-interop` skill
