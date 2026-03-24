# Dev Container Configuration Templates

Ready-to-use devcontainer.json templates for common technology stacks.

## Java / Spring Boot

```jsonc
{
  "name": "Java Spring Boot",
  "image": "mcr.microsoft.com/devcontainers/java:21",
  "features": {
    "ghcr.io/devcontainers/features/java:1": {
      "version": "21",
      "installMaven": true,
      "installGradle": true
    },
    "ghcr.io/devcontainers/features/node:1": { "version": "22" },
    "ghcr.io/devcontainers/features/docker-in-docker:2": {}
  },
  "forwardPorts": [8080, 5005],
  "portsAttributes": {
    "8080": { "label": "App", "onAutoForward": "notify" },
    "5005": { "label": "Debug", "onAutoForward": "silent" }
  },
  "postCreateCommand": "./gradlew dependencies",
  "mounts": [
    "source=devcontainer-gradle-cache,target=/home/vscode/.gradle,type=volume"
  ],
  "customizations": {
    "vscode": {
      "extensions": [
        "vscjava.vscode-java-pack",
        "vmware.vscode-spring-boot",
        "vscjava.vscode-spring-boot-dashboard"
      ],
      "settings": {
        "java.server.launchMode": "Standard",
        "java.compile.nullAnalysis.mode": "automatic"
      }
    }
  }
}
```

## Node.js / TypeScript

```jsonc
{
  "name": "Node.js TypeScript",
  "image": "mcr.microsoft.com/devcontainers/typescript-node:22",
  "forwardPorts": [3000, 5173],
  "portsAttributes": {
    "3000": { "label": "App", "onAutoForward": "openBrowser" },
    "5173": { "label": "Vite Dev", "onAutoForward": "openBrowser" }
  },
  "postCreateCommand": "npm ci",
  "mounts": [
    "source=devcontainer-npm-cache,target=/home/vscode/.npm,type=volume"
  ],
  "customizations": {
    "vscode": {
      "extensions": [
        "dbaeumer.vscode-eslint",
        "esbenp.prettier-vscode",
        "bradlc.vscode-tailwindcss"
      ],
      "settings": {
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "esbenp.prettier-vscode",
        "editor.codeActionsOnSave": {
          "source.fixAll.eslint": "explicit"
        }
      }
    }
  }
}
```

## Python / FastAPI

```jsonc
{
  "name": "Python FastAPI",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "features": {
    "ghcr.io/devcontainers/features/node:1": { "version": "22" }
  },
  "forwardPorts": [8000],
  "portsAttributes": {
    "8000": { "label": "FastAPI", "onAutoForward": "notify" }
  },
  "postCreateCommand": "pip install -r requirements.txt",
  "mounts": [
    "source=devcontainer-pip-cache,target=/home/vscode/.cache/pip,type=volume"
  ],
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "ms-python.black-formatter",
        "charliermarsh.ruff"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "[python]": {
          "editor.defaultFormatter": "ms-python.black-formatter",
          "editor.formatOnSave": true
        }
      }
    }
  }
}
```

## Full Stack (Docker Compose)

### devcontainer.json

```jsonc
{
  "name": "Full Stack",
  "dockerComposeFile": "docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/workspaces/${localWorkspaceFolderBasename}",
  "forwardPorts": [3000, 8080, 5432, 6379],
  "portsAttributes": {
    "3000": { "label": "Frontend", "onAutoForward": "openBrowser" },
    "8080": { "label": "Backend", "onAutoForward": "notify" },
    "5432": { "label": "PostgreSQL", "onAutoForward": "silent" },
    "6379": { "label": "Redis", "onAutoForward": "silent" }
  },
  "features": {
    "ghcr.io/devcontainers/features/java:1": { "version": "21" },
    "ghcr.io/devcontainers/features/node:1": { "version": "22" }
  },
  "postCreateCommand": {
    "backend": "cd backend && ./gradlew dependencies",
    "frontend": "cd frontend && npm ci"
  },
  "customizations": {
    "vscode": {
      "extensions": [
        "vscjava.vscode-java-pack",
        "dbaeumer.vscode-eslint",
        "esbenp.prettier-vscode"
      ]
    }
  },
  "shutdownAction": "stopCompose"
}
```

### docker-compose.yml

```yaml
services:
  app:
    build:
      context: ..
      dockerfile: .devcontainer/Dockerfile
    volumes:
      - ..:/workspaces/${LOCAL_WORKSPACE_FOLDER_BASENAME}:cached
      - gradle-cache:/home/vscode/.gradle
      - npm-cache:/home/vscode/.npm
    command: sleep infinity
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

  db:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_USER: devuser
      POSTGRES_PASSWORD: devpass
      POSTGRES_DB: devdb
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U devuser -d devdb"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis-data:/data

volumes:
  postgres-data:
  redis-data:
  gradle-cache:
  npm-cache:
```

## Kubernetes Development

```jsonc
{
  "name": "Kubernetes Dev",
  "image": "mcr.microsoft.com/devcontainers/base:ubuntu",
  "features": {
    "ghcr.io/devcontainers/features/kubectl-helm-minikube:1": {
      "version": "latest",
      "helm": "latest",
      "minikube": "latest"
    },
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/terraform:1": {},
    "ghcr.io/devcontainers/features/github-cli:1": {}
  },
  "postCreateCommand": "minikube start --driver=docker",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-kubernetes-tools.vscode-kubernetes-tools",
        "redhat.vscode-yaml",
        "hashicorp.terraform"
      ]
    }
  }
}
```

## Resources

- [Dev Container Templates Registry](https://containers.dev/templates)
- [Official Images Source](https://github.com/devcontainers/images)
- [Official Features Source](https://github.com/devcontainers/features)
