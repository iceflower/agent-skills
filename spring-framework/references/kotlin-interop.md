# Spring Boot Kotlin Interoperability Patterns

Java-Kotlin 상호운용의 일반 규칙(플랫폼 타입, null 안전성, 컬렉션, 코루틴 브리징, SAM 변환)은 `java-kotlin-interop` 스킬 참조.

이 문서는 Spring Framework/Boot에서의 Kotlin 상호운용 패턴만 다룹니다.

## 1. Spring Framework 7 / Spring Boot 4: JSpecify Integration

Spring Framework 7+ uses JSpecify annotations throughout the entire codebase with `@NullMarked` on all packages.

```kotlin
// Before (Spring 6 / Boot 3): platform types everywhere
val user = userRepository.findById(id)  // User! — platform type
user.name                                // May NPE

// After (Spring 7 / Boot 4 + Kotlin 2.1+): proper null safety
val user = userRepository.findById(id)  // User — non-null
val maybe = userRepository.findByEmail(email)  // User? — nullable
maybe?.name                              // Compiler-enforced safety
```

- Kotlin 2.2+ automatically translates JSpecify annotations to Kotlin nullability
- Platform types (`T!`) are eliminated for Spring APIs
- Generic types and arrays also carry nullability: `List<String>` not `List<String!>!`
- **Spring Boot 4**: No extra work needed — Spring APIs are already fully annotated

## 2. Spring-Specific Interop Patterns

### Kotlin Extensions Used from Java

```kotlin
// Kotlin extension function
fun User.toResponse(): UserResponse = UserResponse(id, name, email)

// Java — called as static method on the generated Kt class
UserResponse response = UserMappingsKt.toResponse(user);
```

- Extension functions compile to static methods with receiver as first parameter
- Use `@file:JvmName("UserMappings")` for cleaner Java access

### Spring Configuration in Mixed Projects

```kotlin
// Kotlin @Configuration is open by default (allopen plugin)
@Configuration
class AppConfig {
    @Bean
    fun userService(repo: UserRepository): UserService = UserService(repo)
}

// Java @Configuration must use CGLIB proxying
@Configuration
public class JavaConfig {
    @Bean
    public PaymentService paymentService() { return new PaymentService(); }
}
```

- Kotlin's `allopen` plugin makes `@Configuration`, `@Service`, etc. automatically open
- Java classes must be non-final for CGLIB proxying (or use `proxyBeanMethods = false`)

### JPA Entities in Mixed Projects

```kotlin
// Kotlin entity — requires allopen + noarg plugins
@Entity
class User(
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    val id: Long = 0,
    var name: String,
    var email: String
)
```

```java
// Java entity — works without plugins
@Entity
public class Order {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    // JPA requires no-arg constructor — Java generates implicitly with default visibility
}
```

- Kotlin JPA entities need `kotlin-jpa` (noarg) plugin for no-arg constructor generation
- Kotlin JPA entities need `kotlin-allopen` plugin to make classes non-final
