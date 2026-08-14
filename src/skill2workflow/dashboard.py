"""Read-only control-plane snapshot helpers for local operator UIs."""

from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .control_plane import (
    LocalControlPlane,
    WORKFLOW_ARTIFACT_REPORT_SCHEMA_VERSION,
)
from .visualizer import run_overlay_for_nodes


SNAPSHOT_SCHEMA_VERSION = "skill2workflow-control-snapshot-0.1.0"
RUN_DETAIL_SCHEMA_VERSION = "skill2workflow-run-detail-0.1.0"
RUN_LIST_SCHEMA_VERSION = "skill2workflow-run-list-0.1.0"
RUN_PAGE_SCHEMA_VERSION = "skill2workflow-run-list-0.2.0"
SUPPORT_BUNDLE_SCHEMA_VERSION = "skill2workflow-support-bundle-0.1.0"
WORKFLOW_INVENTORY_SCHEMA_VERSION = "skill2workflow-workflow-inventory-0.1.0"
RECURRING_SCHEDULE_LIST_SCHEMA_VERSION = "skill2workflow-recurring-schedule-list-0.1.0"
RECURRING_SCHEDULE_ACTION_SCHEMA_VERSION = "skill2workflow-recurring-schedule-action-0.1.0"
RECURRING_SCHEDULE_DISPATCH_LIST_SCHEMA_VERSION = "skill2workflow-recurring-schedule-dispatch-list-0.1.0"
MAX_RECENT_EVENTS = 5
MAX_LIVE_SNAPSHOT_BYTES = 1024 * 1024
MAX_OFFLINE_SNAPSHOT_ITEMS = 1000
MAX_RUN_DETAIL_EVENTS = 50
MAX_RUN_LIST_ITEMS = 100
MAX_RUN_PAGE_ITEMS = 100
MAX_RECURRING_SCHEDULE_LIST_ITEMS = 100
MAX_RECURRING_SCHEDULE_DISPATCH_LIST_ITEMS = 100
MAX_SUPPORT_BUNDLE_BYTES = 128 * 1024
MAX_REMOTE_WORKFLOW_ARTIFACT_REPORT_ISSUES = 64
MAX_WORKFLOW_INVENTORY_ITEMS = 100


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
        isinstance(max_items, bool)
        or not isinstance(max_items, int)
        or max_items <= 0
        or max_items > MAX_OFFLINE_SNAPSHOT_ITEMS
    ):
        raise ValueError("max_items must be an integer from 1 through 1000")

    bounded_storage = bool(
        max_items is not None
        and hasattr(control.store, "snapshot_window")
        and hasattr(control.executor.store, "snapshot_window")
    )
    if bounded_storage:
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


def build_run_detail(
    state_dir: Path,
    run_id: str,
    storage: str = "json",
    max_events: int = MAX_RUN_DETAIL_EVENTS,
) -> Dict[str, object]:
    """Build one bounded, operator-safe detail view without exposing run state."""

    control = LocalControlPlane(Path(state_dir), storage=storage)
    return build_run_detail_from_control(control, run_id, max_events=max_events)


def build_run_list(
    state_dir: Path,
    storage: str = "json",
    max_items: int = MAX_RUN_LIST_ITEMS,
) -> Dict[str, object]:
    """Build a bounded, operator-safe list of recent run summaries."""

    control = LocalControlPlane(Path(state_dir), storage=storage)
    return build_run_list_from_control(control, max_items=max_items)


def build_run_list_from_control(
    control: LocalControlPlane,
    max_items: int = MAX_RUN_LIST_ITEMS,
) -> Dict[str, object]:
    """Project recent runs without loading workflow, context, or result payloads."""

    if (
        isinstance(max_items, bool)
        or not isinstance(max_items, int)
        or max_items <= 0
        or max_items > MAX_RUN_LIST_ITEMS
    ):
        raise ValueError("max_items must be a positive bounded integer")
    bounded_sqlite = hasattr(control.executor.store, "snapshot_window")
    if bounded_sqlite:
        window = control.executor.snapshot_window(max_items)
        total = int(window["total"])
        selected = window["items"]
        status_counts = _fixed_run_status_counts(window.get("status_counts", {}))
    else:
        all_runs = control.list_runs()
        total = len(all_runs)
        selected = _tail(all_runs, max_items)
        status_counts = _fixed_run_status_counts(all_runs)
    runs = [_safe_run_summary(run) for run in selected if isinstance(run, dict)]
    return {
        "schema_version": RUN_LIST_SCHEMA_VERSION,
        "summary": {
            "total": total,
            "status_counts": status_counts,
        },
        "runs": runs,
        "window": {
            "max_items": max_items,
            "total": total,
            "returned": len(runs),
            "truncated": len(runs) < total,
        },
    }


def build_run_page_from_control(
    control: LocalControlPlane,
    *,
    max_items: int = MAX_RUN_PAGE_ITEMS,
    cursor: str = "",
    status: str = "",
    workflow_id: str = "",
) -> Dict[str, object]:
    """Build a filtered, cursor-paged redacted run projection for SQLite service use."""

    if (
        isinstance(max_items, bool)
        or not isinstance(max_items, int)
        or max_items <= 0
        or max_items > MAX_RUN_PAGE_ITEMS
    ):
        raise ValueError("max_items must be a positive bounded integer")
    normalized_status = str(status or "")
    if normalized_status and normalized_status not in _RUN_STATUS_VALUES[:-1]:
        raise ValueError("run page status is invalid")
    normalized_workflow_id = str(workflow_id or "")
    if len(normalized_workflow_id) > 128:
        raise ValueError("run page workflow_id is too long")
    before_updated_at, before_run_id = _decode_run_page_cursor(cursor)
    if not hasattr(control.executor, "run_page"):
        raise ValueError("run pages require sqlite storage")
    page = control.executor.run_page(
        max_items,
        before_updated_at=before_updated_at,
        before_run_id=before_run_id,
        status=normalized_status,
        workflow_id=normalized_workflow_id,
    )
    runs = [
        _safe_run_summary(run)
        for run in page.get("items", [])
        if isinstance(run, dict)
    ]
    next_cursor = None
    if page.get("has_more") and isinstance(page.get("next_cursor"), dict):
        next_cursor = _encode_run_page_cursor(page["next_cursor"])
    total = int(page.get("total", 0))
    return {
        "schema_version": RUN_PAGE_SCHEMA_VERSION,
        "summary": {
            "total": total,
            "status_counts": _fixed_run_status_counts(page.get("status_counts", {})),
        },
        "filters": {
            "status": normalized_status,
            "workflow_id": normalized_workflow_id,
        },
        "runs": runs,
        "window": {
            "max_items": max_items,
            "total": total,
            "returned": len(runs),
            "has_more": bool(page.get("has_more")),
            "next_cursor": next_cursor,
        },
    }


def build_recurring_schedule_list_from_store(
    schedule_store,
    max_items: int = MAX_RECURRING_SCHEDULE_LIST_ITEMS,
) -> Dict[str, object]:
    """Project recurring schedule definitions without exposing trigger input."""

    if (
        isinstance(max_items, bool)
        or not isinstance(max_items, int)
        or max_items <= 0
        or max_items > MAX_RECURRING_SCHEDULE_LIST_ITEMS
    ):
        raise ValueError("max_items must be a positive bounded integer")
    if hasattr(schedule_store, "list_bounded"):
        bounded = schedule_store.list_bounded(max_items)
        selected = bounded["items"]
        total = int(bounded["total"])
        status_counts = dict(bounded["status_counts"])
    else:
        schedules = schedule_store.list()
        total = len(schedules)
        selected = schedules[-max_items:]
        status_counts = {"active": 0, "disabled": 0, "other": 0}
        for schedule in schedules:
            meta = schedule.get("schedule") if isinstance(schedule, dict) else None
            if not isinstance(meta, dict):
                status_counts["other"] += 1
                continue
            status = _safe_string(meta.get("status", ""))
            status_counts[status if status in {"active", "disabled"} else "other"] += 1
    projected = []
    for schedule in selected:
        if not isinstance(schedule, dict):
            continue
        meta = schedule.get("schedule")
        if not isinstance(meta, dict):
            continue
        status = _safe_string(meta.get("status", ""))
        normalized_status = status if status in {"active", "disabled"} else "other"
        projected.append(
            {
                "schedule_id": _safe_string(meta.get("id", "")),
                "workflow_id": _safe_string(meta.get("workflow_id", "")),
                "workflow_version": _safe_string(meta.get("version", "")),
                "status": normalized_status,
                "enabled": bool(meta.get("enabled", False)),
                "starts_at": _safe_string(meta.get("starts_at", "")),
                "next_run_at": _safe_string(meta.get("next_run_at", "")),
                "interval_seconds": _safe_non_negative_int(meta.get("interval_seconds", 0)),
                "missed_run_policy": _safe_string(meta.get("missed_run_policy", "")),
                "last_scheduled_for": _safe_string(meta.get("last_scheduled_for", "")),
                "last_run_id": _safe_string(meta.get("last_run_id", "")),
                "last_trigger_id": _safe_string(meta.get("last_trigger_id", "")),
            }
        )
    return {
        "schema_version": RECURRING_SCHEDULE_LIST_SCHEMA_VERSION,
        "summary": {
            "total": total,
            "status_counts": status_counts,
        },
        "schedules": projected,
        "window": {
            "max_items": max_items,
            "total": total,
            "returned": len(projected),
            "truncated": len(projected) < total,
        },
    }


def build_recurring_schedule_dispatch_list_from_store(
    schedule_store,
    schedule_id: str = "",
    max_items: int = MAX_RECURRING_SCHEDULE_DISPATCH_LIST_ITEMS,
) -> Dict[str, object]:
    """Project recent dispatch metadata without lease or trigger payloads."""

    if (
        isinstance(max_items, bool)
        or not isinstance(max_items, int)
        or max_items <= 0
        or max_items > MAX_RECURRING_SCHEDULE_DISPATCH_LIST_ITEMS
    ):
        raise ValueError("max_items must be a positive bounded integer")
    normalized_schedule_id = _safe_string(schedule_id)
    if hasattr(schedule_store, "list_dispatches_bounded"):
        bounded = schedule_store.list_dispatches_bounded(
            max_items,
            schedule_id=normalized_schedule_id,
        )
        selected = bounded["items"]
        total = int(bounded["total"])
        status_counts = dict(bounded["status_counts"])
    else:
        records = schedule_store.list_dispatches(schedule_id=normalized_schedule_id)
        total = len(records)
        selected = records[-max_items:]
        status_counts = {
            "claimed": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0,
            "uncertain": 0,
            "other": 0,
        }
        for record in records:
            status = _safe_string(record.get("status", "")) if isinstance(record, dict) else ""
            status_counts[status if status in status_counts and status != "other" else "other"] += 1
    projected = []
    for record in selected:
        if not isinstance(record, dict):
            continue
        status = _safe_string(record.get("status", ""))
        normalized_status = status if status in {
            "claimed", "completed", "failed", "skipped", "uncertain"
        } else "other"
        projected.append(
            {
                "dispatch_id": _safe_string(record.get("dispatch_id", "")),
                "schedule_id": _safe_string(record.get("schedule_id", "")),
                "scheduled_for": _safe_string(record.get("scheduled_for", "")),
                "status": normalized_status,
                "coalesced_occurrences": _safe_non_negative_int(
                    record.get("coalesced_occurrences", 0)
                ),
                "run_id": _safe_string(record.get("run_id", "")),
                "trigger_id": _safe_string(record.get("trigger_id", "")),
                "error_type": _safe_dispatch_error_type(record.get("error_type", "")),
                "completed_at": _safe_string(record.get("completed_at", "")),
            }
        )
    return {
        "schema_version": RECURRING_SCHEDULE_DISPATCH_LIST_SCHEMA_VERSION,
        "schedule_id": normalized_schedule_id,
        "summary": {
            "total": total,
            "status_counts": status_counts,
        },
        "dispatches": projected,
        "window": {
            "max_items": max_items,
            "total": total,
            "returned": len(projected),
            "truncated": len(projected) < total,
        },
    }


def build_workflow_artifact_report_from_control(
    control: LocalControlPlane,
    max_issues: int = MAX_REMOTE_WORKFLOW_ARTIFACT_REPORT_ISSUES,
) -> Dict[str, object]:
    """Project the value-free artifact report for a bounded remote read."""

    if (
        isinstance(max_issues, bool)
        or not isinstance(max_issues, int)
        or max_issues <= 0
        or max_issues > 256
    ):
        raise ValueError("max_issues must be a positive bounded integer")
    report = control.inspect_workflow_artifacts(max_issues=max_issues)
    summary = dict(report.get("summary", {}))
    issues = list(report.get("issues", []))
    issue_count = int(summary.get("issue_count", len(issues)))
    summary["truncated"] = bool(summary.get("truncated", False)) or len(issues) > max_issues
    return {
        "schema_version": WORKFLOW_ARTIFACT_REPORT_SCHEMA_VERSION,
        "status": report.get("status", "attention" if issue_count else "clean"),
        "summary": summary,
        "issues": issues[:max_issues],
    }


def build_workflow_inventory_from_control(
    control: LocalControlPlane,
    max_items: int = MAX_WORKFLOW_INVENTORY_ITEMS,
) -> Dict[str, object]:
    """Project bounded published-version metadata without workflow content."""

    if (
        isinstance(max_items, bool)
        or not isinstance(max_items, int)
        or max_items <= 0
        or max_items > MAX_WORKFLOW_INVENTORY_ITEMS
    ):
        raise ValueError("max_items must be a positive bounded integer")

    bounded_sqlite = hasattr(control.store, "snapshot_window")
    if bounded_sqlite:
        window = control.store.snapshot_window(max_items)
        total = int(window.get("workflow_total", 0))
        selected = list(window.get("workflows", []))
        raw_counts = window.get("workflow_status_counts", {})
    else:
        all_workflows = control.list_workflows()
        ordered = sorted(
            all_workflows,
            key=lambda record: (
                str(record.get("published_at", "")),
                str(record.get("workflow_id", "")),
                str(record.get("version", "")),
            ),
        )
        total = len(ordered)
        selected = _tail(ordered, max_items)
        raw_counts = _status_counts(ordered)

    status_counts = {"published": 0, "deprecated": 0, "other": 0}
    for status, count in (raw_counts.items() if isinstance(raw_counts, dict) else ()):
        normalized = status if status in {"published", "deprecated"} else "other"
        status_counts[normalized] += _safe_non_negative_int(count)

    versions = []
    for record in selected:
        if not isinstance(record, dict):
            raise ValueError("workflow inventory record is invalid")
        workflow_id = _inventory_reference(record.get("workflow_id"), "workflow_id")
        version = _inventory_reference(record.get("version"), "version")
        checksum = record.get("checksum")
        if (
            not isinstance(checksum, str)
            or len(checksum) != 64
            or any(char not in "0123456789abcdef" for char in checksum)
        ):
            raise ValueError("workflow inventory checksum is invalid")
        status = record.get("status")
        status = status if status in {"published", "deprecated"} else "other"
        aliases = record.get("aliases", [])
        if not isinstance(aliases, list) or len(aliases) > 16:
            raise ValueError("workflow inventory aliases are invalid")
        normalized_aliases = []
        for alias in aliases:
            if not isinstance(alias, str) or not alias or len(alias) > 64:
                raise ValueError("workflow inventory alias is invalid")
            if any(
                ord(char) < 0x20
                or ord(char) == 0x7F
                or char not in "abcdefghijklmnopqrstuvwxyz0123456789._-"
                for char in alias
            ):
                raise ValueError("workflow inventory alias is invalid")
            normalized_aliases.append(alias)
        versions.append(
            {
                "workflow_id": workflow_id,
                "version": version,
                "status": status,
                "aliases": sorted(set(normalized_aliases)),
                "checksum": checksum,
            }
        )

    return {
        "schema_version": WORKFLOW_INVENTORY_SCHEMA_VERSION,
        "summary": {
            "total": total,
            "status_counts": status_counts,
        },
        "versions": versions,
        "window": {
            "max_items": max_items,
            "total": total,
            "returned": len(versions),
            "truncated": len(versions) < total,
        },
    }


def _inventory_reference(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError(f"workflow inventory {field} is invalid")
    if any(
        ord(char) < 0x20
        or ord(char) == 0x7F
        or char in {"/", "?", "#"}
        for char in value
    ):
        raise ValueError(f"workflow inventory {field} is invalid")
    return value


def build_support_bundle_from_control(
    control: LocalControlPlane,
    telemetry,
    *,
    service_status: str,
    ready: bool,
    scheduler_lease_owned: bool,
    storage: str = "sqlite",
) -> Dict[str, object]:
    """Build one fixed, redacted diagnostic package from live service state."""

    if storage != "sqlite":
        raise ValueError("support bundle requires sqlite storage")
    if service_status not in {"starting", "ready", "draining", "stopped", "unknown"}:
        raise ValueError("support bundle service status is invalid")
    run_list = build_run_list_from_control(control)
    observability = telemetry.aggregate(
        service_status=service_status,
        ready=ready,
        scheduler_lease_owned=scheduler_lease_owned,
    )
    # Keep the 0.1.0 support-bundle contract stable when new telemetry routes
    # are added; the live metrics endpoint remains the complete route matrix.
    http_requests = dict(observability.get("http_requests", {}))
    http_requests.pop("audit_consistency", None)
    http_requests.pop("recurring_schedule_list", None)
    http_requests.pop("recurring_schedule_action", None)
    http_requests.pop("recurring_schedule_dispatch_list", None)
    http_requests.pop("workflow_artifact_report", None)
    http_requests.pop("backup_readiness", None)
    http_requests.pop("retention_readiness", None)
    http_requests.pop("operational_readiness", None)
    http_requests.pop("audit_integrity", None)
    http_requests.pop("runtime_info", None)
    http_requests.pop("workflow_release", None)
    http_requests.pop("workflow_promotion", None)
    http_requests.pop("workflow_deprecation", None)
    http_requests.pop("workflow_inventory", None)
    http_requests.pop("workflow_diff", None)
    http_requests.pop("run_page", None)
    observability = dict(observability)
    observability["http_requests"] = http_requests
    return {
        "schema_version": SUPPORT_BUNDLE_SCHEMA_VERSION,
        "service": {
            "status": service_status,
            "ready": bool(ready),
            "storage": storage,
            "scheduler_lease_owned": bool(scheduler_lease_owned),
        },
        "run_list": run_list,
        "observability": observability,
    }


_RUN_STATUS_VALUES = (
    "created",
    "running",
    "waiting",
    "completed",
    "failed",
    "cancelled",
    "interrupted",
    "other",
)


def _safe_run_summary(run: Dict[str, object]) -> Dict[str, object]:
    """Normalize one executor summary and discard every unlisted field."""

    status = _safe_string(run.get("status", ""))
    if status not in _RUN_STATUS_VALUES[:-1]:
        status = "other"
    return {
        "run_id": _safe_string(run.get("run_id", "")),
        "workflow_id": _safe_string(run.get("workflow_id", "")),
        "workflow_version": _safe_string(run.get("workflow_version", "")),
        "status": status,
        "current_node": _safe_string(run.get("current_node", "")),
        "event_count": _safe_non_negative_int(run.get("event_count", 0)),
        "node_result_count": _safe_non_negative_int(run.get("node_result_count", 0)),
    }


def _fixed_run_status_counts(value: object) -> Dict[str, int]:
    counts = {status: 0 for status in _RUN_STATUS_VALUES}
    if isinstance(value, list):
        for run in value:
            if isinstance(run, dict):
                status = _safe_string(run.get("status", ""))
                counts[status if status in _RUN_STATUS_VALUES[:-1] else "other"] += 1
    elif isinstance(value, dict):
        for status, count in value.items():
            normalized = status if status in _RUN_STATUS_VALUES[:-1] else "other"
            counts[normalized] += _safe_non_negative_int(count)
    return counts


def _encode_run_page_cursor(value: object) -> str:
    if not isinstance(value, dict) or set(value) != {"updated_at", "run_id"}:
        raise ValueError("run page cursor is invalid")
    updated_at = str(value.get("updated_at", ""))
    run_id = str(value.get("run_id", ""))
    _validate_run_page_cursor_parts(updated_at, run_id)
    raw = json.dumps(
        {"updated_at": updated_at, "run_id": run_id},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_run_page_cursor(cursor: str):
    normalized = str(cursor or "")
    if not normalized:
        return "", ""
    if len(normalized) > 512 or any(
        character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        for character in normalized
    ):
        raise ValueError("run page cursor is invalid")
    try:
        raw = base64.urlsafe_b64decode(normalized + "=" * (-len(normalized) % 4))
        value = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("run page cursor is invalid") from error
    if not isinstance(value, dict) or set(value) != {"updated_at", "run_id"}:
        raise ValueError("run page cursor is invalid")
    updated_at = str(value.get("updated_at", ""))
    run_id = str(value.get("run_id", ""))
    _validate_run_page_cursor_parts(updated_at, run_id)
    return updated_at, run_id


def _validate_run_page_cursor_parts(updated_at: str, run_id: str) -> None:
    try:
        parsed = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("run page cursor is invalid") from error
    if parsed.tzinfo is None and len(updated_at) != 19:
        raise ValueError("run page cursor is invalid")
    if not run_id.startswith("run_") or len(run_id) > 128:
        raise ValueError("run page cursor is invalid")
    if any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-" for character in run_id):
        raise ValueError("run page cursor is invalid")


def build_run_detail_from_control(
    control: LocalControlPlane,
    run_id: str,
    max_events: int = MAX_RUN_DETAIL_EVENTS,
) -> Dict[str, object]:
    """Project one run into a fixed safe contract for authenticated operators.

    The complete run contains workflow DSL, trigger context, node results, and
    connector metadata.  None of those structures cross this boundary.  Only
    bounded status evidence and an allowlisted event tail are returned.
    """

    if (
        isinstance(max_events, bool)
        or not isinstance(max_events, int)
        or max_events <= 0
        or max_events > MAX_RUN_DETAIL_EVENTS
    ):
        raise ValueError("max_events must be a positive bounded integer")
    state = control.get_run(str(run_id))
    events = state.get("events", [])
    if not isinstance(events, list):
        events = []
    # Keep the source read bounded as well as the response.  The overlay only
    # exposes the same fixed event tail, so loading the complete per-run audit
    # history would add cost without adding operator-visible information.
    audit_events = control.list_audit_events(
        run_id=str(run_id),
        limit=max_events,
    )
    workflow = state.get("workflow", {})
    node_ids = [
        node.get("id")
        for node in _items(workflow, "nodes")
        if isinstance(node, dict) and isinstance(node.get("id"), str) and node.get("id")
    ]
    current_node = _safe_string(state.get("current_node", ""))
    if current_node and current_node not in node_ids:
        node_ids.append(current_node)
    overlays = run_overlay_for_nodes(node_ids, state, audit_events)
    safe_overlays = {
        node_id: _safe_run_overlay(overlay)
        for node_id, overlay in overlays.items()
    }
    returned_events = events[-max_events:]
    start_index = len(events) - len(returned_events)
    safe_events = [
        _safe_run_event(event, sequence=start_index + index + 1)
        for index, event in enumerate(returned_events)
        if isinstance(event, dict)
    ]
    return {
        "schema_version": RUN_DETAIL_SCHEMA_VERSION,
        "run": {
            "run_id": _safe_string(state.get("run_id", "")),
            "workflow_id": _safe_string(state.get("workflow_id", "")),
            "workflow_version": _safe_string(state.get("workflow_version", "")),
            "status": _safe_string(state.get("status", "")),
            "current_node": current_node,
            "event_count": len(events),
            "node_result_count": _safe_non_negative_int(
                len(state.get("node_results", {}))
                if isinstance(state.get("node_results", {}), dict)
                else 0
            ),
            "node_overlays": safe_overlays,
            "created_at": _safe_string(state.get("created_at", "")),
            "updated_at": _safe_string(state.get("updated_at", "")),
        },
        "events": safe_events,
        "window": {
            "max_events": max_events,
            "total": len(events),
            "returned": len(safe_events),
            "truncated": len(safe_events) < len(events),
        },
    }


_RUN_OVERLAY_FIELDS = (
    "node_id",
    "status",
    "current",
    "event_count",
    "latest_event_type",
    "result_status",
    "attempts",
    "max_attempts",
    "retry_count",
    "recovered",
    "connector_id",
    "connector_kind",
    "connector_status",
    "audit_event_count",
)
_RUN_EVENT_FIELDS = (
    "sequence",
    "type",
    "node_id",
    "timestamp",
    "approved",
    "attempt",
    "max_attempts",
    "connector_id",
    "connector_kind",
    "connector_status",
    "has_error",
)


def _safe_run_overlay(overlay: Dict[str, object]) -> Dict[str, object]:
    """Keep operational overlay fields while replacing raw errors with a flag."""

    safe = {field: overlay.get(field) for field in _RUN_OVERLAY_FIELDS}
    safe["has_error"] = bool(overlay.get("error"))
    return safe


def _safe_run_event(event: Dict[str, object], sequence: int) -> Dict[str, object]:
    """Project one event using a fixed allowlist; never copy arbitrary payloads."""

    safe: Dict[str, object] = {"sequence": _safe_non_negative_int(sequence)}
    for field in _RUN_EVENT_FIELDS[1:]:
        if field == "has_error":
            safe[field] = bool(event.get("error") or event.get("last_error"))
        elif field in event:
            value = event.get(field)
            if field in {"approved"}:
                if isinstance(value, bool):
                    safe[field] = value
            elif field in {"attempt", "max_attempts"}:
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    safe[field] = value
            else:
                safe[field] = _safe_string(value)
    return safe


def _safe_string(value: object, limit: int = 256) -> str:
    """Return only bounded primitive text; never stringify nested provider data."""

    if not isinstance(value, str):
        return ""
    return value[:limit]


def _safe_non_negative_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _safe_dispatch_error_type(value: object) -> str:
    """Keep only a bounded exception type token, never provider error text."""

    if not isinstance(value, str):
        return ""
    candidate = value[:64]
    if candidate and all(char.isalnum() or char in {"_", ".", "-"} for char in candidate):
        return candidate
    return ""


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
