#!/usr/bin/env python3
"""Validate message schemas for common issues.

Checks:
- JSON Schema validity and completeness
- Missing required fields (type, properties, description)
- Backward compatibility concerns
- Schema versioning presence
- Naming convention adherence
- Missing examples in schema definitions

Supports JSON Schema files used for message validation in event-driven systems.

Usage:
    python validate_schema.py schema.json
    python validate_schema.py schemas/
    python validate_schema.py --recursive events/
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

# Fields that should be present in a well-defined message schema
RECOMMENDED_ROOT_FIELDS = {"type", "properties", "description"}
RECOMMENDED_PROPERTY_FIELDS = {"type", "description"}


def load_schema(filepath: str) -> Tuple[Dict[str, Any] | None, str | None]:
    """Load a JSON schema file. Returns (schema, error)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        return None, f"Cannot read file: {e}"

    try:
        schema = json.loads(content)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"

    if not isinstance(schema, dict):
        return None, "Schema root must be an object"

    return schema, None


def validate_schema(schema: Dict[str, Any], filepath: str) -> List[Finding]:
    """Validate a single message schema."""
    findings: List[Finding] = []

    # Check for $schema reference
    if "$schema" not in schema:
        findings.append((
            filepath, 0, WARN,
            "Missing '$schema' field. Add a JSON Schema draft reference.\n"
            "  Example: \"$schema\": \"https://json-schema.org/draft/2020-12/schema\"",
        ))

    # Check root type
    root_type = schema.get("type")
    if not root_type:
        findings.append((
            filepath, 0, ERROR,
            "Missing 'type' at schema root. Message schemas should define a type (typically 'object').",
        ))
    elif root_type != "object":
        findings.append((
            filepath, 0, WARN,
            f"Root type is '{root_type}'. Message schemas typically use 'object' as root type.",
        ))

    # Check for title/description
    if not schema.get("title") and not schema.get("description"):
        findings.append((
            filepath, 0, WARN,
            "Missing 'title' and 'description'. Add at least one to document the schema purpose.",
        ))

    # Check properties
    properties = schema.get("properties", {})
    if root_type == "object" and not properties:
        findings.append((
            filepath, 0, ERROR,
            "Schema type is 'object' but no 'properties' defined.",
        ))

    # Check required fields list
    required = schema.get("required", [])
    if root_type == "object" and not required:
        findings.append((
            filepath, 0, WARN,
            "No 'required' fields defined. Consider specifying mandatory fields.",
        ))

    # Validate individual properties
    for prop_name, prop_def in properties.items():
        if not isinstance(prop_def, dict):
            continue
        _validate_property(prop_name, prop_def, filepath, findings, path_prefix="")

    # Check for common message metadata fields
    _check_message_metadata(properties, filepath, findings)

    # Check for additionalProperties
    if "additionalProperties" not in schema and root_type == "object":
        findings.append((
            filepath, 0, WARN,
            "No 'additionalProperties' setting. Consider setting to false "
            "for strict schema validation, or true with documentation.",
        ))

    # Check schema versioning
    _check_versioning(schema, filepath, findings)

    return findings


def _validate_property(
    name: str,
    prop_def: Dict,
    filepath: str,
    findings: List[Finding],
    path_prefix: str,
) -> None:
    """Validate a single property definition."""
    prop_path = f"{path_prefix}.{name}" if path_prefix else name

    if "type" not in prop_def and "$ref" not in prop_def and "oneOf" not in prop_def \
       and "anyOf" not in prop_def and "allOf" not in prop_def:
        findings.append((
            filepath, 0, WARN,
            f"Property '{prop_path}' has no 'type' or schema reference defined.",
        ))

    if not prop_def.get("description"):
        findings.append((
            filepath, 0, WARN,
            f"Property '{prop_path}' missing 'description'.",
        ))

    # Check for example
    if "example" not in prop_def and "examples" not in prop_def \
       and "default" not in prop_def and "const" not in prop_def:
        prop_type = prop_def.get("type", "")
        if prop_type not in ("object", "array"):
            findings.append((
                filepath, 0, WARN,
                f"Property '{prop_path}' missing 'example'. "
                f"Examples help consumers understand expected values.",
            ))

    # Check string constraints
    if prop_def.get("type") == "string":
        if not any(k in prop_def for k in ("format", "pattern", "enum", "minLength", "maxLength", "const")):
            findings.append((
                filepath, 0, WARN,
                f"String property '{prop_path}' has no format, pattern, or enum constraint.\n"
                f"  Consider adding validation constraints.",
            ))

    # Recurse into nested object properties
    if prop_def.get("type") == "object" and "properties" in prop_def:
        for nested_name, nested_def in prop_def["properties"].items():
            if isinstance(nested_def, dict):
                _validate_property(nested_name, nested_def, filepath, findings, prop_path)

    # Check array items
    if prop_def.get("type") == "array":
        items = prop_def.get("items")
        if not items:
            findings.append((
                filepath, 0, WARN,
                f"Array property '{prop_path}' has no 'items' schema defined.",
            ))


def _check_message_metadata(
    properties: Dict, filepath: str, findings: List[Finding]
) -> None:
    """Check for common message metadata fields."""
    metadata_fields = {
        "event_type": "Event type identifier for routing and filtering",
        "timestamp": "Event timestamp for ordering and deduplication",
        "version": "Schema version for backward compatibility",
    }

    # Only check if it looks like an event/message schema
    has_any_metadata = any(
        k in properties for k in ("event_type", "eventType", "type", "timestamp", "version")
    )

    if not has_any_metadata and len(properties) > 2:
        missing = []
        for field, purpose in metadata_fields.items():
            camel = re.sub(r"_(\w)", lambda m: m.group(1).upper(), field)
            if field not in properties and camel not in properties:
                missing.append(f"  - {field}: {purpose}")

        if missing:
            findings.append((
                filepath, 0, WARN,
                "Consider adding message metadata fields:\n" + "\n".join(missing),
            ))


def _check_versioning(
    schema: Dict, filepath: str, findings: List[Finding]
) -> None:
    """Check if schema includes versioning information."""
    has_version = (
        "version" in schema
        or "schemaVersion" in schema
        or "$id" in schema
    )

    if not has_version:
        findings.append((
            filepath, 0, WARN,
            "No schema versioning found. Add a 'version' field or '$id' with version.\n"
            "  Versioned schemas enable backward-compatible evolution.",
        ))


def find_schema_files(path: str, recursive: bool) -> List[str]:
    """Find JSON schema files."""
    if os.path.isfile(path):
        return [path]

    if not os.path.isdir(path):
        return []

    files = []
    if recursive:
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for filename in filenames:
                if filename.endswith(".json"):
                    files.append(os.path.join(dirpath, filename))
    else:
        for filename in os.listdir(path):
            if filename.endswith(".json"):
                files.append(os.path.join(path, filename))

    return sorted(files)


def is_json_schema(data: Dict) -> bool:
    """Check if a JSON file looks like a JSON Schema."""
    schema_indicators = {"$schema", "type", "properties", "definitions", "$defs", "items"}
    return bool(schema_indicators & set(data.keys()))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate message schemas for common issues.",
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

    json_files = find_schema_files(path, args.recursive)
    if not json_files:
        print(f"No JSON files found at {path}")
        return 0

    all_findings: List[Finding] = []
    schemas_checked = 0

    for filepath in json_files:
        schema, error = load_schema(filepath)
        if error:
            all_findings.append((filepath, 0, ERROR, error))
            continue

        if not is_json_schema(schema):
            continue

        schemas_checked += 1
        all_findings.extend(validate_schema(schema, filepath))

    if schemas_checked == 0:
        print(f"No JSON Schema files found in {len(json_files)} JSON file(s).")
        return 0

    if not all_findings:
        print(f"OK: No issues found in {schemas_checked} schema(s).")
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
            indented = message.replace("\n", "\n      ")
            print(f"    [{severity}] {indented}")

    print(f"\nChecked {schemas_checked} schema(s): {error_count} error(s), {warn_count} warning(s).")
    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
