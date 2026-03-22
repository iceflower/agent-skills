# OpenFeature Standard Reference

## Overview

OpenFeature is a CNCF (Cloud Native Computing Foundation) open standard that provides a vendor-agnostic API for feature flag evaluation. It decouples application code from specific feature flag providers.

## Core Concepts

### Evaluation API

The Evaluation API is the primary interface for feature flag evaluation.

```typescript
import { OpenFeature } from '@openfeature/server-sdk';

// Initialize provider
OpenFeature.setProvider(new MyProvider());

// Get a client (optionally scoped to a domain)
const client = OpenFeature.getClient('my-service');

// Basic evaluation methods
const boolValue = await client.getBooleanValue('flag-key', false);
const stringValue = await client.getStringValue('flag-key', 'default');
const numberValue = await client.getNumberValue('flag-key', 0);
const objectValue = await client.getObjectValue('flag-key', {});
```

### Evaluation Context

The evaluation context carries information about the current user, environment, and request for targeting decisions.

```typescript
// Global context (applies to all evaluations)
OpenFeature.setContext({
  environment: 'production',
  region: 'us-east-1',
});

// Per-request context
const context: EvaluationContext = {
  targetingKey: 'user-123',           // Required: unique identifier
  email: 'user@example.com',
  country: 'US',
  plan: 'enterprise',
  custom: {
    betaTester: true,
    accountAge: 365,
  },
};

const result = await client.getBooleanValue('feature-key', false, context);
```

### Evaluation Details

For more information than just the value, use the detail methods.

```typescript
const details = await client.getBooleanDetails('flag-key', false, context);

// details object:
// {
//   flagKey: 'flag-key',
//   value: true,
//   variant: 'on',
//   reason: 'TARGETING_MATCH',     // Why this value was returned
//   flagMetadata: { ... },
//   errorCode: undefined,
//   errorMessage: undefined,
// }
```

#### Evaluation Reasons

| Reason | Description |
| --- | --- |
| `STATIC` | Flag has a fixed value (no rules) |
| `DEFAULT` | Default value was returned (error or no match) |
| `TARGETING_MATCH` | A targeting rule matched |
| `SPLIT` | Percentage rollout determined the value |
| `DISABLED` | Flag is disabled |
| `CACHED` | Value returned from cache |
| `ERROR` | An error occurred during evaluation |

---

## Provider Implementation

A provider connects the OpenFeature SDK to a specific feature flag backend.

### Provider Interface

```typescript
import {
  Provider,
  ResolutionDetails,
  EvaluationContext,
  JsonValue,
} from '@openfeature/server-sdk';

class CustomProvider implements Provider {
  metadata = { name: 'custom-provider' };

  async resolveBooleanEvaluation(
    flagKey: string,
    defaultValue: boolean,
    context: EvaluationContext
  ): Promise<ResolutionDetails<boolean>> {
    // Fetch flag value from your backend
    const flag = await this.fetchFlag(flagKey);

    if (!flag) {
      return { value: defaultValue, reason: 'DEFAULT' };
    }

    const value = this.evaluate(flag, context);
    return {
      value,
      variant: value ? 'on' : 'off',
      reason: 'TARGETING_MATCH',
    };
  }

  async resolveStringEvaluation(
    flagKey: string,
    defaultValue: string,
    context: EvaluationContext
  ): Promise<ResolutionDetails<string>> {
    // Similar implementation for string flags
  }

  async resolveNumberEvaluation(
    flagKey: string,
    defaultValue: number,
    context: EvaluationContext
  ): Promise<ResolutionDetails<number>> {
    // Similar implementation for number flags
  }

  async resolveObjectEvaluation(
    flagKey: string,
    defaultValue: JsonValue,
    context: EvaluationContext
  ): Promise<ResolutionDetails<JsonValue>> {
    // Similar implementation for object flags
  }
}
```

### Provider Lifecycle

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    NOT      │───▶│   READY     │───▶│   STALE     │───▶│   ERROR     │
│  READY      │    │             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
   initialize()      Connection OK      Connection lost    Unrecoverable
                      Flags synced       Cache serving      error
```

### Provider Registration

```typescript
// Register a named provider for a specific domain
OpenFeature.setProvider('payments-service', new PaymentsProvider());
OpenFeature.setProvider('auth-service', new AuthProvider());

// Get domain-scoped client
const paymentsClient = OpenFeature.getClient('payments-service');
const authClient = OpenFeature.getClient('auth-service');
```

---

## Hooks

Hooks allow cross-cutting concerns (logging, metrics, validation) to be applied at evaluation time.

### Hook Stages

```text
┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐
│   before    │───▶│   after    │───▶│  finally   │    │   error    │
│             │    │            │    │            │    │            │
│ Modify ctx  │    │ Read result│    │ Cleanup    │    │ Handle err │
│ Validate    │    │ Record     │    │ Always runs│    │ Fallback   │
└────────────┘    └────────────┘    └────────────┘    └────────────┘
                                                           ▲
                                               Called on error only
```

### Hook Implementation

```typescript
import { Hook, HookContext, EvaluationDetails } from '@openfeature/server-sdk';

// Logging hook
const loggingHook: Hook = {
  before(hookContext: HookContext) {
    console.log(`Evaluating flag: ${hookContext.flagKey}`);
    return hookContext.context; // Return (optionally modified) context
  },

  after(hookContext: HookContext, details: EvaluationDetails<any>) {
    console.log(
      `Flag ${hookContext.flagKey} = ${details.value} (${details.reason})`
    );
  },

  error(hookContext: HookContext, error: Error) {
    console.error(`Flag evaluation error: ${hookContext.flagKey}`, error);
  },

  finally(hookContext: HookContext) {
    // Cleanup, always runs
  },
};

// Metrics hook
const metricsHook: Hook = {
  after(hookContext: HookContext, details: EvaluationDetails<any>) {
    metrics.increment('feature_flag.evaluation', {
      flag: hookContext.flagKey,
      value: String(details.value),
      reason: details.reason,
    });
  },

  error(hookContext: HookContext, error: Error) {
    metrics.increment('feature_flag.error', {
      flag: hookContext.flagKey,
      error: error.message,
    });
  },
};
```

### Hook Registration

```typescript
// Global hooks (apply to all evaluations)
OpenFeature.addHooks(loggingHook, metricsHook);

// Client-level hooks
const client = OpenFeature.getClient();
client.addHooks(customValidationHook);

// Per-evaluation hooks
const value = await client.getBooleanValue(
  'flag-key',
  false,
  context,
  { hooks: [specialHook] }
);
```

### Hook Execution Order

```text
Global hooks → Client hooks → Per-evaluation hooks → Provider hooks
  (before)        (before)         (before)             (before)
                                                      [evaluation]
Provider hooks → Per-evaluation hooks → Client hooks → Global hooks
  (after)          (after)                (after)        (after)
```

---

## SDK Configuration Patterns

### Caching and Performance

```typescript
// Configure provider with caching
const provider = new MyProvider({
  cache: {
    enabled: true,
    ttl: 60_000,          // Cache TTL in ms
    maxItems: 1000,       // Max cached flags
  },
  connection: {
    timeout: 5_000,       // Connection timeout
    retryAttempts: 3,     // Retry on failure
    retryDelay: 1_000,    // Delay between retries
  },
});
```

### Event Handling

```typescript
// Listen for provider state changes
OpenFeature.addHandler(ProviderEvents.Ready, (details) => {
  console.log('Provider is ready:', details);
});

OpenFeature.addHandler(ProviderEvents.Error, (details) => {
  console.error('Provider error:', details);
  // Fall back to defaults or cached values
});

OpenFeature.addHandler(ProviderEvents.ConfigurationChanged, (details) => {
  console.log('Flags updated:', details.flagsChanged);
  // Re-evaluate flags if needed
});

OpenFeature.addHandler(ProviderEvents.Stale, (details) => {
  console.warn('Provider data is stale, using cached values');
});
```

### Graceful Shutdown

```typescript
// Clean up on application shutdown
process.on('SIGTERM', async () => {
  await OpenFeature.close(); // Closes all providers
});
```

---

## Provider-Specific Setup

### LaunchDarkly Provider

```typescript
import { init } from '@launchdarkly/node-server-sdk';
import { LaunchDarklyProvider } from '@openfeature/launchdarkly-provider';

const ldClient = init('sdk-key');
await ldClient.waitForInitialization();

OpenFeature.setProvider(new LaunchDarklyProvider(ldClient));
```

### Unleash Provider

```typescript
import { UnleashClient } from 'unleash-client';
import { UnleashProvider } from '@openfeature/unleash-provider';

const unleash = new UnleashClient({
  url: 'https://unleash.example.com/api',
  appName: 'my-app',
  customHeaders: { Authorization: process.env.UNLEASH_API_TOKEN },
});

OpenFeature.setProvider(new UnleashProvider(unleash));
```

### Flipt Provider

```typescript
import { FliptProvider } from '@openfeature/flipt-provider';

OpenFeature.setProvider(
  new FliptProvider({
    host: 'http://flipt.example.com',
    namespace: 'production',
  })
);
```

### Flagsmith Provider

```typescript
import Flagsmith from 'flagsmith-nodejs';
import { FlagsmithProvider } from '@openfeature/flagsmith-provider';

const flagsmith = new Flagsmith({
  environmentKey: process.env.FLAGSMITH_ENV_KEY,
});

OpenFeature.setProvider(new FlagsmithProvider(flagsmith));
```

---

## Best Practices

### Do

- Use the OpenFeature SDK as the only interface for flag evaluation in application code
- Register providers at application startup, before any flag evaluations
- Always provide sensible default values that represent the safe/current behavior
- Use evaluation context consistently across all evaluations
- Implement hooks for observability rather than adding logging at each evaluation site
- Handle provider errors gracefully — the SDK returns defaults on error

### Do Not

- Do not call provider APIs directly — always go through OpenFeature SDK
- Do not create multiple clients for the same domain — reuse clients
- Do not block application startup on flag service availability — use cached/default values
- Do not store sensitive data in evaluation context — it may be logged or transmitted
- Do not use flag evaluation in tight loops without caching — check provider caching options
