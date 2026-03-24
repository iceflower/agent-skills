# ICU Message Format Reference

Detailed reference for ICU Message Format syntax and CLDR plural rules.

## Syntax Overview

```text
{variable}                          # Simple replacement
{variable, type}                    # Typed format
{variable, type, style}             # Typed format with style
```

## Types

### number

```text
{price, number}                     # Default: 1,234.56
{price, number, integer}            # Integer: 1,235
{price, number, currency}           # Currency (requires locale)
{price, number, percent}            # Percent: 12%
{price, number, ::currency/USD}     # Skeleton: $1,234.56
```

### date / time

```text
{when, date}                        # Default date
{when, date, short}                 # 1/1/26
{when, date, medium}                # Jan 1, 2026
{when, date, long}                  # January 1, 2026
{when, date, full}                  # Thursday, January 1, 2026
{when, time, short}                 # 2:30 PM
{when, time, medium}                # 2:30:00 PM
```

### plural

```text
{count, plural,
  =0 {No messages}
  one {# message}
  other {# messages}
}
```

The `#` symbol is replaced with the formatted numeric value.

### select

```text
{type, select,
  warning {⚠️ Warning: {detail}}
  error {❌ Error: {detail}}
  other {ℹ️ Info: {detail}}
}
```

### selectordinal

```text
{rank, selectordinal,
  one {#st}
  two {#nd}
  few {#rd}
  other {#th}
}
```

## CLDR Plural Categories

Not all languages use all categories. Always provide `other`.

| Language | Categories Used |
| --- | --- |
| English | one, other |
| French | one, many, other |
| Arabic | zero, one, two, few, many, other |
| Polish | one, few, many, other |
| Korean | other (only) |
| Japanese | other (only) |
| Chinese | other (only) |
| Russian | one, few, many, other |
| Czech | one, few, many, other |
| Welsh | zero, one, two, few, many, other |

### Category Definitions (English)

| Category | Rule | Example |
| --- | --- | --- |
| one | n = 1 | 1 item |
| other | everything else | 0, 2, 3, ... items |

### Category Definitions (Arabic)

| Category | Rule | Example |
| --- | --- | --- |
| zero | n = 0 | 0 كتب |
| one | n = 1 | كتاب واحد |
| two | n = 2 | كتابان |
| few | 3-10 (complex rule) | 3 كتب |
| many | 11-99 (complex rule) | 11 كتابًا |
| other | 100+ | 100 كتاب |

## Escaping

Use single quotes to escape syntax characters:

```text
{name} has '{'braces'}' in it       # Output: {name} has {braces} in it
It''s a nice day                     # Output: It's a nice day
```

## Nesting Best Practices

- Keep nesting depth to 2 levels maximum
- Complex messages with 3+ variables may be better split into separate messages
- Provide translator notes for nested messages

## ICU MessageFormat 2.0 (Preview)

The next-generation format introduces new syntax:

```text
.input {$count :number}
.match $count
one {{You have {$count} notification}}
*   {{You have {$count} notifications}}
```

Key changes:

- Declaration syntax (`.input`, `.local`)
- Pattern matching (`.match`)
- Function calls (`:number`, `:datetime`)
- Markup support

Status: Technical Preview. Not yet recommended for production.

## Resources

- [ICU User Guide - Messages](https://unicode-org.github.io/icu/userguide/format_parse/messages/)
- [CLDR Plural Rules](https://www.unicode.org/cldr/charts/latest/supplemental/language_plural_rules.html)
- [MessageFormat 2.0 WG](https://github.com/unicode-org/message-format-wg)
