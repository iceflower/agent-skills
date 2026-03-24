---
name: secrets-management
description: >-
  Secret lifecycle management including storage solutions, rotation policies,
  Kubernetes patterns (ESO, Sealed Secrets, CSI), CI/CD pipeline secrets,
  certificate management, and secret detection/prevention.
  Use when managing secrets, credentials, or certificates in any environment.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
compatibility: May require vault CLI or cloud provider CLI
---

# Secrets Management Rules

## 1. Secret Types and Classification

### Classification by Sensitivity

| Sensitivity | Type | Examples | Rotation Period |
| --- | --- | --- | --- |
| Critical | Encryption keys | Data-at-rest keys, signing keys | 1 year (automated) |
| Critical | Database credentials | Production DB root/admin passwords | 90 days |
| High | API keys (external) | Payment gateway, cloud provider keys | 90 days |
| High | TLS certificates | Server certs, mTLS certs | Before expiry (auto-renew) |
| High | SSH keys | Deploy keys, service keys | 1 year |
| Medium | API keys (internal) | Service-to-service tokens | 180 days |
| Medium | OAuth client secrets | OIDC client credentials | 180 days |
| Low | Webhook secrets | HMAC signing secrets | 1 year |

### Classification Rules

- All secrets must be classified before storage
- Classification determines storage location, rotation policy, and access control
- When in doubt, classify higher — downgrade after review

---

## 2. Storage Solutions Comparison

| Feature | Vault | AWS SM | Azure KV | GCP SM | K8s Secrets | SOPS |
| --- | --- | --- | --- | --- | --- | --- |
| Dynamic secrets | Yes | No | No | No | No | No |
| Rotation | Built-in | Built-in | Built-in | Manual | Manual | Manual |
| Audit logging | Yes | CloudTrail | Monitor | Audit Log | API audit | Git |
| Access control | Policies | IAM | RBAC | IAM | RBAC | Git/KMS |
| HA | Yes | Managed | Managed | Managed | etcd | N/A |
| Multi-cloud | Yes | AWS only | Azure only | GCP only | K8s only | Any |
| Cost | Self-hosted/HCP | Per secret | Per operation | Per version | Free | Free |
| GitOps compatible | Via ESO | Via ESO | Via ESO | Via ESO | Direct | Direct |

### Selection Criteria

- **Multi-cloud or vendor-neutral**: HashiCorp Vault
- **Single cloud, managed**: Use cloud provider's secret manager
- **Kubernetes-native, simple**: External Secrets Operator + cloud SM
- **GitOps with encryption**: SOPS with Age/KMS
- **Dynamic credentials needed**: Vault (database, cloud IAM)

---

## 3. Rotation Policies

### Automated Rotation Pattern

```text
1. Generate new secret (Version N+1)
2. Deploy new secret to consumers (dual-credential phase)
3. Verify consumers use Version N+1
4. Revoke old secret (Version N)
5. Remove old secret from storage
```

### Zero-Downtime Rotation (Dual-Credential)

```text
Phase 1: [Active: V1]
Phase 2: [Active: V1, V2]  ← Deploy V2, app accepts both
Phase 3: [Active: V2]       ← Remove V1 from app config
Phase 4: [Active: V2]       ← Revoke V1 credential
```

### Rotation Frequency by Type

| Secret Type | Rotation | Automation |
| --- | --- | --- |
| Database passwords | 90 days | Vault dynamic secrets or cloud SM rotation |
| API keys | 90-180 days | Automated with notification |
| TLS certificates | Before expiry | cert-manager auto-renewal |
| Encryption keys | Annually | Key rotation with re-encryption |
| OAuth client secrets | 180 days | Automated with client update |
| SSH keys | Annually | Automated key pair generation |

### Emergency Rotation

Trigger immediate rotation when:

- Secret confirmed or suspected leaked
- Team member with access leaves the organization
- Unauthorized access detected in audit logs
- Compliance audit finding

### Emergency Rotation Procedure

```text
1. IMMEDIATE (0-15 min)
   - Identify all systems using the compromised secret
   - Generate new secret (Version N+1)
   - Deploy new secret to all consumers

2. CONTAIN (15-60 min)
   - Revoke the compromised secret (Version N)
   - Verify all consumers are using Version N+1
   - Check audit logs for unauthorized usage during exposure window

3. ASSESS (1-4 hours)
   - Determine exposure timeline (when leaked, when detected)
   - Identify blast radius (what data/systems were accessible)
   - Document findings for incident report

4. REMEDIATE (1-7 days)
   - Conduct root cause analysis (how the secret was leaked)
   - Implement prevention measures (pre-commit hooks, secret scanning)
   - Update runbooks and rotation procedures
   - File incident report per incident-response process
```

---

## 4. Kubernetes Secret Patterns

### External Secrets Operator (ESO)

```yaml
# ClusterSecretStore — connect to AWS Secrets Manager
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secrets-manager
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
            namespace: external-secrets
---
# ExternalSecret — sync a specific secret
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: myapp-db-credentials
  namespace: myapp
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: myapp-db-credentials
    creationPolicy: Owner
    deletionPolicy: Retain
  data:
    - secretKey: username
      remoteRef:
        key: myapp/prod/database
        property: username
    - secretKey: password
      remoteRef:
        key: myapp/prod/database
        property: password
```

### Sealed Secrets

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

### CSI Secret Store Driver

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

### Pattern Selection Guide

| Pattern | Pros | Cons | Best For |
| --- | --- | --- | --- |
| ESO | Cloud-native, multi-provider | Requires operator install | Cloud secret managers |
| Sealed Secrets | Simple, Git-native | Manual rotation, cluster-specific keys | Small teams, simple setups |
| CSI Driver | No K8s Secret object | Pod restart needed for refresh | Compliance requirements |
| SOPS | Git-native, no operator | Manual process, no dynamic refresh | GitOps with encrypted manifests |

---

## 5. Application Integration

### Secret Consumption Patterns

| Pattern | Pros | Cons |
| --- | --- | --- |
| Environment variables | Simple, universal | Visible in process list, no auto-refresh |
| Mounted files | Auto-refresh (volume), no process exposure | File watching needed |
| API call (runtime) | Always fresh, audit trail | Network dependency, caching needed |
| SDK integration | Type-safe, caching built-in | Vendor lock-in |

### Best Practices

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

### Application-Level Rules

- Never log secret values — mask in log output
- Cache secrets in memory with TTL, not on disk
- Handle secret refresh without restart when possible
- Use connection pooling that supports credential rotation
- Fail closed — refuse to start if required secrets are unavailable

---

## 6. Access Control

### Least Privilege Principles

| Principle | Implementation |
| --- | --- |
| Need-to-know | Grant access only to secrets required by the service |
| Time-bound | Use short-lived credentials (tokens, dynamic secrets) |
| Role-based | Map access to service roles, not individuals |
| Audit all access | Enable audit logging for all secret reads |
| Break-glass | Documented emergency access procedure with post-review |

### Dynamic Secrets (Vault)

```text
1. App authenticates to Vault (K8s service account, AWS IAM)
2. App requests database credentials
3. Vault creates temporary DB user with limited permissions
4. Credential has TTL (e.g., 1 hour)
5. Vault revokes credential on TTL expiry or app shutdown
```

### Advantages of Dynamic Secrets

- No shared credentials — each app instance gets unique credentials
- Automatic revocation — no manual cleanup
- Audit trail — every credential issuance is logged
- Blast radius reduction — compromised credential has limited scope and lifetime

---

## 7. CI/CD Pipeline Secrets

### GitHub Actions

```yaml
# Use OIDC for keyless cloud authentication (preferred)
permissions:
  id-token: write
  contents: read

steps:
  - name: Configure AWS credentials
    uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::123456789:role/github-actions
      aws-region: us-east-1

  # Use GitHub Secrets for non-cloud credentials
  - name: Deploy
    env:
      API_KEY: ${{ secrets.DEPLOY_API_KEY }}
    run: ./deploy.sh
```

### Pipeline Secret Rules

| Rule | Rationale |
| --- | --- |
| Use OIDC federation over static keys | No long-lived credentials to rotate |
| Scope secrets to environments | Production secrets only in production environment |
| Never echo secrets in logs | `::add-mask::` in GitHub Actions |
| Use dedicated service accounts | Not personal credentials |
| Rotate CI/CD secrets on personnel changes | Prevent lingering access |

### Preventing Secret Leakage in CI

```yaml
# GitHub Actions — mask any dynamic secret
- name: Mask secret
  run: echo "::add-mask::${{ steps.get-secret.outputs.value }}"

# Prevent secrets in artifacts
- name: Build
  run: |
    # Never write secrets to files that become artifacts
    export DB_URL="${{ secrets.DB_URL }}"
    ./build.sh
```

---

## 8. Certificate Management

### cert-manager with Let's Encrypt

```yaml
# ClusterIssuer for automatic certificate provisioning
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: platform@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            class: nginx
      - dns01:
          route53:
            region: us-east-1
---
# Certificate request
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: myapp-tls
  namespace: myapp
spec:
  secretName: myapp-tls-secret
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - myapp.example.com
    - "*.myapp.example.com"
  renewBefore: 360h  # Renew 15 days before expiry
```

### Certificate Lifecycle

| Phase | Action | Automation |
| --- | --- | --- |
| Provisioning | Request from CA | cert-manager |
| Monitoring | Track expiry dates | cert-manager + alerting |
| Renewal | Re-issue before expiry | cert-manager auto-renewal |
| Revocation | Revoke compromised certs | Manual (emergency) |
| Rotation | Deploy renewed cert | Automatic (Secret update) |

### mTLS Between Services

- Use cert-manager for issuing client certificates
- Alternatively, use service mesh (Istio, Linkerd) for automatic mTLS
- Internal CA for service-to-service communication
- Rotate internal CA annually, service certs every 90 days

---

## 9. Secret Detection and Prevention

### Pre-Commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

### CI Pipeline Scanning

```yaml
# GitHub Actions
- name: Scan for secrets
  uses: gitleaks/gitleaks-action@v2
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Tool Comparison

| Tool | Approach | Speed | Customization |
| --- | --- | --- | --- |
| gitleaks | Regex + entropy | Fast | Custom rules via TOML |
| detect-secrets | Plugin-based | Medium | Custom plugins |
| truffleHog | Regex + entropy + verified | Slow | Custom detectors |
| git-secrets | Regex | Fast | AWS-focused patterns |

### Remediation When Secrets Leak

```text
1. IMMEDIATE: Rotate the compromised secret
2. Assess: Determine exposure window and blast radius
3. Audit: Check access logs for unauthorized usage
4. Clean: Remove from Git history (BFG or git-filter-repo)
5. Prevent: Add detection to pre-commit and CI
6. Document: Record in incident log
```

```bash
# Remove secret from Git history
git filter-repo --invert-paths --path config/secrets.yaml

# Or use BFG Repo Cleaner
bfg --replace-text passwords.txt repo.git
```

### Prevention Rules

- Enable pre-commit hooks for all repositories
- Run secret scanning in CI as a blocking check
- Maintain a `.secrets.baseline` file for known false positives
- Review `.gitignore` for secret-prone patterns (`.env`, `*.pem`, `*.key`)
- Train developers on secret hygiene during onboarding

---

## 10. Anti-Patterns

- Storing secrets in plaintext in Git — even in "private" repositories
- Using the same secret across environments — compromising dev exposes production
- Manual secret rotation without documentation — leads to outages during rotation
- Hardcoding secrets in application code — impossible to rotate without redeployment
- Sharing personal credentials for service access — no audit trail, no revocation control
- Long-lived static credentials without rotation — increases window of exposure
- Storing secrets in ConfigMaps instead of Secrets — no base64 encoding, no RBAC distinction
- No audit logging for secret access — cannot detect unauthorized usage
- Using root/admin credentials in applications — violates least privilege
- Embedding secrets in Docker images — exposed via `docker history` or image scanning

## Additional References

- For HashiCorp Vault integration, setup, policies, and dynamic secrets, see [references/vault-integration.md](references/vault-integration.md)

## Related Skills

- For incident response procedures when secrets are leaked, see [incident-response](../incident-response/) skill
- For Kubernetes secret handling in manifests, see [k8s-workflow](../k8s-workflow/) skill
- For application-level security rules, see [security](../security/) skill
