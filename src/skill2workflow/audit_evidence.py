"""Bounded, redacted local exports for independently retained audit evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from ._controlled_lark_pilot_evidence_writer import (
    ensure_private_directory_anchored,
    read_json_anchored,
    write_private_json_anchored,
)
from .control_plane import LocalControlPlane
from .dashboard import (
    AUDIT_EVENT_LIST_SCHEMA_VERSION,
    MAX_AUDIT_EVENT_LIST_ITEMS,
    build_audit_event_page_from_control,
)
from .storage import AUDIT_INTEGRITY_ALGORITHM, AUDIT_INTEGRITY_SCHEMA_VERSION


AUDIT_EVIDENCE_SCHEMA_VERSION = "skill2workflow-audit-evidence-0.1.0"
AUDIT_EVIDENCE_VERIFICATION_SCHEMA_VERSION = "skill2workflow-audit-evidence-verification-0.1.0"
MAX_AUDIT_EVIDENCE_BYTES = 1024 * 1024

_EVIDENCE_FIELDS = {"schema_version", "integrity", "audit_page"}
_INTEGRITY_FIELDS = {"schema_version", "status", "algorithm", "event_count", "head_digest"}
_PAGE_FIELDS = {"schema_version", "filters", "events", "window"}
_FILTER_FIELDS = {"workflow_id", "workflow_version", "run_id", "event_type"}
_EVENT_FIELDS = {
    "sequence", "type", "run_id", "workflow_id", "workflow_version", "timestamp",
    "node_id", "connector_id", "connector_kind", "connector_status", "attempt",
    "max_attempts", "next_attempt", "backoff_ms", "approved", "has_error",
}
_WINDOW_FIELDS = {"max_items", "total", "returned", "truncated", "next_cursor"}


def export_audit_evidence(
    state_dir: Path,
    output: Path,
    *,
    max_items: int = 100,
    workflow_id: str = "",
    workflow_version: str = "",
    run_id: str = "",
    event_type: str = "",
) -> Dict[str, object]:
    """Create one new private export from a valid SQLite audit-chain window.

    The export is intentionally one bounded, redacted page, not a historical
    archive. It is never written unless the full local SQLite audit chain is
    valid at export time.
    """

    root = Path(state_dir)
    if (root / "audit.log.jsonl").exists() and not (root / "control.sqlite3").exists():
        raise ValueError("audit evidence export requires SQLite storage")
    control = LocalControlPlane(root, storage="sqlite")
    integrity = control.verify_audit_integrity()
    if integrity.get("status") != "valid":
        raise ValueError("audit evidence export requires valid SQLite audit integrity")
    page = build_audit_event_page_from_control(
        control,
        max_items=max_items,
        workflow_id=workflow_id,
        workflow_version=workflow_version,
        run_id=run_id,
        event_type=event_type,
    )
    evidence = {
        "schema_version": AUDIT_EVIDENCE_SCHEMA_VERSION,
        "integrity": _safe_integrity(integrity),
        "audit_page": page,
    }
    validate_audit_evidence(evidence)
    if len(json.dumps(evidence, ensure_ascii=False, indent=2).encode("utf-8")) + 1 > MAX_AUDIT_EVIDENCE_BYTES:
        raise ValueError("audit evidence export exceeds its byte limit")
    output_path = Path(output)
    ensure_private_directory_anchored(output_path.parent)
    write_private_json_anchored(output_path, evidence, require_missing=True)
    window = page["window"]
    return {
        "output": str(output_path),
        "event_count": len(page["events"]),
        "truncated": bool(window["truncated"]),
        "head_digest": str(integrity.get("head_digest", "")),
    }


def verify_audit_evidence_file(path: Path) -> Dict[str, object]:
    """Read one bounded private export and validate only its public contract."""

    evidence = read_json_anchored(Path(path), owner_only=True, max_bytes=MAX_AUDIT_EVIDENCE_BYTES)
    return validate_audit_evidence(evidence)


def validate_audit_evidence(evidence: object) -> Dict[str, object]:
    """Validate the fixed value-free envelope without asserting provenance."""

    if not isinstance(evidence, dict) or set(evidence) != _EVIDENCE_FIELDS:
        raise ValueError("audit evidence is invalid")
    integrity = evidence.get("integrity")
    page = evidence.get("audit_page")
    if not _valid_integrity(integrity) or not _valid_page(page):
        raise ValueError("audit evidence is invalid")
    return {
        "schema_version": AUDIT_EVIDENCE_VERIFICATION_SCHEMA_VERSION,
        "valid": True,
        "event_count": len(page["events"]),
        "truncated": page["window"]["truncated"],
        "head_digest": integrity["head_digest"],
    }


def _safe_integrity(integrity: Dict[str, object]) -> Dict[str, object]:
    """Retain only verification facts that do not disclose audit event values."""

    return {
        "schema_version": str(integrity.get("schema_version", "")),
        "status": str(integrity.get("status", "")),
        "algorithm": str(integrity.get("algorithm", "")),
        "event_count": int(integrity.get("event_count", 0)),
        "head_digest": str(integrity.get("head_digest", "")),
    }


def _valid_integrity(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != _INTEGRITY_FIELDS:
        return False
    count = value.get("event_count")
    digest = value.get("head_digest")
    if (
        value.get("schema_version") != AUDIT_INTEGRITY_SCHEMA_VERSION
        or value.get("status") != "valid"
        or value.get("algorithm") != AUDIT_INTEGRITY_ALGORITHM
        or not _non_negative_integer(count)
        or not isinstance(digest, str)
    ):
        return False
    return (count == 0 and digest == "") or (count > 0 and _hex_digest(digest))


def _valid_page(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != _PAGE_FIELDS:
        return False
    if value.get("schema_version") != AUDIT_EVENT_LIST_SCHEMA_VERSION:
        return False
    filters, events, window = value.get("filters"), value.get("events"), value.get("window")
    if not isinstance(filters, dict) or set(filters) != _FILTER_FIELDS:
        return False
    if any(not isinstance(filters.get(field), str) for field in _FILTER_FIELDS):
        return False
    if (
        len(filters["workflow_id"]) > 128
        or len(filters["workflow_version"]) > 128
        or len(filters["run_id"]) > 128
        or len(filters["event_type"]) > 64
        or not isinstance(events, list)
        or len(events) > MAX_AUDIT_EVENT_LIST_ITEMS
        or not isinstance(window, dict)
        or set(window) != _WINDOW_FIELDS
    ):
        return False
    previous_sequence = 0
    for event in events:
        if not _valid_event(event, filters) or event["sequence"] <= previous_sequence:
            return False
        previous_sequence = event["sequence"]
    return _valid_window(window, len(events))


def _valid_event(event: object, filters: Dict[str, object]) -> bool:
    if not isinstance(event, dict) or set(event) != _EVENT_FIELDS:
        return False
    if (
        not _non_negative_integer(event.get("sequence"))
        or event["sequence"] < 1
        or not isinstance(event.get("type"), str)
        or not event["type"]
        or len(event["type"]) > 64
        or not all(isinstance(event.get(field), str) for field in (
            "run_id", "workflow_id", "workflow_version", "timestamp", "node_id",
            "connector_id", "connector_kind", "connector_status",
        ))
        or any(len(event[field]) > 128 for field in (
            "run_id", "workflow_id", "workflow_version", "node_id", "connector_id",
            "connector_kind", "connector_status",
        ))
        or len(event["timestamp"]) > 256
        or not all(_non_negative_integer(event.get(field)) for field in (
            "attempt", "max_attempts", "next_attempt", "backoff_ms",
        ))
        or not isinstance(event.get("approved"), bool)
        or not isinstance(event.get("has_error"), bool)
    ):
        return False
    filter_event_fields = {
        "workflow_id": "workflow_id",
        "workflow_version": "workflow_version",
        "run_id": "run_id",
        "event_type": "type",
    }
    return all(
        not filters[filter_field] or event[event_field] == filters[filter_field]
        for filter_field, event_field in filter_event_fields.items()
    )


def _valid_window(window: Dict[str, object], returned: int) -> bool:
    max_items, total, declared = window.get("max_items"), window.get("total"), window.get("returned")
    cursor = window.get("next_cursor")
    if (
        not _non_negative_integer(max_items)
        or max_items < 1
        or max_items > MAX_AUDIT_EVENT_LIST_ITEMS
        or not _non_negative_integer(total)
        or declared != returned
        or returned > total
        or returned > max_items
        or not isinstance(window.get("truncated"), bool)
        or not isinstance(cursor, str)
        or len(cursor) > 128
        or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for character in cursor)
    ):
        return False
    return window["truncated"] == bool(cursor)


def _non_negative_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _hex_digest(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)
