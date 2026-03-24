---
name: graphql
description: >-
  GraphQL API design and implementation patterns including schema design
  principles, type system (Object, Input, Interface, Union, Enum), resolver
  patterns, N+1 problem prevention with DataLoader, pagination (Cursor-based,
  Relay Connection), error handling, query complexity and depth limiting,
  authentication/authorization at field level, and Federation (Apollo).
  Covers Spring for GraphQL, Netflix DGS Framework, and GraphQL security
  (OWASP GraphQL Cheat Sheet).
  Use when designing GraphQL schemas, implementing resolvers, optimizing
  query performance, setting up GraphQL Federation, or reviewing GraphQL
  API security.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# GraphQL API Design and Implementation Rules

## 1. Schema Design Principles

### SDL-first vs Code-first

- **SDL-first** (recommended for most projects): Define the schema in `.graphqls`
  files, then implement resolvers to match
  - Encourages contract-first design — schema is the API contract
  - Better for team collaboration — frontend and backend agree on schema first
  - Tools: Spring for GraphQL, Apollo Server
- **Code-first**: Generate the schema from code annotations or DSL
  - Useful when schema closely mirrors domain model
  - Risk of coupling schema to implementation details
  - Tools: Netflix DGS (annotation-based), GraphQL Kotlin, TypeGraphQL

### Schema Organization

```text
src/main/resources/graphql/
  schema.graphqls          # Root schema (Query, Mutation, Subscription)
  types/
    user.graphqls          # User-related types
    order.graphqls         # Order-related types
  inputs/
    user-input.graphqls    # User input types
  enums/
    status.graphqls        # Enum definitions
  interfaces/
    node.graphqls          # Shared interfaces
```

### Naming Conventions

- **Types**: PascalCase (`User`, `OrderItem`)
- **Fields**: camelCase (`firstName`, `createdAt`)
- **Enums**: PascalCase type, SCREAMING_SNAKE_CASE values (`OrderStatus.IN_PROGRESS`)
- **Mutations**: verb + noun (`createUser`, `updateOrder`, `deleteComment`)
- **Queries**: noun for single (`user`), plural for list (`users`)
- **Input types**: suffix with `Input` (`CreateUserInput`, `UpdateOrderInput`)
- **Payload types**: suffix with `Payload` (`CreateUserPayload`)

---

## 2. Type System

### Object Types

```graphql
type User {
  id: ID!
  email: String!
  name: String!
  avatar: String
  orders(first: Int, after: String): OrderConnection!
  createdAt: DateTime!
}
```

- Use `ID!` for identifiers — never `Int!` or `String!`
- Mark required fields with `!` (non-null)
- Use nullable fields (`String`) for optional data
- Add arguments to fields for filtering/pagination

### Input Types

```graphql
input CreateUserInput {
  email: String!
  name: String!
  avatar: String
}

input UpdateUserInput {
  email: String
  name: String
  avatar: String
}
```

- Separate input types for create and update operations
- Create inputs: required fields are non-null
- Update inputs: all fields nullable (partial update)
- Never reuse output types as input types

### Interface Types

```graphql
interface Node {
  id: ID!
}

interface Timestamped {
  createdAt: DateTime!
  updatedAt: DateTime!
}

type User implements Node & Timestamped {
  id: ID!
  email: String!
  createdAt: DateTime!
  updatedAt: DateTime!
}
```

- Use interfaces for shared field contracts
- `Node` interface is standard for Relay-compatible APIs

### Union Types

```graphql
union SearchResult = User | Order | Product

type Query {
  search(term: String!): [SearchResult!]!
}
```

- Use unions when return types share no common fields
- Prefer interfaces when types share fields
- Always handle all union members in the client

### Enum Types

```graphql
enum OrderStatus {
  PENDING
  CONFIRMED
  SHIPPED
  DELIVERED
  CANCELLED
}
```

- Use enums for fixed sets of values
- Use SCREAMING_SNAKE_CASE for values
- Add descriptions for non-obvious values

### Custom Scalar Types

```graphql
scalar DateTime
scalar URL
scalar JSON
scalar BigDecimal
```

- Define custom scalars for domain-specific types
- Always provide serialization/deserialization logic
- Prefer specific scalars over `String` for validation

---

## 3. Resolver Patterns and DataLoader

### Resolver Structure

```text
Query.user(id) → UserResolver
  User.orders → OrderResolver (field resolver)
    Order.items → OrderItemResolver (field resolver)
```

- Keep resolvers thin — delegate business logic to service layer
- One resolver class per type or domain area
- Field resolvers load data lazily — only when requested

> See [references/advanced-patterns.md](references/advanced-patterns.md) for N+1 problem explanation, DataLoader implementation example, and mutation error patterns.

### DataLoader Rules

- Always use DataLoader for field resolvers that load related entities
- DataLoader batches requests within a single request context
- DataLoader also provides per-request caching
- Monitor batch sizes — unexpectedly large batches may indicate issues

### Resolver Best Practices

- Never call repositories directly from resolvers — use a service layer
- Handle null values explicitly in resolvers
- Use `@Secured` or custom directives for field-level authorization
- Log resolver errors with correlation IDs for debugging

---

## 4. Pagination

### Cursor-based Pagination (Relay Connection Spec)

```graphql
type Query {
  users(first: Int, after: String, last: Int, before: String): UserConnection!
}

type UserConnection {
  edges: [UserEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type UserEdge {
  node: User!
  cursor: String!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}
```

### Pagination Guidelines

- Prefer cursor-based over offset-based pagination
  - Cursor-based: stable under concurrent inserts/deletes
  - Offset-based: simple but breaks with data changes
- Cursors should be opaque strings (base64-encoded IDs)
- Always include `totalCount` when feasible
- Set reasonable defaults and maximums for `first`/`last` (e.g., default 20,
  max 100)
- For simple use cases, offset-based pagination is acceptable:

```graphql
type Query {
  users(page: Int = 1, size: Int = 20): UserPage!
}

type UserPage {
  content: [User!]!
  totalElements: Int!
  totalPages: Int!
  hasNext: Boolean!
}
```

---

## 5. Error Handling

### GraphQL Error Response Structure

```json
{
  "data": null,
  "errors": [
    {
      "message": "User not found",
      "locations": [{ "line": 2, "column": 3 }],
      "path": ["user"],
      "extensions": {
        "code": "NOT_FOUND",
        "classification": "DataFetchingException"
      }
    }
  ]
}
```

### Error Handling Patterns

- Use `extensions.code` for machine-readable error codes
- Define a consistent set of error codes across the API:
  - `NOT_FOUND`, `VALIDATION_ERROR`, `UNAUTHORIZED`, `FORBIDDEN`,
    `INTERNAL_ERROR`, `CONFLICT`, `RATE_LIMITED`
- Return partial data when possible — GraphQL supports partial responses
- Never expose internal details (stack traces, SQL) in error messages

- Use union return types for mutations to provide typed error responses (see [references/advanced-patterns.md](references/advanced-patterns.md) for union-based mutation error pattern examples)

---

## 6. Query Complexity and Depth Limiting

### Depth Limiting

- Set a maximum query depth (recommended: 7-10 for general APIs)
- Reject queries exceeding the depth limit before execution

```graphql
# This nested query could be malicious if unbounded:
{
  user {
    friends {
      friends {
        friends {
          friends { ... }  # Excessive depth
        }
      }
    }
  }
}
```

### Complexity Analysis

- Assign complexity scores to fields based on cost:
  - Scalar fields: 0-1
  - Object fields: 1
  - List fields: multiply by expected/requested count
  - Database-heavy fields: higher weight
- Set a maximum total complexity per query (e.g., 1000)
- Return the complexity cost in response extensions for transparency

> For DGS framework configuration example, see [references/advanced-patterns.md](references/advanced-patterns.md).

---

## 7. Authentication and Authorization

### Authentication

- Authenticate at the transport layer (HTTP headers, cookies)
- Pass the authenticated user context to resolvers via GraphQL context
- Do NOT put authentication logic inside individual resolvers

### Field-Level Authorization

```graphql
type User {
  id: ID!
  name: String!                  # Public
  email: String! @auth(role: SELF)     # Only the user themselves
  salary: BigDecimal @auth(role: ADMIN) # Admin only
}
```

- Use custom directives or schema annotations for declarative authorization
- Implement authorization in a middleware/interceptor layer, not in
  business logic
- Return `null` for unauthorized nullable fields; throw for non-null fields
- Log authorization failures for security monitoring

### Authorization Patterns

- **Directive-based**: `@auth(role: ADMIN)` on schema fields
- **Resolver-based**: Check permissions in the resolver or service layer
- **DataLoader-based**: Filter results in DataLoader based on context

---

## 8. Subscriptions (Real-time)

### Subscription Design

```graphql
type Subscription {
  orderStatusChanged(orderId: ID!): OrderStatusEvent!
  newMessage(channelId: ID!): Message!
}

type OrderStatusEvent {
  order: Order!
  previousStatus: OrderStatus!
  newStatus: OrderStatus!
  changedAt: DateTime!
}
```

### Implementation Guidelines

- Use WebSocket (graphql-ws protocol) for subscriptions
- Keep subscription payloads small — include only changed data
- Always require authentication for subscriptions
- Set connection timeouts and maximum subscription limits per client
- Use server-sent events (SSE) as an alternative for simpler use cases
- Consider using a message broker (Redis Pub/Sub, Kafka) for scalability

---

## 9. Federation (Apollo Federation)

### When to Use Federation

- Multiple teams own different parts of the graph
- Microservice architecture where each service owns its domain types
- Need to compose a unified schema from independent subgraphs

> For subgraph schema examples, see [references/advanced-patterns.md](references/advanced-patterns.md).

### Federation Guidelines

- Each entity has exactly one owning subgraph
- Use `@key` directive to define entity identity
- Use `@external`, `@requires`, `@provides` for cross-subgraph fields
- Keep the gateway/router stateless — all logic in subgraphs
- Monitor subgraph latency — gateway adds overhead
- Version subgraphs independently; use schema registry for compatibility

---

## 10. Security

> For the full security reference, see the OWASP GraphQL Cheat Sheet.

### Introspection

- **Disable introspection in production** — it exposes the full schema
- Enable only in development/staging environments

### Query Restrictions

- Set maximum query depth (see Section 6)
- Set maximum query complexity (see Section 6)
- Limit batch queries (array of operations in single request)
- Set request size limits at the HTTP layer
- Implement rate limiting per client/IP

### Input Validation

- Validate all input arguments at the schema level (non-null, enums)
- Add custom validation in resolvers for business rules
- Sanitize string inputs to prevent injection attacks
- Use custom scalars with built-in validation (e.g., `Email`, `URL`)

### Persisted Queries

- Use automatic persisted queries (APQ) or pre-registered queries in
  production
- APQ: client sends a hash; server looks up the query
- Prevents arbitrary query execution in sensitive environments
- Reduces bandwidth by not sending full query strings

### Additional Security Measures

- Enable CORS with strict origin policies
- Use HTTPS for all GraphQL endpoints
- Log and monitor query patterns for anomaly detection
- Set timeouts for resolver execution to prevent resource exhaustion

---

## 11. GraphQL vs REST Selection Criteria

### Prefer GraphQL When

- Clients need flexible data fetching (mobile vs web different needs)
- Multiple related entities are fetched in a single request
- API serves diverse clients with varying data requirements
- Real-time features (subscriptions) are needed
- Rapid frontend iteration without backend changes

### Prefer REST When

- Simple CRUD operations on well-defined resources
- File upload/download is a primary use case
- Caching at the HTTP layer (CDN, browser) is critical
- Team has limited GraphQL experience
- API is primarily server-to-server communication
- OpenAPI/Swagger tooling ecosystem is a requirement

### Hybrid Approach

- Use GraphQL for client-facing APIs with complex data requirements
- Use REST for internal service-to-service communication
- Use REST for file handling, health checks, and webhook endpoints
- A single application can expose both GraphQL and REST endpoints

---

## 12. Framework Reference

For detailed framework-specific implementation patterns with Spring for
GraphQL and Netflix DGS, see
[references/spring-graphql-dgs.md](references/spring-graphql-dgs.md).

For advanced schema design patterns, naming conventions, and mutation
design guidelines, see
[references/schema-design-patterns.md](references/schema-design-patterns.md).
