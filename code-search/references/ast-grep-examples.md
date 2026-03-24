# ast-grep Examples

Practical ast-grep patterns for structural code search and transformation.

## JavaScript / TypeScript

### Find Patterns

```bash
# Console statements
sg run -p 'console.log($$$)' -l js
sg run -p 'console.$METHOD($$$)' -l js    # log, warn, error, etc.

# Async functions
sg run -p 'async function $NAME($$$) { $$$ }' -l js

# Arrow functions assigned to const
sg run -p 'const $NAME = ($$$) => $BODY' -l ts

# React useState
sg run -p 'const [$STATE, $SETTER] = useState($$$)' -l tsx

# Unsafe equality
sg run -p '$A == $B' -l js                # Finds == (not ===)

# Optional chaining candidates
sg run -p '$OBJ && $OBJ.$PROP' -l ts
```

### Transformations

```bash
# var → let
sg run -p 'var $NAME = $VAL' -r 'let $NAME = $VAL' -l js --interactive

# Add optional chaining
sg run -p '$OBJ && $OBJ.$PROP' -r '$OBJ?.$PROP' -l ts --interactive

# console.log removal
sg run -p 'console.log($$$)' -r '' -l js --interactive

# require → import
sg run -p 'const $NAME = require($PATH)' -r 'import $NAME from $PATH' -l js --interactive
```

## Python

```bash
# Find print statements
sg run -p 'print($$$)' -l py

# Find class definitions
sg run -p 'class $NAME($$$): $$$BODY' -l py

# Find decorators
sg run -p '@$DECORATOR
def $NAME($$$): $$$BODY' -l py

# Find assert statements
sg run -p 'assert $CONDITION' -l py

# Find except bare clauses (anti-pattern)
sg run -p 'except: $$$' -l py
```

## Java / Kotlin

```bash
# Find public methods
sg run -p 'public $RET $NAME($$$) { $$$ }' -l java

# Find null checks
sg run -p 'if ($VAR == null) { $$$ }' -l java
sg run -p 'if ($VAR != null) { $$$ }' -l java

# Find annotations
sg run -p '@Deprecated $$$' -l java

# Find Kotlin data classes
sg run -p 'data class $NAME($$$)' -l kotlin

# Find when expressions
sg run -p 'when ($EXPR) { $$$ }' -l kotlin
```

## Go

```bash
# Find error handling patterns
sg run -p 'if err != nil { $$$ }' -l go

# Find goroutine launches
sg run -p 'go $FUNC($$$)' -l go

# Find defer statements
sg run -p 'defer $EXPR' -l go

# Find struct definitions
sg run -p 'type $NAME struct { $$$ }' -l go
```

## YAML Rule Files

For complex patterns, use YAML rule files instead of CLI:

```yaml
# rules/no-console.yml
id: no-console-log
message: Remove console.log statements
severity: warning
language: typescript
rule:
  pattern: console.log($$$)
fix: ""
```

```bash
sg scan --rule rules/no-console.yml
```

### Advanced Rule with Constraints

```yaml
# rules/no-self-comparison.yml
id: no-self-comparison
message: Comparing a value to itself is likely a bug
severity: error
language: javascript
rule:
  pattern: $A === $A
  not:
    pattern: NaN === NaN
```

## Combining ast-grep with Other Tools

```bash
# Find files with pattern, then examine with rg
sg run -p 'console.log($$$)' -l js --json | jq -r '.file' | sort -u

# Count occurrences
sg run -p 'TODO($$$)' -l js --json | jq length

# Batch transform with review
sg run -p '$A == $B' -r '$A === $B' -l js --interactive
```

## Resources

- [ast-grep Official Documentation](https://ast-grep.github.io/)
- [ast-grep Pattern Syntax](https://ast-grep.github.io/guide/pattern-syntax.html)
- [ast-grep Playground](https://ast-grep.github.io/playground.html)
- [ast-grep Rule Configuration](https://ast-grep.github.io/guide/rule-config.html)
