"""Aggregate, redacted production-readiness checks for the service boundary."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict

from .backup import build_state_backup_readiness_report
from .dashboard import (
    MAX_REMOTE_WORKFLOW_ARTIFACT_REPORT_ISSUES,
    build_workflow_artifact_report_from_control,
)
from .state_layout import CURRENT_STATE_LAYOUT_VERSION, inspect_state_layout


OPERATIONAL_READINESS_SCHEMA_VERSION = (
    "skill2workflow-operational-readiness-0.1.0"
)
_LIFECYCLE_STATUSES = {"starting", "ready", "draining", "stopped"}
_ARTIFACT_STATUSES = {"clean", "attention", "unavailable"}
_AUDIT_STATUSES = {"valid", "invalid", "legacy_unsealed", "unavailable"}
_BACKUP_STATUSES = {"ready", "blocked", "unavailable"}
_BLOCKING_REASONS = {
    "service_not_ready",
    "state_layout_not_current",
    "workflow_artifacts_attention",
    "workflow_artifacts_unavailable",
    "audit_integrity_not_valid",
    "audit_integrity_unavailable",
    "offline_backup_unavailable",
}


def build_operational_readiness_report(service) -> Dict[str, object]:
    """Build one fixed, value-free readiness report without changing state."""

    state_dir = Path(service.config.state_dir)
    state_layout = inspect_state_layout(state_dir)
    readiness_status, _ = service.readiness()
    service_ready = readiness_status == 200
    scheduler_lease_owned = bool(
        service.scheduler.dispatcher.has_lease(now_epoch=time.time())
    )

    artifact = _artifact_check(service)
    audit = _audit_check(service)
    backup = _backup_check(state_dir)

    blocking_reasons = []
    if not service_ready:
        blocking_reasons.append("service_not_ready")
    if state_layout != CURRENT_STATE_LAYOUT_VERSION:
        blocking_reasons.append("state_layout_not_current")
    if artifact["status"] == "attention":
        blocking_reasons.append("workflow_artifacts_attention")
    elif artifact["status"] == "unavailable":
        blocking_reasons.append("workflow_artifacts_unavailable")
    if audit["status"] in {"invalid", "legacy_unsealed"}:
        blocking_reasons.append("audit_integrity_not_valid")
    elif audit["status"] == "unavailable":
        blocking_reasons.append("audit_integrity_unavailable")
    if backup["status"] == "unavailable":
        blocking_reasons.append("offline_backup_unavailable")

    return {
        "schema_version": OPERATIONAL_READINESS_SCHEMA_VERSION,
        "status": "ready" if not blocking_reasons else "attention",
        "service": {
            "status": service.status,
            "ready": service_ready,
            "storage": service.config.storage,
            "state_layout_version": state_layout,
            "scheduler_lease_owned": scheduler_lease_owned,
        },
        "checks": {
            "workflow_artifacts": artifact,
            "audit_integrity": audit,
            "offline_backup": backup,
        },
        "blocking_reasons": blocking_reasons,
        "operator_notes": (
            ["offline_backup_requires_stop"]
            if backup["status"] == "blocked"
            else []
        ),
    }


def _artifact_check(service) -> Dict[str, object]:
    try:
        report = build_workflow_artifact_report_from_control(
            service.control_plane,
            max_issues=MAX_REMOTE_WORKFLOW_ARTIFACT_REPORT_ISSUES,
        )
        summary = report["summary"]
        status = report["status"]
        if status not in {"clean", "attention"}:
            raise ValueError("workflow artifact report status is invalid")
        return {"status": status, "issue_count": int(summary["issue_count"])}
    except (KeyError, TypeError, ValueError, OSError):
        return {"status": "unavailable", "issue_count": None}


def _audit_check(service) -> Dict[str, object]:
    try:
        result = service.control_plane.verify_audit_integrity()
        status = result.get("status")
        if status not in {"valid", "invalid", "legacy_unsealed"}:
            raise ValueError("audit integrity status is invalid")
        return {"status": status}
    except (AttributeError, KeyError, TypeError, ValueError, OSError):
        return {"status": "unavailable"}


def _backup_check(state_dir: Path) -> Dict[str, object]:
    try:
        report = build_state_backup_readiness_report(state_dir)
        status = report["status"]
        if status not in {"ready", "blocked"}:
            raise ValueError("backup readiness status is invalid")
        return {
            "status": status,
            "active_scheduler_lease": bool(report["active_scheduler_lease"]),
        }
    except (KeyError, TypeError, ValueError, OSError):
        return {"status": "unavailable", "active_scheduler_lease": None}
