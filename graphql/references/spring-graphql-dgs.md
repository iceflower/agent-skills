# Spring for GraphQL and Netflix DGS Framework

## 1. Framework Comparison

| Aspect              | Spring for GraphQL            | Netflix DGS Framework        |
| ------------------- | ----------------------------- | ---------------------------- |
| Maintained by       | Spring Team (VMware/Broadcom) | Netflix                      |
| Spring Boot support | Native (spring-boot-starter)  | Auto-configuration           |
| Schema approach     | SDL-first                     | SDL-first (annotation-based) |
| DataLoader          | `BatchLoaderRegistry`         | `@DgsDataLoader`             |
| Testing             | `GraphQlTester`               | `DgsQueryExecutor`           |
| Code generation     | Not built-in                  | DGS Codegen plugin           |
| Federation          | Not built-in                  | Apollo Federation support    |
| Subscription        | WebSocket, SSE                | WebSocket, SSE               |
| Maturity            | GA since Spring Boot 2.7      | Production-proven at Netflix |

### When to Choose

- **Spring for GraphQL**: Standard Spring ecosystem integration, simple
  APIs, team familiar with Spring MVC/WebFlux patterns
- **Netflix DGS**: Federation needed, code generation preferred,
  annotation-driven development style, Netflix ecosystem alignment

---

## 2. Spring for GraphQL

### Dependencies

```kotlin
// build.gradle.kts
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-graphql")
    implementation("org.springframework.boot:spring-boot-starter-web")
    // For WebSocket subscriptions:
    // implementation("org.springframework.boot:spring-boot-starter-websocket")

    testImplementation("org.springframework.graphql:spring-graphql-test")
}
```

### Schema File Location

Place `.graphqls` files in `src/main/resources/graphql/`:

```graphql
# src/main/resources/graphql/schema.graphqls
type Query {
  user(id: ID!): User
  users(first: Int = 20, after: String): UserConnection!
}

type Mutation {
  createUser(input: CreateUserInput!): CreateUserPayload!
}

type User {
  id: ID!
  name: String!
  email: String!
  orders: [Order!]!
}
```

### Controller (Annotated Handler)

```java
@Controller
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @QueryMapping
    public User user(@Argument String id) {
        return userService.findById(id);
    }

    @QueryMapping
    public Connection<User> users(
            @Argument int first,
            @Argument String after) {
        return userService.findAll(first, after);
    }

    @MutationMapping
    public CreateUserPayload createUser(@Argument CreateUserInput input) {
        return userService.create(input);
    }

    @SchemaMapping(typeName = "User")
    public List<Order> orders(User user) {
        return orderService.findByUserId(user.getId());
    }
}
```

### DataLoader (BatchLoader)

```java
@Configuration
public class DataLoaderConfig {

    @Bean
    public BatchLoaderRegistry batchLoaderRegistry(
            OrderService orderService) {
        return registry -> {
            registry.forTypePair(String.class, List.class)
                .registerMappedBatchLoader((userIds, env) ->
                    Mono.fromSupplier(() ->
                        orderService.findByUserIds(userIds)
                    )
                );
        };
    }
}

// Usage in controller
@Controller
public class UserController {

    @SchemaMapping(typeName = "User")
    public CompletableFuture<List<Order>> orders(
            User user,
            DataLoader<String, List<Order>> dataLoader) {
        return dataLoader.load(user.getId());
    }
}
```

### Security Configuration

```java
@Configuration
@EnableMethodSecurity
public class GraphQLSecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/graphql").authenticated()
                .anyRequest().permitAll()
            )
            .oauth2ResourceServer(oauth2 ->
                oauth2.jwt(Customizer.withDefaults())
            );
        return http.build();
    }
}

// Field-level security in controller
@Controller
public class UserController {

    @SchemaMapping(typeName = "User")
    @PreAuthorize("hasRole('ADMIN') or #user.id == authentication.name")
    public String email(User user) {
        return user.getEmail();
    }
}
```

### Application Configuration

```yaml
# application.yml
spring:
  graphql:
    graphiql:
      enabled: true          # Enable GraphiQL UI (dev only)
    schema:
      introspection:
        enabled: true        # Disable in production
      locations: classpath:graphql/
    websocket:
      path: /graphql         # WebSocket endpoint for subscriptions
```

### Testing with GraphQlTester

```java
@GraphQlTest(UserController.class)
class UserControllerTest {

    @Autowired
    private GraphQlTester graphQlTester;

    @MockitoBean
    private UserService userService;

    @Test
    void shouldReturnUser() {
        when(userService.findById("1"))
            .thenReturn(new User("1", "John", "john@example.com"));

        graphQlTester.documentName("userById")
            .variable("id", "1")
            .execute()
            .path("user.name").entity(String.class).isEqualTo("John")
            .path("user.email").entity(String.class).isEqualTo("john@example.com");
    }

    @Test
    void shouldCreateUser() {
        var input = Map.of("email", "new@example.com", "name", "New User");

        graphQlTester.documentName("createUser")
            .variable("input", input)
            .execute()
            .path("createUser.user.name").entity(String.class).isEqualTo("New User");
    }
}
```

Test document files go in `src/test/resources/graphql-test/`:

```graphql
# src/test/resources/graphql-test/userById.graphql
query UserById($id: ID!) {
  user(id: $id) {
    name
    email
  }
}
```

---

## 3. Netflix DGS Framework

### DGS Dependencies

```kotlin
// build.gradle.kts
plugins {
    id("com.netflix.dgs.codegen") version "7.0.3"
}

dependencies {
    implementation(platform("com.netflix.graphql.dgs:graphql-dgs-platform-dependencies:9.1.3"))
    implementation("com.netflix.graphql.dgs:graphql-dgs-spring-graphql-starter")

    testImplementation("com.netflix.graphql.dgs:graphql-dgs-spring-graphql-starter-test")
}
```

### Code Generation Configuration

```kotlin
// build.gradle.kts
tasks.generateJava {
    schemaPaths.add("${projectDir}/src/main/resources/schema")
    packageName = "com.example.generated"
    generateClient = true
    typeMapping = mutableMapOf(
        "DateTime" to "java.time.OffsetDateTime",
        "BigDecimal" to "java.math.BigDecimal"
    )
}
```

### Data Fetcher (Resolver)

```java
@DgsComponent
public class UserDataFetcher {

    private final UserService userService;

    public UserDataFetcher(UserService userService) {
        this.userService = userService;
    }

    @DgsQuery
    public User user(@InputArgument String id) {
        return userService.findById(id);
    }

    @DgsQuery
    public Connection<User> users(
            @InputArgument Integer first,
            @InputArgument String after) {
        return userService.findAll(first, after);
    }

    @DgsMutation
    public CreateUserPayload createUser(
            @InputArgument CreateUserInput input) {
        return userService.create(input);
    }

    @DgsData(parentType = "User")
    public CompletableFuture<List<Order>> orders(
            DgsDataFetchingEnvironment dfe) {
        User user = dfe.getSource();
        DataLoader<String, List<Order>> dataLoader =
            dfe.getDataLoader(OrderDataLoader.class);
        return dataLoader.load(user.getId());
    }
}
```

### DataLoader

```java
@DgsDataLoader(name = "orders")
public class OrderDataLoader
        implements MappedBatchLoader<String, List<Order>> {

    private final OrderService orderService;

    public OrderDataLoader(OrderService orderService) {
        this.orderService = orderService;
    }

    @Override
    public CompletionStage<Map<String, List<Order>>> load(
            Set<String> userIds) {
        return CompletableFuture.supplyAsync(() ->
            orderService.findByUserIds(userIds)
        );
    }
}
```

### Custom Scalar

```java
@DgsScalar(name = "DateTime")
public class DateTimeScalar implements Coercing<OffsetDateTime, String> {

    @Override
    public String serialize(Object dataFetcherResult) {
        if (dataFetcherResult instanceof OffsetDateTime dt) {
            return dt.format(DateTimeFormatter.ISO_OFFSET_DATE_TIME);
        }
        throw new CoercingSerializeException("Expected OffsetDateTime");
    }

    @Override
    public OffsetDateTime parseValue(Object input) {
        if (input instanceof String s) {
            return OffsetDateTime.parse(s, DateTimeFormatter.ISO_OFFSET_DATE_TIME);
        }
        throw new CoercingParseValueException("Expected ISO DateTime string");
    }

    @Override
    public OffsetDateTime parseLiteral(Object input) {
        if (input instanceof StringValue sv) {
            return OffsetDateTime.parse(sv.getValue());
        }
        throw new CoercingParseLiteralException("Expected ISO DateTime string");
    }
}
```

### Custom Exception Handler

```java
@DgsComponent
public class CustomDataFetchingExceptionHandler
        implements DataFetcherExceptionHandler {

    @Override
    public CompletableFuture<DataFetcherExceptionHandlerResult> handleException(
            DataFetcherExceptionHandlerParameters params) {

        Throwable exception = params.getException();
        GraphQLError error;

        if (exception instanceof NotFoundException nfe) {
            error = TypedGraphQLError.newNotFoundBuilder()
                .message(nfe.getMessage())
                .path(params.getPath())
                .build();
        } else if (exception instanceof ValidationException ve) {
            error = TypedGraphQLError.newBadRequestBuilder()
                .message(ve.getMessage())
                .path(params.getPath())
                .extensions(Map.of("field", ve.getField()))
                .build();
        } else {
            error = TypedGraphQLError.newInternalErrorBuilder()
                .message("Internal server error")
                .path(params.getPath())
                .build();
        }

        return CompletableFuture.completedFuture(
            DataFetcherExceptionHandlerResult.newResult(error).build()
        );
    }
}
```

### Federation Support (DGS)

```java
@DgsComponent
public class UserEntityFetcher {

    private final UserService userService;

    @DgsEntityFetcher(name = "User")
    public User user(Map<String, Object> values) {
        return userService.findById((String) values.get("id"));
    }
}
```

Schema with federation directives:

```graphql
# User subgraph schema
type User @key(fields: "id") {
  id: ID!
  name: String!
  email: String!
}
```

### Testing with DgsQueryExecutor

```java
@SpringBootTest
class UserDataFetcherTest {

    @Autowired
    private DgsQueryExecutor dgsQueryExecutor;

    @MockitoBean
    private UserService userService;

    @Test
    void shouldReturnUser() {
        when(userService.findById("1"))
            .thenReturn(new User("1", "John", "john@example.com"));

        String name = dgsQueryExecutor.executeAndExtractJsonPath(
            "{ user(id: \"1\") { name } }",
            "data.user.name"
        );

        assertThat(name).isEqualTo("John");
    }

    @Test
    void shouldReturnUserWithVariables() {
        when(userService.findById("1"))
            .thenReturn(new User("1", "John", "john@example.com"));

        Map<String, Object> variables = Map.of("id", "1");
        DocumentContext context = dgsQueryExecutor.executeAndGetDocumentContext(
            "query($id: ID!) { user(id: $id) { name email } }",
            variables
        );

        assertThat(context.read("data.user.name", String.class))
            .isEqualTo("John");
        assertThat(context.read("data.user.email", String.class))
            .isEqualTo("john@example.com");
    }
}
```

---

## 4. Common Configuration Patterns

### Query Depth and Complexity Limiting

```java
// Spring for GraphQL
@Configuration
public class GraphQLInstrumentationConfig {

    @Bean
    public RuntimeWiringConfigurer runtimeWiringConfigurer() {
        return wiringBuilder -> wiringBuilder
            .transformer(builder -> builder
                .instrumentation(new MaxQueryDepthInstrumentation(10))
                .instrumentation(new MaxQueryComplexityInstrumentation(200))
            );
    }
}

// DGS
@DgsComponent
public class InstrumentationConfig {

    @Bean
    public Instrumentation maxDepthInstrumentation() {
        return new MaxQueryDepthInstrumentation(10);
    }

    @Bean
    public Instrumentation maxComplexityInstrumentation() {
        return new MaxQueryComplexityInstrumentation(200);
    }
}
```

### Disabling Introspection in Production

```yaml
# application-prod.yml
spring:
  graphql:
    schema:
      introspection:
        enabled: false
    graphiql:
      enabled: false
```

### File Upload (Multipart)

```java
// Spring for GraphQL does not natively support multipart.
// Use a REST endpoint for file uploads alongside GraphQL.

@RestController
public class FileUploadController {

    @PostMapping("/api/upload")
    public UploadResponse upload(@RequestParam("file") MultipartFile file) {
        String url = fileService.store(file);
        return new UploadResponse(url);
    }
}
```

### Request Logging and Metrics

```java
@DgsComponent  // or @Configuration for Spring for GraphQL
public class QueryLoggingInstrumentation extends SimplePerformantInstrumentation {

    private static final Logger log =
        LoggerFactory.getLogger(QueryLoggingInstrumentation.class);

    @Override
    public InstrumentationContext<ExecutionResult> beginExecution(
            InstrumentationExecutionParameters parameters,
            InstrumentationState state) {
        long start = System.currentTimeMillis();
        String query = parameters.getQuery();
        log.debug("GraphQL query: {}", query);

        return SimpleInstrumentationContext.whenCompleted((result, error) -> {
            long duration = System.currentTimeMillis() - start;
            log.info("GraphQL execution completed in {}ms", duration);
            if (error != null) {
                log.error("GraphQL execution error", error);
            }
        });
    }
}
```
