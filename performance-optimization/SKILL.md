---
name: performance-optimization
description: >-
  Performance optimization patterns for frontend and backend applications.
  Covers Core Web Vitals (LCP, INP, CLS), bundle optimization, image optimization,
  rendering performance, DB query tuning, connection pooling, HTTP caching,
  CDN strategies, compression, performance budgets, and CI integration.
  Use when optimizing application performance, diagnosing slow pages or APIs,
  or setting up performance monitoring and budgets.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# Performance Optimization Rules

## 1. Core Web Vitals

The three metrics Google uses for page experience ranking.

| Metric | Good | Needs Improvement | Poor |
| --- | --- | --- | --- |
| **LCP** (Largest Contentful Paint) | ≤ 2.5s | 2.5s – 4.0s | > 4.0s |
| **INP** (Interaction to Next Paint) | ≤ 200ms | 200ms – 500ms | > 500ms |
| **CLS** (Cumulative Layout Shift) | ≤ 0.1 | 0.1 – 0.25 | > 0.25 |

- INP replaced FID as a Core Web Vital in March 2024
- INP measures total interaction latency (input delay + processing + presentation)
- Measure with field data (CrUX, `web-vitals` library) and lab data (Lighthouse)

## 2. Frontend — Bundle Optimization

### Code Splitting

- Split by route (most effective for initial load)
- Use dynamic `import()` for non-critical modules
- Separate vendor chunks from application code

```jsx
// React route-based splitting
const Dashboard = React.lazy(() => import("./Dashboard"));

<Suspense fallback={<Loading />}>
  <Dashboard />
</Suspense>
```

### Tree Shaking

- Use ES modules (`import`/`export`) — CommonJS is not tree-shakeable
- Set `"sideEffects": false` in `package.json`
- Avoid barrel files (`index.ts` re-exports) for large libraries

### Bundle Analysis

- Use `webpack-bundle-analyzer`, `source-map-explorer`, or `vite-bundle-visualizer`
- Identify and eliminate duplicate dependencies
- Set performance budgets (see Section 8)

## 3. Frontend — Image Optimization

| Technique | Impact |
| --- | --- |
| Modern formats (WebP, AVIF) | 25-50% smaller than JPEG/PNG |
| Responsive images (`srcset` + `sizes`) | Serve viewport-appropriate size |
| Lazy loading (`loading="lazy"`) | Defer offscreen images |
| Explicit dimensions (`width`/`height`) | Prevent CLS |
| `fetchpriority="high"` on LCP image | Prioritize critical image (limit to 1-2 images to avoid priority contention) |
| CDN image transformation | On-demand resize and format conversion |

```html
<img
  src="hero.webp"
  srcset="hero-480.webp 480w, hero-800.webp 800w, hero-1200.webp 1200w"
  sizes="(max-width: 600px) 480px, (max-width: 1000px) 800px, 1200px"
  width="1200" height="630"
  loading="lazy"
  alt="Hero image"
/>
```

## 4. Frontend — Rendering Performance

### Minimize Reflow/Repaint

- Batch DOM reads before writes (avoid interleaving)
- Use `transform` and `opacity` for animations (GPU-composited, no reflow)
- Use `requestAnimationFrame` for DOM mutations
- Use `content-visibility: auto` for offscreen content

### List Virtualization

Render only visible items for large lists (1000+ items).

- React: `@tanstack/react-virtual`, `react-window`
- Vue: `vue-virtual-scroller`

### Avoid Main Thread Blocking

- Break long tasks (> 50ms) with `scheduler.yield()` or `setTimeout`
- Offload heavy computation to Web Workers
- Use `requestIdleCallback` for non-urgent work

### React-Specific

- Use `React.memo` for expensive components
- Use `useMemo`/`useCallback` for referential stability (not premature optimization)
- Avoid creating objects/arrays in render

## 5. Backend — Database Query Tuning

### Index Strategy

| Type | Use Case |
| --- | --- |
| B-Tree (default) | Range queries, sorting, equality |
| Composite index | Multi-column WHERE, column order matters |
| Covering index | Query answered from index only |
| Partial index | Index subset of rows (PostgreSQL) |

- Always use `EXPLAIN ANALYZE` to verify query plans
- Remove unused indexes (they slow down writes)

### N+1 Problem

```python
# BAD: N+1 queries
users = User.query.all()          # 1 query
for user in users:
    print(user.orders)            # N queries

# GOOD: Eager loading
users = User.query.options(joinedload(User.orders)).all()  # 1 query
```

### General Rules

- Select only needed columns (avoid `SELECT *`)
- Use cursor-based pagination over offset-based for large datasets
- Use prepared statements (security + plan caching)
- Monitor slow query logs

## 6. Backend — Connection and Response

### Connection Pooling

- Reuse database connections instead of creating per request
- Pool size guideline (HikariCP/PostgreSQL): `connections = (CPU cores × 2) + effective_spindle_count` — adjust for other databases
- Set idle timeout and max lifetime
- Tools: HikariCP (Java), `pg-pool` (Node.js), PgBouncer (PostgreSQL)

### Response Compression

| Algorithm | Compression | Speed | Support |
| --- | --- | --- | --- |
| gzip | Good | Medium | Universal |
| Brotli (br) | Better (15-25% over gzip) | Slow compress, fast decompress | Modern browsers (HTTPS) |
| zstd | Better | Fast | Chrome 123+ |

- Apply to text resources (HTML, CSS, JS, JSON, SVG)
- Skip already-compressed formats (JPEG, PNG, WOFF2)
- Pre-compress static assets at build time
- Set `Vary: Accept-Encoding` header

## 7. Network — Caching Strategy

### Cache-Control Patterns

| Resource Type | Recommended Header |
| --- | --- |
| Hashed static assets (JS, CSS) | `Cache-Control: public, max-age=31536000, immutable` |
| HTML documents | `Cache-Control: no-cache` |
| API responses (cacheable) | `Cache-Control: public, max-age=60, stale-while-revalidate=300` |
| Sensitive data | `Cache-Control: private, no-store` |

### ETag / Conditional Requests

- Server sends `ETag` (content hash) with response
- Client sends `If-None-Match` on subsequent requests
- Server returns `304 Not Modified` if unchanged (saves bandwidth)

### CDN

- Serve static assets from edge servers
- Use content-hash filenames for cache busting (`app.a1b2c3.js`)
- Set long `max-age` + `immutable` for hashed assets
- Use `s-maxage` for CDN-specific TTL

### Service Worker Caching

| Strategy | Use Case |
| --- | --- |
| Cache First | Static assets, fonts |
| Network First | API responses, dynamic content |
| Stale While Revalidate | Frequently updated but stale-tolerant data |

For detailed caching patterns, see the [caching skill](../caching/SKILL.md).

## 8. Performance Budget and CI

### Define Budgets

| Metric | Budget Example |
| --- | --- |
| JS bundle (compressed) | ≤ 200 KB |
| Total page weight | ≤ 500 KB |
| LCP | ≤ 2.5s |
| INP | ≤ 200ms |
| CLS | ≤ 0.1 |

### CI Integration

```javascript
// .lighthouserc.js
module.exports = {
  ci: {
    assert: {
      assertions: {
        "largest-contentful-paint": ["error", { maxNumericValue: 2500 }],
        "interactive": ["error", { maxNumericValue: 3800 }],
        "cumulative-layout-shift": ["error", { maxNumericValue: 0.1 }],
      },
    },
  },
};
```

Tools for CI:

- **Lighthouse CI** (`lhci`): Core Web Vitals assertions
- **size-limit**: JS cost budget (size + execution time)
- **bundlesize**: Per-file size limits
- **Webpack `performance`**: Asset and entrypoint size hints

## 9. Measurement Tools

| Tool | Type | Best For |
| --- | --- | --- |
| `web-vitals` library | Field (RUM) | Real user Core Web Vitals |
| CrUX (Chrome UX Report) | Field | Population-level metrics |
| Lighthouse | Lab | Comprehensive audit |
| Chrome DevTools Performance | Lab | Detailed profiling |
| WebPageTest | Lab | Multi-location, filmstrip |
| Server-Timing header | Server | Backend timing breakdown |

### Server-Timing

```http
Server-Timing: db;dur=53, app;dur=47.2, cache;desc="Cache Read";dur=23.2
```

Exposes server-side metrics in DevTools Network tab. Avoid exposing
sensitive internals in production.

## 10. Common Anti-Patterns

For detailed anti-patterns organized by layer, see
[references/anti-patterns.md](references/anti-patterns.md).

| Anti-Pattern | Impact | Fix |
| --- | --- | --- |
| Single large bundle | Slow initial load | Code splitting + lazy loading |
| No image optimization | Bandwidth waste, slow LCP | WebP/AVIF, srcset, lazy loading |
| Missing cache headers | Unnecessary server requests | Proper Cache-Control |
| N+1 queries | DB overload | Eager loading, batch queries |
| No connection pooling | Connection exhaustion | Pool with proper sizing |
| No compression | Bandwidth waste | gzip/Brotli |
| Layout shifts | Poor CLS | Explicit dimensions, font-display |
| Render-blocking resources | Slow FCP/LCP | defer/async, critical CSS |
| Unbounded in-memory cache | OOM risk | TTL, LRU eviction, external cache |
| No performance budget | Gradual regression | CI enforcement |
