# GraphQL Advanced Patterns

## Query Complexity Configuration Example (DGS)

```java
@Configuration
public class GraphQLConfig {
    @Bean
    public InstrumentationProvider instrumentation() {
        return new InstrumentationProvider() {
            @Override
            public Instrumentation provide() {
                return new MaxQueryDepthInstrumentation(10);
            }
        };
    }
}
```

## Federation Subgraph Schema Examples

```graphql
# User subgraph
type User @key(fields: "id") {
  id: ID!
  name: String!
  email: String!
}

# Order subgraph
type Order @key(fields: "id") {
  id: ID!
  items: [OrderItem!]!
  user: User!  # Reference to User from another subgraph
}

extend type User @key(fields: "id") {
  id: ID! @external
  orders: [Order!]!  # Extend User with orders from this subgraph
}
```

## Mutation Error Pattern (Union-based)

```graphql
type Mutation {
  createUser(input: CreateUserInput!): CreateUserPayload!
}

union CreateUserPayload = CreateUserSuccess | ValidationError | ConflictError

type CreateUserSuccess {
  user: User!
}

type ValidationError {
  field: String!
  message: String!
}

type ConflictError {
  message: String!
  existingId: ID!
}
```

- Use union return types for mutations to provide typed error responses
- Each error type carries specific contextual information
- Clients get type-safe error handling via `__typename`

## N+1 Problem and DataLoader

The N+1 problem occurs when fetching a list of entities and then
individually fetching related data for each entity.

```text
# N+1 problem example:
Query: { users { orders { id } } }
1 query: SELECT * FROM users           → N users
N queries: SELECT * FROM orders WHERE user_id = ?  (per user)
```

**Solution — DataLoader (batch loading)**:

```java
// DataLoader batches individual load calls into a single batch request
@DgsDataLoader(name = "orders")
public class OrderDataLoader implements BatchLoader<String, List<Order>> {
    @Override
    public CompletionStage<List<List<Order>>> load(List<String> userIds) {
        // Single query: SELECT * FROM orders WHERE user_id IN (...)
        return CompletableFuture.supplyAsync(
            () -> orderService.findByUserIds(userIds)
        );
    }
}
```

- Always use DataLoader for field resolvers that load related entities
- DataLoader batches requests within a single request context
- DataLoader also provides per-request caching
- Monitor batch sizes — unexpectedly large batches may indicate issues
