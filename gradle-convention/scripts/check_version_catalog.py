#!/usr/bin/env python3
"""Scan build.gradle.kts files for hardcoded dependency versions.

Detects inline version strings that should be defined in
gradle/libs.versions.toml (Gradle version catalog).

Usage:
    python check_version_catalog.py
    python check_version_catalog.py /path/to/project
    python check_version_catalog.py --exclude buildSrc
"""

import argparse
import os
import re
import sys
from typing import List, Tuple

# Match patterns like:
#   implementation("group:artifact:1.2.3")
#   api("group:artifact:1.2.3-beta")
#   testImplementation("group:artifact:1.2.3.Final")
#   runtimeOnly("group:artifact:1.2.3")
# But NOT:
#   implementation("group:artifact:${version}")
#   implementation(libs.some.library)
DEPENDENCY_WITH_VERSION = re.compile(
    r"""(?:implementation|api|compileOnly|runtimeOnly|testImplementation|testRuntimeOnly|testCompileOnly|classpath|annotationProcessor|kapt|ksp)"""
    r"""\(\s*"([^"$]+?):([^"$]+?):([^"$]+?)"\s*\)""",
    re.MULTILINE,
)

# Match patterns with single quotes (less common but valid in Groovy-style)
DEPENDENCY_WITH_VERSION_SINGLE = re.compile(
    r"""(?:implementation|api|compileOnly|runtimeOnly|testImplementation|testRuntimeOnly|testCompileOnly|classpath|annotationProcessor|kapt|ksp)"""
    r"""\(\s*'([^'$]+?):([^'$]+?):([^'$]+?)'\s*\)""",
    re.MULTILINE,
)

# Match version assignments like: version = "1.2.3"
VERSION_ASSIGNMENT = re.compile(
    r'version\s*=\s*"(\d+\.\d+[^"]*?)"',
    re.MULTILINE,
)

# Detect string interpolation
HAS_INTERPOLATION = re.compile(r"\$\{|\$\w")


def is_comment_line(line: str) -> bool:
    """Check if a line is a comment."""
    stripped = line.strip()
    return stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*")


def find_gradle_files(root: str, exclude_dirs: List[str]) -> List[str]:
    """Find all build.gradle.kts and build.gradle files."""
    gradle_files = []
    exclude_set = set(exclude_dirs)

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out excluded directories
        dirnames[:] = [
            d
            for d in dirnames
            if d not in exclude_set and not d.startswith(".")
        ]

        for filename in filenames:
            if filename in ("build.gradle.kts", "build.gradle"):
                gradle_files.append(os.path.join(dirpath, filename))

    return sorted(gradle_files)


def check_file(filepath: str) -> List[Tuple[str, int, str, str, str, str]]:
    """Check a single gradle file for hardcoded versions.

    Returns list of (file, line_number, group, artifact, version, full_line).
    """
    findings = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return findings

    lines = content.splitlines()

    in_block_comment = False
    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Track block comments
        if "/*" in stripped:
            in_block_comment = True
        if "*/" in stripped:
            in_block_comment = False
            continue
        if in_block_comment:
            continue

        # Skip single-line comments
        if is_comment_line(line):
            continue

        # Skip lines with string interpolation
        if HAS_INTERPOLATION.search(line):
            continue

        # Check for hardcoded dependency versions
        for pattern in (DEPENDENCY_WITH_VERSION, DEPENDENCY_WITH_VERSION_SINGLE):
            for match in pattern.finditer(line):
                group = match.group(1)
                artifact = match.group(2)
                version = match.group(3)

                # Skip if version looks like a variable reference
                if version.startswith("$") or version.startswith("{"):
                    continue

                findings.append(
                    (filepath, line_num, group, artifact, version, stripped)
                )

    return findings


def check_version_catalog_exists(root: str) -> bool:
    """Check if gradle/libs.versions.toml exists."""
    catalog_path = os.path.join(root, "gradle", "libs.versions.toml")
    return os.path.isfile(catalog_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan build.gradle.kts files for hardcoded dependency versions.",
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=["buildSrc", ".gradle", "build"],
        help="Directories to exclude (default: buildSrc .gradle build)",
    )
    args = parser.parse_args()

    root = os.path.abspath(args.root)

    if not os.path.isdir(root):
        print(f"ERROR: Directory not found: {root}", file=sys.stderr)
        return 1

    # Check for version catalog
    has_catalog = check_version_catalog_exists(root)
    if not has_catalog:
        print(f"[WARN] No gradle/libs.versions.toml found in {root}")
        print("  Consider using a Gradle version catalog for dependency management.\n")

    # Find and check gradle files
    gradle_files = find_gradle_files(root, args.exclude)

    if not gradle_files:
        print(f"No build.gradle.kts or build.gradle files found in {root}")
        return 0

    all_findings = []
    for filepath in gradle_files:
        findings = check_file(filepath)
        all_findings.extend(findings)

    if not all_findings:
        print(f"OK: No hardcoded dependency versions found in {len(gradle_files)} gradle file(s).")
        return 0

    # Report findings
    print(f"Found {len(all_findings)} hardcoded dependency version(s):\n")

    current_file = None
    for filepath, line_num, group, artifact, version, full_line in all_findings:
        rel_path = os.path.relpath(filepath, root)
        if rel_path != current_file:
            current_file = rel_path
            print(f"  {rel_path}:")

        print(f"    line {line_num}: {group}:{artifact}:{version}")
        print(f"      {full_line}")

    print(f"\nMove these versions to gradle/libs.versions.toml for centralized management.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
