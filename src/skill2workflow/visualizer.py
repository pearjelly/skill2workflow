"""Convert between Workflow DSL documents and LiteGraph-compatible graph JSON."""

from __future__ import annotations

import copy
from typing import Dict, Iterable, List, Optional, Tuple


LiteGraph = Dict[str, object]
Workflow = Dict[str, object]
RunState = Dict[str, object]


def workflow_to_litegraph(workflow: Workflow, run_state: Optional[RunState] = None) -> LiteGraph:
    """Return a LiteGraph graph representation for a Workflow DSL document.

    The Workflow DSL remains the execution source of truth. This function only
    creates a view model that LiteGraph can render and annotate.
    """
    nodes = _workflow_nodes(workflow)
    edges = _workflow_edges(workflow, nodes)
    node_id_map = {str(node["id"]): index for index, node in enumerate(nodes, start=1)}
    graph_nodes = [_litegraph_node(node, node_id_map[str(node["id"])], run_state) for node in nodes]

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
        "extra": {
            "source_schema_version": workflow.get("schema_version"),
            "truth_source": "workflow_dsl",
            "source_workflow": copy.deepcopy(workflow),
        },
    }


def apply_litegraph_edits_to_workflow(workflow: Workflow, graph: LiteGraph) -> Workflow:
    """Apply safe LiteGraph parameter edits back to Workflow DSL.

    This write-back intentionally preserves workflow topology. Node ids, edges,
    transitions, source metadata, guards, policies, and execution semantics stay
    in the Workflow DSL. The LiteGraph view may update only node title and
    description.
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
    return updated


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
) -> Dict[str, object]:
    node_id = str(node["id"])
    node_type = str(node.get("type") or "step")
    has_success = bool(node.get("on_success"))
    has_failure = bool(node.get("on_failure"))
    source = _source_metadata(node)

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
        "properties": {
            "workflow_node_id": node_id,
            "node_type": node_type,
            "description": str(node.get("description") or ""),
            "run_status": _run_status(node_id, run_state),
            "source": source,
            "requires": node.get("requires", []),
            "produces": node.get("produces", []),
            "guard": node.get("guard"),
            "action": node.get("action"),
            "retry": node.get("retry"),
        },
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
