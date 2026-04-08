# E2E Testing

## 1. E2E Testing Overview

### When to Write E2E Tests

| Situation | Recommended Test Type |
| --- | --- |
| Single function logic | Unit test |
| Component interaction (DB, API) | Integration test |
| Full user journey across pages/services | E2E test |
| Visual appearance and layout | Visual regression test |
| Cross-browser compatibility | E2E test |

### E2E Test Placement

- Place E2E tests in a separate directory from unit and integration tests
- Recommended: `e2e/` at project root, or `src/e2e/` for monorepos
- Use dedicated configuration (base URL, timeouts, retries) per environment

### E2E Test Principles

- **Test user workflows, not implementation**: E2E tests verify what users experience, not how code is structured
- **Minimize E2E test count**: E2E tests are expensive — cover critical paths only, rely on unit/integration tests for edge cases
- **Independent and idempotent**: Each test must set up and tear down its own state
- **Deterministic**: Avoid time-dependent assertions, random data, or external service dependencies without stubs

---

## 2. Tool Selection

| Tool | Language | Browser Engine | Strengths | Weaknesses |
| --- | --- | --- | --- | --- |
| Playwright | TypeScript/Python/Java/.NET | Chromium, Firefox, WebKit | Multi-browser, auto-wait, trace viewer, parallel by default | No native Chrome extension testing |
| Cypress | JavaScript/TypeScript | Chromium (experimental Firefox/WebKit) | Developer experience, time-travel debug, auto-reload | Single browser primarily, no native multi-tab |
| WebdriverIO | JavaScript/TypeScript | All (via WebDriver) | W3C standard, mobile support | Slower, more complex setup |
| Puppeteer | JavaScript/TypeScript | Chromium only | Low-level control, headless PDF/screenshot | No built-in test runner, Chromium only |
| Selenium | Multiple | All (via WebDriver) | Language support, enterprise adoption | Flaky, slow, verbose API |

### Recommendation

- **New projects, multi-browser**: Playwright
- **Developer experience, single-browser**: Cypress
- **Enterprise, legacy systems**: Selenium or WebdriverIO
- **Scraping/automation (not testing)**: Puppeteer

---

## 3. Playwright Patterns

### Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('User Login', () => {
  test('should log in with valid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.fill('[data-testid="email"]', 'user@example.com');
    await page.fill('[data-testid="password"]', 'securePassword123');
    await page.click('[data-testid="login-button"]');

    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('[data-testid="welcome-message"]')).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.fill('[data-testid="email"]', 'user@example.com');
    await page.fill('[data-testid="password"]', 'wrongPassword');
    await page.click('[data-testid="login-button"]');

    await expect(page.locator('[data-testid="error-message"]')).toHaveText('Invalid credentials');
  });
});
```

### Page Object Model

```typescript
// pages/login.page.ts
export class LoginPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.page.fill('[data-testid="email"]', email);
    await this.page.fill('[data-testid="password"]', password);
    await this.page.click('[data-testid="login-button"]');
  }

  async getErrorMessage(): Promise<string | null> {
    return this.page.locator('[data-testid="error-message"]').textContent();
  }

  async isLoggedIn(): Promise<boolean> {
    return this.page.url().includes('/dashboard');
  }
}

// tests/login.spec.ts
test('should log in successfully', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login('user@example.com', 'securePassword123');
  expect(await loginPage.isLoggedIn()).toBeTruthy();
});
```

### Fixtures for Reusable State

```typescript
// fixtures/auth.fixture.ts
import { test as base, Page } from '@playwright/test';

type AuthFixture = {
  authenticatedPage: Page;
};

export const test = base.extend<AuthFixture>({
  authenticatedPage: async ({ page }, use) => {
    // Set up authenticated state via API
    const response = await page.request.post('/api/auth/login', {
      data: { email: 'user@example.com', password: 'securePassword123' },
    });
    const { token } = await response.json();

    // Inject auth state
    await page.goto('/');
    await page.evaluate((tkn) => {
      localStorage.setItem('authToken', tkn);
    }, token);
    await page.reload();

    await use(page);
  },
});

export { expect } from '@playwright/test';
```

### API-Based Test Setup

```typescript
test('should display order details', async ({ page, request }) => {
  // Create test data via API (faster than UI)
  const orderResponse = await request.post('/api/orders', {
    data: {
      productId: 'prod-123',
      quantity: 2,
      shippingAddress: '123 Test St',
    },
  });
  const { id: orderId } = await orderResponse.json();

  // Navigate to order page and verify
  await page.goto(`/orders/${orderId}`);
  await expect(page.locator('[data-testid="order-id"]')).toHaveText(orderId);
  await expect(page.locator('[data-testid="order-status"]')).toHaveText('Processing');
});
```

### Parallel Execution and Sharding

```bash
# Run tests in parallel (default in Playwright)
npx playwright test --workers=4

# Shard across multiple CI machines
npx playwright test --shard=1/3  # Machine 1
npx playwright test --shard=2/3  # Machine 2
npx playwright test --shard=3/3  # Machine 3

# Merge reports after sharded run
npx playwright merge-reports --reporter=html ./all-blob-reports
```

### Trace Viewer for Debugging

```bash
# Record trace on failure
npx playwright test --trace on-first-retry

# View trace
npx playwright show-trace trace.zip
```

### Configuration

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? 'github' : 'html',
  timeout: 30000,
  expect: { timeout: 5000 },
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'mobile', use: { ...devices['iPhone 14'] } },
  ],
  webServer: {
    command: 'npm run start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
```

---

## 4. Cypress Patterns

### Test Structure

```typescript
describe('User Login', () => {
  beforeEach(() => {
    cy.visit('/login');
  });

  it('should log in with valid credentials', () => {
    cy.get('[data-testid="email"]').type('user@example.com');
    cy.get('[data-testid="password"]').type('securePassword123');
    cy.get('[data-testid="login-button"]').click();

    cy.url().should('include', '/dashboard');
    cy.get('[data-testid="welcome-message"]').should('be.visible');
  });

  it('should show error for invalid credentials', () => {
    cy.get('[data-testid="email"]').type('user@example.com');
    cy.get('[data-testid="password"]').type('wrongPassword');
    cy.get('[data-testid="login-button"]').click();

    cy.get('[data-testid="error-message"]').should('have.text', 'Invalid credentials');
  });
});
```

### Custom Commands

```typescript
// cypress/support/commands.ts
Cypress.Commands.add('login', (email: string, password: string) => {
  cy.request('POST', '/api/auth/login', { email, password }).then((response) => {
    window.localStorage.setItem('authToken', response.body.token);
    cy.visit('/dashboard');
  });
});

Cypress.Commands.add('findByTestId', (testId: string) => {
  return cy.get(`[data-testid="${testId}"]`);
});

// Type definitions
declare global {
  namespace Cypress {
    interface Chainable {
      login(email: string, password: string): Chainable<void>;
      findByTestId(testId: string): Chainable<JQuery<HTMLElement>>;
    }
  }
}
```

### Session Management

```typescript
// Cache authentication across tests
Cypress.Commands.add('loginWithSession', (email: string, password: string) => {
  cy.session([email, password], () => {
    cy.request('POST', '/api/auth/login', { email, password }).then((response) => {
      window.localStorage.setItem('authToken', response.body.token);
    });
  });
});

// Usage
beforeEach(() => {
  cy.loginWithSession('user@example.com', 'securePassword123');
});

it('should view profile', () => {
  cy.visit('/profile');
  cy.get('[data-testid="user-email"]').should('contain', 'user@example.com');
});
```

### Component Testing

```typescript
// Button.cy.tsx
import { mount } from 'cypress/react18';
import { Button } from './Button';

describe('Button Component', () => {
  it('renders with text', () => {
    mount(<Button>Click me</Button>);
    cy.get('button').should('contain', 'Click me');
  });

  it('calls onClick when clicked', () => {
    const onClick = cy.stub();
    mount(<Button onClick={onClick}>Click me</Button>);
    cy.get('button').click();
    expect(onClick).to.have.been.calledOnce;
  });
});
```

### Configuration

```typescript
// cypress.config.ts
import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:3000',
    viewportWidth: 1280,
    viewportHeight: 720,
    defaultCommandTimeout: 10000,
    requestTimeout: 10000,
    retries: {
      runMode: 2,
      openMode: 0,
    },
    video: true,
    screenshotOnRunFailure: true,
    experimentalSessionAndOrigin: true,
  },
  component: {
    devServer: {
      framework: 'react',
      bundler: 'vite',
    },
  },
});
```

---

## 5. Visual Regression Testing

### Playwright Screenshot Comparison

```typescript
test('should match visual snapshot', async ({ page }) => {
  await page.goto('/dashboard');

  // Full page screenshot comparison
  await expect(page).toHaveScreenshot('dashboard.png', {
    maxDiffPixelRatio: 0.01,
    animations: 'disabled',
  });

  // Component-level screenshot
  const chart = page.locator('[data-testid="sales-chart"]');
  await expect(chart).toHaveScreenshot('sales-chart.png');
});

// Per-project threshold
test('responsive layout mobile', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('/');
  await expect(page).toHaveScreenshot('mobile-home.png', {
    maxDiffPixelRatio: 0.02,
  });
});
```

### Percy Integration

```typescript
// With Playwright
import { test } from '@playwright/test';
import PercyClient from '@percy/cli';

test('should capture visual snapshots', async ({ page }) => {
  await page.goto('/products');

  // Snapshot with Percy
  await page.evaluate(() => {
    // @ts-expect-error Percy injected by CI
    window.PercySnapshot('Products Page');
  });
});
```

### Chromatic Integration

```bash
# Run Chromatic after Playwright or Storybook
npx chromatic --project-token=<project-token> --build-script-name=storybook

# With Playwright snapshots
npx chromatic --playwright --project-token=<project-token>
```

### Visual Regression Rules

- **Set `animations: 'disabled'`**: Animations cause non-deterministic screenshots
- **Use consistent viewport sizes**: Define standard breakpoints in config
- **Mask dynamic content**: Dates, ads, and user-specific content should be masked or excluded
- **Adjust `maxDiffPixelRatio`** per component: Strict (0.001) for logos, lenient (0.02) for data-heavy pages
- **Review failures manually**: Automated diff detection finds changes, humans determine intent
- **Commit baseline screenshots**: Store approved baselines in version control

---

## 6. Test Data Management

### API-Based Setup (Recommended)

```typescript
// Most E2E tests should create data via API, not through the UI
test.beforeEach(async ({ request }) => {
  await request.post('/api/test/seed', {
    data: {
      users: [{ email: 'user@example.com', role: 'admin' }],
      products: [{ name: 'Test Product', price: 29.99 }],
    },
  });
});

test.afterEach(async ({ request }) => {
  await request.post('/api/test/cleanup');
});
```

### Database Snapshots

```typescript
// For tests requiring complex data relationships
// Use database snapshots for fast setup
test('should process complex order', async ({ page, request }) => {
  // Restore pre-built database snapshot
  await request.post('/api/test/restore-snapshot', {
    data: { snapshot: 'e2e-orders-with-items' },
  });

  await page.goto('/orders');
  // ... test logic
});
```

### Data Factory Pattern

```typescript
// factories/user.factory.ts
export function createUser(overrides: Partial<User> = {}): User {
  return {
    email: `test-${Date.now()}@example.com`,
    name: 'Test User',
    role: 'user',
    ...overrides,
  };
}

// Usage in test
const admin = createUser({ role: 'admin' });
await request.post('/api/users', { data: admin });
```

### Test Data Rules

- **Never share test data between tests**: Each test creates and cleans up its own data
- **Use API for data setup, UI for verification**: Creating data through the UI is slow and fragile
- **Generate unique identifiers**: Use timestamps or UUIDs to avoid collisions in parallel runs
- **Clean up after tests**: Remove created data to prevent test pollution
- **Do not depend on seeded data for critical tests**: Seeded data may be modified by other tests

---

## 7. CI/CD Integration

### GitHub Actions (Playwright)

```yaml
name: E2E Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  e2e:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard: [1, 2, 3]
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium

      - name: Run E2E tests
        run: npx playwright test --shard=${{ matrix.shard }}/3
        env:
          E2E_BASE_URL: http://localhost:3000

      - name: Upload blob report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: blob-report-${{ matrix.shard }}
          path: blob-report/
          retention-days: 1

  merge-reports:
    if: always()
    needs: [e2e]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Download blob reports
        uses: actions/download-artifact@v4
        with:
          path: all-blob-reports
          pattern: blob-report-*

      - name: Merge into HTML report
        run: npx playwright merge-reports --reporter=html ./all-blob-reports

      - name: Upload HTML report
        uses: actions/upload-artifact@v4
        with:
          name: html-report
          path: playwright-report/
          retention-days: 14
```

### Retry Strategy

| Scenario | Playwright | Cypress |
| --- | --- | --- |
| CI flaky test | `retries: 2` | `retries: { runMode: 2 }` |
| Local development | `retries: 0` | `retries: { openMode: 0 }` |
| Critical smoke test | `retries: 3` | `retries: { runMode: 3 }` |

### Artifact Collection

| Artifact | Purpose | Retention |
| --- | --- | --- |
| Screenshots (on failure) | Visual debugging | 14-30 days |
| Videos (on failure) | Step-by-step replay | 14-30 days |
| Trace files | DOM, network, console snapshot | 7-14 days |
| HTML report | Combined test results | 14-30 days |

---

## 8. Anti-Patterns

- **Testing every path with E2E**: E2E tests are slow and expensive — test critical user journeys only, use unit/integration tests for edge cases
- **Using UI to set up test data**: Creating a user via the login/signup UI before each test is fragile and slow — use API calls or database seeding
- **Shared mutable state between tests**: Tests that depend on data created by previous tests break when run in isolation — each test must be independent
- **Overusing `waitForTimeout`**: Fixed waits are unreliable — use auto-wait assertions (Playwright `expect().toBeVisible()`, Cypress `should()`)
- **Testing third-party integrations with E2E**: Use contract tests or mock servers for external services — real third-party calls make tests flaky
- **Running all E2E tests on every PR**: Full E2E suites are expensive — run smoke tests on PRs, full suites on merge to main
- **Ignoring flaky tests**: Flaky E2E tests erode trust — quarantine and fix immediately, or remove them
- **Hardcoding URLs and credentials**: Use environment variables and config files — `baseURL` in config, secrets in CI environment
- **No visual regression testing**: Visual bugs are invisible to functional E2E tests — add screenshot comparison for critical pages
- **Excessive page objects**: Over-engineering page objects for simple pages adds maintenance cost — use them when multiple tests interact with the same page
