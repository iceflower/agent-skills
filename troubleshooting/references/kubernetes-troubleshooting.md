# Kubernetes Troubleshooting Guide

## 1. OOMKilled

### Identification

```bash
# Check pod status
kubectl get pods -n <namespace> | grep OOMKilled

# Get detailed termination reason
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Last State"

# Check container exit code (137 = SIGKILL from OOM)
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason}'
```

### Common Causes

| Cause | Diagnosis | Fix |
| --- | --- | --- |
| Memory limit too low | Container consistently hits limit | Increase `resources.limits.memory` |
| Memory leak in application | Gradual memory growth over time | Profile app, fix leak, add heap dump on OOM |
| Large in-memory cache | Memory spikes during cache population | Use bounded cache (e.g., Caffeine with `maximumSize`) |
| Thread/goroutine leak | Thread count grows unbounded | Fix leak, set max thread pool size |
| JVM heap exceeds container limit | JVM allocates more than container allows | Set `-Xmx` to ~75% of container memory limit |

### JVM-Specific OOMKilled

```yaml
# Container memory limit vs JVM heap sizing
resources:
  limits:
    memory: "1Gi"    # Container limit
  requests:
    memory: "512Mi"

# JVM flags — heap should be ~75% of container limit
# Remaining 25% is for metaspace, thread stacks, native memory, OS overhead
env:
  - name: JAVA_OPTS
    value: "-Xms512m -Xmx768m -XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0"
```

### Memory Monitoring

```bash
# Real-time memory usage
kubectl top pod <pod-name> -n <namespace>

# Check resource limits and requests
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.spec.containers[0].resources}'

# Check node memory pressure
kubectl describe node <node-name> | grep -A 5 "Conditions"
```

---

## 2. CrashLoopBackOff

### Diagnosis

```bash
# Check pod status and restart count
kubectl get pods -n <namespace> | grep CrashLoopBackOff

# View recent events
kubectl describe pod <pod-name> -n <namespace> | tail -20

# Check container logs (current attempt)
kubectl logs <pod-name> -n <namespace>

# Check previous container logs (last crash)
kubectl logs <pod-name> -n <namespace> --previous
```

### Common Causes and Resolution

| Cause | Diagnosis | Fix |
| --- | --- | --- |
| Application startup failure | Error in logs, exit code 1 | Fix config, dependencies, or startup code |
| Missing config/secrets | `FileNotFoundException`, env var errors | Verify ConfigMap/Secret mounts |
| Failed health checks | Liveness probe failing | Adjust probe `initialDelaySeconds` and thresholds |
| Port conflict | `Address already in use` | Fix container port configuration |
| Insufficient resources | OOMKilled before crash loop | Increase memory/CPU limits |
| Image pull issues | `ImagePullBackOff` preceding crash | Fix image tag, registry credentials |

### Backoff Timing

Kubernetes uses exponential backoff for restart delays:

```text
Restart 1: 10s delay
Restart 2: 20s delay
Restart 3: 40s delay
Restart 4: 80s delay
Restart 5: 160s delay
Maximum:   300s (5 minutes)
```

### Liveness vs Readiness Probe Issues

| Problem | Cause | Fix |
| --- | --- | --- |
| Pod keeps restarting | Liveness probe fails during startup | Increase `initialDelaySeconds` or use startup probe |
| Pod never receives traffic | Readiness probe fails | Fix health endpoint or adjust probe config |
| Intermittent restarts | Liveness probe timeout too short | Increase `timeoutSeconds` and `failureThreshold` |

```yaml
# Recommended probe configuration for slow-starting apps
startupProbe:
  httpGet:
    path: /health
    port: 8080
  failureThreshold: 30    # 30 * 10s = 5 minutes max startup time
  periodSeconds: 10

livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 0   # startup probe handles initial delay
  periodSeconds: 15
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  periodSeconds: 10
  timeoutSeconds: 3
  failureThreshold: 3
```

---

## 3. Pod Debugging Checklist

### Step-by-Step Debugging

```text
1. Check pod status and events
   → kubectl describe pod <pod> -n <ns>

2. Check container logs
   → kubectl logs <pod> -n <ns> [--previous]

3. Check resource usage
   → kubectl top pod <pod> -n <ns>

4. Check node health
   → kubectl describe node <node>

5. Check networking
   → kubectl exec <pod> -n <ns> -- curl -v <target-url>

6. Check DNS resolution
   → kubectl exec <pod> -n <ns> -- nslookup <service-name>

7. Check mounted volumes and secrets
   → kubectl exec <pod> -n <ns> -- ls -la /path/to/mount

8. Check environment variables
   → kubectl exec <pod> -n <ns> -- env | sort
```

### Pod Status Reference

| Status | Meaning | Action |
| --- | --- | --- |
| `Pending` | Not scheduled yet | Check node resources, affinity, taints |
| `ContainerCreating` | Image pulling or volume mounting | Check image, PVC, secrets |
| `Running` | Containers started | Check logs if behavior is wrong |
| `CrashLoopBackOff` | Repeated crashes | Check logs with `--previous` |
| `OOMKilled` | Memory limit exceeded | Increase limits or fix memory usage |
| `Evicted` | Node resource pressure | Check node conditions, clean up |
| `ImagePullBackOff` | Cannot pull container image | Verify image name, tag, registry auth |
| `Terminating` | Stuck during deletion | Check finalizers, force delete if needed |

### Useful Debugging Commands

```bash
# Get all events sorted by time
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Check pod scheduling decisions
kubectl get pod <pod-name> -n <namespace> -o wide

# Exec into a running container for interactive debugging
kubectl exec -it <pod-name> -n <namespace> -- /bin/sh

# Copy files from pod for analysis
kubectl cp <namespace>/<pod-name>:/path/to/file ./local-file

# Check resource quotas
kubectl describe resourcequota -n <namespace>

# Port-forward for local debugging
kubectl port-forward pod/<pod-name> -n <namespace> 8080:8080
```

### Network Debugging

```bash
# Test service DNS resolution
kubectl exec <pod> -n <ns> -- nslookup <service>.<namespace>.svc.cluster.local

# Test connectivity to another service
kubectl exec <pod> -n <ns> -- curl -s -o /dev/null -w "%{http_code}" http://<service>:<port>/health

# Check network policies affecting the pod
kubectl get networkpolicy -n <namespace>

# Verify service endpoints are populated
kubectl get endpoints <service-name> -n <namespace>
```
