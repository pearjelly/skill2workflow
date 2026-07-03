"""Read-only control-plane snapshot helpers for local operator UIs."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .control_plane import LocalControlPlane


SNAPSHOT_SCHEMA_VERSION = "skill2workflow-control-snapshot-0.1.0"


def build_control_snapshot(state_dir: Path, storage: str = "json") -> Dict[str, object]:
    """Build a read-only control-plane snapshot from existing local state."""
    control = LocalControlPlane(Path(state_dir), storage=storage)
    workflows = control.list_workflows()
    runs = [_run_summary(control, run) for run in control.list_runs()]
    audit_events = control.list_audit_events()
    connectors = control.list_connectors()

    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "summary": {
            "workflow_count": len(workflows),
            "run_count": len(runs),
            "audit_event_count": len(audit_events),
            "connector_count": len(connectors),
            "status_counts": _status_counts(workflows),
            "run_status_counts": _run_status_counts(runs),
        },
        "workflows": workflows,
        "runs": runs,
        "audit_events": audit_events,
        "connectors": connectors,
        "version_comparisons": _version_comparisons(control, workflows),
    }


def _run_summary(control: LocalControlPlane, run: Dict[str, object]) -> Dict[str, object]:
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
    return {
        "run_id": run_id,
        "workflow_id": run.get("workflow_id", ""),
        "workflow_version": run.get("workflow_version", ""),
        "status": run.get("status", ""),
        "current_node": run.get("current_node", ""),
        "event_count": len(events),
        "node_result_count": len(node_results),
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


def _items(value: Dict[str, object], key: str) -> List[object]:
    items = value.get(key, [])
    return items if isinstance(items, list) else []
