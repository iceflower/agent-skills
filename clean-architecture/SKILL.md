---
name: clean-architecture
description: >-
  Clean Architecture and Hexagonal Architecture (Ports & Adapters) patterns.
  Covers the dependency rule, domain layer isolation, use case (application service)
  design, repository pattern, input/output port definitions, adapter implementation,
  and onion architecture layering.
  Use when designing layered architecture, defining port/adapter boundaries,
  structuring domain-centric applications, or enforcing the dependency rule
  between infrastructure and domain layers.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# Clean Architecture / Hexagonal Architecture Rules

> **Note**: Code examples in this document use framework-agnostic pseudocode (a mix of common OOP syntax). They are not tied to any specific language or framework.

## 1. Architecture Principles

### Dependency Rule

- Dependencies always point inward: outer layers depend on inner layers, never the reverse
- The domain layer is the center and has zero external dependencies
- Framework, database, and UI are implementation details that belong to the outermost layers
- Changes in infrastructure must never require changes in domain logic

### Separation of Concerns

| Layer          | Responsibility                          | Changes When                  |
| -------------- | --------------------------------------- | ----------------------------- |
| Domain         | Business rules, entities, value objects | Business requirements change  |
| Application    | Use case orchestration, ports           | Workflow or use case changes  |
| Infrastructure | Database, messaging, external APIs      | Technology or vendor changes  |
| Presentation   | HTTP, CLI, event listener adapters      | Interface or protocol changes |

### Core Principles

- Business rules are independent of frameworks, databases, and delivery mechanisms
- Each layer has a well-defined boundary with explicit contracts (interfaces)
- Inner layers define interfaces (ports) that outer layers implement (adapters)
- The architecture makes the system testable without external dependencies

---

## 2. Layer Structure

### Layer Hierarchy (Inside-Out)

```text
┌─────────────────────────────────────────────┐
│              Presentation Layer              │  Controllers, CLI, Event Listeners
├─────────────────────────────────────────────┤
│             Infrastructure Layer             │  DB, External API, Messaging
├─────────────────────────────────────────────┤
│              Application Layer               │  Use Cases, Application Services
├─────────────────────────────────────────────┤
│                Domain Layer                  │  Entities, Value Objects, Domain Services
└─────────────────────────────────────────────┘
         ▲ Dependencies point inward ▲
```

### Layer Responsibilities

#### Domain Layer (Innermost)

- Entities with identity and lifecycle
- Value objects (immutable, equality by value)
- Domain services (cross-aggregate logic)
- Domain events
- Repository interfaces (outbound ports)
- No framework annotations, no infrastructure imports

#### Application Layer

- Use case classes / application services
- Inbound port interfaces (what the system can do)
- Outbound port interfaces (what the system needs)
- Command and query objects
- Transaction boundary management
- Event publishing orchestration

#### Infrastructure Layer

- Repository implementations (ORM adapters, query builders, raw SQL)
- External API clients
- Message broker producers/consumers
- File system access
- Cache implementations
- Framework-specific configuration

#### Presentation Layer

- REST controllers / GraphQL resolvers
- Request/response DTOs
- Input validation (format-level, not business-level)
- Authentication filter integration
- API documentation annotations

---

## 3. Ports and Adapters Pattern

> **See [references/ports-and-adapters.md](references/ports-and-adapters.md) for detailed patterns including:**
>
> - Inbound ports (use cases) and inbound adapters (controllers)
> - Outbound ports (repository interfaces) and outbound adapters (implementations)

---

## 4. Package Structure

### Recommended Layout

```text
order/
├── domain/                              # Domain layer
│   ├── model/
│   │   ├── Order                        # Aggregate root
│   │   ├── OrderLine                    # Entity within aggregate
│   │   ├── OrderId                      # Value object (ID)
│   │   ├── OrderStatus                  # Enum
│   │   └── Money                        # Value object
│   ├── event/
│   │   ├── DomainEvent                  # Event marker interface
│   │   └── OrderConfirmedEvent          # Domain event
│   ├── service/
│   │   └── OrderPricingService          # Domain service
│   └── repository/
│       └── OrderRepository              # Outbound port (interface)
│
├── application/                         # Application layer
│   ├── port/
│   │   ├── inbound/
│   │   │   ├── CreateOrderUseCase
│   │   │   └── GetOrderQuery
│   │   └── outbound/
│   │       ├── PaymentGateway
│   │       └── NotificationSender
│   ├── service/
│   │   ├── CreateOrderService           # Use case implementation
│   │   └── OrderQueryService            # Query implementation
│   └── dto/
│       ├── CreateOrderCommand           # Input command
│       └── OrderDetailResult            # Output result
│
├── infrastructure/                      # Infrastructure layer
│   ├── persistence/
│   │   ├── entity/
│   │   │   └── OrderPersistenceEntity   # ORM / persistence entity
│   │   ├── repository/
│   │   │   └── OrderRepositoryImpl      # Outbound adapter
│   │   └── mapper/
│   │       └── OrderEntityMapper        # Persistence ↔ Domain mapper
│   ├── external/
│   │   └── StripePaymentGateway         # External API adapter
│   ├── messaging/
│   │   └── KafkaNotificationSender      # Messaging adapter
│   └── config/
│       └── PersistenceConfig            # Infrastructure config
│
└── presentation/                        # Presentation layer
    ├── controller/
    │   └── OrderController              # REST inbound adapter
    ├── dto/
    │   ├── CreateOrderRequest           # API request DTO
    │   └── OrderDetailResponse          # API response DTO
    └── mapper/
        └── OrderResponseMapper          # Request/Response ↔ Command/Result
```

### Package Dependency Rules

```text
presentation  → application  (invokes use cases)
infrastructure → domain      (implements repository ports)
infrastructure → application (implements outbound ports)
application   → domain       (uses domain model)
domain        → (nothing)    (no outward dependencies)
```

- `domain` package must not import from `application`, `infrastructure`, or `presentation`
- `application` package must not import from `infrastructure` or `presentation`
- `presentation` must not import from `infrastructure` directly
- Cross-cutting via dependency injection only (DI framework wires adapters to ports)

---

## 5. Data Transformation Between Layers

> See [references/data-transformation.md](references/data-transformation.md) for detailed patterns including mapping examples, use case implementation, and test examples.

### Key Rules

- Each layer boundary has its own data objects -- never pass persistence entities to controllers
- Mapping logic lives at the boundary of the outer layer (adapter side)
- Domain objects never depend on DTO or persistence entity classes
- Use dedicated mapper classes or mapping functions for conversions

---

## 6. Dependency Inversion Principle (DIP)

### Core Mechanism

The domain and application layers define interfaces (ports) that the infrastructure layer implements. A dependency injection framework wires the concrete implementations at runtime.

```text
// Domain layer defines the interface
interface OrderRepository {
    fun findById(id: OrderId): Order?
    fun save(order: Order)
}

// Infrastructure layer implements it
// Repository implementation (infrastructure layer)
class OrderRepositoryImpl implements OrderRepository {
    private persistenceRepository: OrderPersistenceRepository

    fun findById(id: OrderId): Order? { ... }
    fun save(order: Order) { ... }
}

// Application layer depends only on the interface
// Application service
class CreateOrderService implements CreateOrderUseCase {
    private orderRepository: OrderRepository      // Port, not adapter
    private paymentGateway: PaymentGateway        // Port, not adapter

    fun execute(command: CreateOrderCommand): OrderId { ... }
}
```

### DIP Benefits

| Without DIP                                      | With DIP                                    |
| ------------------------------------------------ | ------------------------------------------- |
| Service depends on `OrderRepositoryImpl`         | Service depends on `OrderRepository` (port) |
| Changing DB requires changing service code       | Changing DB only requires new adapter       |
| Testing requires real DB or mock framework       | Testing uses simple fake implementation     |
| Domain coupled to framework                      | Domain is framework-free                    |

### DIP Application Rules

- Define interfaces in the layer that needs the capability (domain or application)
- Implement interfaces in the outer layer that provides the capability (infrastructure)
- Never create an interface just to have an interface -- use DIP only when the boundary is meaningful
- Framework annotations belong on implementations, not on port interfaces

---

## 7. Use Case / Application Service Pattern

### Use Case Design Rules

- One class per use case (Single Responsibility)
- Use cases are thin orchestrators -- business logic belongs in domain objects
- Use cases handle transaction boundaries, not domain objects
- Input is a command/query object, output is a result object or domain ID
- Never return domain entities from use cases -- return result DTOs or IDs
- Use case names describe business actions, not technical operations

### Command vs Query Separation (CQS)

| Aspect  | Command              | Query                      |
| ------- | -------------------- | -------------------------- |
| Purpose | Change state         | Read state                 |
| Return  | Void or created ID   | Result DTO                 |
| Side    | Write side           | Read side                  |
| Tx      | Read-write tx        | Read-only tx               |
| Example | `CreateOrderUseCase` | `GetOrderDetailQuery`      |

---

## 8. Testability by Design

### Testing Strategy Per Layer

| Layer          | Test Type        | Dependencies                       | Speed  |
| -------------- | ---------------- | ---------------------------------- | ------ |
| Domain         | Unit test        | None (pure logic)                  | Fast   |
| Application    | Unit test        | Fake ports (in-memory)             | Fast   |
| Infrastructure | Integration test | Test containers, HTTP mock servers | Slow   |
| Presentation   | API test         | HTTP test client, mock services    | Medium |

### Testability Rules

- Domain layer tests require zero mocking -- if mocking is needed, the domain has external dependencies (violation)
- Application layer tests use fake implementations of ports, not mocks
- Infrastructure tests verify that adapters correctly translate between domain and technology
- Presentation tests verify HTTP contract (status codes, response structure), not business logic
- If a class is hard to test, it likely violates separation of concerns -- fix the design, not the test

---

## 9. Anti-Patterns

### Domain Layer Violations

- **Framework annotations in domain**: ORM annotations, DI annotations, transaction annotations on domain classes couples domain to framework
- **Infrastructure imports in domain**: Domain classes importing framework or infrastructure packages
- **Anemic domain model**: Domain objects with only getters/setters and all logic in services
- **Domain returning infrastructure types**: Domain methods returning paginated wrappers, HTTP response objects, or persistence entities

### Dependency Violations

- **Bidirectional dependencies**: Application layer depending on infrastructure and infrastructure depending back on application
- **Skipping layers**: Controller directly calling repository without going through use case
- **Shared mutable state**: Passing persistence entities across layer boundaries (lazy loading failures, unintended mutations)

### Structural Violations

- **God use case**: Single application service handling dozens of unrelated operations
- **Leaky abstraction**: Outbound port method signatures exposing infrastructure details (e.g., `fun findByRawQuery(query: String)`)
- **DTO explosion**: Creating separate DTOs for every minor variation instead of reusing where appropriate
- **Premature abstraction**: Creating ports and adapters for internal modules that will never have multiple implementations

### Common Mistakes

| Mistake                                   | Why It Hurts                             | Fix                                                        |
| ----------------------------------------- | ---------------------------------------- | ---------------------------------------------------------- |
| Persistence entity as domain entity       | Domain coupled to persistence framework  | Separate domain model and persistence entity               |
| Business logic in controller              | Untestable without HTTP context          | Move to domain or application layer                        |
| Repository returning DTOs                 | Mixes persistence and presentation       | Return domain objects, map at boundary                     |
| Transaction annotations on domain service | Domain depends on framework              | Put transaction management on application service          |
| Using framework events as domain events   | Domain coupled to framework event system | Domain defines events, application publishes via framework |

---

## 10. Related Rules

| Related Skill            | When to Reference                                            |
| ------------------------ | ------------------------------------------------------------ |
| `ddd` skill              | Designing entities, aggregates, value objects, domain events |
| `code-quality` skill     | Abstraction layers, modularity, single responsibility        |
| `testing-unit` skill     | Writing tests for use cases and domain logic                 |
| `error-handling` skill   | Exception hierarchy, business vs system exceptions           |
| `spring-framework` skill | Spring DI wiring, `@Transactional`, JPA repository patterns  |

---

## Additional Resources

- Alistair Cockburn, "Hexagonal Architecture" (original article, 2005)
- Robert C. Martin, "Clean Architecture" concepts and dependency rule
- Vaughn Vernon, "Implementing Domain-Driven Design" (architecture patterns chapter)
- Netflix Tech Blog, "Ready for changes with Hexagonal Architecture"
- Herberto Graca, "DDD, Hexagonal, Onion, Clean, CQRS, How I put it all together" (blog series)
- Tom Hombergs, "Get Your Hands Dirty on Clean Architecture"
