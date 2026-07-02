"""Compile Skill IR into executable Workflow DSL."""

from __future__ import annotations

import re
from typing import Dict, List, Set


Workflow = Dict[str, object]
ValidationError = Dict[str, object]


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
        nodes.append(
            {
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
        )

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
    if workflow.get("schema_version") != "0.1.0":
        errors.append(
            _validation_error(
                "unsupported_schema_version",
                "workflow.schema_version must be 0.1.0",
                ["schema_version"],
            )
        )

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
        if node_type in {"end", "failure"}:
            for key in ("on_success", "on_failure"):
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
        for key in ("on_success", "on_failure"):
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
        for key in ("on_success", "on_failure"):
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


def _validation_error(code: str, message: str, path: List[object]) -> ValidationError:
    return {
        "code": code,
        "message": message,
        "path": path,
        "severity": "error",
    }


def _transition_targets(node: Dict[str, object]) -> Set[object]:
    return {node[key] for key in ("on_success", "on_failure") if node.get(key) is not None}


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
        for key in ("on_success", "on_failure"):
            target = node.get(key)
            if isinstance(target, str) and target in node_map:
                stack.append(target)
    return seen


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "node"
