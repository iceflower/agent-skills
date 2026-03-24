# Scope Functions and Kotlin DSL — Detailed Examples

## Scope Function Anti-Patterns

### Nested Scope Functions (avoid)

```kotlin
// Bad: deeply nested scope functions reduce readability
user?.let { u ->
    u.address?.let { addr ->
        addr.city?.let { city ->
            println(city)
        }
    }
}

// Good: use safe calls or early return
val city = user?.address?.city ?: return
println(city)
```

### Side-Effect-Only let Without Null Check (avoid)

```kotlin
// Bad: let without null check adds no value
val result = computeValue()
result.let {
    println(it)  // just use result directly
}

// Good: use let only for null-conditional or scoping
computeValue()?.let { println(it) }
```

### Overlong apply Blocks (avoid)

```kotlin
// Bad: apply with business logic beyond initialization
val order = Order().apply {
    id = generateId()
    status = OrderStatus.PENDING
    validate()                      // side effect, not config
    repository.save(this)           // external call, not config
    notificationService.send(this)  // unrelated responsibility
}

// Good: apply only for initialization, then call methods separately
val order = Order().apply {
    id = generateId()
    status = OrderStatus.PENDING
}
order.validate()
repository.save(order)
notificationService.send(order)
```

## Kotlin DSL — Extended Examples

### Type-Safe Builder with @DslMarker

```kotlin
@DslMarker
annotation class HtmlDsl

@HtmlDsl
class HtmlBuilder {
    private val elements = mutableListOf<String>()

    fun head(block: HeadBuilder.() -> Unit) {
        elements += HeadBuilder().apply(block).build()
    }

    fun body(block: BodyBuilder.() -> Unit) {
        elements += BodyBuilder().apply(block).build()
    }

    fun build(): String = "<html>${elements.joinToString("")}</html>"
}

@HtmlDsl
class HeadBuilder {
    private var title: String = ""

    fun title(value: String) { title = value }

    fun build(): String = "<head><title>$title</title></head>"
}

@HtmlDsl
class BodyBuilder {
    private val elements = mutableListOf<String>()

    fun h1(text: String) { elements += "<h1>$text</h1>" }
    fun p(text: String) { elements += "<p>$text</p>" }

    fun build(): String = "<body>${elements.joinToString("")}</body>"
}

fun html(block: HtmlBuilder.() -> Unit): String =
    HtmlBuilder().apply(block).build()

// Usage
val page = html {
    head { title("My Page") }
    body {
        h1("Hello")
        p("Welcome to Kotlin DSL")
    }
}
```

### Configuration DSL Pattern

```kotlin
@DslMarker
annotation class ConfigDsl

@ConfigDsl
class ServerConfig {
    var host: String = "localhost"
    var port: Int = 8080
    private var _database: DatabaseConfig? = null

    val database: DatabaseConfig
        get() = _database ?: error("Database not configured")

    fun database(block: DatabaseConfig.() -> Unit) {
        _database = DatabaseConfig().apply(block)
    }
}

@ConfigDsl
class DatabaseConfig {
    var url: String = ""
    var maxPoolSize: Int = 10
    var connectionTimeout: Long = 5000
}

fun serverConfig(block: ServerConfig.() -> Unit): ServerConfig =
    ServerConfig().apply(block)

// Usage
val config = serverConfig {
    host = "0.0.0.0"
    port = 9090
    database {
        url = "jdbc:postgresql://localhost/mydb"
        maxPoolSize = 20
    }
}
```
