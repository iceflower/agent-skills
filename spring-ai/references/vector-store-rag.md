# Vector Store and RAG

## Vector Store API

### Core Interfaces

```java
// Read-only retrieval
@FunctionalInterface
public interface VectorStoreRetriever {
    List<Document> similaritySearch(SearchRequest request);

    default List<Document> similaritySearch(String query) {
        return similaritySearch(SearchRequest.builder().query(query).build());
    }
}

// Full read/write operations
public interface VectorStore extends DocumentWriter, VectorStoreRetriever {
    void add(List<Document> documents);
    void delete(List<String> idList);
    void delete(Filter.Expression filterExpression);
    default void delete(String filterExpression) { ... }
}
```

### Document Class

```java
Document document = new Document(
    "Document content text",
    Map.of("country", "Korea", "year", "2024", "topic", "spring-ai")
);

vectorStore.add(List.of(document));
```

### SearchRequest Builder

```java
SearchRequest request = SearchRequest.builder()
    .query("How does Spring AI work?")
    .topK(5)                            // Default: 4
    .similarityThreshold(0.7)           // Default: 0.0 (accept all)
    .filterExpression("topic == 'spring-ai'")
    .build();

List<Document> results = vectorStore.similaritySearch(request);
```

### Delete Operations

```java
// By document IDs
vectorStore.delete(List.of(document.getId()));

// By filter expression object
Filter.Expression filter = new Filter.Expression(
    Filter.ExpressionType.EQ,
    new Filter.Key("country"),
    new Filter.Value("Korea")
);
vectorStore.delete(filter);

// By filter string
vectorStore.delete("country == 'Korea'");
```

Enhanced `IN` and `NIN` (not-in) filter expression grouping is available in 2.x.

## Metadata Filtering

Spring AI 2.x adds JSpecify `@NonNull`/`@Nullable` annotations to most vector store implementations for compile-time null safety.

### String Syntax (SQL-like)

```java
"country == 'Korea'"
"genre == 'drama' && year >= 2020"
"genre in ['comedy', 'documentary', 'drama']"
"country == 'Korea' AND version == '1.0'"
```

### FilterExpressionBuilder (Programmatic)

```java
FilterExpressionBuilder b = new FilterExpressionBuilder();

// Comparison operators: ==, !=, >, >=, <, <=
Expression exp = b.eq("country", "Korea").build();

// Logical operators: AND, OR
Expression exp = b.and(
    b.eq("genre", "drama"),
    b.gte("year", 2020)
).build();

// IN operator
Expression exp = b.in("genre", "drama", "documentary").build();

// NOT operator
Expression exp = b.not(b.lt("year", 2020)).build();

// NULL operators
Expression exp = b.isNull("year").build();
Expression exp = b.isNotNull("year").build();
```

### Null Value Filters (2.x)

Spring AI 2.x adds `ISNULL` and `ISNOTNULL` filter expressions:

```java
// ISNULL filter
Expression exp = b.isNull("category").build();

// ISNOTNULL filter
Expression exp = b.isNotNull("category").build();
```

## Supported Vector Databases

| Database                       | Artifact                            |
| ------------------------------ | ----------------------------------- |
| Amazon Bedrock Knowledge Base  | `spring-ai-bedrock-kb-store`        |
| Amazon S3                      | `spring-ai-amazon-s3-store`         |
| Apache Cassandra               | `spring-ai-cassandra-store`         |
| Azure Vector Search            | `spring-ai-azure-store`             |
| Chroma                         | `spring-ai-chroma-store`            |
| Elasticsearch                  | `spring-ai-elasticsearch-store`     |
| Infinispan                     | `spring-ai-infinispan-store`        |
| Milvus                         | `spring-ai-milvus-store`            |
| MongoDB Atlas                  | `spring-ai-mongodb-atlas-store`     |
| Neo4j                          | `spring-ai-neo4j-store`             |
| OpenSearch                     | `spring-ai-opensearch-store`        |
| PGVector (PostgreSQL)          | `spring-ai-pgvector-store`          |
| Pinecone                       | `spring-ai-pinecone-store`          |
| Qdrant                         | `spring-ai-qdrant-store`            |
| Redis                          | `spring-ai-redis-store`             |
| Weaviate                       | `spring-ai-weaviate-store`          |
| SimpleVectorStore              | `spring-ai-core` (in-memory)        |

## Batching Strategy

```java
@Bean
public BatchingStrategy batchingStrategy() {
    return new TokenCountBatchingStrategy(
        EncodingType.CL100K_BASE,  // Encoding type
        8000,                      // Max input tokens
        0.1                        // Reserve percentage (10%)
    );
}
```

## Document Ingestion

```java
@Service
public class DocumentIngestionService {
    private final VectorStore vectorStore;

    public void ingestDocuments(Resource resource) {
        // Read from JSON
        JsonReader jsonReader = new JsonReader(
            resource,
            "price", "name", "shortDescription"
        );
        List<Document> documents = jsonReader.get();
        vectorStore.add(documents);
    }
}
```

---

## RAG (Retrieval Augmented Generation)

### QuestionAnswerAdvisor (Simple RAG)

Dependency:

```xml
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-advisors-vector-store</artifactId>
</dependency>
```

Basic usage:

```java
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

Dynamic filter expressions at request time:

```java
String answer = chatClient.prompt()
    .user("Tell me about Spring AI")
    .advisors(a -> a.param(
        QuestionAnswerAdvisor.FILTER_EXPRESSION,
        "type == 'documentation'"))
    .call()
    .content();
```

Custom prompt template:

```java
PromptTemplate customTemplate = PromptTemplate.builder()
    .renderer(StTemplateRenderer.builder()
        .startDelimiterToken('<')
        .endDelimiterToken('>')
        .build())
    .template("""
        <query>
        Context information is below.
        ---------------------
        <question_answer_context>
        ---------------------
        Given the context information and no prior knowledge, answer the query.
        """)
    .build();

QuestionAnswerAdvisor qaAdvisor = QuestionAnswerAdvisor.builder(vectorStore)
    .promptTemplate(customTemplate)
    .build();
```

Required template placeholders: `query`, `question_answer_context`.

### RetrievalAugmentationAdvisor (Advanced RAG)

Dependency:

```xml
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-rag</artifactId>
</dependency>
```

#### Naive RAG

```java
Advisor ragAdvisor = RetrievalAugmentationAdvisor.builder()
    .documentRetriever(VectorStoreDocumentRetriever.builder()
        .vectorStore(vectorStore)
        .similarityThreshold(0.5)
        .build())
    .build();

String answer = chatClient.prompt()
    .advisors(ragAdvisor)
    .user("What is Spring AI?")
    .call()
    .content();
```

#### Advanced RAG with Query Transformation

```java
Advisor ragAdvisor = RetrievalAugmentationAdvisor.builder()
    .queryTransformers(
        RewriteQueryTransformer.builder()
            .chatClientBuilder(chatClientBuilder)
            .build())
    .documentRetriever(VectorStoreDocumentRetriever.builder()
        .vectorStore(vectorStore)
        .similarityThreshold(0.5)
        .build())
    .build();
```

> Inject `ChatClient.Builder chatClientBuilder` via Spring DI. Do not call `.build().mutate()` — pass the builder directly.

#### Allow Empty Context

```java
Advisor ragAdvisor = RetrievalAugmentationAdvisor.builder()
    .documentRetriever(VectorStoreDocumentRetriever.builder()
        .vectorStore(vectorStore)
        .similarityThreshold(0.5)
        .build())
    .queryAugmenter(ContextualQueryAugmenter.builder()
        .allowEmptyContext(true)
        .build())
    .build();
```

### VectorStoreDocumentRetriever

```java
DocumentRetriever retriever = VectorStoreDocumentRetriever.builder()
    .vectorStore(vectorStore)
    .similarityThreshold(0.73)
    .topK(5)
    .filterExpression(new FilterExpressionBuilder()
        .eq("genre", "documentation")
        .build())
    .build();

List<Document> documents = retriever.retrieve(new Query("What is Spring AI?"));
```

Dynamic filter with supplier (e.g., multi-tenant):

```java
DocumentRetriever retriever = VectorStoreDocumentRetriever.builder()
    .vectorStore(vectorStore)
    .filterExpression(() -> new FilterExpressionBuilder()
        .eq("tenant", TenantContextHolder.getTenantIdentifier())
        .build())
    .build();
```

## Query Transformation Modules

### CompressionQueryTransformer

Compresses conversation history into a standalone query.

```java
// Inject ChatClient.Builder via Spring DI
QueryTransformer transformer = CompressionQueryTransformer.builder()
    .chatClientBuilder(chatClientBuilder)
    .build();
```

### RewriteQueryTransformer

Rewrites verbose or ambiguous queries for better retrieval.

```java
QueryTransformer transformer = RewriteQueryTransformer.builder()
    .chatClientBuilder(chatClientBuilder)
    .build();
```

### TranslationQueryTransformer

Translates queries to a target language (matching the embedding model language).

```java
QueryTransformer transformer = TranslationQueryTransformer.builder()
    .chatClientBuilder(chatClientBuilder)
    .targetLanguage("english")
    .build();
```

### MultiQueryExpander

Expands a single query into multiple semantically diverse variants.

```java
MultiQueryExpander expander = MultiQueryExpander.builder()
    .chatClientBuilder(chatClientBuilder)
    .numberOfQueries(3)
    .includeOriginal(true)
    .build();
```

> All transformers accept `ChatClient.Builder` — inject it via Spring DI. Do not pre-build the `ChatClient`.

## Query Augmentation

### ContextualQueryAugmenter

Augments the user query with retrieved document context before sending to the model.

```java
QueryAugmenter augmenter = ContextualQueryAugmenter.builder()
    .allowEmptyContext(false)  // Default: disallow empty context
    .build();
```

## Best Practices

- Set `similarityThreshold` to 0.5-0.8 in production — 0.0 returns irrelevant results
- Use `topK` of 3-10 depending on context window size and cost constraints
- Use metadata filtering for multi-tenant isolation
- Use `CompressionQueryTransformer` for multi-turn conversations to produce standalone queries
- Use `RewriteQueryTransformer` when user queries are verbose or ambiguous
- Monitor retrieval quality — poor retrieval leads to hallucinated answers regardless of model quality
- Use low temperature (0.0) for query transformation to get deterministic results
