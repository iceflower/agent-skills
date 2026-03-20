#!/usr/bin/env python3
"""Scan logging statements for sensitive data exposure.

Detects:
- Passwords and credentials in log messages
- API keys and tokens being logged
- Personal identifiable information (PII) patterns
- Credit card numbers in logs
- Email addresses in log output
- IP addresses being logged (configurable)

Usage:
    python scan_sensitive_data.py src/
    python scan_sensitive_data.py --recursive --severity ERROR app/
    python scan_sensitive_data.py --include-ip-check src/main.py
"""

import argparse
import os
import re
import sys
from typing import Dict, List, Set, Tuple

Finding = Tuple[str, int, str, str, str]  # (file, line, severity, category, message)

ERROR = "ERROR"
WARN = "WARN"

# File extensions to scan
SCANNABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".kt",
    ".go", ".rb", ".php", ".cs", ".scala",
}

# Logging function patterns by language
LOG_PATTERNS = re.compile(
    r"""(?:
        # Python
        logging\.(?:debug|info|warning|error|critical|exception)\s*\(
        |logger\.(?:debug|info|warning|error|critical|exception|log)\s*\(
        |log\.(?:debug|info|warning|error|critical|exception)\s*\(
        |print\s*\(
        # Java/Kotlin
        |log\.(?:trace|debug|info|warn|error)\s*\(
        |logger\.(?:trace|debug|info|warn|error)\s*\(
        |LOG\.(?:trace|debug|info|warn|error)\s*\(
        |System\.out\.print(?:ln)?\s*\(
        |System\.err\.print(?:ln)?\s*\(
        # JavaScript/TypeScript
        |console\.(?:log|debug|info|warn|error|trace)\s*\(
        # Go
        |log\.(?:Print|Fatal|Panic)(?:f|ln)?\s*\(
        |slog\.(?:Debug|Info|Warn|Error)\s*\(
        |zap\.\w+\(\)\.(?:Debug|Info|Warn|Error)\s*\(
        |logrus\.(?:Debug|Info|Warn|Error|Fatal|Panic)(?:f|ln)?\s*\(
    )""",
    re.VERBOSE | re.IGNORECASE,
)


class SensitivePattern:
    """Defines a sensitive data detection pattern."""

    def __init__(
        self,
        name: str,
        category: str,
        severity: str,
        pattern: str,
        message: str,
    ):
        self.name = name
        self.category = category
        self.severity = severity
        self.regex = re.compile(pattern, re.IGNORECASE)
        self.message = message


# Patterns that indicate sensitive data in log statements
SENSITIVE_PATTERNS: List[SensitivePattern] = [
    # Credentials
    SensitivePattern(
        "log-password",
        "Credentials",
        ERROR,
        r"""(?:password|passwd|pwd|secret|credential)[\s]*[=:,]""",
        "Password or credential value in log statement.\n"
        "  Never log credentials. Log the event without the value.",
    ),
    SensitivePattern(
        "log-token",
        "Credentials",
        ERROR,
        r"""(?:token|api[_-]?key|apikey|access[_-]?key|secret[_-]?key|auth[_-]?key)[\s]*[=:,]""",
        "Token or API key in log statement.\n"
        "  Mask or omit sensitive tokens from logs.",
    ),
    SensitivePattern(
        "log-bearer",
        "Credentials",
        ERROR,
        r"""(?:bearer\s+[A-Za-z0-9._~+/=-]+|authorization[\s]*[=:])""",
        "Authorization header or bearer token in log.\n"
        "  Never log authentication headers.",
    ),
    SensitivePattern(
        "log-connection-string",
        "Credentials",
        ERROR,
        r"""(?:connection[_-]?string|database[_-]?url|db[_-]?url|jdbc:|mongodb://|postgres://|mysql://)""",
        "Database connection string in log.\n"
        "  Connection strings often contain credentials. Log only the host/database name.",
    ),
    # PII
    SensitivePattern(
        "log-ssn",
        "PII",
        ERROR,
        r"""\b\d{3}[-]?\d{2}[-]?\d{4}\b""",
        "Possible SSN pattern in log statement.\n"
        "  Never log Social Security Numbers or national ID numbers.",
    ),
    SensitivePattern(
        "log-credit-card",
        "PII",
        ERROR,
        r"""\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6(?:011|5\d{2}))\s?[-]?\s?\d{4}\s?[-]?\s?\d{4}\s?[-]?\s?\d{4}\b""",
        "Possible credit card number in log statement.\n"
        "  Never log full credit card numbers. Use masking: **** **** **** 1234",
    ),
    SensitivePattern(
        "log-email-data",
        "PII",
        WARN,
        r"""(?:email|e-mail|mail)\s*[=:]\s*[^\s,)]+@[^\s,)]+""",
        "Email address being logged with identifying context.\n"
        "  Consider masking: u***@example.com",
    ),
    # Sensitive request/response data
    SensitivePattern(
        "log-request-body",
        "Data Exposure",
        WARN,
        r"""(?:request\.body|req\.body|request\.json|request\.form|request\.data)""",
        "Logging full request body may expose sensitive user data.\n"
        "  Log only non-sensitive fields or use a sanitization function.",
    ),
    SensitivePattern(
        "log-response-full",
        "Data Exposure",
        WARN,
        r"""(?:response\.(?:body|text|content|data|json))""",
        "Logging full response body may expose sensitive data.\n"
        "  Log only status codes and non-sensitive metadata.",
    ),
    SensitivePattern(
        "log-headers",
        "Data Exposure",
        WARN,
        r"""(?:request\.headers|req\.headers|response\.headers)""",
        "Logging full headers may expose authorization tokens and cookies.\n"
        "  Log only specific non-sensitive headers.",
    ),
    SensitivePattern(
        "log-cookie",
        "Data Exposure",
        ERROR,
        r"""(?:cookie|set-cookie|session[_-]?id)\s*[=:]""",
        "Cookie or session ID in log statement.\n"
        "  Never log session identifiers or cookie values.",
    ),
    # Private keys
    SensitivePattern(
        "log-private-key",
        "Credentials",
        ERROR,
        r"""(?:private[_-]?key|-----BEGIN)""",
        "Private key material in log statement.\n"
        "  Never log private keys or key material.",
    ),
]

# Optional IP address pattern (can produce noise)
IP_PATTERN = SensitivePattern(
    "log-ip-address",
    "PII",
    WARN,
    r"""\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b""",
    "IP address in log statement.\n"
    "  Consider whether logging IP addresses complies with privacy regulations (GDPR).",
)


def scan_file(
    filepath: str, include_ip: bool
) -> List[Finding]:
    """Scan a single file for sensitive data in log statements."""
    findings: List[Finding] = []

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return findings

    patterns = list(SENSITIVE_PATTERNS)
    if include_ip:
        patterns.append(IP_PATTERN)

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip comments
        if stripped.startswith(("#", "//", "*", "/*")):
            continue

        # Only check lines that contain logging statements
        if not LOG_PATTERNS.search(line):
            continue

        for pattern in patterns:
            if pattern.regex.search(line):
                findings.append((
                    filepath, i, pattern.severity, pattern.category,
                    f"{pattern.message}\n  Pattern: {pattern.name}",
                ))

    return findings


def find_source_files(
    path: str, recursive: bool, exclude_dirs: Set[str]
) -> List[str]:
    """Find source files to scan."""
    if os.path.isfile(path):
        return [path]

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
                _, ext = os.path.splitext(filename)
                if ext in SCANNABLE_EXTENSIONS:
                    files.append(os.path.join(dirpath, filename))
    else:
        for filename in os.listdir(path):
            _, ext = os.path.splitext(filename)
            if ext in SCANNABLE_EXTENSIONS:
                full_path = os.path.join(path, filename)
                if os.path.isfile(full_path):
                    files.append(full_path)

    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan logging statements for sensitive data exposure.",
        epilog="Exit code 0 = clean, 1 = issues found.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="File or directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        default=True,
        help="Recursively scan directories (default: true)",
    )
    parser.add_argument(
        "--severity",
        choices=["WARN", "ERROR"],
        default="WARN",
        help="Minimum severity to report (default: WARN)",
    )
    parser.add_argument(
        "--include-ip-check",
        action="store_true",
        help="Include IP address detection (may produce noise)",
    )
    parser.add_argument(
        "--exclude",
        default="venv,node_modules,__pycache__,.git,dist,build,vendor,test,tests",
        help="Comma-separated directory names to exclude",
    )
    args = parser.parse_args()

    path = os.path.abspath(args.path)
    if not os.path.exists(path):
        print(f"Error: Path not found: {path}", file=sys.stderr)
        return 1

    exclude_dirs = set(args.exclude.split(","))
    files = find_source_files(path, args.recursive, exclude_dirs)

    if not files:
        print(f"No source files found at {path}")
        return 0

    severity_order = {"WARN": 0, "ERROR": 1}
    min_level = severity_order.get(args.severity, 0)

    all_findings: List[Finding] = []
    for filepath in files:
        findings = scan_file(filepath, args.include_ip_check)
        filtered = [f for f in findings if severity_order.get(f[2], 0) >= min_level]
        all_findings.extend(filtered)

    if not all_findings:
        print(f"OK: No sensitive data patterns found in {len(files)} file(s).")
        return 0

    error_count = sum(1 for f in all_findings if f[2] == ERROR)
    warn_count = sum(1 for f in all_findings if f[2] == WARN)

    by_category: Dict[str, List[Finding]] = {}
    for finding in all_findings:
        by_category.setdefault(finding[3], []).append(finding)

    for category, findings in sorted(by_category.items()):
        print(f"\n  [{category}]")
        for filepath, line_num, severity, _, message in findings:
            rel_path = os.path.relpath(filepath, path if os.path.isdir(path) else os.path.dirname(path))
            indented = message.replace("\n", "\n      ")
            print(f"    [{severity}] {rel_path}:{line_num}: {indented}")

    print(f"\nScanned {len(files)} file(s): {error_count} error(s), {warn_count} warning(s).")
    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
