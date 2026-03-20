# AOP (Aspect-Oriented Programming) Patterns

## Aspect Definition

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

## Pointcut Expressions

| Expression                                      | Matches                                 |
| ----------------------------------------------- | --------------------------------------- |
| `execution(* com.example.service.*.*(..))`      | All methods in service package          |
| `@annotation(com.example.Loggable)`             | Methods annotated with @Loggable        |
| `@within(org.springframework.stereotype.Service)` | All methods in @Service classes       |
| `bean(userService)`                             | All methods on bean named userService   |

## Proxy Mechanism Rules

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

## AOP Rules

- Use `@Around` for timing, logging, retry — use `@Before`/`@After` for simpler cross-cutting
- Never put business logic in aspects — only cross-cutting concerns
- Self-invocation bypasses proxy — extract to separate bean when AOP is needed
- AOP adds runtime overhead — avoid on hot paths with millions of calls/sec
