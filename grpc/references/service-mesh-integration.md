# Service Mesh Integration (Istio / Envoy)

## Service Mesh Benefits for gRPC

| Feature            | Without Mesh                    | With Service Mesh              |
| ------------------ | ------------------------------- | ------------------------------ |
| Load Balancing     | Client-side LB code required    | Automatic L7 balancing         |
| mTLS               | Manual certificate management   | Automatic certificate rotation |
| Retries            | Application-level configuration | Mesh-level policy              |
| Circuit Breaking   | Resilience4j or similar library | Envoy configuration            |
| Observability      | Manual instrumentation          | Automatic metrics and tracing  |
| Traffic Management | Custom routing logic            | VirtualService rules           |

## Istio Configuration for gRPC

```yaml
# DestinationRule — circuit breaking and connection pool
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: order-service
spec:
  host: order-service
  trafficPolicy:
    connectionPool:
      http:
        h2UpgradePolicy: UPGRADE  # Force HTTP/2 for gRPC
        maxRequestsPerConnection: 100
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

```yaml
# VirtualService — traffic routing and retries
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-service
spec:
  hosts:
    - order-service
  http:
    - route:
        - destination:
            host: order-service
            port:
              number: 50051
      retries:
        attempts: 3
        perTryTimeout: 2s
        retryOn: cancelled,deadline-exceeded,unavailable
      timeout: 10s
```

## Service Mesh Integration Rules

- Use `h2UpgradePolicy: UPGRADE` in DestinationRule to ensure HTTP/2 for gRPC traffic
- Delegate mTLS, retries, and circuit breaking to the mesh when available — avoid duplicating in application code
- When using mesh-level retries, disable application-level retries to prevent retry amplification
- Configure `outlierDetection` for automatic ejection of unhealthy endpoints
- Use Istio `VirtualService` for canary deployments, traffic splitting, and fault injection
- Ensure gRPC health checking is configured — Envoy uses it for endpoint health status
- Use `grpc_health_v1.Health` service for standardized health checks

## gRPC Health Checking

```kotlin
// Implement standard gRPC health check service
@GrpcService
class HealthService : HealthGrpc.HealthImplBase() {

    override fun check(
        request: HealthCheckRequest,
        responseObserver: StreamObserver<HealthCheckResponse>
    ) {
        val response = HealthCheckResponse.newBuilder()
            .setStatus(HealthCheckResponse.ServingStatus.SERVING)
            .build()
        responseObserver.onNext(response)
        responseObserver.onCompleted()
    }

    override fun watch(
        request: HealthCheckRequest,
        responseObserver: StreamObserver<HealthCheckResponse>
    ) {
        // Stream health status updates
        val response = HealthCheckResponse.newBuilder()
            .setStatus(HealthCheckResponse.ServingStatus.SERVING)
            .build()
        responseObserver.onNext(response)
        // Keep stream open for updates
    }
}
```
