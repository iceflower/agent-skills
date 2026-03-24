---
name: openapi-spec
description: >-
  OpenAPI specification writing best practices including schema design,
  documentation generation, validation, versioning, and code generation
  patterns.
  Use when writing, reviewing, or maintaining OpenAPI specifications.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# OpenAPI Specification Rules

## 1. Core Principles

### Specification Structure

- Use OpenAPI 3.0+ (prefer 3.1 for full JSON Schema compatibility)
- Write specs in YAML for readability — convert to JSON for tooling
  if needed
- Organize large specs using `$ref` to external files
- Keep the spec as the single source of truth for your API contract

### File Organization

```text
openapi/
  openapi.yaml           # Root specification file
  paths/
    users.yaml           # /users endpoints
    orders.yaml          # /orders endpoints
  schemas/
    User.yaml            # User schema
    Order.yaml           # Order schema
    common/
      Pagination.yaml    # Shared pagination schema
      Error.yaml         # Shared error schema
  parameters/
    common.yaml          # Shared parameters (page, limit, etc.)
  responses/
    errors.yaml          # Shared error responses
  examples/
    users.yaml           # Example payloads
```

### Root Document Structure

```yaml
openapi: 3.1.0
info:
  title: Order Management API
  description: >-
    API for managing orders, products, and customer information.
  version: 1.2.0
  contact:
    name: API Team
    email: api-team@example.com

servers:
  - url: https://api.example.com/v1
    description: Production
  - url: https://staging-api.example.com/v1
    description: Staging

tags:
  - name: Users
  - name: Orders

paths:
  /users:
    $ref: './paths/users.yaml'
  /orders:
    $ref: './paths/orders.yaml'
```

---

## 2. Schema Design

### Schema Best Practices

- Define all schemas in `components/schemas` and reference them
- Use `required` arrays explicitly — do not rely on defaults
- Add `description` to every property
- Set `format` for strings (date-time, email, uri, uuid)
- Use `example` values that are realistic and self-explanatory

```yaml
components:
  schemas:
    User:
      type: object
      required:
        - id
        - email
        - name
        - role
      properties:
        id:
          type: string
          format: uuid
          description: Unique user identifier
          example: "550e8400-e29b-41d4-a716-446655440000"
        email:
          type: string
          format: email
          description: User's email address
          example: "john.doe@example.com"
        name:
          type: string
          minLength: 1
          maxLength: 100
          description: User's display name
          example: "John Doe"
        role:
          $ref: '#/components/schemas/UserRole'
        createdAt:
          type: string
          format: date-time
          description: Account creation timestamp
          readOnly: true
          example: "2024-01-15T10:30:00Z"

    UserRole:
      type: string
      enum:
        - admin
        - user
        - viewer
      description: User permission level
```

### Request/Response Separation

- Define separate schemas for create, update, and response
- Use `readOnly` for server-generated fields (id, createdAt)
- Use `writeOnly` for sensitive fields (password)
- Never reuse the same schema for both request and response
  when they differ

```yaml
schemas:
  CreateUserRequest:
    type: object
    required:
      - email
      - name
      - password
    properties:
      email:
        type: string
        format: email
      name:
        type: string
        minLength: 1
      password:
        type: string
        format: password
        minLength: 8
        writeOnly: true

  UserResponse:
    type: object
    required:
      - id
      - email
      - name
      - role
      - createdAt
    properties:
      id:
        type: string
        format: uuid
        readOnly: true
      email:
        type: string
        format: email
      name:
        type: string
      role:
        $ref: '#/components/schemas/UserRole'
      createdAt:
        type: string
        format: date-time
        readOnly: true
```

### Composition Patterns

- Use `allOf` for inheritance/extension
- Use `oneOf` with discriminator for polymorphic types
- Use `$ref` for shared components — do not duplicate schemas

```yaml
# Polymorphic notification type
Notification:
  oneOf:
    - $ref: '#/components/schemas/EmailNotification'
    - $ref: '#/components/schemas/SmsNotification'
    - $ref: '#/components/schemas/PushNotification'
  discriminator:
    propertyName: channel
    mapping:
      email: '#/components/schemas/EmailNotification'
      sms: '#/components/schemas/SmsNotification'
      push: '#/components/schemas/PushNotification'
```

---

## 3. Path and Operation Design

### Operation Definition

```yaml
paths:
  /users:
    get:
      operationId: listUsers
      summary: List all users
      description: >-
        Returns a paginated list of users. Supports filtering
        by role and status.
      tags:
        - Users
      parameters:
        - $ref: '#/components/parameters/PageParam'
        - $ref: '#/components/parameters/LimitParam'
        - name: role
          in: query
          schema:
            $ref: '#/components/schemas/UserRole'
          description: Filter by user role
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserListResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '500':
          $ref: '#/components/responses/InternalError'
      security:
        - bearerAuth: []

    post:
      operationId: createUser
      summary: Create a new user
      tags:
        - Users
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateUserRequest'
            examples:
              admin:
                summary: Create admin user
                value:
                  email: "admin@example.com"
                  name: "Admin User"
                  password: "secureP@ss123"
      responses:
        '201':
          description: User created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '409':
          $ref: '#/components/responses/Conflict'
```

### Naming Rules

- `operationId`: camelCase, verb+noun (`listUsers`, `createOrder`,
  `getUserById`)
- `summary`: Short description (under 80 characters)
- `description`: Detailed explanation including business rules
- `tags`: Group related endpoints together

---

## 4. Reusable Components

### Shared Parameters

```yaml
components:
  parameters:
    PageParam:
      name: page
      in: query
      description: Page number (1-based)
      schema:
        type: integer
        minimum: 1
        default: 1

    LimitParam:
      name: limit
      in: query
      description: Number of items per page
      schema:
        type: integer
        minimum: 1
        maximum: 100
        default: 20
```

### Shared Responses

```yaml
components:
  responses:
    BadRequest:
      description: Invalid request parameters
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'

    Unauthorized:
      description: Authentication required
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'

    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'

    Conflict:
      description: Resource already exists
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'

    InternalError:
      description: Internal server error
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
```

---

## 5. Security Definitions

```yaml
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: JWT access token

    apiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
      description: API key for service-to-service calls

# Global security (can be overridden per operation)
security:
  - bearerAuth: []
```

---

## 6. Validation and Linting

### Validation Tools

- **Spectral**: Configurable OpenAPI linter with custom rules
- **openapi-generator validate**: Syntax and structure validation
- **Redocly CLI**: Validation, bundling, and preview

### Spectral Configuration

```yaml
# .spectral.yaml
extends:
  - spectral:oas

rules:
  operation-operationId: error
  operation-description: warn
  operation-tags: error
  info-contact: warn
  oas3-api-servers: error
  no-$ref-siblings: error

  # Custom rules
  path-must-use-kebab-case:
    given: "$.paths[*]~"
    then:
      function: pattern
      functionOptions:
        match: "^(/[a-z][a-z0-9-]*)+$"
    severity: error
    message: "Path segments must use kebab-case"
```

### CI Integration

```yaml
lint-openapi:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Lint OpenAPI spec
      uses: stoplightio/spectral-action@latest
      with:
        file_glob: 'openapi/openapi.yaml'
    - name: Validate spec
      run: npx @redocly/cli lint openapi/openapi.yaml
```

---

## 7. Documentation Generation

### Tool Selection

| Tool              | Output      | Use Case                  |
| ----------------- | ----------- | ------------------------- |
| Redoc             | Static HTML | Public API documentation  |
| Swagger UI        | Interactive | Developer portal/testing  |
| Stoplight         | Hosted docs | Team collaboration        |
| openapi-generator | Code SDKs   | Client library generation |

### Documentation Rules

- Every operation must have `summary` and `description`
- Every parameter must have `description`
- Every schema property must have `description` and `example`
- Use `externalDocs` for linking to guides and tutorials
- Include realistic examples for all request/response bodies

---

## 8. Code Generation

### Generator Rules

- Generate client SDKs and server stubs from the spec,
  not the other way around
- Treat generated code as build artifacts — do not manually edit
- Configure the generator to match your project's code style
- Run generation in CI to keep code and spec in sync

```bash
# Generate TypeScript client
npx @openapitools/openapi-generator-cli generate \
  -i openapi/openapi.yaml \
  -g typescript-axios \
  -o src/generated/api
```

---

## 9. Anti-Patterns

- Writing code first and generating the spec from code
- Using `additionalProperties: true` by default
- Defining inline schemas instead of reusable components
- Missing error responses — document all possible error codes
- Using generic descriptions like "Returns data" or "Request body"
- Forgetting `required` arrays — all required fields must be listed
- Duplicating schemas instead of using `$ref`
- Mixing API versions in a single spec file
- Skipping validation in CI — spec drift causes integration failures
- Not versioning the spec alongside the codebase

---

## 10. Related Skills

- **api-design**: REST API design principles and patterns
- **code-quality**: General code quality for generated code review
- **ci-cd**: CI pipeline integration for spec validation

## 11. Additional References

- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html) — Official OpenAPI specification
- [Swagger Editor](https://editor.swagger.io/) — Browser-based spec editor
- [Spectral](https://docs.stoplight.io/docs/spectral/) — OpenAPI linting tool
- [Redocly CLI](https://redocly.com/docs/cli/) — OpenAPI validation and bundling
