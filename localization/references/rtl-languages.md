# RTL Language Support Reference

Detailed patterns for supporting Right-to-Left (RTL) languages in web applications.

## RTL Languages

| Language | Code | Script |
| --- | --- | --- |
| Arabic | ar | Arabic |
| Hebrew | he | Hebrew |
| Persian (Farsi) | fa | Arabic |
| Urdu | ur | Arabic |
| Pashto | ps | Arabic |
| Sindhi | sd | Arabic |
| Kurdish (Sorani) | ckb | Arabic |
| Dhivehi | dv | Thaana |
| Yiddish | yi | Hebrew |

## HTML Setup

### Document Level

```html
<html lang="ar" dir="rtl">
```

### Dynamic Direction Switching

```js
function setDirection(locale) {
  const rtlLocales = ["ar", "he", "fa", "ur", "ps", "sd", "ckb", "dv", "yi"];
  const lang = locale.split("-")[0];
  const dir = rtlLocales.includes(lang) ? "rtl" : "ltr";
  document.documentElement.dir = dir;
  document.documentElement.lang = locale;
}
```

### Bidirectional Content

```html
<!-- bdi: isolates inline bidirectional content -->
<p>User <bdi>محمد</bdi> commented on your post</p>

<!-- bdo: overrides text direction -->
<p><bdo dir="ltr">+1-555-123-4567</bdo></p>

<!-- dir="auto": browser detects direction from content -->
<input type="text" dir="auto" />
```

## CSS Logical Properties — Full Reference

### Margin

```css
/* Physical → Logical */
margin-top       → margin-block-start
margin-bottom    → margin-block-end
margin-left      → margin-inline-start
margin-right     → margin-inline-end

/* Shorthand */
margin: 10px 20px;  →  margin-block: 10px; margin-inline: 20px;
```

### Padding

```css
padding-top      → padding-block-start
padding-bottom   → padding-block-end
padding-left     → padding-inline-start
padding-right    → padding-inline-end
```

### Border

```css
border-left            → border-inline-start
border-right           → border-inline-end
border-left-color      → border-inline-start-color
border-right-width     → border-inline-end-width
border-top-left-radius → border-start-start-radius
border-top-right-radius → border-start-end-radius
border-bottom-left-radius → border-end-start-radius
border-bottom-right-radius → border-end-end-radius
```

### Position

```css
top     → inset-block-start
bottom  → inset-block-end
left    → inset-inline-start
right   → inset-inline-end
```

### Size

```css
width      → inline-size
height     → block-size
min-width  → min-inline-size
max-width  → max-inline-size
min-height → min-block-size
max-height → max-block-size
```

### Text and Float

```css
text-align: left   → text-align: start
text-align: right  → text-align: end
float: left        → float: inline-start
float: right       → float: inline-end
clear: left        → clear: inline-start
```

## Icon and Image Mirroring

Some icons must be mirrored in RTL. Others must NOT be mirrored.

### Icons to Mirror

- Navigation arrows (back, forward, next, previous)
- Progress indicators (horizontal)
- Text alignment icons
- Undo/redo icons
- List indent/outdent icons
- Send/reply icons

```css
[dir="rtl"] .icon-mirror {
  transform: scaleX(-1);
}
```

### Icons NOT to Mirror

- Media controls (play, pause, fast forward)
- Clocks and timers
- Checkmarks and X marks
- Plus/minus signs
- Music notes
- Charts (unless directional)
- Slashes (/)
- Logos and brand icons

## Layout Patterns

### Flexbox (auto-adjusts with dir)

```css
.container {
  display: flex;
  /* In RTL, flex items automatically reverse inline direction */
  gap: 16px;
}
```

### Grid (auto-adjusts with dir)

```css
.layout {
  display: grid;
  grid-template-columns: 1fr 3fr;
  /* In RTL, columns are automatically mirrored */
}
```

### Scroll Direction

```css
/* Horizontal scroll in RTL starts from the right */
.scroll-container {
  overflow-x: auto;
  direction: inherit; /* Follows document dir */
}
```

## Testing Checklist

- [ ] Text alignment follows content direction
- [ ] Navigation order reversed (breadcrumbs, pagination)
- [ ] Form labels aligned correctly
- [ ] Icons with directional meaning are mirrored
- [ ] Phone numbers, code, and URLs remain LTR
- [ ] Flexbox/Grid layouts work in both directions
- [ ] Scrollbars appear on correct side
- [ ] Bidirectional text renders correctly
- [ ] No hardcoded `left`/`right` in CSS (use logical properties)
- [ ] Input fields support RTL text entry

## Resources

- [W3C Internationalization: Inline BiDi Markup](https://www.w3.org/International/articles/inline-bidi-markup/)
- [CSS Logical Properties (MDN)](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_logical_properties_and_values)
- [Material Design BiDi Guide](https://m2.material.io/design/usability/bidirectionality.html)
