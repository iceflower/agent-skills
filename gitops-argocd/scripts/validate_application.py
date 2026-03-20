#!/usr/bin/env python3
"""Validate Argo CD Application YAML manifests.

Checks:
- Required fields (metadata.name, spec.source, spec.destination)
- Sync policy configuration
- Project reference validity
- Source configuration (repoURL, path/chart, targetRevision)
- Destination configuration (server/name, namespace)
- Common misconfigurations

Usage:
    python validate_application.py app.yaml
    python validate_application.py apps/
    python validate_application.py --recursive argocd/
"""

import argparse
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

Finding = Tuple[str, int, str, str]  # (file, line, severity, message)

ERROR = "ERROR"
WARN = "WARN"

# Try to import yaml, use fallback if not available
try:
    import yaml as _yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

ARGOCD_KINDS = {"Application", "ApplicationSet", "AppProject"}


def parse_yaml_documents(content: str) -> List[Tuple[int, Dict]]:
    """Parse YAML content into list of (start_line, document_dict)."""
    if HAS_YAML:
        return _parse_with_pyyaml(content)
    return _parse_with_fallback(content)


def _parse_with_pyyaml(content: str) -> List[Tuple[int, Dict]]:
    """Parse using PyYAML."""
    documents = []
    raw_docs = re.split(r"^---\s*$", content, flags=re.MULTILINE)
    line_offset = 0

    for raw_doc in raw_docs:
        if not raw_doc.strip():
            line_offset += raw_doc.count("\n")
            continue
        try:
            doc = _yaml.safe_load(raw_doc)
            if isinstance(doc, dict):
                documents.append((line_offset + 1, doc))
        except _yaml.YAMLError:
            pass
        line_offset += raw_doc.count("\n")

    return documents


def _parse_with_fallback(content: str) -> List[Tuple[int, Dict]]:
    """Simple string-based parser for Argo CD Application manifests."""
    documents = []
    raw_docs = re.split(r"^---\s*$", content, flags=re.MULTILINE)
    line_offset = 0

    for raw_doc in raw_docs:
        if not raw_doc.strip():
            line_offset += raw_doc.count("\n")
            continue

        doc = _extract_fields(raw_doc)
        if doc.get("kind"):
            documents.append((line_offset + 1, doc))
        line_offset += raw_doc.count("\n")

    return documents


def _extract_fields(text: str) -> Dict[str, Any]:
    """Extract basic fields from YAML text using regex."""
    doc: Dict[str, Any] = {}

    m = re.search(r"^kind:\s*(\S+)", text, re.MULTILINE)
    if m:
        doc["kind"] = m.group(1).strip("\"'")

    m = re.search(r"^apiVersion:\s*(\S+)", text, re.MULTILINE)
    if m:
        doc["apiVersion"] = m.group(1).strip("\"'")

    m = re.search(r"^\s+name:\s*(\S+)", text, re.MULTILINE)
    if m:
        doc.setdefault("metadata", {})["name"] = m.group(1).strip("\"'")

    # Check for key sections
    doc["_has_source"] = bool(re.search(r"^\s+source:", text, re.MULTILINE))
    doc["_has_sources"] = bool(re.search(r"^\s+sources:", text, re.MULTILINE))
    doc["_has_destination"] = bool(re.search(r"^\s+destination:", text, re.MULTILINE))
    doc["_has_project"] = bool(re.search(r"^\s+project:", text, re.MULTILINE))
    doc["_has_sync_policy"] = bool(re.search(r"^\s+syncPolicy:", text, re.MULTILINE))
    doc["_has_automated"] = bool(re.search(r"^\s+automated:", text, re.MULTILINE))
    doc["_has_repo_url"] = bool(re.search(r"^\s+repoURL:", text, re.MULTILINE))
    doc["_has_target_revision"] = bool(re.search(r"^\s+targetRevision:", text, re.MULTILINE))
    doc["_has_namespace"] = bool(re.search(r"^\s+namespace:", text, re.MULTILINE))
    doc["_has_server"] = bool(re.search(r"^\s+server:", text, re.MULTILINE))
    doc["_has_self_heal"] = bool(re.search(r"selfHeal:\s*true", text, re.MULTILINE))
    doc["_has_prune"] = bool(re.search(r"prune:\s*true", text, re.MULTILINE))
    doc["_has_retry"] = bool(re.search(r"^\s+retry:", text, re.MULTILINE))

    m = re.search(r"^\s+project:\s*(\S+)", text, re.MULTILINE)
    if m:
        doc["_project_value"] = m.group(1).strip("\"'")

    return doc


def deep_get(d: Any, *keys: str, default: Any = None) -> Any:
    """Get a nested value from a dictionary."""
    current = d
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current


def validate_application(
    doc: Dict, filepath: str, start_line: int
) -> List[Finding]:
    """Validate a single Argo CD Application document."""
    findings: List[Finding] = []
    kind = doc.get("kind", "")
    name = deep_get(doc, "metadata", "name", default="<unknown>")
    label = f"{kind}/{name}"

    if "_has_source" in doc:
        return _validate_with_fallback(doc, filepath, start_line, label)

    # Full YAML validation
    api_version = doc.get("apiVersion", "")
    if not api_version.startswith("argoproj.io/"):
        findings.append((
            filepath, start_line, ERROR,
            f"{label}: apiVersion should be argoproj.io/v1alpha1, got '{api_version}'",
        ))

    metadata = doc.get("metadata", {})
    if not metadata.get("name"):
        findings.append((filepath, start_line, ERROR, f"{label}: Missing metadata.name"))

    spec = doc.get("spec", {})
    if not spec:
        findings.append((filepath, start_line, ERROR, f"{label}: Missing spec"))
        return findings

    # Project
    project = spec.get("project")
    if not project:
        findings.append((filepath, start_line, ERROR, f"{label}: Missing spec.project"))
    elif project == "default":
        findings.append((
            filepath, start_line, WARN,
            f"{label}: Using 'default' project. Consider a dedicated AppProject for isolation.",
        ))

    # Source
    source = spec.get("source")
    sources = spec.get("sources")
    if not source and not sources:
        findings.append((filepath, start_line, ERROR, f"{label}: Missing spec.source or spec.sources"))
    elif source:
        _validate_source(source, label, filepath, start_line, findings)

    if sources and isinstance(sources, list):
        for i, src in enumerate(sources):
            _validate_source(src, f"{label} sources[{i}]", filepath, start_line, findings)

    # Destination
    destination = spec.get("destination", {})
    if not destination:
        findings.append((filepath, start_line, ERROR, f"{label}: Missing spec.destination"))
    else:
        if not destination.get("server") and not destination.get("name"):
            findings.append((
                filepath, start_line, ERROR,
                f"{label}: spec.destination must have 'server' or 'name'",
            ))
        if not destination.get("namespace"):
            findings.append((
                filepath, start_line, WARN,
                f"{label}: No namespace in destination. Resources will use the default namespace.",
            ))

    # Sync policy
    sync_policy = spec.get("syncPolicy")
    if not sync_policy:
        findings.append((
            filepath, start_line, WARN,
            f"{label}: No syncPolicy defined. Manual sync will be required.",
        ))
    else:
        automated = sync_policy.get("automated")
        if automated:
            if not automated.get("selfHeal"):
                findings.append((
                    filepath, start_line, WARN,
                    f"{label}: automated sync without selfHeal. "
                    f"Drift from Git will not be auto-corrected.",
                ))
            if not automated.get("prune"):
                findings.append((
                    filepath, start_line, WARN,
                    f"{label}: automated sync without prune. "
                    f"Deleted resources in Git will remain in the cluster.",
                ))

        if not sync_policy.get("retry"):
            findings.append((
                filepath, start_line, WARN,
                f"{label}: No retry policy. Transient failures will not be retried.",
            ))

    return findings


def _validate_source(
    source: Dict, label: str, filepath: str, start_line: int, findings: List[Finding]
) -> None:
    """Validate a source block."""
    if not source.get("repoURL"):
        findings.append((filepath, start_line, ERROR, f"{label}: Missing source.repoURL"))

    if not source.get("path") and not source.get("chart"):
        findings.append((
            filepath, start_line, ERROR,
            f"{label}: Source must have 'path' (Git) or 'chart' (Helm)",
        ))

    target_rev = source.get("targetRevision")
    if not target_rev:
        findings.append((
            filepath, start_line, WARN,
            f"{label}: No targetRevision specified. Defaults to HEAD.",
        ))
    elif target_rev in ("HEAD", "master", "main"):
        findings.append((
            filepath, start_line, WARN,
            f"{label}: targetRevision is '{target_rev}'. "
            f"Consider using a specific tag or SHA for production.",
        ))


def _validate_with_fallback(
    doc: Dict, filepath: str, start_line: int, label: str
) -> List[Finding]:
    """Validate using fields extracted by fallback parser."""
    findings: List[Finding] = []

    if not doc.get("_has_source") and not doc.get("_has_sources"):
        findings.append((filepath, start_line, ERROR, f"{label}: Missing spec.source"))

    if not doc.get("_has_destination"):
        findings.append((filepath, start_line, ERROR, f"{label}: Missing spec.destination"))

    if not doc.get("_has_project"):
        findings.append((filepath, start_line, ERROR, f"{label}: Missing spec.project"))
    elif doc.get("_project_value") == "default":
        findings.append((
            filepath, start_line, WARN,
            f"{label}: Using 'default' project. Consider a dedicated AppProject.",
        ))

    if not doc.get("_has_repo_url"):
        findings.append((filepath, start_line, ERROR, f"{label}: Missing source.repoURL"))

    if not doc.get("_has_target_revision"):
        findings.append((
            filepath, start_line, WARN,
            f"{label}: No targetRevision specified.",
        ))

    if not doc.get("_has_sync_policy"):
        findings.append((
            filepath, start_line, WARN,
            f"{label}: No syncPolicy defined.",
        ))
    elif doc.get("_has_automated"):
        if not doc.get("_has_self_heal"):
            findings.append((
                filepath, start_line, WARN,
                f"{label}: automated sync without selfHeal.",
            ))
        if not doc.get("_has_prune"):
            findings.append((
                filepath, start_line, WARN,
                f"{label}: automated sync without prune.",
            ))

    return findings


def find_yaml_files(path: str, recursive: bool) -> List[str]:
    """Find YAML files at the given path."""
    if os.path.isfile(path):
        return [path]

    if not os.path.isdir(path):
        return []

    yaml_files = []
    if recursive:
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for filename in filenames:
                if filename.endswith((".yaml", ".yml")):
                    yaml_files.append(os.path.join(dirpath, filename))
    else:
        for filename in os.listdir(path):
            if filename.endswith((".yaml", ".yml")):
                yaml_files.append(os.path.join(path, filename))

    return sorted(yaml_files)


def is_argocd_manifest(content: str) -> bool:
    """Quick check if content looks like an Argo CD manifest."""
    return bool(
        re.search(r"argoproj\.io/", content)
        and re.search(r"^kind:\s*(Application|ApplicationSet|AppProject)", content, re.MULTILINE)
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Argo CD Application YAML manifests.",
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

    yaml_files = find_yaml_files(path, args.recursive)
    if not yaml_files:
        print(f"No YAML files found at {path}")
        return 0

    if not HAS_YAML:
        print("Note: PyYAML not installed. Using basic string parser (limited accuracy).\n")

    all_findings: List[Finding] = []
    apps_checked = 0

    for filepath in yaml_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            print(f"WARN: Cannot read {filepath}: {e}", file=sys.stderr)
            continue

        if not is_argocd_manifest(content):
            continue

        documents = parse_yaml_documents(content)
        for start_line, doc in documents:
            if not isinstance(doc, dict):
                continue
            if doc.get("kind") not in ARGOCD_KINDS:
                continue

            apps_checked += 1
            findings = validate_application(doc, filepath, start_line)
            all_findings.extend(findings)

    if apps_checked == 0:
        print(f"No Argo CD Application manifests found in {len(yaml_files)} YAML file(s).")
        return 0

    if not all_findings:
        print(f"OK: No issues found in {apps_checked} Application(s).")
        return 0

    error_count = sum(1 for f in all_findings if f[2] == ERROR)
    warn_count = sum(1 for f in all_findings if f[2] == WARN)

    findings_by_file: dict = {}
    for filepath, line_num, severity, message in all_findings:
        rel_path = os.path.relpath(filepath, os.path.dirname(path) if os.path.isfile(path) else path)
        findings_by_file.setdefault(rel_path, []).append((line_num, severity, message))

    for rel_path, findings in sorted(findings_by_file.items()):
        print(f"\n  {rel_path}:")
        for line_num, severity, message in findings:
            indented = message.replace("\n", "\n      ")
            print(f"    [{severity}] line ~{line_num}: {indented}")

    print(f"\nChecked {apps_checked} Application(s): {error_count} error(s), {warn_count} warning(s).")
    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
