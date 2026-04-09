# Tool/Function Calling

## @Tool Annotation

### Basic Usage

```java
class DateTimeTools {

    @Tool(description = "Get the current date and time in the user's timezone")
    String getCurrentDateTime() {
        return LocalDateTime.now()
            .atZone(LocaleContextHolder.getTimeZone().toZoneId())
            .toString();
    }

    @Tool(description = "Set a user alarm for the given time")
    void setAlarm(
        @ToolParam(description = "Time in ISO-8601 format") String time
    ) {
        LocalDateTime alarmTime = LocalDateTime.parse(time, DateTimeFormatter.ISO_DATE_TIME);
        alarmService.schedule(alarmTime);
    }
}
```

### @Tool Attributes

| Attribute         | Default     | Description                                          |
| ----------------- | ----------- | ---------------------------------------------------- |
| `name`            | method name | Tool identifier used by the model                    |
| `description`     | `""`        | How/when to call the tool (critical for model)       |
| `returnDirect`    | `false`     | Return result directly to caller, not to model       |
| `resultConverter` | default     | Custom `ToolCallResultConverter` implementation      |

### @ToolParam Attributes

| Attribute     | Default  | Description                        |
| ------------- | -------- | ---------------------------------- |
| `description` | `""`     | Parameter usage description        |
| `required`    | `true`   | Whether parameter is mandatory     |

Alternative annotations for parameter metadata: `@Nullable`, Jackson's `@JsonProperty`, Swagger's `@Schema`.

## Registering Tools with ChatClient

### Direct Tool Object

```java
ChatClient.create(chatModel)
    .prompt("What day is tomorrow?")
    .tools(new DateTimeTools())
    .call()
    .content();
```

### Default Tools (Builder)

```java
ChatClient chatClient = ChatClient.builder(chatModel)
    .defaultTools(new DateTimeTools(), new WeatherTools())
    .build();
```

### Tool Callbacks (Programmatic)

```java
ToolCallback[] callbacks = ToolCallbacks.from(new DateTimeTools());

ChatClient.create(chatModel)
    .prompt("What day is tomorrow?")
    .toolCallbacks(callbacks)
    .call()
    .content();
```

### Tool Names (Dynamic Resolution from Beans)

```java
@Configuration
class ToolConfig {
    @Bean("currentWeather")
    @Description("Get the weather in a location")
    Function<WeatherRequest, WeatherResponse> currentWeather() {
        return request -> weatherService.getWeather(request);
    }
}

// Resolve by bean name
ChatClient.create(chatModel)
    .prompt("What's the weather in Seoul?")
    .toolNames("currentWeather")
    .call()
    .content();
```

## ToolCallback Interface

```java
public interface ToolCallback {
    ToolDefinition getToolDefinition();
    ToolMetadata getToolMetadata();
    String call(String toolInput);
    String call(String toolInput, ToolContext toolContext);
}
```

### Built-in Implementations

| Implementation          | Source                                                |
| ----------------------- | ----------------------------------------------------- |
| `MethodToolCallback`    | From `@Tool` annotated methods                        |
| `FunctionToolCallback`  | From `Function`, `Supplier`, `Consumer`, `BiFunction` |

### FunctionToolCallback Builder

```java
ToolCallback toolCallback = FunctionToolCallback
    .builder("currentWeather", new WeatherService())
    .description("Get the weather in a location")
    .inputType(WeatherRequest.class)
    .build();
```

## Tool Context

Pass application-level context to tools without exposing it to the model.

```java
class CustomerTools {

    @Tool(description = "Retrieve customer information")
    Customer getCustomerInfo(
        Long id,
        ToolContext toolContext
    ) {
        String tenantId = (String) toolContext.getContext().get("tenantId");
        return customerRepository.findByIdAndTenant(id, tenantId);
    }
}

// Pass context at call time
chatClient.prompt()
    .tools(new CustomerTools())
    .toolContext(Map.of("tenantId", "acme"))
    .user("Tell me about customer 42")
    .call()
    .content();
```

## Return Direct

When `returnDirect = true`, the tool result goes directly to the caller instead of being sent back to the model for further processing.

```java
class CustomerTools {

    @Tool(description = "Retrieve customer info", returnDirect = true)
    Customer getCustomerInfo(Long id) {
        return customerRepository.findById(id);
    }
}
```

## Tool Execution Approaches

### Framework-Controlled (Default)

The framework automatically executes tool calls and feeds results back to the model.

```java
// Default behavior — no special configuration needed
chatClient.prompt()
    .tools(new MyTools())
    .user("What's the weather?")
    .call()
    .content();
```

### Advisor-Controlled

```java
var toolCallAdvisor = ToolCallAdvisor.builder()
    .toolCallingManager(toolCallingManager)
    .advisorOrder(BaseAdvisor.HIGHEST_PRECEDENCE + 300)
    .build();

ChatClient chatClient = ChatClient.builder(chatModel)
    .defaultAdvisors(toolCallAdvisor)
    .build();
```

### User-Controlled (Manual Loop)

```java
ToolCallingChatOptions options = ToolCallingChatOptions.builder()
    .toolCallbacks(toolCallbacks)
    .internalToolExecutionEnabled(false)
    .build();

Prompt prompt = new Prompt("Your question", options);
ChatResponse response = chatModel.call(prompt);

while (response.hasToolCalls()) {
    ToolExecutionResult result = toolCallingManager.executeToolCalls(prompt, response);
    prompt = new Prompt(result.conversationHistory(), options);
    response = chatModel.call(prompt);
}
```

## Tool Argument Augmentation

Capture additional model reasoning without modifying tool signatures.

```java
public record AgentThinking(
    @ToolParam(description = "Your reasoning for calling this tool", required = true)
    String innerThought,
    @ToolParam(description = "Confidence level", required = false)
    String confidence
) {}

AugmentedToolCallbackProvider<AgentThinking> provider =
    AugmentedToolCallbackProvider.<AgentThinking>builder()
        .toolObject(new MyTools())
        .argumentType(AgentThinking.class)
        .argumentConsumer(event -> {
            log.info("Tool: {} | Reasoning: {}",
                event.toolDefinition().name(),
                event.arguments().innerThought());
        })
        .removeExtraArgumentsAfterProcessing(true)
        .build();

ChatClient chatClient = ChatClient.builder(chatModel)
    .defaultToolCallbacks(provider)
    .build();
```

## Error Handling

### Global Exception Processor

```java
@Bean
ToolExecutionExceptionProcessor toolErrorProcessor() {
    // Return error message to model (default behavior)
    return new DefaultToolExecutionExceptionProcessor(false);
}

// Or throw exceptions to halt processing
@Bean
ToolExecutionExceptionProcessor toolErrorProcessor() {
    return new DefaultToolExecutionExceptionProcessor(true);
}
```

Property: `spring.ai.tools.throw-exception-on-error` (default: `false`)

## MCP Tool Annotations

> Spring AI 2.x integrates MCP (Model Context Protocol) annotations as a core module.
> Artifact: `org.springframework.ai:spring-ai-mcp-annotations`

### @McpTool

Expose methods as MCP tools. Use in conjunction with or instead of `@Tool` when building MCP servers.

```java
@Component
public class MyMcpTools {

    @McpTool(
        name = "get_customer",
        description = "Retrieve customer information by ID",
        annotations = @McpTool.Annotations(
            readOnlyHint = true,
            destructiveHint = false,
            openWorldHint = true
        )
    )
    public String getCustomer(
        @McpToolParam(description = "Customer ID", required = true) String customerId
    ) {
        return customerService.findById(customerId);
    }
}
```

### @McpTool.Annotations Attributes

| Attribute | Default | Description |
|-----------|---------|-------------|
| `readOnlyHint` | `false` | Whether the tool is read-only (no side effects) |
| `destructiveHint` | `true` | Whether the tool may perform destructive operations |
| `openWorldHint` | `true` | Whether the tool operates in an open world (unknown state space) |

### @McpToolParam

Parameter descriptions for MCP tools — equivalent to `@ToolParam` but for MCP context.

```java
@McpToolParam(description = "City name for weather lookup", required = false) String city
```

### @McpProgressToken

Enable progress notifications for long-running MCP tools.

```java
@McpTool(name = "process_document", description = "Process a large document with progress tracking")
public String processDocument(
    @McpToolParam(description = "Document file path") String filePath,
    McpSyncServerExchange exchange,
    @McpProgressToken Object progressToken
) {
    // Create progress notifier
    ProgressNotifier notifier = createProgressNotifier(exchange, progressToken);

    for (int i = 0; i < totalPages; i++) {
        processPage(i);
        notifier.notify(i + 1, totalPages, "Processing page " + (i + 1));
    }

    return "Document processed successfully";
}

private ProgressNotifier createProgressNotifier(McpSyncServerExchange exchange, Object progressToken) {
    if (progressToken == null) {
        return (current, total, message) -> {}; // no-op
    }
    return (current, total, message) -> exchange.progressNotification(
        new ProgressNotification(progressToken, (double) current, (double) total, message)
    );
}

@FunctionalInterface
interface ProgressNotifier {
    void notify(int current, int total, String message);
}
```

### MCP Server Dependencies

| Role | Artifact |
|------|----------|
| MCP Server (STDIO) | `spring-ai-starter-mcp-server` |
| MCP Server (WebMVC) | `spring-ai-starter-mcp-server-webmvc` |
| MCP Server (WebFlux) | `spring-ai-starter-mcp-server-webflux` |
| MCP Client | `spring-ai-starter-mcp-client` |
| MCP Annotations only | `spring-ai-mcp-annotations` |

### MCP Server Configuration

```yaml
spring:
  ai:
    mcp:
      server:
        name: my-mcp-server
        version: 1.0.0
        type: SYNC        # SYNC or ASYNC
        protocol: STDIO   # STDIO, SSE, or STREAMABLE
```

### MCP Client Customization (2.x)

```java
@Configuration
class McpClientConfig {
    @Bean
    McpClientCustomizer<McpAsyncClient.Builder> mcpClientCustomizer() {
        return builder -> builder
            .toolCallbacks(additionalToolCallbacks)
            // Customize client behavior
            .build();
    }
}
```

### MCP Tool Annotations Rules

- Use `@McpTool` for tools exposed via MCP server — not for internal tool calling
- `@Tool` and `@McpTool` serve different purposes: `@Tool` for ChatClient tool calling, `@McpTool` for MCP server tool exposure
- Always provide meaningful `description` — MCP clients use it for tool discovery
- Use `@McpTool.Annotations` hints to help MCP clients optimize tool usage
- `@McpProgressToken` requires `McpSyncServerExchange` parameter in the method signature
- Progress notifications are optional — guard against null `progressToken`

## Key Interfaces

### ToolDefinition

```java
public interface ToolDefinition {
    String name();
    String description();
    String inputSchema(); // JSON Schema
}
```

### ToolCallingManager

```java
public interface ToolCallingManager {
    List<ToolDefinition> resolveToolDefinitions(ToolCallingChatOptions options);
    ToolExecutionResult executeToolCalls(Prompt prompt, ChatResponse response);
}
```

### ToolCallbackResolver Implementations

| Resolver                         | Purpose                                   |
| -------------------------------- | ----------------------------------------- |
| `SpringBeanToolCallbackResolver` | Resolves Function/Supplier/Consumer beans |
| `StaticToolCallbackResolver`     | From static ToolCallback lists            |
| `DelegatingToolCallbackResolver` | Delegates to multiple resolvers           |

## Utility Classes

| Class                    | Purpose                                        |
| ------------------------ | ---------------------------------------------- |
| `ToolCallbacks`          | Generate `ToolCallback[]` from `@Tool` objects |
| `ToolDefinitions`        | Build `ToolDefinition` from methods            |
| `JsonSchemaGenerator`    | Auto-generate JSON schemas from signatures     |
| `ToolCallingChatOptions` | Configure tool calling behavior                |

## Limitations

Method-based tools do NOT support:

- `Optional`, `CompletableFuture`, `Future`
- Reactive types (`Mono`, `Flux`, `Flow`)
- Functional types (use function approach instead)

Function-based tools do NOT support:

- Primitive types
- `Optional`, collections, async/reactive types
