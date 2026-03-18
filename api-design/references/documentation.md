# API Documentation

## OpenAPI Specification Structure

### Required Sections

```yaml
openapi: 3.1.0
info:
  title: Service Name API
  version: 1.0.0
  description: Brief service description
  contact:
    name: Team Name

servers:
  - url: https://api.example.com/v1
    description: Production

paths:
  /resources:
    get:
      summary: Short action description
      operationId: listResources
      tags:
        - Resources
      parameters: []
      responses: {}

components:
  schemas: {}
  securitySchemes: {}
```

### General Documentation Rules

- Every endpoint must have a `summary` (short) and optionally a `description` (detailed)
- Use `operationId` for unique identification — must be unique across the spec
- Group related endpoints with `tags`
- Define reusable schemas in `components/schemas`
- Define security schemes in `components/securitySchemes`

## Schema Documentation

### Request/Response Schema

```yaml
components:
  schemas:
    User:
      type: object
      required:
        - name
        - email
      properties:
        id:
          type: integer
          format: int64
          description: Unique user identifier
          readOnly: true
          example: 42
        name:
          type: string
          minLength: 2
          maxLength: 50
          description: User display name
          example: John Doe
        email:
          type: string
          format: email
          description: User email address
          example: john@example.com
        status:
          type: string
          enum:
            - ACTIVE
            - INACTIVE
            - SUSPENDED
          description: Current account status
          example: ACTIVE
```

### Schema Rules

- Always include `description` for non-obvious fields
- Always include `example` values for documentation clarity
- Use `required` to mark mandatory fields explicitly
- Use `format` for standard types (email, date-time, uri, uuid)
- Use `readOnly` for fields that appear only in responses
- Use `writeOnly` for fields that appear only in requests (e.g., password)

## Error Response Documentation

### Standard Error Schema

```yaml
components:
  schemas:
    ErrorResponse:
      type: object
      required:
        - error
      properties:
        error:
          type: object
          required:
            - code
            - message
          properties:
            code:
              type: string
              description: Machine-readable error code
              example: ENTITY_NOT_FOUND
            message:
              type: string
              description: Human-readable error message
              example: "User not found: 42"
            details:
              type: array
              items:
                $ref: "#/components/schemas/FieldError"
        meta:
          $ref: "#/components/schemas/ResponseMeta"
```

### Error Documentation Rules

- Document all possible error responses for each endpoint
- Use `$ref` to reuse common error schemas
- Include realistic error examples
- Document error codes with their meanings in a central location

## Parameter Documentation

### Path and Query Parameters

```yaml
parameters:
  - name: userId
    in: path
    required: true
    description: Unique user identifier
    schema:
      type: integer
      format: int64
      minimum: 1
    example: 42
  - name: status
    in: query
    required: false
    description: Filter by account status
    schema:
      type: string
      enum:
        - ACTIVE
        - INACTIVE
    example: ACTIVE
  - name: page
    in: query
    required: false
    description: Page number (1-based)
    schema:
      type: integer
      minimum: 1
      default: 1
    example: 1
```

### Parameter Rules

- Always include `description` and `example`
- Specify `minimum`, `maximum`, `minLength`, `maxLength` constraints
- Use `default` for optional parameters with default values
- Define common parameters in `components/parameters` for reuse

## Authentication Documentation

```yaml
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: JWT access token

security:
  - BearerAuth: []
```

- Define security at the global level for default authentication
- Override per-endpoint for public endpoints (empty security array)
- Document token format and expiration in the description

## Versioning in Documentation

- Include API version in the spec `info.version`
- Document breaking changes between versions
- Maintain separate spec files per major version
- Mark deprecated endpoints with `deprecated: true` and migration notes

## Documentation Anti-Patterns

- Missing examples in schemas and parameters
- Undocumented error responses
- Inconsistent naming between spec and implementation
- Copy-pasted schemas instead of `$ref` references
- Missing authentication documentation
- No versioning strategy
- Stale documentation that does not match implementation