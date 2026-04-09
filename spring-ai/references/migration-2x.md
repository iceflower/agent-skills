# Migration Guide: Spring AI 1.x → 2.x

## Platform Requirements

| Component | 1.x | 2.x |
|-----------|-----|-----|
| Spring Boot | 3.x | **4.0+** (Spring Framework 7.0) |
| JDK | 17+ | 17+ (JDK 25 LTS recommended) |
| Jackson | **Jackson 2** (`com.fasterxml.jackson`) | **Jackson 3** (`tools.jackson`) |
| Spring AI BOM | `1.1.x` | `2.0.0-M4+` |

---

## 1. FunctionCallback → ToolCallback API

### API Mapping

| 1.x (Deprecated) | 2.x (Current) |
|-----------------|---------------|
| `FunctionCallback` | `ToolCallback` |
| `FunctionCallback.builder().function()` | `FunctionToolCallback.builder()` |
| `FunctionCallback.builder().method()` | `MethodToolCallback.builder()` |
| `FunctionCallingOptions` | `ToolCallingChatOptions` |
| `ChatClient.builder().defaultFunctions()` | `ChatClient.builder().defaultTools()` |
| `ChatClient.functions()` | `ChatClient.tools()` |
| `FunctionCallingOptions.builder().functions()` | `ToolCallingChatOptions.builder().toolNames()` |
| `FunctionCallingOptions.builder().functionCallbacks()` | `ToolCallingChatOptions.builder().toolCallbacks()` |

### Example Migration

```java
// Before (1.x)
FunctionCallback weatherCallback = FunctionCallback.builder()
    .function("getCurrentWeather", new WeatherService())
    .build();

chatClient.prompt()
    .functionCallbacks(weatherCallback)
    .call()
    .content();

// After (2.x)
ToolCallback weatherCallback = FunctionToolCallback
    .builder("getCurrentWeather", new WeatherService())
    .description("Get current weather for a city")
    .inputType(WeatherRequest.class)
    .build();

chatClient.prompt()
    .tools(weatherCallback)
    .call()
    .content();
```

---

## 2. MCP Annotations Package Relocation

### Package Change

```java
// Before (1.x) — external community library
import org.springaicommunity.mcp.annotation.McpTool;
import org.springaicommunity.mcp.annotation.McpToolParam;
import org.springaicommunity.mcp.annotation.McpProgressToken;

// After (2.x) — Spring AI core module
import org.springframework.ai.mcp.annotation.McpTool;
import org.springframework.ai.mcp.annotation.McpToolParam;
import org.springframework.ai.mcp.annotation.McpProgressToken;
```

### Dependency Change

```xml
<!-- Before (1.x) -->
<dependency>
    <groupId>org.springaicommunity</groupId>
    <artifactId>mcp-annotations</artifactId>
</dependency>

<!-- After (2.x) -->
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-mcp-annotations</artifactId>
</dependency>
```

### Transport Module Relocation

- Maven Group ID: `io.modelcontextprotocol.sdk` → `org.springframework.ai`
- Package: `io.modelcontextprotocol.server.transport` → `org.springframework.ai.mcp.server.webmvc.transport`
- Using Spring Boot starters (`spring-ai-starter-mcp-server*`) handles this automatically.

---

## 3. Jackson 2 → Jackson 3

Spring AI 2.x uses Jackson 3, aligned with Spring Boot 4.0.

### Import Changes

```java
// Before (Jackson 2)
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.annotation.JsonProperty;

// After (Jackson 3)
import tools.jackson.databind.ObjectMapper;
import tools.jackson.annotation.JsonProperty;
```

### Impact Areas

- Custom `@Tool` method return types with Jackson annotations
- Structured output entity classes with Jackson annotations
- Custom JSON serializers/deserializers
- `ObjectMapper` beans (may need explicit Jackson 3 configuration)

---

## 4. Default Temperature Removed

Spring AI 2.x no longer provides a default `temperature` value.

```yaml
# Before (1.x) — temperature defaulted to 0.7
spring:
  ai:
    openai:
      chat:
        options:
          # temperature not set — defaulted to 0.7

# After (2.x) — must be explicit
spring:
  ai:
    openai:
      chat:
        options:
          temperature: 0.7  # required if you want non-provider-default
```

---

## 5. ChatOptions Builder Pattern

All provider ChatOptions now require builder pattern in 2.x.

```java
// Before (1.x) — setter style (removed in 2.x)
AnthropicChatOptions options = new AnthropicChatOptions();
options.setTemperature(0.7);
options.setModel("claude-3-sonnet-20240229");

// After (2.x) — builder only
AnthropicChatOptions options = AnthropicChatOptions.builder()
    .temperature(0.7)
    .model("claude-sonnet-4-5-20250929")
    .build();
```

Affected classes: `AnthropicChatOptions`, `AzureOpenAiChatOptions`, `BedrockChatOptions`, `DeepSeekChatOptions`, `MistralAiChatOptions`, `MiniMaxChatOptions`.

---

## 6. Renamed Methods

### ChatClient

```java
// Before (1.x)
chatClient.disableMemory()

// After (2.x)
chatClient.disableInternalConversationHistory()
```

The old method is provided as a deprecated shim for backward compatibility.

---

## 7. Model Changes

### OpenAI Default Model

- 1.x: Previous default
- 2.x: **`gpt-5-mini`**

### Claude 3 Models Removed

The following Claude 3 models are **no longer available**:
- `claude-3-opus-*`
- `claude-3-sonnet-*`
- `claude-3-haiku-*`

**Migration**: Use Claude 4.x models:
- `claude-sonnet-4-5-20250929`
- `claude-opus-4-1-20250805`

### Deprecated Provider Integrations

The following are deprecated and will be removed in a future release:
- Vertex AI
- OCI GenAI
- ZhiPu AI

---

## 8. Anthropic SDK Integration

Spring AI 2.x switches from RestClient-based implementation to the official Anthropic Java SDK. Review custom Anthropic configurations.

---

## 9. Automated Migration (OpenRewrite)

```bash
mvn org.openrewrite.maven:rewrite-maven-plugin:6.32.0:run \
  -Drewrite.recipeArtifactCoordinates=org.springframework.ai:spring-ai-rewrite-recipes:2.0.0-M3 \
  -Drewrite.activeRecipes=org.springframework.ai.migrate.To2_0_0_M3
```

---

## Migration Checklist

- [ ] Update Spring Boot to 4.0+
- [ ] Update Spring AI BOM to 2.0.0-M4+
- [ ] Migrate `FunctionCallback` → `ToolCallback` API
- [ ] Update MCP annotation imports (`org.springframework.ai.mcp.annotation`)
- [ ] Update Jackson imports (`tools.jackson`)
- [ ] Set explicit `temperature` in all ChatOptions
- [ ] Convert ChatOptions to builder pattern
- [ ] Replace `disableMemory()` → `disableInternalConversationHistory()`
- [ ] Update Claude 3 models → Claude 4.x
- [ ] Review Anthropic SDK integration changes
- [ ] Run OpenRewrite migration recipe
- [ ] Verify tool calling behavior with new ToolCallback API
- [ ] Test structured output with Jackson 3 entity classes
