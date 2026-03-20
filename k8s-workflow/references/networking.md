# Kubernetes Networking

## 1. Service Types

| Type | Exposure | Use Case | Access Pattern |
| --- | --- | --- | --- |
| ClusterIP | Internal only | Service-to-service | `svc-name.namespace.svc.cluster.local` |
| NodePort | External via node IP | Development, debugging | `<NodeIP>:<NodePort>` |
| LoadBalancer | External via cloud LB | Simple external access | Cloud-provisioned LB IP |
| ExternalName | DNS alias | External service reference | CNAME to external DNS |

### Rules

- Default to `ClusterIP` — expose externally only through Ingress or Gateway
- Never use `NodePort` in production — use Ingress + ClusterIP instead
- `LoadBalancer` creates one cloud LB per Service — use Ingress to share a single LB
- Use `ExternalName` for referencing external services without hardcoding URLs

---

## 2. Ingress

### Basic Ingress Resource

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - myapp.example.com
      secretName: myapp-tls
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: myapp-api
                port:
                  number: 8080
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp-frontend
                port:
                  number: 80
```

### Common Annotations by Controller

| Annotation | nginx | ALB (AWS) |
| --- | --- | --- |
| SSL redirect | `nginx.ingress.kubernetes.io/ssl-redirect` | `alb.ingress.kubernetes.io/ssl-redirect` |
| Body size limit | `nginx.ingress.kubernetes.io/proxy-body-size` | N/A |
| Rate limiting | `nginx.ingress.kubernetes.io/limit-rps` | N/A |
| Health check | `nginx.ingress.kubernetes.io/health-check-path` | `alb.ingress.kubernetes.io/healthcheck-path` |
| WAF | N/A | `alb.ingress.kubernetes.io/wafv2-acl-arn` |

---

## 3. Gateway API

### Gateway API vs Ingress

| Feature | Ingress | Gateway API |
| --- | --- | --- |
| API maturity | Stable (v1) | Stable (v1 for core) |
| Role separation | Single resource | Gateway (infra) + Route (app) |
| Protocol support | HTTP/HTTPS | HTTP, gRPC, TCP, TLS |
| Header manipulation | Via annotations | Native |
| Traffic splitting | Via annotations | Native |
| Cross-namespace | Limited | Built-in |

### Gateway + HTTPRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: main-gateway
  namespace: infra
spec:
  gatewayClassName: istio
  listeners:
    - name: https
      protocol: HTTPS
      port: 443
      tls:
        mode: Terminate
        certificateRefs:
          - name: wildcard-tls
      allowedRoutes:
        namespaces:
          from: Selector
          selector:
            matchLabels:
              gateway-access: "true"
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: myapp-route
  namespace: myapp
spec:
  parentRefs:
    - name: main-gateway
      namespace: infra
  hostnames:
    - myapp.example.com
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /api
      backendRefs:
        - name: myapp-api
          port: 8080
```

---

## 4. Network Policies

### Default Deny All

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: myapp
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

### Allow Specific Traffic

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-traffic
  namespace: myapp
spec:
  podSelector:
    matchLabels:
      app: myapp-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
        - podSelector:
            matchLabels:
              app: myapp-frontend
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: myapp-db
      ports:
        - protocol: TCP
          port: 5432
    - to:  # Allow DNS
        - namespaceSelector: {}
      ports:
        - protocol: UDP
          port: 53
```

### Network Policy Rules

- Start with default deny, then whitelist needed traffic
- Always allow DNS (port 53 UDP) in egress policies
- Use namespace selectors for cross-namespace communication
- Test policies in non-production first — misconfigured policies break connectivity

---

## 5. DNS and Service Discovery

### CoreDNS Resolution

```text
Service DNS:     <service>.<namespace>.svc.cluster.local
Pod DNS:         <pod-ip-dashed>.<namespace>.pod.cluster.local
Headless Service: <pod-name>.<service>.<namespace>.svc.cluster.local
```

### Headless Services (StatefulSet)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mydb
spec:
  clusterIP: None  # Headless — returns pod IPs directly
  selector:
    app: mydb
  ports:
    - port: 5432
```

DNS returns individual pod IPs: `mydb-0.mydb.default.svc.cluster.local`

### ExternalDNS

Automatically manages DNS records based on Ingress/Service annotations:

```yaml
metadata:
  annotations:
    external-dns.alpha.kubernetes.io/hostname: myapp.example.com
    external-dns.alpha.kubernetes.io/ttl: "300"
```

---

## 6. Service Mesh Overview

### When to Consider Service Mesh

| Need | Without Mesh | With Mesh |
| --- | --- | --- |
| mTLS between services | Manual cert management | Automatic |
| Traffic splitting | Ingress controller annotations | Native weighted routing |
| Observability | Application-level instrumentation | Automatic (sidecar proxy) |
| Retries/timeouts | Application code | Sidecar configuration |
| Circuit breaking | Application library | Sidecar configuration |

### Mesh Comparison

| Feature | Istio | Linkerd |
| --- | --- | --- |
| Complexity | High | Low |
| Resource overhead | Higher | Lower |
| mTLS | Yes | Yes |
| Traffic management | Advanced | Basic |
| Multi-cluster | Yes | Yes |
| WASM extensions | Yes | No |

### Decision Guide

- **<20 services, simple routing**: No mesh — use Ingress + application libraries
- **20-50 services, need mTLS**: Linkerd (simpler, lighter)
- **50+ services, advanced traffic management**: Istio (more features, more overhead)
