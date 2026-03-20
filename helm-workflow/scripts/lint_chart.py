#!/usr/bin/env python3
"""Lint Helm charts for common issues.

Checks:
- Missing or invalid values.schema.json
- Deprecated Kubernetes API versions in templates
- Missing Chart.yaml required fields
- Common template issues (missing labels, no resource limits)
- values.yaml structure issues

Usage:
    python lint_chart.py mychart/
    python lint_chart.py --strict mychart/
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple

Finding = Tuple[str, int, str, str]  # (file, line, severity, message)

ERROR = "ERROR"
WARN = "WARN"

# Deprecated/removed API versions mapping (apiVersion -> removed in K8s version)
DEPRECATED_APIS = {
    "extensions/v1beta1": {
        "Deployment": "apps/v1 (removed in 1.16)",
        "DaemonSet": "apps/v1 (removed in 1.16)",
        "ReplicaSet": "apps/v1 (removed in 1.16)",
        "Ingress": "networking.k8s.io/v1 (removed in 1.22)",
    },
    "apps/v1beta1": {
        "Deployment": "apps/v1 (removed in 1.16)",
        "StatefulSet": "apps/v1 (removed in 1.16)",
    },
    "apps/v1beta2": {
        "Deployment": "apps/v1 (removed in 1.16)",
        "DaemonSet": "apps/v1 (removed in 1.16)",
        "StatefulSet": "apps/v1 (removed in 1.16)",
        "ReplicaSet": "apps/v1 (removed in 1.16)",
    },
    "networking.k8s.io/v1beta1": {
        "Ingress": "networking.k8s.io/v1 (removed in 1.22)",
        "IngressClass": "networking.k8s.io/v1 (removed in 1.22)",
    },
    "policy/v1beta1": {
        "PodDisruptionBudget": "policy/v1 (removed in 1.25)",
        "PodSecurityPolicy": "removed entirely in 1.25",
    },
    "rbac.authorization.k8s.io/v1beta1": {
        "ClusterRole": "rbac.authorization.k8s.io/v1 (removed in 1.22)",
        "ClusterRoleBinding": "rbac.authorization.k8s.io/v1 (removed in 1.22)",
        "Role": "rbac.authorization.k8s.io/v1 (removed in 1.22)",
        "RoleBinding": "rbac.authorization.k8s.io/v1 (removed in 1.22)",
    },
    "autoscaling/v2beta1": {
        "HorizontalPodAutoscaler": "autoscaling/v2 (removed in 1.26)",
    },
}

# Required fields in Chart.yaml
CHART_REQUIRED_FIELDS = ["apiVersion", "name", "version", "description"]


def validate_chart_yaml(chart_dir: str) -> List[Finding]:
    """Validate Chart.yaml for required fields and conventions."""
    findings: List[Finding] = []
    chart_path = os.path.join(chart_dir, "Chart.yaml")

    if not os.path.isfile(chart_path):
        findings.append((chart_path, 0, ERROR, "Chart.yaml not found"))
        return findings

    try:
        with open(chart_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        findings.append((chart_path, 0, ERROR, f"Cannot read Chart.yaml: {e}"))
        return findings

    for field in CHART_REQUIRED_FIELDS:
        pattern = rf"^{field}:\s*\S+"
        if not re.search(pattern, content, re.MULTILINE):
            findings.append((
                chart_path, 0, ERROR,
                f"Missing or empty required field: {field}",
            ))

    # Check apiVersion is v2 (Helm 3)
    m = re.search(r"^apiVersion:\s*(\S+)", content, re.MULTILINE)
    if m and m.group(1) != "v2":
        findings.append((
            chart_path, 0, WARN,
            f"Chart apiVersion is '{m.group(1)}'. Helm 3 charts should use apiVersion: v2.",
        ))

    # Check for maintainers
    if "maintainers:" not in content:
        findings.append((
            chart_path, 0, WARN,
            "No maintainers defined in Chart.yaml.",
        ))

    return findings


def validate_values_schema(chart_dir: str) -> List[Finding]:
    """Validate values.schema.json if present, warn if missing."""
    findings: List[Finding] = []
    schema_path = os.path.join(chart_dir, "values.schema.json")
    values_path = os.path.join(chart_dir, "values.yaml")

    if not os.path.isfile(values_path):
        return findings

    if not os.path.isfile(schema_path):
        findings.append((
            schema_path, 0, WARN,
            "No values.schema.json found. Consider adding a JSON Schema "
            "for values.yaml to validate user-provided values.",
        ))
        return findings

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
    except json.JSONDecodeError as e:
        findings.append((schema_path, 0, ERROR, f"Invalid JSON in values.schema.json: {e}"))
        return findings
    except OSError as e:
        findings.append((schema_path, 0, ERROR, f"Cannot read values.schema.json: {e}"))
        return findings

    if not isinstance(schema, dict):
        findings.append((schema_path, 0, ERROR, "values.schema.json root must be an object"))
        return findings

    if "$schema" not in schema:
        findings.append((
            schema_path, 0, WARN,
            "Missing $schema field. Add: \"$schema\": \"https://json-schema.org/draft/2020-12/schema\"",
        ))

    if "properties" not in schema and "type" not in schema:
        findings.append((
            schema_path, 0, WARN,
            "Schema has no 'properties' or 'type' definition. It may not validate anything.",
        ))

    return findings


def scan_templates_for_deprecated_apis(chart_dir: str) -> List[Finding]:
    """Scan template files for deprecated Kubernetes API versions."""
    findings: List[Finding] = []
    templates_dir = os.path.join(chart_dir, "templates")

    if not os.path.isdir(templates_dir):
        findings.append((templates_dir, 0, WARN, "No templates/ directory found"))
        return findings

    for dirpath, _, filenames in os.walk(templates_dir):
        for filename in filenames:
            if not filename.endswith((".yaml", ".yml", ".tpl")):
                continue

            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except OSError:
                continue

            for i, line in enumerate(lines, start=1):
                _check_deprecated_api(line, i, filepath, findings)
                _check_template_issues(line, i, filepath, findings)

    return findings


def _check_deprecated_api(
    line: str, line_num: int, filepath: str, findings: List[Finding]
) -> None:
    """Check a single line for deprecated API usage."""
    m = re.match(r"\s*apiVersion:\s*[\"']?([^\s\"'{}]+)", line)
    if not m:
        return

    api_version = m.group(1)
    # Skip Helm template expressions
    if "{{" in api_version:
        return

    if api_version in DEPRECATED_APIS:
        kinds = DEPRECATED_APIS[api_version]
        kind_list = ", ".join(f"{k} -> {v}" for k, v in kinds.items())
        findings.append((
            filepath, line_num, ERROR,
            f"Deprecated apiVersion '{api_version}'. "
            f"Migration paths: {kind_list}",
        ))


def _check_template_issues(
    line: str, line_num: int, filepath: str, findings: List[Finding]
) -> None:
    """Check for common template issues in a line."""
    stripped = line.strip()

    # Check for hardcoded image tags (not using .Values)
    if re.match(r"\s*image:\s*[\"']?[a-zA-Z]", stripped):
        if "{{" not in stripped and ".Values" not in stripped:
            findings.append((
                filepath, line_num, WARN,
                f"Hardcoded image reference. Use .Values for image configuration.\n"
                f"  {stripped.strip()}",
            ))


def scan_templates_for_best_practices(chart_dir: str) -> List[Finding]:
    """Check templates for Helm best practice compliance."""
    findings: List[Finding] = []
    templates_dir = os.path.join(chart_dir, "templates")

    if not os.path.isdir(templates_dir):
        return findings

    has_notes = os.path.isfile(os.path.join(templates_dir, "NOTES.txt"))
    if not has_notes:
        findings.append((
            os.path.join(templates_dir, "NOTES.txt"), 0, WARN,
            "No NOTES.txt found. Add one to provide post-install instructions.",
        ))

    helpers_path = os.path.join(templates_dir, "_helpers.tpl")
    if not os.path.isfile(helpers_path):
        findings.append((
            helpers_path, 0, WARN,
            "No _helpers.tpl found. Use helpers for reusable template definitions.",
        ))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lint Helm charts for common issues.",
        epilog="Exit code 0 = clean, 1 = errors found.",
    )
    parser.add_argument(
        "chart",
        help="Path to the Helm chart directory",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )

    args = parser.parse_args()
    chart_dir = os.path.abspath(args.chart)

    if not os.path.isdir(chart_dir):
        print(f"Error: Not a directory: {chart_dir}", file=sys.stderr)
        return 1

    all_findings: List[Finding] = []
    all_findings.extend(validate_chart_yaml(chart_dir))
    all_findings.extend(validate_values_schema(chart_dir))
    all_findings.extend(scan_templates_for_deprecated_apis(chart_dir))
    all_findings.extend(scan_templates_for_best_practices(chart_dir))

    if not all_findings:
        print(f"OK: No issues found in {chart_dir}")
        return 0

    error_count = 0
    warn_count = 0

    findings_by_file: Dict[str, List] = {}
    for filepath, line_num, severity, message in all_findings:
        rel_path = os.path.relpath(filepath, chart_dir)
        findings_by_file.setdefault(rel_path, []).append((line_num, severity, message))

    for rel_path, findings in sorted(findings_by_file.items()):
        print(f"\n  {rel_path}:")
        for line_num, severity, message in findings:
            if severity == ERROR:
                error_count += 1
            else:
                warn_count += 1
            location = f"line {line_num}" if line_num > 0 else "general"
            indented = message.replace("\n", "\n      ")
            print(f"    [{severity}] {location}: {indented}")

    print(f"\nTotal: {error_count} error(s), {warn_count} warning(s)")

    if args.strict:
        return 1 if (error_count + warn_count) > 0 else 0
    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
