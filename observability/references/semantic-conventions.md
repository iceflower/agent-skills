# OTel Semantic Conventions Reference

Standard attribute names for consistent telemetry across services and tools.
Based on [OTel Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/).

## Resource Attributes

| Attribute | Example | Description |
| --- | --- | --- |
| `service.name` | `order-service` | Logical name of the service |
| `service.version` | `1.2.3` | Service version |
| `service.namespace` | `production` | Service namespace |
| `deployment.environment.name` | `production` | Deployment environment |
| `host.name` | `server-01` | Hostname |
| `container.id` | `abc123...` | Container ID |
| `k8s.pod.name` | `order-service-xyz` | Kubernetes pod name |
| `k8s.namespace.name` | `default` | Kubernetes namespace |
| `cloud.provider` | `aws`, `gcp`, `azure` | Cloud provider |
| `cloud.region` | `us-east-1` | Cloud region |

## HTTP (Client and Server)

### Common

| Attribute | Example | Required |
| --- | --- | --- |
| `http.request.method` | `GET`, `POST` | Yes |
| `http.response.status_code` | `200`, `500` | Yes (when available) |
| `url.scheme` | `https` | Yes |
| `url.path` | `/api/users/42` | Recommended |
| `http.route` | `/api/users/{id}` | Recommended (server) |
| `network.protocol.version` | `1.1`, `2`, `3` | Recommended |
| `http.request.body.size` | `1024` | Optional |
| `http.response.body.size` | `2048` | Optional |
| `user_agent.original` | `Mozilla/5.0...` | Optional |

### Server-Specific

| Attribute | Example | Description |
| --- | --- | --- |
| `server.address` | `api.example.com` | Server hostname |
| `server.port` | `443` | Server port |
| `client.address` | `192.168.1.100` | Client IP |

### Span Naming

- HTTP server: `{method} {http.route}` → `GET /api/users/{id}`
- HTTP client: `{method}` → `GET` (avoid including full URL)

## Database

| Attribute | Example | Required |
| --- | --- | --- |
| `db.system` | `postgresql`, `mysql`, `redis`, `mongodb` | Yes |
| `db.operation.name` | `SELECT`, `INSERT`, `findAndModify` | Recommended |
| `db.collection.name` | `users`, `orders` | Recommended |
| `db.namespace` | `mydb` | Recommended |
| `db.query.text` | `SELECT * FROM users WHERE id = ?` | Opt-in (may contain PII) |
| `server.address` | `db.example.com` | Recommended |
| `server.port` | `5432` | Recommended |

### Span Naming

- `{db.operation.name} {db.collection.name}` → `SELECT users`
- If collection unknown: `{db.operation.name}` → `SELECT`

**Security**: `db.query.text` is opt-in because it may contain sensitive data.
Sanitize or redact before enabling in production.

## Messaging

| Attribute | Example | Required |
| --- | --- | --- |
| `messaging.system` | `kafka`, `rabbitmq`, `activemq` | Yes |
| `messaging.operation.type` | `publish`, `receive`, `process` | Yes |
| `messaging.destination.name` | `orders-topic` | Recommended |
| `messaging.message.id` | `msg-123` | Recommended |
| `messaging.consumer.group.name` | `order-processors` | Recommended |
| `messaging.kafka.offset` | `42` | Kafka-specific |

### Span Naming

- `{destination} {operation}` → `orders-topic publish`

## RPC (gRPC)

| Attribute | Example | Required |
| --- | --- | --- |
| `rpc.system` | `grpc` | Yes |
| `rpc.service` | `mypackage.MyService` | Recommended |
| `rpc.method` | `GetUser` | Recommended |
| `rpc.grpc.status_code` | `0` (OK), `2` (UNKNOWN) | Yes |

### Span Naming

- `{rpc.service}/{rpc.method}` → `mypackage.MyService/GetUser`

## Error Conventions

| Attribute | Example | Description |
| --- | --- | --- |
| `error.type` | `java.lang.NullPointerException` | Error class name |
| `exception.type` | `ValueError` | Exception type |
| `exception.message` | `Invalid input` | Exception message |
| `exception.stacktrace` | `...` | Full stack trace |

Record exceptions as span events:

```java
span.recordException(exception);
span.setStatus(StatusCode.ERROR, "Processing failed");
```

## Metric Naming Conventions

| Rule | Example |
| --- | --- |
| Use dots as separators | `http.server.request.duration` |
| Use lowercase | `db.client.operation.duration` |
| Include unit in name | `http.server.request.body.size` |
| Use standard units | `s` (seconds), `By` (bytes), `{request}` (count) |

### Standard Metrics

| Metric | Type | Unit |
| --- | --- | --- |
| `http.server.request.duration` | Histogram | `s` |
| `http.server.active_requests` | UpDownCounter | `{request}` |
| `db.client.operation.duration` | Histogram | `s` |
| `messaging.process.duration` | Histogram | `s` |
| `rpc.server.duration` | Histogram | `s` |

## Resources

- [Semantic Conventions Spec](https://opentelemetry.io/docs/specs/semconv/)
- [HTTP Conventions](https://opentelemetry.io/docs/specs/semconv/http/)
- [Database Conventions](https://opentelemetry.io/docs/specs/semconv/database/)
- [Messaging Conventions](https://opentelemetry.io/docs/specs/semconv/messaging/)
- [RPC Conventions](https://opentelemetry.io/docs/specs/semconv/rpc/)
