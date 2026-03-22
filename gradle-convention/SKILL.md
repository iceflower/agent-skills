---
name: gradle-convention
description: >-
  Gradle build conventions for Kotlin/JVM multi-module projects.
  Covers multi-module project structure, convention plugins, buildSrc setup,
  dependency management with version catalogs, Gradle wrapper configuration,
  build cache configuration, task optimization, and plugin publishing.
  Use when writing or reviewing build.gradle.kts, settings.gradle.kts, version
  catalog files, or configuring convention plugins for shared build logic.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
compatibility:
  - OpenCode
  - Claude Code
  - Codex
  - Antigravity
---

# Gradle Convention Rules

## 1. Multi-Module Project Structure

### Recommended Layout

```text
project-root/
├── settings.gradle.kts
├── build.gradle.kts              # Root: shared config
├── buildSrc/                     # Convention plugins
│   ├── build.gradle.kts
│   └── src/main/kotlin/
│       └── kotlin-conventions.gradle.kts
├── gradle/
│   └── libs.versions.toml        # Version catalog
└── modules/
    ├── app/                      # Application entry point
    │   ├── build.gradle.kts
    │   └── src/
    ├── domain/                   # Domain logic
    │   ├── build.gradle.kts
    │   └── src/
    └── infrastructure/           # External integrations
        ├── build.gradle.kts
        └── src/
```

### Module Dependency Direction

```text
app → domain ← infrastructure
```

- `domain`: Pure business logic, no framework dependencies
- `app`: Application entry point, routing, configuration
- `infrastructure`: Database, external APIs, messaging
- `domain` should never depend on `app` or `infrastructure`

---

## 2. Version Catalog

### libs.versions.toml

```toml
[versions]
kotlin = "2.3.10"
kotlinx-coroutines = "1.10.2"
kotlinx-serialization = "1.8.1"
ktor = "3.1.2"
exposed = "0.61.0"
kotest = "5.9.0"
mockk = "1.13.13"

[libraries]
kotlinx-coroutines-core = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-core", version.ref = "kotlinx-coroutines" }
kotlinx-serialization-json = { module = "org.jetbrains.kotlinx:kotlinx-serialization-json", version.ref = "kotlinx-serialization" }
ktor-server-core = { module = "io.ktor:ktor-server-core", version.ref = "ktor" }
ktor-server-netty = { module = "io.ktor:ktor-server-netty", version.ref = "ktor" }
exposed-core = { module = "org.jetbrains.exposed:exposed-core", version.ref = "exposed" }
exposed-jdbc = { module = "org.jetbrains.exposed:exposed-jdbc", version.ref = "exposed" }
kotest-runner = { module = "io.kotest:kotest-runner-junit5", version.ref = "kotest" }
mockk = { module = "io.mockk:mockk", version.ref = "mockk" }

[bundles]
kotest = ["kotest-runner", "mockk"]

[plugins]
kotlin-jvm = { id = "org.jetbrains.kotlin.jvm", version.ref = "kotlin" }
kotlin-serialization = { id = "org.jetbrains.kotlin.plugin.serialization", version.ref = "kotlin" }
```

### Usage in build.gradle.kts

```kotlin
dependencies {
    implementation(libs.kotlinx.coroutines.core)
    implementation(libs.kotlinx.serialization.json)
    testImplementation(libs.bundles.kotest)
}
```

### Version Catalog Rules

- All dependency versions must be defined in `libs.versions.toml`
- Never hardcode version strings in `build.gradle.kts`
- Use `bundles` to group related test/utility dependencies
- Keep versions up to date — check for updates regularly

---

## 3. Dependency Declarations

### Configuration Types

| Configuration | Purpose | Transitive |
| --- | --- | --- |
| `implementation` | Internal dependency | No |
| `api` | Exposed to consumers | Yes |
| `compileOnly` | Compile-time only (annotations, etc.) | No |
| `runtimeOnly` | Runtime only (JDBC drivers, etc.) | No |
| `testImplementation` | Test dependencies | No |

### Rules

```kotlin
dependencies {
    // Use implementation by default
    implementation(libs.ktor.server.core)

    // Use api only in library modules when the type is part of the public API
    api(libs.some.shared.model)

    // Use compileOnly for annotation processors
    compileOnly(libs.some.annotation.processor)

    // Use runtimeOnly for runtime-only dependencies
    runtimeOnly(libs.postgresql)

    // Test dependencies
    testImplementation(libs.bundles.kotest)
}
```

- Default to `implementation` — only use `api` when the dependency type appears in public signatures
- Use `runtimeOnly` for JDBC drivers, logging backends
- Use `compileOnly` for compile-time annotations

---

## 4. Convention Plugins (buildSrc)

### Shared Configuration

```kotlin
// buildSrc/src/main/kotlin/kotlin-conventions.gradle.kts
plugins {
    kotlin("jvm")
}

group = "com.example"

kotlin {
    jvmToolchain(21)
}

tasks.withType<Test> {
    useJUnitPlatform()
}
```

### Application Module Convention

```kotlin
// buildSrc/src/main/kotlin/app-conventions.gradle.kts
plugins {
    id("kotlin-conventions")
    application
}

// Configure the main class for the application plugin
application {
    mainClass.set("com.example.MainKt")
}
```

### Convention Plugin Rules

- Extract common build logic into `buildSrc` convention plugins
- Apply convention plugins in module `build.gradle.kts` instead of repeating config
- Keep convention plugins focused — one per concern (kotlin, application, serialization)

---

## 5. Build Optimization

### gradle.properties

```properties
# Parallel execution
org.gradle.parallel=true

# Build cache
org.gradle.caching=true

# Daemon (keep JVM alive between builds)
org.gradle.daemon=true

# JVM memory for Gradle daemon
org.gradle.jvmargs=-Xmx2g -XX:+UseParallelGC

# Kotlin incremental compilation
kotlin.incremental=true
```

### CI-Specific Settings

```properties
# In CI: disable daemon (short-lived environments)
org.gradle.daemon=false
```

---

## 6. Task Conventions

### Custom Task Naming

- Use camelCase for task names
- Prefix with action verb: `generate`, `check`, `publish`
- Group related tasks with `group` property

### Common Tasks

| Task | Purpose |
| --- | --- |
| `./gradlew build` | Compile + test + assemble |
| `./gradlew jar` | Build JAR artifact |
| `./gradlew test` | Run all tests |
| `./gradlew dependencies` | Show dependency tree |
| `./gradlew dependencyUpdates` | Check for dependency updates |

---

## 7. Framework-Specific Build Patterns

Examples in this skill use framework-agnostic Kotlin/JVM libraries. For Spring Boot projects, see:

- **Spring Boot plugins, starters, convention plugins**: `spring-framework` skill
- **Spring Boot + Kotlin build setup** (allopen, noarg, JPA plugins): `spring-framework` skill — [references/kotlin-interop.md](../spring-framework/references/kotlin-interop.md)

---

## 8. Anti-Patterns

- Hardcoding dependency versions in `build.gradle.kts`
- Using `compile` (deprecated) instead of `implementation`
- Applying plugins in `allprojects`/`subprojects` blocks (use convention plugins)
- Copying build logic across module `build.gradle.kts` files
- Using `buildscript` block when plugin DSL is available
- Skipping `gradle wrapper` — always commit the wrapper
