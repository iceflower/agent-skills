#!/usr/bin/env python3
"""Validate OpenAPI/Swagger specification files for completeness.

Checks for common issues:
  - Missing description on endpoints
  - Missing examples in schemas
  - Missing operationId
  - Undocumented error responses (no 4xx/5xx)
  - Missing security scheme
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Tuple


def load_spec(file_path: str) -> Dict[str, Any]:
    """Load an OpenAPI spec from JSON or YAML file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Try JSON first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try PyYAML if available
    try:
        import yaml
        return yaml.safe_load(content)
    except ImportError:
        pass

    # Fallback: simple YAML-like parsing for common structures
    return _simple_yaml_parse(content)


def _simple_yaml_parse(content: str) -> Dict[str, Any]:
    """Minimal YAML parser for OpenAPI specs.

    Handles basic key-value pairs and nested structures.  This is a
    best-effort fallback when PyYAML is not installed.
    """
    result: Dict[str, Any] = {}
    stack: List[Tuple[int, dict]] = [(-1, result)]
    prev_key = None

    for line in content.splitlines():
        stripped = line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        content_part = stripped.lstrip()

        # Pop stack to find parent at correct indentation
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()

        current_dict = stack[-1][1]

        if ":" in content_part:
            key, _, value = content_part.partition(":")
            key = key.strip().strip('"').strip("'")
            value = value.strip()

            if value:
                # Remove surrounding quotes
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                # Booleans
                if value.lower() == "true":
                    current_dict[key] = True
                elif value.lower() == "false":
                    current_dict[key] = False
                # Numbers
                elif value.isdigit():
                    current_dict[key] = int(value)
                # Arrays as string
                elif value.startswith("["):
                    current_dict[key] = value
                else:
                    current_dict[key] = value
                prev_key = key
            else:
                new_dict: Dict[str, Any] = {}
                current_dict[key] = new_dict
                stack.append((indent, new_dict))
                prev_key = key
        elif content_part.startswith("- "):
            # List item: attach to previous key in parent
            if prev_key and isinstance(current_dict.get(prev_key), dict):
                pass  # Skip complex list items in simple parser
            elif prev_key:
                if not isinstance(current_dict.get(prev_key), list):
                    current_dict[prev_key] = []
                item = content_part[2:].strip().strip('"').strip("'")
                current_dict[prev_key].append(item)

    return result


class Finding:
    """Represents a single validation finding."""

    def __init__(self, path: str, message: str, severity: str = "WARNING"):
        self.path = path
        self.message = message
        self.severity = severity

    def __str__(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"


def validate_spec(spec: Dict[str, Any], file_path: str) -> List[Finding]:
    """Run all validation checks on the spec."""
    findings: List[Finding] = []

    _check_info(spec, file_path, findings)
    _check_security_schemes(spec, file_path, findings)
    _check_paths(spec, file_path, findings)
    _check_schemas(spec, file_path, findings)

    return findings


def _check_info(spec: Dict[str, Any], fp: str, findings: List[Finding]) -> None:
    info = spec.get("info", {})
    if not info.get("description"):
        findings.append(Finding(f"{fp}:info", "Missing API description in info block"))
    if not info.get("version"):
        findings.append(Finding(f"{fp}:info", "Missing API version in info block"))


def _check_security_schemes(spec: Dict[str, Any], fp: str, findings: List[Finding]) -> None:
    components = spec.get("components", {})
    security_schemes = components.get("securitySchemes", {})
    global_security = spec.get("security")

    if not security_schemes:
        findings.append(Finding(
            f"{fp}:components.securitySchemes",
            "No security schemes defined",
            "WARNING",
        ))

    if not global_security and security_schemes:
        findings.append(Finding(
            f"{fp}:security",
            "Security schemes defined but no global security requirement set",
            "INFO",
        ))


def _check_paths(spec: Dict[str, Any], fp: str, findings: List[Finding]) -> None:
    paths = spec.get("paths", {})
    if not paths:
        findings.append(Finding(f"{fp}:paths", "No paths defined in spec"))
        return

    http_methods = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        for method in http_methods:
            operation = path_item.get(method)
            if operation is None:
                continue

            op_path = f"{fp}:paths.{path}.{method}"

            # Missing operationId
            if not operation.get("operationId"):
                findings.append(Finding(op_path, "Missing operationId"))

            # Missing summary or description
            if not operation.get("summary") and not operation.get("description"):
                findings.append(Finding(op_path, "Missing summary and description"))

            # Check responses
            responses = operation.get("responses", {})
            if not responses:
                findings.append(Finding(op_path, "No responses defined"))
                continue

            # Check for error responses
            has_4xx = any(str(code).startswith("4") for code in responses)
            has_5xx = any(str(code).startswith("5") for code in responses)

            if not has_4xx:
                findings.append(Finding(
                    op_path,
                    "No 4xx error responses documented",
                    "WARNING",
                ))

            if not has_5xx and method in ("post", "put", "patch", "delete"):
                findings.append(Finding(
                    op_path,
                    "No 5xx error responses documented for mutating operation",
                    "INFO",
                ))

            # Check each response for description
            for code, resp in responses.items():
                if isinstance(resp, dict) and not resp.get("description"):
                    findings.append(Finding(
                        f"{op_path}.responses.{code}",
                        "Response missing description",
                    ))

            # Check parameters for description/example
            for param in operation.get("parameters", []):
                if isinstance(param, dict):
                    param_name = param.get("name", "unknown")
                    if not param.get("description"):
                        findings.append(Finding(
                            f"{op_path}.parameters.{param_name}",
                            f"Parameter '{param_name}' missing description",
                            "INFO",
                        ))
                    schema = param.get("schema", {})
                    if isinstance(schema, dict) and not param.get("example") and not schema.get("example"):
                        findings.append(Finding(
                            f"{op_path}.parameters.{param_name}",
                            f"Parameter '{param_name}' missing example",
                            "INFO",
                        ))


def _check_schemas(spec: Dict[str, Any], fp: str, findings: List[Finding]) -> None:
    components = spec.get("components", {})
    schemas = components.get("schemas", {})

    for schema_name, schema_def in schemas.items():
        if not isinstance(schema_def, dict):
            continue

        schema_path = f"{fp}:components.schemas.{schema_name}"

        if not schema_def.get("description"):
            findings.append(Finding(
                schema_path,
                f"Schema '{schema_name}' missing description",
                "INFO",
            ))

        properties = schema_def.get("properties", {})
        for prop_name, prop_def in properties.items():
            if not isinstance(prop_def, dict):
                continue

            prop_path = f"{schema_path}.properties.{prop_name}"

            if not prop_def.get("description"):
                findings.append(Finding(
                    prop_path,
                    f"Property '{prop_name}' missing description",
                    "INFO",
                ))

            if not prop_def.get("example") and prop_def.get("type") != "object":
                findings.append(Finding(
                    prop_path,
                    f"Property '{prop_name}' missing example",
                    "INFO",
                ))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate OpenAPI/Swagger specification files for completeness.",
        epilog="Supports JSON and YAML formats. Exit code 0 = clean, 1 = findings.",
    )
    parser.add_argument(
        "file",
        help="Path to the OpenAPI spec file (JSON or YAML)",
    )
    parser.add_argument(
        "--severity",
        choices=["INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Minimum severity to report (default: INFO)",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    try:
        spec = load_spec(args.file)
    except Exception as e:
        print(f"Error: Failed to parse spec file: {e}", file=sys.stderr)
        return 1

    if not isinstance(spec, dict):
        print("Error: Spec file does not contain a valid object/mapping.", file=sys.stderr)
        return 1

    findings = validate_spec(spec, args.file)

    # Filter by severity
    severity_order = {"INFO": 0, "WARNING": 1, "ERROR": 2}
    min_level = severity_order.get(args.severity, 0)
    filtered = [f for f in findings if severity_order.get(f.severity, 0) >= min_level]

    if not filtered:
        print(f"OK: No issues found in {args.file}")
        return 0

    for finding in filtered:
        print(finding)

    print(f"\nTotal: {len(filtered)} issue(s) found")
    return 1


if __name__ == "__main__":
    sys.exit(main())
