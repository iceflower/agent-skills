# Performance Anti-Patterns by Layer

Detailed performance anti-patterns organized by frontend, backend, and network layers.

## Frontend Anti-Patterns

### Bundle and Loading

| Anti-Pattern | Problem | Fix |
| --- | --- | --- |
| Single large JS bundle | Blocks rendering, slow initial load | Route-based code splitting, dynamic `import()` |
| Unused JS/CSS shipped | Unnecessary download/parse/execute | Tree shaking, PurgeCSS, bundle analysis |
| Barrel files for large libraries | Prevents effective tree shaking | Import directly from module path |
| `document.write()` | Blocks HTML parser, breaks HTTP/2 | Use DOM APIs |
| Sync XHR on main thread | Freezes UI | Use `fetch` or async XHR |
| CSS `@import` chains | Serial request waterfall | Use `<link>` tags or bundler |

### Rendering

| Anti-Pattern | Problem | Fix |
| --- | --- | --- |
| Interleaved DOM reads/writes | Forces synchronous reflow | Batch reads first, then writes |
| Animating layout properties | Reflow on every frame | Use `transform`/`opacity` |
| Excessive DOM size (> 1500 nodes) | Slow DOM operations, memory bloat | Virtualization (windowing) |
| Forced synchronous layout | Reading layout props after write | Avoid `offsetHeight` after DOM mutation |
| `will-change` on everything | Excessive GPU memory | Apply only to animating elements |
| Unoptimized React renders | Wasted CPU, frame drops | `React.memo`, proper state design |

### Images and Media

| Anti-Pattern | Problem | Fix |
| --- | --- | --- |
| Unoptimized images (original size) | Bandwidth waste, slow LCP | Resize, compress, use WebP/AVIF |
| Missing `width`/`height` | Layout shift (CLS) | Always set explicit dimensions |
| All images eager-loaded | Slow initial load | `loading="lazy"` for offscreen images |
| No responsive images | Mobile downloads desktop-size images | `srcset` + `sizes` |
| GIF for animations | Very large file size | Use video (MP4/WebM) or CSS animations |

### Fonts

| Anti-Pattern | Problem | Fix |
| --- | --- | --- |
| Flash of Invisible Text (FOIT) | Text invisible until font loads | `font-display: swap` |
| Too many font variants | Multiple large downloads | Limit to 2-3 weights/styles |
| No font preload | Late font discovery | `<link rel="preload" as="font">` |
| No subset | Full font downloaded for one language | Use `unicode-range` subsetting |

## Backend Anti-Patterns

### Database

| Anti-Pattern | Problem | Fix |
| --- | --- | --- |
| N+1 queries | 1 + N DB round trips | Eager loading, batch queries, DataLoader |
| Missing indexes | Full table scans | `EXPLAIN ANALYZE`, add targeted indexes |
| `SELECT *` | Unnecessary data transfer | Select only needed columns |
| Offset pagination on large tables | Scans all preceding rows | Cursor-based pagination |
| No query parameter binding | No plan caching + SQL injection risk | Prepared statements |
| Unused indexes | Write overhead, storage waste | Audit and remove periodically |
| Over-indexing | Slow writes, storage bloat | Index only queried columns |
| Missing connection pooling | Connection creation overhead | HikariCP, PgBouncer, pg-pool |
| Pool too large | DB connection exhaustion | Size pool based on CPU cores |

### Application

| Anti-Pattern | Problem | Fix |
| --- | --- | --- |
| Synchronous blocking I/O | Thread starvation | Async I/O, reactive patterns |
| Synchronous logging | I/O blocks request thread | Async logging with buffer |
| Unbounded in-memory cache | OOM, GC pressure | TTL + LRU eviction, external cache |
| No caching at all | Repeated identical computation | Redis/Memcached for hot data |
| Serializing entire object graph | CPU + bandwidth waste | DTOs, projection queries |
| Missing pagination | Memory explosion on large datasets | Always paginate |
| No circuit breaker for external calls | Cascading failures | Circuit breaker pattern |
| Missing timeouts | Thread/connection leak | Set connect + read timeouts |

## Network Anti-Patterns

| Anti-Pattern | Problem | Fix |
| --- | --- | --- |
| No Cache-Control headers | Every visit hits origin | Set appropriate caching headers |
| `no-store` on cacheable static assets | No browser/CDN caching | `max-age=31536000, immutable` for hashed files |
| Domain sharding on HTTP/2 | Breaks multiplexing | Single domain |
| Redirect chains | Extra round trips | Direct URLs |
| No compression | 3-5x larger responses | gzip/Brotli for text resources |
| Missing `Vary: Accept-Encoding` | CDN serves wrong encoding | Always set with compression |
| Excessive preload hints | Priority contention | Preload only critical resources |
| Too many DNS lookups | Connection latency | Limit third-party domains, `dns-prefetch` |
| No CDN for static assets | High latency for distant users | CDN with edge caching |
| Missing HTTP/2 | No multiplexing, header overhead | Enable HTTP/2 (virtually all servers support it) |

## Resources

- [web.dev Performance Learning Path](https://web.dev/learn/performance)
- [Chrome DevTools Performance](https://developer.chrome.com/docs/devtools/performance)
- [PostgreSQL Performance Tips](https://www.postgresql.org/docs/current/performance-tips.html)
