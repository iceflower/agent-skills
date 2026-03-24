#!/usr/bin/env python3
"""Validate Prometheus alerting rules for common issues.

Checks:
- Required fields (alert, expr, labels, annotations)
- Missing severity label
- Missing summary/description annotations
- Invalid or risky PromQL patterns
- Missing for duration (instant alerts)
- Runbook URL presence

Usage:
    python check_alert_rules.py alerts.yaml
    python check_alert_rules.py rules/
    python check_alert_rules.py --recursive monitoring/
"""

import argparse
import os
import re
import sys
from typing import Any, Dict, List, Tuple

Finding = Tuple[str, int, str, str]  # (file, line, severity, message)

ERROR = "ERROR"
WARN = "WARN"

try:
    import yaml as _yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def parse_yaml(content: str) -> Any:
    """Parse YAML content."""
    if HAS_YAML:
        try:
            return _yaml.safe_load(content)
        except _yaml.YAMLError:
            return None
    return _parse_fallback(content)


def _parse_fallback(content: str) -> Dict[str, Any]:
    """Extract alert rules using regex when PyYAML is unavailable."""
    result: Dict[str, Any] = {"groups": []}

    # Split by group pattern
    group_blocks = re.split(r"^\s*-\s*name:", content, flags=re.MULTILINE)
    if len(group_blocks) <= 1:
        return result

    for block in group_blocks[1:]:
        group: Dict[str, Any] = {"rules": []}

        name_match = re.match(r"\s*(\S+)", block)
        if name_match:
            group["name"] = name_match.group(1).strip("\"'")

        # Extract alert blocks
        alert_blocks = re.split(r"^\s+-\s*alert:", block, flags=re.MULTILINE)
        for alert_block in alert_blocks[1:]:
            rule: Dict[str, Any] = {}

            alert_name = re.match(r"\s*(\S+)", alert_block)
            if alert_name:
                rule["alert"] = alert_name.group(1).strip("\"'")

            expr_match = re.search(r"^\s+expr:\s*(.+?)$", alert_block, re.MULTILINE)
            if expr_match:
                rule["expr"] = expr_match.group(1).strip().strip("\"'")

            for_match = re.search(r"^\s+for:\s*(\S+)", alert_block, re.MULTILINE)
            if for_match:
                rule["for"] = for_match.group(1).strip("\"'")

            # Extract labels
            labels_match = re.search(
                r"^\s+labels:\s*\n((?:\s+\w+:.*\n)*)", alert_block, re.MULTILINE
            )
            if labels_match:
                rule["labels"] = {}
                for lm in re.finditer(r"^\s+(\w+):\s*(.+)$", labels_match.group(1), re.MULTILINE):
                    rule["labels"][lm.group(1)] = lm.group(2).strip().strip("\"'")

            # Extract annotations
            ann_match = re.search(
                r"^\s+annotations:\s*\n((?:\s+\w+:.*\n)*)", alert_block, re.MULTILINE
            )
            if ann_match:
                rule["annotations"] = {}
                for am in re.finditer(r"^\s+(\w+):\s*(.+)$", ann_match.group(1), re.MULTILINE):
                    rule["annotations"][am.group(1)] = am.group(2).strip().strip("\"'")

            if rule.get("alert"):
                group["rules"].append(rule)

        if group.get("rules"):
            result["groups"].append(group)

    return result


def validate_rule(
    rule: Dict, group_name: str, filepath: str, rule_index: int
) -> List[Finding]:
    """Validate a single alerting rule."""
    findings: List[Finding] = []
    alert_name = rule.get("alert", "<unnamed>")
    label = f"{group_name}/{alert_name}"

    # Required: alert name
    if not rule.get("alert"):
        findings.append((
            filepath, rule_index, ERROR,
            f"Rule in group '{group_name}' has no 'alert' name.",
        ))

    # Required: expr
    expr = rule.get("expr", "")
    if not expr:
        findings.append((
            filepath, rule_index, ERROR,
            f"{label}: Missing 'expr' (PromQL expression).",
        ))
    else:
        _check_expr(expr, label, filepath, rule_index, findings)

    # Check 'for' duration
    if not rule.get("for"):
        findings.append((
            filepath, rule_index, WARN,
            f"{label}: No 'for' duration. Alert fires instantly on first evaluation.\n"
            f"  Add a 'for' duration (e.g., '5m') to avoid false positives from transient spikes.",
        ))

    # Labels
    labels = rule.get("labels", {})
    if not labels:
        findings.append((
            filepath, rule_index, WARN,
            f"{label}: No labels defined.",
        ))
    else:
        if "severity" not in labels:
            findings.append((
                filepath, rule_index, WARN,
                f"{label}: Missing 'severity' label.\n"
                f"  Add severity (critical/warning/info) for proper alert routing.",
            ))
        else:
            severity_val = labels["severity"]
            valid_severities = {"critical", "warning", "info", "page", "ticket"}
            if severity_val.lower() not in valid_severities:
                findings.append((
                    filepath, rule_index, WARN,
                    f"{label}: Unusual severity value '{severity_val}'.\n"
                    f"  Common values: critical, warning, info",
                ))

    # Annotations
    annotations = rule.get("annotations", {})
    if not annotations:
        findings.append((
            filepath, rule_index, WARN,
            f"{label}: No annotations defined.\n"
            f"  Add 'summary' and 'description' for actionable alert messages.",
        ))
    else:
        if "summary" not in annotations:
            findings.append((
                filepath, rule_index, WARN,
                f"{label}: Missing 'summary' annotation.",
            ))
        if "description" not in annotations:
            findings.append((
                filepath, rule_index, WARN,
                f"{label}: Missing 'description' annotation.\n"
                f"  Add context about what triggered the alert and potential impact.",
            ))
        if "runbook_url" not in annotations and "runbook" not in annotations:
            findings.append((
                filepath, rule_index, WARN,
                f"{label}: No runbook URL in annotations.\n"
                f"  Add 'runbook_url' to guide on-call engineers.",
            ))

    return findings


def _check_expr(
    expr: str, label: str, filepath: str, rule_index: int, findings: List[Finding]
) -> None:
    """Check PromQL expression for common issues."""
    # Warn about == 0 without rate/increase
    if "== 0" in expr and not any(fn in expr for fn in ("rate(", "increase(", "delta(")):
        pass  # This is normal for gauge metrics

    # Check for missing rate() on counter metrics
    if "_total" in expr and "rate(" not in expr and "increase(" not in expr:
        findings.append((
            filepath, rule_index, WARN,
            f"{label}: Expression uses '_total' metric without rate() or increase().\n"
            f"  Counter metrics should typically be wrapped in rate() or increase().",
        ))

    # Warn about alerts without thresholds
    if not re.search(r"[><=!]+\s*\d", expr) and "absent(" not in expr and "vector(" not in expr:
        findings.append((
            filepath, rule_index, WARN,
            f"{label}: Expression has no comparison threshold.\n"
            f"  Consider adding a threshold for clarity (e.g., '> 0.9').",
        ))


def validate_file(filepath: str) -> List[Finding]:
    """Validate an alert rules file."""
    findings: List[Finding] = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        findings.append((filepath, 0, ERROR, f"Cannot read file: {e}"))
        return findings

    data = parse_yaml(content)
    if not isinstance(data, dict):
        findings.append((filepath, 0, ERROR, "Invalid YAML or not a valid alert rules file."))
        return findings

    groups = data.get("groups", [])
    if not groups:
        return findings

    if not isinstance(groups, list):
        findings.append((filepath, 0, ERROR, "'groups' must be a list."))
        return findings

    for group_idx, group in enumerate(groups):
        if not isinstance(group, dict):
            continue

        group_name = group.get("name", f"<group-{group_idx}>")
        rules = group.get("rules", [])

        if not rules:
            findings.append((
                filepath, 0, WARN,
                f"Group '{group_name}' has no rules.",
            ))
            continue

        for rule_idx, rule in enumerate(rules):
            if not isinstance(rule, dict):
                continue
            if not rule.get("alert"):
                continue  # Skip recording rules

            rule_findings = validate_rule(rule, group_name, filepath, rule_idx + 1)
            findings.extend(rule_findings)

    return findings


def find_rule_files(path: str, recursive: bool) -> List[str]:
    """Find alert rule YAML files."""
    if os.path.isfile(path):
        return [path]

    if not os.path.isdir(path):
        return []

    files = []
    if recursive:
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for filename in filenames:
                if filename.endswith((".yaml", ".yml")):
                    files.append(os.path.join(dirpath, filename))
    else:
        for filename in os.listdir(path):
            if filename.endswith((".yaml", ".yml")):
                files.append(os.path.join(path, filename))

    return sorted(files)


def is_alert_rules_file(content: str) -> bool:
    """Quick check if content looks like a Prometheus alert rules file."""
    return bool(
        re.search(r"^\s*groups:", content, re.MULTILINE)
        and re.search(r"^\s+-?\s*alert:", content, re.MULTILINE)
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Prometheus alerting rules for common issues.",
        epilog="Exit code 0 = clean, 1 = errors found.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="File or directory path (default: current directory)",
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Recursively scan directories",
    )
    args = parser.parse_args()

    path = os.path.abspath(args.path)
    if not os.path.exists(path):
        print(f"Error: Path not found: {path}", file=sys.stderr)
        return 1

    yaml_files = find_rule_files(path, args.recursive)
    if not yaml_files:
        print(f"No YAML files found at {path}")
        return 0

    if not HAS_YAML:
        print("Note: PyYAML not installed. Using basic string parser (limited accuracy).\n")

    all_findings: List[Finding] = []
    files_checked = 0

    for filepath in yaml_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue

        if not is_alert_rules_file(content):
            continue

        files_checked += 1
        all_findings.extend(validate_file(filepath))

    if files_checked == 0:
        print(f"No Prometheus alert rules found in {len(yaml_files)} YAML file(s).")
        return 0

    if not all_findings:
        print(f"OK: No issues found in {files_checked} alert rules file(s).")
        return 0

    error_count = sum(1 for f in all_findings if f[2] == ERROR)
    warn_count = sum(1 for f in all_findings if f[2] == WARN)

    findings_by_file: Dict[str, List] = {}
    for filepath, line_num, severity, message in all_findings:
        rel_path = os.path.relpath(filepath, os.path.dirname(path) if os.path.isfile(path) else path)
        findings_by_file.setdefault(rel_path, []).append((line_num, severity, message))

    for rel_path, findings in sorted(findings_by_file.items()):
        print(f"\n  {rel_path}:")
        for line_num, severity, message in findings:
            location = f"rule #{line_num}" if line_num > 0 else "general"
            indented = message.replace("\n", "\n      ")
            print(f"    [{severity}] {location}: {indented}")

    print(f"\nChecked {files_checked} file(s): {error_count} error(s), {warn_count} warning(s).")
    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
