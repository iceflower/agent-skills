# HashiCorp Vault Integration

Practical guide for integrating HashiCorp Vault for secrets management, including setup, policies, and dynamic secrets.

## Overview

HashiCorp Vault provides centralized secrets management with access control, audit logging, encryption as a service, and dynamic secret generation. It eliminates hardcoded secrets and provides short-lived, automatically rotated credentials.

## Core Concepts

```text
┌─────────────────────────────────────────────┐
│                  Vault                       │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │  Auth    │  │  Secret  │  │  Audit    │  │
│  │ Methods  │  │ Engines  │  │  Devices  │  │
│  └──────────┘  └──────────┘  └───────────┘  │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │          Policy Engine               │    │
│  └──────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

- **Auth Methods**: How clients authenticate (token, AppRole, Kubernetes, OIDC)
- **Secret Engines**: Where secrets are stored or generated (KV, database, PKI)
- **Policies**: What authenticated clients can access
- **Audit Devices**: Where access logs are sent

## Authentication Setup

### AppRole (Application Authentication)

Best for machine-to-machine authentication.

```bash
# Enable AppRole auth method
vault auth enable approle

# Create a role for the order service
vault write auth/approle/role/order-service \
    token_policies="order-service-policy" \
    token_ttl=1h \
    token_max_ttl=4h \
    secret_id_ttl=720h \
    secret_id_num_uses=0

# Get RoleID (embed in application config)
vault read auth/approle/role/order-service/role-id

# Generate SecretID (deliver securely, rotate regularly)
vault write -f auth/approle/role/order-service/secret-id
```

### Kubernetes Authentication

For applications running in Kubernetes.

```bash
# Enable Kubernetes auth
vault auth enable kubernetes

# Configure with cluster details
vault write auth/kubernetes/config \
    kubernetes_host="https://kubernetes.default.svc" \
    kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

# Create role bound to service account
vault write auth/kubernetes/role/order-service \
    bound_service_account_names=order-service \
    bound_service_account_namespaces=production \
    policies=order-service-policy \
    ttl=1h
```

## Policy Configuration

### Policy Syntax

```hcl
# order-service-policy.hcl

# Read database credentials
path "database/creds/order-service-db" {
  capabilities = ["read"]
}

# Read application secrets
path "secret/data/order-service/*" {
  capabilities = ["read", "list"]
}

# No access to other services' secrets
path "secret/data/payment-service/*" {
  capabilities = ["deny"]
}

# Allow token renewal
path "auth/token/renew-self" {
  capabilities = ["update"]
}
```

```bash
# Apply policy
vault policy write order-service-policy order-service-policy.hcl
```

### Policy Best Practices

| Principle              | Implementation                                    |
| ---------------------- | ------------------------------------------------- |
| Least privilege        | Grant only required paths and capabilities         |
| Path specificity       | Use exact paths, avoid wildcards when possible     |
| Separate by service    | One policy per service/application                 |
| Deny by default        | Vault denies everything not explicitly allowed     |
| Regular audits         | Review policies quarterly                          |

## KV Secret Engine

### Version 2 (Versioned)

```bash
# Enable KV v2
vault secrets enable -path=secret kv-v2

# Write a secret
vault kv put secret/order-service/config \
    db_host="db.internal" \
    api_key="sk-..." \
    feature_flags='{"new_checkout": true}'

# Read current version
vault kv get secret/order-service/config

# Read specific version
vault kv get -version=2 secret/order-service/config

# Delete (soft delete, recoverable)
vault kv delete secret/order-service/config

# Undelete
vault kv undelete -versions=3 secret/order-service/config
```

## Dynamic Secrets

### Database Credentials

Dynamic secrets are generated on demand with automatic expiration.

```bash
# Enable database secret engine
vault secrets enable database

# Configure PostgreSQL connection
vault write database/config/order-db \
    plugin_name=postgresql-database-plugin \
    connection_url="postgresql://{{username}}:{{password}}@db.internal:5432/orders" \
    allowed_roles="order-service-db" \
    username="vault_admin" \
    password="admin_password"

# Create role with SQL template
vault write database/roles/order-service-db \
    db_name=order-db \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
    revocation_statements="REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM \"{{name}}\"; DROP ROLE IF EXISTS \"{{name}}\";" \
    default_ttl=1h \
    max_ttl=24h
```

```bash
# Application requests credentials (fresh each time)
vault read database/creds/order-service-db

# Returns:
# username: v-approle-order-se-abc123
# password: A1b2C3d4E5-randomized
# lease_duration: 1h
# lease_id: database/creds/order-service-db/xyz789
```

### Credential Lifecycle

```text
┌─────────┐   authenticate   ┌─────────┐   request creds   ┌──────────┐
│   App   │─────────────────▶│  Vault  │──────────────────▶│ Database │
└─────────┘                  └────┬────┘                   └──────────┘
     │                            │
     │   credentials (1h TTL)     │
     │◀───────────────────────────┘
     │
     │   renew lease (before expiry)
     │──────────────────────────▶│
     │                           │
     │   extended TTL            │
     │◀──────────────────────────┘
     │
     │   (TTL expires)
     │                           │   revoke credentials
     │                           │──────────────────────▶│
```

## Application Integration

### Spring Boot with Spring Cloud Vault

```yaml
# application.yml
spring:
  cloud:
    vault:
      uri: https://vault.internal:8200
      authentication: kubernetes
      kubernetes:
        role: order-service
        service-account-token-file: /var/run/secrets/kubernetes.io/serviceaccount/token
      kv:
        enabled: true
        backend: secret
        application-name: order-service
      database:
        enabled: true
        role: order-service-db
        backend: database
```

### Sidecar Pattern (Vault Agent)

```yaml
# Kubernetes pod with Vault Agent sidecar
apiVersion: v1
kind: Pod
metadata:
  annotations:
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/role: "order-service"
    vault.hashicorp.com/agent-inject-secret-db: "database/creds/order-service-db"
    vault.hashicorp.com/agent-inject-template-db: |
      {{- with secret "database/creds/order-service-db" -}}
      spring.datasource.username={{ .Data.username }}
      spring.datasource.password={{ .Data.password }}
      {{- end -}}
spec:
  serviceAccountName: order-service
  containers:
    - name: order-service
      image: order-service:latest
```

## Secret Rotation

### Automated Rotation Strategy

| Secret Type          | Rotation Method              | Frequency        |
| -------------------- | ---------------------------- | ---------------- |
| Database credentials | Dynamic secrets (auto)       | Every request    |
| API keys             | Vault rotation + KV version  | 30-90 days       |
| TLS certificates     | PKI engine (auto)            | 30 days          |
| Encryption keys      | Transit engine rotation      | 90 days          |

## Audit and Compliance

```bash
# Enable file audit device
vault audit enable file file_path=/var/log/vault/audit.log

# Audit log includes all access attempts
# Sensitive values are HMAC'd (not plaintext)
```

Every Vault operation is logged: who accessed what, when, and whether it was allowed or denied.
