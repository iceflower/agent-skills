# OTel SDK Patterns by Language

Detailed setup and usage patterns for OpenTelemetry SDKs.

## Java

### Zero-Code (Java Agent)

```bash
java -javaagent:opentelemetry-javaagent.jar \
     -Dotel.service.name=my-service \
     -Dotel.exporter.otlp.endpoint=http://collector:4317 \
     -jar my-app.jar
```

Environment variable configuration:

```bash
OTEL_SERVICE_NAME=my-service
OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4317
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1  # 10% sampling
OTEL_METRICS_EXPORTER=otlp
OTEL_LOGS_EXPORTER=otlp
```

### Spring Boot Starter (Boot 4.0+)

```yaml
# application.yml
spring:
  application:
    name: my-service
management:
  otlp:
    tracing:
      endpoint: http://collector:4318/v1/traces
    metrics:
      export:
        endpoint: http://collector:4318/v1/metrics
  tracing:
    sampling:
      probability: 0.1
```

### Manual Instrumentation (Java)

```java
import io.opentelemetry.api.GlobalOpenTelemetry;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.Tracer;

@Service
public class OrderService {
    private static final Tracer tracer =
        GlobalOpenTelemetry.getTracer("com.example.orders");

    public Order processOrder(OrderRequest request) {
        Span span = tracer.spanBuilder("processOrder")
            .setAttribute("order.type", request.getType())
            .startSpan();
        try (var scope = span.makeCurrent()) {
            // Business logic
            Order order = createOrder(request);
            span.setAttribute("order.id", order.getId());
            return order;
        } catch (Exception e) {
            span.setStatus(StatusCode.ERROR);
            span.recordException(e);
            throw e;
        } finally {
            span.end();
        }
    }
}
```

### Metrics (Java)

```java
import io.opentelemetry.api.metrics.LongCounter;
import io.opentelemetry.api.metrics.Meter;

@Component
public class OrderMetrics {
    private final LongCounter orderCounter;
    private final LongHistogram orderDuration;

    public OrderMetrics() {
        Meter meter = GlobalOpenTelemetry.getMeter("com.example.orders");
        orderCounter = meter.counterBuilder("orders.created")
            .setDescription("Number of orders created")
            .setUnit("{order}")
            .build();
        orderDuration = meter.histogramBuilder("orders.duration")
            .setDescription("Order processing duration")
            .setUnit("ms")
            .ofLongs()
            .build();
    }

    public void recordOrderCreated(String type) {
        orderCounter.add(1, Attributes.of(AttributeKey.stringKey("order.type"), type));
    }

    public void recordDuration(long durationMs) {
        orderDuration.record(durationMs);
    }
}
```

## Node.js

### SDK Setup

```typescript
import { NodeSDK } from "@opentelemetry/sdk-node";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-grpc";
import { OTLPMetricExporter } from "@opentelemetry/exporter-metrics-otlp-grpc";
import { PeriodicExportingMetricReader } from "@opentelemetry/sdk-metrics";
import { getNodeAutoInstrumentations } from "@opentelemetry/auto-instrumentations-node";
import { ATTR_SERVICE_NAME } from "@opentelemetry/semantic-conventions";
import { resourceFromAttributes } from "@opentelemetry/resources";

const sdk = new NodeSDK({
  resource: resourceFromAttributes({
    [ATTR_SERVICE_NAME]: "my-service",
  }),
  traceExporter: new OTLPTraceExporter({
    url: "http://collector:4317",
  }),
  metricReader: new PeriodicExportingMetricReader({
    exporter: new OTLPMetricExporter({
      url: "http://collector:4317",
    }),
    exportIntervalMillis: 60000,
  }),
  instrumentations: [getNodeAutoInstrumentations()],
});

sdk.start();
process.on("SIGTERM", () => sdk.shutdown());
```

### Manual Spans (Node.js)

```typescript
import { trace, SpanStatusCode } from "@opentelemetry/api";

const tracer = trace.getTracer("order-service");

async function processOrder(request: OrderRequest): Promise<Order> {
  return tracer.startActiveSpan("processOrder", async (span) => {
    try {
      span.setAttribute("order.type", request.type);
      const order = await createOrder(request);
      span.setAttribute("order.id", order.id);
      return order;
    } catch (error) {
      span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
      span.recordException(error);
      throw error;
    } finally {
      span.end();
    }
  });
}
```

### Metrics (Node.js)

```typescript
import { metrics } from "@opentelemetry/api";

const meter = metrics.getMeter("order-service");

const orderCounter = meter.createCounter("orders.created", {
  description: "Number of orders created",
  unit: "{order}",
});

const orderDuration = meter.createHistogram("orders.duration", {
  description: "Order processing duration",
  unit: "ms",
});

function recordOrder(type: string, durationMs: number) {
  orderCounter.add(1, { "order.type": type });
  orderDuration.record(durationMs);
}
```

## Python

### Python SDK Setup

```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

resource = Resource.create({SERVICE_NAME: "my-service"})

# Traces
tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://collector:4317"))
)
trace.set_tracer_provider(tracer_provider)

# Metrics
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="http://collector:4317"),
    export_interval_millis=60000,
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
```

### Zero-Code (Python)

```bash
pip install opentelemetry-distro opentelemetry-exporter-otlp
opentelemetry-bootstrap -a install  # Install auto-instrumentation packages

OTEL_SERVICE_NAME=my-service \
OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4317 \
opentelemetry-instrument python app.py
```

### Manual Spans (Python)

```python
tracer = trace.get_tracer("order-service")

# Context manager (preferred)
def process_order(request):
    with tracer.start_as_current_span("processOrder") as span:
        span.set_attribute("order.type", request.type)
        try:
            order = create_order(request)
            span.set_attribute("order.id", order.id)
            return order
        except Exception as e:
            span.set_status(StatusCode.ERROR, str(e))
            span.record_exception(e)
            raise

# Decorator
@tracer.start_as_current_span("validate_order")
def validate_order(request):
    pass
```

## Resources

- [OTel Java](https://opentelemetry.io/docs/languages/java/)
- [OTel Node.js](https://opentelemetry.io/docs/languages/js/)
- [OTel Python](https://opentelemetry.io/docs/languages/python/)
- [Spring Boot Starter](https://opentelemetry.io/docs/zero-code/java/spring-boot-starter/)
