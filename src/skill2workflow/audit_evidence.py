"""Bounded, redacted local exports for independently retained audit evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from ._controlled_lark_pilot_evidence_writer import (
    ensure_private_directory_anchored,
    write_private_json_anchored,
)
from .control_plane import LocalControlPlane
from .dashboard import build_audit_event_page_from_control


AUDIT_EVIDENCE_SCHEMA_VERSION = "skill2workflow-audit-evidence-0.1.0"


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


def _safe_integrity(integrity: Dict[str, object]) -> Dict[str, object]:
    """Retain only verification facts that do not disclose audit event values."""

    return {
        "schema_version": str(integrity.get("schema_version", "")),
        "status": str(integrity.get("status", "")),
        "algorithm": str(integrity.get("algorithm", "")),
        "event_count": int(integrity.get("event_count", 0)),
        "head_digest": str(integrity.get("head_digest", "")),
    }
