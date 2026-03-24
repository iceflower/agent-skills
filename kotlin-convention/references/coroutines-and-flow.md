# Coroutines and Flow — Detailed Examples

## Coroutine Exception Handling

### SupervisorJob with CoroutineExceptionHandler

```kotlin
class OrderProcessingService(
    private val orderRepository: OrderRepository,
    private val notificationService: NotificationService,
) {
    private val exceptionHandler = CoroutineExceptionHandler { _, throwable ->
        logger.error("Unhandled coroutine exception", throwable)
    }

    private val scope = CoroutineScope(
        SupervisorJob() + Dispatchers.Default + exceptionHandler
    )

    fun processOrdersAsync(orders: List<Order>) {
        orders.forEach { order ->
            scope.launch {
                // Each order is independent; one failure does not cancel others
                orderRepository.save(order)
                notificationService.sendConfirmation(order)
            }
        }
    }
}
```

### coroutineScope vs supervisorScope

```kotlin
// coroutineScope: ALL children cancel if ANY child fails
suspend fun fetchAllOrFail(ids: List<Long>): List<User> = coroutineScope {
    ids.map { id ->
        async { userService.getById(id) }  // one failure → all cancelled
    }.awaitAll()
}

// supervisorScope: other children continue even if one fails
suspend fun fetchAllBestEffort(ids: List<Long>): List<User?> = supervisorScope {
    ids.map { id ->
        async {
            runCatching { userService.getById(id) }.getOrNull()
        }
    }.awaitAll()
}
```

## Flow Operator Patterns

### Chaining Operators

```kotlin
fun observeActiveUsers(): Flow<List<UserSummary>> =
    userRepository.observeAll()
        .map { users -> users.filter { it.isActive } }
        .map { users -> users.map { it.toSummary() } }
        .distinctUntilChanged()
        .catch { e ->
            logger.error("Error observing users", e)
            emit(emptyList())
        }
        .flowOn(Dispatchers.IO)
```

### Combining Flows

```kotlin
fun observeDashboard(userId: Long): Flow<Dashboard> =
    combine(
        profileRepository.observe(userId),
        orderRepository.observeRecent(userId),
        notificationRepository.observeUnread(userId),
    ) { profile, orders, notifications ->
        Dashboard(profile, orders, notifications)
    }
```

### Flow Testing

```kotlin
@Test
fun `should emit filtered active users`() = runTest {
    // Given
    val users = listOf(
        User(1, "Alice", isActive = true),
        User(2, "Bob", isActive = false),
    )
    val fakeRepo = FakeUserRepository(flowOf(users))
    val sut = UserObserver(fakeRepo)

    // When & Then
    sut.observeActiveUsers().test {
        val result = awaitItem()
        assertThat(result).hasSize(1)
        assertThat(result.first().name).isEqualTo("Alice")
        awaitComplete()
    }
}

// Using Turbine for Flow testing
@Test
fun `should handle errors gracefully`() = runTest {
    val errorFlow = flow<List<User>> { throw IOException("Network error") }
    val fakeRepo = FakeUserRepository(errorFlow)
    val sut = UserObserver(fakeRepo)

    sut.observeActiveUsers().test {
        val result = awaitItem()
        assertThat(result).isEmpty()  // catch emits emptyList()
        awaitComplete()
    }
}
```

## StateFlow vs SharedFlow — Extended Examples

### StateFlow for UI State

```kotlin
class UserViewModel(
    private val userRepository: UserRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow<UiState>(UiState.Loading)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    fun loadUser(id: Long) {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            runCatching { userRepository.getById(id) }
                .onSuccess { _uiState.value = UiState.Success(it) }
                .onFailure { _uiState.value = UiState.Error(it.message) }
        }
    }
}
```

### SharedFlow for Events

```kotlin
class EventBus {
    private val _events = MutableSharedFlow<AppEvent>(
        replay = 0,
        extraBufferCapacity = 64,
        onBufferOverflow = BufferOverflow.DROP_OLDEST,
    )
    val events: SharedFlow<AppEvent> = _events.asSharedFlow()

    suspend fun emit(event: AppEvent) {
        _events.emit(event)
    }
}
```
