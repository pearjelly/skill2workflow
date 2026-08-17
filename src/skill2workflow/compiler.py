"""Compile Skill IR into executable Workflow DSL."""

from __future__ import annotations

import re
from typing import Dict, List, Set

from .connectors import default_connector_binding
from .input_schema import validate_input_schema_contract

Workflow = Dict[str, object]
ValidationError = Dict[str, object]
_TRANSITION_KEYS = ("on_success", "on_failure", "on_fallback")


def compile_ir_to_workflow(ir: Dict[str, object]) -> Workflow:
    """Compile Skill IR into the initial skill2workflow DSL."""
    metadata = ir.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    name = str(metadata.get("name") or "skill-workflow")
    description = str(metadata.get("description") or ir.get("description") or "")
    steps = _step_records_from_ir(ir)
    if not steps:
        steps = [
            {
                "title": "Review skill guidance",
                "detail": "",
                "line": None,
                "section": None,
                "index": 1,
            }
        ]

    workflow_id = f"workflow_{_slugify(name)}"
    nodes: List[Dict[str, object]] = [
        {
            "id": "start",
            "type": "start",
            "title": "Start",
            "description": "Workflow entry point.",
        }
    ]

    step_ids = []
    for index, step in enumerate(steps, start=1):
        title = str(step["title"])
        detail = str(step.get("detail") or "")
        node_id = f"node_{index:03d}_{_slugify(title)}"
        node_type = _node_type_for_step(f"{title} {detail}")
        step_ids.append(node_id)
        source = {
            "file": ir.get("source_path", "SKILL.md"),
            "kind": "ordered_step",
            "index": index,
        }
        if step.get("line") is not None:
            source["line"] = step["line"]
        if step.get("section"):
            source["section"] = step["section"]
        node = {
            "id": node_id,
            "type": node_type,
            "title": title,
            "description": detail or title,
            "requires": [],
            "produces": [f"{node_id}_result"],
            "guard": None,
            "action": _action_for_node(node_type, _format_instruction(title, detail)),
            "retry": {"max_attempts": 0},
            "metadata": {"source": source},
        }
        connector = default_connector_binding(node_type)
        if connector:
            node["connector"] = connector
        nodes.append(node)

    nodes.extend(
        [
            {
                "id": "failure",
                "type": "failure",
                "title": "Failure",
                "description": "Terminal failure node.",
            },
            {
                "id": "end",
                "type": "end",
                "title": "End",
                "description": "Workflow completed.",
            },
        ]
    )

    sequence = ["start"] + step_ids + ["end"]
    edges = []
    for index, (source, target) in enumerate(zip(sequence, sequence[1:]), start=1):
        edges.append(
            {
                "id": f"edge_{index:03d}_{source}_to_{target}",
                "from": source,
                "to": target,
                "condition": None,
                "label": "next",
            }
        )
        _node_by_id(nodes, source)["on_success"] = target

    for node in nodes:
        if node["type"] in {"step", "human_gate", "tool_call", "verification", "instruction"}:
            node["on_failure"] = "failure"
            edges.append(
                {
                    "id": f"edge_{node['id']}_failure",
                    "from": node["id"],
                    "to": "failure",
                    "condition": {"expr": "node.status == 'failed'"},
                    "label": "failure",
                }
            )

    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": workflow_id,
            "name": name,
            "description": description,
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": nodes,
        "edges": edges,
        "state_schema": {},
        "guards": [
            {"id": f"guard_{index:03d}", "description": gate}
            for index, gate in enumerate(ir.get("hard_gates") or [], start=1)
        ],
        "checkpoints": [],
        "policies": {
            "default_retry": {"max_attempts": 0},
            "default_timeout_ms": 300000,
        },
    }


def validate_workflow(workflow: Workflow) -> List[str]:
    """Return human-readable validation errors for a Workflow DSL document."""
    return [str(error["message"]) for error in validate_workflow_structured(workflow)]


def validate_workflow_structured(workflow: Workflow) -> List[ValidationError]:
    """Return machine-readable validation errors for a Workflow DSL document."""
    errors: List[ValidationError] = []
    if not isinstance(workflow, dict):
        return [
            _validation_error(
                "workflow_not_object",
                "workflow document must be a JSON object",
                [],
            )
        ]
    if workflow.get("schema_version") != "0.1.0":
        errors.append(
            _validation_error(
                "unsupported_schema_version",
                "workflow.schema_version must be 0.1.0",
                ["schema_version"],
            )
        )

    if "input_schema" in workflow:
        errors.extend(validate_input_schema_contract(workflow.get("input_schema"), ["input_schema"]))

    workflow_meta = workflow.get("workflow")
    if not isinstance(workflow_meta, dict):
        errors.append(
            _validation_error(
                "workflow_metadata_invalid",
                "workflow.workflow must be an object",
                ["workflow"],
            )
        )

    nodes = workflow.get("nodes")
    if not isinstance(nodes, list):
        errors.append(_validation_error("nodes_not_list", "workflow.nodes must be a list", ["nodes"]))
        return errors
    edges = workflow.get("edges", [])
    if not isinstance(edges, list):
        errors.append(_validation_error("edges_not_list", "workflow.edges must be a list", ["edges"]))
        return errors

    node_ids = [node.get("id") for node in nodes if isinstance(node, dict)]
    if len(node_ids) != len(set(node_ids)):
        errors.append(_validation_error("duplicate_node_id", "node ids must be unique", ["nodes"]))

    node_map = {node.get("id"): node for node in nodes if isinstance(node, dict)}
    node_index_map = {node.get("id"): index for index, node in enumerate(nodes) if isinstance(node, dict)}
    edge_ids = [edge.get("id") for edge in edges if isinstance(edge, dict)]
    if len(edge_ids) != len(set(edge_ids)):
        errors.append(_validation_error("duplicate_edge_id", "edge ids must be unique", ["edges"]))

    entry = workflow.get("entry")
    if entry not in node_map:
        errors.append(
            _validation_error(
                "entry_missing",
                "workflow.entry must reference an existing node",
                ["entry"],
            )
        )

    end_nodes = [node for node in nodes if isinstance(node, dict) and node.get("type") == "end"]
    if not end_nodes:
        errors.append(_validation_error("end_node_missing", "workflow must contain at least one end node", ["nodes"]))

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(_validation_error("node_not_object", "all nodes must be objects", ["nodes", index]))
            continue
        node_id = node.get("id")
        node_type = node.get("type")
        _validate_node_timeout(node, index, errors)
        if node_type in {"end", "failure"}:
            for key in _TRANSITION_KEYS:
                if node.get(key):
                    errors.append(
                        _validation_error(
                            "terminal_transition_declared",
                            f"{node_id} {node_type} must not define {key}",
                            ["nodes", index, key],
                        )
                    )
            continue
        if node_type not in {"end", "failure"} and not node.get("on_success"):
            errors.append(
                _validation_error(
                    "node_success_missing",
                    f"{node_id} must define on_success",
                    ["nodes", index, "on_success"],
                )
            )
        if node_type == "human_gate" and not node.get("on_failure"):
            errors.append(
                _validation_error(
                    "human_gate_failure_missing",
                    f"{node_id} human_gate must define on_failure",
                    ["nodes", index, "on_failure"],
                )
            )
        if node.get("on_fallback") and node_type != "tool_call":
            errors.append(
                _validation_error(
                    "fallback_transition_unsupported",
                    f"{node_id} on_fallback is supported only for tool_call nodes",
                    ["nodes", index, "on_fallback"],
                )
            )
        _validate_retry_policy(node.get("retry"), ["nodes", index, "retry"], errors)
        _validate_connector_binding(node, index, errors)
        for key in _TRANSITION_KEYS:
            target = node.get(key)
            if target is not None and target not in node_map:
                errors.append(
                    _validation_error(
                        "node_transition_target_missing",
                        f"{node_id}.{key} references missing node {target}",
                        ["nodes", index, key],
                    )
                )

    edge_pairs = _validate_edges(edges, node_map, errors)
    _validate_transition_edges(node_map, edge_pairs, errors, node_index_map)

    if entry in node_map:
        reachable = _reachable_nodes(node_map, str(entry))
        unreachable = sorted(set(node_map) - reachable)
        if unreachable:
            errors.append(
                _validation_error(
                    "unreachable_nodes",
                    f"unreachable nodes: {', '.join(unreachable)}",
                    ["nodes"],
                )
            )

    _validate_policies(workflow.get("policies"), errors)

    return errors


def _validate_edges(
    edges: List[Dict[str, object]],
    node_map: Dict[object, Dict[str, object]],
    errors: List[ValidationError],
) -> Set[tuple]:
    edge_pairs = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(_validation_error("edge_not_object", "all edges must be objects", ["edges", index]))
            continue

        edge_id = str(edge.get("id") or "<missing edge id>")
        source = edge.get("from")
        target = edge.get("to")

        if source not in node_map:
            errors.append(
                _validation_error(
                    "edge_source_missing",
                    f"{edge_id}.from references missing node {source}",
                    ["edges", index, "from"],
                )
            )
        if target not in node_map:
            errors.append(
                _validation_error(
                    "edge_target_missing",
                    f"{edge_id}.to references missing node {target}",
                    ["edges", index, "to"],
                )
            )
        if source in node_map and node_map[source].get("type") in {"end", "failure"}:
            errors.append(
                _validation_error(
                    "terminal_edge_source",
                    f"{edge_id} must not originate from terminal node {source}",
                    ["edges", index, "from"],
                )
            )

        if source in node_map and target in node_map:
            edge_pairs.add((source, target))
            transition_targets = _transition_targets(node_map[source])
            if target not in transition_targets:
                errors.append(
                    _validation_error(
                        "edge_not_declared_by_transition",
                        f"{edge_id} from {source} to {target} is not declared by node transitions",
                        ["edges", index],
                    )
                )

    return edge_pairs


def _validate_transition_edges(
    node_map: Dict[object, Dict[str, object]],
    edge_pairs: Set[tuple],
    errors: List[ValidationError],
    node_index_map: Dict[object, int],
) -> None:
    for node_id, node in node_map.items():
        if node.get("type") in {"end", "failure"}:
            continue
        for key in _TRANSITION_KEYS:
            target = node.get(key)
            if target is None or target not in node_map:
                continue
            if (node_id, target) not in edge_pairs:
                errors.append(
                    _validation_error(
                        "transition_edge_missing",
                        f"{node_id}.{key} must have matching edge to {target}",
                        ["nodes", node_index_map.get(node_id, 0), key],
                    )
                )


def _validate_connector_binding(
    node: Dict[str, object],
    index: int,
    errors: List[ValidationError],
) -> None:
    node_type = node.get("type")
    connector = node.get("connector")
    if node_type == "tool_call" and not connector:
        errors.append(
            _validation_error(
                "connector_binding_missing",
                f"{node.get('id')} tool_call must define connector.id",
                ["nodes", index, "connector"],
            )
        )
        return
    if connector is None:
        return
    if not isinstance(connector, dict):
        errors.append(
            _validation_error(
                "connector_binding_invalid",
                f"{node.get('id')} connector must be an object",
                ["nodes", index, "connector"],
            )
        )
        return
    if not connector.get("id"):
        errors.append(
            _validation_error(
                "connector_binding_missing",
                f"{node.get('id')} connector.id is required",
                ["nodes", index, "connector", "id"],
            )
        )
    if connector.get("id") == "http":
        _validate_http_connector_request(node, index, connector, errors)


def _validate_policies(policies: object, errors: List[ValidationError]) -> None:
    if policies is None:
        return
    if not isinstance(policies, dict):
        errors.append(
            _validation_error(
                "policies_invalid",
                "workflow.policies must be an object",
                ["policies"],
            )
        )
        return
    _validate_retry_policy(policies.get("default_retry"), ["policies", "default_retry"], errors)
    if "default_timeout_ms" in policies:
        value = policies.get("default_timeout_ms")
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            or value > 86_400_000
        ):
            errors.append(
                _validation_error(
                    "policy_timeout_invalid",
                    "policies.default_timeout_ms must be an integer between 0 and 86400000",
                    ["policies", "default_timeout_ms"],
                )
            )
    if "workflow_timeout_ms" in policies:
        value = policies.get("workflow_timeout_ms")
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            or value > 2_592_000_000
        ):
            errors.append(
                _validation_error(
                    "policy_workflow_timeout_invalid",
                    "policies.workflow_timeout_ms must be an integer between 0 and 2592000000",
                    ["policies", "workflow_timeout_ms"],
                )
            )


def _validate_retry_policy(
    retry: object,
    path: List[object],
    errors: List[ValidationError],
) -> None:
    if retry is None:
        return
    if not isinstance(retry, dict):
        errors.append(_validation_error("retry_invalid", "retry policy must be an object", path))
        return
    max_attempts = retry.get("max_attempts")
    if max_attempts is not None and (
        isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 0
    ):
        errors.append(
            _validation_error(
                "retry_max_attempts_invalid",
                "retry.max_attempts must be a non-negative integer",
                path + ["max_attempts"],
            )
        )
    backoff_ms = retry.get("backoff_ms")
    if backoff_ms is not None and (
        isinstance(backoff_ms, bool)
        or not isinstance(backoff_ms, int)
        or backoff_ms < 0
        or backoff_ms > 60000
    ):
        errors.append(
            _validation_error(
                "retry_backoff_invalid",
                "retry.backoff_ms must be an integer between 0 and 60000",
                path + ["backoff_ms"],
            )
        )


def _validate_node_timeout(
    node: Dict[str, object],
    index: int,
    errors: List[ValidationError],
) -> None:
    """Validate the additive per-node active execution timeout."""

    if "timeout_ms" not in node:
        return
    value = node.get("timeout_ms")
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > 86_400_000
    ):
        errors.append(
            _validation_error(
                "node_timeout_invalid",
                f"{node.get('id')} timeout_ms must be an integer between 0 and 86400000",
                ["nodes", index, "timeout_ms"],
            )
        )


def _validate_http_connector_request(
    node: Dict[str, object],
    index: int,
    connector: Dict[str, object],
    errors: List[ValidationError],
) -> None:
    request = connector.get("request")
    if not isinstance(request, dict):
        return
    if "response_mode" in request:
        response_mode = request.get("response_mode")
        if not isinstance(response_mode, str) or response_mode not in {"full", "metadata"}:
            errors.append(
                _validation_error(
                    "response_mode_invalid",
                    f"{node.get('id')} connector.request.response_mode must be full or metadata",
                    ["nodes", index, "connector", "request", "response_mode"],
                )
            )
    if "input_mapping" not in request:
        return
    input_mapping = request.get("input_mapping")
    path = ["nodes", index, "connector", "request", "input_mapping"]
    if not isinstance(input_mapping, list):
        errors.append(
            _validation_error(
                "input_mapping_invalid",
                f"{node.get('id')} connector.request.input_mapping must be a list",
                path,
            )
        )
        return
    for mapping_index, mapping in enumerate(input_mapping):
        mapping_path = path + [mapping_index]
        if not isinstance(mapping, dict):
            errors.append(
                _validation_error(
                    "input_mapping_invalid",
                    f"{node.get('id')} connector.request.input_mapping[{mapping_index}] must be an object",
                    mapping_path,
                )
            )
            continue
        source = mapping.get("from")
        target = mapping.get("to")
        if not isinstance(source, str) or source == "/input/" or not source.startswith("/input/"):
            errors.append(
                _validation_error(
                    "input_mapping_source_invalid",
                    f"{node.get('id')} connector.request.input_mapping[{mapping_index}].from must start with /input/",
                    mapping_path + ["from"],
                )
            )
        if not _valid_http_input_mapping_target(target):
            errors.append(
                _validation_error(
                    "input_mapping_target_invalid",
                    f"{node.get('id')} connector.request.input_mapping[{mapping_index}].to must start with /body/ or be /query/<name>",
                    mapping_path + ["to"],
                )
            )
        if "required" in mapping and not isinstance(mapping.get("required"), bool):
            errors.append(
                _validation_error(
                    "input_mapping_required_invalid",
                    f"{node.get('id')} connector.request.input_mapping[{mapping_index}].required must be a boolean",
                    mapping_path + ["required"],
                )
            )


def _valid_http_input_mapping_target(target: object) -> bool:
    if not isinstance(target, str):
        return False
    if target.startswith("/body/") and target != "/body/":
        return True
    if not target.startswith("/query/") or target == "/query/":
        return False
    return len(target.split("/")) == 3 and bool(target.split("/")[-1])


def _validation_error(code: str, message: str, path: List[object]) -> ValidationError:
    return {
        "code": code,
        "message": message,
        "path": path,
        "severity": "error",
    }


def _transition_targets(node: Dict[str, object]) -> Set[object]:
    return {node[key] for key in _TRANSITION_KEYS if node.get(key) is not None}


def _node_type_for_step(title: str) -> str:
    lowered = title.lower()
    human_terms = ("approval", "approve", "user review", "ask user", "human", "confirm")
    verify_terms = ("verify", "test", "validate", "check")
    tool_terms = ("tool", "command", "run ")

    if any(term in lowered for term in human_terms):
        return "human_gate"
    if any(term in lowered for term in verify_terms):
        return "verification"
    if any(term in lowered for term in tool_terms):
        return "tool_call"
    return "step"


def _step_records_from_ir(ir: Dict[str, object]) -> List[Dict[str, object]]:
    details = ir.get("ordered_step_details")
    if isinstance(details, list) and details:
        records = []
        for index, item in enumerate(details, start=1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            records.append(
                {
                    "title": title,
                    "detail": str(item.get("detail") or "").strip(),
                    "line": item.get("line"),
                    "section": item.get("section"),
                    "index": index,
                }
            )
        return records

    records = []
    for index, step in enumerate(list(ir.get("ordered_steps") or []), start=1):
        title = str(step).strip()
        if title:
            records.append(
                {
                    "title": title,
                    "detail": "",
                    "line": None,
                    "section": None,
                    "index": index,
                }
            )
    return records


def _format_instruction(title: str, detail: str) -> str:
    if detail:
        return f"{title} — {detail}"
    return title


def _action_for_node(node_type: str, title: str) -> Dict[str, str]:
    if node_type == "human_gate":
        return {"kind": "human_approval", "prompt": title}
    if node_type == "tool_call":
        return {"kind": "tool_call", "instruction": title}
    if node_type == "verification":
        return {"kind": "verification", "instruction": title}
    return {"kind": "agent_instruction", "instruction": title}


def _node_by_id(nodes: List[Dict[str, object]], node_id: str) -> Dict[str, object]:
    for node in nodes:
        if node["id"] == node_id:
            return node
    raise KeyError(node_id)


def _reachable_nodes(node_map: Dict[object, Dict[str, object]], entry: str) -> Set[str]:
    seen: Set[str] = set()
    stack = [entry]
    while stack:
        node_id = stack.pop()
        if node_id in seen:
            continue
        seen.add(node_id)
        node = node_map[node_id]
        for key in _TRANSITION_KEYS:
            target = node.get(key)
            if isinstance(target, str) and target in node_map:
                stack.append(target)
    return seen


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "node"
