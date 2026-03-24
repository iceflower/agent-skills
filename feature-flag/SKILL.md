---
name: feature-flag
description: >-
  Feature flag and progressive delivery patterns including toggle classification
  (release, experiment, ops, permission), flag lifecycle management, targeting
  rules, percentage rollouts, A/B testing integration, trunk-based development
  with feature flags, and progressive delivery strategies (canary, blue-green).
  Covers OpenFeature standard, LaunchDarkly, Unleash, Flipt, and Flagsmith.
  Use when implementing feature flags, designing toggle strategies, planning
  progressive delivery, or integrating feature management with CI/CD pipelines
  and trunk-based development workflows.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# Feature Flag and Progressive Delivery Rules

## 1. Toggle Classification

Based on Martin Fowler's Feature Toggles taxonomy, classify every flag before creation.

| Category | Lifetime | Dynamism | Decision Owner | Example |
| --- | --- | --- | --- | --- |
| Release Toggle | Short (days–weeks) | Per-deployment | Engineering | Hide incomplete payment flow |
| Experiment Toggle | Medium (weeks–months) | Per-request | Product/Data | A/B test checkout button color |
| Ops Toggle | Long-lived | Per-request | Operations/SRE | Circuit breaker for external API |
| Permission Toggle | Long-lived | Per-request | Product/Sales | Premium feature gating |

### Classification Rules

- Every flag MUST have a category assigned at creation time
- Release toggles MUST have a planned removal date (default: 30 days after full rollout)
- Experiment toggles MUST define success metrics and evaluation criteria before activation
- Ops toggles MUST document the operational scenario they address
- Permission toggles MUST map to a defined entitlement or role

---

## 2. Flag Naming and Structure

### Naming Convention

```text
<category>.<domain>.<feature-name>
```

| Component | Format | Example |
| --- | --- | --- |
| Category | `release`, `experiment`, `ops`, `permission` | `release` |
| Domain | lowercase, kebab-case | `checkout` |
| Feature name | lowercase, kebab-case | `new-payment-flow` |

Full example: `release.checkout.new-payment-flow`

### Flag Definition Schema

```json
{
  "key": "release.checkout.new-payment-flow",
  "category": "release",
  "description": "Enables the redesigned payment flow with multi-step checkout",
  "owner": "team-payments",
  "created": "2026-03-01",
  "expiry": "2026-04-15",
  "default_value": false,
  "tags": ["checkout", "payments", "q1-release"]
}
```

### Rules

- Flag keys MUST be globally unique
- Descriptions MUST explain what the flag controls, not just name it
- Every flag MUST have an owner (team or individual)
- Release and experiment flags MUST have an expiry date
- Use boolean flags for on/off; use string/JSON variants only when multiple states are needed

---

## 3. Flag Lifecycle Management

### Lifecycle Phases

```text
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Created  │───▶│  Testing  │───▶│ Rollout  │───▶│  Stable  │───▶│ Removed  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     │                                │                              │
     │         Flag off in prod       │    Gradual % increase        │  Code cleanup
     │         On in dev/staging      │    Monitor metrics           │  Remove flag checks
     │                                │    Rollback if needed        │  Delete flag config
```

### Phase Rules

| Phase | Required Actions |
| --- | --- |
| Created | Define flag with metadata, assign owner, set expiry |
| Testing | Enable in dev/staging environments, verify both paths |
| Rollout | Gradual percentage increase with metric monitoring |
| Stable | Flag at 100% for all users, begin cleanup planning |
| Removed | Delete flag checks from code, remove flag configuration |

### Cleanup Enforcement

- Track flag age in CI — warn at 80% of expiry, fail build at 120% of expiry
- Run static analysis to detect stale flag references
- Maintain a flag inventory dashboard showing age, status, and owner
- Include flag cleanup in sprint planning when flags approach expiry

---

## 4. Targeting Rules and Percentage Rollouts

### Targeting Hierarchy

Evaluate targeting rules in this order:

1. **User-level override** — specific user IDs (for testing or VIP access)
2. **Segment match** — user belongs to a defined segment (beta-testers, internal-staff)
3. **Rule-based evaluation** — attribute conditions (country == "US", plan == "enterprise")
4. **Percentage rollout** — consistent hashing of user ID for gradual rollout
5. **Default value** — fallback when no rules match

### Percentage Rollout Rules

```text
Recommended rollout schedule:

Day 1:   1%  — smoke test, verify metrics
Day 2:   5%  — expand, monitor error rates
Day 3:  10%  — check performance impact
Day 5:  25%  — broader exposure
Day 7:  50%  — half of traffic
Day 10: 100% — full rollout, begin cleanup timer
```

- Use consistent hashing (e.g., murmur3 of user ID + flag key) so users get a stable experience
- Never use random assignment for percentage rollouts — it causes flickering
- Define rollback criteria before starting rollout (error rate threshold, latency p99, conversion drop)
- Automate rollback when metrics breach defined thresholds

### Targeting Rule Example

```json
{
  "flag": "experiment.checkout.one-click-buy",
  "rules": [
    {
      "priority": 1,
      "condition": { "user_id": { "in": ["user-123", "user-456"] } },
      "value": true
    },
    {
      "priority": 2,
      "condition": { "segment": "beta-testers" },
      "value": true
    },
    {
      "priority": 3,
      "condition": { "country": "US", "plan": "premium" },
      "value": true,
      "percentage": 50
    }
  ],
  "default": false
}
```

---

## 5. Trunk-Based Development with Feature Flags

### Core Pattern

Feature flags enable trunk-based development by decoupling deployment from release.

```text
┌─────────────────────────────────────────────────────────┐
│                     main branch                         │
│  ──●──●──●──●──●──●──●──●──●──●──●──●──●──●──●──●──▶  │
│    │     │        │           │        │                 │
│   Add   Impl    Impl       Wire     Remove              │
│   flag  behind  more       100%     flag                │
│         flag    logic      rollout  + code              │
└─────────────────────────────────────────────────────────┘
```

### Trunk-Based Development Rules

- Merge to main frequently (at least daily) — feature flags protect incomplete work
- Never use long-lived feature branches when a release flag can achieve the same goal
- Wrap all incomplete or risky code paths behind release flags
- Deploy flag-guarded code to production even if the feature is not ready for users
- Use flag-driven deployment (deploy code) vs flag-driven release (enable feature) as separate steps

### Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
| --- | --- | --- |
| Flag in flag | Nested flag checks create exponential test paths | Refactor to single flag or combine conditions |
| Flag-driven architecture | Business logic depends on flag topology | Keep flag checks at boundaries, not deep in domain |
| Permanent release flag | Release flags that never get removed | Enforce expiry, track in CI |
| Flag-based branching | Using flags instead of proper abstraction | Use strategy pattern or polymorphism |

---

## 6. OpenFeature Standard

OpenFeature is the CNCF open standard for feature flag evaluation.

### Architecture

```text
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Application │────▶│  OpenFeature SDK │────▶│    Provider       │
│   Code      │     │  (Vendor-neutral)│     │ (LaunchDarkly,   │
│             │     │                  │     │  Unleash, Flipt,  │
│             │     │  ┌────────────┐  │     │  Flagsmith, etc.) │
│             │     │  │   Hooks    │  │     └──────────────────┘
│             │     │  └────────────┘  │
└─────────────┘     └──────────────────┘
```

### Key Rules

- Use OpenFeature SDK as the abstraction layer — never call provider APIs directly
- Register a single provider per application instance
- Use evaluation context to pass user attributes for targeting
- Implement hooks for logging, metrics, and validation — not in application code
- For detailed API usage and provider implementation, see `references/openfeature-standard.md`

### Basic Usage Pattern

```typescript
import { OpenFeature } from '@openfeature/server-sdk';

// Set provider once at startup
OpenFeature.setProvider(new YourProvider());

const client = OpenFeature.getClient();

// Evaluate with context
const showFeature = await client.getBooleanValue(
  'release.checkout.new-payment-flow',
  false, // default value
  { targetingKey: userId, country: userCountry }
);
```

---

## 7. Testing Strategy

### Test Both Paths

Every flag evaluation point MUST have tests for both the flag-on and flag-off states.

```text
Test Matrix for a Single Flag:

┌───────────────┬──────────┬──────────┐
│   Scenario    │ Flag ON  │ Flag OFF │
├───────────────┼──────────┼──────────┤
│ Unit test     │    ✓     │    ✓     │
│ Integration   │    ✓     │    ✓     │
│ E2E (staging) │    ✓     │    ✓     │
│ E2E (prod)    │  Canary  │ Default  │
└───────────────┴──────────┴──────────┘
```

### Testing Rules

- Use test-specific providers (in-memory) that let you set flag values per test
- Never depend on external flag service in unit tests
- Integration tests MAY connect to a test-environment flag service
- Test the default/fallback path — assume the flag service will be unavailable
- For experiment flags, test that metrics are emitted correctly in both variants

### Test Helper Pattern

```typescript
// Test helper: override flags for testing
function withFlags(overrides: Record<string, boolean>, fn: () => void) {
  const testProvider = new InMemoryProvider(overrides);
  OpenFeature.setProvider(testProvider);
  try {
    fn();
  } finally {
    OpenFeature.clearProvider();
  }
}

// Usage in test
withFlags({ 'release.checkout.new-payment-flow': true }, () => {
  const result = renderCheckoutPage();
  expect(result).toContain('multi-step');
});
```

---

## 8. Security Considerations

### Server-Side vs Client-Side Evaluation

| Aspect | Server-Side | Client-Side |
| --- | --- | --- |
| Flag data exposure | None — evaluation happens on server | Flag rules may be visible to users |
| Targeting accuracy | Full context available | Limited to client-known attributes |
| Latency | Network round-trip for each eval | Instant after initial load |
| Recommended for | Permission flags, sensitive logic | UI toggles, non-sensitive features |

### Security Rules

- NEVER expose permission flag rules or targeting logic to client-side code
- Use server-side evaluation for any flag that controls access to paid features or sensitive data
- Client-side SDKs should receive only the evaluated result, not the full rule set
- Rotate API keys for flag services on the same schedule as other service credentials
- Audit flag changes — every flag modification must be logged with who, what, when
- Restrict flag modification permissions by environment (dev: team-wide, prod: restricted)

### Audit Requirements

| Event | Required Fields |
| --- | --- |
| Flag created | Key, owner, category, expiry, created_by, timestamp |
| Flag modified | Key, old_value, new_value, modified_by, timestamp, reason |
| Flag evaluated | Key, context_hash, result, provider, timestamp |
| Flag deleted | Key, deleted_by, timestamp, final_state |

---

## 9. Progressive Delivery Integration

Feature flags integrate with progressive delivery to minimize blast radius.

### Strategy Overview

| Strategy | Flag Role | Blast Radius |
| --- | --- | --- |
| Percentage rollout | Flag controls user % | Per-user |
| Canary + flag | Flag targets canary instances | Per-instance then per-user |
| Blue-green + flag | Flag switches traffic between environments | Per-environment |
| Ring-based | Flag targets deployment rings | Per-ring |

### Integration Rules

- Combine infrastructure-level delivery (canary, blue-green) with feature flags for maximum control
- Use feature flags for user-level targeting and infrastructure tools for instance-level routing
- Define automated rollback triggers for both layers
- Monitor both infrastructure metrics (CPU, memory, error rate) and business metrics (conversion, revenue)
- For detailed progressive delivery strategies, see `references/progressive-delivery.md`

---

## 10. Flag Technical Debt Management

### Debt Indicators

| Indicator | Threshold | Action |
| --- | --- | --- |
| Flag count per service | > 20 active flags | Prioritize cleanup sprint |
| Average flag age | > 45 days for release flags | Enforce expiry policy |
| Orphaned flags | Flag in config but not in code | Remove from config |
| Dead code behind flags | Flag always evaluates to same value | Remove flag and dead path |

### Cleanup Process

1. **Identify** — Static analysis scan for flag references in code
2. **Verify** — Confirm flag is at 100% or 0% and stable for > 7 days
3. **Remove code** — Delete flag checks and the unused code path
4. **Remove config** — Delete flag definition from the flag service
5. **Verify deployment** — Deploy cleanup and confirm no regressions

### CI Integration

```yaml
# Example: Flag hygiene check in CI
flag-hygiene:
  script:
    - python scripts/check_flag_expiry.py --warn-days 7 --fail-days -14
    - python scripts/find_orphaned_flags.py --source-dir src/ --flag-config flags.json
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

---

## 11. Platform Comparison

| Feature | LaunchDarkly | Unleash | Flipt | Flagsmith |
| --- | --- | --- | --- | --- |
| Hosting | SaaS / Relay Proxy | Self-hosted / SaaS | Self-hosted | Self-hosted / SaaS |
| OpenFeature support | Yes | Yes | Yes | Yes |
| Targeting | Advanced | Strategy-based | Segment + rule | Segment + rule |
| A/B testing | Built-in | Via integration | Via integration | Built-in |
| Audit log | Yes | Yes (Enterprise) | Yes | Yes |
| Pricing | Per-seat | Open-source core | Open-source (Apache 2.0) | Open-source core |
| Best for | Enterprise, complex targeting | Self-hosted, privacy-first | GitOps-native, lightweight | Full-featured self-hosted |

### Selection Guidance

- **Need SaaS with advanced targeting** → LaunchDarkly
- **Need self-hosted with privacy** → Unleash
- **Need GitOps-native with declarative config** → Flipt
- **Need open-source with A/B testing** → Flagsmith
- **Need vendor-neutral code** → Use OpenFeature SDK regardless of provider choice
