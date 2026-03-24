---
name: devcontainer
description: >-
  Dev Container configuration patterns including devcontainer.json structure,
  image selection, Features, Docker Compose integration, lifecycle commands,
  port forwarding, VS Code customizations, and GitHub Codespaces integration.
  Use when setting up reproducible development environments with Dev Containers,
  configuring Codespaces, or writing devcontainer.json files.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# Dev Container Rules

## 1. Core Structure

Place configuration in `.devcontainer/devcontainer.json`.

### Image Source (choose one)

```jsonc
// Option 1: Pre-built image
{ "image": "mcr.microsoft.com/devcontainers/base:ubuntu" }

// Option 2: Custom Dockerfile
{ "build": { "dockerfile": "Dockerfile", "context": ".." } }

// Option 3: Docker Compose
{ "dockerComposeFile": "docker-compose.yml", "service": "app" }
```

### Minimal Template

```jsonc
{
  "name": "My Project",
  "image": "mcr.microsoft.com/devcontainers/base:ubuntu",
  "features": {},
  "forwardPorts": [],
  "postCreateCommand": "",
  "customizations": {
    "vscode": {
      "extensions": [],
      "settings": {}
    }
  }
}
```

## 2. Image Selection

### Official Base Images

| Image | Use Case |
| --- | --- |
| `devcontainers/base:ubuntu` | General purpose |
| `devcontainers/typescript-node` | Node.js / TypeScript |
| `devcontainers/python` | Python |
| `devcontainers/java` | Java |
| `devcontainers/go` | Go |
| `devcontainers/rust` | Rust |
| `devcontainers/universal` | Multi-language (Codespaces default) |

All images are prefixed with `mcr.microsoft.com/`.

### Custom Dockerfile

```jsonc
{
  "build": {
    "dockerfile": "Dockerfile",
    "context": "..",
    "args": { "VARIANT": "3.12" },
    "target": "development"
  }
}
```

```dockerfile
ARG VARIANT=3.12
FROM mcr.microsoft.com/devcontainers/python:${VARIANT}

RUN apt-get update && apt-get install -y --no-install-recommends \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

USER vscode
COPY requirements.txt /tmp/
RUN pip install --user -r /tmp/requirements.txt
```

### Rules

- Prefer official `devcontainers/*` images as base (pre-configured non-root user, tools)
- Use specific version tags, not `latest`
- Extend with Features before resorting to custom Dockerfile
- Set `context: ".."` to access project root files from Dockerfile

## 3. Features

Modular, self-contained tool installers distributed via OCI registries.

### Usage

```jsonc
{
  "features": {
    "ghcr.io/devcontainers/features/node:1": { "version": "22" },
    "ghcr.io/devcontainers/features/java:1": { "version": "21", "installGradle": true },
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/github-cli:1": {}
  }
}
```

### Common Features

| Feature | Description |
| --- | --- |
| `node` | Node.js, nvm, yarn |
| `python` | Python, pip, venv |
| `java` | JDK, Maven, Gradle |
| `go` | Go runtime |
| `docker-in-docker` | Docker daemon inside container |
| `docker-outside-of-docker` | Share host Docker socket |
| `kubectl-helm-minikube` | Kubernetes tools |
| `terraform` | Terraform CLI |
| `aws-cli` / `azure-cli` | Cloud CLIs |
| `github-cli` | GitHub CLI (gh) |
| `common-utils` | zsh, git, curl, etc. |

### Rules

- Prefer Features over manual installation in Dockerfile
- Pin Feature versions (`feature:1`, not `feature:latest`) — browse available versions at [containers.dev/features](https://containers.dev/features)
- Features apply only to the primary service (in Docker Compose setups)

## 4. Docker Compose Integration

For multi-container setups (app + DB + cache).

```jsonc
{
  "dockerComposeFile": "docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/workspaces/${localWorkspaceFolderBasename}",
  "forwardPorts": [3000, 5432, 6379],
  "shutdownAction": "stopCompose"
}
```

```yaml
# .devcontainer/docker-compose.yml
services:
  app:
    build:
      context: ..
      dockerfile: .devcontainer/Dockerfile
    volumes:
      - ..:/workspaces/${LOCAL_WORKSPACE_FOLDER_BASENAME}:cached
    command: sleep infinity

  db:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_USER: devuser
      POSTGRES_PASSWORD: devpass
      POSTGRES_DB: devdb
    volumes:
      - postgres-data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  postgres-data:
```

### Rules

- Use `command: sleep infinity` on the dev service to keep it running
- Use `:cached` volume flag on macOS for performance
- Override existing compose files with array: `["../docker-compose.yml", "docker-compose.extend.yml"]`
- Use named volumes for data persistence across rebuilds

## 5. Lifecycle Commands

### Execution Order

```text
initializeCommand     → Runs on HOST before container build
onCreateCommand       → Container first creation only
updateContentCommand  → Creation + content changes (prebuild)
postCreateCommand     → After creation + updateContent
postStartCommand      → Every container start
postAttachCommand     → Every VS Code attach
```

### Usage Guide

| Command | When | Use For |
| --- | --- | --- |
| `initializeCommand` | Before build (host) | Git submodules, host checks |
| `onCreateCommand` | First creation | Heavy dependency install, DB schema |
| `postCreateCommand` | After creation | `npm ci`, `pip install`, build |
| `postStartCommand` | Every start | Background services, temp cleanup |
| `postAttachCommand` | Every attach | Welcome message, status display |

### Parallel Execution

```jsonc
{
  "postCreateCommand": {
    "install": "npm ci",
    "db": "npm run db:migrate",
    "build": "npm run build"
  }
}
```

Object form runs commands in parallel. If any command fails, the container
creation still succeeds but the failed command's error is shown.
Use `&&` chaining for sequential execution where order matters.

## 6. Ports and Environment

### Port Forwarding

```jsonc
{
  "forwardPorts": [3000, 5432],
  "portsAttributes": {
    "3000": { "label": "App", "onAutoForward": "openBrowser" },
    "5432": { "label": "PostgreSQL", "onAutoForward": "silent" }
  },
  "otherPortsAttributes": { "onAutoForward": "notify" }
}
```

`onAutoForward` options: `notify`, `openBrowser`, `openBrowserOnce`,
`openPreview`, `silent`, `ignore`

### Environment Variables

```jsonc
{
  "containerEnv": { "MY_VAR": "value" },
  "remoteEnv": {
    "NODE_ENV": "development",
    "PATH": "${containerEnv:PATH}:/custom/path",
    "HOST_HOME": "${localEnv:HOME}"
  }
}
```

- `containerEnv`: Set at build time, all processes
- `remoteEnv`: Set at attach time, VS Code terminals
- `${localEnv:VAR}`: Reference host environment variables
- For secrets, use `.env` files or Codespaces secrets — never hardcode

## 7. VS Code Customizations

```jsonc
{
  "customizations": {
    "vscode": {
      "extensions": [
        "dbaeumer.vscode-eslint",
        "esbenp.prettier-vscode"
      ],
      "settings": {
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "esbenp.prettier-vscode"
      }
    }
  }
}
```

- Extensions install inside the container
- Include only project-essential extensions (affects startup time)
- Use `publisher.extension-name` format for extension IDs

## 8. GitHub Codespaces

### Prebuild

Pre-builds container images to reduce Codespace creation time.
Configure in Repository Settings → Codespaces → Prebuild.

Commands run during prebuild: `onCreateCommand`, `updateContentCommand`,
`postCreateCommand`. Commands NOT run: `postStartCommand`, `postAttachCommand`.

### Machine Type Requirements

```jsonc
{
  "hostRequirements": {
    "cpus": 4,
    "memory": "8gb",
    "storage": "32gb"
  }
}
```

### Secrets

```bash
gh secret set DATABASE_URL --app codespaces
```

Access in devcontainer.json via `${localEnv:DATABASE_URL}`.

## 9. Cache Optimization

Mount named volumes for package manager caches.
Named volumes are OS-independent and work consistently across Windows, macOS, and Linux:

```jsonc
{
  "mounts": [
    "source=devcontainer-npm-cache,target=/home/vscode/.npm,type=volume",
    "source=devcontainer-pip-cache,target=/home/vscode/.cache/pip,type=volume",
    "source=devcontainer-gradle-cache,target=/home/vscode/.gradle,type=volume"
  ]
}
```

## 10. Common Anti-Patterns

| Anti-Pattern | Problem | Fix |
| --- | --- | --- |
| Hardcoded secrets in `containerEnv` | Security risk in VCS | Use `.env` files or Codespaces secrets |
| `privileged: true` | Security risk | Use `docker-in-docker` Feature |
| `image: ...:latest` | Non-reproducible builds | Pin specific version tags |
| Everything in `postCreateCommand` | Slow container creation | Distribute across lifecycle commands |
| Running as root | Security risk | Set `remoteUser: "vscode"` |
| `.devcontainer` in `.gitignore` | Team can't share environment | Commit to version control |
| Too many extensions | Slow startup | Only project-essential extensions |
| No named volumes for data | Data loss on rebuild | Use Docker named volumes |
| Host-specific absolute paths | Breaks on other machines | Use `${localWorkspaceFolderBasename}` |
| Manual tool install in Dockerfile | Hard to maintain | Use Features instead |

For language-specific configuration templates, see
[references/templates.md](references/templates.md).
