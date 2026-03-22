# ChatClient Patterns

## ChatClient Creation

### Auto-configured Builder (Recommended)

```java
@RestController
class ChatController {
    private final ChatClient chatClient;

    public ChatController(ChatClient.Builder builder) {
        this.chatClient = builder
            .defaultSystem("You are a helpful assistant.")
            .defaultAdvisors(new SimpleLoggerAdvisor())
            .build();
    }
}
```

### Programmatic Creation

```java
ChatModel chatModel = ...; // auto-configured by Spring Boot

// Simple
ChatClient chatClient = ChatClient.create(chatModel);

// With builder
ChatClient chatClient = ChatClient.builder(chatModel)
    .defaultSystem("You are a helpful assistant.")
    .defaultOptions(OpenAiChatOptions.builder()
        .model("gpt-4o")
        .temperature(0.7)
        .build())
    .build();
```

## Fluent API Reference

### Prompt Initialization

```java
chatClient.prompt()                     // Empty prompt
chatClient.prompt("User message")       // Shorthand for user message
chatClient.prompt(new Prompt(messages)) // From Prompt object
```

### Message Building

```java
// System message
.system("You are a helpful assistant")
.system(new ClassPathResource("prompts/system.st"))
.system(s -> s.text("Act as a {role}").param("role", "teacher"))

// User message
.user("Tell me a joke")
.user(new ClassPathResource("prompts/user.st"))
.user(u -> u
    .text("Tell me about {topic}")
    .param("topic", "Spring AI"))
```

### Message Metadata

```java
.user(u -> u
    .text("What is the weather?")
    .metadata("messageId", "msg-123")
    .metadata("userId", "user-456"))

.system(s -> s
    .text("You are helpful")
    .metadata("version", "1.0"))
```

Metadata rules:

- Keys cannot be null or empty
- Values cannot be null
- Map entries cannot contain null elements

### Options and Advisors

```java
.options(OpenAiChatOptions.builder()
    .model("gpt-4o")
    .temperature(0.5)
    .build())

.advisors(
    MessageChatMemoryAdvisor.builder(chatMemory).build(),
    new SimpleLoggerAdvisor())

.advisors(a -> a.param(ChatMemory.CONVERSATION_ID, "session-123"))
```

### Tools

```java
.tools(new DateTimeTools())                        // Tool object
.toolCallbacks(ToolCallbacks.from(new MyTools()))   // ToolCallback array
.toolNames("currentWeather")                        // Resolve by bean name
.toolContext(Map.of("tenantId", "acme"))             // Tool context
```

## Response Handling

### Synchronous Responses

```java
// String content
String content = chatClient.prompt()
    .user("Tell me a joke")
    .call()
    .content();

// Full ChatResponse
ChatResponse response = chatClient.prompt()
    .user("Tell me a joke")
    .call()
    .chatResponse();

// ChatClientResponse (includes advisor context)
ChatClientResponse clientResponse = chatClient.prompt()
    .user("Tell me a joke")
    .call()
    .chatClientResponse();
```

### Structured Output (Entity Mapping)

```java
record ActorFilms(String actor, List<String> movies) {}

// Single entity
ActorFilms films = chatClient.prompt()
    .user("Generate filmography for Tom Hanks")
    .call()
    .entity(ActorFilms.class);

// Generic types
List<ActorFilms> filmsList = chatClient.prompt()
    .user("Generate filmographies for 3 actors")
    .call()
    .entity(new ParameterizedTypeReference<List<ActorFilms>>() {});

// With native structured output support
ActorFilms films = chatClient.prompt()
    .advisors(AdvisorParams.ENABLE_NATIVE_STRUCTURED_OUTPUT)
    .user("Generate filmography for Tom Hanks")
    .call()
    .entity(ActorFilms.class);

// Entity with ChatResponse metadata
ResponseEntity<ActorFilms> responseEntity = chatClient.prompt()
    .user("Generate filmography for Tom Hanks")
    .call()
    .responseEntity(ActorFilms.class);
```

### Streaming Responses

```java
// Stream string content
Flux<String> contentStream = chatClient.prompt()
    .user("Write a long story")
    .stream()
    .content();

// Stream ChatResponse
Flux<ChatResponse> responseStream = chatClient.prompt()
    .user("Write a long story")
    .stream()
    .chatResponse();
```

Streaming requirements:

- Requires `spring-boot-starter-webflux` dependency
- Tool calling within streaming is still blocking
- Advisors perform non-blocking operations for streaming

## Builder Default Configuration

```java
ChatClient chatClient = ChatClient.builder(chatModel)
    .defaultSystem("You are a {role}")
    .defaultUser("Default user context")

    .defaultOptions(ChatOptions.builder()
        .model("gpt-4o")
        .temperature(0.7)
        .build())

    .defaultAdvisors(
        MessageChatMemoryAdvisor.builder(chatMemory).build(),
        new SimpleLoggerAdvisor())

    .defaultTools(new DateTimeTools())
    .defaultToolCallbacks(ToolCallbacks.from(new MyTools()))
    .defaultFunctions("currentWeather")
    .build();

// Runtime override
chatClient.prompt()
    .system(s -> s.param("role", "pirate"))
    .user("Tell me a joke")
    .call()
    .content();
```

## Multiple ChatClients for Different Models

```java
@Configuration
public class ChatClientConfig {

    @Bean
    @Qualifier("openai")
    public ChatClient openAiChatClient(OpenAiChatModel chatModel) {
        return ChatClient.builder(chatModel)
            .defaultOptions(OpenAiChatOptions.builder()
                .model("gpt-4o")
                .build())
            .build();
    }

    @Bean
    @Qualifier("anthropic")
    public ChatClient anthropicChatClient(AnthropicChatModel chatModel) {
        return ChatClient.builder(chatModel)
            .defaultOptions(AnthropicChatOptions.builder()
                .model("claude-sonnet-4-20250514")
                .build())
            .build();
    }
}

// Inject with qualifier
@RestController
class MyController {
    public MyController(
        @Qualifier("openai") ChatClient openAiClient,
        @Qualifier("anthropic") ChatClient anthropicClient
    ) { ... }
}
```

## OpenAI-Compatible Endpoints

```java
// Mutate API for different providers with OpenAI-compatible API
OpenAiApi groqApi = baseOpenAiApi.mutate()
    .baseUrl("https://api.groq.com/openai")
    .apiKey(System.getenv("GROQ_API_KEY"))
    .build();

OpenAiChatModel groqModel = baseChatModel.mutate()
    .openAiApi(groqApi)
    .defaultOptions(OpenAiChatOptions.builder()
        .model("llama3-70b-8192")
        .temperature(0.5)
        .build())
    .build();

ChatClient groqClient = ChatClient.create(groqModel);
```

## Template Renderer Customization

```java
// Custom delimiters (e.g., <placeholder> instead of {placeholder})
chatClient.prompt()
    .templateRenderer(StTemplateRenderer.builder()
        .startDelimiterToken('<')
        .endDelimiterToken('>')
        .build())
    .user(u -> u.text("Tell me about <topic>").param("topic", "AI"))
    .call()
    .content();
```

## Logging

```java
// Add SimpleLoggerAdvisor
ChatClient chatClient = ChatClient.builder(chatModel)
    .defaultAdvisors(new SimpleLoggerAdvisor())
    .build();

// Configure log level in application.yml
// logging.level.org.springframework.ai.chat.client.advisor=DEBUG
```

## Important Notes

- **Bug workaround**: Set `spring.http.client.factory=jdk` for Spring Boot 3.4+
- **Thread safety**: `ChatClient` instances are thread-safe and should be reused
- **Streaming stack**: Streaming requires WebFlux; non-streaming requires Servlet stack
- **Tool calling**: Always blocking, even within streaming responses
