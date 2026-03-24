# API Versioning Implementation Patterns

Detailed implementation examples for various frameworks and API gateways.

## Spring Framework 7 / Spring Boot 4

### Configuration Options

```java
@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void configureApiVersioning(ApiVersionConfigurer configurer) {
        // Option 1: Header-based
        configurer.useRequestHeader("Api-Version");

        // Option 2: Query parameter
        configurer.useRequestParameter("version");

        // Option 3: URL path segment
        configurer.usePathSegment(1); // /v{version}/...

        // Default version for requests without version info
        configurer.defaultVersion("1.0");
    }
}
```

### Controller Usage

```java
@RestController
@RequestMapping("/accounts")
public class AccountController {

    // Exact version match
    @GetMapping(path = "/{id}", version = "1")
    public AccountV1 getAccountV1(@PathVariable Long id) {
        return accountService.getV1(id);
    }

    @GetMapping(path = "/{id}", version = "2")
    public AccountV2 getAccountV2(@PathVariable Long id) {
        return accountService.getV2(id);
    }

    // Version range: matches 1.2 and above
    @GetMapping(path = "/{id}", version = "1.2+")
    public AccountV1Extended getAccountV1_2Plus(@PathVariable Long id) {
        return accountService.getV1Extended(id);
    }
}
```

### Shared Logic Pattern

```java
@RestController
@RequestMapping("/users")
public class UserController {

    private final UserService userService;

    // Common endpoint (all versions)
    @GetMapping
    public List<UserResponse> listUsers() {
        return userService.listAll();
    }

    // Version-specific: v1 returns flat structure
    @GetMapping(path = "/{id}", version = "1")
    public UserV1Response getUserV1(@PathVariable Long id) {
        User user = userService.findById(id);
        return UserV1Response.from(user);
    }

    // Version-specific: v2 returns nested structure
    @GetMapping(path = "/{id}", version = "2")
    public UserV2Response getUserV2(@PathVariable Long id) {
        User user = userService.findById(id);
        return UserV2Response.from(user);
    }
}
```

## Express.js

### Router-Based Versioning (URL Path)

```javascript
// routes/v1/users.js
import { Router } from "express";
const router = Router();

router.get("/users", (req, res) => {
  // V1: flat response
  res.json(users.map(u => ({
    id: u.id,
    fullName: u.fullName,
    email: u.email,
  })));
});

export default router;

// routes/v2/users.js
import { Router } from "express";
const router = Router();

router.get("/users", (req, res) => {
  // V2: nested response
  res.json(users.map(u => ({
    id: u.id,
    name: { first: u.firstName, last: u.lastName },
    contact: { email: u.email },
  })));
});

export default router;

// app.js
import v1Router from "./routes/v1/users.js";
import v2Router from "./routes/v2/users.js";

app.use("/api/v1", v1Router);
app.use("/api/v2", v2Router);
```

### Header-Based Versioning Middleware

```javascript
function versionMiddleware(versionHandlers) {
  return (req, res, next) => {
    const version = req.headers["api-version"] || "1";
    const handler = versionHandlers[version];

    if (!handler) {
      return res.status(400).json({
        error: {
          code: "UNSUPPORTED_VERSION",
          message: `API version '${version}' is not supported`,
          supported: Object.keys(versionHandlers),
        },
      });
    }

    handler(req, res, next);
  };
}

// Usage
app.get("/api/users/:id",
  versionMiddleware({
    "1": getUserV1,
    "2": getUserV2,
  })
);
```

### Deprecation Middleware

```javascript
function deprecationMiddleware(deprecatedAt, sunsetDate, successorUrl) {
  return (req, res, next) => {
    res.set("Deprecation", `@${Math.floor(new Date(deprecatedAt).getTime() / 1000)}`);
    res.set("Sunset", new Date(sunsetDate).toUTCString());
    if (successorUrl) {
      res.set("Link", `<${successorUrl}>; rel="successor-version"`);
    }
    next();
  };
}

// Apply to deprecated v1 routes
app.use("/api/v1",
  deprecationMiddleware("2024-06-01", "2024-12-31", "https://api.example.com/v2"),
  v1Router
);
```

## API Gateway Configuration

### Kong

```yaml
# Route for v1
- name: users-v1
  paths:
    - /api/v1/users
  service:
    name: users-service-v1
    url: http://users-v1:8081

# Route for v2
- name: users-v2
  paths:
    - /api/v2/users
  service:
    name: users-service-v2
    url: http://users-v2:8082

# Header-based routing
- name: users-header-v2
  headers:
    Api-Version:
      - "2"
  paths:
    - /api/users
  service:
    name: users-service-v2
```

### Nginx

```nginx
upstream users_v1 {
    server users-v1:8081;
}

upstream users_v2 {
    server users-v2:8082;
}

server {
    listen 80;

    # Path-based routing
    location /api/v1/ {
        proxy_pass http://users_v1/;
    }

    location /api/v2/ {
        proxy_pass http://users_v2/;
    }

    # Header-based routing
    location /api/users {
        if ($http_api_version = "2") {
            proxy_pass http://users_v2;
        }
        proxy_pass http://users_v1;  # default to v1
    }
}
```

### AWS API Gateway (CDK)

```typescript
const apiV1 = new apigateway.RestApi(this, "ApiV1", {
  deployOptions: { stageName: "v1" },
});

const apiV2 = new apigateway.RestApi(this, "ApiV2", {
  deployOptions: { stageName: "v2" },
});

// Canary deployment for gradual v2 rollout
const deployment = new apigateway.Deployment(this, "ApiV2Deployment", {
  api: apiV2,
});

new apigateway.Stage(this, "ApiV2Stage", {
  deployment,
  stageName: "v2",
  canary: {
    percentTraffic: 10,  // 10% traffic to canary
  },
});
```

## Deprecation Response Patterns

### 410 Gone (After Retirement)

```json
{
  "error": {
    "code": "API_RETIRED",
    "message": "API v1 has been retired as of 2024-12-31",
    "migration": "https://api.example.com/v2/migration-guide",
    "successor": "https://api.example.com/v2/users"
  }
}
```

### 301 Redirect (Soft Retirement)

```http
HTTP/1.1 301 Moved Permanently
Location: https://api.example.com/v2/users/42
```

## Resources

- [Spring API Versioning Blog](https://spring.io/blog/2025/09/16/api-versioning-in-spring/)
- [RFC 9745: Deprecation Header](https://www.rfc-editor.org/rfc/rfc9745.html)
- [RFC 8594: Sunset Header](https://www.rfc-editor.org/rfc/rfc8594.html)
- [Kong Gateway Docs](https://developer.konghq.com/gateway/)
