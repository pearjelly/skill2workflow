"""Convert between Workflow DSL documents and LiteGraph-compatible graph JSON."""

from __future__ import annotations

import copy
from typing import Dict, Iterable, List, Optional, Tuple


LiteGraph = Dict[str, object]
Workflow = Dict[str, object]
RunState = Dict[str, object]


def workflow_to_litegraph(
    workflow: Workflow,
    run_state: Optional[RunState] = None,
    audit_events: Optional[List[Dict[str, object]]] = None,
) -> LiteGraph:
    """Return a LiteGraph graph representation for a Workflow DSL document.

    The Workflow DSL remains the execution source of truth. This function only
    creates a view model that LiteGraph can render and annotate.
    """
    nodes = _workflow_nodes(workflow)
    edges = _workflow_edges(workflow, nodes)
    node_id_map = {str(node["id"]): index for index, node in enumerate(nodes, start=1)}
    node_ids = [str(node["id"]) for node in nodes]
    overlay_by_node = run_overlay_for_nodes(node_ids, run_state, audit_events) if isinstance(run_state, dict) else {}
    graph_nodes = [
        _litegraph_node(node, node_id_map[str(node["id"])], run_state, overlay_by_node.get(str(node["id"])))
        for node in nodes
    ]

    links = []
    last_link_id = 0
    for edge in edges:
        source = str(edge["from"])
        target = str(edge["to"])
        if source not in node_id_map or target not in node_id_map:
            continue

        last_link_id += 1
        source_graph_id = node_id_map[source]
        target_graph_id = node_id_map[target]
        source_slot = _source_slot(edge, _node_by_id(nodes, source))
        target_slot = _target_slot(links, target_graph_id)
        links.append([last_link_id, source_graph_id, source_slot, target_graph_id, target_slot, "flow"])
        _attach_output_link(graph_nodes[source_graph_id - 1], source_slot, last_link_id)
        _attach_input_link(graph_nodes[target_graph_id - 1], target_slot, last_link_id)

    workflow_meta = workflow.get("workflow", {})
    if not isinstance(workflow_meta, dict):
        workflow_meta = {}
    extra = {
        "source_schema_version": workflow.get("schema_version"),
        "truth_source": "workflow_dsl",
        "source_workflow": copy.deepcopy(workflow),
    }
    if isinstance(run_state, dict):
        extra["run_overlay"] = _run_overlay_summary(run_state, overlay_by_node)

    return {
        "version": "skill2workflow-litegraph-0.1.0",
        "workflow": {
            "id": workflow_meta.get("id", "workflow"),
            "name": workflow_meta.get("name", "workflow"),
            "version": workflow_meta.get("version", "0.1.0"),
            "status": workflow_meta.get("status", "draft"),
            "description": workflow_meta.get("description", ""),
            "entry": workflow.get("entry", "start"),
        },
        "last_node_id": len(graph_nodes),
        "last_link_id": last_link_id,
        "nodes": graph_nodes,
        "links": links,
        "groups": [],
        "config": {},
        "extra": extra,
    }


def run_overlay_for_nodes(
    node_ids: Iterable[str],
    run_state: Optional[RunState],
    audit_events: Optional[List[Dict[str, object]]] = None,
) -> Dict[str, Dict[str, object]]:
    """Return compact read-only run evidence keyed by workflow node id."""

    normalized_node_ids = [str(node_id) for node_id in node_ids]
    events_by_node = _events_by_node(run_state.get("events", []) if isinstance(run_state, dict) else [])
    audit_by_node = _events_by_node(audit_events or [])
    overlays: Dict[str, Dict[str, object]] = {}
    for node_id in normalized_node_ids:
        node_events = events_by_node.get(node_id, [])
        node_audit_events = audit_by_node.get(node_id, [])
        result = _node_result(run_state, node_id)
        latest_event = node_events[-1] if node_events else {}
        overlay = {
            "node_id": node_id,
            "status": _run_status(node_id, run_state),
            "current": bool(isinstance(run_state, dict) and run_state.get("current_node") == node_id),
            "event_count": len(node_events),
            "latest_event_type": str(latest_event.get("type", "")) if isinstance(latest_event, dict) else "",
            "result_status": str(result.get("status", "")) if result else "",
            "attempts": _overlay_int(result.get("attempts") if result else None, node_events, "attempt"),
            "max_attempts": _overlay_int(result.get("max_attempts") if result else None, node_events, "max_attempts"),
            "retry_count": sum(1 for event in node_events if event.get("type") == "node_retrying"),
            "recovered": any(event.get("type") == "node_recovered" for event in node_events),
            "connector_id": _overlay_text(result, node_events, "connector_id"),
            "connector_kind": _overlay_text(result, node_events, "connector_kind"),
            "connector_status": _overlay_text(result, node_events, "connector_status"),
            "error": _overlay_error(result, node_events),
            "audit_event_count": len(node_audit_events),
        }
        overlays[node_id] = overlay
    return overlays


def _events_by_node(events: object) -> Dict[str, List[Dict[str, object]]]:
    grouped: Dict[str, List[Dict[str, object]]] = {}
    if not isinstance(events, list):
        return grouped
    for event in events:
        if not isinstance(event, dict):
            continue
        node_id = str(event.get("node_id", ""))
        if not node_id:
            continue
        grouped.setdefault(node_id, []).append(event)
    return grouped


def _node_result(run_state: Optional[RunState], node_id: str) -> Dict[str, object]:
    if not isinstance(run_state, dict):
        return {}
    node_results = run_state.get("node_results", {})
    if not isinstance(node_results, dict):
        return {}
    result = node_results.get(node_id)
    return result if isinstance(result, dict) else {}


def _overlay_int(explicit: object, events: List[Dict[str, object]], key: str) -> int:
    if explicit not in (None, ""):
        try:
            return int(explicit)
        except (TypeError, ValueError):
            return 0
    for event in reversed(events):
        if event.get(key) not in (None, ""):
            try:
                return int(event.get(key))
            except (TypeError, ValueError):
                return 0
    return 0


def _overlay_text(result: Dict[str, object], events: List[Dict[str, object]], key: str) -> str:
    if key in {"connector_id", "connector_kind"}:
        connector = result.get("connector", {})
        if isinstance(connector, dict) and connector.get(key.replace("connector_", "")):
            return str(connector.get(key.replace("connector_", "")))
    for event in reversed(events):
        if event.get(key) not in (None, ""):
            return str(event.get(key))
    return ""


def _overlay_error(result: Dict[str, object], events: List[Dict[str, object]]) -> str:
    for key in ("last_error", "error"):
        if result.get(key):
            return str(result.get(key))
    for event in reversed(events):
        if event.get("error"):
            return str(event.get("error"))
    return ""


def _run_overlay_summary(
    run_state: Optional[RunState],
    overlay_by_node: Dict[str, Dict[str, object]],
) -> Dict[str, object]:
    if not isinstance(run_state, dict):
        return {}
    return {
        "run_id": str(run_state.get("run_id", "")),
        "status": str(run_state.get("status", "")),
        "current_node": str(run_state.get("current_node", "")),
        "trigger": _compact_trigger(run_state),
        "node_count": len(overlay_by_node),
        "nodes": copy.deepcopy(overlay_by_node),
    }


def _compact_trigger(run_state: RunState) -> Dict[str, object]:
    context = run_state.get("context", {})
    if not isinstance(context, dict):
        return {}
    trigger = context.get("trigger", {})
    if not isinstance(trigger, dict):
        return {}
    input_keys = trigger.get("input_keys", [])
    if not isinstance(input_keys, list):
        input_keys = []
    return {
        "trigger_id": str(trigger.get("trigger_id", "")),
        "source": str(trigger.get("source", "")),
        "idempotency_key": str(trigger.get("idempotency_key", "")),
        "input_keys": [str(key) for key in input_keys],
    }


def apply_litegraph_edits_to_workflow(workflow: Workflow, graph: LiteGraph) -> Workflow:
    """Apply safe LiteGraph parameter edits back to Workflow DSL.

    This write-back intentionally preserves workflow topology. Node ids, edges,
    transitions, source metadata, guards, policies, and connector identities
    stay in the Workflow DSL. The LiteGraph view may update only allowlisted
    authoring parameters.
    """
    workflow_nodes = _workflow_nodes(workflow)
    graph_nodes = _graph_nodes(graph)
    _assert_matching_node_ids(workflow_nodes, graph_nodes)
    _assert_matching_topology(workflow, graph)

    graph_by_workflow_id = {
        str(node["properties"]["workflow_node_id"]): node
        for node in graph_nodes
        if isinstance(node.get("properties"), dict)
    }
    updated = copy.deepcopy(workflow)
    for node in updated.get("nodes", []):
        if not isinstance(node, dict) or not node.get("id"):
            continue
        graph_node = graph_by_workflow_id[str(node["id"])]
        title = str(graph_node.get("title") or "").strip()
        if not title:
            raise ValueError(f"graph node {node['id']} title must not be empty")
        node["title"] = title
        properties = graph_node.get("properties", {})
        if isinstance(properties, dict):
            description = str(properties.get("description") or "")
            if description or "description" in node:
                node["description"] = description
            _apply_action_edits(node, properties.get("action"))
            _apply_retry_edits(node, properties.get("retry"))
            _apply_connector_edits(node, properties.get("connector"))
    return updated


def _apply_action_edits(node: Dict[str, object], graph_action: object) -> None:
    action = node.get("action")
    if action is None or graph_action is None:
        return
    if not isinstance(action, dict) or not isinstance(graph_action, dict):
        raise ValueError(f"{node['id']} action must remain an object")
    if graph_action.get("kind", action.get("kind")) != action.get("kind"):
        raise ValueError(f"{node['id']} action kind cannot be changed")
    for key in ("prompt", "instruction"):
        if key in graph_action and (key in action or _action_kind_supports_key(action.get("kind"), key)):
            action[key] = str(graph_action.get(key) or "")


def _action_kind_supports_key(kind: object, key: str) -> bool:
    return (kind == "human_approval" and key == "prompt") or (
        kind in {"tool_call", "verification", "agent_instruction"} and key == "instruction"
    )


def _apply_retry_edits(node: Dict[str, object], graph_retry: object) -> None:
    retry = node.get("retry")
    if retry is None or graph_retry is None:
        return
    if not isinstance(retry, dict) or not isinstance(graph_retry, dict):
        raise ValueError(f"{node['id']} retry must remain an object")
    if "max_attempts" in graph_retry:
        retry["max_attempts"] = _non_negative_int(graph_retry["max_attempts"], f"{node['id']} retry.max_attempts")


def _apply_connector_edits(node: Dict[str, object], graph_connector: object) -> None:
    connector = node.get("connector")
    if connector is None or graph_connector is None:
        return
    if not isinstance(connector, dict) or not isinstance(graph_connector, dict):
        raise ValueError(f"{node['id']} connector must remain an object")
    if graph_connector.get("id") != connector.get("id") or graph_connector.get("kind") != connector.get("kind"):
        raise ValueError(f"{node['id']} connector identity cannot be changed")
    if connector.get("id") != "http" or "request" not in graph_connector:
        return
    graph_request = graph_connector.get("request")
    if graph_request is None:
        return
    if not isinstance(graph_request, dict):
        raise ValueError(f"{node['id']} connector.request must remain an object")
    request = connector.setdefault("request", {})
    if not isinstance(request, dict):
        raise ValueError(f"{node['id']} connector.request must remain an object")
    for key in ("method", "url"):
        if key in graph_request:
            request[key] = str(graph_request.get(key) or "")
    if "headers" in graph_request:
        if not isinstance(graph_request["headers"], dict):
            raise ValueError(f"{node['id']} connector.request.headers must be an object")
        request["headers"] = copy.deepcopy(graph_request["headers"])
    if "body" in graph_request:
        request["body"] = copy.deepcopy(graph_request["body"])
    if "timeout_ms" in graph_request:
        request["timeout_ms"] = _non_negative_int(
            graph_request["timeout_ms"],
            f"{node['id']} connector.request.timeout_ms",
        )


def _non_negative_int(value: object, label: str) -> int:
    try:
        integer = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a non-negative integer")
    if integer < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return integer


def _workflow_nodes(workflow: Workflow) -> List[Dict[str, object]]:
    nodes = workflow.get("nodes", [])
    if not isinstance(nodes, list):
        return []
    return [node for node in nodes if isinstance(node, dict) and node.get("id")]


def _graph_nodes(graph: LiteGraph) -> List[Dict[str, object]]:
    nodes = graph.get("nodes", [])
    if not isinstance(nodes, list):
        raise ValueError("LiteGraph graph.nodes must be a list")
    return [node for node in nodes if isinstance(node, dict)]


def _workflow_edges(workflow: Workflow, nodes: List[Dict[str, object]]) -> List[Dict[str, object]]:
    edges = workflow.get("edges", [])
    if isinstance(edges, list) and edges:
        return [
            edge
            for edge in edges
            if isinstance(edge, dict) and edge.get("from") is not None and edge.get("to") is not None
        ]

    derived_edges = []
    for node in nodes:
        node_id = node.get("id")
        for transition, label in (("on_success", "success"), ("on_failure", "failure")):
            target = node.get(transition)
            if target:
                derived_edges.append(
                    {
                        "id": f"derived_{node_id}_{label}",
                        "from": node_id,
                        "to": target,
                        "label": label,
                    }
                )
    return derived_edges


def _assert_matching_node_ids(
    workflow_nodes: List[Dict[str, object]],
    graph_nodes: List[Dict[str, object]],
) -> None:
    workflow_ids = {str(node["id"]) for node in workflow_nodes}
    graph_ids = []
    for node in graph_nodes:
        properties = node.get("properties", {})
        if not isinstance(properties, dict) or not properties.get("workflow_node_id"):
            raise ValueError("LiteGraph node is missing properties.workflow_node_id")
        graph_ids.append(str(properties["workflow_node_id"]))

    if len(graph_ids) != len(set(graph_ids)) or workflow_ids != set(graph_ids):
        raise ValueError("graph node set does not match workflow DSL")


def _assert_matching_topology(workflow: Workflow, graph: LiteGraph) -> None:
    workflow_nodes = _workflow_nodes(workflow)
    workflow_edges = _workflow_edges(workflow, workflow_nodes)
    expected = {
        (
            str(edge["from"]),
            str(edge["to"]),
            "failure" if str(edge.get("label") or "").lower() == "failure" else "success",
        )
        for edge in workflow_edges
    }
    actual = _graph_edge_set(graph)
    if expected != actual:
        raise ValueError("graph topology does not match workflow DSL")


def _graph_edge_set(graph: LiteGraph) -> set:
    graph_nodes = _graph_nodes(graph)
    graph_nodes_by_id = {node.get("id"): node for node in graph_nodes}
    graph_workflow_ids = {
        node.get("id"): str(node.get("properties", {}).get("workflow_node_id"))
        for node in graph_nodes
        if isinstance(node.get("properties"), dict)
    }

    edges = set()
    for link in _graph_links(graph):
        normalized = _normalize_graph_link(link)
        if normalized is None:
            continue
        source_graph_id, source_slot, target_graph_id = normalized
        source_node = graph_nodes_by_id.get(source_graph_id)
        if not isinstance(source_node, dict):
            continue
        source_outputs = source_node.get("outputs", [])
        output_name = "success"
        if isinstance(source_outputs, list) and 0 <= source_slot < len(source_outputs):
            output = source_outputs[source_slot]
            if isinstance(output, dict):
                output_name = str(output.get("name") or "success")
        if output_name != "failure":
            output_name = "success"
        if source_graph_id in graph_workflow_ids and target_graph_id in graph_workflow_ids:
            edges.add((graph_workflow_ids[source_graph_id], graph_workflow_ids[target_graph_id], output_name))
    return edges


def _graph_links(graph: LiteGraph) -> List[object]:
    links = graph.get("links", [])
    if isinstance(links, list):
        return [link for link in links if isinstance(link, (list, dict))]
    if isinstance(links, dict):
        return [link for link in links.values() if isinstance(link, (list, dict))]
    return []


def _normalize_graph_link(link: object) -> Optional[Tuple[object, int, object]]:
    try:
        if isinstance(link, list) and len(link) >= 5:
            return link[1], int(link[2]), link[3]
        if isinstance(link, dict):
            return link.get("origin_id"), int(link.get("origin_slot", 0)), link.get("target_id")
    except (TypeError, ValueError):
        return None
    return None


def _litegraph_node(
    node: Dict[str, object],
    graph_id: int,
    run_state: Optional[RunState],
    run_overlay: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    node_id = str(node["id"])
    node_type = str(node.get("type") or "step")
    has_success = bool(node.get("on_success"))
    has_failure = bool(node.get("on_failure"))
    source = _source_metadata(node)

    properties = {
        "workflow_node_id": node_id,
        "node_type": node_type,
        "description": str(node.get("description") or ""),
        "run_status": _run_status(node_id, run_state),
        "source": source,
        "requires": copy.deepcopy(node.get("requires", [])),
        "produces": copy.deepcopy(node.get("produces", [])),
        "guard": copy.deepcopy(node.get("guard")),
        "action": copy.deepcopy(node.get("action")),
        "retry": copy.deepcopy(node.get("retry")),
        "connector": copy.deepcopy(node.get("connector")),
    }
    if run_overlay:
        properties["run_overlay"] = copy.deepcopy(run_overlay)

    return {
        "id": graph_id,
        "type": f"skill2workflow/{node_type}",
        "pos": _node_position(graph_id, node_type),
        "size": [260, 110],
        "flags": {},
        "order": graph_id,
        "mode": 0,
        "title": str(node.get("title") or node_id),
        "inputs": [] if node_type == "start" else [{"name": "in", "type": "flow", "link": None}],
        "outputs": _outputs(has_success, has_failure),
        "properties": properties,
    }


def _outputs(has_success: bool, has_failure: bool) -> List[Dict[str, object]]:
    outputs = []
    if has_success:
        outputs.append({"name": "success", "type": "flow", "links": []})
    if has_failure:
        outputs.append({"name": "failure", "type": "flow", "links": []})
    return outputs


def _source_metadata(node: Dict[str, object]) -> Dict[str, object]:
    metadata = node.get("metadata", {})
    if not isinstance(metadata, dict):
        return {}
    source = metadata.get("source", {})
    if not isinstance(source, dict):
        return {}
    return source


def _node_position(graph_id: int, node_type: str) -> List[int]:
    if node_type == "failure":
        return [260 * max(graph_id - 2, 0) + 80, 260]
    if node_type == "end":
        return [260 * max(graph_id - 1, 0) + 80, 80]
    return [260 * (graph_id - 1) + 80, 80]


def _run_status(node_id: str, run_state: Optional[RunState]) -> str:
    if not run_state:
        return "not_started"

    node_results = run_state.get("node_results", {})
    if isinstance(node_results, dict):
        result = node_results.get(node_id)
        if isinstance(result, dict) and result.get("status"):
            return str(result["status"])

    if run_state.get("current_node") == node_id:
        return str(run_state.get("status") or "active")

    return "not_started"


def _source_slot(edge: Dict[str, object], source_node: Dict[str, object]) -> int:
    label = str(edge.get("label") or "").lower()
    if label == "failure" or edge.get("to") == source_node.get("on_failure"):
        return 1
    return 0


def _target_slot(existing_links: Iterable[List[object]], target_graph_id: int) -> int:
    return sum(1 for link in existing_links if len(link) > 3 and link[3] == target_graph_id)


def _attach_output_link(node: Dict[str, object], source_slot: int, link_id: int) -> None:
    outputs = node.get("outputs", [])
    if not isinstance(outputs, list) or source_slot >= len(outputs):
        return
    output = outputs[source_slot]
    if isinstance(output, dict):
        links = output.setdefault("links", [])
        if isinstance(links, list):
            links.append(link_id)


def _attach_input_link(node: Dict[str, object], target_slot: int, link_id: int) -> None:
    inputs = node.get("inputs", [])
    if not isinstance(inputs, list):
        return
    while target_slot >= len(inputs):
        inputs.append({"name": f"in_{target_slot + 1}", "type": "flow", "link": None})
    input_slot = inputs[target_slot]
    if isinstance(input_slot, dict):
        input_slot["link"] = link_id


def _node_by_id(nodes: List[Dict[str, object]], node_id: str) -> Dict[str, object]:
    for node in nodes:
        if node.get("id") == node_id:
            return node
    return {}
