---
name: spring-ai
description: >-
  Spring AI conventions and patterns for building AI-powered applications
  including ChatClient configuration, tool/function calling, prompt template
  management, vector store integration, RAG (Retrieval Augmented Generation),
  Advisors API, MCP (Model Context Protocol) integration, multi-model
  routing patterns, advanced RAG (query rewriting, hybrid search, reranking,
  agentic RAG), agent frameworks (Router Agent, Human-in-the-Loop, memory patterns),
  and model evaluation/token monitoring.
  Use when building or reviewing Spring AI applications, integrating LLMs
  with Spring Boot, implementing ChatClient, configuring tool calling,
  designing prompt templates, working with vector databases in Spring,
  or building advanced RAG pipelines and autonomous agent workflows.
license: MIT
metadata:
  author: iceflower
  version: "2.1"
  last-reviewed: "2026-04"
---

# Spring AI Core Rules

## Platform Requirements

| Requirement           | Version                          |
| --------------------- | -------------------------------- |
| Spring AI             | 2.0.x (latest: 2.0.0-M4)         |
| Spring Boot           | 4.0+ (Spring Framework 7.0)      |
| JDK                   | 17+ (JDK 25 LTS recommended)     |
| Jackson               | 3 (`tools.jackson` package)      |

> Jackson 3 uses `tools.jackson` package namespace instead of `com.fasterxml.jackson`. Ensure all serialization dependencies align.

## 1. ChatClient Configuration

> See [references/chatclient-patterns.md](references/chatclient-patterns.md) for detailed fluent API usage, streaming patterns, and structured output.

### Key Rules

- Inject `ChatClient.Builder` (auto-configured), not `ChatClient` directly — build in constructor or `@Bean`
- Use `ChatClient.create(chatModel)` only for simple cases — prefer builder for defaults
- Set default system prompt, advisors, and tools on the builder — override per-request as needed
- Use `.call()` for synchronous responses, `.stream()` for reactive `Flux` responses
- Use `.entity(Class<T>)` for structured output — Spring AI handles JSON schema generation
- Always configure `spring.ai.retry` properties for production resilience
- Always configure `spring.ai.openai.chat.options.temperature` explicitly — no default value in 2.x

### ChatClient Creation

```java
@RestController
class MyController {
    private final ChatClient chatClient;

    public MyController(ChatClient.Builder builder) {
        this.chatClient = builder
            .defaultSystem("You are a helpful assistant.")
            .build();
    }
}
```

---

## 2. Tool/Function Calling

> See [references/tool-calling.md](references/tool-calling.md) for detailed @Tool annotation usage, ToolCallback interface, and migration patterns.

### Tool Calling Rules

- Use `@Tool` annotation for declarative tool definitions — method name becomes tool name by default
- Always provide descriptive `description` — the model uses it to decide when to call the tool
- Use `@ToolParam(description = "...")` for parameter descriptions — improves model accuracy
- Register tools via `.tools(new MyTools())` on ChatClient or `.defaultTools()` on builder — `.defaultFunctions()` is removed in 2.x; both methods use `ToolCallback` internally
- Use `ToolContext` to pass application context (tenant ID, user info) without exposing to the model
- Tool methods must not return reactive types (`Mono`, `Flux`) — tool calling is synchronous
- Set `returnDirect = true` on `@Tool` when the tool result should go directly to the user

### Tool Definition Example

```java
class WeatherTools {
    @Tool(description = "Get current weather for a given city")
    String getWeather(
        @ToolParam(description = "City name") String city,
        @ToolParam(description = "Temperature unit", required = false) String unit
    ) {
        return weatherService.getCurrentWeather(city, unit);
    }
}

// Register with ChatClient
chatClient.prompt()
    .tools(new WeatherTools())
    .user("What is the weather in Seoul?")
    .call()
    .content();
```

---

## 3. Prompt Template Management

### PromptTemplate

```java
// Inline template with {placeholder} syntax
chatClient.prompt()
    .user(u -> u
        .text("Tell me about {topic} in {language}")
        .param("topic", "Spring AI")
        .param("language", "Korean"))
    .call()
    .content();

// From resource file
chatClient.prompt()
    .user(u -> u
        .text(new ClassPathResource("prompts/summary.st"))
        .param("document", documentText))
    .call()
    .content();
```

### Prompt Template Rules

- Use `{placeholder}` syntax for template variables (default StringTemplate renderer)
- Store complex prompts in `src/main/resources/prompts/` as `.st` files
- Use `.system()` for persona/instruction, `.user()` for task-specific input
- Use `TemplateRenderer` customization for non-default delimiters
- Never hardcode long prompts inline — extract to resource files for maintainability

---

## 4. Vector Store Integration

> See [references/vector-store-rag.md](references/vector-store-rag.md) for detailed vector store patterns, supported databases, and RAG implementation.

### Vector Store Rules

- Use `VectorStore` interface for write operations (`add`, `delete`), `VectorStoreRetriever` for read-only
- Use `SearchRequest.builder()` to configure `topK`, `similarityThreshold`, and `filterExpression`
- Default `topK` is 4 and `similarityThreshold` is 0.0 (accept all) — tune for your use case
- Use metadata filtering for multi-tenant isolation (e.g., `"tenantId == 'acme'"`)
- Configure `BatchingStrategy` for large document ingestion — default is `TokenCountBatchingStrategy`

### Basic Usage

```java
// Add documents
vectorStore.add(List.of(
    new Document("Spring AI simplifies AI integration.", Map.of("topic", "spring-ai")),
    new Document("RAG improves answer accuracy.", Map.of("topic", "rag"))
));

// Search
List<Document> results = vectorStore.similaritySearch(
    SearchRequest.builder()
        .query("How does RAG work?")
        .topK(5)
        .similarityThreshold(0.7)
        .filterExpression("topic == 'rag'")
        .build()
);
```

---

## 5. RAG (Retrieval Augmented Generation)

> See [references/vector-store-rag.md](references/vector-store-rag.md) for detailed RAG advisor configuration and query transformation.

### RAG Rules

- Use `QuestionAnswerAdvisor` for simple RAG — single vector store, no query transformation
- Use `RetrievalAugmentationAdvisor` for advanced RAG — supports query transformers and custom augmenters
- Always set a meaningful `similarityThreshold` (e.g., 0.5-0.8) — 0.0 returns irrelevant results
- Use `ContextualQueryAugmenter.builder().allowEmptyContext(true)` to let the model answer without context
- Use `RewriteQueryTransformer` or `CompressionQueryTransformer` for better retrieval accuracy

### Quick RAG Setup

```java
// Simple RAG with QuestionAnswerAdvisor
ChatClient chatClient = ChatClient.builder(chatModel)
    .defaultAdvisors(
        QuestionAnswerAdvisor.builder(vectorStore)
            .searchRequest(SearchRequest.builder()
                .similarityThreshold(0.7)
                .topK(5)
                .build())
            .build())
    .build();

String answer = chatClient.prompt()
    .user("What is Spring AI?")
    .call()
    .content();
```

---

## 6. Advisors API

### Advisor Chain

Advisors intercept and modify ChatClient requests and responses in a chain pattern, similar to servlet filters.

```java
ChatClient chatClient = ChatClient.builder(chatModel)
    .defaultAdvisors(
        MessageChatMemoryAdvisor.builder(chatMemory).build(),
        QuestionAnswerAdvisor.builder(vectorStore).build(),
        new SimpleLoggerAdvisor()
    )
    .build();
```

### Key Interfaces

| Interface        | Purpose                      | Key Method                             |
| ---------------- | ---------------------------- | -------------------------------------- |
| `CallAdvisor`    | Synchronous interception     | `adviseCall(request, chain)`           |
| `StreamAdvisor`  | Streaming interception       | `adviseStream(request, chain)`         |

### Ordering Rules

- Lower `getOrder()` value = higher priority (processed first on request, last on response)
- Use `Ordered.HIGHEST_PRECEDENCE` for security/auth advisors
- Use `Ordered.LOWEST_PRECEDENCE` for logging advisors

### Built-in Advisors

| Advisor                         | Purpose                                 |
| ------------------------------- | --------------------------------------- |
| `MessageChatMemoryAdvisor`      | Conversation memory via message history |
| `PromptChatMemoryAdvisor`       | Memory incorporated into system prompt  |
| `VectorStoreChatMemoryAdvisor`  | Memory retrieval from vector store      |
| `QuestionAnswerAdvisor`         | Simple RAG pattern                      |
| `RetrievalAugmentationAdvisor`  | Advanced modular RAG                    |
| `SafeGuardAdvisor`              | Content safety filtering                |
| `ReReadingAdvisor`              | RE2 technique for better reasoning      |
| `SimpleLoggerAdvisor`           | Request/response logging                |

> **Deprecation note (2.x):** `ChatClient.disableMemory()` is deprecated. Use `disableInternalConversationHistory()` instead.

---

## 7. MCP (Model Context Protocol) Integration

### Overview

Spring AI provides MCP integration through Boot starters for both client and server roles.

### Client Setup

```xml
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-starter-mcp-client</artifactId>
</dependency>
```

### Server Setup

```xml
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-starter-mcp-server-webmvc</artifactId>
</dependency>
```

### Server Annotations

> Annotations (`@McpTool`, `@McpResource`, `@McpPrompt`) are provided by `spring-ai-mcp-annotations` artifact — included transitively by the server starters.

```java
@McpTool          // Expose tools to MCP clients
@McpResource      // Expose resources via URI-based access
@McpPrompt        // Provide prompt templates
```

### Transport Options

| Transport            | Use Case                        | Property                                   |
| -------------------- | ------------------------------- | ------------------------------------------ |
| STDIO                | Local process communication     | `spring.ai.mcp.server.stdio=true`          |
| SSE                  | Server-Sent Events over HTTP    | `spring.ai.mcp.server.protocol=SSE`        |
| Streamable-HTTP      | Bidirectional HTTP streaming    | `spring.ai.mcp.server.protocol=STREAMABLE` |
| Stateless Streamable | Stateless HTTP without sessions | `spring.ai.mcp.server.protocol=STATELESS`  |

### MCP Rules

- Use `spring-ai-starter-mcp-client` for consuming external MCP servers
- Use `spring-ai-starter-mcp-server-webmvc` or `webflux` for exposing tools as MCP server
- Annotate tool methods with `@McpTool` for automatic discovery
- Choose transport based on deployment: STDIO for local, SSE/Streamable-HTTP for remote

---

## 8. Multi-Model Routing

### ChatModel Abstraction

Spring AI provides a unified `ChatModel` interface across all providers, enabling model-agnostic code.

### Multiple Model Configuration

```java
@Configuration
public class MultiModelConfig {

    @Bean
    @Qualifier("fast")
    public ChatClient fastClient(OpenAiChatModel openAiModel) {
        return ChatClient.builder(openAiModel)
            .defaultOptions(OpenAiChatOptions.builder()
                .model("gpt-5-mini")
                .temperature(0.3)
                .build())
            .build();
    }

    @Bean
    @Qualifier("powerful")
    public ChatClient powerfulClient(AnthropicChatModel anthropicModel) {
        return ChatClient.builder(anthropicModel)
            .defaultOptions(AnthropicChatOptions.builder()
                .model("claude-sonnet-4-5-20250929")
                .build())
            .build();
    }
}
```

### Routing Pattern

```java
@Service
public class ModelRouter {
    private final ChatClient fastClient;
    private final ChatClient powerfulClient;

    public ChatClient route(String taskType) {
        return switch (taskType) {
            case "summarize", "classify" -> fastClient;
            case "analyze", "generate" -> powerfulClient;
            default -> fastClient;
        };
    }
}
```

### Routing Rules

- Use `@Qualifier` to distinguish multiple `ChatClient` beans
- Configure model-specific options via provider `ChatOptions` (e.g., `OpenAiChatOptions`)
- Route based on task complexity — use cheaper/faster models for simple tasks
- Use `ChatModel.mutate()` for runtime model switching with OpenAI-compatible endpoints

---

## 9. Agent Building Patterns

### ReAct Agent with Tool Loop

```java
ChatClient agentClient = ChatClient.builder(chatModel)
    .defaultSystem("""
        You are a helpful assistant. Use the provided tools to answer questions.
        Think step by step before answering.
        """)
    .defaultTools(new SearchTools(), new CalculatorTools())
    .build();

String result = agentClient.prompt()
    .user(userQuestion)
    .call()
    .content();
```

### Agent with Memory and RAG

```java
ChatClient agentClient = ChatClient.builder(chatModel)
    .defaultAdvisors(
        MessageChatMemoryAdvisor.builder(chatMemory).build(),
        RetrievalAugmentationAdvisor.builder()
            .documentRetriever(VectorStoreDocumentRetriever.builder()
                .vectorStore(vectorStore)
                .similarityThreshold(0.6)
                .build())
            .build()
    )
    .defaultTools(new CustomerTools())
    .build();
```

### Agent Building Rules

- Combine advisors (memory + RAG) with tools for capable agents
- Use `MessageChatMemoryAdvisor` for multi-turn conversations
- Pass conversation ID via `.advisors(a -> a.param(ChatMemory.CONVERSATION_ID, id))`
- Keep tool descriptions clear and specific — vague descriptions cause incorrect tool selection
- Monitor token usage — agents with many tools and long memory consume more tokens

---

## 10. Error Handling and Cost Optimization

### Error Handling

```java
// Configure retry behavior
// application.yml
spring:
  ai:
    retry:
      max-attempts: 3
      backoff:
        initial-interval: 1000
        multiplier: 2.0
        max-interval: 10000

// Tool execution error handling
@Bean
ToolExecutionExceptionProcessor toolErrorProcessor() {
    return exception -> "Tool execution failed: " + exception.getMessage();
}
```

### Cost Optimization Rules

- Use structured output (`.entity()`) to reduce unnecessary tokens in responses
- Set appropriate `maxTokens` in `ChatOptions` to cap response length
- Use cheaper models for simple tasks (classification, summarization)
- Cache frequently asked questions and their responses
- Use `similarityThreshold` in RAG to avoid sending irrelevant context
- Monitor token usage via `ChatResponse.getMetadata().getUsage()`
- Use streaming (`.stream()`) for better user experience, not for cost savings — token count is the same

### Anti-Patterns

- Creating a new `ChatClient` per request — build once, reuse the instance
- Using expensive models for simple classification tasks — route by complexity
- Setting `similarityThreshold` to 0.0 in production — floods context with irrelevant documents
- Ignoring retry configuration — API calls fail without proper retry/backoff
- Hardcoding API keys — use `spring.ai.<provider>.api-key` from environment variables
- Returning JPA entities from `@Tool` methods — use simple DTOs or Strings
- Blocking the event loop with tool calls in WebFlux — tool calling is inherently blocking
- Using setter-style `ChatOptions` (e.g., `new AnthropicChatOptions()`) — use builder pattern in 2.x
- Relying on default temperature — must be explicitly configured in 2.x

---

## Related Skills

- `security`: Secure handling of API keys, prompt injection defense, and output sanitization
- `error-handling`: Error classification and retry patterns for LLM API calls
- `caching`: Caching strategies for LLM responses and vector store results

## Additional References

- For ChatClient fluent API, streaming, and structured output patterns, see [references/chatclient-patterns.md](references/chatclient-patterns.md)
- For @Tool annotation usage, ToolCallback interface, and migration patterns, see [references/tool-calling.md](references/tool-calling.md)
- For vector store patterns, supported databases, and basic RAG implementation, see [references/vector-store-rag.md](references/vector-store-rag.md)
- For advanced RAG (query rewriting, hybrid search, reranking, agentic RAG), agent frameworks, and model evaluation, see [references/advanced-rag-agents.md](references/advanced-rag-agents.md)
- For migration from Spring AI 1.x to 2.x, see [references/migration-2x.md](references/migration-2x.md)
