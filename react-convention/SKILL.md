---
name: react-convention
description: >-
  React and Next.js coding conventions including component patterns, hooks,
  state management, performance optimization, and project structure.
  Use when writing, reviewing, or refactoring React/Next.js code.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# React/Next.js Coding Conventions

## 1. Component Design Principles

### Component Types

- **Server Components** (Next.js App Router default): Use for data fetching,
  static content, and anything that does not need client interactivity
- **Client Components** (`'use client'`): Use only when browser APIs, event
  handlers, hooks with state/effects, or third-party client libraries are needed
- Keep Client Components as small and as low in the tree as possible

### Component Structure

```tsx
// 1. Imports (external → internal → types → styles)
import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/Button';
import type { UserProfile } from '@/types/user';
import styles from './UserCard.module.css';

// 2. Type definitions
interface UserCardProps {
  user: UserProfile;
  onSelect: (userId: string) => void;
}

// 3. Component definition (named export preferred)
export function UserCard({ user, onSelect }: UserCardProps) {
  // 3a. Hooks
  const [isExpanded, setIsExpanded] = useState(false);

  // 3b. Derived state and handlers
  const handleClick = useCallback(() => {
    onSelect(user.id);
  }, [onSelect, user.id]);

  // 3c. Early returns for edge cases
  if (!user) return null;

  // 3d. Render
  return (
    <div className={styles.card}>
      <h3>{user.name}</h3>
      <button onClick={handleClick}>Select</button>
    </div>
  );
}
```

### Naming Conventions

- **Components**: PascalCase (`UserProfile`, `OrderList`)
- **Hooks**: camelCase with `use` prefix (`useAuth`, `useDebounce`)
- **Event handlers**: `handle` prefix (`handleClick`, `handleSubmit`)
- **Props callbacks**: `on` prefix (`onClick`, `onSubmit`, `onSelect`)
- **Boolean props**: `is`/`has`/`should` prefix (`isLoading`, `hasError`)
- **Files**: Match the component name (`UserCard.tsx`, `useAuth.ts`)

---

## 2. Hooks Rules and Patterns

### Rules of Hooks

- Call hooks only at the top level — never inside loops, conditions,
  or nested functions
- Call hooks only from React function components or custom hooks
- Every custom hook must start with `use`

### Custom Hook Patterns

```tsx
// Encapsulate reusable stateful logic
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

// Return objects for named access (3+ return values)
function useAuth() {
  // ...
  return { user, isLoading, signIn, signOut };
}

// Return tuples for simple state + setter patterns
function useToggle(initial = false): [boolean, () => void] {
  const [value, setValue] = useState(initial);
  const toggle = useCallback(() => setValue((v) => !v), []);
  return [value, toggle];
}
```

### useEffect Guidelines

- Every effect must have a cleanup function if it creates subscriptions,
  timers, or event listeners
- Keep the dependency array accurate — never suppress the exhaustive-deps
  lint rule
- Prefer event handlers over effects for user-triggered actions
- Split unrelated effects into separate `useEffect` calls

```tsx
// Bad: Mixing unrelated logic
useEffect(() => {
  fetchUser(id);
  document.title = `User ${id}`;
  const timer = setInterval(pollStatus, 5000);
  return () => clearInterval(timer);
}, [id]);

// Good: Separate concerns
useEffect(() => { fetchUser(id); }, [id]);
useEffect(() => { document.title = `User ${id}`; }, [id]);
useEffect(() => {
  const timer = setInterval(pollStatus, 5000);
  return () => clearInterval(timer);
}, []);
```

---

## 3. State Management

### State Placement Decision

1. **Local state** (`useState`): UI-only state used by a single component
2. **Lifted state**: State shared by siblings — lift to nearest common parent
3. **Context**: Low-frequency global state (theme, auth, locale)
4. **External store** (Zustand, Jotai, Redux Toolkit): High-frequency or
   complex shared state

### State Rules

- Keep state as close to where it is used as possible
- Derive values instead of storing redundant state
- Never store values that can be computed from existing state or props
- Use `useReducer` when state transitions are complex or interdependent

```tsx
// Bad: Redundant state
const [items, setItems] = useState<Item[]>([]);
const [itemCount, setItemCount] = useState(0); // redundant

// Good: Derived value
const [items, setItems] = useState<Item[]>([]);
const itemCount = items.length; // computed
```

### Context Best Practices

- Split contexts by domain (AuthContext, ThemeContext) —
  never create a single global context
- Wrap context value in `useMemo` to prevent unnecessary re-renders
- Create a typed custom hook per context for consumer convenience

```tsx
const AuthContext = createContext<AuthState | null>(null);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

---

## 4. Performance Optimization

### Rendering Optimization

- Use `React.memo` only for components that re-render frequently
  with unchanged props — do not apply it everywhere
- Use `useMemo` for expensive computations,
  not for simple object/array creation
- Use `useCallback` for functions passed to memoized children
- Profile before optimizing — premature optimization adds complexity

### List Rendering

- Always use a stable, unique `key` — never use array index as key
  unless the list is static and never reordered
- Virtualize long lists (>100 items) using libraries like
  `@tanstack/react-virtual`

### Code Splitting

```tsx
// Lazy load heavy components
const HeavyChart = lazy(() => import('./HeavyChart'));

function Dashboard() {
  return (
    <Suspense fallback={<ChartSkeleton />}>
      <HeavyChart data={data} />
    </Suspense>
  );
}
```

### Image Optimization (Next.js)

- Always use `next/image` instead of plain `<img>` tags
- Set explicit `width` and `height` or use `fill` with a sized container
- Use `priority` for above-the-fold images (LCP candidates)
- Configure `remotePatterns` in `next.config.js` for external images

---

## 5. Next.js App Router Patterns

### Data Fetching

- Fetch data in Server Components — not in Client Components
- Use `fetch` with Next.js caching options in Server Components
- Co-locate data fetching with the component that consumes it
- Use `loading.tsx` for streaming Suspense boundaries

```tsx
// app/users/page.tsx — Server Component
async function UsersPage() {
  const users = await getUsers(); // Server-side fetch
  return <UserList users={users} />;
}
```

### Route Organization

```text
app/
  layout.tsx          # Root layout (shared across all pages)
  page.tsx            # Home page
  (auth)/             # Route group (no URL segment)
    login/page.tsx
    register/page.tsx
  users/
    page.tsx          # /users
    [id]/
      page.tsx        # /users/:id
      loading.tsx     # Suspense boundary
      error.tsx       # Error boundary
```

### Server Actions

- Define server actions in separate files with `'use server'` directive
- Validate all inputs on the server side — never trust client data
- Return structured responses, not raw errors

```tsx
'use server';

import { z } from 'zod';

const CreateUserSchema = z.object({
  name: z.string().min(1).max(100),
  email: z.string().email(),
});

export async function createUser(formData: FormData) {
  const parsed = CreateUserSchema.safeParse({
    name: formData.get('name'),
    email: formData.get('email'),
  });
  if (!parsed.success) {
    return { error: parsed.error.flatten() };
  }
  // ... create user
  return { success: true };
}
```

---

## 6. Error Handling Patterns

- Use Error Boundaries (`error.tsx` in App Router) for unexpected runtime errors
- Use conditional rendering for expected empty/error states
- Never let errors silently disappear — log or display them

```tsx
// app/users/error.tsx
'use client';

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div role="alert">
      <h2>Something went wrong</h2>
      <button onClick={reset}>Try again</button>
    </div>
  );
}
```

---

## 7. Testing Conventions

- Test behavior, not implementation details
- Use `@testing-library/react` — query by role, label, or text,
  not by class name or test ID
- Test user interactions with `userEvent` over `fireEvent`
- Mock external dependencies (API calls, routers) at the boundary

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

test('submits form with user input', async () => {
  const onSubmit = vi.fn();
  render(<LoginForm onSubmit={onSubmit} />);

  await userEvent.type(screen.getByLabelText('Email'), 'test@example.com');
  await userEvent.click(screen.getByRole('button', { name: 'Sign In' }));

  expect(onSubmit).toHaveBeenCalledWith({ email: 'test@example.com' });
});
```

---

## 8. Anti-Patterns

- Using `useEffect` for data fetching in Next.js App Router
  (use Server Components or TanStack Query instead)
- Passing too many props through multiple layers (prop drilling) —
  use composition or context
- Storing derived state in `useState`
- Suppressing `exhaustive-deps` lint warnings
- Using `any` for component props — always define typed interfaces
- Creating mega-components (>300 lines) instead of composing smaller ones
- Using `dangerouslySetInnerHTML` without sanitization
- Mutating state directly instead of using setter functions
- Calling `setState` in render without a condition (infinite loop)

---

## 9. Related Skills

- **code-quality**: General code quality principles applicable to React code
- **testing**: Testing strategies and patterns
- **typescript-convention**: TypeScript best practices for React projects

## 10. Additional References

- [React Documentation](https://react.dev/) — Official React docs
- [Next.js Documentation](https://nextjs.org/docs) — Official Next.js docs
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/) — TypeScript patterns for React
