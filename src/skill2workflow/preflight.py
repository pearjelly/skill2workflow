"""Side-effect-free trigger preflight for Workflow DSL documents.

Preflight answers the operator question “can this input start this workflow?”
without executing a node, resolving a credential, persisting state, or
including trigger values in the result.  The result is deliberately smaller
and stricter than the execution runtime: it is an admission hint, never a
second execution authority.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Sequence

from .compiler import validate_workflow_structured
from .input_schema import InputSchemaValidationError, validate_trigger_input


WORKFLOW_PREFLIGHT_SCHEMA_VERSION = "skill2workflow-workflow-preflight-0.1.0"
WORKFLOW_RELEASE_PREFLIGHT_SCHEMA_VERSION = (
    "skill2workflow-workflow-release-preflight-0.1.0"
)
MAX_WORKFLOW_PREFLIGHT_BYTES = 64 * 1024
MAX_WORKFLOW_PREFLIGHT_NODES = 1000
MAX_WORKFLOW_PREFLIGHT_MAPPINGS = 2000
MAX_WORKFLOW_PREFLIGHT_INPUT_KEYS = 128
MAX_WORKFLOW_PREFLIGHT_ISSUES = 64


def build_workflow_preflight(
    workflow: Dict[str, object],
    input_value: Optional[Dict[str, object]] = None,
    *,
    input_present: bool = False,
) -> Dict[str, object]:
    """Build a deterministic, value-free trigger admission report.

    ``input_present=False`` uses an empty object for validation while making
    the distinction visible in the report.  This lets operators check a
    workflow contract before they have a trigger payload.
    """

    if not isinstance(workflow, dict):
        raise ValueError("workflow document must be a JSON object")
    errors = validate_workflow_structured(workflow)
    if errors:
        raise ValueError(str(errors[0]["message"]))
    raw_nodes = workflow.get("nodes", [])
    if not isinstance(raw_nodes, list):  # validator already reports this.
        raise ValueError("workflow.nodes must be a list")
    if len(raw_nodes) > MAX_WORKFLOW_PREFLIGHT_NODES:
        raise ValueError(
            "workflow preflight supports at most "
            f"{MAX_WORKFLOW_PREFLIGHT_NODES} nodes"
        )
    if input_present and not isinstance(input_value, dict):
        raise ValueError("preflight input must be a JSON object")
    effective_input: Dict[str, object] = input_value if input_present else {}
    if len(effective_input) > MAX_WORKFLOW_PREFLIGHT_INPUT_KEYS:
        raise ValueError(
            "preflight input must contain at most "
            f"{MAX_WORKFLOW_PREFLIGHT_INPUT_KEYS} top-level properties"
        )
    try:
        json.dumps(effective_input, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ValueError("preflight input must be finite JSON") from error

    input_report = _input_report(workflow.get("input_schema"), effective_input, input_present)
    issues: List[Dict[str, object]] = []
    if input_report["status"] != "valid":
        issues.append(
            {
                "code": "input_invalid",
                "severity": "error",
                "node_id": None,
                "path": list(input_report["error_path"] or ["input"]),
            }
        )

    nodes: List[Dict[str, object]] = []
    mapping_count = 0
    blocked_node_count = 0
    connector_node_count = 0
    side_effecting_node_count = 0
    for raw_node in raw_nodes:
        node = _node_preflight(raw_node, effective_input)
        nodes.append(node)
        connector = node["connector"]
        if connector is not None:
            connector_node_count += 1
            if connector["external_side_effect"]:
                side_effecting_node_count += 1
        mapping = node["input_mapping"]
        mapping_count += mapping["mapping_count"]
        if mapping["status"] == "blocked":
            blocked_node_count += 1
            for index in mapping["missing_required_indexes"]:
                if len(issues) >= MAX_WORKFLOW_PREFLIGHT_ISSUES:
                    break
                issues.append(
                    {
                        "code": "required_mapping_input_missing",
                        "severity": "error",
                        "node_id": node["id"],
                        "path": ["connector", "request", "input_mapping", index, "from"],
                    }
                )

    for node in nodes:
        node["input_mapping"].pop("missing_required_indexes", None)
        node["input_mapping"].pop("missing_optional_indexes", None)

    metadata = workflow.get("workflow")
    if not isinstance(metadata, dict):
        raise ValueError("workflow.workflow must be an object")
    result: Dict[str, object] = {
        "schema_version": WORKFLOW_PREFLIGHT_SCHEMA_VERSION,
        "workflow": {
            "id": str(metadata.get("id", "")),
            "version": str(metadata.get("version", "")),
            "status": str(metadata.get("status", "")),
        },
        "ready": input_report["status"] == "valid" and not issues,
        "input": {
            key: value for key, value in input_report.items()
        },
        "summary": {
            "node_count": len(nodes),
            "connector_node_count": connector_node_count,
            "side_effecting_node_count": side_effecting_node_count,
            "mapping_count": mapping_count,
            "blocked_node_count": blocked_node_count,
            "issue_count": len(issues),
        },
        "nodes": nodes,
        "issues": issues,
        "safety": {
            "side_effect_free": True,
            "connector_calls": False,
            "credentials_resolved": False,
            "raw_values_included": False,
        },
    }
    _check_size(result)
    return result


def build_workflow_release_preflight(workflow: Dict[str, object]) -> Dict[str, object]:
    """Validate one unpublished Workflow DSL document without storing it.

    The release preflight deliberately reuses the execution preflight's
    structural validation and value-free mapping analysis, but it is not an
    execution admission result: a document with required trigger input remains
    publishable even when its *empty* trigger is blocked.
    """

    report = build_workflow_preflight(workflow)
    metadata = report["workflow"]
    result: Dict[str, object] = {
        "schema_version": WORKFLOW_RELEASE_PREFLIGHT_SCHEMA_VERSION,
        "workflow": {
            "id": metadata["id"],
            "version": metadata["version"],
        },
        "document_valid": True,
        "empty_trigger_ready": report["ready"],
        "summary": report["summary"],
        "issues": report["issues"],
        "safety": report["safety"],
    }
    _check_size(result)
    return result


def render_workflow_preflight_text(preflight: Dict[str, object]) -> str:
    """Render a compact operator summary without trigger values."""

    workflow = preflight["workflow"]
    input_report = preflight["input"]
    summary = preflight["summary"]
    lines = [
        "READY" if preflight["ready"] else "BLOCKED",
        "Workflow {}@{} ({})".format(
            workflow["id"], workflow["version"], workflow["status"]
        ),
        "input: {} (provided={}; properties={}; missing_required={}; unknown={})".format(
            input_report["status"],
            str(input_report["provided"]).lower(),
            input_report["provided_property_count"],
            input_report["missing_required_count"],
            input_report["unknown_property_count"],
        ),
        "nodes: {}; connectors: {}; side effects: {}; mappings: {}; blocked nodes: {}".format(
            summary["node_count"],
            summary["connector_node_count"],
            summary["side_effecting_node_count"],
            summary["mapping_count"],
            summary["blocked_node_count"],
        ),
    ]
    for node in preflight["nodes"]:
        mapping = node["input_mapping"]
        lines.append(
            "- {} [{}]; mapping={} ({}/{})".format(
                node["id"],
                node["type"],
                mapping["status"],
                mapping["mapped_count"],
                mapping["mapping_count"],
            )
        )
    if preflight["issues"]:
        lines.append("issues:")
        for issue in preflight["issues"]:
            lines.append("- {} ({})".format(issue["code"], issue["severity"]))
    return "\n".join(lines) + "\n"


def _input_report(schema: object, value: Dict[str, object], provided: bool) -> Dict[str, object]:
    properties: Dict[str, object] = {}
    required: List[str] = []
    additional_properties = True
    if isinstance(schema, dict):
        raw_properties = schema.get("properties")
        if isinstance(raw_properties, dict):
            properties = raw_properties
        raw_required = schema.get("required")
        if isinstance(raw_required, list):
            required = [name for name in raw_required if isinstance(name, str)]
        if isinstance(schema.get("additionalProperties"), bool):
            additional_properties = bool(schema["additionalProperties"])
    missing = sorted(name for name in required if name not in value)
    unknown = sorted(set(value) - set(properties)) if not additional_properties else []
    status = "valid"
    error_code = None
    error_path = None
    if schema is not None:
        try:
            validate_trigger_input(schema, value)
        except InputSchemaValidationError as error:
            status = "invalid"
            error_code = str(error.code)
            error_path = _safe_path(error.path)
    return {
        "provided": bool(provided),
        "status": status,
        "provided_property_count": len(value),
        "declared_property_count": len(properties),
        "required_property_count": len(required),
        "missing_required_count": len(missing),
        "unknown_property_count": len(unknown),
        "error_code": error_code,
        "error_path": error_path,
    }


def _node_preflight(node: Dict[str, object], input_value: Dict[str, object]) -> Dict[str, object]:
    connector_value = node.get("connector")
    connector = None
    if isinstance(connector_value, dict):
        credentials = connector_value.get("credentials")
        credential_count = len(credentials) if isinstance(credentials, list) else 0
        connector = {
            "id": str(connector_value.get("id", "")),
            "kind": str(connector_value.get("kind", "")),
            "external_side_effect": bool(node.get("type") == "tool_call"),
            "credential_handle_count": credential_count,
            "credentials_resolved": False,
        }
    mapping = _mapping_report(connector_value, input_value)
    return {
        "id": str(node.get("id", "")),
        "type": str(node.get("type", "")),
        "connector": connector,
        "input_mapping": mapping,
    }


def _mapping_report(connector: object, input_value: Dict[str, object]) -> Dict[str, object]:
    if not isinstance(connector, dict):
        return {
            "status": "not_applicable",
            "mapping_count": 0,
            "mapped_count": 0,
            "missing_required_count": 0,
            "missing_optional_count": 0,
            "missing_required_indexes": [],
            "missing_optional_indexes": [],
        }
    request = connector.get("request")
    mappings = request.get("input_mapping") if isinstance(request, dict) else None
    if not mappings:
        return {
            "status": "not_applicable",
            "mapping_count": 0,
            "mapped_count": 0,
            "missing_required_count": 0,
            "missing_optional_count": 0,
            "missing_required_indexes": [],
            "missing_optional_indexes": [],
        }
    if not isinstance(mappings, list):
        raise ValueError("workflow preflight input mappings must be a list")
    if len(mappings) > MAX_WORKFLOW_PREFLIGHT_MAPPINGS:
        raise ValueError(
            "workflow preflight supports at most "
            f"{MAX_WORKFLOW_PREFLIGHT_MAPPINGS} input mappings per node"
        )
    root = {"input": input_value}
    missing_required: List[int] = []
    missing_optional: List[int] = []
    mapped = 0
    for index, mapping in enumerate(mappings):
        if not isinstance(mapping, dict):
            continue
        present = _json_pointer_get(root, mapping.get("from", ""))
        if present is _MISSING:
            (missing_required if mapping.get("required", True) else missing_optional).append(index)
        else:
            mapped += 1
    status = "blocked" if missing_required else ("skipped" if missing_optional else "ready")
    return {
        "status": status,
        "mapping_count": len(mappings),
        "mapped_count": mapped,
        "missing_required_count": len(missing_required),
        "missing_optional_count": len(missing_optional),
        "missing_required_indexes": missing_required,
        "missing_optional_indexes": missing_optional,
    }


_MISSING = object()


def _json_pointer_get(root: object, pointer: object) -> object:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        return _MISSING
    current = root
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                return _MISSING
            current = current[token]
        elif isinstance(current, list) and token.isdigit():
            index = int(token)
            if index >= len(current):
                return _MISSING
            current = current[index]
        else:
            return _MISSING
    return current


def _safe_path(path: Sequence[object]) -> List[object]:
    safe: List[object] = []
    for part in list(path)[:16]:
        if isinstance(part, bool):
            safe.append(int(part))
        elif isinstance(part, int):
            safe.append(max(0, min(part, 1000000)))
        else:
            text = str(part)
            safe.append(text[:128])
    return safe or ["input"]


def _check_size(result: Dict[str, object]) -> None:
    compact = json.dumps(
        result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    pretty = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    if len(compact) > MAX_WORKFLOW_PREFLIGHT_BYTES or len(pretty) > MAX_WORKFLOW_PREFLIGHT_BYTES:
        raise ValueError(
            "workflow preflight exceeds " f"{MAX_WORKFLOW_PREFLIGHT_BYTES} bytes"
        )
