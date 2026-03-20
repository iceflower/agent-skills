---
name: openapi-spec
description: >-
  OpenAPI specification writing guide including schema design,
  documentation generation, validation, and versioning.
  Use when writing or reviewing OpenAPI specifications.
---

# OpenAPI Specification Rules

## 1. Document Structure

### Root Structure

- Use **OpenAPI 3.1** (or 3.0.3 minimum) for all new specifications
- Organize the specification in a consistent top-level order
- Provide complete `info` metadata including description, version, and contact

```yaml
openapi: 3.1.0
info:
  title: User Management API
  description: |
    API for managing users, roles, and permissions.
    Supports CRUD operations with pagination and filtering.
  version: 1.2.0
  contact:
    name: Platform Team
    email: platform@example.com
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: https://api.example.com/v1
    description: Production
  - url: https://staging-api.example.com/v1
    description: Staging

tags:
  - name: Users
    description: User management operations
  - name: Roles
    description: Role and permission management

paths:
  # ... path definitions

components:
  schemas:
    # ... schema definitions
  securitySchemes:
    # ... security definitions
```

### File Organization for Large APIs

- Split large specs into multiple files using `$ref`
- Organize by domain (users, orders, products) or by type (paths, schemas)
- Use a consistent directory structure

```text
openapi/
  openapi.yaml          # root document
  paths/
    users.yaml
    orders.yaml
    products.yaml
  schemas/
    User.yaml
    Order.yaml
    Product.yaml
    common/
      Pagination.yaml
      Error.yaml
  parameters/
    common.yaml
  examples/
    users.yaml
```

## 2. Path Definitions

### Path Naming Conventions

- Use **plural nouns** for resource collections (`/users`, `/orders`)
- Use **kebab-case** for multi-word paths (`/order-items`)
- Represent hierarchy through nesting (`/users/{userId}/orders`)
- Limit nesting to 2 levels; flatten deeper relationships with query parameters

### Operation Structure

- Provide a unique `operationId` for every operation (used for code generation)
- Use `camelCase` for `operationId` values
- Include `summary` (short) and `description` (detailed) for every operation
- Tag every operation for logical grouping

```yaml
paths:
  /users:
    get:
      operationId: listUsers
      summary: List all users
      description: |
        Returns a paginated list of users. Supports filtering
        by role and searching by name or email.
      tags:
        - Users
      parameters:
        - $ref: '#/components/parameters/PageParam'
        - $ref: '#/components/parameters/PageSizeParam'
        - name: role
          in: query
          schema:
            $ref: '#/components/schemas/UserRole'
        - name: search
          in: query
          description: Search by name or email (case-insensitive)
          schema:
            type: string
            minLength: 2
            maxLength: 100
      responses:
        '200':
          description: Successful response with paginated user list
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserListResponse'
              example:
                $ref: '#/components/examples/UserListExample'
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'

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
      responses:
        '201':
          description: User created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
          headers:
            Location:
              description: URL of the created user
              schema:
                type: string
                format: uri
        '400':
          $ref: '#/components/responses/BadRequest'
        '409':
          $ref: '#/components/responses/Conflict'
```

### Path Parameters

- Define path parameters at the path level, not per-operation
- Use descriptive parameter names (`userId` not `id`)
- Always include `description`, `schema`, and `example`

## 3. Schema Design

### Schema Best Practices

- Define schemas in `components/schemas` and reference with `$ref`
- Use `required` arrays to explicitly list required properties
- Set `additionalProperties: false` to prevent undocumented fields
- Include `description` for every property
- Use `format` hints (`date-time`, `email`, `uri`, `uuid`) for string types

```yaml
components:
  schemas:
    User:
      type: object
      required:
        - id
        - name
        - email
        - role
        - createdAt
      properties:
        id:
          type: string
          format: uuid
          description: Unique identifier for the user
          readOnly: true
        name:
          type: string
          minLength: 1
          maxLength: 100
          description: Full name of the user
        email:
          type: string
          format: email
          description: Email address (must be unique)
        role:
          $ref: '#/components/schemas/UserRole'
        avatar:
          type: string
          format: uri
          description: URL to the user's avatar image
          nullable: true
        createdAt:
          type: string
          format: date-time
          description: Timestamp when the user was created
          readOnly: true
        updatedAt:
          type: string
          format: date-time
          description: Timestamp of the last update
          readOnly: true
      additionalProperties: false
```

### Enumeration Types

```yaml
components:
  schemas:
    UserRole:
      type: string
      enum:
        - admin
        - editor
        - viewer
      description: Role assigned to the user

    OrderStatus:
      type: string
      enum:
        - pending
        - confirmed
        - shipped
        - delivered
        - cancelled
      description: Current status of the order
```

### Request and Response Separation

- Define separate schemas for create, update, and response objects
- Use `readOnly` and `writeOnly` when shared schemas are necessary
- Never expose internal fields (database IDs, audit columns) in create requests

```yaml
components:
  schemas:
    CreateUserRequest:
      type: object
      required:
        - name
        - email
        - role
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 100
        email:
          type: string
          format: email
        role:
          $ref: '#/components/schemas/UserRole'
        password:
          type: string
          format: password
          minLength: 8
          writeOnly: true
      additionalProperties: false

```

## 4. Component Reuse

### Reuse Principles

- Define reusable `responses`, `parameters`, `schemas`, and `examples` under `components`
- Reference with `$ref` everywhere; never duplicate schema definitions inline
- Create standard error response components (`BadRequest`, `Unauthorized`, `NotFound`, `Conflict`)
- Create standard pagination parameters (`page`, `pageSize`) and a shared `PaginationMeta` schema

### Error Response Pattern

```yaml
components:
  schemas:
    ErrorResponse:
      type: object
      required:
        - code
        - message
      properties:
        code:
          type: string
          description: Machine-readable error code
          example: VALIDATION_ERROR
        message:
          type: string
          description: Human-readable error message
        details:
          type: array
          items:
            type: object
            properties:
              field:
                type: string
              message:
                type: string
      additionalProperties: false

  responses:
    BadRequest:
      description: Invalid request parameters
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
```

### Security Schemes

- Define security schemes under `components/securitySchemes`
- Apply global security at the root level; override per-operation when needed

## 5. Documentation

### Description Writing

- Write `description` fields in complete sentences
- Include business context, not just technical details
- Document constraints, side effects, and rate limits
- Use Markdown in descriptions for formatting

- Include side effects, rate limits, and reversibility in operation descriptions

### Examples

- Provide examples for every schema and response
- Use realistic data (not "string", "test", or "foo")
- Cover common scenarios and edge cases in separate examples
- Define examples under `components/examples` and reference with `$ref`

## 6. Validation Tools

### Linting and Validation

- Validate specs with **Spectral** (or equivalent) in CI
- Use a shared ruleset for consistency across teams
- Fix all validation errors before merging

- Configure rules for `operationId`, `tags`, `description`, server URLs, and schema validation
- Add custom rules for path naming conventions and required descriptions

### Code Generation

- Use **openapi-generator** or **orval** for client/server code generation
- Generate TypeScript types from schemas to keep code in sync
- Regenerate on every spec change in CI

### Mock Servers

- Use **Prism** or **MSW** for mock servers based on the spec
- Run mock servers in development for frontend independence
- Validate that mock responses match the spec

## 7. Versioning

### URL-Based Versioning

- Include the major version in the URL path (`/v1/users`)
- Increment the major version only for breaking changes
- Maintain previous versions during a deprecation period

### Breaking vs Non-Breaking Changes

| Change Type                            | Breaking? |
| -------------------------------------- | --------- |
| Adding a new optional field            | No        |
| Adding a new endpoint                  | No        |
| Adding a new enum value                | No        |
| Removing a field                       | Yes       |
| Renaming a field                       | Yes       |
| Changing a field type                  | Yes       |
| Making an optional field required      | Yes       |
| Removing an enum value                 | Yes       |
| Changing the URL path                  | Yes       |

### Deprecation Process

- Mark deprecated fields with `deprecated: true` and describe the migration path
- Include a `Sunset` header with the removal date in responses
- Provide at least 6 months of deprecation notice for public APIs

## 8. Anti-Patterns

### Schema Anti-Patterns

- Do not use `additionalProperties: true` (default) for response schemas
- Do not define inline schemas; always use `$ref` to `components/schemas`
- Do not use `oneOf`/`anyOf` without a discriminator for polymorphic types
- Do not omit `required` arrays; be explicit about required fields
- Do not use `string` without `format` for dates, emails, URIs, or UUIDs

### Documentation Anti-Patterns

- Do not leave `description` empty on operations, parameters, or schemas
- Do not use placeholder examples ("string", "test", 0)
- Do not omit error responses; document at least 400, 401, 404, and 500
- Do not mix snake_case and camelCase in property names within the same API

### Versioning Anti-Patterns

- Do not make breaking changes without incrementing the major version
- Do not remove endpoints without a deprecation period
- Do not maintain more than 2 active major versions simultaneously
- Do not version individual endpoints differently from the rest of the API

### Tooling Anti-Patterns

- Do not skip spec validation in CI
- Do not manually keep client code in sync; use code generation
- Do not write specs after implementation; write spec first (design-first approach)
- Do not ignore Spectral warnings; fix them or explicitly disable with justification

## 9. Related Skills

- `api-design` - REST API design principles complementing OpenAPI specs
- `typescript-convention` - TypeScript types generated from OpenAPI schemas
- `code-quality` - Code quality rules for generated and handwritten code
- `ci-cd` - CI/CD integration for spec validation and code generation
