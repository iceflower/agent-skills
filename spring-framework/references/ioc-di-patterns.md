# IoC and Dependency Injection Patterns

## Constructor Injection (Preferred)

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

## Injection Anti-Patterns

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

## Bean Scope

| Scope       | Lifecycle                        | Use Case                         |
| ----------- | -------------------------------- | -------------------------------- |
| `singleton` | One instance per ApplicationContext (default) | Stateless services, repositories |
| `prototype` | New instance per injection/request | Stateful, short-lived objects    |
| `request`   | One per HTTP request             | Request-scoped data              |
| `session`   | One per HTTP session             | Session-scoped data              |

- Default is `singleton` — do not store mutable state in singleton beans
- Injecting `prototype` into `singleton` does NOT create new instances — use `ObjectProvider<T>` or `@Lookup`

## Conditional Bean Registration

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
