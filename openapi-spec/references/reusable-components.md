# OpenAPI Reusable Components

## Shared Responses

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

## Shared Parameters

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

## Security Definitions

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

## Composition Patterns

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
