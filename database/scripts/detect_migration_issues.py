#!/usr/bin/env python3
"""Scan SQL migration files for risky operations.

Detects potentially dangerous SQL operations in migration files and
reports them with severity levels:
  HIGH   - DROP TABLE, TRUNCATE
  MEDIUM - DROP COLUMN, RENAME, ALTER TYPE
  LOW    - ADD INDEX without CONCURRENTLY
"""

import argparse
import os
import re
import sys
from typing import List, NamedTuple


class Finding(NamedTuple):
    file: str
    line: int
    severity: str
    description: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.file}:{self.line}: {self.description}"


# Patterns: (compiled_regex, severity, description_template)
# Description template may use group references via a callable.
PATTERNS = [
    # HIGH severity
    (
        re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
        "HIGH",
        "DROP TABLE detected - causes irreversible data loss",
    ),
    (
        re.compile(r"\bTRUNCATE\b", re.IGNORECASE),
        "HIGH",
        "TRUNCATE detected - removes all rows without logging individual deletions",
    ),
    (
        re.compile(r"\bDROP\s+DATABASE\b", re.IGNORECASE),
        "HIGH",
        "DROP DATABASE detected - destroys entire database",
    ),
    (
        re.compile(r"\bDROP\s+SCHEMA\b", re.IGNORECASE),
        "HIGH",
        "DROP SCHEMA detected - destroys entire schema and its objects",
    ),
    # MEDIUM severity
    (
        re.compile(r"\bDROP\s+COLUMN\b", re.IGNORECASE),
        "MEDIUM",
        "DROP COLUMN detected - may cause data loss and break dependent code",
    ),
    (
        re.compile(
            r"\bALTER\s+TABLE\s+\S+\s+DROP\s+(?:COLUMN\s+)?(\S+)",
            re.IGNORECASE,
        ),
        "MEDIUM",
        "ALTER TABLE ... DROP detected - column removal may break queries",
    ),
    (
        re.compile(r"\bRENAME\s+TABLE\b", re.IGNORECASE),
        "MEDIUM",
        "RENAME TABLE detected - may break application queries and ORM mappings",
    ),
    (
        re.compile(r"\bRENAME\s+COLUMN\b", re.IGNORECASE),
        "MEDIUM",
        "RENAME COLUMN detected - may break application queries and ORM mappings",
    ),
    (
        re.compile(
            r"\bALTER\s+TABLE\s+\S+\s+RENAME\b",
            re.IGNORECASE,
        ),
        "MEDIUM",
        "ALTER TABLE ... RENAME detected - may break dependent code",
    ),
    (
        re.compile(
            r"\bALTER\s+(?:TABLE\s+\S+\s+ALTER\s+(?:COLUMN\s+)?\S+\s+)?(?:SET\s+DATA\s+)?TYPE\b",
            re.IGNORECASE,
        ),
        "MEDIUM",
        "ALTER TYPE / SET DATA TYPE detected - may cause data truncation or conversion errors",
    ),
    (
        re.compile(
            r"\bALTER\s+TABLE\s+\S+\s+ALTER\s+(?:COLUMN\s+)?\S+\s+SET\s+NOT\s+NULL\b",
            re.IGNORECASE,
        ),
        "MEDIUM",
        "SET NOT NULL detected - will fail if existing rows contain NULL values",
    ),
]

# Special pattern: CREATE INDEX without CONCURRENTLY
INDEX_PATTERN = re.compile(
    r"\bCREATE\s+(?:UNIQUE\s+)?INDEX\b",
    re.IGNORECASE,
)
CONCURRENTLY_PATTERN = re.compile(r"\bCONCURRENTLY\b", re.IGNORECASE)


def scan_file(file_path: str) -> List[Finding]:
    """Scan a single SQL file for risky operations."""
    findings: List[Finding] = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        print(f"Warning: Cannot read {file_path}: {e}", file=sys.stderr)
        return findings

    in_block_comment = False

    for line_num, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        # Handle block comments
        if in_block_comment:
            if "*/" in line:
                in_block_comment = False
                line = line[line.index("*/") + 2:]
            else:
                continue

        if "/*" in line:
            # Check if block comment is on a single line
            before_comment = line[:line.index("/*")]
            after_start = line[line.index("/*") + 2:]
            if "*/" in after_start:
                line = before_comment + after_start[after_start.index("*/") + 2:]
            else:
                in_block_comment = True
                line = before_comment

        # Skip single-line comments
        if line.startswith("--"):
            continue
        # Remove inline comments
        if "--" in line:
            line = line[:line.index("--")]

        if not line.strip():
            continue

        # Check standard patterns
        matched_descriptions = set()
        for pattern, severity, description in PATTERNS:
            if pattern.search(line):
                if description not in matched_descriptions:
                    matched_descriptions.add(description)
                    findings.append(Finding(file_path, line_num, severity, description))

        # Special check: CREATE INDEX without CONCURRENTLY
        if INDEX_PATTERN.search(line) and not CONCURRENTLY_PATTERN.search(line):
            findings.append(Finding(
                file_path,
                line_num,
                "LOW",
                "CREATE INDEX without CONCURRENTLY - locks table for writes during index creation (PostgreSQL)",
            ))

    return findings


def scan_directory(directory: str, recursive: bool = True) -> List[Finding]:
    """Scan a directory for SQL migration files."""
    findings: List[Finding] = []
    sql_files: List[str] = []

    if recursive:
        for root, _dirs, files in os.walk(directory):
            for fname in sorted(files):
                if fname.lower().endswith(".sql"):
                    sql_files.append(os.path.join(root, fname))
    else:
        for fname in sorted(os.listdir(directory)):
            full_path = os.path.join(directory, fname)
            if os.path.isfile(full_path) and fname.lower().endswith(".sql"):
                sql_files.append(full_path)

    if not sql_files:
        print(f"No .sql files found in {directory}", file=sys.stderr)
        return findings

    for sql_file in sql_files:
        findings.extend(scan_file(sql_file))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan SQL migration files for risky operations.",
        epilog="Exit code 0 = no issues, 1 = findings detected.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to scan for *.sql files, or a single .sql file (default: current directory)",
    )
    parser.add_argument(
        "--severity",
        choices=["LOW", "MEDIUM", "HIGH"],
        default="LOW",
        help="Minimum severity to report (default: LOW)",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not scan subdirectories",
    )

    args = parser.parse_args()

    severity_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    min_level = severity_order[args.severity]

    if os.path.isfile(args.path):
        if not args.path.lower().endswith(".sql"):
            print(f"Warning: {args.path} does not have .sql extension", file=sys.stderr)
        findings = scan_file(args.path)
    elif os.path.isdir(args.path):
        findings = scan_directory(args.path, recursive=not args.no_recursive)
    else:
        print(f"Error: Path not found: {args.path}", file=sys.stderr)
        return 1

    filtered = [f for f in findings if severity_order.get(f.severity, 0) >= min_level]

    if not filtered:
        print(f"OK: No risky operations detected (min severity: {args.severity})")
        return 0

    # Sort by severity (highest first), then by file and line
    filtered.sort(key=lambda f: (-severity_order.get(f.severity, 0), f.file, f.line))

    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for finding in filtered:
        print(finding)
        counts[finding.severity] = counts.get(finding.severity, 0) + 1

    print(f"\nSummary: {counts['HIGH']} HIGH, {counts['MEDIUM']} MEDIUM, {counts['LOW']} LOW")
    return 1


if __name__ == "__main__":
    sys.exit(main())
