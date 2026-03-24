# Network Communication Patterns

3 patterns for efficient network communication in distributed systems.

---

## Pattern 28: Single-Socket Channel

Maintain single connection for ordering.

**Benefits**:

- Preserves request order
- Simple flow control
- No reordering logic needed

**Implementation**:

```java
class SingleSocketChannel {
    private final Socket socket;
    private final Object lock = new Object();

    public Response sendRequest(Request request) {
        synchronized (lock) {
            socket.write(request.serialize());
            return Response.deserialize(socket.read());
        }
    }
}
```

---

## Pattern 29: Batched Requests

Send multiple requests in single message.

```java
class BatchedRequest {
    private final List<Request> requests = new ArrayList<>();

    public void add(Request request) {
        requests.add(request);
        if (requests.size() >= BATCH_SIZE) {
            flush();
        }
    }

    public List<Response> flush() {
        if (requests.isEmpty()) return Collections.emptyList();

        List<Response> responses = sendBatch(requests);
        requests.clear();
        return responses;
    }
}
```

**Trade-offs**:

- Lower network overhead
- Higher throughput
- Higher latency per request

---

## Pattern 30: Request Pipeline

Send multiple requests without waiting for responses.

```text
Client                                    Server
   │───────────Request 1───────────────────▶│
   │───────────Request 2───────────────────▶│
   │◀──────────Response 1──────────────────│
   │───────────Request 3───────────────────▶│
   │◀──────────Response 2──────────────────│
   │◀──────────Response 3──────────────────│
```

**Pipeline Depth**: Max concurrent in-flight requests.
