# Advanced RAG Patterns and Agent Frameworks

## 1. Advanced RAG Patterns

### RAG Architecture Overview

```text
Basic RAG:
  Query → Embed → Vector Store → Retrieve → LLM → Response

Advanced RAG:
  Query → Transform → Embed → Retrieve → Rerank → Compress → LLM → Response
         │              │          │          │          │
    Query Rewrite  Multi-Vector  Hybrid    Cross-Encoder Context
    Decompose      Store        Search    Reranker   Compress
```

### Query Transformation

#### Query Rewriting

```java
// Use RewriteQueryTransformer for better retrieval
ChatClient ragClient = ChatClient.builder(chatModel)
    .defaultAdvisors(
        RetrievalAugmentationAdvisor.builder()
            .documentRetriever(VectorStoreDocumentRetriever.builder()
                .vectorStore(vectorStore)
                .similarityThreshold(0.6)
                .topK(10)
                .build())
            .queryTransformer(RewriteQueryTransformer.builder()
                .chatClientBuilder(ChatClient.builder(chatModel))
                .build())
            .build())
    .build();
```

#### Query Decomposition

```java
// Split complex queries into sub-queries
@Component
public class QueryDecompositionService {
    private final ChatClient chatClient;

    public List<String> decompose(String complexQuery) {
        return chatClient.prompt()
            .system("""
                Decompose the following question into 2-4 simpler sub-questions.
                Return each sub-question on a separate line.
                Do not include numbering or bullets.
                """)
            .user(complexQuery)
            .call()
            .content()
            .lines()
            .filter(line -> !line.isBlank())
            .toList();
    }
}
```

### Hybrid Search

Combine vector similarity with keyword (BM25) search for better recall.

```java
@Configuration
public class HybridSearchConfig {

    @Bean
    public DocumentRetriever hybridRetriever(VectorStore vectorStore) {
        return VectorStoreDocumentRetriever.builder()
            .vectorStore(vectorStore)
            .similarityThreshold(0.5)
            .topK(10)
            .build();
        // Note: For full hybrid search (vector + BM25), use a
        // vector store that supports hybrid queries (e.g., Elasticsearch,
        // Weaviate, Pinecone with sparse vectors, Milvus hybrid search)
    }
}
```

### Reranking

```java
// Apply cross-encoder reranking after initial retrieval
@Bean
public DocumentRetriever rerankingRetriever(VectorStore vectorStore) {
    return VectorStoreDocumentRetriever.builder()
        .vectorStore(vectorStore)
        .similarityThreshold(0.4)  // Lower threshold for initial broad retrieval
        .topK(20)                  // Retrieve more candidates
        .build();
}

// Then use a custom advisor that reranks results
@Component
public class RerankingAdvisor implements CallAdvisor {
    @Override
    public AdvisedResponse adviseCall(AdvisedRequest request, CallAdvisorChain chain) {
        // After retrieval, rerank using a cross-encoder model
        // and pass only top-K results to the LLM
        List<Document> retrieved = getRetrievedDocuments(request);
        List<Document> reranked = reranker.rerank(retrieved, request.userText(), 5);
        // Inject reranked context into prompt
        // ...
    }
}
```

### Context Compression

Reduce noise by compressing retrieved documents before injecting into the prompt.

```java
// Use CompressionQueryTransformer to compress retrieved context
@Bean
public RetrievalAugmentationAdvisor ragAdvisor(VectorStore vectorStore, ChatModel chatModel) {
    return RetrievalAugmentationAdvisor.builder()
        .documentRetriever(VectorStoreDocumentRetriever.builder()
            .vectorStore(vectorStore)
            .similarityThreshold(0.5)
            .topK(10)
            .build())
        .queryTransformer(CompressionQueryTransformer.builder()
            .chatClientBuilder(ChatClient.builder(chatModel))
            .build())
        .build();
}
```

### Multi-Modal RAG

```java
// RAG with multimodal content (text + images)
Document multimodalDoc = new Document(
    "This diagram shows the system architecture...",
    Map.of(
        "type", "image",
        "source", "classpath:docs/architecture.png"
    )
);
vectorStore.add(List.of(multimodalDoc));

// Retrieve and include image content in prompt
List<Document> results = vectorStore.similaritySearch(
    SearchRequest.builder()
        .query("system architecture")
        .topK(3)
        .build()
);
```

### Agentic RAG (Self-Correcting)

```java
// RAG agent that evaluates answer quality and retries
@Service
public class AgenticRagService {
    private final ChatClient chatClient;
    private final VectorStore vectorStore;

    public String query(String userQuery) {
        int maxRetries = 3;

        for (int attempt = 0; attempt < maxRetries; attempt++) {
            String answer = chatClient.prompt()
                .system("""
                    You are a helpful assistant.
                    If the provided context does not contain enough information,
                    say "I need more context" and suggest what information is missing.
                    """)
                .user(userQuery)
                .advisors(RetrievalAugmentationAdvisor.builder()
                    .documentRetriever(VectorStoreDocumentRetriever.builder()
                        .vectorStore(vectorStore)
                        .similarityThreshold(0.4 + (attempt * 0.1))  // Broaden search each retry
                        .topK(5 + (attempt * 5))  // Retrieve more each retry
                        .build())
                    .build())
                .call()
                .content();

            if (!answer.contains("I need more context")) {
                return answer;
            }
        }

        return "Unable to find sufficient information to answer your question.";
    }
}
```

### RAG Pattern Selection Guide

| Pattern | Use Case | Complexity | Recall Improvement |
| --- | --- | --- | --- |
| Basic RAG | Simple Q&A over documents | Low | Baseline |
| Query Rewriting | Ambiguous user queries | Medium | +15-25% |
| Query Decomposition | Complex multi-faceted questions | Medium | +20-30% |
| Hybrid Search | Keyword + semantic matching | Medium | +10-20% |
| Reranking | High precision required | High | +15-30% |
| Context Compression | Long documents, token limits | Medium | +10-15% (noise reduction) |
| Agentic RAG | Self-correcting, iterative retrieval | High | +25-40% |

---

## 2. Agent Frameworks

### Agent Architecture Patterns

```text
Simple Tool-Using Agent:
  User → ChatClient → LLM → Tool Call → Result → LLM → Response

ReAct Agent (Reason + Act):
  User → LLM → Think → Act (Tool) → Observe → Think → Act → ... → Response

Multi-Agent System:
  User → Router Agent → Specialist Agent A → Result → Synthesizer → Response
                      → Specialist Agent B →
```

### Tool Calling Best Practices

#### Tool Description Rules

- **Be specific about when to use**: Not "gets data" but "retrieves customer order history from the database given a customer ID"
- **Include parameter constraints**: Not "a date" but "date in ISO 8601 format (YYYY-MM-DD)"
- **Document return format**: Describe what the tool returns so the LLM can interpret it correctly
- **Avoid overlapping tools**: Two tools with similar descriptions confuse the model

#### Tool Context Pattern

```java
@Component
public class OrderTools {
    private final OrderService orderService;
    private final TenantContext tenantContext;

    @Tool(description = "Retrieve order history for the current customer. Returns a list of orders with ID, date, status, and total amount.")
    public List<OrderSummary> getOrderHistory(
        @ToolParam(description = "Maximum number of orders to return, default 10", required = false) Integer limit
    ) {
        // Use ToolContext to pass tenant/customer info without exposing to LLM
        String tenantId = tenantContext.getCurrentTenantId();
        String customerId = tenantContext.getCurrentCustomerId();

        return orderService.getOrderHistory(tenantId, customerId, limit != null ? limit : 10);
    }

    @Tool(description = "Get detailed information about a specific order including line items and shipping address")
    public OrderDetail getOrderDetail(
        @ToolParam(description = "The order ID to look up, e.g., 'ORD-12345'") String orderId
    ) {
        String tenantId = tenantContext.getCurrentTenantId();
        return orderService.getOrderDetail(tenantId, orderId);
    }
}
```

#### Tool Return Types

```java
// GOOD: Return simple DTOs (not JPA entities)
public record OrderSummary(String orderId, LocalDate date, String status, BigDecimal total) {}

// BAD: Returning JPA entities (exposes internal structure, may trigger lazy loading)
@Tool(description = "Get orders")
public List<OrderEntity> getOrders() { ... } // Never do this

// Return strings for simple results
@Tool(description = "Check if a product is in stock")
public String checkStock(@ToolParam(description = "Product SKU") String sku) {
    return inventoryService.isInStock(sku) ? "In stock" : "Out of stock";
}

// Use returnDirect for pass-through responses
@Tool(description = "Get current weather for a city", returnDirect = true)
public String getWeather(@ToolParam(description = "City name") String city) {
    // The tool result goes directly to the user without LLM processing
    return weatherService.getCurrentWeather(city);
}
```

### Multi-Agent Patterns

#### Router Agent

```java
@Service
public class RouterAgent {
    private final ChatClient customerAgent;
    private final ChatClient technicalAgent;
    private final ChatClient billingAgent;
    private final ChatClient routerClient;

    public String handleRequest(String userQuery) {
        String routing = routerClient.prompt()
            .system("""
                Classify the user query into one of: customer, technical, billing.
                Return only the category name.
                """)
            .user(userQuery)
            .call()
            .content()
            .trim()
            .toLowerCase();

        return switch (routing) {
            case "customer" -> customerAgent.prompt().user(userQuery).call().content();
            case "technical" -> technicalAgent.prompt().user(userQuery).call().content();
            case "billing" -> billingAgent.prompt().user(userQuery).call().content();
            default -> customerAgent.prompt().user(userQuery).call().content();
        };
    }
}
```

#### Agent with Human-in-the-Loop

```java
@Service
public class HumanInTheLoopAgent {
    private final ChatClient chatClient;
    private final ApprovalService approvalService;

    public String processOrder(String orderDetails) {
        String analysis = chatClient.prompt()
            .system("You are an order processing assistant. Analyze the order and decide if it requires human approval.")
            .user(orderDetails)
            .call()
            .content();

        if (analysis.contains("REQUIRES_APPROVAL")) {
            // Pause execution, request human approval
            String approvalId = approvalService.requestApproval(orderDetails, analysis);
            return "Order requires human approval. Approval request ID: " + approvalId;
        }

        // Auto-process low-risk orders
        return processApprovedOrder(orderDetails);
    }
}
```

### Agent Memory Patterns

```java
// Short-term: Conversation memory (within a session)
ChatClient clientWithMemory = ChatClient.builder(chatModel)
    .defaultAdvisors(
        MessageChatMemoryAdvisor.builder(chatMemory).build()
    )
    .build();

// Medium-term: Vector store memory (across sessions)
ChatClient clientWithSemanticMemory = ChatClient.builder(chatModel)
    .defaultAdvisors(
        VectorStoreChatMemoryAdvisor.builder(vectorStore)
            .similarityThreshold(0.7)
            .topK(5)
            .build()
    )
    .build();

// Long-term: Structured storage (persistent facts)
ChatClient clientWithStructuredMemory = ChatClient.builder(chatModel)
    .defaultTools(new UserPreferenceTools(preferenceRepository))
    .defaultSystem("""
        You have access to user preferences and history.
        Use the tools to save and retrieve user preferences.
        Always check preferences before making recommendations.
        """)
    .build();
```

### Agent Guardrails

```java
// Input guardrail: Validate user input before processing
@Component
public class InputGuardrailAdvisor implements CallAdvisor {
    private static final int MAX_INPUT_LENGTH = 4000;
    private static final List<String> BLOCKED_PATTERNS = List.of(
        "ignore previous instructions",
        "system prompt",
        "jailbreak"
    );

    @Override
    public AdvisedResponse adviseCall(AdvisedRequest request, CallAdvisorChain chain) {
        String userText = request.userText();

        if (userText.length() > MAX_INPUT_LENGTH) {
            throw new IllegalArgumentException("Input exceeds maximum length");
        }

        for (String pattern : BLOCKED_PATTERNS) {
            if (userText.toLowerCase().contains(pattern)) {
                throw new SecurityException("Potentially harmful input detected");
            }
        }

        return chain.nextCall(request);
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;  // Run first
    }
}

// Output guardrail: Validate LLM response before returning
@Component
public class OutputGuardrailAdvisor implements CallAdvisor {
    @Override
    public AdvisedResponse adviseCall(AdvisedRequest request, CallAdvisorChain chain) {
        AdvisedResponse response = chain.nextCall(request);

        String content = response.response().getResult().getOutput().getText();
        if (containsSensitiveInfo(content)) {
            return AdvisedResponse.from(response)
                .withContent("[REDACTED - sensitive information detected]")
                .build();
        }

        return response;
    }

    private boolean containsSensitiveInfo(String content) {
        // Check for PII, internal URLs, API keys, etc.
        return content.matches(".*\\b\\d{3}-\\d{2}-\\d{4}\\b.*") // SSN pattern
            || content.contains("internal.company.com")
            || content.matches(".*\\b[A-Za-z0-9]{32,}\\b.*"); // Likely API key
    }

    @Override
    public int getOrder() {
        return Ordered.LOWEST_PRECEDENCE;  // Run last
    }
}
```

---

## 3. Model Evaluation and Observability

### Evaluation Framework

```java
@Component
public class ModelEvaluator {
    private final ChatClient judgeClient;

    public EvaluationResult evaluate(String query, String response, String expectedAnswer) {
        String evaluation = judgeClient.prompt()
            .system("""
                Evaluate the AI response on these criteria:
                1. Relevance (1-5): Does the response address the query?
                2. Accuracy (1-5): Is the information correct?
                3. Completeness (1-5): Does it cover all aspects?
                4. Clarity (1-5): Is it clear and well-structured?
                Return JSON: {"relevance": N, "accuracy": N, "completeness": N, "clarity": N, "reasoning": "..."}
                """)
            .user("""
                Query: %s
                Response: %s
                Expected: %s
                """.formatted(query, response, expectedAnswer))
            .call()
            .entity(EvaluationResult.class);

        return evaluation;
    }
}

public record EvaluationResult(
    int relevance,
    int accuracy,
    int completeness,
    int clarity,
    String reasoning
) {}
```

### Token Usage Monitoring

```java
@Component
public class TokenMonitoringAdvisor implements CallAdvisor {
    private final MeterRegistry registry;

    @Override
    public AdvisedResponse adviseCall(AdvisedRequest request, CallAdvisorChain chain) {
        AdvisedResponse response = chain.nextCall(request);

        Usage usage = response.response().getMetadata().getUsage();
        registry.counter("ai.tokens.total",
            "model", request.modelName()
        ).increment(usage.getTotalTokens().intValue());

        registry.counter("ai.tokens.prompt",
            "model", request.modelName()
        ).increment(usage.getPromptTokens().intValue());

        registry.counter("ai.tokens.completion",
            "model", request.modelName()
        ).increment(usage.getCompletionTokens().intValue());

        return response;
    }

    @Override
    public int getOrder() {
        return Ordered.LOWEST_PRECEDENCE - 1;  // After logging, before output guardrail
    }
}
```

### Cost Dashboard Metrics

```promql
# Token usage by model
sum by (model) (rate(ai_tokens_total[5m]))

# Cost estimation (approximate)
sum by (model) (rate(ai_tokens_prompt[1h])) * 0.00003   # Input cost per token
+ sum by (model) (rate(ai_tokens_completion[1h])) * 0.00006  # Output cost per token

# Error rate by model
sum by (model) (rate(ai_request_errors_total[5m]))
/
sum by (model) (rate(ai_requests_total[5m]))

# Average response time
histogram_quantile(0.95, sum by (le, model) (rate(ai_request_duration_seconds_bucket[5m])))
```

---

## 4. Anti-Patterns

- **Retrieving too many documents**: Sending 50 documents to the LLM wastes tokens and increases hallucination risk — start with 5, max 20
- **Not setting similarityThreshold**: Default 0.0 accepts irrelevant documents — always set 0.5-0.8 threshold
- **Using the same model for embedding and generation**: Embedding models optimize for retrieval, generation models for quality — use specialized models for each
- **Ignoring context window limits**: RAG context + prompt + response must fit in the model's context window — count tokens and truncate if needed
- **No guardrails on agent systems**: Agents with tools can perform arbitrary actions — always add input/output validation
- **Returning JPA entities from tools**: Entity lazy-loading fails outside transaction context — use simple DTOs or Strings
- **Hardcoding prompts in code**: Long system prompts should be in resource files for maintainability
- **Not monitoring token usage**: Agents with many tools consume tokens rapidly — monitor and set limits
- **Single model for all tasks**: Use smaller models for classification/summarization and larger models for reasoning/creative tasks
- **No fallback on model failure**: Always implement retry logic and fallback to alternative models
