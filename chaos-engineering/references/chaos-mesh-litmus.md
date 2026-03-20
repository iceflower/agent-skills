# Chaos Mesh vs LitmusChaos

Comparison of two major Kubernetes-native chaos engineering tools, with experiment examples for each.

## Overview

Both Chaos Mesh and LitmusChaos are CNCF projects that inject faults into Kubernetes clusters to test system resilience. They differ in architecture, experiment types, and operational model.

## Feature Comparison

| Feature                  | Chaos Mesh                    | LitmusChaos                    |
| ------------------------ | ----------------------------- | ------------------------------ |
| CNCF Status              | Incubating                    | Incubating                     |
| Architecture             | Operator + Sidecar            | Operator + Runner pods         |
| Dashboard                | Built-in web UI               | ChaosCenter (web UI)           |
| Experiment CRDs          | Native Kubernetes CRDs        | ChaosEngine + ChaosExperiment  |
| Fault types              | Pod, Network, IO, Stress, DNS | Pod, Network, IO, Stress, DNS  |
| Cloud provider faults    | Limited                       | AWS, GCP, Azure support        |
| Workflow support          | Built-in workflows            | ChaosWorkflow CRD              |
| Steady-state validation  | StatusCheck                   | Litmus Probes                  |
| Scheduling               | Built-in Cron                 | Built-in scheduling            |
| RBAC integration         | Kubernetes RBAC               | Kubernetes RBAC + ChaosCenter  |
| Installation             | Helm chart                    | Helm chart or operator         |

## Chaos Mesh

### Installation

```bash
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm install chaos-mesh chaos-mesh/chaos-mesh \
    --namespace chaos-mesh \
    --create-namespace \
    --set chaosDaemon.runtime=containerd \
    --set chaosDaemon.socketPath=/run/containerd/containerd.sock
```

### Pod Fault Experiment

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: pod-kill-test
  namespace: chaos-mesh
spec:
  action: pod-kill
  mode: one
  selector:
    namespaces:
      - production
    labelSelectors:
      app: order-service
  scheduler:
    cron: "@every 2h"
```

### Network Fault Experiment

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-delay-test
  namespace: chaos-mesh
spec:
  action: delay
  mode: all
  selector:
    namespaces:
      - production
    labelSelectors:
      app: order-service
  delay:
    latency: "200ms"
    jitter: "50ms"
    correlation: "50"
  direction: to
  target:
    selector:
      namespaces:
        - production
      labelSelectors:
        app: payment-service
    mode: all
  duration: "5m"
```

### IO Fault Experiment

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: IOChaos
metadata:
  name: io-latency-test
  namespace: chaos-mesh
spec:
  action: latency
  mode: one
  selector:
    namespaces:
      - production
    labelSelectors:
      app: order-service
  volumePath: /data
  path: "/*"
  delay: "100ms"
  percent: 50
  duration: "10m"
```

### Workflow (Multiple Faults)

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: Workflow
metadata:
  name: resilience-test-workflow
  namespace: chaos-mesh
spec:
  entry: serial-tests
  templates:
    - name: serial-tests
      templateType: Serial
      children:
        - network-delay-phase
        - pod-kill-phase
    - name: network-delay-phase
      templateType: NetworkChaos
      deadline: 5m
      networkChaos:
        action: delay
        mode: all
        selector:
          labelSelectors:
            app: order-service
        delay:
          latency: "300ms"
    - name: pod-kill-phase
      templateType: PodChaos
      deadline: 2m
      podChaos:
        action: pod-kill
        mode: one
        selector:
          labelSelectors:
            app: order-service
```

## LitmusChaos

### Installation

```bash
helm repo add litmuschaos https://litmuschaos.github.io/litmus-helm
helm install litmus litmuschaos/litmus \
    --namespace litmus \
    --create-namespace
```

### Pod Delete Experiment

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: order-service-chaos
  namespace: production
spec:
  appinfo:
    appns: production
    applabel: app=order-service
    appkind: deployment
  chaosServiceAccount: litmus-admin
  experiments:
    - name: pod-delete
      spec:
        components:
          env:
            - name: TOTAL_CHAOS_DURATION
              value: "60"
            - name: CHAOS_INTERVAL
              value: "20"
            - name: FORCE
              value: "false"
        probe:
          - name: check-order-api
            type: httpProbe
            httpProbe/inputs:
              url: http://order-service.production.svc:8080/health
              method:
                get:
                  criteria: ==
                  responseCode: "200"
            mode: Continuous
            runProperties:
              probeTimeout: 5s
              interval: 5s
```

### Network Loss Experiment

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: network-loss-test
  namespace: production
spec:
  appinfo:
    appns: production
    applabel: app=order-service
    appkind: deployment
  chaosServiceAccount: litmus-admin
  experiments:
    - name: pod-network-loss
      spec:
        components:
          env:
            - name: NETWORK_INTERFACE
              value: "eth0"
            - name: NETWORK_PACKET_LOSS_PERCENTAGE
              value: "30"
            - name: TOTAL_CHAOS_DURATION
              value: "120"
            - name: DESTINATION_IPS
              value: "10.0.1.50"
```

## Choosing Between Them

| Scenario                              | Recommendation     |
| ------------------------------------- | ------------------ |
| Kubernetes-only faults                | Either tool        |
| Cloud provider faults (EC2, RDS)      | LitmusChaos        |
| Built-in workflow orchestration       | Chaos Mesh         |
| Rich steady-state probes              | LitmusChaos        |
| Minimal operational overhead          | Chaos Mesh         |
| Team prefers GUI-driven experiments   | LitmusChaos        |
| Fine-grained network fault control    | Chaos Mesh         |

## Safety Guidelines

- Always define blast radius with label selectors and namespace restrictions
- Set `duration` on every experiment to auto-recover
- Run experiments in staging before production
- Have a kill switch: `kubectl delete` the ChaosEngine/PodChaos to stop immediately
- Monitor system health during experiments with dashboards and alerts
- Start with minimal fault intensity and increase gradually
