#!/usr/bin/env python3
"""Validate Terraform configurations.

Runs terraform fmt and validate if terraform is installed, otherwise
falls back to static analysis for common issues.

Checks:
- terraform fmt -check (formatting)
- terraform validate (configuration validity)
- Hardcoded secrets in .tf files
- Missing backend configuration
- Deprecated resources
- Missing .terraform.lock.hcl

Usage:
    python validate_terraform.py
    python validate_terraform.py /path/to/terraform/dir
    python validate_terraform.py --skip-fmt
"""

import argparse
import os
import re
import subprocess
import sys
from typing import List, Tuple

Finding = Tuple[str, int, str, str]  # (file, line, severity, message)

ERROR = "ERROR"
WARN = "WARN"
INFO = "INFO"

# Deprecated/removed resources (commonly encountered)
DEPRECATED_RESOURCES = {
    "aws_opsworks_stack": "OpsWorks was discontinued. Remove this resource.",
    "aws_opsworks_instance": "OpsWorks was discontinued. Remove this resource.",
    "aws_opsworks_layer": "OpsWorks was discontinued. Remove this resource.",
    "aws_opsworks_application": "OpsWorks was discontinued. Remove this resource.",
    "aws_simpledb_domain": "SimpleDB was discontinued. Remove this resource.",
    "aws_worklink_fleet": "WorkLink was discontinued. Remove this resource.",
    "aws_worklink_website_certificate_authority_association": "WorkLink was discontinued.",
    "aws_evidently_project": "CloudWatch Evidently is being discontinued.",
    "aws_evidently_feature": "CloudWatch Evidently is being discontinued.",
}

# Patterns that may indicate hardcoded secrets
SECRET_PATTERNS = [
    (re.compile(r'password\s*=\s*"[^"$]+"', re.IGNORECASE), "Possible hardcoded password"),
    (re.compile(r'secret\s*=\s*"[^"$]+"', re.IGNORECASE), "Possible hardcoded secret"),
    (re.compile(r'access_key\s*=\s*"[A-Z0-9]{16,}"', re.IGNORECASE), "Possible hardcoded access key"),
    (re.compile(r'secret_key\s*=\s*"[^"$]+"', re.IGNORECASE), "Possible hardcoded secret key"),
    (re.compile(r'token\s*=\s*"[^"$]+"', re.IGNORECASE), "Possible hardcoded token"),
    (re.compile(r'api_key\s*=\s*"[^"$]+"', re.IGNORECASE), "Possible hardcoded API key"),
    (re.compile(r'private_key\s*=\s*"[^"$]+"', re.IGNORECASE), "Possible hardcoded private key"),
]


def is_terraform_installed() -> bool:
    """Check if terraform CLI is available."""
    try:
        result = subprocess.run(
            ["terraform", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


def run_terraform_fmt(directory: str) -> Tuple[bool, str]:
    """Run terraform fmt -check and return (passed, output)."""
    try:
        result = subprocess.run(
            ["terraform", "fmt", "-check", "-recursive", "-diff"],
            capture_output=True,
            text=True,
            cwd=directory,
            timeout=60,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except (subprocess.TimeoutExpired, OSError) as e:
        return False, str(e)


def run_terraform_validate(directory: str) -> Tuple[bool, str]:
    """Run terraform validate and return (passed, output)."""
    # Check if .terraform directory exists (init required)
    terraform_dir = os.path.join(directory, ".terraform")
    if not os.path.isdir(terraform_dir):
        return True, "Skipped: terraform init has not been run (.terraform directory not found)"

    try:
        result = subprocess.run(
            ["terraform", "validate", "-json"],
            capture_output=True,
            text=True,
            cwd=directory,
            timeout=60,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except (subprocess.TimeoutExpired, OSError) as e:
        return False, str(e)


def find_tf_files(directory: str) -> List[str]:
    """Find all .tf files recursively."""
    tf_files = []
    for dirpath, dirnames, filenames in os.walk(directory):
        # Skip hidden dirs and .terraform
        dirnames[:] = [
            d for d in dirnames if not d.startswith(".") and d != ".terraform"
        ]
        for filename in filenames:
            if filename.endswith(".tf"):
                tf_files.append(os.path.join(dirpath, filename))
    return sorted(tf_files)


def check_hardcoded_secrets(filepath: str) -> List[Finding]:
    """Scan a .tf file for hardcoded secrets."""
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return findings

    in_block_comment = False
    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        if "/*" in stripped:
            in_block_comment = True
        if "*/" in stripped:
            in_block_comment = False
            continue
        if in_block_comment or stripped.startswith("#") or stripped.startswith("//"):
            continue

        for pattern, description in SECRET_PATTERNS:
            if pattern.search(line):
                # Exclude lines that use variable references
                if "${" in line or "var." in line:
                    continue
                findings.append(
                    (filepath, line_num, ERROR,
                     f"{description}\n  {stripped}\n"
                     f"  Use environment variables or a secret manager instead.")
                )
    return findings


def check_deprecated_resources(filepath: str) -> List[Finding]:
    """Scan for deprecated resource types."""
    findings = []
    resource_pattern = re.compile(r'resource\s+"(\w+)"\s+"')

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return findings

    for line_num, line in enumerate(lines, start=1):
        match = resource_pattern.search(line)
        if match:
            resource_type = match.group(1)
            if resource_type in DEPRECATED_RESOURCES:
                findings.append(
                    (filepath, line_num, WARN,
                     f"Deprecated resource type '{resource_type}': "
                     f"{DEPRECATED_RESOURCES[resource_type]}")
                )
    return findings


def check_backend_config(directory: str, tf_files: List[str]) -> List[Finding]:
    """Check for backend configuration."""
    findings = []
    has_backend = False

    for filepath in tf_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue

        if re.search(r'backend\s+"', content) or re.search(r"backend\s+\{", content):
            has_backend = True
            break

    if not has_backend and tf_files:
        findings.append(
            ("", 0, WARN,
             "No backend configuration found. State will be stored locally.\n"
             "  For team collaboration, configure a remote backend (S3, GCS, etc.).")
        )
    return findings


def check_lock_file(directory: str) -> List[Finding]:
    """Check for .terraform.lock.hcl."""
    findings = []
    lock_file = os.path.join(directory, ".terraform.lock.hcl")
    if not os.path.isfile(lock_file):
        # Only warn if there are .tf files
        tf_files = [f for f in os.listdir(directory) if f.endswith(".tf")]
        if tf_files:
            findings.append(
                ("", 0, INFO,
                 "No .terraform.lock.hcl found. "
                 "Run 'terraform init' to generate the dependency lock file.")
            )
    return findings


def static_analysis(directory: str) -> List[Finding]:
    """Perform static analysis when terraform CLI is not available."""
    findings: List[Finding] = []
    tf_files = find_tf_files(directory)

    if not tf_files:
        print(f"No .tf files found in {directory}")
        return findings

    for filepath in tf_files:
        findings.extend(check_hardcoded_secrets(filepath))
        findings.extend(check_deprecated_resources(filepath))

    findings.extend(check_backend_config(directory, tf_files))
    findings.extend(check_lock_file(directory))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Terraform configurations.",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Terraform configuration directory (default: current directory)",
    )
    parser.add_argument(
        "--skip-fmt",
        action="store_true",
        help="Skip terraform fmt check",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip terraform validate",
    )
    args = parser.parse_args()

    directory = os.path.abspath(args.directory)
    if not os.path.isdir(directory):
        print(f"ERROR: Directory not found: {directory}", file=sys.stderr)
        return 1

    has_terraform = is_terraform_installed()
    findings: List[Finding] = []
    exit_code = 0

    if has_terraform:
        print(f"Terraform CLI detected. Running checks in {directory}\n")

        # terraform fmt
        if not args.skip_fmt:
            passed, output = run_terraform_fmt(directory)
            if passed:
                print("[PASS] terraform fmt: All files formatted correctly.")
            else:
                print(f"[FAIL] terraform fmt: Files need formatting.")
                if output.strip():
                    for line in output.strip().splitlines()[:20]:
                        print(f"  {line}")
                exit_code = 1

        # terraform validate
        if not args.skip_validate:
            passed, output = run_terraform_validate(directory)
            if passed:
                print(f"[PASS] terraform validate: {output.strip()[:100] if output.strip() else 'Configuration is valid.'}")
            else:
                print(f"[FAIL] terraform validate:")
                if output.strip():
                    for line in output.strip().splitlines()[:20]:
                        print(f"  {line}")
                exit_code = 1

        print()  # blank line separator
    else:
        print("Terraform CLI not found. Running static analysis only.\n")

    # Always run static analysis
    findings = static_analysis(directory)

    if findings:
        print(f"Static analysis found {len(findings)} issue(s):\n")
        for filepath, line_num, severity, message in findings:
            if filepath:
                rel_path = os.path.relpath(filepath, directory)
                location = f"{rel_path}:{line_num}" if line_num > 0 else rel_path
            else:
                location = "general"

            indented = message.replace("\n", "\n    ")
            print(f"  [{severity}] {location}: {indented}")

            if severity == ERROR:
                exit_code = 1
    else:
        print("Static analysis: No issues found.")

    if exit_code == 0:
        print("\nOK: All checks passed.")
    else:
        print(f"\nFound issues that need attention.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
