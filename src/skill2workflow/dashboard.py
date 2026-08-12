"""Read-only control-plane snapshot helpers for local operator UIs."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .control_plane import LocalControlPlane
from .visualizer import run_overlay_for_nodes


SNAPSHOT_SCHEMA_VERSION = "skill2workflow-control-snapshot-0.1.0"
MAX_RECENT_EVENTS = 5
MAX_LIVE_SNAPSHOT_BYTES = 1024 * 1024


def build_control_snapshot(
    state_dir: Path,
    storage: str = "json",
    connector_runtime=None,
    max_items: Optional[int] = None,
) -> Dict[str, object]:
    """Build a read-only control-plane snapshot from existing local state."""
    control = LocalControlPlane(Path(state_dir), storage=storage, connector_runtime=connector_runtime)
    return build_control_snapshot_from_control(control, max_items=max_items)


def build_control_snapshot_from_control(
    control: LocalControlPlane,
    max_items: Optional[int] = None,
) -> Dict[str, object]:
    """Build a snapshot from an existing control plane with an optional tail window."""

    if max_items is not None and (
        isinstance(max_items, bool) or not isinstance(max_items, int) or max_items <= 0
    ):
        raise ValueError("max_items must be a positive integer")

    bounded_sqlite = bool(
        max_items is not None
        and hasattr(control.store, "snapshot_window")
        and hasattr(control.executor.store, "snapshot_window")
    )
    if bounded_sqlite:
        control_window = control.store.snapshot_window(max_items)
        run_window = control.executor.snapshot_window(max_items)
        workflows = control_window["workflows"]
        audit_events = control_window["audit_events"]
        selected_runs = run_window["items"]
        workflow_total = int(control_window["workflow_total"])
        run_total = int(run_window["total"])
        audit_total = int(control_window["audit_total"])
        workflow_status_counts = control_window["workflow_status_counts"]
        run_status_counts = run_window["status_counts"]
    else:
        all_workflows = control.list_workflows()
        all_audit_events = control.list_audit_events()
        all_runs = control.list_runs()
        workflows = _tail(all_workflows, max_items)
        audit_events = _tail(all_audit_events, max_items)
        selected_runs = _tail(all_runs, max_items)
        workflow_total = len(all_workflows)
        run_total = len(all_runs)
        audit_total = len(all_audit_events)
        workflow_status_counts = _status_counts(all_workflows)
        run_status_counts = _run_status_counts(all_runs)
    all_connectors = control.list_connectors()
    connectors = _tail(all_connectors, max_items)
    runs = [_run_summary(control, run, audit_events) for run in selected_runs]
    all_version_comparisons = _version_comparisons(control, workflows)
    version_comparisons = _tail(all_version_comparisons, max_items)

    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "summary": {
            "workflow_count": workflow_total,
            "run_count": run_total,
            "audit_event_count": audit_total,
            "connector_count": len(all_connectors),
            "status_counts": workflow_status_counts,
            "run_status_counts": run_status_counts,
        },
        "workflows": workflows,
        "runs": runs,
        "audit_events": audit_events,
        "connectors": connectors,
        "version_comparisons": version_comparisons,
        "operator_insights": _operator_insights(runs, audit_events, version_comparisons),
    }
    if max_items is not None:
        snapshot["window"] = {
            "max_items": max_items,
            "workflows": _window(workflow_total, len(workflows)),
            "runs": _window(run_total, len(runs)),
            "audit_events": _window(audit_total, len(audit_events)),
            "connectors": _window(len(all_connectors), len(connectors)),
            "version_comparisons": _window(
                len(all_version_comparisons), len(version_comparisons)
            ),
        }
    return snapshot


def _tail(items: List[object], max_items: Optional[int]) -> List[object]:
    if max_items is None or len(items) <= max_items:
        return list(items)
    return list(items[-max_items:])


def _window(total: int, returned: int) -> Dict[str, object]:
    return {
        "total": total,
        "returned": returned,
        "truncated": returned < total,
    }


def _run_summary(
    control: LocalControlPlane,
    run: Dict[str, object],
    audit_events: Optional[List[Dict[str, object]]] = None,
) -> Dict[str, object]:
    run_id = str(run.get("run_id", ""))
    detail = control.get_run(run_id) if run_id else run
    events = run.get("events", [])
    if not events:
        events = detail.get("events", [])
    if not isinstance(events, list):
        events = []
    node_results = run.get("node_results", {})
    if not node_results:
        node_results = detail.get("node_results", {})
    if not isinstance(node_results, dict):
        node_results = {}
    workflow = detail.get("workflow", {})
    nodes = _items(workflow, "nodes") if isinstance(workflow, dict) else []
    node_ids = [str(node.get("id")) for node in nodes if isinstance(node, dict) and node.get("id")]
    run_audit_events = [
        event
        for event in (audit_events or [])
        if str(event.get("run_id", "")) == run_id
    ]
    return {
        "run_id": run_id,
        "workflow_id": run.get("workflow_id", ""),
        "workflow_version": run.get("workflow_version", ""),
        "status": run.get("status", ""),
        "current_node": run.get("current_node", ""),
        "event_count": len(events),
        "node_result_count": len(node_results),
        "node_overlays": run_overlay_for_nodes(node_ids, detail, run_audit_events),
        "created_at": run.get("created_at", ""),
        "updated_at": run.get("updated_at", ""),
    }


def _status_counts(workflows: List[Dict[str, object]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for record in workflows:
        status = str(record.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _run_status_counts(runs: List[Dict[str, object]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for run in runs:
        status = str(run.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _version_comparisons(
    control: LocalControlPlane,
    workflows: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    by_workflow: Dict[str, List[Dict[str, object]]] = {}
    for record in workflows:
        workflow_id = str(record.get("workflow_id", ""))
        by_workflow.setdefault(workflow_id, []).append(record)

    comparisons: List[Dict[str, object]] = []
    for workflow_id, records in sorted(by_workflow.items()):
        ordered = sorted(records, key=lambda record: str(record.get("version", "")))
        for previous, current in zip(ordered, ordered[1:]):
            previous_version = str(previous.get("version", ""))
            current_version = str(current.get("version", ""))
            previous_workflow = control.get_workflow(workflow_id, previous_version)
            current_workflow = control.get_workflow(workflow_id, current_version)
            previous_nodes = _items(previous_workflow, "nodes")
            current_nodes = _items(current_workflow, "nodes")
            previous_edges = _items(previous_workflow, "edges")
            current_edges = _items(current_workflow, "edges")
            comparisons.append(
                {
                    "workflow_id": workflow_id,
                    "versions": [previous_version, current_version],
                    "from_status": previous.get("status", ""),
                    "to_status": current.get("status", ""),
                    "checksum_changed": previous.get("checksum") != current.get("checksum"),
                    "node_count_delta": len(current_nodes) - len(previous_nodes),
                    "edge_count_delta": len(current_edges) - len(previous_edges),
                }
            )
    return comparisons


def _operator_insights(
    runs: List[Dict[str, object]],
    audit_events: List[Dict[str, object]],
    version_comparisons: List[Dict[str, object]],
) -> Dict[str, object]:
    waiting_runs = [run for run in runs if str(run.get("status", "")) == "waiting"]
    failed_runs = [run for run in runs if str(run.get("status", "")) == "failed"]
    interrupted_runs = [
        run for run in runs if str(run.get("status", "")) == "interrupted"
    ]
    connector_failures = [
        event for event in audit_events if str(event.get("type", "")) == "connector_failed"
    ]
    version_changes = [
        _version_change_summary(comparison)
        for comparison in version_comparisons
        if bool(comparison.get("checksum_changed"))
    ]

    attention_items: List[Dict[str, object]] = []
    for run in waiting_runs:
        attention_items.append(_run_attention_item(run, "waiting_run", "warning"))
    for run in failed_runs:
        attention_items.append(_run_attention_item(run, "failed_run", "critical"))
    for run in interrupted_runs:
        attention_items.append(
            _run_attention_item(run, "interrupted_run", "critical")
        )
    for event in connector_failures:
        attention_items.append(_connector_failure_attention_item(event))

    return {
        "attention_counts": {
            "waiting_runs": len(waiting_runs),
            "failed_runs": len(failed_runs),
            "interrupted_runs": len(interrupted_runs),
            "connector_failures": len(connector_failures),
            "version_changes": len(version_changes),
        },
        "attention_items": attention_items,
        "recent_events": audit_events[-MAX_RECENT_EVENTS:],
        "connector_event_counts": _event_counts(
            [event for event in audit_events if str(event.get("type", "")).startswith("connector_")]
        ),
        "version_changes": version_changes,
    }


def _run_attention_item(run: Dict[str, object], kind: str, severity: str) -> Dict[str, object]:
    workflow_ref = f"{run.get('workflow_id', '')}@{run.get('workflow_version', '')}"
    return {
        "kind": kind,
        "severity": severity,
        "run_id": run.get("run_id", ""),
        "workflow_id": run.get("workflow_id", ""),
        "workflow_version": run.get("workflow_version", ""),
        "status": run.get("status", ""),
        "current_node": run.get("current_node", ""),
        "message": f"{workflow_ref} is {run.get('status', '')}",
    }


def _connector_failure_attention_item(event: Dict[str, object]) -> Dict[str, object]:
    workflow_ref = f"{event.get('workflow_id', '')}@{event.get('workflow_version', '')}"
    return {
        "kind": "connector_failure",
        "severity": "critical",
        "run_id": event.get("run_id", ""),
        "workflow_id": event.get("workflow_id", ""),
        "workflow_version": event.get("workflow_version", ""),
        "node_id": event.get("node_id", ""),
        "connector_id": event.get("connector_id", ""),
        "connector_kind": event.get("connector_kind", ""),
        "timestamp": event.get("timestamp", ""),
        "message": f"{workflow_ref} connector {event.get('connector_id', '')} failed",
    }


def _version_change_summary(comparison: Dict[str, object]) -> Dict[str, object]:
    versions = comparison.get("versions", [])
    if not isinstance(versions, list):
        versions = []
    return {
        "kind": "version_change",
        "workflow_id": comparison.get("workflow_id", ""),
        "versions": versions,
        "label": " -> ".join(str(version) for version in versions),
        "node_count_delta": comparison.get("node_count_delta", 0),
        "edge_count_delta": comparison.get("edge_count_delta", 0),
        "checksum_changed": comparison.get("checksum_changed", False),
    }


def _event_counts(events: List[Dict[str, object]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for event in events:
        event_type = str(event.get("type", "unknown"))
        counts[event_type] = counts.get(event_type, 0) + 1
    return dict(sorted(counts.items()))


def _items(value: Dict[str, object], key: str) -> List[object]:
    items = value.get(key, [])
    return items if isinstance(items, list) else []
