#!/usr/bin/env python3
"""Validate Kubernetes YAML manifests for common issues.

Checks:
- Missing resources.requests/limits
- Using 'latest' image tag or no tag
- Running as root (no securityContext)
- Missing health probes (liveness/readiness)

Handles multi-document YAML files (--- separator).
Uses PyYAML if available, falls back to simple string parsing.

Usage:
    python validate_manifests.py deployment.yaml
    python validate_manifests.py k8s/
    python validate_manifests.py --recursive k8s/
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


# ── YAML Parsing ──────────────────────────────────────────────────────────


def parse_yaml_documents(content: str, filepath: str) -> List[Tuple[int, Dict]]:
    """Parse YAML content into list of (start_line, document_dict).

    Uses PyYAML if available, otherwise falls back to simple parsing.
    """
    if HAS_YAML:
        return _parse_with_pyyaml(content, filepath)
    return _parse_with_fallback(content, filepath)


def _parse_with_pyyaml(
    content: str, filepath: str
) -> List[Tuple[int, Dict]]:
    """Parse using PyYAML."""
    documents = []
    try:
        # Split by document separator to track line numbers
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
                pass  # Skip invalid documents

            line_offset += raw_doc.count("\n")

    except Exception:
        pass
    return documents


def _parse_with_fallback(
    content: str, filepath: str
) -> List[Tuple[int, Dict]]:
    """Simple string-based YAML parser for basic K8s manifest validation.

    This is NOT a full YAML parser. It extracts key fields needed for
    validation using regex patterns on common K8s manifest structures.
    """
    documents = []

    # Split by document separator
    raw_docs = re.split(r"^---\s*$", content, flags=re.MULTILINE)
    line_offset = 0

    for raw_doc in raw_docs:
        if not raw_doc.strip():
            line_offset += raw_doc.count("\n")
            continue

        doc = _extract_basic_fields(raw_doc)
        if doc.get("kind"):
            documents.append((line_offset + 1, doc))

        line_offset += raw_doc.count("\n")

    return documents


def _extract_basic_fields(text: str) -> Dict[str, Any]:
    """Extract basic K8s fields from YAML text using regex."""
    doc: Dict[str, Any] = {}

    # kind
    m = re.search(r"^kind:\s*(\S+)", text, re.MULTILINE)
    if m:
        doc["kind"] = m.group(1).strip('"').strip("'")

    # apiVersion
    m = re.search(r"^apiVersion:\s*(\S+)", text, re.MULTILINE)
    if m:
        doc["apiVersion"] = m.group(1).strip('"').strip("'")

    # metadata.name
    m = re.search(r"^metadata:\s*\n\s+name:\s*(\S+)", text, re.MULTILINE)
    if m:
        doc.setdefault("metadata", {})["name"] = m.group(1).strip('"').strip("'")

    # Check for key sections by presence
    doc["_has_resources_requests"] = bool(
        re.search(r"^\s+requests:\s*$", text, re.MULTILINE)
        and re.search(r"^\s+resources:\s*$", text, re.MULTILINE)
    )
    doc["_has_resources_limits"] = bool(
        re.search(r"^\s+limits:\s*$", text, re.MULTILINE)
        and re.search(r"^\s+resources:\s*$", text, re.MULTILINE)
    )
    doc["_has_liveness_probe"] = "livenessProbe" in text
    doc["_has_readiness_probe"] = "readinessProbe" in text
    doc["_has_security_context"] = "securityContext" in text
    doc["_has_run_as_non_root"] = "runAsNonRoot" in text

    # Extract image references
    images = re.findall(r"^\s+image:\s*[\"']?([^\s\"']+)", text, re.MULTILINE)
    doc["_images"] = images

    return doc


# ── Deep dictionary access helpers ────────────────────────────────────────


def deep_get(d: Any, *keys: str, default: Any = None) -> Any:
    """Get a nested value from a dictionary."""
    current = d
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current


def find_containers(doc: Dict) -> List[Dict]:
    """Find container specs in a K8s resource document."""
    containers = []
    kind = doc.get("kind", "")

    # Standard workload resources
    if kind in ("Deployment", "StatefulSet", "DaemonSet", "Job"):
        spec_template = deep_get(doc, "spec", "template", "spec", default={})
        containers.extend(spec_template.get("containers", []))
        containers.extend(spec_template.get("initContainers", []))
    elif kind == "Pod":
        pod_spec = deep_get(doc, "spec", default={})
        containers.extend(pod_spec.get("containers", []))
        containers.extend(pod_spec.get("initContainers", []))
    elif kind == "CronJob":
        job_spec = deep_get(
            doc, "spec", "jobTemplate", "spec", "template", "spec", default={}
        )
        containers.extend(job_spec.get("containers", []))
        containers.extend(job_spec.get("initContainers", []))

    return containers


def find_pod_spec(doc: Dict) -> Optional[Dict]:
    """Find the pod spec in a workload resource."""
    kind = doc.get("kind", "")
    if kind in ("Deployment", "StatefulSet", "DaemonSet", "Job"):
        return deep_get(doc, "spec", "template", "spec", default=None)
    elif kind == "Pod":
        return deep_get(doc, "spec", default=None)
    elif kind == "CronJob":
        return deep_get(
            doc, "spec", "jobTemplate", "spec", "template", "spec", default=None
        )
    return None


# ── Validation checks ─────────────────────────────────────────────────────

WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob", "Pod"}


def validate_document(
    doc: Dict, filepath: str, start_line: int
) -> List[Finding]:
    """Validate a single K8s document."""
    findings: List[Finding] = []
    kind = doc.get("kind", "")
    name = deep_get(doc, "metadata", "name", default="<unknown>")
    resource_label = f"{kind}/{name}"

    if kind not in WORKLOAD_KINDS:
        return findings  # Only validate workload resources

    # When using fallback parser, use extracted flags
    if "_images" in doc:
        return _validate_with_fallback(doc, filepath, start_line, resource_label)

    containers = find_containers(doc)
    pod_spec = find_pod_spec(doc)

    for container in containers:
        container_name = container.get("name", "<unnamed>")
        label = f"{resource_label} container '{container_name}'"

        # Check image tag
        image = container.get("image", "")
        if image:
            _check_image_tag(image, label, filepath, start_line, findings)

        # Check resource requests/limits
        resources = container.get("resources")
        if not resources:
            findings.append(
                (filepath, start_line, WARN,
                 f"{label}: No resources defined.\n"
                 f"  Set resources.requests and resources.limits for proper scheduling.")
            )
        else:
            if not resources.get("requests"):
                findings.append(
                    (filepath, start_line, WARN,
                     f"{label}: Missing resources.requests.\n"
                     f"  Set cpu and memory requests for proper pod scheduling.")
                )
            if not resources.get("limits"):
                findings.append(
                    (filepath, start_line, WARN,
                     f"{label}: Missing resources.limits.\n"
                     f"  Set cpu and memory limits to prevent resource exhaustion.")
                )

        # Check health probes (skip init containers)
        is_init = container in deep_get(
            doc, "spec", "template", "spec", "initContainers", default=[]
        )
        if not is_init:
            if not container.get("livenessProbe"):
                findings.append(
                    (filepath, start_line, WARN,
                     f"{label}: Missing livenessProbe.\n"
                     f"  Add a liveness probe to detect and restart stuck containers.")
                )
            if not container.get("readinessProbe"):
                findings.append(
                    (filepath, start_line, WARN,
                     f"{label}: Missing readinessProbe.\n"
                     f"  Add a readiness probe to avoid routing traffic to unready pods.")
                )

    # Check security context
    if pod_spec:
        pod_sc = pod_spec.get("securityContext", {})
        has_pod_run_as_non_root = pod_sc.get("runAsNonRoot", False) if pod_sc else False

        if not has_pod_run_as_non_root:
            # Check container-level security context
            has_any_security = False
            for container in find_containers(doc):
                container_sc = container.get("securityContext", {})
                if container_sc and container_sc.get("runAsNonRoot", False):
                    has_any_security = True
                    break

            if not has_any_security:
                findings.append(
                    (filepath, start_line, WARN,
                     f"{resource_label}: No runAsNonRoot in securityContext.\n"
                     f"  Add securityContext.runAsNonRoot: true to prevent running as root.")
                )

    return findings


def _validate_with_fallback(
    doc: Dict, filepath: str, start_line: int, resource_label: str
) -> List[Finding]:
    """Validate using fields extracted by fallback parser."""
    findings: List[Finding] = []

    # Check images
    for image in doc.get("_images", []):
        _check_image_tag(image, resource_label, filepath, start_line, findings)

    # Check resources
    if not doc.get("_has_resources_requests"):
        findings.append(
            (filepath, start_line, WARN,
             f"{resource_label}: No resources.requests found.\n"
             f"  Set cpu and memory requests for proper pod scheduling.")
        )
    if not doc.get("_has_resources_limits"):
        findings.append(
            (filepath, start_line, WARN,
             f"{resource_label}: No resources.limits found.\n"
             f"  Set cpu and memory limits to prevent resource exhaustion.")
        )

    # Check probes
    if not doc.get("_has_liveness_probe"):
        findings.append(
            (filepath, start_line, WARN,
             f"{resource_label}: No livenessProbe found.")
        )
    if not doc.get("_has_readiness_probe"):
        findings.append(
            (filepath, start_line, WARN,
             f"{resource_label}: No readinessProbe found.")
        )

    # Check security
    if not doc.get("_has_run_as_non_root"):
        findings.append(
            (filepath, start_line, WARN,
             f"{resource_label}: No runAsNonRoot in securityContext.")
        )

    return findings


def _check_image_tag(
    image: str,
    label: str,
    filepath: str,
    start_line: int,
    findings: List[Finding],
) -> None:
    """Check if an image uses a proper tag."""
    # Strip digest references
    if "@sha256:" in image:
        return  # Pinned by digest is fine

    if ":" not in image:
        findings.append(
            (filepath, start_line, WARN,
             f"{label}: Image '{image}' has no tag (defaults to :latest).\n"
             f"  Pin to a specific version for reproducible deployments.")
        )
    elif image.endswith(":latest"):
        findings.append(
            (filepath, start_line, ERROR,
             f"{label}: Image uses ':latest' tag: {image}\n"
             f"  Pin to a specific version for reproducible deployments.")
        )


# ── File discovery ────────────────────────────────────────────────────────


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


def is_k8s_manifest(content: str) -> bool:
    """Quick check if content looks like a K8s manifest."""
    return bool(
        re.search(r"^apiVersion:", content, re.MULTILINE)
        and re.search(r"^kind:", content, re.MULTILINE)
    )


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Kubernetes YAML manifests for common issues.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="File or directory path (default: current directory)",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Recursively scan directories",
    )
    args = parser.parse_args()

    path = os.path.abspath(args.path)

    if not os.path.exists(path):
        print(f"ERROR: Path not found: {path}", file=sys.stderr)
        return 1

    yaml_files = find_yaml_files(path, args.recursive)

    if not yaml_files:
        print(f"No YAML files found at {path}")
        return 0

    if not HAS_YAML:
        print("Note: PyYAML not installed. Using basic string parser (limited accuracy).\n")

    all_findings: List[Finding] = []
    manifests_checked = 0

    for filepath in yaml_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            print(f"WARN: Cannot read {filepath}: {e}", file=sys.stderr)
            continue

        if not is_k8s_manifest(content):
            continue

        documents = parse_yaml_documents(content, filepath)

        for start_line, doc in documents:
            if not doc or not isinstance(doc, dict):
                continue
            if doc.get("kind") not in WORKLOAD_KINDS:
                continue

            manifests_checked += 1
            findings = validate_document(doc, filepath, start_line)
            all_findings.extend(findings)

    if manifests_checked == 0:
        print(f"No Kubernetes workload manifests found in {len(yaml_files)} YAML file(s).")
        return 0

    if not all_findings:
        print(f"OK: No issues found in {manifests_checked} manifest(s) across {len(yaml_files)} file(s).")
        return 0

    # Report
    error_count = sum(1 for f in all_findings if f[2] == ERROR)
    warn_count = sum(1 for f in all_findings if f[2] == WARN)

    findings_by_file: dict = {}
    for filepath, line_num, severity, message in all_findings:
        rel_path = os.path.relpath(filepath, os.path.dirname(path) if os.path.isfile(path) else path)
        findings_by_file.setdefault(rel_path, []).append((line_num, severity, message))

    for rel_path, findings in findings_by_file.items():
        print(f"\n  {rel_path}:")
        for line_num, severity, message in findings:
            indented = message.replace("\n", "\n      ")
            print(f"    [{severity}] line ~{line_num}: {indented}")

    print(
        f"\nChecked {manifests_checked} manifest(s): "
        f"{error_count} error(s), {warn_count} warning(s)."
    )

    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
