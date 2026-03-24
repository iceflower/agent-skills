---
name: java-kotlin-interop
description: >-
  Java-Kotlin interoperability guide covering platform types, null safety with JSpecify,
  JVM annotations (@JvmStatic, @JvmOverloads, @JvmExposeBoxed, @Throws), collection interop,
  coroutine-Java bridging, SAM conversion, and build configuration for mixed projects.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# Java-Kotlin Interoperability Rules

## 1. Platform Types and Null Safety

### The Core Problem

Java types without nullability annotations are treated as **platform types** (`T!`) in Kotlin — neither nullable nor non-nullable. This bypasses Kotlin's null-safety guarantees.

```kotlin
// Java method: String getName() — no annotation
val name = javaObject.name  // Type: String! (platform type)
name.length                  // Compiles, but may throw NPE at runtime
```

### Solution: Nullability Annotations

```java
// Java — annotate all public API boundaries
import org.jspecify.annotations.NullMarked;
import org.jspecify.annotations.Nullable;

@NullMarked  // All types non-null by default in this class
public class UserService {
    public User findById(long id) { ... }              // Non-null return
    public @Nullable User findByEmail(String email) { ... }  // Nullable return
}
```

```kotlin
// Kotlin — now properly typed
val user: User = userService.findById(1L)          // Non-null
val maybeUser: User? = userService.findByEmail(email)  // Nullable
```

### Annotation Priority (Kotlin Recognition Order)

| Priority | Annotation Source | Package                            |
| -------- | ----------------- | ---------------------------------- |
| 1        | JSpecify          | `org.jspecify.annotations`         |
| 2        | JetBrains         | `org.jetbrains.annotations`        |
| 3        | Android           | `androidx.annotation`              |
| 4        | JSR-305           | `javax.annotation`                 |
| 5        | FindBugs          | `edu.umd.cs.findbugs.annotations`  |
| 6        | Eclipse           | `org.eclipse.jdt.annotation`       |
| 7        | Lombok            | `lombok`                           |

### Framework JSpecify Integration

- For Spring Framework 7 / Boot 4 JSpecify integration details, see `spring-framework` skill — [references/kotlin-interop.md](../spring-framework/references/kotlin-interop.md)

### Rules

- **Java side**: Always annotate public APIs with `@NullMarked` (class/package level) and `@Nullable` (specific fields/returns)
- **Kotlin side**: Never use `!!` on platform types — assign to explicitly typed variable first
- **Mixed project**: Use JSpecify over JSR-305 for new code (better Kotlin integration)

---

## 2. Calling Kotlin from Java

> **See [references/calling-kotlin-from-java.md](references/calling-kotlin-from-java.md) for detailed patterns including:**
>
> - Companion object members (@JvmStatic, @JvmField)
> - Default parameters (@JvmOverloads)
> - Checked exceptions (@Throws)
> - Value classes (@JvmExposeBoxed)
> - Package-level functions (@JvmName)

---

## 3. Collection Interop

### Read-Only vs Mutable Mapping

| Java Type              | Kotlin Read-Only       | Kotlin Mutable             |
| ---------------------- | ---------------------- | -------------------------- |
| `java.util.List`       | `kotlin.List`          | `kotlin.MutableList`       |
| `java.util.Set`        | `kotlin.Set`           | `kotlin.MutableSet`        |
| `java.util.Map`        | `kotlin.Map`           | `kotlin.MutableMap`        |
| `java.util.Collection` | `kotlin.Collection`    | `kotlin.MutableCollection` |

### Common Pitfalls

```kotlin
// Pitfall 1: Java can mutate Kotlin's read-only collection
fun getNames(): List<String> = listOf("Alice", "Bob")

// Java code can cast and mutate:
// List<String> names = getNames();
// ((java.util.ArrayList<String>) names).add("Charlie"); // UnsupportedOperationException

// Pitfall 2: Platform type collections — mutability unknown
fun processJavaList(list: MutableList<String>) {
    list.add("item")  // OK — explicitly mutable
}
fun processJavaList(list: List<String>) {
    // Cannot add — Kotlin treats as read-only
}
```

### Collection Interop Rules

- Return `List` (read-only) from Kotlin APIs — Java consumers cannot mutate accidentally
- Accept `MutableList` in Kotlin parameters when Java caller needs to mutate
- Defensive copy when receiving collections from Java: `list.toList()` or `list.toMutableList()`
- Use `List.copyOf()` in Java when passing to Kotlin to ensure immutability

---

## 4. Generics and Variance

### Declaration-Site Variance → Use-Site Wildcards

```kotlin
// Kotlin: declaration-site variance
class Box<out T>(val value: T)  // Covariant
class Consumer<in T> { fun consume(item: T) {} }  // Contravariant

// Generated Java:
// Box<? extends T>   for out
// Consumer<? super T> for in
```

### Controlling Wildcard Generation

```kotlin
// Force wildcard
fun boxDerived(value: Derived): Box<@JvmWildcard Derived> = Box(value)
// Java: Box<? extends Derived>

// Suppress wildcard
fun unboxBase(box: Box<@JvmSuppressWildcards Base>): Base = box.value
// Java: Box<Base> (no wildcard)
```

### Reified Type Parameters

```kotlin
// Kotlin — inline + reified preserves type at runtime
inline fun <reified T> parseJson(json: String): T {
    return objectMapper.readValue(json, T::class.java)
}

// Cannot be called from Java — reified is a Kotlin-only feature
// Java alternative: pass Class<T> explicitly
fun <T> parseJson(json: String, type: Class<T>): T {
    return objectMapper.readValue(json, type)
}
```

### Generics Rules

- Provide non-reified overload with `Class<T>` parameter for Java consumers
- Use `@JvmWildcard` / `@JvmSuppressWildcards` to control Java signature when needed
- Java raw types become `Any!` in Kotlin — avoid raw types in interop boundaries

---

## 5. Coroutines and Java Interop

### Exposing Suspend Functions to Java

```kotlin
// Kotlin suspend function
suspend fun fetchUser(id: Long): User { ... }

// Java cannot call suspend functions directly
// Solution 1: Provide a CompletableFuture wrapper
fun fetchUserAsync(id: Long): CompletableFuture<User> =
    CoroutineScope(Dispatchers.IO).future { fetchUser(id) }

// Solution 2: Provide a blocking wrapper (for simple cases)
@JvmStatic
fun fetchUserBlocking(id: Long): User = runBlocking { fetchUser(id) }
```

### Flow to Java

```kotlin
// Kotlin Flow
fun userStream(): Flow<User> = ...

// Java-friendly wrapper using Reactor or RxJava
fun userFlux(): Flux<User> = userStream().asFlux()

// Or using Publisher
fun userPublisher(): Publisher<User> = userStream().asPublisher()
```

### Coroutines Interop Rules

- Never expose raw `suspend fun` as public API consumed by Java — wrap in `CompletableFuture`
- Use `kotlinx-coroutines-jdk8` for `future {}` builder
- Use `kotlinx-coroutines-reactor` for `Flow.asFlux()` / `Flow.asPublisher()` conversion
- `runBlocking` wrappers are acceptable for CLI tools but NOT for server request handlers

---

## 6. SAM Conversion

### Java SAM Interface in Kotlin

```kotlin
// Java interface
// public interface Predicate<T> { boolean test(T t); }

// Kotlin — automatic SAM conversion
val isAdult = Predicate<User> { it.age >= 18 }
users.stream().filter { it.age >= 18 }
```

### Kotlin Fun Interface in Java

```kotlin
// Kotlin — fun interface enables SAM conversion
fun interface Validator<T> {
    fun validate(value: T): Boolean
}
```

```java
// Java — lambda works with fun interface
Validator<String> notEmpty = s -> !s.isEmpty();
```

### SAM Conversion Rules

- Use `fun interface` in Kotlin when Java consumers should use lambdas
- Regular Kotlin interfaces do NOT support SAM conversion from Java — must use `fun interface`
- If a Kotlin interface has multiple abstract methods, Java must use anonymous class

---

## 7. Keyword and Name Conflicts

### Kotlin Keywords as Java Identifiers

```kotlin
// Java method named with Kotlin keyword — use backticks
javaObject.`is`(value)
javaObject.`when`
javaObject.`object`
javaObject.`in`(collection)
```

### `internal` Visibility from Java

```kotlin
internal fun processInternal() { ... }

// Java can access (public in bytecode) but name is mangled:
// processInternal$module_name()
// This is intentional — discourages accidental use from Java
```

### Name Conflict Rules

- Avoid using Kotlin keywords (`is`, `when`, `object`, `in`, `fun`, `val`, `var`) as Java identifiers in interop boundaries
- `internal` Kotlin members are accessible from Java but name-mangled — do not depend on them from Java
- Use `@JvmName` to provide clean Java-friendly names when needed

---

## 8. Framework-Specific Interop Patterns

> **See `spring-framework` skill — [references/kotlin-interop.md](../spring-framework/references/kotlin-interop.md) for:**
>
> - Spring `@Configuration` with Kotlin (allopen plugin)
> - JPA entities in mixed Java/Kotlin projects
> - Extension function usage from Java in Spring context

---

## 9. Build Configuration for Mixed Projects

### Gradle (Kotlin DSL)

```kotlin
// build.gradle.kts
plugins {
    java
    kotlin("jvm") version "2.3.0"
    // Add framework-specific plugins as needed (e.g., spring, jpa)
}

// Source directories
sourceSets {
    main {
        java.srcDirs("src/main/java")
        kotlin.srcDirs("src/main/kotlin")
    }
}

// Ensure Java and Kotlin compile together
tasks.withType<JavaCompile> {
    sourceCompatibility = "21"
    targetCompatibility = "21"
}

kotlin {
    jvmToolchain(21)
}
```

### Compilation Order

- Kotlin compiler runs first — can see Java sources
- Java compiler runs second — can see Kotlin compiled classes
- **Circular dependencies between Java and Kotlin files are supported** (both compilers handle cross-references)

---

## 10. Migration Strategy

### Gradual Java → Kotlin Migration

| Step | Action                                    | Risk Level |
| ---- | ----------------------------------------- | ---------- |
| 1    | Add Kotlin plugin to build                | Low        |
| 2    | Write new test code in Kotlin             | Low        |
| 3    | Write new utility/extension classes       | Low        |
| 4    | Convert data classes (DTOs, responses)    | Low        |
| 5    | Convert service layer classes             | Medium     |
| 6    | Convert controller layer                  | Medium     |
| 7    | Convert entity classes (requires plugins) | Medium     |

### Migration Rules

- Convert bottom-up (least-depended-on classes first)
- Add nullability annotations to Java code before converting callers to Kotlin
- Use IntelliJ's "Convert Java File to Kotlin" as starting point, then refine
- Keep test coverage high — run tests after each conversion
- Do not convert and refactor simultaneously — convert first, then refactor

---

## 11. Anti-Patterns

- Using `!!` on platform types — assign to typed variable or add Java annotation instead
- Exposing `suspend fun` directly to Java consumers — wrap in `CompletableFuture`
- Exposing `Flow` to Java — wrap in `Flux` or `Publisher`
- Using regular Kotlin interfaces for Java SAM consumption — use `fun interface`
- Relying on Kotlin `internal` visibility for encapsulation from Java — it is `public` in bytecode
- Mixing `javax` and `jakarta` annotations in the same project
- Not adding `@JvmStatic` / `@JvmOverloads` / `@Throws` on Kotlin code called from Java
- Using `data class` for ORM entities without understanding `equals`/`hashCode` implications
- Not using `@JvmExposeBoxed` for value classes consumed from Java
- Ignoring platform types — always determine proper nullability at interop boundaries
