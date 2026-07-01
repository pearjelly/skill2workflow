"""Compile Skill IR into executable Workflow DSL."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set


Workflow = Dict[str, object]


def compile_ir_to_workflow(ir: Dict[str, object]) -> Workflow:
    """Compile Skill IR into the initial skill2workflow DSL."""
    metadata = ir.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    name = str(metadata.get("name") or "skill-workflow")
    description = str(metadata.get("description") or ir.get("description") or "")
    steps = list(ir.get("ordered_steps") or [])
    if not steps:
        steps = ["Review skill guidance"]

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
        title = str(step)
        node_id = f"node_{index:03d}_{_slugify(title)}"
        node_type = _node_type_for_step(title)
        step_ids.append(node_id)
        nodes.append(
            {
                "id": node_id,
                "type": node_type,
                "title": title,
                "description": title,
                "requires": [],
                "produces": [f"{node_id}_result"],
                "guard": None,
                "action": _action_for_node(node_type, title),
                "retry": {"max_attempts": 0},
                "metadata": {
                    "source": {
                        "file": ir.get("source_path", "SKILL.md"),
                        "kind": "ordered_step",
                        "index": index,
                    }
                },
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
    errors: List[str] = []
    nodes = workflow.get("nodes")
    if not isinstance(nodes, list):
        return ["workflow.nodes must be a list"]

    node_ids = [node.get("id") for node in nodes if isinstance(node, dict)]
    if len(node_ids) != len(set(node_ids)):
        errors.append("node ids must be unique")

    node_map = {node.get("id"): node for node in nodes if isinstance(node, dict)}
    entry = workflow.get("entry")
    if entry not in node_map:
        errors.append("workflow.entry must reference an existing node")

    end_nodes = [node for node in nodes if isinstance(node, dict) and node.get("type") == "end"]
    if not end_nodes:
        errors.append("workflow must contain at least one end node")

    for node in nodes:
        if not isinstance(node, dict):
            errors.append("all nodes must be objects")
            continue
        node_id = node.get("id")
        node_type = node.get("type")
        if node_type not in {"end", "failure"} and not node.get("on_success"):
            errors.append(f"{node_id} must define on_success")
        if node_type == "human_gate" and not node.get("on_failure"):
            errors.append(f"{node_id} human_gate must define on_failure")
        for key in ("on_success", "on_failure"):
            target = node.get(key)
            if target is not None and target not in node_map:
                errors.append(f"{node_id}.{key} references missing node {target}")

    if entry in node_map:
        reachable = _reachable_nodes(node_map, str(entry))
        unreachable = sorted(set(node_map) - reachable)
        if unreachable:
            errors.append(f"unreachable nodes: {', '.join(unreachable)}")

    return errors


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

