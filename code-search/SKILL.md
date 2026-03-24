---
name: code-search
description: >-
  Efficient code search strategies for large codebases including ripgrep
  advanced patterns, AST-based search with ast-grep, git history search
  (pickaxe, git grep, bisect), LSP navigation, GitHub code search,
  and codebase exploration strategies (top-down, bottom-up, call chain,
  data flow tracing).
  Use when searching large codebases, tracing code history, navigating
  unfamiliar projects, or finding specific patterns across files.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# Code Search Rules

## 1. Tool Selection Guide

| Need | Tool |
| --- | --- |
| Fast text search | ripgrep (`rg`) |
| Structural code patterns | ast-grep (`sg`) |
| When was code introduced/removed | `git log -S` / `git log -G` |
| Search tracked files only | `git grep` |
| Find bug-introducing commit | `git bisect` |
| Symbol navigation (definition, references) | LSP (IDE) |
| Search across repositories | GitHub Code Search |

**Principle**: Combine tools — text search (rg) + structural search (ast-grep) +
semantic navigation (LSP) + history search (git) for comprehensive exploration.

## 2. ripgrep (rg)

### Essential Flags

| Flag | Purpose | Example |
| --- | --- | --- |
| `-t` / `-T` | Include / exclude file type | `rg -trust 'pattern'` |
| `-g` | Glob filter | `rg 'pattern' -g '*.toml'` |
| `-g '!...'` | Glob exclude | `rg 'pattern' -g '!vendor'` |
| `-F` | Fixed string (no regex) | `rg -F 'a.b.c'` |
| `-i` | Case insensitive | `rg -i 'error'` |
| `-S` | Smart case | `rg -S 'Error'` (case-sensitive if uppercase) |
| `-w` | Word boundary | `rg -w 'log'` (not `logging`) |
| `-l` | Files with matches only | `rg -l 'TODO'` |
| `-c` | Count matches per file | `rg -c 'TODO'` |
| `-C N` | Context (N lines around) | `rg -C3 'pattern'` |
| `-A N` / `-B N` | After / before context | `rg -B2 -A5 'fn main'` |
| `-U` | Multiline mode | `rg -U 'fn \w+\([^)]*\)\s*\{'` (note: cannot handle nested braces) |
| `--pcre2` | PCRE2 regex (lookaround) | `rg --pcre2 '(?<=fn )\w+'` |
| `-r` | Replace (stdout only) | `rg 'old' -r 'new'` |

### Ignore Hierarchy

Files are automatically excluded based on (highest priority first):

1. `.rgignore` — ripgrep-specific
2. `.ignore` — shared with other tools (fd, etc.)
3. `.gitignore` — git tracked ignores

Override with `-u` (once: skip gitignore, twice: include hidden, thrice: include binary).

### Configuration File

Set `RIPGREP_CONFIG_PATH` to a config file:

```text
--smart-case
--max-columns=150
--max-columns-preview
--glob=!.git/*
--glob=!node_modules/*
--glob=!vendor/*
```

## 3. AST-Based Search (ast-grep)

Search code by structure, not text. Ignores whitespace, comments, and formatting.

### Meta-Variables

| Syntax | Matches |
| --- | --- |
| `$VAR` | Single AST node |
| `$$$` | Zero or more nodes (spread) |
| `$_` | Wildcard (non-capturing) |

### Examples

```bash
# Find all console.log calls
sg run -p 'console.log($$$)' -l js

# Find equality self-comparison (bug pattern)
sg run -p '$A == $A' -l js

# Find and replace var → let (interactive)
sg run -p 'var $NAME = $VAL' -r 'let $NAME = $VAL' -l js --interactive

# Find optional chaining candidates
sg run -p '$PROP && $PROP()' -r '$PROP?.()' -l ts
```

### When to Use ast-grep Over ripgrep

- Finding function calls with specific argument patterns
- Matching code structures regardless of formatting
- Avoiding false positives in comments and strings
- Safe structural code transformations

## 4. Git History Search

### git log -S (Pickaxe)

Find commits where a string's occurrence count changed (added/removed).

```bash
# When was this function introduced?
git log -S "functionName" --oneline

# With diff output
git log -S "functionName" -p

# Regex mode
git log -S "function\w+" --pickaxe-regex
```

### git log -G (Regex in Diff)

Find commits where diff lines match a regex (broader than -S).

```bash
# Find changes involving a pattern
git log -G "frotz\(nitfol" --oneline
```

| | `-S` | `-G` |
| --- | --- | --- |
| Matches | Occurrence count change | Regex match in diff lines |
| Moved code | Skipped (count unchanged) | Found (appears in diff) |
| Use for | "When was this added/removed?" | "When was this changed?" |

**Recommendation**: Start with `-S` for most cases. Use `-G` when you need to find
changes that include moving or reformatting code.

### git grep

Search tracked files with git-aware filtering.

```bash
git grep -n 'pattern'                    # Line numbers
git grep -W 'pattern'                    # Show full function context
git grep -p 'pattern'                    # Show enclosing function name
git grep -e 'A' --and -e 'B'           # Boolean AND
git grep 'pattern' HEAD~5               # Search at specific commit
git grep 'pattern' -- '*.java'          # File pattern filter
```

### git bisect

Binary search for the commit that introduced a bug.

```bash
git bisect start HEAD v1.0 --          # Start
git bisect good                         # Current commit is good
git bisect bad                          # Current commit is bad

# Automated with test script
git bisect run ./test.sh               # 0=good, 1-124=bad, 125=skip

# Limit to specific path
git bisect start HEAD v1.0 -- src/module/
```

## 5. LSP Navigation

### Key Features

| Action | VS Code Shortcut | Purpose |
| --- | --- | --- |
| Go to Definition | `F12` | Jump to symbol definition |
| Find All References | `Shift+F12` | Find all usages of a symbol |
| Go to Implementation | `Ctrl+Shift+F12` | Find interface implementations |
| Peek Definition | `Alt+F12` | Inline preview without navigation |
| Workspace Symbol | `Ctrl+T` | Search symbols across project |
| File Symbol | `Ctrl+Shift+O` | Search symbols in current file |
| Call Hierarchy | Right-click → Show Call Hierarchy | Incoming and outgoing calls |

### When to Use LSP Over Text Search

- Navigating type hierarchies (interface → implementation)
- Finding all references (includes renamed imports, destructured usages)
- Understanding call chains (Call Hierarchy)
- Safe rename across entire codebase

## 6. GitHub Code Search

### Key Qualifiers

```text
repo:owner/name pattern        # Search in specific repo
org:name pattern               # Search in organization
language:go pattern            # Filter by language
path:src/*.js pattern          # Filter by file path
symbol:functionName            # Search symbol definitions
content:pattern                # Search file contents only (not paths)
```

### Operators

- Implicit AND: `sparse index` (both words)
- OR: `sparse OR index`
- NOT: `"fatal error" NOT path:__testing__`
- Regex: `/sparse.*index/`
- Exact: `"exact phrase"`

## 7. Codebase Exploration Strategies

### Top-Down (Architecture → Detail)

1. Read project structure: directory layout, build config, entry points
2. Identify module/package boundaries
3. Map inter-module dependencies (imports)
4. Drill down into specific implementations

Best for: Understanding overall architecture of an unfamiliar project.
Effort: 1-2 hours for medium projects, half day for large ones.

### Bottom-Up (Specific → General)

1. Start from a specific feature, bug, or error message
2. Trace callers upward (LSP: incoming calls)
3. Understand the module's role and boundaries
4. Place in the context of the full system

Best for: Debugging, understanding a specific feature.
Effort: 15-60 minutes for a focused investigation.

### Call Chain Tracing

1. Find the entry point (API handler, event listener)
2. Use LSP Call Hierarchy to trace outgoing calls
3. Use `rg -A10` or `git grep -W` to read function bodies
4. Map the full request/event flow

### Data Flow Tracing

1. Find where a variable/value is created
2. Use LSP Find References to trace all usages
3. Follow transformations (map, convert, serialize)
4. Identify where the value is consumed (API response, DB write, UI)

## 8. Common Anti-Patterns

| Anti-Pattern | Problem | Fix |
| --- | --- | --- |
| `grep -r . pattern` | Searches binary/ignored files, slow | Use `rg` (auto-filters) |
| Overly broad regex (`.*`) | Too many results, slow | Narrow with type/path filters first |
| Text search for code structure | False positives in comments/strings | Use ast-grep |
| Reading entire git history linearly | Inefficient | Use `git log -S` or `git bisect` |
| Reading all results without filtering | Time wasted | Use `-l`, `-c`, `--max-count` |
| Only using IDE search | Slow on large projects | Combine CLI tools with IDE |
| No search scope restriction | Searches irrelevant files | Specify directory, type, glob |
| Ignoring git-based search | Missing historical context | Use pickaxe for "when was this added" |

For detailed ripgrep patterns and ast-grep examples, see
[references/ripgrep-patterns.md](references/ripgrep-patterns.md) and
[references/ast-grep-examples.md](references/ast-grep-examples.md).
