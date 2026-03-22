# Schema Design Patterns

## 1. Naming Conventions (Detailed)

### Type Naming

| Category    | Convention              | Example                  |
| ----------- | ----------------------- | ------------------------ |
| Object type | PascalCase              | `User`, `OrderItem`      |
| Input type  | PascalCase + Input      | `CreateUserInput`        |
| Payload     | PascalCase + Payload    | `CreateUserPayload`      |
| Connection  | PascalCase + Connection | `UserConnection`         |
| Edge        | PascalCase + Edge       | `UserEdge`               |
| Enum        | PascalCase              | `OrderStatus`            |
| Enum value  | SCREAMING_SNAKE         | `IN_PROGRESS`            |
| Interface   | PascalCase              | `Node`, `Timestamped`    |
| Union       | PascalCase              | `SearchResult`           |
| Scalar      | PascalCase              | `DateTime`, `BigDecimal` |
| Directive   | camelCase               | `@auth`, `@deprecated`   |

### Field Naming

- Use camelCase for all fields: `firstName`, `createdAt`, `isActive`
- Boolean fields: prefix with `is`, `has`, `can` (`isActive`, `hasOrders`)
- Date/time fields: suffix with `At` (`createdAt`, `updatedAt`, `deletedAt`)
- Count fields: suffix with `Count` (`orderCount`, `commentCount`)
- Collection fields: use plural (`orders`, `items`, `tags`)
- Avoid abbreviations: `description` not `desc`, `information` not `info`

### Query and Mutation Naming

```graphql
type Query {
  # Single resource: noun (singular)
  user(id: ID!): User
  order(id: ID!): Order

  # Resource list: noun (plural)
  users(filter: UserFilter, first: Int, after: String): UserConnection!
  orders(status: OrderStatus): [Order!]!

  # Search: "search" prefix
  searchUsers(term: String!): [User!]!

  # Counts: noun + "Count"
  userCount(filter: UserFilter): Int!
}

type Mutation {
  # Create: "create" + noun
  createUser(input: CreateUserInput!): CreateUserPayload!

  # Update: "update" + noun
  updateUser(id: ID!, input: UpdateUserInput!): UpdateUserPayload!

  # Delete: "delete" + noun
  deleteUser(id: ID!): DeleteUserPayload!

  # Domain actions: verb + noun
  activateUser(id: ID!): ActivateUserPayload!
  cancelOrder(id: ID!, reason: String): CancelOrderPayload!
  assignReviewer(prId: ID!, reviewerId: ID!): AssignReviewerPayload!
}
```

---

## 2. Mutation Design Patterns

### Single Input Argument Pattern

Always use a single `input` argument for mutations:

```graphql
# Good: Single input object
type Mutation {
  createUser(input: CreateUserInput!): CreateUserPayload!
}

input CreateUserInput {
  email: String!
  name: String!
  role: UserRole = MEMBER
}

# Bad: Multiple arguments
type Mutation {
  createUser(email: String!, name: String!, role: UserRole): User!
}
```

Benefits:

- Easier to evolve (add fields without breaking clients)
- Cleaner client code with input variables
- Consistent mutation signature across the API

### Mutation Payload Pattern

Always return a payload type, never the entity directly:

```graphql
type CreateUserPayload {
  user: User!
  clientMutationId: String  # Optional: for Relay compatibility
}

type UpdateUserPayload {
  user: User!
}

type DeleteUserPayload {
  deletedId: ID!
  success: Boolean!
}
```

### Union Payload Pattern (Typed Errors)

```graphql
union CreateUserPayload =
  | CreateUserSuccess
  | EmailAlreadyExistsError
  | InvalidEmailFormatError

type CreateUserSuccess {
  user: User!
}

type EmailAlreadyExistsError {
  message: String!
  existingUserId: ID!
  suggestedAction: String!
}

type InvalidEmailFormatError {
  message: String!
  providedEmail: String!
}
```

Client usage:

```graphql
mutation {
  createUser(input: { email: "test@example.com", name: "Test" }) {
    __typename
    ... on CreateUserSuccess {
      user { id name }
    }
    ... on EmailAlreadyExistsError {
      message existingUserId
    }
    ... on InvalidEmailFormatError {
      message providedEmail
    }
  }
}
```

### Bulk Mutation Pattern

```graphql
type Mutation {
  createUsers(inputs: [CreateUserInput!]!): CreateUsersPayload!
  deleteUsers(ids: [ID!]!): DeleteUsersPayload!
}

type CreateUsersPayload {
  users: [User!]!
  errors: [BulkOperationError!]!
  successCount: Int!
  failureCount: Int!
}

type BulkOperationError {
  index: Int!
  message: String!
  code: String!
}
```

---

## 3. Input Validation Patterns

### Schema-Level Validation

```graphql
input CreateProductInput {
  name: String!                    # Required
  price: BigDecimal!               # Required, typed
  category: ProductCategory!       # Enum validation
  tags: [String!]                  # Optional list, non-null elements
  description: String              # Optional
}
```

### Custom Validation Directive

```graphql
directive @constraint(
  minLength: Int
  maxLength: Int
  pattern: String
  min: Float
  max: Float
) on INPUT_FIELD_DEFINITION | ARGUMENT_DEFINITION

input CreateUserInput {
  email: String! @constraint(pattern: "^[\\w.-]+@[\\w.-]+\\.\\w+$")
  name: String! @constraint(minLength: 1, maxLength: 100)
  age: Int @constraint(min: 0, max: 200)
}
```

### Validation Error Response

```graphql
type ValidationError {
  field: String!
  message: String!
  code: ValidationErrorCode!
}

enum ValidationErrorCode {
  REQUIRED
  INVALID_FORMAT
  TOO_SHORT
  TOO_LONG
  OUT_OF_RANGE
  DUPLICATE
}
```

---

## 4. Filter and Sort Patterns

### Filter Input

```graphql
input UserFilter {
  name: StringFilter
  email: StringFilter
  status: UserStatus
  createdAt: DateTimeFilter
  role: [UserRole!]
  AND: [UserFilter!]
  OR: [UserFilter!]
  NOT: UserFilter
}

input StringFilter {
  eq: String
  ne: String
  contains: String
  startsWith: String
  in: [String!]
}

input DateTimeFilter {
  eq: DateTime
  gt: DateTime
  gte: DateTime
  lt: DateTime
  lte: DateTime
  between: DateTimeRange
}

input DateTimeRange {
  start: DateTime!
  end: DateTime!
}
```

### Sort Input

```graphql
input UserSort {
  field: UserSortField!
  direction: SortDirection = ASC
}

enum UserSortField {
  NAME
  CREATED_AT
  EMAIL
}

enum SortDirection {
  ASC
  DESC
}

type Query {
  users(
    filter: UserFilter
    sort: [UserSort!]
    first: Int
    after: String
  ): UserConnection!
}
```

---

## 5. Schema Evolution and Deprecation

### Adding Fields (Non-Breaking)

```graphql
type User {
  id: ID!
  name: String!
  email: String!
  phone: String          # New optional field — non-breaking
  avatarUrl: String      # New optional field — non-breaking
}
```

### Deprecating Fields

```graphql
type User {
  id: ID!
  name: String!
  fullName: String!              # New field
  firstName: String @deprecated(reason: "Use `fullName` instead. Removal: 2026-06")
  lastName: String @deprecated(reason: "Use `fullName` instead. Removal: 2026-06")
}
```

- Always provide a deprecation reason with the replacement field
- Include a planned removal date
- Monitor usage of deprecated fields before removal
- Never remove fields without a deprecation period

### Breaking Changes to Avoid

- Removing a type or field
- Changing a field from nullable to non-null
- Changing a field type
- Removing an enum value
- Adding a required (non-null) argument without a default

### Safe Changes (Non-Breaking)

- Adding a new optional field
- Adding a new type
- Adding a new enum value
- Adding an optional argument with a default
- Deprecating a field

---

## 6. Schema Composition Patterns

### Shared Types

```graphql
# Common types reusable across domains
type Money {
  amount: BigDecimal!
  currency: CurrencyCode!
}

type Address {
  street: String!
  city: String!
  state: String
  country: String!
  postalCode: String!
}

type DateRange {
  start: DateTime!
  end: DateTime!
}
```

### Relay Global Object Identification

```graphql
interface Node {
  id: ID!  # Globally unique ID (e.g., base64("User:123"))
}

type Query {
  node(id: ID!): Node
  nodes(ids: [ID!]!): [Node]!
}

type User implements Node {
  id: ID!  # Encodes type + database ID
  name: String!
}
```

- Use globally unique IDs that encode the type
- Implement the `node` query for generic refetching
- Standard pattern for Relay-compatible clients
