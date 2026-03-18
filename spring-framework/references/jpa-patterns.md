# JPA and Data Access Patterns

## N+1 Problem Prevention

```kotlin
// Bad: N+1 queries
val users = userRepository.findAll()
users.forEach { user ->
    val orders = orderRepository.findByUserId(user.id) // N additional queries
}

// Good: Fetch join
@Query("SELECT u FROM User u JOIN FETCH u.orders")
fun findAllWithOrders(): List<User>

// Good: EntityGraph
@EntityGraph(attributePaths = ["orders"])
fun findAll(): List<User>
```

## JPA Entity Conventions

```kotlin
@Entity
@Table(name = "users")
class User(
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    val id: Long = 0,

    @Column(nullable = false, length = 100)
    var name: String,

    @Column(nullable = false, unique = true)
    var email: String,

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    var status: UserStatus = UserStatus.ACTIVE,

    @Column(nullable = false, updatable = false)
    val createdAt: Instant = Instant.now(),

    @Column(nullable = false)
    var updatedAt: Instant = Instant.now()
) {
    fun deactivate() {
        status = UserStatus.INACTIVE
        updatedAt = Instant.now()
    }
}
```

## Entity Design Rules

- Use `val` for immutable fields (id, createdAt), `var` for mutable fields
- Always use `EnumType.STRING` for enums (not `ORDINAL`)
- Include `createdAt` and `updatedAt` audit columns
- Put business logic in entity methods, not in service layer
- Avoid bidirectional relationships unless necessary — prefer unidirectional

## Spring Data Repository Patterns

```kotlin
interface UserRepository : JpaRepository<User, Long> {
    fun findByEmail(email: String): User?
    fun findByStatusAndCreatedAtAfter(status: UserStatus, after: Instant): List<User>
    fun existsByEmail(email: String): Boolean

    @Query("SELECT u FROM User u WHERE u.name LIKE CONCAT(:keyword, '%')")
    fun searchByNamePrefix(@Param("keyword") keyword: String, pageable: Pageable): Page<User>
}

// Extension for throwing on not found
fun UserRepository.findByIdOrThrow(id: Long): User =
    findByIdOrNull(id) ?: throw EntityNotFoundException("User", id)
```

## Repository Rules

- Use Spring Data derived query methods for simple queries
- Use `@Query` with JPQL for complex queries
- Use native queries (`nativeQuery = true`) only when JPQL is insufficient
- Always use `Pageable` for list queries that may return large result sets