# Calling Kotlin from Java

## Companion Object Members

```kotlin
class UserService {
    companion object {
        @JvmStatic
        fun defaultInstance(): UserService = UserService()

        @JvmField
        val MAX_USERS = 1000

        const val VERSION = "1.0"  // Inlined at compile time
    }
}
```

```java
// Java — clean access with @JvmStatic and @JvmField
UserService service = UserService.defaultInstance();  // Static call
int max = UserService.MAX_USERS;                      // Direct field
String version = UserService.VERSION;                 // Constant

// Without annotations: requires .Companion
UserService service = UserService.Companion.defaultInstance();
```

## Default Parameters

```kotlin
class Circle @JvmOverloads constructor(
    val centerX: Int,
    val centerY: Int,
    val radius: Double = 1.0
) {
    @JvmOverloads
    fun draw(color: String = "black", filled: Boolean = true) { ... }
}
```

```java
// Java — overloaded constructors and methods generated
new Circle(10, 20);         // radius defaults to 1.0
new Circle(10, 20, 5.0);   // explicit radius
circle.draw();              // both defaults
circle.draw("red");         // filled defaults to true
circle.draw("red", false);  // all explicit
```

## Checked Exceptions

```kotlin
// Kotlin — no checked exceptions by default
@Throws(IOException::class)  // Required for Java interop
fun readFile(path: String): String {
    return File(path).readText()
}
```

```java
// Java — can now catch the declared exception
try {
    String content = FileUtilKt.readFile("data.txt");
} catch (IOException e) {
    // Handle exception
}
```

## Value Classes (Kotlin 2.2+)

```kotlin
@JvmInline
@JvmExposeBoxed  // Expose boxed constructors and methods to Java
value class UserId(val value: Long)

@JvmInline
@JvmExposeBoxed
value class Email(val value: String)

// Function using value classes
@JvmExposeBoxed
fun findUser(id: UserId): User? = ...
```

```java
// Java — boxed variants available
UserId id = new UserId(42L);           // Constructor accessible
User user = UserServiceKt.findUser(id); // Boxed parameter accepted
```

- Without `@JvmExposeBoxed`: value classes are unboxed (mangled names, unusable from Java)
- Module-wide option: compile with `-Xjvm-expose-boxed`

## Package-Level Functions

```kotlin
// FileUtils.kt
@file:JvmName("FileUtils")  // Custom class name for Java
package com.example.util

fun readContent(path: String): String = ...
```

```java
// Java
String content = FileUtils.readContent("data.txt");
// Without @JvmName: FileUtilsKt.readContent(...)
```

## Property Access

```kotlin
class User(
    val name: String,           // Java: getName()
    var email: String,          // Java: getEmail(), setEmail()
    @get:JvmName("isVerified")
    val verified: Boolean       // Java: isVerified()
)
```

## Annotation Summary

| Annotation         | Purpose                                         | When to Use                     |
| ------------------ | ----------------------------------------------- | ------------------------------- |
| `@JvmStatic`       | Generate static method                          | Companion object functions      |
| `@JvmField`        | Expose as public field (no getter/setter)        | Companion object properties     |
| `@JvmOverloads`    | Generate overloads for default parameters        | Functions called from Java      |
| `@JvmName`         | Specify JVM method/class name                    | Name clashes, file-level funcs  |
| `@Throws`          | Declare checked exceptions                       | Functions throwing exceptions   |
| `@JvmExposeBoxed`  | Expose boxed value class for Java                | Value classes used from Java    |
| `@JvmWildcard`     | Force wildcard in generated Java signature       | Generic variance control        |
| `@JvmSuppressWildcards` | Suppress wildcard in generated Java signature | Generic variance control   |