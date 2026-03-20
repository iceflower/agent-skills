# Contract Testing

## 1. Contract Testing Overview

### What Is Contract Testing

Contract testing verifies that two services (consumer and provider) can communicate correctly by testing against a shared contract, without requiring both services to be running simultaneously.

### Why It Matters for Microservices

| Problem | How Contract Testing Solves It |
| --- | --- |
| Integration tests are slow and brittle | Contracts are tested independently per service |
| API changes break consumers silently | Consumer expectations are verified against provider |
| End-to-end test environments are expensive | No shared environment needed |
| Deployment coupling | Each service deploys independently with confidence |

### Consumer-Driven vs Provider-Driven

| Approach | Flow | Best For |
| --- | --- | --- |
| Consumer-Driven (CDC) | Consumer defines expectations → Provider verifies | Many consumers, provider must not break them |
| Provider-Driven | Provider publishes contract → Consumers adapt | Single authoritative API, OpenAPI-first design |
| Bi-Directional | Both sides publish contracts → Broker compares | Teams with equal ownership |

---

## 2. Pact Framework

### Consumer Test (Kotlin/JUnit 5)

```kotlin
@ExtendWith(PactConsumerTestExt::class)
@PactTestFor(providerName = "user-service", port = "8080")
class UserClientPactTest {

    @Pact(consumer = "order-service")
    fun getUserPact(builder: PactDslWithProvider): V4Pact {
        return builder
            .given("user with ID 1 exists")
            .uponReceiving("a request for user 1")
            .path("/api/users/1")
            .method("GET")
            .willRespondWith()
            .status(200)
            .headers(mapOf("Content-Type" to "application/json"))
            .body(
                PactDslJsonBody()
                    .integerType("id", 1)
                    .stringType("name", "John Doe")
                    .stringType("email", "john@example.com")
            )
            .toPact(V4Pact::class.java)
    }

    @Test
    @PactTestFor(pactMethod = "getUserPact")
    fun `should fetch user by ID`(mockServer: MockServer) {
        val client = UserClient(baseUrl = mockServer.getUrl())
        val user = client.getUser(1)

        assertThat(user.name).isEqualTo("John Doe")
        assertThat(user.email).isEqualTo("john@example.com")
    }
}
```

### Provider Verification (Kotlin/JUnit 5)

```kotlin
@Provider("user-service")
@PactBroker(
    host = "pact-broker.example.com",
    authentication = PactBrokerAuth(token = "\${PACT_BROKER_TOKEN}")
)
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class UserProviderPactTest {

    @TestTemplate
    @ExtendWith(PactVerificationInvocationContextProvider::class)
    fun verifyPact(context: PactVerificationContext) {
        context.verifyInteraction()
    }

    @State("user with ID 1 exists")
    fun setupUser() {
        userRepository.save(User(id = 1, name = "John Doe", email = "john@example.com"))
    }
}
```

### Pact Broker Workflow

```text
1. Consumer test runs → generates pact file (JSON contract)
2. Pact file published to Pact Broker
3. Provider pulls contracts from Broker
4. Provider verifies against each consumer contract
5. Verification result published back to Broker
6. can-i-deploy checks before deployment
```

### Version Selectors

| Selector | Purpose |
| --- | --- |
| `{ "mainBranch": true }` | Latest from main branch |
| `{ "branch": "feat/xyz" }` | Specific feature branch |
| `{ "deployedOrReleased": true }` | Currently deployed versions |
| `{ "environment": "production" }` | Versions in production |

---

## 3. Spring Cloud Contract

### Contract DSL (Groovy)

```groovy
// contracts/shouldReturnUser.groovy
Contract.make {
    description "should return user by ID"
    request {
        method GET()
        url "/api/users/1"
        headers {
            accept(applicationJson())
        }
    }
    response {
        status OK()
        headers {
            contentType(applicationJson())
        }
        body([
            id   : 1,
            name : $(producer(regex('[A-Za-z ]+')), consumer("John Doe")),
            email: $(producer(regex('[a-z]+@[a-z]+\\.[a-z]+')), consumer("john@example.com"))
        ])
    }
}
```

### Contract DSL (YAML)

```yaml
description: should return user by ID
request:
  method: GET
  url: /api/users/1
  headers:
    Accept: application/json
response:
  status: 200
  headers:
    Content-Type: application/json
  body:
    id: 1
    name: John Doe
    email: john@example.com
  matchers:
    body:
      - path: $.name
        type: by_regex
        value: "[A-Za-z ]+"
      - path: $.email
        type: by_regex
        value: "[a-z]+@[a-z]+\\.[a-z]+"
```

### Provider Side — Auto-Generated Tests

```kotlin
// build.gradle.kts
plugins {
    id("org.springframework.cloud.contract") version "4.2.0"
}

contracts {
    testFramework = TestFramework.JUNIT5
    baseClassForTests = "com.example.BaseContractTest"
}
```

```kotlin
// BaseContractTest.kt
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.MOCK)
@AutoConfigureMockMvc
abstract class BaseContractTest {
    @Autowired
    lateinit var mockMvc: MockMvc

    @BeforeEach
    fun setup() {
        // Setup test data
    }
}
```

### Consumer Side — Stub Runner

```kotlin
@SpringBootTest
@AutoConfigureStubRunner(
    ids = ["com.example:user-service:+:stubs:8080"],
    stubsMode = StubRunnerProperties.StubsMode.REMOTE,
    repositoryRoot = "https://nexus.example.com/repository/maven-releases/"
)
class UserClientContractTest {

    @Test
    fun `should call user service stub`() {
        val response = restTemplate.getForEntity(
            "http://localhost:8080/api/users/1",
            UserResponse::class.java
        )
        assertThat(response.statusCode).isEqualTo(HttpStatus.OK)
        assertThat(response.body?.name).matches("[A-Za-z ]+")
    }
}
```

---

## 4. Contract Testing Workflow

### CI/CD Integration

```text
Consumer Pipeline:
  1. Run consumer contract tests
  2. Publish pacts to Broker
  3. can-i-deploy --pacticipant order-service --version $GIT_SHA --to production
  4. Deploy if can-i-deploy succeeds

Provider Pipeline:
  1. Pull pacts from Broker (deployedOrReleased selector)
  2. Run provider verification
  3. Publish verification results
  4. can-i-deploy --pacticipant user-service --version $GIT_SHA --to production
  5. Deploy if can-i-deploy succeeds
```

### can-i-deploy

```bash
# Check if safe to deploy
pact-broker can-i-deploy \
  --pacticipant order-service \
  --version $(git rev-parse HEAD) \
  --to-environment production

# Record deployment
pact-broker record-deployment \
  --pacticipant order-service \
  --version $(git rev-parse HEAD) \
  --environment production
```

### Provider States

Provider states set up the preconditions for contract verification:

```kotlin
@State("user with ID 1 exists")
fun userExists() {
    userRepository.save(testUser)
}

@State("no users exist")
fun noUsers() {
    userRepository.deleteAll()
}

@State("user with ID 1 exists", action = StateChangeAction.TEARDOWN)
fun cleanupUser() {
    userRepository.deleteAll()
}
```

---

## 5. Schema-Based Contracts

### OpenAPI as Contract

```yaml
# openapi.yaml — serves as the contract
openapi: "3.1.0"
info:
  title: User Service API
  version: "1.0.0"
paths:
  /api/users/{id}:
    get:
      operationId: getUser
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        "200":
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/User"
```

### Validation Tools

| Tool | Purpose | Usage |
| --- | --- | --- |
| Prism | Mock server from OpenAPI | `prism mock openapi.yaml` |
| Spectral | Lint OpenAPI spec | `spectral lint openapi.yaml` |
| Schemathesis | Property-based API testing | `schemathesis run openapi.yaml --base-url http://localhost:8080` |
| openapi-diff | Detect breaking changes | `openapi-diff old.yaml new.yaml` |

### When to Use Schema-Based vs Consumer-Driven

| Criteria | Consumer-Driven (Pact) | Schema-Based (OpenAPI) |
| --- | --- | --- |
| API ownership | Multiple consumers with different needs | Single authoritative API definition |
| Design approach | Consumer-first, bottom-up | API-first, top-down |
| Contract scope | Only what each consumer uses | Entire API surface |
| Breaking change detection | Consumer tests fail | openapi-diff detects |
| Tooling maturity | Pact Broker ecosystem | OpenAPI ecosystem (Prism, Spectral) |
| Best for | Microservices with many consumers | Public APIs, API-first teams |
| Overhead | Per-consumer test maintenance | Schema maintenance + validation |

- **Choose Consumer-Driven** when consumers have diverse needs and you want to guarantee no consumer breaks
- **Choose Schema-Based** when you have a well-defined API-first workflow and want a single source of truth
- **Combine both** when you need API-first design (OpenAPI) plus consumer-specific contract verification (Pact)

---

## 6. Testing Patterns

### Consumer-Driven Contract Testing Flow

```text
Consumer Team                    Pact Broker                    Provider Team
     │                               │                               │
     ├─ Write consumer test ─────────┤                               │
     ├─ Generate pact ───────────────┤                               │
     ├─ Publish pact ────────────────▶│                               │
     │                               ├── Webhook trigger ───────────▶│
     │                               │                               ├─ Pull pact
     │                               │                               ├─ Run verification
     │                               │◀── Publish result ────────────┤
     ├─ can-i-deploy ───────────────▶│                               │
     │◀── Yes/No ────────────────────┤                               │
```

### Contract Versioning

- Use Git SHA as the pact version for traceability
- Use branch-based selectors for feature development
- Use `deployedOrReleased` for production safety
- Never modify published contracts — publish new versions

---

## 7. Anti-Patterns

- Testing implementation details (internal data structures, exact field order)
- Overly strict contracts (exact timestamps, UUIDs) — use matchers instead
- Skipping provider verification — contracts are only useful if both sides verify
- Using contract tests as integration tests — they verify the contract, not business logic
- Not using `can-i-deploy` — deploying without checking compatibility
- Monolithic contracts covering the entire API — test only what each consumer actually uses
- Not maintaining provider states — verification fails for wrong reasons
- Treating contracts as documentation — they complement, not replace, API docs
