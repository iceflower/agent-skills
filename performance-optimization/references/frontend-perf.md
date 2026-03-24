# Frontend Performance Reference

Detailed frontend performance optimization techniques and patterns.

## Critical Rendering Path

### Render-Blocking Resources

CSS and synchronous JS block rendering. Optimize the critical path:

```html
<!-- Critical CSS inlined -->
<style>/* Above-the-fold styles */</style>

<!-- Non-critical CSS deferred -->
<link rel="preload" href="styles.css" as="style" onload="this.rel='stylesheet'" />

<!-- JS deferred (executes after HTML parsing) -->
<script src="app.js" defer></script>

<!-- JS async (executes as soon as downloaded) -->
<script src="analytics.js" async></script>
```

### Resource Hints

```html
<!-- Preload: critical resources for current page -->
<link rel="preload" href="hero.webp" as="image" />
<link rel="preload" href="font.woff2" as="font" type="font/woff2" crossorigin />

<!-- Prefetch: resources for likely next navigation -->
<link rel="prefetch" href="/dashboard" />

<!-- DNS Prefetch: resolve DNS for third-party domains -->
<link rel="dns-prefetch" href="//api.example.com" />

<!-- Preconnect: establish connection early -->
<link rel="preconnect" href="https://cdn.example.com" crossorigin />
```

**Priority rules:**

- `preload` only resources needed within 3 seconds of page load
- Use `fetchpriority="high"` on LCP image
- Use `fetchpriority="low"` on non-critical above-the-fold images
- Limit preload to 2-3 resources to avoid priority contention

## LCP Optimization Checklist

1. **Identify the LCP element**: Usually the largest image or text block
2. **If image**: Optimize format (WebP/AVIF), preload, `fetchpriority="high"`, responsive sizes
3. **If text**: Ensure fonts load fast (`font-display: swap`, preload font)
4. **Reduce server response time**: TTFB < 800ms
5. **Eliminate render-blocking resources**: Inline critical CSS, defer JS
6. **Avoid client-side rendering for LCP**: Use SSR/SSG for LCP content

## INP Optimization Checklist

1. **Identify slow interactions**: Chrome DevTools → Performance → Interactions track
2. **Reduce input delay**: Minimize main thread work during idle
3. **Reduce processing time**: Break long tasks (> 50ms), use `scheduler.yield()`
4. **Reduce presentation delay**: Minimize DOM size, avoid forced reflow

```js
// Break long tasks with scheduler.yield()
async function processItems(items) {
  for (const item of items) {
    processItem(item);
    // Yield to the browser between items
    if (navigator.scheduling?.isInputPending?.()) {
      await scheduler.yield();
    }
  }
}
```

## CLS Optimization Checklist

1. **Images/video**: Always set `width` and `height` attributes
2. **Ads/embeds**: Reserve space with CSS `aspect-ratio` or explicit dimensions
3. **Fonts**: Use `font-display: swap` + preload + `size-adjust` for fallback
4. **Dynamic content**: Insert above existing content only with user interaction
5. **Animations**: Use `transform` instead of layout properties

```css
/* Reserve space for dynamic content */
.ad-slot {
  min-height: 250px;
  aspect-ratio: 300 / 250;
}

/* Font fallback with size-adjust */
@font-face {
  font-family: "Custom Font";
  src: url("custom.woff2") format("woff2");
  font-display: swap;
}

@font-face {
  font-family: "Custom Font Fallback";
  src: local("Arial");
  size-adjust: 105%;
  ascent-override: 95%;
}
```

## Bundle Optimization Techniques

### Webpack Configuration

```javascript
// webpack.config.js
module.exports = {
  optimization: {
    splitChunks: {
      chunks: "all",
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: "vendors",
          chunks: "all",
        },
        // Separate large libraries
        react: {
          test: /[\\/]node_modules[\\/](react|react-dom)[\\/]/,
          name: "react",
          chunks: "all",
          priority: 10,
        },
      },
    },
    // Enable tree shaking
    usedExports: true,
    sideEffects: true,
  },
  performance: {
    maxAssetSize: 250000,
    maxEntrypointSize: 500000,
    hints: "warning",
  },
};
```

### Import Cost Awareness

| Library | Typical Size (minified + gzip) |
| --- | --- |
| `moment` | ~67 KB (use `date-fns` or `dayjs` instead) |
| `lodash` (full) | ~70 KB (import individual functions) |
| `chart.js` | ~60 KB (tree-shake unused chart types) |

```js
// BAD: imports entire library
import _ from "lodash";
_.get(obj, "a.b");

// GOOD: imports only needed function
import get from "lodash/get";
get(obj, "a.b");
```

## Resources

- [web.dev: Optimize LCP](https://web.dev/articles/optimize-lcp)
- [web.dev: Optimize INP](https://web.dev/articles/optimize-inp)
- [web.dev: Optimize CLS](https://web.dev/articles/optimize-cls)
- [Webpack Code Splitting](https://webpack.js.org/guides/code-splitting/)
- [Chrome DevTools Performance](https://developer.chrome.com/docs/devtools/performance)
