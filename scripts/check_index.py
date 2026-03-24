#!/usr/bin/env python3
"""Check that all skill directories are listed in the index routing table.

Compares skill directories (those containing SKILL.md) against entries
in index/SKILL.md to find skills missing from the routing table.

Usage:
    python scripts/check_index.py <skills-root-directory>

Exit codes:
    0 - All skills are in the index.
    1 - One or more skills missing from the index.
"""

from __future__ import annotations

import sys
from pathlib import Path

EXCLUDED_DIRS = {"scripts", "index"}


def get_skill_dirs(root: Path) -> set[str]:
    """Return set of directory names that contain a SKILL.md file."""
    dirs: set[str] = set()
    for skill_md in root.rglob("SKILL.md"):
        if any(p.startswith(".") for p in skill_md.parts):
            continue
        skill_dir = skill_md.parent
        if skill_dir == root:
            continue
        # Only top-level skill directories
        rel = skill_dir.relative_to(root)
        if len(rel.parts) == 1:
            dirs.add(rel.parts[0])
    return dirs - EXCLUDED_DIRS


def get_index_entries(root: Path) -> set[str]:
    """Return set of skill names referenced in the index SKILL.md routing table."""
    index_path = root / "index" / "SKILL.md"
    if not index_path.is_file():
        return set()

    entries: set[str] = set()
    text = index_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        # Match table rows like "| Some description | skill-name |"
        line = line.strip()
        if line.startswith("|") and not line.startswith("| ---") and not line.startswith("| Keyword"):
            parts = [p.strip() for p in line.split("|")]
            # Last non-empty part is the skill name
            for part in reversed(parts):
                if part and part != "Recommended Skill":
                    entries.add(part)
                    break
    return entries


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <skills-root-directory>", file=sys.stderr)
        return 1

    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"Error: '{root}' is not a directory", file=sys.stderr)
        return 1

    skill_dirs = get_skill_dirs(root)
    index_entries = get_index_entries(root)

    missing = skill_dirs - index_entries
    if missing:
        print("Skills missing from index/SKILL.md routing table:")
        for name in sorted(missing):
            print(f"  - {name}")
        print(f"\n{len(missing)} skill(s) not found in index.")
        return 1

    print(f"All {len(skill_dirs)} skills are present in the index routing table.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
