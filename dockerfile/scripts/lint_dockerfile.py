#!/usr/bin/env python3
"""Lint Dockerfiles for common issues.

Checks for security, performance, and best practice violations
including missing USER instruction, latest tags, COPY . usage,
unnecessary ADD, missing HEALTHCHECK, and missing .dockerignore.

Usage:
    python lint_dockerfile.py
    python lint_dockerfile.py Dockerfile.prod
    python lint_dockerfile.py Dockerfile.dev Dockerfile.prod
"""

import argparse
import os
import re
import sys
from typing import List, Tuple

# Severity levels
ERROR = "ERROR"
WARN = "WARN"

Finding = Tuple[str, int, str, str]  # (file, line, severity, message)


def parse_dockerfile(filepath: str) -> List[Tuple[int, str, str]]:
    """Parse a Dockerfile into (line_number, instruction, arguments) tuples.

    Handles line continuations with backslash.
    """
    instructions = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        print(f"ERROR: Cannot read {filepath}: {e}", file=sys.stderr)
        return instructions

    current_line = ""
    current_line_num = 0

    for i, line in enumerate(lines, start=1):
        stripped = line.rstrip()

        # Skip comments and empty lines
        if not current_line and (stripped.lstrip().startswith("#") or stripped.strip() == ""):
            continue

        if not current_line:
            current_line_num = i

        # Handle line continuations
        if stripped.endswith("\\"):
            current_line += stripped[:-1] + " "
            continue

        current_line += stripped

        # Parse instruction
        parts = current_line.strip().split(None, 1)
        if parts:
            instruction = parts[0].upper()
            arguments = parts[1] if len(parts) > 1 else ""
            instructions.append((current_line_num, instruction, arguments))

        current_line = ""

    # Handle last line without newline
    if current_line.strip():
        parts = current_line.strip().split(None, 1)
        if parts:
            instruction = parts[0].upper()
            arguments = parts[1] if len(parts) > 1 else ""
            instructions.append((current_line_num, instruction, arguments))

    return instructions


def lint_file(filepath: str) -> List[Finding]:
    """Lint a single Dockerfile."""
    findings: List[Finding] = []
    instructions = parse_dockerfile(filepath)

    if not instructions:
        findings.append((filepath, 0, ERROR, "Dockerfile is empty or could not be parsed"))
        return findings

    has_user = False
    has_healthcheck = False
    last_from_line = 0
    is_multistage = False
    from_count = 0

    for line_num, instruction, arguments in instructions:
        # Track FROM instructions
        if instruction == "FROM":
            from_count += 1
            last_from_line = line_num
            if from_count > 1:
                is_multistage = True

            # Check for :latest tag or no tag
            image = arguments.split()[0] if arguments else ""
            # Remove --platform=... prefix
            if image.startswith("--"):
                parts = arguments.split()
                image = parts[1] if len(parts) > 1 else ""

            # Ignore scratch and AS aliases
            base_image = image.split(" ")[0].strip()
            if base_image and base_image != "scratch":
                if ":" not in base_image and "@" not in base_image:
                    findings.append(
                        (filepath, line_num, WARN,
                         f"FROM {base_image} has no tag specified (defaults to :latest). "
                         f"Pin to a specific version.")
                    )
                elif base_image.endswith(":latest"):
                    findings.append(
                        (filepath, line_num, ERROR,
                         f"FROM uses ':latest' tag: {base_image}. "
                         f"Pin to a specific version for reproducible builds.")
                    )

        # Track USER instruction
        if instruction == "USER":
            has_user = True

        # Track HEALTHCHECK
        if instruction == "HEALTHCHECK":
            has_healthcheck = True

        # Check ADD vs COPY
        if instruction == "ADD":
            # ADD is acceptable for URLs and tar extraction
            arg_lower = arguments.lower().strip()
            if not (
                arg_lower.startswith("http://")
                or arg_lower.startswith("https://")
                or ".tar" in arg_lower
                or ".gz" in arg_lower
                or ".bz2" in arg_lower
                or ".xz" in arg_lower
            ):
                findings.append(
                    (filepath, line_num, WARN,
                     f"Use COPY instead of ADD unless you need URL fetch or tar extraction.\n"
                     f"  ADD {arguments}")
                )

        # Check COPY . . (copies everything)
        if instruction == "COPY":
            # Detect: COPY . .  or  COPY . /app  etc.
            copy_args = arguments.strip()
            # Remove --from=... --chown=... flags
            cleaned = re.sub(r"--\w+=[^\s]+\s*", "", copy_args).strip()
            parts = cleaned.split()
            if parts and parts[0] == ".":
                findings.append(
                    (filepath, line_num, WARN,
                     f"COPY . copies the entire build context. "
                     f"This invalidates Docker layer cache on any file change.\n"
                     f"  Consider copying specific files for better cache efficiency.")
                )

        # Check for RUN with apt-get without cleanup
        if instruction == "RUN":
            if "apt-get install" in arguments and "rm -rf /var/lib/apt" not in arguments:
                if "&&" not in arguments or "rm " not in arguments:
                    findings.append(
                        (filepath, line_num, WARN,
                         "apt-get install without cleanup in the same layer. "
                         "Add '&& rm -rf /var/lib/apt/lists/*' to reduce image size.")
                    )

    # Check for missing USER instruction (only for the final stage)
    if not has_user:
        findings.append(
            (filepath, 0, WARN,
             "No USER instruction found. Container will run as root.\n"
             "  Add a non-root user: RUN addgroup -S app && adduser -S app -G app\n"
             "  Then: USER app")
        )

    # Check for missing HEALTHCHECK
    if not has_healthcheck:
        findings.append(
            (filepath, 0, WARN,
             "No HEALTHCHECK instruction found. "
             "Consider adding a HEALTHCHECK for container orchestration.")
        )

    # Check for .dockerignore
    dockerfile_dir = os.path.dirname(os.path.abspath(filepath))
    dockerignore_path = os.path.join(dockerfile_dir, ".dockerignore")
    if not os.path.isfile(dockerignore_path):
        findings.append(
            (filepath, 0, WARN,
             f"No .dockerignore file found in {dockerfile_dir}.\n"
             f"  Create one to exclude .git, node_modules, build artifacts, etc.")
        )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lint Dockerfiles for common issues.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        default=["Dockerfile"],
        help="Dockerfile path(s) to lint (default: ./Dockerfile)",
    )
    args = parser.parse_args()

    total_findings: List[Finding] = []
    files_checked = 0

    for filepath in args.files:
        if not os.path.isfile(filepath):
            print(f"ERROR: File not found: {filepath}", file=sys.stderr)
            total_findings.append((filepath, 0, ERROR, f"File not found: {filepath}"))
            continue

        files_checked += 1
        findings = lint_file(filepath)
        total_findings.extend(findings)

    if files_checked == 0:
        print("ERROR: No Dockerfile(s) found to lint.", file=sys.stderr)
        return 1

    if not total_findings:
        print(f"OK: No issues found in {files_checked} Dockerfile(s).")
        return 0

    # Group findings by file
    findings_by_file: dict = {}
    for filepath, line_num, severity, message in total_findings:
        findings_by_file.setdefault(filepath, []).append((line_num, severity, message))

    error_count = 0
    warn_count = 0

    for filepath, findings in findings_by_file.items():
        print(f"\n  {filepath}:")
        for line_num, severity, message in findings:
            if severity == ERROR:
                error_count += 1
            else:
                warn_count += 1
            location = f"line {line_num}" if line_num > 0 else "general"
            # Indent multiline messages
            indented = message.replace("\n", "\n      ")
            print(f"    [{severity}] {location}: {indented}")

    print(f"\nTotal: {error_count} error(s), {warn_count} warning(s) in {files_checked} file(s).")

    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
