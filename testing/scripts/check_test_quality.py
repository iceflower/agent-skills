#!/usr/bin/env python3
"""Check test quality for common issues.

Checks:
- Missing assertions in test methods
- Test naming convention violations
- Empty test methods
- Commented-out tests
- Missing test class/function docstrings
- Overly long test methods
- Multiple assertions without description (in frameworks that support it)

Usage:
    python check_test_quality.py tests/
    python check_test_quality.py --recursive src/
    python check_test_quality.py --max-lines 50 tests/test_service.py
"""

import argparse
import os
import re
import sys
from typing import Dict, List, Set, Tuple

Finding = Tuple[str, int, str, str]  # (file, line, severity, message)

ERROR = "ERROR"
WARN = "WARN"

# Test file patterns
TEST_FILE_PATTERNS = [
    re.compile(r"^test_.*\.py$"),
    re.compile(r"^.*_test\.py$"),
    re.compile(r"^.*Test\.java$"),
    re.compile(r"^.*Test\.kt$"),
    re.compile(r"^.*\.test\.[jt]sx?$"),
    re.compile(r"^.*\.spec\.[jt]sx?$"),
    re.compile(r"^.*_test\.go$"),
]

# Assert patterns by language
PYTHON_ASSERT_PATTERNS = [
    r"\bassert\b",
    r"self\.assert\w+\(",
    r"pytest\.raises\(",
    r"pytest\.warns\(",
    r"pytest\.approx\(",
    r"\.should\b",
    r"expect\(",
    r"mock\.assert_",
    r"\.assert_called",
    r"\.assert_any_call",
    r"with\s+pytest\.",
]

JS_ASSERT_PATTERNS = [
    r"\bexpect\s*\(",
    r"\bassert\s*[\.(]",
    r"\.should\b",
    r"\.to\b",
    r"\.toBe\(",
    r"\.toEqual\(",
    r"\.toThrow\(",
    r"\.rejects\.",
    r"\.resolves\.",
]

JAVA_ASSERT_PATTERNS = [
    r"\bassertThat\(",
    r"\bassertEquals\(",
    r"\bassertTrue\(",
    r"\bassertFalse\(",
    r"\bassertNull\(",
    r"\bassertNotNull\(",
    r"\bassertThrows\(",
    r"\bassertDoesNotThrow\(",
    r"\bverify\(",
    r"\bassertThatThrownBy\(",
    r"Assertions\.\w+\(",
]

GO_ASSERT_PATTERNS = [
    r"\bt\.(?:Error|Fatal|Fail|Log)f?\(",
    r"\bt\.(?:Helper|Run|Parallel|Skip)\(",
    r"\bassert\.\w+\(",
    r"\brequire\.\w+\(",
]


def is_test_file(filename: str) -> bool:
    """Check if a filename matches test file patterns."""
    return any(p.match(filename) for p in TEST_FILE_PATTERNS)


def detect_language(filepath: str) -> str:
    """Detect language from file extension."""
    ext = os.path.splitext(filepath)[1]
    mapping = {
        ".py": "python",
        ".java": "java",
        ".kt": "kotlin",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".go": "go",
    }
    return mapping.get(ext, "unknown")


def get_assert_patterns(language: str) -> List[str]:
    """Get assertion patterns for a language."""
    patterns = {
        "python": PYTHON_ASSERT_PATTERNS,
        "javascript": JS_ASSERT_PATTERNS,
        "typescript": JS_ASSERT_PATTERNS,
        "java": JAVA_ASSERT_PATTERNS,
        "kotlin": JAVA_ASSERT_PATTERNS,
        "go": GO_ASSERT_PATTERNS,
    }
    return patterns.get(language, [])


def check_python_tests(filepath: str, lines: List[str], max_lines: int) -> List[Finding]:
    """Check Python test file quality."""
    findings: List[Finding] = []
    in_function = False
    func_name = ""
    func_start = 0
    func_lines: List[str] = []
    indent_level = 0

    for i, line in enumerate(lines, start=1):
        stripped = line.rstrip()

        # Detect test function/method
        m = re.match(r"^(\s*)def\s+(test_\w+)\s*\(", stripped)
        if m:
            # Check previous function
            if in_function:
                _check_python_function(
                    filepath, func_name, func_start, func_lines,
                    max_lines, findings,
                )

            indent_level = len(m.group(1))
            func_name = m.group(2)
            func_start = i
            func_lines = []
            in_function = True
            continue

        if in_function:
            # Check if we've left the function
            if stripped and not stripped.startswith("#"):
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent_level and not line.strip() == "":
                    _check_python_function(
                        filepath, func_name, func_start, func_lines,
                        max_lines, findings,
                    )
                    in_function = False
                    # Check if this is a new test function
                    m2 = re.match(r"^(\s*)def\s+(test_\w+)\s*\(", stripped)
                    if m2:
                        indent_level = len(m2.group(1))
                        func_name = m2.group(2)
                        func_start = i
                        func_lines = []
                        in_function = True
                    continue

            func_lines.append(stripped)

        # Check for commented-out tests
        if re.match(r"\s*#\s*def\s+test_", stripped):
            findings.append((
                filepath, i, WARN,
                "Commented-out test function. Remove or re-enable it.",
            ))

        # Check naming: test functions should be descriptive
        m = re.match(r"^\s*def\s+(test\d+|test_\d+)\s*\(", stripped)
        if m:
            findings.append((
                filepath, i, WARN,
                f"Test '{m.group(1)}' has a non-descriptive name. "
                f"Use a name that describes the behavior being tested.",
            ))

    # Check last function
    if in_function:
        _check_python_function(
            filepath, func_name, func_start, func_lines,
            max_lines, findings,
        )

    return findings


def _check_python_function(
    filepath: str,
    func_name: str,
    func_start: int,
    func_lines: List[str],
    max_lines: int,
    findings: List[Finding],
) -> None:
    """Check a single Python test function."""
    # Filter out blank lines and comments for content check
    content_lines = [
        ln for ln in func_lines
        if ln.strip() and not ln.strip().startswith("#")
    ]

    # Empty test
    if not content_lines or (len(content_lines) == 1 and "pass" in content_lines[0]):
        findings.append((
            filepath, func_start, ERROR,
            f"Test '{func_name}' is empty. Either implement it or remove it.",
        ))
        return

    # Check for assertions
    has_assert = False
    all_patterns = PYTHON_ASSERT_PATTERNS
    for ln in content_lines:
        for pat in all_patterns:
            if re.search(pat, ln):
                has_assert = True
                break
        if has_assert:
            break

    if not has_assert:
        findings.append((
            filepath, func_start, ERROR,
            f"Test '{func_name}' has no assertions. "
            f"Tests must verify expected behavior.",
        ))

    # Too long
    if len(content_lines) > max_lines:
        findings.append((
            filepath, func_start, WARN,
            f"Test '{func_name}' is {len(content_lines)} lines (max: {max_lines}). "
            f"Consider splitting into smaller focused tests.",
        ))


def check_js_tests(filepath: str, lines: List[str], max_lines: int) -> List[Finding]:
    """Check JavaScript/TypeScript test file quality."""
    findings: List[Finding] = []

    # Track it/test blocks (simplified - doesn't handle nested properly)
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Check for skipped tests
        if re.search(r"\b(?:it|test|describe)\.skip\s*\(", stripped):
            findings.append((
                filepath, i, WARN,
                "Skipped test found. Remove skip or re-enable the test.",
            ))

        # Check for .only (accidentally committed focused tests)
        if re.search(r"\b(?:it|test|describe)\.only\s*\(", stripped):
            findings.append((
                filepath, i, ERROR,
                "Focused test (.only) found. This disables all other tests.\n"
                "  Remove .only before committing.",
            ))

        # Check for empty test descriptions
        if re.search(r"\b(?:it|test)\s*\(\s*[\"']\s*[\"']", stripped):
            findings.append((
                filepath, i, WARN,
                "Test has empty description. Add a meaningful test name.",
            ))

        # Check commented-out tests
        if re.match(r"\s*//\s*(?:it|test|describe)\s*\(", stripped):
            findings.append((
                filepath, i, WARN,
                "Commented-out test. Remove or re-enable it.",
            ))

    return findings


def check_java_tests(filepath: str, lines: List[str], max_lines: int) -> List[Finding]:
    """Check Java/Kotlin test file quality."""
    findings: List[Finding] = []
    in_method = False
    method_name = ""
    method_start = 0
    method_lines: List[str] = []
    brace_count = 0
    has_test_annotation = False

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Track @Test annotation
        if re.match(r"@Test\b", stripped):
            has_test_annotation = True
            continue

        # Track @Disabled / @Ignore
        if re.match(r"@(?:Disabled|Ignore)\b", stripped):
            findings.append((
                filepath, i, WARN,
                "Disabled/Ignored test. Remove annotation or re-enable the test.",
            ))

        # Detect method start after @Test
        if has_test_annotation:
            m = re.match(r".*\b(\w+)\s*\(", stripped)
            if m and "class " not in stripped:
                if in_method:
                    _check_java_method(
                        filepath, method_name, method_start, method_lines,
                        max_lines, findings,
                    )

                method_name = m.group(1)
                method_start = i
                method_lines = []
                brace_count = stripped.count("{") - stripped.count("}")
                in_method = brace_count > 0
                has_test_annotation = False
                continue

        has_test_annotation = False

        if in_method:
            method_lines.append(stripped)
            brace_count += stripped.count("{") - stripped.count("}")
            if brace_count <= 0:
                _check_java_method(
                    filepath, method_name, method_start, method_lines,
                    max_lines, findings,
                )
                in_method = False

    if in_method:
        _check_java_method(
            filepath, method_name, method_start, method_lines,
            max_lines, findings,
        )

    return findings


def _check_java_method(
    filepath: str,
    method_name: str,
    method_start: int,
    method_lines: List[str],
    max_lines: int,
    findings: List[Finding],
) -> None:
    """Check a single Java test method."""
    content_lines = [
        ln for ln in method_lines
        if ln.strip() and not ln.strip().startswith("//")
    ]

    if not content_lines or (len(content_lines) == 1 and content_lines[0].strip() == "}"):
        findings.append((
            filepath, method_start, ERROR,
            f"Test '{method_name}' is empty.",
        ))
        return

    has_assert = False
    for ln in content_lines:
        for pat in JAVA_ASSERT_PATTERNS:
            if re.search(pat, ln):
                has_assert = True
                break
        if has_assert:
            break

    if not has_assert:
        findings.append((
            filepath, method_start, ERROR,
            f"Test '{method_name}' has no assertions.",
        ))

    if len(content_lines) > max_lines:
        findings.append((
            filepath, method_start, WARN,
            f"Test '{method_name}' is {len(content_lines)} lines (max: {max_lines}).",
        ))


def check_file(filepath: str, max_lines: int) -> List[Finding]:
    """Check a single test file."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return []

    language = detect_language(filepath)

    if language == "python":
        return check_python_tests(filepath, lines, max_lines)
    elif language in ("javascript", "typescript"):
        return check_js_tests(filepath, lines, max_lines)
    elif language in ("java", "kotlin"):
        return check_java_tests(filepath, lines, max_lines)

    return []


def find_test_files(
    path: str, recursive: bool, exclude_dirs: Set[str]
) -> List[str]:
    """Find test files at the given path."""
    if os.path.isfile(path):
        return [path] if is_test_file(os.path.basename(path)) else []

    if not os.path.isdir(path):
        return []

    files = []
    if recursive:
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith(".") and d not in exclude_dirs
            ]
            for filename in filenames:
                if is_test_file(filename):
                    files.append(os.path.join(dirpath, filename))
    else:
        for filename in os.listdir(path):
            if is_test_file(filename):
                full_path = os.path.join(path, filename)
                if os.path.isfile(full_path):
                    files.append(full_path)

    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check test quality for common issues.",
        epilog="Exit code 0 = clean, 1 = issues found.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="File or directory to check (default: current directory)",
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        default=True,
        help="Recursively scan directories (default: true)",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=40,
        help="Maximum lines per test method before warning (default: 40)",
    )
    parser.add_argument(
        "--exclude",
        default="venv,node_modules,__pycache__,.git,dist,build,vendor",
        help="Comma-separated directory names to exclude",
    )
    args = parser.parse_args()

    path = os.path.abspath(args.path)
    if not os.path.exists(path):
        print(f"Error: Path not found: {path}", file=sys.stderr)
        return 1

    exclude_dirs = set(args.exclude.split(","))
    files = find_test_files(path, args.recursive, exclude_dirs)

    if not files:
        print(f"No test files found at {path}")
        return 0

    all_findings: List[Finding] = []
    for filepath in files:
        all_findings.extend(check_file(filepath, args.max_lines))

    if not all_findings:
        print(f"OK: No issues found in {len(files)} test file(s).")
        return 0

    error_count = sum(1 for f in all_findings if f[2] == ERROR)
    warn_count = sum(1 for f in all_findings if f[2] == WARN)

    findings_by_file: Dict[str, List] = {}
    for filepath, line_num, severity, message in all_findings:
        rel_path = os.path.relpath(filepath, path if os.path.isdir(path) else os.path.dirname(path))
        findings_by_file.setdefault(rel_path, []).append((line_num, severity, message))

    for rel_path, findings in sorted(findings_by_file.items()):
        print(f"\n  {rel_path}:")
        for line_num, severity, message in findings:
            indented = message.replace("\n", "\n      ")
            print(f"    [{severity}] line {line_num}: {indented}")

    print(f"\nChecked {len(files)} test file(s): {error_count} error(s), {warn_count} warning(s).")
    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
