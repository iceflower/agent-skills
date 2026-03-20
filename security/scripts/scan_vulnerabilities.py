#!/usr/bin/env python3
"""Scan source code for common security vulnerability patterns.

Detects:
- SQL injection patterns (string concatenation in queries)
- XSS vulnerabilities (unescaped output)
- Command injection (shell=True, os.system, subprocess with shell)
- Hardcoded secrets and credentials
- Insecure cryptographic practices
- Path traversal risks
- Insecure deserialization

Usage:
    python scan_vulnerabilities.py src/
    python scan_vulnerabilities.py --severity ERROR app.py
    python scan_vulnerabilities.py --recursive --exclude venv,node_modules src/
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
    ".go", ".rb", ".php", ".cs", ".rs", ".scala",
}

# ── Pattern Definitions ──────────────────────────────────────────────────


class VulnPattern:
    """Defines a vulnerability detection pattern."""

    def __init__(
        self,
        name: str,
        category: str,
        severity: str,
        pattern: str,
        message: str,
        languages: Set[str] | None = None,
    ):
        self.name = name
        self.category = category
        self.severity = severity
        self.regex = re.compile(pattern, re.IGNORECASE)
        self.message = message
        self.languages = languages  # None means all languages


PATTERNS: List[VulnPattern] = [
    # SQL Injection
    VulnPattern(
        "sql-string-concat",
        "SQL Injection",
        ERROR,
        r"""(?:execute|query|cursor\.execute|raw|rawQuery)\s*\(\s*(?:f[\"']|[\"'].*?\s*[+%]|.*?\.format\()""",
        "Possible SQL injection via string concatenation/formatting.\n"
        "  Use parameterized queries instead: cursor.execute('SELECT * FROM t WHERE id = %s', (id,))",
    ),
    VulnPattern(
        "sql-fstring",
        "SQL Injection",
        ERROR,
        r"""(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER)\s+.*\{.*\}""",
        "SQL statement with embedded expression. Use parameterized queries.",
    ),
    # XSS
    VulnPattern(
        "xss-innerhtml",
        "XSS",
        ERROR,
        r"""\.innerHTML\s*=\s*(?!['"]<\w)""",
        "Direct innerHTML assignment. Use textContent or sanitize HTML input.\n"
        "  Consider: element.textContent = value or DOMPurify.sanitize(value)",
        {".js", ".ts", ".jsx", ".tsx"},
    ),
    VulnPattern(
        "xss-dangerously-set",
        "XSS",
        WARN,
        r"dangerouslySetInnerHTML",
        "Usage of dangerouslySetInnerHTML. Ensure input is sanitized.",
        {".js", ".ts", ".jsx", ".tsx"},
    ),
    VulnPattern(
        "xss-document-write",
        "XSS",
        WARN,
        r"document\.write\s*\(",
        "document.write() can introduce XSS. Prefer DOM manipulation methods.",
        {".js", ".ts", ".jsx", ".tsx"},
    ),
    # Command Injection
    VulnPattern(
        "cmd-os-system",
        "Command Injection",
        ERROR,
        r"os\.system\s*\(",
        "os.system() is vulnerable to command injection.\n"
        "  Use subprocess.run() with a list of arguments and shell=False.",
        {".py"},
    ),
    VulnPattern(
        "cmd-shell-true",
        "Command Injection",
        ERROR,
        r"subprocess\.(?:call|run|Popen|check_output|check_call)\s*\(.*shell\s*=\s*True",
        "subprocess with shell=True is vulnerable to command injection.\n"
        "  Pass command as a list with shell=False.",
        {".py"},
    ),
    VulnPattern(
        "cmd-eval",
        "Command Injection",
        ERROR,
        r"\beval\s*\(\s*(?!json)",
        "eval() executes arbitrary code. Avoid using eval with untrusted input.",
    ),
    VulnPattern(
        "cmd-exec",
        "Command Injection",
        WARN,
        r"Runtime\.getRuntime\(\)\.exec\s*\(",
        "Runtime.exec() can be vulnerable to command injection.\n"
        "  Validate and sanitize all input parameters.",
        {".java", ".kt"},
    ),
    # Hardcoded Secrets
    VulnPattern(
        "secret-password",
        "Hardcoded Secrets",
        ERROR,
        r"""(?:password|passwd|pwd)\s*[=:]\s*[\"'][^\"']{4,}[\"']""",
        "Possible hardcoded password. Use environment variables or a secret manager.",
    ),
    VulnPattern(
        "secret-api-key",
        "Hardcoded Secrets",
        ERROR,
        r"""(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?token)\s*[=:]\s*[\"'][A-Za-z0-9+/=_-]{8,}[\"']""",
        "Possible hardcoded API key or token. Use environment variables or a secret manager.",
    ),
    VulnPattern(
        "secret-private-key",
        "Hardcoded Secrets",
        ERROR,
        r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----",
        "Embedded private key detected. Store keys in secure key management.",
    ),
    # Insecure Crypto
    VulnPattern(
        "crypto-md5",
        "Insecure Crypto",
        WARN,
        r"""(?:hashlib\.md5|MD5\.Create|MessageDigest\.getInstance\s*\(\s*[\"']MD5)""",
        "MD5 is cryptographically broken. Use SHA-256 or stronger for security purposes.",
    ),
    VulnPattern(
        "crypto-sha1",
        "Insecure Crypto",
        WARN,
        r"""(?:hashlib\.sha1|SHA1\.Create|MessageDigest\.getInstance\s*\(\s*[\"']SHA-?1)""",
        "SHA-1 is considered weak. Use SHA-256 or stronger for security purposes.",
    ),
    VulnPattern(
        "crypto-des",
        "Insecure Crypto",
        ERROR,
        r"""(?:DES\.new|Cipher\.getInstance\s*\(\s*[\"']DES)""",
        "DES encryption is insecure. Use AES-256 or ChaCha20.",
    ),
    # Path Traversal
    VulnPattern(
        "path-traversal",
        "Path Traversal",
        WARN,
        r"""(?:open|readFile|readFileSync|createReadStream)\s*\(.*(?:req\.|request\.|params\.|query\.)""",
        "File operation with user-controlled path. Validate and sanitize the path.\n"
        "  Use os.path.realpath() and verify it stays within the allowed directory.",
    ),
    # Insecure Deserialization
    VulnPattern(
        "deserialize-pickle",
        "Insecure Deserialization",
        ERROR,
        r"pickle\.loads?\s*\(",
        "pickle.loads() can execute arbitrary code. Use json or a safe serialization format.\n"
        "  If pickle is required, only deserialize data from trusted sources.",
        {".py"},
    ),
    VulnPattern(
        "deserialize-yaml-load",
        "Insecure Deserialization",
        WARN,
        r"yaml\.load\s*\([^)]*\)\s*(?!.*Loader)",
        "yaml.load() without SafeLoader can execute arbitrary code.\n"
        "  Use yaml.safe_load() instead.",
        {".py"},
    ),
    # SSRF
    VulnPattern(
        "ssrf-request",
        "SSRF",
        WARN,
        r"""(?:requests\.get|requests\.post|urllib\.request\.urlopen|fetch)\s*\(.*(?:req\.|request\.|params\.|query\.|user)""",
        "HTTP request with user-controlled URL. Validate against an allowlist.\n"
        "  Block internal/private IP ranges and restrict allowed protocols.",
    ),
]


def scan_file(filepath: str, ext: str) -> List[Finding]:
    """Scan a single file for vulnerability patterns."""
    findings: List[Finding] = []

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return findings

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip comments (basic heuristic)
        if stripped.startswith(("#", "//", "*", "/*")):
            continue

        for pattern in PATTERNS:
            if pattern.languages and ext not in pattern.languages:
                continue

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
        description="Scan source code for common security vulnerability patterns.",
        epilog="Exit code 0 = clean, 1 = vulnerabilities found.",
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
    files = find_source_files(path, args.recursive, exclude_dirs)

    if not files:
        print(f"No source files found at {path}")
        return 0

    severity_order = {"WARN": 0, "ERROR": 1}
    min_level = severity_order.get(args.severity, 0)

    all_findings: List[Finding] = []
    for filepath in files:
        _, ext = os.path.splitext(filepath)
        findings = scan_file(filepath, ext)
        filtered = [f for f in findings if severity_order.get(f[2], 0) >= min_level]
        all_findings.extend(filtered)

    if not all_findings:
        print(f"OK: No vulnerabilities found in {len(files)} file(s).")
        return 0

    error_count = sum(1 for f in all_findings if f[2] == ERROR)
    warn_count = sum(1 for f in all_findings if f[2] == WARN)

    # Group by category then file
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
