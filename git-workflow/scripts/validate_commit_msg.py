#!/usr/bin/env python3
"""Validate git commit messages against conventional commit format.

Format: type(scope): subject

Supported types: feat, fix, docs, style, refactor, test, chore, perf, ci, revert

Usage:
    echo "feat(auth): Add login" | python validate_commit_msg.py
    python validate_commit_msg.py --file .git/COMMIT_EDITMSG
    python validate_commit_msg.py --file - < message.txt
"""

import argparse
import re
import sys
from typing import List, Tuple

VALID_TYPES = {
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "test",
    "chore",
    "perf",
    "ci",
    "revert",
}

SUBJECT_MAX_LENGTH = 50
BODY_MAX_LENGTH = 72

# Pattern: type(scope): subject  OR  type: subject
HEADER_PATTERN = re.compile(
    r"^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?:\s+(?P<subject>.+)$"
)


def read_commit_message(file_path: str) -> str:
    """Read commit message from file path or stdin."""
    if file_path == "-" or file_path is None:
        return sys.stdin.read()
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def strip_comments(message: str) -> str:
    """Remove lines starting with # (git comment lines)."""
    lines = message.splitlines()
    stripped = [line for line in lines if not line.startswith("#")]
    # Remove trailing blank lines
    while stripped and stripped[-1].strip() == "":
        stripped.pop()
    return "\n".join(stripped)


def validate(message: str) -> List[Tuple[str, str]]:
    """Validate a commit message. Returns list of (severity, message) tuples."""
    errors: List[Tuple[str, str]] = []

    message = strip_comments(message)
    if not message.strip():
        errors.append(("ERROR", "Commit message is empty"))
        return errors

    lines = message.splitlines()
    header = lines[0]

    # --- Validate header format ---
    match = HEADER_PATTERN.match(header)
    if not match:
        errors.append(
            (
                "ERROR",
                f"Header does not match format 'type(scope): subject' or 'type: subject'\n"
                f"  Got: {header}",
            )
        )
        return errors  # Can't validate further without a valid header

    commit_type = match.group("type")
    subject = match.group("subject")

    # --- Validate type ---
    if commit_type not in VALID_TYPES:
        valid = ", ".join(sorted(VALID_TYPES))
        errors.append(
            (
                "ERROR",
                f"Invalid commit type '{commit_type}'. Must be one of: {valid}",
            )
        )

    # --- Validate subject length ---
    if len(header) > SUBJECT_MAX_LENGTH:
        errors.append(
            (
                "WARN",
                f"Subject line is {len(header)} chars (recommended max: {SUBJECT_MAX_LENGTH})\n"
                f"  {header}",
            )
        )

    # --- Validate no trailing period ---
    if subject.endswith("."):
        errors.append(("ERROR", "Subject must not end with a period"))

    # --- Validate imperative mood (heuristic: should not start with past tense) ---
    first_word = subject.split()[0] if subject.split() else ""
    past_tense_suffixes = ("ed",)
    gerund_suffixes = ("ing",)
    # Only flag obvious cases with common suffixes, allow short words
    if len(first_word) > 4:
        lower = first_word.lower()
        if any(lower.endswith(s) for s in past_tense_suffixes):
            errors.append(
                (
                    "WARN",
                    f"Subject may not use imperative mood (starts with '{first_word}'). "
                    f"Use imperative: 'Add' not 'Added'",
                )
            )
        if any(lower.endswith(s) for s in gerund_suffixes):
            errors.append(
                (
                    "WARN",
                    f"Subject may not use imperative mood (starts with '{first_word}'). "
                    f"Use imperative: 'Add' not 'Adding'",
                )
            )

    # --- Validate blank line after header ---
    if len(lines) > 1 and lines[1].strip() != "":
        errors.append(
            ("ERROR", "Second line must be blank (separates header from body)")
        )

    # --- Validate body line length ---
    body_lines = lines[2:] if len(lines) > 2 else []
    for i, line in enumerate(body_lines, start=3):
        if len(line) > BODY_MAX_LENGTH:
            errors.append(
                (
                    "WARN",
                    f"Body line {i} is {len(line)} chars (recommended max: {BODY_MAX_LENGTH})\n"
                    f"  {line}",
                )
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate git commit messages against conventional commit format.",
        epilog="Reads from stdin if --file is not provided.",
    )
    parser.add_argument(
        "--file",
        "-f",
        default=None,
        help="Path to commit message file (use '-' for stdin, default: stdin)",
    )
    args = parser.parse_args()

    try:
        message = read_commit_message(args.file)
    except FileNotFoundError:
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"ERROR: Could not read file: {e}", file=sys.stderr)
        return 1

    errors = validate(message)

    if not errors:
        print("OK: Commit message is valid.")
        return 0

    has_error = False
    for severity, msg in errors:
        prefix = severity
        if severity == "ERROR":
            has_error = True
        print(f"[{prefix}] {msg}")

    if has_error:
        print(f"\nFound {len(errors)} issue(s). Commit message is invalid.")
        return 1

    print(f"\nFound {len(errors)} warning(s). Commit message is acceptable but could be improved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
