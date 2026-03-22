# Proto3 Style Guide

## File Organization

### Directory Structure

```text
proto/
├── com/
│   └── example/
│       ├── order/
│       │   └── v1/
│       │       ├── order.proto          # Messages
│       │       └── order_service.proto  # Service definition
│       ├── payment/
│       │   └── v1/
│       │       ├── payment.proto
│       │       └── payment_service.proto
│       └── common/
│           └── v1/
│               └── common.proto         # Shared types
└── buf.yaml
```

### File Rules

- One service definition per `.proto` file
- Separate messages from service definitions when messages are shared
- Place common types (pagination, error details) in a shared `common` package
- File names should use `snake_case.proto`

### File Header Template

```protobuf
syntax = "proto3";

package com.example.order.v1;

option java_multiple_files = true;
option java_package = "com.example.order.v1";
option java_outer_classname = "OrderProto";

import "google/protobuf/timestamp.proto";
import "com/example/common/v1/common.proto";
```

---

## Naming Conventions

### Messages

| Element    | Convention       | Example                    |
| ---------- | ---------------- | -------------------------- |
| Message    | PascalCase       | `OrderItem`, `UserProfile` |
| Field      | snake_case       | `order_id`, `created_at`   |
| Enum       | PascalCase       | `OrderStatus`              |
| Enum Value | UPPER_SNAKE_CASE | `ORDER_STATUS_CREATED`     |
| Service    | PascalCase       | `OrderService`             |
| RPC Method | PascalCase       | `CreateOrder`, `GetOrder`  |

### Enum Naming Rules

- Prefix all values with the enum name in UPPER_SNAKE_CASE
- First value (0) must always be `UNSPECIFIED` or `UNKNOWN`
- Group related values logically

```protobuf
// Correct
enum PaymentStatus {
  PAYMENT_STATUS_UNSPECIFIED = 0;
  PAYMENT_STATUS_PENDING = 1;
  PAYMENT_STATUS_COMPLETED = 2;
  PAYMENT_STATUS_FAILED = 3;
  PAYMENT_STATUS_REFUNDED = 4;
}

// Incorrect — missing prefix, no UNSPECIFIED zero value
enum PaymentStatus {
  PENDING = 0;
  COMPLETED = 1;
  FAILED = 2;
}
```

### Field Naming Rules

- Use `snake_case` for all fields
- Suffix ID fields with `_id` (e.g., `user_id`, `order_id`)
- Suffix timestamp fields with `_at` (e.g., `created_at`, `updated_at`)
- Suffix duration fields with `_duration` (e.g., `timeout_duration`)
- Suffix boolean fields with `is_` or `has_` (e.g., `is_active`, `has_discount`)
- Use `_count` for counters (e.g., `retry_count`, `item_count`)

---

## RPC Method Naming

### Standard Method Names

Follow the Google API Design Guide standard methods:

| Method | RPC Name      | Request              | Response             | Mapping          |
| ------ | ------------- | -------------------- | -------------------- | ---------------- |
| List   | `ListOrders`  | `ListOrdersRequest`  | `ListOrdersResponse` | GET (collection) |
| Get    | `GetOrder`    | `GetOrderRequest`    | `Order`              | GET (resource)   |
| Create | `CreateOrder` | `CreateOrderRequest` | `Order`              | POST             |
| Update | `UpdateOrder` | `UpdateOrderRequest` | `Order`              | PATCH/PUT        |
| Delete | `DeleteOrder` | `DeleteOrderRequest` | `Empty` or response  | DELETE           |

### Custom Method Names

For operations that do not map to standard CRUD:

```protobuf
// Use verb + noun format
rpc CancelOrder(CancelOrderRequest) returns (CancelOrderResponse);
rpc ApprovePayment(ApprovePaymentRequest) returns (ApprovePaymentResponse);
rpc SearchProducts(SearchProductsRequest) returns (SearchProductsResponse);

// Avoid generic names
rpc ProcessOrder(ProcessOrderRequest) returns (ProcessOrderResponse);  // Bad — too vague
rpc ConfirmOrder(ConfirmOrderRequest) returns (ConfirmOrderResponse);  // Good — specific action
```

---

## Versioning

### Package-Level Versioning

- Include version in the package name: `com.example.order.v1`
- Major breaking changes require a new version: `com.example.order.v2`
- Minor compatible changes stay in the same version

### Version Bump Criteria

| Change Type                       | Version Impact    |
| --------------------------------- | ----------------- |
| Add new field to existing message | Same version      |
| Add new RPC method to service     | Same version      |
| Add new enum value (non-zero)     | Same version      |
| Rename a field                    | New major version |
| Remove a field                    | New major version |
| Change field type                 | New major version |
| Change field number               | New major version |
| Rename a service or RPC method    | New major version |

---

## Backward Compatibility

### Safe Changes (Wire Compatible)

- Adding new fields with new field numbers
- Adding new enum values (consumers must handle unknown values)
- Adding new RPC methods to an existing service
- Adding new service definitions
- Changing `optional` to `repeated` (only if the field was not used as a boolean presence check)

### Breaking Changes (Wire Incompatible)

- Removing or renaming fields
- Changing field numbers
- Changing field types (e.g., `int32` to `string`)
- Removing enum values
- Renaming services or RPC methods
- Moving fields in or out of `oneof`

### Reserved Fields

```protobuf
message Order {
  reserved 6, 15, 100 to 200;
  reserved "legacy_status", "old_tracking_id";

  string order_id = 1;
  string user_id = 2;
  // Field 6 was previously used for 'legacy_status' — do not reuse
}
```

### Backward Compatibility Rules

- Never reuse field numbers — mark removed fields as `reserved`
- Reserve both the field number and the field name to prevent accidental reuse
- Always handle unknown enum values gracefully on the consumer side — proto3 preserves unknown values
- Add new fields as optional (default in proto3) — old consumers will ignore them
- When a breaking change is unavoidable, create a new package version and maintain both versions during migration
- Use `buf breaking` or similar tools to detect breaking changes in CI

---

## Common Patterns

### Pagination

```protobuf
message ListOrdersRequest {
  int32 page_size = 1;   // Max items to return (default/max enforced server-side)
  string page_token = 2; // Token from previous response
}

message ListOrdersResponse {
  repeated Order orders = 1;
  string next_page_token = 2; // Empty string means last page
  int32 total_size = 3;       // Optional — total count if available
}
```

### Partial Updates with FieldMask

```protobuf
import "google/protobuf/field_mask.proto";

message UpdateOrderRequest {
  Order order = 1;
  google.protobuf.FieldMask update_mask = 2;
  // Only fields listed in update_mask will be updated
}
```

### Wrapper Types for Nullable Fields

```protobuf
import "google/protobuf/wrappers.proto";

message OrderFilter {
  google.protobuf.StringValue status = 1;  // null = no filter
  google.protobuf.Int32Value min_amount = 2;
}
```

### Oneof for Mutually Exclusive Fields

```protobuf
message PaymentMethod {
  oneof method {
    CreditCard credit_card = 1;
    BankTransfer bank_transfer = 2;
    DigitalWallet digital_wallet = 3;
  }
}
```

---

## Buf Configuration

### buf.yaml

```yaml
version: v2
modules:
  - path: proto
lint:
  use:
    - STANDARD
  except:
    - PACKAGE_VERSION_SUFFIX
breaking:
  use:
    - FILE
```

### buf.gen.yaml (Java/Kotlin)

```yaml
version: v2
managed:
  enabled: true
  override:
    - file_option: java_multiple_files
      value: true
    - file_option: java_package_prefix
      value: com.example
plugins:
  - remote: buf.build/protocolbuffers/java
    out: build/generated/source/proto/main/java
  - remote: buf.build/grpc/java
    out: build/generated/source/proto/main/grpc
  - remote: buf.build/grpc/kotlin
    out: build/generated/source/proto/main/grpckt
```

### Linting and Breaking Change Detection

```bash
# Lint proto files
buf lint

# Check for breaking changes against main branch
buf breaking --against '.git#branch=main'

# Generate code
buf generate
```
