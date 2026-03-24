#!/usr/bin/env python3
"""Check that all references/ links in SKILL.md files point to existing files.

Scans every SKILL.md for Markdown links containing 'references/' and verifies
the target file exists on disk.

Usage:
    python scripts/check_references.py <skills-root-directory>

Exit codes:
    0 - All reference links are valid.
    1 - One or more broken reference links found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LINK_PATTERN = re.compile(r"\[.*?\]\((.*?references/.*?)\)")


def check_skill(skill_md: Path, root: Path) -> list[str]:
    """Return a list of broken reference links for a single SKILL.md."""
    errors: list[str] = []
    text = skill_md.read_text(encoding="utf-8")
    skill_dir = skill_md.parent

    for match in LINK_PATTERN.finditer(text):
        ref_path = match.group(1)
        # Strip any fragment or query string
        ref_path = ref_path.split("#")[0].split("?")[0]
        if not ref_path:
            continue

        resolved = (skill_dir / ref_path).resolve()
        if not resolved.is_file():
            errors.append(f"broken link: {ref_path}")

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
        if not any(p.startswith(".") for p in f.parts)
    )
    if not skill_files:
        print(f"No SKILL.md files found under '{root}'")
        return 0

    has_errors = False
    for skill_path in skill_files:
        errors = check_skill(skill_path, root)
        if errors:
            has_errors = True
            rel = skill_path.relative_to(root)
            print(f"\n{rel}:")
            for err in errors:
                print(f"  - {err}")

    if has_errors:
        print("\nReference link validation failed.")
        return 1

    print(f"All reference links in {len(skill_files)} SKILL.md files are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
