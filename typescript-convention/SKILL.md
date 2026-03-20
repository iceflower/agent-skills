---
name: typescript-convention
description: >-
  TypeScript coding conventions including type system best practices,
  strict mode configuration, utility types, and module patterns.
  Use when writing or reviewing TypeScript code.
---

# TypeScript Coding Conventions

## 1. Type System Rules

### Prefer Interfaces for Object Shapes

- Use `interface` for object types that may be extended or implemented
- Use `type` for unions, intersections, mapped types, and utility compositions
- Do not mix `interface` and `type` for the same purpose within a project

```typescript
// Good: interface for object shapes
interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
}

interface AdminUser extends User {
  permissions: Permission[];
}

// Good: type for unions and compositions
type UserRole = 'admin' | 'editor' | 'viewer';
type UserResponse = SuccessResponse<User> | ErrorResponse;
type Nullable<T> = T | null;
```

### Explicit Return Types

- Always declare explicit return types for exported functions and public methods
- Inferred types are acceptable for private helper functions and closures
- Always declare return types for functions that return complex or conditional types

```typescript
// Good: explicit return type for exported function
export function findUser(id: string): User | undefined {
  return users.find(u => u.id === id);
}

// Good: explicit return type for async function
export async function fetchUsers(): Promise<User[]> {
  const response = await api.get('/users');
  return response.data;
}

// Acceptable: inferred for simple private helper
const double = (n: number) => n * 2;
```

### Avoid `any`

- Never use `any` unless absolutely unavoidable (e.g., third-party library gaps)
- Use `unknown` when the type is genuinely unknown; narrow before use
- Use `Record<string, unknown>` instead of `object` for generic key-value maps
- Add `// eslint-disable-next-line @typescript-eslint/no-explicit-any` with a comment when `any` is required

```typescript
// Bad
function parse(input: any): any {
  return JSON.parse(input);
}

// Good: use unknown and narrow
function parse(input: string): unknown {
  return JSON.parse(input);
}

function isUser(value: unknown): value is User {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'name' in value
  );
}
```

### Const Assertions and Enums

- Prefer `as const` objects over TypeScript enums for simple value sets
- Use enums only when you need reverse mapping or the values are purely internal
- Always use string enums if you use enums; avoid numeric enums

```typescript
// Preferred: const assertion
const HttpStatus = {
  OK: 200,
  NOT_FOUND: 404,
  INTERNAL_ERROR: 500,
} as const;

type HttpStatus = (typeof HttpStatus)[keyof typeof HttpStatus];

// Acceptable: string enum when reverse mapping is useful
enum OrderStatus {
  Pending = 'PENDING',
  Confirmed = 'CONFIRMED',
  Shipped = 'SHIPPED',
  Delivered = 'DELIVERED',
}
```

## 2. Strict Mode Configuration

### Required tsconfig Settings

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "exactOptionalPropertyTypes": true,
    "forceConsistentCasingInFileNames": true,
    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  }
}
```

### Strict Mode Impact

| Flag                              | What It Catches                                 |
| --------------------------------- | ----------------------------------------------- |
| `strictNullChecks`                | Prevents accessing `.property` on `null`/`undefined` |
| `strictFunctionTypes`             | Catches contravariant function parameter bugs   |
| `noUncheckedIndexedAccess`        | Array/object index returns `T \| undefined`     |
| `exactOptionalPropertyTypes`      | Distinguishes `undefined` from missing property |
| `noImplicitOverride`              | Requires `override` keyword for inherited methods |
| `noPropertyAccessFromIndexSignature` | Forces bracket notation for index signatures |

### Migration Strategy

- Enable `strict: true` for all new projects from day one
- For existing projects, enable strict flags incrementally
- Use `// @ts-expect-error` (not `// @ts-ignore`) for temporary suppressions
- Track and reduce `@ts-expect-error` count over time

## 3. Utility Types

### Built-In Utility Types

```typescript
// Partial: make all properties optional
function updateUser(id: string, updates: Partial<User>): User {
  return { ...getUser(id), ...updates };
}

// Pick and Omit: select or exclude properties
type UserPreview = Pick<User, 'id' | 'name'>;
type CreateUserInput = Omit<User, 'id' | 'createdAt'>;

// Required: make all properties required
type CompleteUser = Required<User>;

// Readonly: make all properties readonly
type FrozenConfig = Readonly<AppConfig>;

// Record: typed key-value map
type PermissionMap = Record<UserRole, Permission[]>;
```

### Custom Utility Types

```typescript
// Deep partial
type DeepPartial<T> = {
  [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K];
};

// Deep readonly
type DeepReadonly<T> = {
  readonly [K in keyof T]: T[K] extends object ? DeepReadonly<T[K]> : T[K];
};

// Non-nullable properties
type NonNullableFields<T> = {
  [K in keyof T]: NonNullable<T[K]>;
};

// Brand type for nominal typing
type Brand<T, B extends string> = T & { readonly __brand: B };
type UserId = Brand<string, 'UserId'>;
type OrderId = Brand<string, 'OrderId'>;

function getUser(id: UserId): User { /* ... */ }
// getUser('raw-string') // Error: not assignable to UserId
// getUser('abc' as UserId) // OK
```

## 4. Generics

### Generic Function Patterns

- Constrain generics with `extends` to provide type safety
- Use meaningful names: `T` for single types, `TKey`/`TValue` for maps, `TInput`/`TOutput` for transforms
- Avoid unnecessary generics; use them only when the function genuinely works with multiple types

```typescript
// Good: constrained generic
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

// Good: generic with default
function createList<T = string>(items: T[]): { items: T[]; count: number } {
  return { items, count: items.length };
}

// Bad: unnecessary generic (string is always string)
function formatName<T extends string>(name: T): string {
  return name.trim().toLowerCase();
}

// Good: just use string
function formatName(name: string): string {
  return name.trim().toLowerCase();
}
```

### Generic Interface Patterns

```typescript
// Generic repository
interface Repository<T extends { id: string }> {
  findById(id: string): Promise<T | undefined>;
  findAll(filter?: Partial<T>): Promise<T[]>;
  save(entity: T): Promise<T>;
  delete(id: string): Promise<void>;
}

// Generic result type
type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E };

function ok<T>(data: T): Result<T> {
  return { success: true, data };
}

function err<E = Error>(error: E): Result<never, E> {
  return { success: false, error };
}

// Usage
async function fetchUser(id: string): Promise<Result<User>> {
  try {
    const user = await api.get<User>(`/users/${id}`);
    return ok(user);
  } catch (e) {
    return err(e instanceof Error ? e : new Error(String(e)));
  }
}
```

## 5. Module Patterns

### Barrel Exports

- Use `index.ts` barrel files to simplify imports from a module
- Re-export only the public API; keep internal modules private
- Avoid deep barrel nesting (max 2 levels)

```typescript
// features/users/index.ts
export { UserService } from './UserService';
export { UserRepository } from './UserRepository';
export type { User, CreateUserInput, UserFilters } from './types';

// Do NOT export internal helpers
// export { hashPassword } from './utils'; // internal
```

### Module Organization

```text
src/
  features/
    users/
      index.ts          # public barrel export
      types.ts           # types and interfaces
      UserService.ts     # business logic
      UserRepository.ts  # data access
      UserController.ts  # HTTP handler
      __tests__/
        UserService.test.ts
  shared/
    types/
      index.ts
      common.ts
      api.ts
    utils/
      index.ts
      date.ts
      string.ts
```

### Import Rules

- Use **path aliases** (`@/features/users`) instead of relative paths with `../../../`
- Configure path aliases in both `tsconfig.json` and bundler config
- Sort imports: external packages first, then internal modules, then relative files
- Never use default exports; always use named exports

```typescript
// Good: organized imports with path aliases
import { Router } from 'express';
import { z } from 'zod';

import { UserService } from '@/features/users';
import { AuthMiddleware } from '@/middleware/auth';
import { validate } from '@/shared/utils';

import { createUserSchema } from './schemas';
```

## 6. Error Handling

### Typed Error Handling

- Define domain-specific error classes extending `Error`
- Use discriminated unions for error results
- Never throw untyped errors; always include error codes and context

```typescript
// Domain error hierarchy
class AppError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: number,
    public readonly cause?: Error,
  ) {
    super(message);
    this.name = this.constructor.name;
  }
}

class NotFoundError extends AppError {
  constructor(resource: string, id: string, cause?: Error) {
    super(`${resource} with id ${id} not found`, 'NOT_FOUND', 404, cause);
  }
}

class ValidationError extends AppError {
  constructor(
    message: string,
    public readonly fields: Record<string, string>,
    cause?: Error,
  ) {
    super(message, 'VALIDATION_ERROR', 400, cause);
  }
}
```

## 7. Type Narrowing and Guards

### Type Guard Functions

```typescript
// Custom type guard
function isNonNull<T>(value: T | null | undefined): value is T {
  return value != null;
}

// Usage: filter null values with type safety
const users: (User | null)[] = await Promise.all(ids.map(findUser));
const validUsers: User[] = users.filter(isNonNull);

// Discriminated union narrowing
type Shape =
  | { kind: 'circle'; radius: number }
  | { kind: 'rectangle'; width: number; height: number };

function area(shape: Shape): number {
  switch (shape.kind) {
    case 'circle':
      return Math.PI * shape.radius ** 2;
    case 'rectangle':
      return shape.width * shape.height;
    default:
      // Exhaustiveness check
      const _exhaustive: never = shape;
      return _exhaustive;
  }
}
```

## 8. Anti-Patterns

### Type System Anti-Patterns

- Do not use `any` as a quick fix; use `unknown` and narrow
- Do not use `!` (non-null assertion) unless you have verified the value exists
- Do not use `as` type assertions to silence errors; fix the root type mismatch
- Do not create `god interfaces` with dozens of optional properties
- Do not use `Function` type; use specific function signatures

```typescript
// Bad
const handler: Function = () => {};

// Good
type EventHandler = (event: AppEvent) => void;
const handler: EventHandler = (event) => { /* ... */ };
```

### Module Anti-Patterns

- Do not use `default export`; always use `named export`
- Do not create circular dependencies between modules
- Do not export everything; keep internal implementation details private
- Do not use relative paths deeper than 2 levels (`../../..`); use path aliases

### Configuration Anti-Patterns

- Do not start a new project without `strict: true`
- Do not suppress errors with `@ts-ignore`; use `@ts-expect-error` if needed
- Do not disable strict flags to avoid fixing type errors
- Do not use `skipLibCheck: false` in application code (slows compilation significantly)

### Code Style Anti-Patterns

- Do not use `I` prefix for interfaces (`IUser`); use plain names (`User`)
- Do not suffix types with `Type` (`UserType`); use plain names (`User`)
- Do not create wrapper types that add no type safety
- Do not use `namespace`; use ES modules instead

## 9. Related Skills

- `react-convention` - React/Next.js patterns that build on TypeScript types
- `code-quality` - General code quality rules applicable to TypeScript
- `testing` - Testing strategies for TypeScript projects
- `error-handling` - Error handling patterns used across languages
