# Kubernetes Secret Patterns — Detailed Examples

## CSI Secret Store Driver

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: aws-secrets
spec:
  provider: aws
  parameters:
    objects: |
      - objectName: "myapp/prod/database"
        objectType: "secretsmanager"
        jmesPath:
          - path: username
            objectAlias: db-username
          - path: password
            objectAlias: db-password
  secretObjects:
    - secretName: myapp-db-creds
      type: Opaque
      data:
        - objectName: db-username
          key: username
        - objectName: db-password
          key: password
---
# Mount in Pod
volumes:
  - name: secrets
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: aws-secrets
```

## Sealed Secrets

```bash
# Encrypt secret for safe Git storage
kubectl create secret generic myapp-secret \
  --from-literal=api-key=supersecret \
  --dry-run=client -o yaml | \
  kubeseal --format=yaml \
  --controller-name=sealed-secrets \
  --controller-namespace=kube-system \
  > sealed-secret.yaml

# The sealed-secret.yaml is safe to commit to Git
# Controller decrypts it to a regular Secret in-cluster
```

## Secret Consumption Best Practices

```yaml
# Environment variable from Secret (K8s)
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: myapp-db-credentials
        key: password

# File mount from Secret (auto-refresh with projected volume)
volumes:
  - name: secrets
    projected:
      sources:
        - secret:
            name: myapp-db-credentials
```
