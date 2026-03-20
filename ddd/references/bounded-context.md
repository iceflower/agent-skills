# Bounded Context

A Bounded Context defines explicit boundaries within which a domain model is consistent and unambiguous.

## Overview

In large systems, a single unified model becomes impractical. Bounded Contexts partition the domain into manageable areas, each with its own ubiquitous language and model. The same real-world concept may have different representations in different contexts.

```text
┌─────────────────────┐    ┌─────────────────────┐
│   Sales Context     │    │  Shipping Context    │
│                     │    │                      │
│  Customer:          │    │  Customer:           │
│   - name            │    │   - name             │
│   - creditLimit     │    │   - shippingAddress   │
│   - purchaseHistory │    │   - deliveryPrefs    │
└─────────────────────┘    └─────────────────────┘
```

## Context Mapping Patterns

Context Mapping describes the relationships between Bounded Contexts.

### Partnership

Two teams cooperate closely, evolving their models together.

```text
┌──────────┐  Partnership  ┌──────────┐
│ Context A│ ◄───────────▶ │ Context B│
└──────────┘               └──────────┘
```

**Characteristics**: Shared planning, joint releases, mutual dependency.

### Shared Kernel

Two contexts share a small, explicitly defined subset of the model.

```text
┌──────────┐               ┌──────────┐
│ Context A│──┐         ┌──│ Context B│
└──────────┘  │         │  └──────────┘
              ▼         ▼
         ┌──────────────────┐
         │   Shared Kernel  │
         │  (Money, Address) │
         └──────────────────┘
```

**Guidelines**:

- Keep the shared kernel as small as possible
- Changes require agreement from both teams
- Publish as a shared library with semantic versioning

### Customer-Supplier (Upstream/Downstream)

One context (upstream) provides data that another (downstream) consumes.

```text
┌──────────────┐         ┌──────────────┐
│   Upstream   │────────▶│  Downstream  │
│  (Supplier)  │         │  (Customer)  │
└──────────────┘         └──────────────┘
```

**Variants**:

- **Conformist**: Downstream adopts upstream model as-is
- **Customer-Supplier**: Downstream negotiates API needs with upstream

### Open Host Service / Published Language

Upstream exposes a well-defined protocol for integration.

```text
┌──────────────┐   Published API   ┌──────────────┐
│   Upstream   │──────────────────▶│  Downstream  │
│  (OHS + PL)  │   (REST/gRPC)    │              │
└──────────────┘                   └──────────────┘
```

```java
// Published Language: shared API contract
public record ProductCatalogResponse(
    String productId,
    String name,
    BigDecimal price,
    String currency
) {}
```

## Anti-Corruption Layer (ACL)

The ACL is a translation layer that protects a downstream context from the upstream model, preventing foreign concepts from leaking in.

### When to Use

- Integrating with legacy systems
- Consuming external APIs with different domain models
- Protecting your model from upstream changes

### Architecture

```text
┌───────────────┐     ┌──────────────────────────────────┐     ┌───────────┐
│   External    │     │     Anti-Corruption Layer         │     │   Our     │
│   System      │────▶│                                    │────▶│  Domain   │
│   (Legacy)    │     │  Adapter → Translator → Facade   │     │  Model    │
└───────────────┘     └──────────────────────────────────┘     └───────────┘
```

### Implementation

```java
// External system's model (we don't control this)
public record LegacyCustomerDTO(
    String custNo,
    String custName,
    int custType,  // 1=individual, 2=corporate
    String addr1,
    String addr2
) {}

// Our domain model
public record Customer(
    CustomerId id,
    CustomerName name,
    CustomerType type,
    Address address
) {}

// ACL: Translator
@Component
public class CustomerTranslator {

    public Customer toDomain(LegacyCustomerDTO dto) {
        return new Customer(
            new CustomerId(dto.custNo()),
            new CustomerName(dto.custName()),
            mapCustomerType(dto.custType()),
            new Address(dto.addr1(), dto.addr2())
        );
    }

    private CustomerType mapCustomerType(int legacyType) {
        return switch (legacyType) {
            case 1 -> CustomerType.INDIVIDUAL;
            case 2 -> CustomerType.CORPORATE;
            default -> throw new UnknownCustomerTypeException(legacyType);
        };
    }
}

// ACL: Adapter (calls external system)
@Component
public class LegacyCustomerAdapter implements CustomerPort {
    private final LegacyCustomerClient client;
    private final CustomerTranslator translator;

    @Override
    public Customer findById(CustomerId id) {
        LegacyCustomerDTO dto = client.getCustomer(id.value());
        return translator.toDomain(dto);
    }
}
```

## Integration Patterns

### Synchronous Integration

```text
┌─────────┐   REST/gRPC   ┌─────────┐
│ Context │───────────────▶│ Context │
│    A    │  (ACL here)    │    B    │
└─────────┘                └─────────┘
```

**Pros**: Simple, immediate consistency
**Cons**: Temporal coupling, cascading failures

### Asynchronous Integration (Event-Driven)

```text
┌─────────┐   Domain Event   ┌─────────────┐   ┌─────────┐
│ Context │──────────────────▶│   Message   │──▶│ Context │
│    A    │                   │   Broker    │   │    B    │
└─────────┘                   └─────────────┘   └─────────┘
```

**Pros**: Loose coupling, resilient to failures
**Cons**: Eventual consistency, more complex error handling

### Data Integration (Shared Database)

```text
┌─────────┐         ┌─────────┐
│ Context │         │ Context │
│    A    │         │    B    │
└────┬────┘         └────┬────┘
     │                   │
     ▼                   ▼
┌─────────────────────────────┐
│       Shared Database       │
└─────────────────────────────┘
```

**Warning**: Generally an anti-pattern. Creates tight coupling through shared schema. Use only as a transitional strategy.

## Context Map Visualization

Document all context relationships in a single diagram:

```text
┌────────────┐  Partnership   ┌────────────┐
│   Sales    │◄──────────────▶│  Marketing │
└─────┬──────┘                └────────────┘
      │ Upstream
      ▼
┌────────────┐     ACL      ┌──────────────┐
│  Billing   │◄─────────────│   Legacy     │
└─────┬──────┘              │   Accounting │
      │ Published Language  └──────────────┘
      ▼
┌────────────┐
│  Shipping  │  (Conformist to external carrier API)
└────────────┘
```

## Decision Guide

| Question                                | Pattern                     |
| --------------------------------------- | --------------------------- |
| Teams can coordinate releases?          | Partnership / Shared Kernel |
| Upstream willing to accommodate?        | Customer-Supplier           |
| Upstream model acceptable as-is?        | Conformist                  |
| Need protection from external changes?  | Anti-Corruption Layer       |
| Many downstream consumers?              | Open Host Service           |
| Integrating with legacy system?         | ACL + Adapter               |
