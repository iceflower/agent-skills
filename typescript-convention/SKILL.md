---
name: typescript-convention
description: >-
  TypeScript coding conventions including type system best practices,
  strict mode configuration, utility types, error handling, and project
  organization patterns.
  Use when writing, reviewing, or refactoring TypeScript code.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# TypeScript Coding Conventions

## 1. Strict Mode and Configuration

### Mandatory Compiler Options

```jsonc
// tsconfig.json — non-negotiable strict settings
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "exactOptionalPropertyTypes": true,
    "forceConsistentCasingInFileNames": true,
    "verbatimModuleSyntax": true
  }
}
```

### What `strict: true` Enables

- `strictNullChecks` — `null` and `undefined` are distinct types
- `strictFunctionTypes` — contravariant function parameter checking
- `strictBindCallApply` — correct types for `bind`, `call`, `apply`
- `strictPropertyInitialization` — class properties must be initialized
- `noImplicitAny` — no implicit `any` types
- `noImplicitThis` — `this` must have an explicit type
- `alwaysStrict` — emit `"use strict"` in every file

### Rules

- Never disable `strict` mode for convenience
- If a library lacks types, write a declaration file (`*.d.ts`)
  rather than using `any`
- Fix type errors instead of suppressing them with `@ts-ignore`
- Use `@ts-expect-error` only when a type error is genuinely expected
  (e.g., testing invalid inputs) — and add a comment explaining why

---

## 2. Type Design Principles

### Prefer Narrow Types

- Use the most specific type that accurately represents the data
- Prefer union types over broad primitives
- Use `as const` for literal types when values are fixed

```typescript
// Bad: Too broad
function setStatus(status: string) {}

// Good: Narrow and type-safe
type OrderStatus = 'pending' | 'confirmed' | 'shipped' | 'delivered';
function setStatus(status: OrderStatus) {}
```

### Type vs Interface

- Use `interface` for object shapes that may be extended or implemented
- Use `type` for unions, intersections, mapped types, and utility types
- Be consistent within a project — pick one default and document it
- Both are valid for plain object shapes; prefer `interface`
  for public API contracts

```typescript
// Interface: extensible object shape
interface User {
  id: string;
  name: string;
  email: string;
}

// Type: union, intersection, utility
type Result<T> = { success: true; data: T } | { success: false; error: string };
type ReadonlyUser = Readonly<User>;
type UserKeys = keyof User;
```

### Discriminated Unions

- Use discriminated unions for modeling states with different data shapes
- Always include a `type` or `kind` discriminant property
- Use exhaustive checks with `never` to catch unhandled cases

```typescript
type ApiResponse<T> =
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: string };

function handleResponse<T>(response: ApiResponse<T>) {
  switch (response.status) {
    case 'loading':
      return showSpinner();
    case 'success':
      return renderData(response.data);
    case 'error':
      return showError(response.error);
    default:
      // Exhaustive check — compile error if a case is missed
      const _exhaustive: never = response;
      return _exhaustive;
  }
}
```

---

## 3. Utility Types and Generics

### Built-in Utility Types

| Utility           | Purpose                                    |
| ----------------- | ------------------------------------------ |
| `Partial<T>`      | Make all properties optional               |
| `Required<T>`     | Make all properties required               |
| `Readonly<T>`     | Make all properties readonly               |
| `Pick<T, K>`      | Select specific properties                 |
| `Omit<T, K>`      | Exclude specific properties                |
| `Record<K, V>`    | Create an object type with key/value types |
| `Extract<T, U>`   | Extract union members matching U           |
| `Exclude<T, U>`   | Remove union members matching U            |
| `NonNullable<T>`  | Remove null and undefined                  |
| `ReturnType<T>`   | Get function return type                   |
| `Parameters<T>`   | Get function parameter types as tuple      |

### Generic Constraints

- Always constrain generics to the minimum required shape
- Use `extends` to specify constraints
- Provide default type parameters when a sensible default exists

```typescript
// Bad: Unconstrained generic
function getProperty<T>(obj: T, key: string) {
  return (obj as any)[key]; // unsafe
}

// Good: Constrained generic
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key]; // type-safe
}
```

### Avoid Over-Abstraction

- Do not create generics unless the type will be reused
  with different type arguments
- A concrete type is simpler and clearer than an unused generic
- Extract generic types only when you see real duplication

---

## 4. Null and Undefined Handling

### Null Safety Rules

- Always enable `strictNullChecks` (included in `strict: true`)
- Use `undefined` for optional/missing values,
  `null` for intentional absence
- Never use `!` (non-null assertion) in production code
  unless the invariant is documented and guaranteed
- Prefer optional chaining (`?.`) and nullish coalescing (`??`)

```typescript
// Bad: Non-null assertion hiding potential bugs
const name = user!.name;

// Good: Explicit handling
const name = user?.name ?? 'Unknown';

// Good: Type guard with early return
function processUser(user: User | undefined) {
  if (!user) {
    throw new Error('User is required');
  }
  // user is narrowed to User here
  return user.name;
}
```

### Optional Properties vs Undefined

```typescript
// Optional property: key may not exist
interface Config {
  timeout?: number; // { timeout: 500 } or {}
}

// Explicit undefined: key exists but may have no value
interface Config {
  timeout: number | undefined; // { timeout: 500 } or { timeout: undefined }
}
```

---

## 5. Function and Module Patterns

### Function Signatures

- Use explicit return types for public/exported functions
- Use inferred types for internal helper functions
- Prefer named parameters (object destructuring) for 3+ parameters

```typescript
// Bad: Positional parameters
function createUser(
  name: string,
  email: string,
  role: string,
  isActive: boolean
) {}

// Good: Named parameters
interface CreateUserParams {
  name: string;
  email: string;
  role: UserRole;
  isActive: boolean;
}

function createUser(params: CreateUserParams): User {
  // ...
}
```

### Overloads

- Use function overloads when the return type depends on input type
- Keep the implementation signature broader than all overloads
- Prefer union types or generics over overloads when possible

```typescript
function parse(input: string): ParsedText;
function parse(input: Buffer): ParsedBinary;
function parse(input: string | Buffer): ParsedText | ParsedBinary {
  // implementation
}
```

### Module Organization

- One exported entity per file for major types and classes
- Group related utilities in a single module file
- Use barrel exports (`index.ts`) at module boundaries only
- Avoid deep barrel re-exports — they cause circular dependency risks

---

## 6. Error Handling

### Typed Errors

```typescript
// Define error types with discriminants
class NotFoundError extends Error {
  readonly code = 'NOT_FOUND' as const;
  constructor(resource: string, id: string) {
    super(`${resource} with id ${id} not found`);
    this.name = 'NotFoundError';
  }
}

class ValidationError extends Error {
  readonly code = 'VALIDATION_ERROR' as const;
  constructor(
    message: string,
    public readonly fields: Record<string, string>
  ) {
    super(message);
    this.name = 'ValidationError';
  }
}
```

### Result Pattern (for expected failures)

```typescript
type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

function parseConfig(raw: string): Result<Config, ValidationError> {
  try {
    const parsed = JSON.parse(raw);
    // validate...
    return { ok: true, value: parsed as Config };
  } catch (e) {
    return { ok: false, error: new ValidationError('Invalid config', {}) };
  }
}

// Caller handles both cases explicitly
const result = parseConfig(input);
if (!result.ok) {
  console.error(result.error.message);
  return;
}
// result.value is typed as Config here
```

---

## 7. Type Assertion and Narrowing

### Prefer Type Guards Over Assertions

```typescript
// Bad: Type assertion (bypasses type checker)
const user = data as User;

// Good: Type guard (runtime verified)
function isUser(data: unknown): data is User {
  return (
    typeof data === 'object' &&
    data !== null &&
    'id' in data &&
    'name' in data
  );
}

if (isUser(data)) {
  // data is narrowed to User
}
```

### Zod for Runtime Validation

```typescript
import { z } from 'zod';

const UserSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(100),
  email: z.string().email(),
  role: z.enum(['admin', 'user', 'viewer']),
});

type User = z.infer<typeof UserSchema>;

// Validates at runtime AND infers TypeScript type
const user = UserSchema.parse(unknownData);
```

---

## 8. Anti-Patterns

- Using `any` instead of `unknown` for values of uncertain type
- Disabling strict mode or individual strict checks
- Using `@ts-ignore` instead of fixing the type error
- Using type assertions (`as`) to silence the compiler
  when a type guard is possible
- Declaring `enum` with numeric values — prefer string enums
  or `as const` objects
- Exporting mutable state from modules
- Using `Function` type — use specific function signatures instead
- Creating deeply nested generic types that are unreadable
- Using `object` type — use `Record<string, unknown>` or a specific shape
- Relying on declaration merging when explicit extension is clearer

---

## 9. Related Skills

- **code-quality**: General code quality principles
- **react-convention**: React-specific TypeScript patterns
- **testing**: Testing strategies for TypeScript code

## 10. Additional References

- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/) — Official TypeScript documentation
- [TypeScript Performance Wiki](https://github.com/microsoft/TypeScript/wiki/Performance) — Compiler performance tips
- [Total TypeScript](https://www.totaltypescript.com/) — Advanced TypeScript patterns and tutorials
