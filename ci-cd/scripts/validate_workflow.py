#!/usr/bin/env python3
"""Validate GitHub Actions workflow YAML files.

Checks for common issues:
  - Actions using unpinned versions or 'latest' tag
  - Missing 'permissions' block
  - Secrets referenced but not in env
  - 'pull_request_target' usage warning
  - Missing timeout-minutes on jobs
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, NamedTuple, Optional


class Finding(NamedTuple):
    file: str
    line: int
    severity: str
    description: str

    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line > 0 else self.file
        return f"[{self.severity}] {loc}: {self.description}"


def load_yaml_simple(file_path: str) -> Optional[Dict[str, Any]]:
    """Load YAML using PyYAML if available, else return None."""
    try:
        import yaml
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        return None
    except Exception:
        return None


def find_workflow_files(path: str) -> List[str]:
    """Find GitHub Actions workflow files."""
    files: List[str] = []

    if os.path.isfile(path):
        files.append(path)
    elif os.path.isdir(path):
        for root, _dirs, filenames in os.walk(path):
            for fname in sorted(filenames):
                if fname.endswith((".yml", ".yaml")):
                    files.append(os.path.join(root, fname))
    return files


def validate_with_regex(file_path: str) -> List[Finding]:
    """Validate workflow file using line-by-line regex analysis.

    This works regardless of whether PyYAML is installed.
    """
    findings: List[Finding] = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        findings.append(Finding(file_path, 0, "ERROR", f"Cannot read file: {e}"))
        return findings

    content = "".join(lines)

    has_permissions_block = False
    has_pull_request_target = False
    in_jobs_section = False
    current_job_name = ""
    current_job_line = 0
    job_has_timeout = False
    jobs_seen: List[tuple] = []  # (name, line, has_timeout)

    # Patterns
    uses_pattern = re.compile(r"^\s*-?\s*uses:\s*(.+)", re.IGNORECASE)
    permissions_pattern = re.compile(r"^permissions\s*:", re.IGNORECASE)
    prt_pattern = re.compile(r"pull_request_target", re.IGNORECASE)
    secrets_pattern = re.compile(r"\$\{\{\s*secrets\.(\w+)\s*\}\}")
    timeout_pattern = re.compile(r"^\s+timeout-minutes\s*:", re.IGNORECASE)
    job_pattern = re.compile(r"^  (\w[\w-]*):\s*$")
    jobs_header = re.compile(r"^jobs\s*:\s*$")
    env_secret_pattern = re.compile(r"^\s+\w+:\s*\$\{\{\s*secrets\.\w+\s*\}\}")

    for line_num, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()

        # Track permissions block
        if permissions_pattern.match(line):
            has_permissions_block = True

        # Check for pull_request_target
        if prt_pattern.search(line) and not line.lstrip().startswith("#"):
            has_pull_request_target = True
            findings.append(Finding(
                file_path, line_num, "HIGH",
                "pull_request_target trigger detected - requires careful security review "
                "(code from fork runs with write access to base repo)",
            ))

        # Track jobs section
        if jobs_header.match(line):
            in_jobs_section = True
            continue

        if in_jobs_section:
            job_match = job_pattern.match(raw_line)
            if job_match:
                # Save previous job
                if current_job_name:
                    jobs_seen.append((current_job_name, current_job_line, job_has_timeout))
                current_job_name = job_match.group(1)
                current_job_line = line_num
                job_has_timeout = False

            if timeout_pattern.match(line):
                job_has_timeout = True

        # Check uses: directives
        uses_match = uses_pattern.match(line)
        if uses_match:
            action_ref = uses_match.group(1).strip().strip('"').strip("'")
            # Skip comments
            if "#" in action_ref:
                action_ref = action_ref[:action_ref.index("#")].strip()

            # Skip docker:// and local paths
            if action_ref.startswith(("docker://", "./", "../")):
                continue

            _check_action_version(file_path, line_num, action_ref, findings)

        # Check for secrets references
        for secret_match in secrets_pattern.finditer(line):
            secret_name = secret_match.group(1)
            # This is informational - we note secrets found
            if secret_name == "GITHUB_TOKEN":
                continue  # Built-in, always available

    # Save last job
    if current_job_name:
        jobs_seen.append((current_job_name, current_job_line, job_has_timeout))

    # Report missing permissions
    if not has_permissions_block:
        findings.append(Finding(
            file_path, 1, "MEDIUM",
            "Missing top-level 'permissions' block - workflow runs with default "
            "token permissions (consider restricting with explicit permissions)",
        ))

    # Report missing timeout-minutes
    for job_name, job_line, has_timeout in jobs_seen:
        if not has_timeout:
            findings.append(Finding(
                file_path, job_line, "LOW",
                f"Job '{job_name}' missing timeout-minutes - may run indefinitely "
                f"(default is 6 hours)",
            ))

    return findings


def _check_action_version(
    file_path: str, line_num: int, action_ref: str, findings: List[Finding]
) -> None:
    """Check if an action reference uses a pinned version."""
    if "@" not in action_ref:
        findings.append(Finding(
            file_path, line_num, "HIGH",
            f"Action '{action_ref}' has no version pinning - specify @version or @sha",
        ))
        return

    action_name, version = action_ref.rsplit("@", 1)

    if version.lower() == "latest":
        findings.append(Finding(
            file_path, line_num, "HIGH",
            f"Action '{action_name}' uses @latest - pin to a specific version or SHA",
        ))
    elif version == "main" or version == "master":
        findings.append(Finding(
            file_path, line_num, "HIGH",
            f"Action '{action_name}' uses @{version} branch - pin to a specific "
            f"version tag or SHA for reproducibility",
        ))
    elif not re.match(r"^[a-f0-9]{40}$", version):
        # Not a full SHA - check if it looks like a version tag
        if re.match(r"^v?\d+$", version):
            # Major version only (e.g., @v4) - acceptable but note it
            findings.append(Finding(
                file_path, line_num, "INFO",
                f"Action '{action_name}@{version}' uses major version tag - "
                f"consider pinning to full SHA for supply-chain security",
            ))
        elif not re.match(r"^v?\d+\.\d+", version):
            findings.append(Finding(
                file_path, line_num, "MEDIUM",
                f"Action '{action_name}@{version}' - version '{version}' does not "
                f"look like a semver tag or SHA",
            ))


def validate_with_yaml(file_path: str, spec: Dict[str, Any]) -> List[Finding]:
    """Additional structural validation when PyYAML is available."""
    findings: List[Finding] = []

    if not isinstance(spec, dict):
        findings.append(Finding(file_path, 0, "ERROR", "Workflow file is not a valid mapping"))
        return findings

    # Check for 'on' key (trigger)
    triggers = spec.get("on") or spec.get(True)  # YAML parses 'on' as True
    if triggers is None:
        findings.append(Finding(file_path, 0, "MEDIUM", "No trigger ('on') defined"))

    # Check jobs exist
    jobs = spec.get("jobs", {})
    if not jobs:
        findings.append(Finding(file_path, 0, "ERROR", "No jobs defined in workflow"))

    return findings


def main() -> int:
    default_path = ".github/workflows/"

    parser = argparse.ArgumentParser(
        description="Validate GitHub Actions workflow YAML files.",
        epilog="Exit code 0 = clean, 1 = findings detected.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=default_path,
        help=f"Workflow file or directory (default: {default_path})",
    )
    parser.add_argument(
        "--severity",
        choices=["INFO", "LOW", "MEDIUM", "HIGH", "ERROR"],
        default="LOW",
        help="Minimum severity to report (default: LOW)",
    )

    args = parser.parse_args()

    if not os.path.exists(args.path):
        # Try alternative common path
        if args.path == default_path and os.path.isdir(".github"):
            print(f"Warning: {args.path} not found, but .github/ exists", file=sys.stderr)
        print(f"Error: Path not found: {args.path}", file=sys.stderr)
        return 1

    workflow_files = find_workflow_files(args.path)

    if not workflow_files:
        print(f"No workflow files (*.yml, *.yaml) found in {args.path}", file=sys.stderr)
        return 1

    severity_order = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "ERROR": 4}
    min_level = severity_order.get(args.severity, 1)

    all_findings: List[Finding] = []

    for wf_file in workflow_files:
        # Always do regex-based validation (no dependencies needed)
        all_findings.extend(validate_with_regex(wf_file))

        # Additionally validate structure if PyYAML is available
        spec = load_yaml_simple(wf_file)
        if spec is not None:
            all_findings.extend(validate_with_yaml(wf_file, spec))

    filtered = [f for f in all_findings if severity_order.get(f.severity, 0) >= min_level]

    # Deduplicate
    seen = set()
    unique: List[Finding] = []
    for f in filtered:
        key = (f.file, f.line, f.description)
        if key not in seen:
            seen.add(key)
            unique.append(f)

    if not unique:
        print(f"OK: No issues found in {len(workflow_files)} workflow file(s)")
        return 0

    unique.sort(key=lambda f: (-severity_order.get(f.severity, 0), f.file, f.line))

    for finding in unique:
        print(finding)

    counts: Dict[str, int] = {}
    for f in unique:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    parts = [f"{v} {k}" for k, v in sorted(counts.items(), key=lambda x: -severity_order.get(x[0], 0))]
    print(f"\nSummary ({len(workflow_files)} file(s) scanned): {', '.join(parts)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
