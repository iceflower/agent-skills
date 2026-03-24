---
name: localization
description: >-
  Internationalization (i18n) and localization (l10n) patterns including
  ICU Message Format, i18n library integration (react-intl, i18next, vue-i18n),
  RTL language support, Intl API formatting, translation file management,
  and Unicode/CLDR considerations.
  Use when building multilingual applications, implementing i18n libraries,
  handling RTL layouts, or managing translation workflows.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# Internationalization (i18n) and Localization (l10n) Rules

## 1. Core Principles

- **Externalize all user-facing strings** — no hardcoded text in code
- **Use ICU Message Format** for plurals, gender, and selections
- **Use Intl API** for date, number, and currency formatting — never format manually
- **Design for text expansion** — translations can be 30-50% longer than English
- **Separate translation files by namespace/feature** for lazy loading
- **Automate translation workflows** with extraction tools and CI checks

## 2. ICU Message Format

The standard syntax for handling complex multilingual messages.

### Basic Syntax

```text
{variable, type, style}
```

### Plural

```text
{count, plural,
  =0 {No items}
  one {1 item}
  other {# items}
}
```

CLDR plural categories: `zero`, `one`, `two`, `few`, `many`, `other`.
Languages use different subsets (English: `one`/`other`, Arabic: all six,
Korean: `other` only). Always include `other` as fallback.

### Select (Gender / Category)

```text
{gender, select,
  male {He liked your post}
  female {She liked your post}
  other {They liked your post}
}
```

### Nested Messages

```text
{gender, select,
  male {{count, plural, one {He has # item} other {He has # items}}}
  female {{count, plural, one {She has # item} other {She has # items}}}
  other {{count, plural, one {They have # item} other {They have # items}}}
}
```

### Rules

- Always provide the `other` category as fallback (required even for languages like Korean/Japanese that only use `other`)
- Use `#` as a placeholder for the numeric value in plural messages
- Keep messages as complete sentences — never concatenate fragments
- Provide translator context/description for ambiguous messages

## 3. i18n Library Patterns

### Library Selection

| Library | Framework | Message Format | Namespace |
| --- | --- | --- | --- |
| react-intl (FormatJS) | React | ICU native | Manual |
| i18next | Any | Own syntax (ICU plugin) | Native |
| vue-i18n | Vue | Own + ICU support | Manual / SFC |

### react-intl (FormatJS)

```jsx
import { FormattedMessage, useIntl } from "react-intl";

// Declarative
<FormattedMessage id="greeting" defaultMessage="Hello, {name}!" values={{ name }} />

// Imperative
const intl = useIntl();
intl.formatMessage({ id: "greeting" }, { name });
intl.formatNumber(1000, { style: "currency", currency: "USD" });
intl.formatDate(new Date(), { dateStyle: "long" });
```

### i18next

```js
import { useTranslation } from "react-i18next";
const { t } = useTranslation("common");

t("greeting", { name: "World" });      // "Hello, {{name}}!"
t("item", { count: 5 });               // plural: item_one / item_other keys
t("common:button.save");               // namespace prefix
```

### vue-i18n

```vue
<template>
  <p>{{ $t("greeting", { name: "World" }) }}</p>
</template>

<script setup>
import { useI18n } from "vue-i18n";
const { t } = useI18n();
</script>
```

## 4. Translation File Management

### Directory Structure

```text
locales/
├── en/
│   ├── common.json        # Shared UI (buttons, labels)
│   ├── auth.json           # Authentication
│   ├── dashboard.json      # Dashboard page
│   └── errors.json         # Error messages
├── ko/
│   ├── common.json
│   ├── auth.json
│   └── ...
└── ja/
    └── ...
```

### Key Naming

```json
{
  "button.save": "Save",
  "button.cancel": "Cancel",
  "validation.required": "This field is required",
  "validation.minLength": "Must be at least {min} characters"
}
```

- Use dot-notation or nested keys consistently (don't mix)
- Use descriptive, hierarchical key names — not source text as keys
- Group by feature/component, not by page

### Namespace Splitting

- Split by feature: `auth.json`, `dashboard.json`, `settings.json`
- Keep shared UI in `common.json`
- Align namespaces with code-splitting for lazy loading

## 5. Intl API Formatting

Use the browser/runtime `Intl` API — never write manual formatting logic.

### Numbers and Currency

```js
new Intl.NumberFormat("ko-KR").format(1234567);
// "1,234,567"

new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(42);
// "$42.00"

new Intl.NumberFormat("en", { notation: "compact" }).format(1500000);
// "1.5M"
```

### Dates and Times

```js
new Intl.DateTimeFormat("ko-KR", { dateStyle: "long" }).format(date);
// "2026년 3월 24일"

new Intl.RelativeTimeFormat("ko", { numeric: "auto" }).format(-1, "day");
// "어제"
```

### Lists

```js
new Intl.ListFormat("en", { type: "conjunction" }).format(["A", "B", "C"]);
// "A, B, and C"
```

### Collation (Sorting)

```js
const collator = new Intl.Collator("de", { sensitivity: "base" });
["ä", "a", "z"].sort(collator.compare);
// ["a", "ä", "z"] (German sorting)
```

## 6. RTL (Right-to-Left) Support

RTL languages: Arabic (ar), Hebrew (he), Persian (fa), Urdu (ur).

### HTML Direction

```html
<html lang="ar" dir="rtl">

<!-- Bidirectional isolation -->
<p>User: <bdi>مستخدم</bdi> posted a comment</p>
```

### CSS Logical Properties

Replace physical properties (left/right) with logical properties for
automatic RTL support.

| Physical | Logical |
| --- | --- |
| `margin-left` | `margin-inline-start` |
| `margin-right` | `margin-inline-end` |
| `padding-left` | `padding-inline-start` |
| `padding-right` | `padding-inline-end` |
| `border-left` | `border-inline-start` |
| `left` / `right` | `inset-inline-start` / `inset-inline-end` |
| `text-align: left` | `text-align: start` |
| `float: left` | `float: inline-start` |
| `width` / `height` | `inline-size` / `block-size` |

### RTL Considerations

- Mirror directional icons (arrows, progress bars) with `transform: scaleX(-1)`
- Keep phone numbers, code snippets, and URLs in LTR direction
- Use HTML `dir` attribute over CSS `direction` (better for accessibility)
- Flexbox and Grid automatically adjust with `dir="rtl"`
- Test layouts in both LTR and RTL modes (if your application supports RTL languages)
- Icons to mirror in RTL: navigation arrows, progress bars, send/reply, undo/redo
- Icons NOT to mirror: media controls, clocks, checkmarks, logos, slashes

## 7. Unicode and CLDR

### BCP 47 Language Tags

```text
en          # English
en-US       # American English
zh-Hans     # Simplified Chinese
zh-Hant-TW  # Traditional Chinese (Taiwan)
sr-Latn     # Serbian (Latin script)
sr-Cyrl     # Serbian (Cyrillic script)
```

### Grapheme Cluster Awareness

```js
// String.length counts UTF-16 code units, not visible characters
"👨‍👩‍👧‍👦".length;                    // 11

// Use Intl.Segmenter for correct grapheme counting
const seg = new Intl.Segmenter("en", { granularity: "grapheme" });
[...seg.segment("👨‍👩‍👧‍👦")].length;   // 1
```

### Locale-Aware String Operations

- Case conversion: use `toLocaleLowerCase(locale)` (Turkish `i` → `İ`)
- Sorting: use `Intl.Collator` (Swedish `ä` sorts after `z`)
- Word breaking: CJK languages have no spaces — use `Intl.Segmenter`
- Normalization: use `String.prototype.normalize("NFC")` before comparison

## 8. Translation Workflow and CI

### Extraction

```bash
# FormatJS
formatjs extract 'src/**/*.tsx' --out-file lang/en.json

# i18next
npx i18next-scanner --config i18next-scanner.config.js
```

### CI Checks

Validate on every PR:

- **Missing keys**: source code keys exist in all translation files
- **Unused keys**: translation files have no orphaned keys
- **Syntax validation**: ICU message format is parseable
- **Placeholder match**: variables in source match variables in translations

### Translation Platforms

- Crowdin, Phrase, Lokalise, Transifex (SaaS)
- Weblate (open source, self-hosted)

Integrate via CLI + CI pipeline for automated upload/download.

## 9. Common Anti-Patterns

| Anti-Pattern | Problem | Fix |
| --- | --- | --- |
| String concatenation | Word order varies by language | Use complete message with placeholders |
| Hardcoded strings | Not translatable | Externalize to translation files |
| Manual date/number formatting | Locale-specific formats ignored | Use `Intl` API |
| `count === 1 ? "item" : "items"` | Fails for languages with complex plural rules | Use ICU plural |
| Source text as translation key | Key breaks when English text changes | Use descriptive keys |
| Fixed-width UI | Text truncation in longer languages | Design for 30-50% expansion |
| Text in images | Cannot be translated | Separate text from images |
| Ignoring BiDi | Layout breaks for RTL languages | Use CSS logical properties |
| Missing translator context | Ambiguous translations | Provide descriptions |
| Server timezone for display | Wrong time for user | Use user's timezone |

## 10. References

For detailed RTL implementation patterns and ICU format examples, see
[references/rtl-languages.md](references/rtl-languages.md) and
[references/icu-message-format.md](references/icu-message-format.md).

### External Resources

- [ICU Message Format](https://unicode-org.github.io/icu/userguide/format_parse/messages/)
- [CLDR Plural Rules](https://www.unicode.org/cldr/charts/latest/supplemental/language_plural_rules.html)
- [FormatJS](https://formatjs.github.io/)
- [i18next](https://www.i18next.com/)
- [vue-i18n](https://vue-i18n.intlify.dev/)
- [MDN Intl API](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl)
- [CSS Logical Properties (MDN)](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_logical_properties_and_values)
- [W3C Internationalization](https://www.w3.org/International/)
