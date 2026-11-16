"""Compile Skill IR into executable Workflow DSL."""

from __future__ import annotations

import re
import copy
from typing import Any, Dict, List, Set
from urllib.parse import urlsplit

from .connectors import MAX_HTTP_ALLOWED_ORIGINS, MAX_HTTP_ORIGIN_BYTES, default_connector_binding
from .input_schema import validate_input_schema_contract
from .http_assertions import validate_http_assertion_binding, skill_http_assertion_binding
from .skill_http import skill_http_action_binding
from .skill_input import skill_input_schema_contract
from .skill_version import skill_workflow_version
from .inference import infer_step
from .decisions import decision_errors
from .agent_protocol import agent_node_errors, skill_agent_config
from .workflow_shapes import validate_workflow_shapes

from .models import SkillIR, Workflow
ValidationError = Dict[str, Any]
_TRANSITION_KEYS = ("on_success", "on_failure", "on_fallback")
SKILL_COMPILE_REVIEW_SCHEMA_VERSION = "skill2workflow-skill-compile-review-0.1.0"
_SKILL_COMPILE_REVIEW_NOTICE_CODES = (
    "checklist_not_found",
    "human_gate_not_inferred",
    "verification_not_inferred",
)


def compile_ir_to_workflow(ir: SkillIR) -> Workflow:
    """Compile Skill IR into the initial skill2workflow DSL."""
    workflow_version = skill_workflow_version(ir['workflow_version']) if 'workflow_version' in ir else '0.1.0'
    input_schema = skill_input_schema_contract(ir['input_schema']) if 'input_schema' in ir else None
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
    nodes: List[Dict[str, Any]] = [
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
        explicit_type = step.get("node_type")
        explicit_connector = step.get("connector")
        agent = skill_agent_config(step["agent"]) if step.get("agent") is not None else None
        if agent is not None:
            if explicit_type != "tool_call" or explicit_connector != {"id": agent["connector"], "kind": "agent"}:
                raise ValueError("Invalid Skill step annotation")
        elif explicit_connector is not None:
            if (explicit_type != "tool_call" or not isinstance(explicit_connector, dict)
                    or not isinstance(explicit_connector.get("id"), str)
                    or explicit_connector.get("id") not in {"http", "http_assert"}
                    or explicit_connector.get("kind") != explicit_connector.get("id")):
                raise ValueError("Invalid Skill step annotation")
            config = {k: v for k, v in explicit_connector.items() if k not in {"id", "kind"}}
            factory = skill_http_action_binding if explicit_connector["id"] == "http" else skill_http_assertion_binding
            explicit_connector = factory(config)
            errors: List[ValidationError] = []
            _validate_connector_binding({"id": node_id, "type": explicit_type, "connector": explicit_connector}, index, errors)
            if errors:
                raise ValueError("Invalid Skill step annotation")
        elif explicit_type is not None and explicit_type not in {"human_gate", "step", "decision"}:
            raise ValueError("Unsupported explicit Skill step type")
        inferred_type, term = infer_step(f"{title} {detail}")
        node_type = explicit_type or inferred_type
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
        if explicit_type is None:
            source.update(inferred_type=inferred_type, matched_term=term)
        node: Dict[str, Any] = {
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
        connector = copy.deepcopy(explicit_connector) if explicit_connector is not None else default_connector_binding(node_type)
        if connector:
            node["connector"] = connector
        if agent is not None:
            node["action"] = {"kind": "agent_instruction", "instruction": agent["instruction"]}
            node["output_schema"] = copy.deepcopy(agent["output_schema"])
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
    edges: List[Dict[str, Any]] = []
    for index, (source_id, target) in enumerate(zip(sequence, sequence[1:]), start=1):
        edges.append(
            {
                "id": f"edge_{index:03d}_{source_id}_to_{target}",
                "from": source_id,
                "to": target,
                "condition": None,
                "label": "next",
            }
        )
        _node_by_id(nodes, source_id)["on_success"] = target

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

    workflow: Workflow = {
        "schema_version": "0.1.0",
        "workflow": {
            "id": workflow_id,
            "name": name,
            "description": description,
            "version": workflow_version,
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
    if input_schema is not None:
        workflow['input_schema'] = input_schema
    if any(step.get("node_type") == "decision" or step.get("next") is not None or step.get("agent") is not None for step in steps):
        for step, node_id in zip(steps, step_ids):
            if step.get("agent") is not None:
                _node_by_id(nodes, node_id)["requires"] = [
                    _resolve_step_reference(reference, steps, step_ids) for reference in step["agent"]["requires"]
                ]
        _compile_decisions(workflow, steps, step_ids)
    return workflow


def summarize_skill_compile(ir: SkillIR, workflow: Workflow) -> Dict[str, Any]:
    """Return a compact, source-free review of one compiled Skill draft.

    This is authoring guidance only. It describes what the conservative compiler
    inferred; it does not validate business intent or alter runtime behavior.
    """

    node_types = []
    nodes = workflow.get("nodes") if isinstance(workflow, dict) else None
    if isinstance(nodes, list):
        node_types = [node.get("type") for node in nodes if isinstance(node, dict)]
    ordered_step_details = ir.get("ordered_step_details") if isinstance(ir, dict) else None
    ordered_steps = ir.get("ordered_steps") if isinstance(ir, dict) else None
    if isinstance(ordered_step_details, list):
        ordered_step_count = len(ordered_step_details)
    elif isinstance(ordered_steps, list):
        ordered_step_count = len(ordered_steps)
    else:
        ordered_step_count = 0
    hard_gates = ir.get("hard_gates") if isinstance(ir, dict) else None
    hard_gate_count = len(hard_gates) if isinstance(hard_gates, list) else 0
    human_gate_count = node_types.count("human_gate")
    verification_node_count = node_types.count("verification") + sum(
        1 for node in (nodes if isinstance(nodes, list) else []) if isinstance(node, dict)
        and node.get("type") == "tool_call"
        and isinstance(node.get("connector"), dict)
        and node["connector"].get("id") == "http_assert"
    )
    executable_node_count = sum(
        node_type in {"step", "human_gate", "tool_call", "verification", "instruction", "decision"}
        for node_type in node_types
    )
    notices = []
    if ordered_step_count == 0:
        notices.append("checklist_not_found")
    if human_gate_count == 0:
        notices.append("human_gate_not_inferred")
    if verification_node_count == 0:
        notices.append("verification_not_inferred")
    notices.extend(inference_notices(workflow))
    return {
        "schema_version": SKILL_COMPILE_REVIEW_SCHEMA_VERSION,
        "ordered_step_count": ordered_step_count,
        "executable_node_count": executable_node_count,
        "human_gate_count": human_gate_count,
        "verification_node_count": verification_node_count,
        "hard_gate_count": hard_gate_count,
        "notices": notices,
    }


def validate_workflow(workflow: object) -> List[str]:
    """Return human-readable validation errors for a Workflow DSL document."""
    return [str(error["message"]) for error in validate_workflow_structured(workflow)]


def validate_workflow_notices(workflow: Workflow) -> List[ValidationError]:
    """Report descriptive/reserved declarations separately from validity."""
    notices = []
    def notice(path):
        notices.append({"code": "descriptive_field", "message": "Reserved/descriptive field is ignored at runtime", "path": path, "severity": "notice"})
    if not isinstance(workflow, dict):
        return notices
    for key in ("guards", "state_schema", "checkpoints"):
        if workflow.get(key):
            notice([key])
    nodes = workflow.get("nodes")
    for index, node in enumerate(nodes if isinstance(nodes, list) else []):
        if isinstance(node, dict):
            for key in ("guard", "requires", "produces"):
                if (key == "requires" and workflow.get("schema_version") == "0.2.0"
                        and isinstance(node.get("connector"), dict) and node["connector"].get("kind") == "agent"):
                    continue
                if node.get(key):
                    notice(["nodes", index, key])
    edges = workflow.get("edges")
    for index, edge in enumerate(edges if isinstance(edges, list) else []):
        if isinstance(edge, dict) and edge.get("condition"):
            notice(["edges", index, "condition"])
    return notices


def validate_workflow_structured(workflow: object) -> List[ValidationError]:
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
    if not isinstance(workflow.get("schema_version"), str) or workflow.get("schema_version") not in {"0.1.0", "0.2.0"}:
        errors.append(
            _validation_error(
                "unsupported_schema_version",
                "workflow.schema_version must be 0.1.0 or 0.2.0",
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

    shape_errors = validate_workflow_shapes(workflow)
    if shape_errors:
        return errors + shape_errors

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

    node_map: Dict[Any, Dict[str, Any]] = {node.get("id"): node for node in nodes if isinstance(node, dict)}
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
        if node_type == "decision":
            errors.extend(decision_errors(node, index, node_map, workflow.get("schema_version")))
            continue
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
        if isinstance(node.get("connector"), dict) and node["connector"].get("kind") == "agent":
            errors.extend(agent_node_errors(node, index, workflow.get("schema_version")))
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
    _validate_transition_edges(node_map, edge_pairs, errors, node_index_map, edges)
    if workflow.get("schema_version") == "0.2.0" and _has_cycle(node_map):
        errors.append(_validation_error("workflow_cycle", "Workflow DSL 0.2.0 requires a DAG", ["nodes"]))
    elif workflow.get("schema_version") == "0.2.0":
        _validate_agent_dependencies(node_map, entry, node_index_map, errors)

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
    edges: List[Dict[str, Any]],
    node_map: Dict[object, Dict[str, Any]],
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
            if node_map[source].get("type") == "decision" and dict(_decision_targets(node_map[source])).get(edge.get("label")) != target:
                errors.append(_validation_error(
                    "decision_edge_invalid", "decision edge label must identify its branch/default destination", ["edges", index],
                ))
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
    node_map: Dict[object, Dict[str, Any]],
    edge_pairs: Set[tuple],
    errors: List[ValidationError],
    node_index_map: Dict[object, int],
    edges: List[Dict[str, Any]],
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

        if node.get("type") == "decision":
            for label, target in _decision_targets(node):
                if target in node_map and not any(
                    isinstance(edge, dict) and edge.get("from") == node_id
                    and edge.get("to") == target and edge.get("label") == label for edge in edges
                ):
                    errors.append(_validation_error(
                        "transition_edge_missing", f"{node_id}.{label} must have matching edge to {target}",
                        ["nodes", node_index_map.get(node_id, 0), label],
                    ))


def _validate_connector_binding(
    node: Dict[str, Any],
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
    if connector.get("id") in {"http", "http_assert"}:
        _validate_http_connector_request(node, index, connector, errors)
    if connector.get("id") == "http_assert":
        message = validate_http_assertion_binding(connector)
        if node_type != "tool_call" or message:
            errors.append(_validation_error(
                "http_assertion_invalid", message or "http assertion requires a tool_call node",
                ["nodes", index, "connector"],
            ))


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
    node: Dict[str, Any],
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
    node: Dict[str, Any],
    index: int,
    connector: Dict[str, Any],
    errors: List[ValidationError],
) -> None:
    request = connector.get("request")
    if not isinstance(request, dict):
        errors.append(_validation_error(
            "connector_request_missing",
            f"{node.get('id')} {connector.get('id')} connector requires connector.request",
            ["nodes", index, "connector", "request"],
        ))
        return
    if "allowed_origins" in request:
        _validate_http_allowed_origins(node, index, request.get("allowed_origins"), errors)
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


def _validate_http_allowed_origins(
    node: Dict[str, Any],
    index: int,
    origins: object,
    errors: List[ValidationError],
) -> None:
    path = ["nodes", index, "connector", "request", "allowed_origins"]
    if not isinstance(origins, list) or not origins:
        errors.append(
            _validation_error(
                "allowed_origins_invalid",
                f"{node.get('id')} connector.request.allowed_origins must be a non-empty list",
                path,
            )
        )
        return
    if len(origins) > MAX_HTTP_ALLOWED_ORIGINS:
        errors.append(
            _validation_error(
                "allowed_origins_too_many",
                f"{node.get('id')} connector.request.allowed_origins must contain at most {MAX_HTTP_ALLOWED_ORIGINS} entries",
                path,
            )
        )
    for origin_index, origin in enumerate(origins[:MAX_HTTP_ALLOWED_ORIGINS]):
        origin_path = path + [origin_index]
        if not isinstance(origin, str):
            errors.append(
                _validation_error(
                    "allowed_origin_entry_invalid",
                    f"{node.get('id')} connector.request.allowed_origins[{origin_index}] must be an origin string",
                    origin_path,
                )
            )
            continue
        try:
            if len(origin.encode("utf-8")) > MAX_HTTP_ORIGIN_BYTES:
                raise ValueError("origin too long")
            parsed = urlsplit(origin)
            hostname = parsed.hostname
            _ = parsed.port
        except (UnicodeError, ValueError):
            hostname = None
            parsed = None
        if (
            parsed is None
            or parsed.scheme not in ("http", "https")
            or not parsed.netloc
            or not hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            errors.append(
                _validation_error(
                    "allowed_origin_entry_invalid",
                    f"{node.get('id')} connector.request.allowed_origins[{origin_index}] must be an http/https origin without userinfo, query, or fragment",
                    origin_path,
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


def _transition_targets(node: Dict[str, Any]) -> Set[object]:
    targets = {node[key] for key in _TRANSITION_KEYS if node.get(key) is not None}
    targets.update(target for _, target in _decision_targets(node))
    return targets


def _decision_targets(node):
    if node.get("type") != "decision":
        return []
    branches = node.get("branches")
    targets = [
        (f"branch_{index}", branch["to"])
        for index, branch in enumerate(branches if isinstance(branches, list) else [])
        if isinstance(branch, dict) and isinstance(branch.get("to"), str)
    ]
    if isinstance(node.get("default"), str):
        targets.append(("default", node["default"]))
    return targets


def _has_cycle(node_map):
    targets = {key: _transition_targets(node) & set(node_map) for key, node in node_map.items()}
    incoming = dict.fromkeys(node_map, 0)
    for destinations in targets.values():
        for destination in destinations:
            incoming[destination] += 1
    ready = [key for key, count in incoming.items() if count == 0]
    visited = 0
    while ready:
        source = ready.pop()
        visited += 1
        for target in targets[source]:
            incoming[target] -= 1
            if incoming[target] == 0:
                ready.append(target)
    return visited != len(node_map)


def _resolve_step_reference(reference, steps, step_ids):
    if type(reference) is int or (isinstance(reference, str) and reference.isascii() and reference.isdigit()):
        index = int(reference)
        if 1 <= index <= len(step_ids):
            return step_ids[index - 1]
    elif isinstance(reference, str):
        if reference in {"end", "failure"} or reference in step_ids:
            return reference
        matches = [step_ids[index] for index, step in enumerate(steps) if step["title"] == reference]
        if len(matches) == 1:
            return matches[0]
    raise ValueError("Invalid Skill step reference")


def _validate_agent_dependencies(
    node_map: Dict[str, Dict[str, Any]], entry: object,
    indexes: Dict[Any, int], errors: List[ValidationError],
) -> None:
    if entry not in node_map:
        return
    parents: Dict[str, Set[str]] = {node_id: set() for node_id in node_map}
    outgoing = {node_id: set(node_map) & _transition_targets(node) for node_id, node in node_map.items()}
    for source, targets in outgoing.items():
        for target in targets:
            parents[target].add(source)
    incoming = {node_id: len(sources) for node_id, sources in parents.items()}
    ready = [node_id for node_id, count in incoming.items() if count == 0]
    dominators: Dict[str, Set[str]] = {}
    while ready:
        node_id = ready.pop()
        sources = parents[node_id]
        inherited = set.intersection(*(dominators[source] for source in sources)) if sources else set()
        dominators[node_id] = inherited | {node_id}
        for target in outgoing[node_id]:
            incoming[target] -= 1
            if incoming[target] == 0:
                ready.append(target)
    for node_id, node in node_map.items():
        if not isinstance(node.get("connector"), dict) or node["connector"].get("kind") != "agent":
            continue
        requires = node.get("requires", [])
        if not isinstance(requires, list):
            continue
        for dependency_index, dependency in enumerate(requires):
            if not isinstance(dependency, str) or dependency not in node_map:
                code = "agent_dependency_missing"
            elif dependency == node_id or dependency not in dominators.get(node_id, set()):
                code = "agent_dependency_not_dominating"
            else:
                continue
            errors.append(_validation_error(
                code, "agent requires an existing output dependency on every incoming path",
                ["nodes", indexes[node_id], "requires", dependency_index],
            ))


def _compile_decisions(workflow, steps, step_ids):
    workflow["schema_version"] = "0.2.0"
    for step, node_id in zip(steps, step_ids):
        node = _node_by_id(workflow["nodes"], node_id)
        if node["type"] == "decision":
            config = step.get("decision")
            if not isinstance(config, dict) or set(config) != {"branches", "default"}:
                raise ValueError("Invalid Skill step annotation")
            node.pop("on_success", None)
            node.pop("action", None)
            node["branches"] = copy.deepcopy(config["branches"])
            node["default"] = _resolve_step_reference(config["default"], steps, step_ids)
            if not isinstance(node["branches"], list):
                raise ValueError("Invalid Skill step annotation")
            for branch in node["branches"]:
                if not isinstance(branch, dict) or set(branch) != {"when", "to"}:
                    raise ValueError("Invalid Skill step annotation")
                branch["to"] = _resolve_step_reference(branch["to"], steps, step_ids)
                condition = branch["when"]
                if isinstance(condition, dict) and isinstance(condition.get("path"), str) and condition["path"].startswith("/nodes/"):
                    parts = condition["path"].split("/")
                    reference = parts[2].replace("~1", "/").replace("~0", "~")
                    parts[2] = _resolve_step_reference(reference, steps, step_ids).replace("~", "~0").replace("/", "~1")
                    condition["path"] = "/".join(parts)
        elif step.get("next") is not None:
            node["on_success"] = _resolve_step_reference(step["next"], steps, step_ids)
    edges = []
    for node in workflow["nodes"]:
        transitions = _decision_targets(node) if node.get("type") == "decision" else [
            (label, node[key]) for key, label in (("on_success", "next"), ("on_failure", "failure"), ("on_fallback", "fallback"))
            if node.get(key)
        ]
        for label, target in transitions:
            edges.append({"id": f"edge_{node['id']}_{label}", "from": node["id"], "to": target, "label": label, "condition": None})
    workflow["edges"] = edges
    if validate_workflow_structured(workflow):
        raise ValueError("Invalid Skill step annotation")


def _node_type_for_step(title: str) -> str:
    return infer_step(title)[0]


def inference_notices(workflow: Workflow) -> List[str]:
    """List inferred source indexes, types and fixed terms without source text."""
    notices = []
    for node in workflow.get("nodes", []):
        source = node.get("metadata", {}).get("source", {})
        if "inferred_type" in source:
            notices.append(
                f"inferred_node:{source['index']}:{source['inferred_type']}:{source.get('matched_term') or ''}"
            )
    return notices


def _step_records_from_ir(ir: SkillIR) -> List[Dict[str, Any]]:
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
                    "node_type": item.get("node_type"),
                    "connector": item.get("connector"),
                    "decision": item.get("decision"),
                    "next": item.get("next"),
                    "agent": item.get("agent"),
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


def _node_by_id(nodes: List[Dict[str, Any]], node_id: str) -> Dict[str, Any]:
    for node in nodes:
        if node["id"] == node_id:
            return node
    raise KeyError(node_id)


def _reachable_nodes(node_map: Dict[object, Dict[str, Any]], entry: str) -> Set[str]:
    seen: Set[str] = set()
    stack = [entry]
    while stack:
        node_id = stack.pop()
        if node_id in seen:
            continue
        seen.add(node_id)
        node = node_map[node_id]
        for target in _transition_targets(node):
            if isinstance(target, str) and target in node_map:
                stack.append(target)
    return seen


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "node"
