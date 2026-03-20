---
name: react-convention
description: >-
  React and Next.js coding conventions including component patterns, hooks,
  state management, performance optimization, and testing.
  Use when writing or reviewing React/Next.js code.
---

# React and Next.js Conventions

## 1. Component Design Rules

### File and Naming Conventions

- Use **PascalCase** for component names and filenames (`UserProfile.tsx`)
- Use **camelCase** for non-component files (`useAuth.ts`, `formatDate.ts`)
- One component per file; co-locate related types and helpers only when small
- Suffix hook files with `use` prefix (`useDebounce.ts`, `useLocalStorage.ts`)

### Component Declaration

- Prefer **function declarations** over arrow functions for top-level components
- Use **arrow functions** for inline callbacks and small helper components
- Always provide explicit return types for public components

```tsx
// Good: function declaration for components
function UserProfile({ userId }: UserProfileProps) {
  return <div>...</div>;
}

// Good: arrow function for small inline helpers
const Badge = ({ label }: { label: string }) => <span>{label}</span>;

// Bad: arrow function for top-level component
const UserProfile = ({ userId }: UserProfileProps) => {
  return <div>...</div>;
};
```

### Props Design

- Define props with a dedicated `interface` named `ComponentNameProps`
- Destructure props in the function signature
- Avoid passing more than 5-6 props; refactor with composition or context
- Use `children` prop for composition instead of render props when possible

```tsx
interface UserCardProps {
  user: User;
  isActive: boolean;
  onSelect: (userId: string) => void;
  children?: React.ReactNode;
}

function UserCard({ user, isActive, onSelect, children }: UserCardProps) {
  return (
    <div className={isActive ? 'active' : ''}>
      <h3>{user.name}</h3>
      {children}
      <button onClick={() => onSelect(user.id)}>Select</button>
    </div>
  );
}
```

### Component Composition

- Prefer **composition** over prop drilling
- Use **compound components** for tightly related UI groups
- Split large components into smaller, focused units

```tsx
// Good: compound component pattern
function Tabs({ children }: { children: React.ReactNode }) {
  const [activeIndex, setActiveIndex] = useState(0);
  return (
    <TabsContext.Provider value={{ activeIndex, setActiveIndex }}>
      {children}
    </TabsContext.Provider>
  );
}

Tabs.Panel = function TabPanel({ index, children }: TabPanelProps) {
  const { activeIndex } = useTabsContext();
  if (index !== activeIndex) return null;
  return <div role="tabpanel">{children}</div>;
};

Tabs.Button = function TabButton({ index, children }: TabButtonProps) {
  const { activeIndex, setActiveIndex } = useTabsContext();
  return (
    <button
      role="tab"
      aria-selected={index === activeIndex}
      onClick={() => setActiveIndex(index)}
    >
      {children}
    </button>
  );
};
```

## 2. Hooks Best Practices

### Custom Hook Rules

- Extract reusable logic into custom hooks
- Custom hooks must start with `use` prefix
- Return a tuple or object; prefer object for 3+ return values
- Keep hooks focused on a single concern

```tsx
// Good: focused custom hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

// Good: object return for multiple values
function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const login = useCallback(async (credentials: Credentials) => {
    setIsLoading(true);
    const user = await authService.login(credentials);
    setUser(user);
    setIsLoading(false);
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  return { user, isLoading, login, logout };
}
```

### useEffect Guidelines

- Always specify the dependency array
- Return a cleanup function for subscriptions, timers, and event listeners
- Do not use `useEffect` for derived state; compute during render instead
- Keep effects focused; split unrelated effects into separate `useEffect` calls

```tsx
// Bad: derived state in useEffect
function UserList({ users }: { users: User[] }) {
  const [sortedUsers, setSortedUsers] = useState<User[]>([]);
  useEffect(() => {
    setSortedUsers([...users].sort((a, b) => a.name.localeCompare(b.name)));
  }, [users]);
  return <ul>{sortedUsers.map(u => <li key={u.id}>{u.name}</li>)}</ul>;
}

// Good: compute during render
function UserList({ users }: { users: User[] }) {
  const sortedUsers = useMemo(
    () => [...users].sort((a, b) => a.name.localeCompare(b.name)),
    [users]
  );
  return <ul>{sortedUsers.map(u => <li key={u.id}>{u.name}</li>)}</ul>;
}
```

### Rules of Hooks

- Never call hooks inside conditions, loops, or nested functions
- Never call hooks from regular JavaScript functions (only from components or custom hooks)

## 3. State Management Patterns

### Local vs Global State

- Start with **local state** (`useState`); lift only when sharing is needed
- Use **context** for low-frequency global state (theme, locale, auth)
- Use **external stores** (Zustand, Jotai, Redux Toolkit) for high-frequency or complex global state
- Co-locate state with the components that use it

### Context Usage

- Provide a custom hook for each context to avoid raw `useContext` calls
- Split contexts by domain to prevent unnecessary re-renders
- Never put rapidly changing values in context without memoization

```tsx
// Good: context with custom hook
const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>('light');
  const value = useMemo(() => ({ theme, setTheme }), [theme]);
  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}
```

### Server State

- Use **TanStack Query** (React Query) or **SWR** for server state
- Configure `staleTime` and `gcTime` (cacheTime) appropriately
- Prefer `queryKey` factories for consistent cache key generation

```tsx
// Good: query key factory
const userKeys = {
  all: ['users'] as const,
  lists: () => [...userKeys.all, 'list'] as const,
  list: (filters: UserFilters) => [...userKeys.lists(), filters] as const,
  details: () => [...userKeys.all, 'detail'] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
};

function useUser(userId: string) {
  return useQuery({
    queryKey: userKeys.detail(userId),
    queryFn: () => fetchUser(userId),
    staleTime: 5 * 60 * 1000,
  });
}
```

## 4. Performance Optimization

### Memoization Rules

- Do not memoize by default; measure first
- Use `React.memo` for components that re-render frequently with same props
- Use `useMemo` for expensive computations only
- Use `useCallback` for callbacks passed to memoized children

```tsx
// Good: memo when parent re-renders frequently but child props are stable
const ExpensiveList = React.memo(function ExpensiveList({ items }: { items: Item[] }) {
  return (
    <ul>
      {items.map(item => (
        <li key={item.id}>{expensiveFormat(item)}</li>
      ))}
    </ul>
  );
});

// Parent component
function Dashboard() {
  const [count, setCount] = useState(0);
  const items = useMemo(() => computeItems(data), [data]);
  const handleSelect = useCallback((id: string) => {
    selectItem(id);
  }, []);

  return (
    <>
      <button onClick={() => setCount(c => c + 1)}>{count}</button>
      <ExpensiveList items={items} onSelect={handleSelect} />
    </>
  );
}
```

### Rendering Optimization

- Use **key** prop correctly; avoid index as key for dynamic lists
- Lazy load routes and heavy components with `React.lazy` and `Suspense`
- Virtualize long lists with `react-window` or `@tanstack/react-virtual`
- Avoid creating objects or arrays inline in JSX when passed as props

```tsx
// Good: lazy loading routes
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Settings = React.lazy(() => import('./pages/Settings'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Suspense>
  );
}
```

## 5. Next.js Conventions

### App Router Patterns

- Use **Server Components** by default; add `'use client'` only when needed
- Keep client components small and push them to the leaf nodes
- Use `loading.tsx` and `error.tsx` for route-level loading/error states
- Prefer **Server Actions** for form mutations over API routes

```tsx
// app/users/page.tsx - Server Component (default)
async function UsersPage() {
  const users = await getUsers(); // direct server-side data fetch
  return (
    <div>
      <h1>Users</h1>
      <UserList users={users} />
      <AddUserForm />
    </div>
  );
}

// app/users/AddUserForm.tsx - Client Component (interactive)
'use client';

function AddUserForm() {
  const [isPending, startTransition] = useTransition();

  async function handleSubmit(formData: FormData) {
    startTransition(async () => {
      await createUser(formData);
    });
  }

  return (
    <form action={handleSubmit}>
      <input name="name" required />
      <button type="submit" disabled={isPending}>Add User</button>
    </form>
  );
}
```

### Data Fetching

- Fetch data in **Server Components** at the route level
- Use `fetch` with Next.js caching options for HTTP-based data
- Deduplicate requests with React cache for non-fetch data sources
- Configure `revalidate` strategies per route or per fetch call

```tsx
// Good: server-side fetch with revalidation
async function getProducts(): Promise<Product[]> {
  const res = await fetch('https://api.example.com/products', {
    next: { revalidate: 3600 }, // revalidate every hour
  });
  if (!res.ok) throw new Error('Failed to fetch products');
  return res.json();
}
```

### Metadata and SEO

- Export `metadata` or `generateMetadata` from page/layout files
- Provide Open Graph and Twitter card metadata for public pages

## 6. Testing Conventions

### Component Testing

- Use **React Testing Library** for component tests
- Test behavior, not implementation details
- Query by role, label, or text; avoid test IDs unless no accessible alternative
- Prefer `userEvent` over `fireEvent` for user interaction simulation

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

test('submits the form with user input', async () => {
  const user = userEvent.setup();
  const onSubmit = vi.fn();
  render(<ContactForm onSubmit={onSubmit} />);

  await user.type(screen.getByLabelText('Name'), 'Alice');
  await user.type(screen.getByLabelText('Email'), 'alice@example.com');
  await user.click(screen.getByRole('button', { name: 'Submit' }));

  expect(onSubmit).toHaveBeenCalledWith({
    name: 'Alice',
    email: 'alice@example.com',
  });
});
```

### Hook Testing

- Use `renderHook` from React Testing Library for custom hooks
- Wrap hooks that require providers with a wrapper option

```tsx
import { renderHook, act } from '@testing-library/react';

test('useCounter increments value', () => {
  const { result } = renderHook(() => useCounter(0));

  act(() => {
    result.current.increment();
  });

  expect(result.current.count).toBe(1);
});
```

## 7. Anti-Patterns

### Component Anti-Patterns

- Do not use `useEffect` to synchronize state that can be derived
- Do not spread all props blindly (`{...props}`) without explicit typing
- Do not mutate state directly; always use setter functions
- Do not put JSX in state; store data and derive JSX during render

### Performance Anti-Patterns

- Do not memoize everything by default; it adds overhead without measurement
- Do not create new functions or objects inside render without reason
- Do not ignore virtualization for lists longer than 100 items
- Do not fetch data in `useEffect` when a server component or data library suffices

### Next.js Anti-Patterns

- Do not add `'use client'` to components that have no interactivity
- Do not use `getServerSideProps` or `getStaticProps` in the App Router
- Do not import server-only code in client components
- Do not bypass the Next.js router for internal navigation

## 8. Related Skills

- `typescript-convention` - TypeScript type system rules used alongside React
- `testing` - General testing patterns and strategies
- `code-quality` - Code readability and maintainability rules
- `api-design` - API design patterns for data fetching layers
