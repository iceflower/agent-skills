# SOLID Principles — Detailed Examples

## SRP Practical Application

```kotlin
// Bad: report generation + formatting + delivery in one class
class ReportService(
    private val repository: OrderRepository,
    private val templateEngine: TemplateEngine,
    private val emailSender: EmailSender
) {
    fun generateMonthlyReport(month: YearMonth): Report { ... }
    fun renderAsHtml(report: Report): String { ... }
    fun sendToStakeholders(html: String) { ... }
}

// Good: each responsibility separated
class ReportGenerator(private val repository: OrderRepository) {
    fun generate(month: YearMonth): Report { ... }
}

class ReportRenderer(private val templateEngine: TemplateEngine) {
    fun renderAsHtml(report: Report): String { ... }
}

class ReportDelivery(private val emailSender: EmailSender) {
    fun sendToStakeholders(html: String) { ... }
}
```

## OCP Strategy Pattern Application

```kotlin
// Closed for modification: DiscountCalculator never changes
// Open for extension: add new DiscountPolicy implementations
fun interface DiscountPolicy {
    fun calculate(order: Order): Money
}

class PercentageDiscount(private val rate: Double) : DiscountPolicy {
    override fun calculate(order: Order): Money =
        order.totalAmount * rate
}

class FixedAmountDiscount(private val amount: Money) : DiscountPolicy {
    override fun calculate(order: Order): Money = amount
}

// New discount type added without modifying existing code
class TieredDiscount(private val tiers: List<Tier>) : DiscountPolicy {
    override fun calculate(order: Order): Money =
        tiers.firstOrNull { it.matches(order) }?.discount ?: Money.ZERO
}

class DiscountCalculator(private val policy: DiscountPolicy) {
    fun applyDiscount(order: Order): Order =
        order.withDiscount(policy.calculate(order))
}
```

## OCP Template Method Application

```kotlin
// Base class defines the algorithm skeleton
abstract class DataExporter {
    fun export(data: List<Record>): ByteArray {
        val filtered = filterRecords(data)
        val formatted = formatRecords(filtered)
        return encode(formatted)
    }

    protected open fun filterRecords(data: List<Record>): List<Record> = data
    protected abstract fun formatRecords(data: List<Record>): String
    protected abstract fun encode(content: String): ByteArray
}

// Extension: new format without modifying base class
class CsvExporter : DataExporter() {
    override fun formatRecords(data: List<Record>): String = ...
    override fun encode(content: String): ByteArray = content.toByteArray()
}
```

## OCP Sealed Class for Bounded Extension

```kotlin
// When extension should be controlled, use sealed types
sealed interface PaymentMethod {
    data class CreditCard(val number: String, val expiry: String) : PaymentMethod
    data class BankTransfer(val accountNumber: String) : PaymentMethod
    data object Cash : PaymentMethod
}

// Exhaustive when — adding new subtype forces handling everywhere
fun process(method: PaymentMethod): PaymentResult = when (method) {
    is PaymentMethod.CreditCard -> processCreditCard(method)
    is PaymentMethod.BankTransfer -> processBankTransfer(method)
    is PaymentMethod.Cash -> processCash()
}
```

## LSP Violation Examples

```kotlin
// Classic violation: Square is NOT a behavioral subtype of Rectangle
open class Rectangle(open var width: Int, open var height: Int) {
    open fun area(): Int = width * height
}

class Square(side: Int) : Rectangle(side, side) {
    override var width: Int = side
        set(value) { field = value; height = value }  // Breaks independent width/height
    override var height: Int = side
        set(value) { field = value; width = value }
}

// Client code breaks: expects width and height to be independent
fun doubleWidth(rect: Rectangle) {
    rect.width *= 2
    check(rect.area() == rect.width * rect.height)  // Fails for Square
}
```

```kotlin
// Fix: model as separate types with shared interface
interface Shape {
    fun area(): Int
}

data class Rectangle(val width: Int, val height: Int) : Shape {
    override fun area(): Int = width * height
}

data class Square(val side: Int) : Shape {
    override fun area(): Int = side * side
}
```

## LSP Design by Contract

```kotlin
interface Collection<E> {
    /**
     * Contract:
     * - Precondition: element is not null
     * - Postcondition: contains(element) returns true after add
     * - Postcondition: size increases by 1
     */
    fun add(element: E): Boolean
}

// Violation: ReadOnlyCollection breaks postcondition by throwing
class ReadOnlyCollection<E> : Collection<E> {
    override fun add(element: E): Boolean =
        throw UnsupportedOperationException()  // LSP violation
}
```

## ISP Violation and Fix

```kotlin
// Bad: fat interface forces all implementors to handle irrelevant methods
interface UserService {
    fun findById(id: Long): User
    fun findAll(pageable: Pageable): Page<User>
    fun create(request: CreateUserRequest): User
    fun update(id: Long, request: UpdateUserRequest): User
    fun delete(id: Long)
    fun exportToCsv(): ByteArray
    fun importFromCsv(data: ByteArray)
    fun sendVerificationEmail(userId: Long)
}

// Good: segregated by client needs
interface UserReader {
    fun findById(id: Long): User
    fun findAll(pageable: Pageable): Page<User>
}

interface UserWriter {
    fun create(request: CreateUserRequest): User
    fun update(id: Long, request: UpdateUserRequest): User
    fun delete(id: Long)
}

interface UserDataTransfer {
    fun exportToCsv(): ByteArray
    fun importFromCsv(data: ByteArray)
}

// A class can implement multiple role interfaces
class UserServiceImpl(
    private val repository: UserRepository,
    private val emailSender: EmailSender
) : UserReader, UserWriter {
    override fun findById(id: Long): User = ...
    override fun create(request: CreateUserRequest): User = ...
    // ...
}
```

## ISP Client-Specific Interfaces

```kotlin
// Controller only needs read operations
class UserController(private val userReader: UserReader) {
    fun getUser(id: Long): UserResponse =
        userReader.findById(id).toResponse()
}

// Admin controller needs both read and write
class AdminUserController(
    private val userReader: UserReader,
    private val userWriter: UserWriter
) { ... }
```

## DIP Practical Application

```kotlin
// Bad: high-level policy depends on low-level detail
class OrderService {
    private val repository = MySqlOrderRepository()  // Concrete dependency
    private val notifier = SmtpEmailNotifier()       // Concrete dependency

    fun placeOrder(order: Order) {
        repository.save(order)
        notifier.notify(order)
    }
}

// Good: depend on abstractions defined by the high-level module
interface OrderRepository {
    fun save(order: Order): Order
    fun findById(id: Long): Order?
}

interface OrderNotifier {
    fun notify(order: Order)
}

class OrderService(
    private val repository: OrderRepository,   // Abstraction
    private val notifier: OrderNotifier         // Abstraction
) {
    fun placeOrder(order: Order) {
        repository.save(order)
        notifier.notify(order)
    }
}

// Low-level modules implement the abstractions
class JpaOrderRepository : OrderRepository { ... }
class EmailOrderNotifier : OrderNotifier { ... }
class SlackOrderNotifier : OrderNotifier { ... }
```

## DIP Ports and Adapters Relationship

```text
Domain Layer (high-level)
├── OrderService (uses ports)
├── OrderRepository (port — outbound interface)
└── OrderNotifier (port — outbound interface)

Infrastructure Layer (low-level)
├── JpaOrderRepository (adapter — implements port)
├── EmailOrderNotifier (adapter — implements port)
└── SlackOrderNotifier (adapter — implements port)
```

- **Port**: interface defined in the domain layer (abstraction owned by high-level module)
- **Adapter**: implementation in the infrastructure layer (detail that depends on abstraction)
- DIP ensures the domain layer has zero dependency on infrastructure frameworks
