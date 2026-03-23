# ripgrep Advanced Patterns

Practical ripgrep patterns for common code search scenarios.

## Finding Definitions

```bash
# Function definitions (various languages)
rg 'def \w+\(' -t py                        # Python
rg '(func|function)\s+\w+' -t go            # Go
rg 'fn \w+' -t rust                         # Rust
rg '(public|private|protected).*\w+\s*\(' -t java  # Java methods

# Class definitions
rg 'class \w+' -t py
rg '(class|interface|enum) \w+' -t java

# Constant/variable definitions
rg '(const|let|var)\s+\w+' -t js
rg 'val \w+|var \w+' -t kotlin
```

## Finding Usages

```bash
# Import statements
rg '^import ' -t py
rg '^(import|from .* import)' -t py
rg "^(import|require\()" -t js

# TODO/FIXME comments
rg '(TODO|FIXME|HACK|XXX|WARN):?' --type-add 'src:*.{js,ts,py,java,go,rs}' -tsrc

# API endpoints
rg '@(Get|Post|Put|Delete|Patch)Mapping' -t java
rg 'app\.(get|post|put|delete|patch)\(' -t js
rg '@app\.(route|get|post)' -t py
```

## Multiline Patterns

```bash
# Multi-line function signature
rg -U 'fn \w+\([^)]*\)\s*->\s*\w+' -t rust

# Struct/class with fields
rg -U 'struct \w+ \{[^}]+\}' -t rust
rg -U 'data class \w+\([^)]+\)' -t kotlin

# Multi-line string containing pattern
rg -U --multiline-dotall 'try \{.*catch' -t java
```

## Filtering Techniques

```bash
# Exclude test files
rg 'pattern' -g '!*test*' -g '!*spec*' -g '!__tests__'

# Only source directories
rg 'pattern' src/ lib/ app/

# Exclude generated code
rg 'pattern' -g '!*.generated.*' -g '!*_gen.*' -g '!dist/' -g '!build/'

# Custom type definition
rg --type-add 'web:*.{html,css,js,ts,jsx,tsx}' -tweb 'pattern'
rg --type-add 'config:*.{yml,yaml,json,toml}' -tconfig 'pattern'
```

## Output Formatting

```bash
# JSON output (for piping)
rg 'pattern' --json

# Only filenames
rg -l 'pattern'

# Count per file
rg -c 'pattern' | sort -t: -k2 -rn  # Sort by count descending

# Max results
rg 'pattern' --max-count 5           # 5 results per file

# Column number (for editor integration)
rg --column 'pattern'

# Statistics
rg 'pattern' --stats
```

## Replacement (Preview Only)

ripgrep replacements only affect stdout — they never modify files.
Use `sed`, `ast-grep`, or IDE for actual file modifications.

```bash
# Simple replacement
rg 'oldName' -r 'newName'

# Capture group
rg '(\w+)Error' -r '${1}Exception'

# Named capture
rg '(?P<name>\w+)\.log' -r '${name}.debug'

# Preview changes in context
rg 'oldPattern' -r 'newPattern' -C2
```

## Performance Tips

```bash
# Limit search depth
rg 'pattern' --max-depth 3

# Limit file size
rg 'pattern' --max-filesize 1M

# Use fixed strings when possible (faster)
rg -F 'exact.string.match'

# Parallel threads (default: auto)
rg 'pattern' --threads 8

# Sort output (disables streaming, slower)
rg 'pattern' --sort path
```

## Combining with Other Tools

```bash
# Find files, then search
fd -e rs | xargs rg 'pattern'

# Search and open in editor
rg -l 'pattern' | xargs code

# Count TODOs by author (with git blame)
rg -l 'TODO' | xargs -I{} git blame {} | rg 'TODO'

# Search in git diff only
git diff --name-only | xargs rg 'pattern'
```

## Resources

- [ripgrep User Guide](https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md)
- [ripgrep Docs](https://ripgrep.dev/docs/)
- [Rust regex syntax](https://docs.rs/regex/latest/regex/#syntax)
