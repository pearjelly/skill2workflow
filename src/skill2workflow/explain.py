"""Bounded, side-effect-free workflow execution explanations.

The explanation is an operator view, not another execution authority.  It
contains topology and policy metadata only; connector request values,
instructions, headers, URLs, credentials, and trigger values are deliberately
not copied into the result.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

from .compiler import validate_workflow_structured


WORKFLOW_EXPLANATION_SCHEMA_VERSION = "skill2workflow-workflow-explanation-0.1.0"
MAX_WORKFLOW_EXPLANATION_BYTES = 64 * 1024
MAX_WORKFLOW_EXPLANATION_NODES = 1000
MAX_WORKFLOW_EXPLANATION_EDGES = 2000
MAX_WORKFLOW_EXPLANATION_INPUT_PROPERTIES = 128


def build_workflow_explanation(workflow: Dict[str, object]) -> Dict[str, object]:
    """Build a deterministic redacted plan for a valid Workflow DSL document."""

    if not isinstance(workflow, dict):
        raise ValueError("workflow document must be a JSON object")
    errors = validate_workflow_structured(workflow)
    if errors:
        raise ValueError(str(errors[0]["message"]))

    raw_nodes = workflow.get("nodes", [])
    raw_edges = workflow.get("edges", [])
    if len(raw_nodes) > MAX_WORKFLOW_EXPLANATION_NODES:
        raise ValueError(
            "workflow explanation supports at most "
            f"{MAX_WORKFLOW_EXPLANATION_NODES} nodes"
        )
    if len(raw_edges) > MAX_WORKFLOW_EXPLANATION_EDGES:
        raise ValueError(
            "workflow explanation supports at most "
            f"{MAX_WORKFLOW_EXPLANATION_EDGES} edges"
        )

    metadata = workflow.get("workflow")
    if not isinstance(metadata, dict):  # validator already reports this; keep typing narrow.
        raise ValueError("workflow.workflow must be an object")
    policies = workflow.get("policies")
    if not isinstance(policies, dict):
        policies = {}

    nodes = [_node_explanation(node, policies) for node in raw_nodes]
    edges = [_edge_explanation(edge) for edge in raw_edges]
    input_contract = _input_contract(workflow.get("input_schema"))
    connector_count = sum(1 for node in nodes if node["connector"] is not None)
    side_effect_count = sum(
        1 for node in nodes if node["external_side_effect"]
    )
    summary = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "human_gate_count": sum(1 for node in nodes if node["type"] == "human_gate"),
        "connector_node_count": connector_count,
        "side_effecting_node_count": side_effect_count,
        "terminal_node_count": sum(
            1 for node in nodes if node["type"] in {"end", "failure"}
        ),
        "retrying_node_count": sum(
            1 for node in nodes if node["retry"]["max_attempts"] > 0
        ),
        "timed_node_count": sum(
            1
            for node in nodes
            if node["timeout_ms"] is not None and node["timeout_ms"] > 0
        ),
        "input_property_count": len(input_contract["properties"]),
        "required_input_count": len(input_contract["required"]),
    }
    result: Dict[str, object] = {
        "schema_version": WORKFLOW_EXPLANATION_SCHEMA_VERSION,
        "workflow": {
            "id": str(metadata.get("id", "")),
            "version": str(metadata.get("version", "")),
            "status": str(metadata.get("status", "")),
        },
        "entry": str(workflow.get("entry", "")),
        "summary": summary,
        "nodes": nodes,
        "edges": edges,
        "input_contract": input_contract,
        "policies": _policy_explanation(policies),
        "safety": {
            "side_effect_free": True,
            "connector_calls": False,
            "credentials_resolved": False,
            "raw_values_included": False,
        },
    }
    encoded = json.dumps(
        result,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(encoded) > MAX_WORKFLOW_EXPLANATION_BYTES:
        raise ValueError(
            "workflow explanation exceeds "
            f"{MAX_WORKFLOW_EXPLANATION_BYTES} bytes"
        )
    pretty_encoded = json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    ).encode("utf-8")
    if len(pretty_encoded) > MAX_WORKFLOW_EXPLANATION_BYTES:
        raise ValueError(
            "workflow explanation exceeds "
            f"{MAX_WORKFLOW_EXPLANATION_BYTES} bytes"
        )
    return result


def render_workflow_explanation_text(explanation: Dict[str, object]) -> str:
    """Render the fixed explanation contract as a compact operator summary."""

    workflow = explanation["workflow"]
    summary = explanation["summary"]
    lines = [
        "Workflow {}@{} ({})".format(
            workflow["id"], workflow["version"], workflow["status"]
        ),
        "entry: {}".format(explanation["entry"]),
        "nodes: {}; edges: {}; human gates: {}; external side effects: {}".format(
            summary["node_count"],
            summary["edge_count"],
            summary["human_gate_count"],
            summary["side_effecting_node_count"],
        ),
        "inputs: {} properties ({} required)".format(
            summary["input_property_count"], summary["required_input_count"]
        ),
        "nodes:",
    ]
    for node in explanation["nodes"]:
        transitions = node["transitions"]
        transition_text = ", ".join(
            "{}={}".format(key, value)
            for key, value in transitions.items()
            if value is not None
        ) or "terminal"
        connector = node["connector"]
        connector_text = ""
        if connector is not None:
            connector_text = " connector={}".format(connector["id"])
        lines.append(
            "- {} [{}]{}; {}".format(
                node["id"], node["type"], connector_text, transition_text
            )
        )
    return "\n".join(lines) + "\n"


def _node_explanation(node: Dict[str, object], policies: Dict[str, object]) -> Dict[str, object]:
    connector = _connector_explanation(node.get("connector"))
    retry = node.get("retry")
    if not isinstance(retry, dict):
        retry = policies.get("default_retry")
    if not isinstance(retry, dict):
        retry = {}
    timeout = node.get("timeout_ms")
    if timeout is not None and (isinstance(timeout, bool) or not isinstance(timeout, int)):
        timeout = None
    return {
        "id": str(node.get("id", "")),
        "type": str(node.get("type", "")),
        "transitions": {
            "success": _optional_string(node.get("on_success")),
            "failure": _optional_string(node.get("on_failure")),
            "fallback": _optional_string(node.get("on_fallback")),
        },
        "connector": connector,
        "external_side_effect": bool(
            node.get("type") == "tool_call" and connector is not None
        ),
        "retry": {
            "max_attempts": _nonnegative_int(retry.get("max_attempts"), 0),
            "backoff_ms": _nonnegative_int(retry.get("backoff_ms"), 0),
        },
        "timeout_ms": timeout,
    }


def _connector_explanation(value: object) -> Optional[Dict[str, object]]:
    if value is None:
        return None
    if not isinstance(value, dict):
        return {"id": "", "kind": "", "method": "", "credential_handle_count": 0, "input_mapping_count": 0, "external_side_effect": False}
    request = value.get("request")
    if not isinstance(request, dict):
        request = {}
    credentials = value.get("credentials")
    if not isinstance(credentials, list):
        credentials = []
    mappings = request.get("input_mapping")
    if not isinstance(mappings, list):
        mappings = []
    method = request.get("method", "")
    if not isinstance(method, str):
        method = ""
    return {
        "id": str(value.get("id", "")),
        "kind": str(value.get("kind", "")),
        "method": method.upper() if method else "",
        "credential_handle_count": len(credentials),
        "input_mapping_count": len(mappings),
        "external_side_effect": True,
    }


def _edge_explanation(edge: Dict[str, object]) -> Dict[str, object]:
    label = edge.get("label")
    if label not in {"next", "failure", "fallback"}:
        label = "custom" if label is not None else None
    return {
        "from": str(edge.get("from", "")),
        "to": str(edge.get("to", "")),
        "label": label,
        "conditioned": edge.get("condition") is not None,
    }


def _input_contract(schema: object) -> Dict[str, object]:
    if not isinstance(schema, dict):
        return {
            "present": False,
            "type": "object",
            "required": [],
            "properties": [],
            "additional_properties": True,
        }
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        properties = {}
    if len(properties) > MAX_WORKFLOW_EXPLANATION_INPUT_PROPERTIES:
        raise ValueError(
            "workflow explanation supports at most "
            f"{MAX_WORKFLOW_EXPLANATION_INPUT_PROPERTIES} input properties"
        )
    required = schema.get("required")
    if not isinstance(required, list):
        required = []
    required_set = {str(name) for name in required}
    summarized = []
    for name in sorted(properties):
        child = properties[name]
        child_type = child.get("type", "") if isinstance(child, dict) else ""
        nested = bool(
            isinstance(child, dict)
            and (
                isinstance(child.get("properties"), dict)
                or isinstance(child.get("items"), dict)
            )
        )
        summarized.append({
            "name": str(name),
            "type": str(child_type),
            "required": str(name) in required_set,
            "nested": nested,
        })
    return {
        "present": True,
        "type": str(schema.get("type", "object")),
        "required": sorted(required_set),
        "properties": summarized,
        "additional_properties": bool(schema.get("additionalProperties", True)),
    }


def _policy_explanation(policies: Dict[str, object]) -> Dict[str, object]:
    retry = policies.get("default_retry")
    if not isinstance(retry, dict):
        retry = {}
    workflow_timeout = policies.get("workflow_timeout_ms")
    if isinstance(workflow_timeout, bool) or not isinstance(workflow_timeout, int):
        workflow_timeout = None
    default_timeout = policies.get("default_timeout_ms")
    if isinstance(default_timeout, bool) or not isinstance(default_timeout, int):
        default_timeout = None
    return {
        "default_retry": {
            "max_attempts": _nonnegative_int(retry.get("max_attempts"), 0),
            "backoff_ms": _nonnegative_int(retry.get("backoff_ms"), 0),
        },
        "default_timeout_ms": default_timeout,
        "workflow_timeout_ms": workflow_timeout,
    }


def _optional_string(value: object) -> Optional[str]:
    return str(value) if isinstance(value, str) else None


def _nonnegative_int(value: object, default: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return default
