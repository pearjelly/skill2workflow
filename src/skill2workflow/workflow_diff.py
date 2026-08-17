"""Value-free structural Workflow DSL diff helpers.

The same structural comparison is used for published-version review and for
portable bundle review.  Keeping it in one dependency-light module prevents
the two operator paths from drifting into different notions of change.
"""

from __future__ import annotations

from typing import Dict, List


Workflow = Dict[str, object]


def workflow_diff_changes(
    from_workflow: Workflow, to_workflow: Workflow
) -> Dict[str, object]:
    """Return bounded structural changes without copying workflow values."""

    from_meta = from_workflow.get("workflow", {})
    to_meta = to_workflow.get("workflow", {})
    workflow_changed = _canonical_without(
        from_meta, {"id", "version", "status"}
    ) != _canonical_without(to_meta, {"id", "version", "status"})
    entry_changed = from_workflow.get("entry") != to_workflow.get("entry")
    input_schema_changed = _field_changed(from_workflow, to_workflow, "input_schema")
    policies_changed = _field_changed(from_workflow, to_workflow, "policies")
    excluded = {
        "schema_version",
        "workflow",
        "entry",
        "nodes",
        "edges",
        "input_schema",
        "policies",
    }
    other_changed = _canonical_without(from_workflow, excluded) != _canonical_without(
        to_workflow, excluded
    )
    node_changes = _named_item_changes(from_workflow.get("nodes"), to_workflow.get("nodes"))
    edge_changes = _named_item_changes(from_workflow.get("edges"), to_workflow.get("edges"))
    sections = []
    for name, changed in (
        ("workflow", workflow_changed),
        ("entry", entry_changed),
        ("input_schema", input_schema_changed),
        ("policies", policies_changed),
        ("nodes", bool(node_changes["added"] or node_changes["removed"] or node_changes["changed"])),
        ("edges", bool(edge_changes["added"] or edge_changes["removed"] or edge_changes["changed"])),
        ("other", other_changed),
    ):
        if changed:
            sections.append(name)
    return {
        "sections": sections,
        "workflow_changed": workflow_changed,
        "entry_changed": entry_changed,
        "input_schema_changed": input_schema_changed,
        "policies_changed": policies_changed,
        "other_changed": other_changed,
        "nodes": node_changes,
        "edges": edge_changes,
    }


def _named_item_changes(from_value: object, to_value: object) -> Dict[str, List[str]]:
    from_items = _named_item_map(from_value)
    to_items = _named_item_map(to_value)
    added = sorted(set(to_items) - set(from_items))
    removed = sorted(set(from_items) - set(to_items))
    changed = sorted(
        key
        for key in set(from_items) & set(to_items)
        if _canonical_without(from_items[key], {"id"})
        != _canonical_without(to_items[key], {"id"})
    )
    return {"added": added, "removed": removed, "changed": changed}


def _named_item_map(value: object) -> Dict[str, Dict[str, object]]:
    if not isinstance(value, list):
        return {}
    result: Dict[str, Dict[str, object]] = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        result[str(item["id"])] = item
    return result


def _field_changed(
    from_value: Dict[str, object], to_value: Dict[str, object], key: str
) -> bool:
    return _field_marker(from_value, key) != _field_marker(to_value, key)


def _field_marker(value: Dict[str, object], key: str) -> object:
    return {"present": key in value, "value": value.get(key)}


def _canonical_without(value: object, excluded: set) -> object:
    if not isinstance(value, dict):
        return value
    return {key: item for key, item in value.items() if key not in excluded}
