#!/usr/bin/env python3
"""Lint SKILL.md frontmatter for required fields.

Validates that every SKILL.md file in the given directory tree contains
all mandatory frontmatter fields defined by the Agent Skills standard.

Usage:
    python scripts/lint_frontmatter.py <skills-root-directory>

Exit codes:
    0 - All SKILL.md files pass validation.
    1 - One or more SKILL.md files have missing or invalid fields.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REQUIRED_TOP_LEVEL = {"name", "description", "license", "metadata", "compatibility"}
REQUIRED_METADATA = {"author", "version", "last-reviewed"}
REQUIRED_COMPATIBILITY = {"OpenCode", "Claude Code", "Codex", "Antigravity"}


def parse_frontmatter(path: Path) -> dict | None:
    """Extract YAML frontmatter from a Markdown file.

    Returns the parsed dict, or None if no valid frontmatter block is found.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None

    end = text.find("---", 3)
    if end == -1:
        return None

    raw = text[3:end]
    try:
        return yaml.safe_load(raw)
    except yaml.YAMLError:
        return None


def validate(path: Path) -> list[str]:
    """Return a list of error messages for a single SKILL.md file."""
    errors: list[str] = []

    fm = parse_frontmatter(path)
    if fm is None:
        errors.append("YAML frontmatter block not found or unparseable")
        return errors

    # Top-level required fields
    missing_top = REQUIRED_TOP_LEVEL - set(fm.keys())
    if missing_top:
        errors.append(f"missing top-level fields: {', '.join(sorted(missing_top))}")

    # metadata sub-fields
    metadata = fm.get("metadata")
    if metadata is None:
        pass  # already reported above
    elif not isinstance(metadata, dict):
        errors.append("'metadata' must be a mapping")
    else:
        missing_meta = REQUIRED_METADATA - set(metadata.keys())
        if missing_meta:
            errors.append(
                f"missing metadata fields: {', '.join(sorted(missing_meta))}"
            )

    # compatibility required values
    compat = fm.get("compatibility")
    if compat is None:
        pass  # already reported above
    elif not isinstance(compat, list):
        errors.append("'compatibility' must be a list")
    else:
        compat_set = set(compat)
        missing_compat = REQUIRED_COMPATIBILITY - compat_set
        if missing_compat:
            errors.append(
                f"missing compatibility values: {', '.join(sorted(missing_compat))}"
            )

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <skills-root-directory>", file=sys.stderr)
        return 1

    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"Error: '{root}' is not a directory", file=sys.stderr)
        return 1

    skill_files = sorted(
        f for f in root.rglob("SKILL.md")
        if ".claude" not in f.parts and not any(p.startswith(".") for p in f.parts)
    )
    if not skill_files:
        print(f"No SKILL.md files found under '{root}'")
        return 0

    has_errors = False
    for skill_path in skill_files:
        errors = validate(skill_path)
        if errors:
            has_errors = True
            rel = skill_path.relative_to(root)
            print(f"\n{rel}:")
            for err in errors:
                print(f"  - {err}")

    if has_errors:
        print(f"\nFrontmatter validation failed.")
        return 1

    print(f"All {len(skill_files)} SKILL.md files passed frontmatter validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
