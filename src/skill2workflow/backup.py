"""Verified offline backup and restore for the self-hosted SQLite state boundary."""

from __future__ import annotations

import base64
import binascii
import hashlib
import heapq
import json
import shutil
import sqlite3
import stat
import tempfile
import time
from contextlib import ExitStack, closing
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Tuple

from .state_layout import (
    CURRENT_STATE_LAYOUT_VERSION,
    LEGACY_STATE_LAYOUT_VERSION,
    STATE_LAYOUT_MARKER,
    inspect_state_layout,
    validate_current_state_marker,
)
from .storage import verify_audit_integrity


BACKUP_SCHEMA_VERSION = "skill2workflow-state-backup-0.1.0"
BACKUP_READINESS_SCHEMA_VERSION = "skill2workflow-backup-readiness-0.1.0"
BACKUP_LIST_SCHEMA_VERSION = "skill2workflow-state-backup-list-0.1.0"
BACKUP_RETENTION_POLICY_SCHEMA_VERSION = "skill2workflow-backup-retention-policy-0.1.0"
BACKUP_RETENTION_PLAN_SCHEMA_VERSION = "skill2workflow-backup-retention-plan-0.1.0"
REMOTE_BACKUP_RETENTION_PLAN_SCHEMA_VERSION = (
    "skill2workflow-remote-backup-retention-plan-0.1.0"
)
REMOTE_BACKUP_INVENTORY_SCHEMA_VERSION = (
    "skill2workflow-remote-backup-inventory-0.1.0"
)
REMOTE_BACKUP_INVENTORY_PAGE_SCHEMA_VERSION = (
    "skill2workflow-remote-backup-inventory-page-0.1.0"
)
MAX_BACKUP_LIST_ITEMS = 1000
MAX_REMOTE_BACKUP_INVENTORY_ITEMS = 100
MAX_REMOTE_BACKUP_INVENTORY_PAGE_ITEMS = 100
STATE_LAYOUT_VERSION = CURRENT_STATE_LAYOUT_VERSION
_DATABASES = ("control.sqlite3", "runs.sqlite3", "scheduler.sqlite3")
_REQUIRED_TABLES = {
    "control.sqlite3": {"workflow_versions", "audit_events"},
    "runs.sqlite3": {"runs", "run_events"},
    "scheduler.sqlite3": {
        "recurring_schedules",
        "schedule_dispatches",
        "scheduler_leases",
    },
}
_REQUIRED_COLUMNS = {
    "control.sqlite3": {
        "workflow_versions": {
            "record_key", "workflow_id", "name", "version", "status", "checksum",
            "artifact", "published_at", "deprecated_at", "record_json",
        },
        "audit_events": {
            "sequence", "event_type", "workflow_id", "workflow_version", "run_id",
            "timestamp", "payload_json",
        },
    },
    "runs.sqlite3": {
        "runs": {
            "run_id", "workflow_id", "workflow_version", "status", "current_node",
            "state_json", "updated_at",
        },
        "run_events": {
            "run_id", "sequence", "event_type", "node_id", "timestamp", "payload_json",
        },
    },
    "scheduler.sqlite3": {
        "recurring_schedules": {"schedule_id", "definition_json", "updated_at"},
        "schedule_dispatches": {
            "dispatch_id", "schedule_id", "scheduled_for", "status", "owner_id",
            "claim_expires_at", "record_json",
        },
        "scheduler_leases": {"lease_name", "owner_id", "expires_at"},
    },
}
_OPTIONAL_COLUMNS = {
    "control.sqlite3": {
        "trigger_idempotency": {
            "workflow_id",
            "workflow_version",
            "idempotency_key",
            "request_fingerprint",
            "status",
            "response_json",
            "created_at",
            "updated_at",
        },
    },
    "runs.sqlite3": {
        "run_cancellations": {
            "run_id",
            "requested_at",
            "status",
            "applied_at",
        },
        "run_executions": {
            "run_id",
            "owner_id",
            "execution_id",
            "status",
            "claimed_at",
            "updated_at",
        },
        "run_summaries": {
            "run_id",
            "workflow_id",
            "workflow_version",
            "status",
            "current_node",
            "event_count",
            "node_result_count",
            "updated_at",
            "detail_projection_json",
        },
    },
    "scheduler.sqlite3": {
        "recurring_schedule_summaries": {
            "schedule_id",
            "workflow_id",
            "workflow_version",
            "status",
            "enabled",
            "starts_at",
            "next_run_at",
            "interval_seconds",
            "missed_run_policy",
            "last_activity_at",
            "last_scheduled_for",
            "last_run_id",
            "last_trigger_id",
            "updated_at",
        },
    },
}
_MANIFEST_KEYS = {
    "schema_version",
    "state_layout_version",
    "created_at",
    "storage",
    "database_count",
    "workflow_artifact_count",
    "scheduler_leases_cleared",
    "scheduler_database_synthesized",
    "files",
}
_FILE_KEYS = {"path", "kind", "size_bytes", "sha256"}


def inspect_state_backup_readiness(
    state_dir: Path,
    now_epoch: float = None,
    require_stopped: bool = True,
) -> Dict[str, object]:
    """Read and validate the complete offline state boundary without changing it."""

    source = _existing_directory(state_dir, "state directory")
    layout = inspect_state_layout(source)
    if layout not in {CURRENT_STATE_LAYOUT_VERSION, LEGACY_STATE_LAYOUT_VERSION}:
        raise ValueError("state backup requires initialized SQLite state")
    scheduler_synthesized = _require_database_files(
        source,
        allow_missing_scheduler=layout == LEGACY_STATE_LAYOUT_VERSION,
    )
    for database in _DATABASES:
        if database == "scheduler.sqlite3" and scheduler_synthesized:
            continue
        _validate_database(source / database, database)
    current_epoch = time.time() if now_epoch is None else float(now_epoch)
    active = None
    if not scheduler_synthesized:
        with closing(
            sqlite3.connect(f"file:{source / 'scheduler.sqlite3'}?mode=ro", uri=True)
        ) as scheduler:
            active = scheduler.execute(
                "select count(*) from scheduler_leases where expires_at > ?",
                (current_epoch,),
            ).fetchone()
    active_lease = bool(active and int(active[0]) > 0)
    if require_stopped and active_lease:
        raise ValueError(
            "state backup requires the service to be stopped; active scheduler lease found"
        )
    with closing(
        sqlite3.connect(f"file:{source / 'control.sqlite3'}?mode=ro", uri=True)
    ) as control:
        records = _iter_workflow_artifact_records(control)
        artifact_count = 0
        for relative_path, checksum in records:
            artifact_count += 1
            _validate_workflow_artifact(source, relative_path, checksum)
    return {
        "schema_version": BACKUP_SCHEMA_VERSION,
        "status": "ready",
        "state_layout_version": layout,
        "database_count": len(_DATABASES),
        "workflow_artifact_count": artifact_count,
        "active_scheduler_lease": active_lease,
        "scheduler_database_synthesized": scheduler_synthesized,
    }


def build_state_backup_readiness_report(
    state_dir: Path,
    now_epoch: float = None,
) -> Dict[str, object]:
    """Return the fixed, value-free preflight projection for remote operators."""

    readiness = inspect_state_backup_readiness(
        state_dir,
        now_epoch=now_epoch,
        require_stopped=False,
    )
    active_lease = bool(readiness["active_scheduler_lease"])
    return {
        "schema_version": BACKUP_READINESS_SCHEMA_VERSION,
        "status": "blocked" if active_lease else "ready",
        "storage": "sqlite",
        "state_layout_version": readiness["state_layout_version"],
        "database_count": readiness["database_count"],
        "workflow_artifact_count": readiness["workflow_artifact_count"],
        "active_scheduler_lease": active_lease,
        "scheduler_database_synthesized": readiness["scheduler_database_synthesized"],
        "backup_allowed": not active_lease,
        "blocking_reasons": ["active_scheduler_lease"] if active_lease else [],
    }


def create_state_backup(
    state_dir: Path,
    output_dir: Path,
    now_epoch: float = None,
) -> Dict[str, object]:
    """Create one verified owner-only snapshot while all SQLite writers are locked."""

    source = _existing_directory(state_dir, "state directory")
    source_layout = inspect_state_layout(source)
    if source_layout not in {
        CURRENT_STATE_LAYOUT_VERSION,
        LEGACY_STATE_LAYOUT_VERSION,
    }:
        raise ValueError("state backup requires initialized SQLite state")
    output = _new_path(output_dir, "backup output directory")
    if _is_within(output, source):
        raise ValueError("backup output directory must be outside the state directory")
    scheduler_synthesized = _require_database_files(
        source,
        allow_missing_scheduler=source_layout == LEGACY_STATE_LAYOUT_VERSION,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=str(output.parent))
    )
    staging.chmod(0o700)
    completed = False
    try:
        with ExitStack() as stack:
            guards = _lock_databases(
                source,
                stack,
                allow_missing_scheduler=scheduler_synthesized,
            )
            scheduler = guards.get("scheduler.sqlite3")
            current_epoch = time.time() if now_epoch is None else float(now_epoch)
            active = (
                scheduler.execute(
                    "select count(*) from scheduler_leases where expires_at > ?",
                    (current_epoch,),
                ).fetchone()
                if scheduler is not None
                else None
            )
            if active and int(active[0]) > 0:
                raise ValueError(
                    "state backup requires the service to be stopped; active scheduler lease found"
                )
            artifact_records = _iter_workflow_artifact_records(guards["control.sqlite3"])
            for database in _DATABASES:
                destination = staging / database
                if database == "scheduler.sqlite3" and scheduler_synthesized:
                    _initialize_empty_scheduler_database(destination)
                else:
                    _backup_database(source / database, destination)
                if database == "scheduler.sqlite3":
                    with closing(sqlite3.connect(destination)) as connection:
                        connection.execute("delete from scheduler_leases")
                        connection.commit()
                _validate_database(destination, database)
                destination.chmod(0o600)
            for relative_path, checksum in artifact_records:
                _copy_workflow_artifact(source, staging, relative_path, checksum)
            if source_layout == CURRENT_STATE_LAYOUT_VERSION:
                _copy_state_layout_marker(source, staging)

        entries = _manifest_entries(staging)
        workflow_count = sum(entry["kind"] == "workflow_artifact" for entry in entries)
        manifest = {
            "schema_version": BACKUP_SCHEMA_VERSION,
            "state_layout_version": source_layout,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "storage": "sqlite",
            "database_count": len(_DATABASES),
            "workflow_artifact_count": workflow_count,
            "scheduler_leases_cleared": True,
            "scheduler_database_synthesized": scheduler_synthesized,
            "files": entries,
        }
        manifest_path = staging / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        manifest_path.chmod(0o600)
        _verify_backup_directory(staging)
        staging.rename(output)
        completed = True
    finally:
        if not completed and staging.exists():
            shutil.rmtree(staging)
    return _summary("created", output)


def verify_state_backup(backup_dir: Path) -> Dict[str, object]:
    """Verify the manifest, every checksum, SQLite integrity, and artifact references."""

    backup = _existing_directory(backup_dir, "backup directory")
    _verify_backup_directory(backup)
    return _summary("valid", backup)


def list_state_backups(
    parent_dir: Path,
    limit: int = 100,
    *,
    scan_limit: Optional[int] = None,
) -> Dict[str, object]:
    """Return a bounded, read-only inventory of direct child backup sets.

    ``scan_limit`` is an internal early-stop guard for callers that only need
    to know whether the inventory exceeds a fixed budget.  When present, the
    returned ``total`` is a lower bound once the guard trips; callers must use
    ``window.truncated`` rather than treating it as a complete count.
    """

    _validate_backup_list_limit(limit)
    if scan_limit is not None and (
        isinstance(scan_limit, bool)
        or not isinstance(scan_limit, int)
        or scan_limit < 1
    ):
        raise ValueError("backup scan limit must be a positive integer")
    parent = _existing_directory(parent_dir, "backup parent directory")
    _require_owner_only_directory(parent, "backup parent directory")
    selected = []
    total = 0
    for candidate in parent.iterdir():
        if candidate.is_symlink() or not candidate.is_dir():
            continue
        total += 1
        if scan_limit is not None and total > scan_limit:
            break
        metadata, sort_key = _backup_inventory_metadata(candidate)
        item = (sort_key, candidate.name, metadata)
        if len(selected) < limit:
            heapq.heappush(selected, item)
        elif sort_key > selected[0][0]:
            heapq.heapreplace(selected, item)

    backups = []
    for _, name, metadata in sorted(selected, key=lambda item: item[0]):
        candidate = parent / name
        item = {"name": name, **metadata}
        try:
            manifest = _verify_backup_directory(candidate)
            item.update(_backup_inventory_summary(manifest))
            item["status"] = "valid"
        except (OSError, sqlite3.Error, ValueError):
            item["status"] = "invalid"
        backups.append(item)
    return {
        "schema_version": BACKUP_LIST_SCHEMA_VERSION,
        "status": "ok",
        "total": total,
        "backups": backups,
        "window": {
            "max_items": limit,
            "returned": len(backups),
            "truncated": total > len(backups),
        },
    }


def build_remote_backup_inventory(
    parent_dir: Path,
    max_items: int = MAX_REMOTE_BACKUP_INVENTORY_ITEMS,
) -> Dict[str, object]:
    """Return a bounded, redacted backup inventory for authenticated operators.

    The local inventory intentionally includes the operator-chosen directory
    name so a shell user can verify or restore a specific set.  A service
    response must not export that name (it can contain business identifiers),
    so this projection retains only integrity, age, layout, and size metadata.
    """

    if (
        isinstance(max_items, bool)
        or not isinstance(max_items, int)
        or not 1 <= max_items <= MAX_REMOTE_BACKUP_INVENTORY_ITEMS
    ):
        raise ValueError(
            "remote backup inventory max_items must be an integer from 1 through "
            f"{MAX_REMOTE_BACKUP_INVENTORY_ITEMS}"
        )
    inventory = list_state_backups(parent_dir, limit=max_items)
    backups = []
    for item in reversed(inventory["backups"]):
        backups.append(
            {
                "status": str(item["status"]),
                "created_at": str(item["created_at"]),
                "state_layout_version": str(item["state_layout_version"]),
                "workflow_artifact_count": int(item["workflow_artifact_count"]),
                "file_count": int(item["file_count"]),
                "total_bytes": int(item["total_bytes"]),
            }
        )
    return {
        "schema_version": REMOTE_BACKUP_INVENTORY_SCHEMA_VERSION,
        "status": "ok",
        "total": int(inventory["total"]),
        "backups": backups,
        "window": {
            "max_items": max_items,
            "returned": len(backups),
            "truncated": bool(inventory["window"]["truncated"]),
        },
    }


def build_remote_backup_inventory_page(
    parent_dir: Path,
    max_items: int = MAX_REMOTE_BACKUP_INVENTORY_PAGE_ITEMS,
    cursor: str = "",
) -> Dict[str, object]:
    """Return one newest-first, redacted page of configured backup sets.

    The cursor contains only a normalized ordering timestamp/fallback and a
    digest of the private directory name.  It never carries a backup name or
    filesystem path across the service boundary.
    """

    if (
        isinstance(max_items, bool)
        or not isinstance(max_items, int)
        or not 1 <= max_items <= MAX_REMOTE_BACKUP_INVENTORY_PAGE_ITEMS
    ):
        raise ValueError(
            "remote backup inventory page max_items must be an integer from 1 through "
            f"{MAX_REMOTE_BACKUP_INVENTORY_PAGE_ITEMS}"
        )
    cursor_key = _decode_remote_backup_inventory_cursor(cursor)
    parent = _existing_directory(parent_dir, "backup parent directory")
    _require_owner_only_directory(parent, "backup parent directory")

    selected = []
    total = 0
    for candidate in parent.iterdir():
        if candidate.is_symlink() or not candidate.is_dir():
            continue
        total += 1
        metadata, sort_key = _backup_inventory_metadata(candidate)
        order_key = _remote_backup_inventory_order_key(candidate, sort_key)
        if cursor_key is not None and order_key >= cursor_key:
            continue
        item = (order_key, candidate.name, metadata, candidate)
        if len(selected) < max_items + 1:
            heapq.heappush(selected, item)
        elif (order_key, candidate.name) > (selected[0][0], selected[0][1]):
            heapq.heapreplace(selected, item)

    has_more = len(selected) > max_items
    selected = sorted(selected, key=lambda item: (item[0], item[1]), reverse=True)
    selected = selected[:max_items]
    backups = [
        _redacted_remote_backup_item(candidate, metadata)
        for _, _, metadata, candidate in selected
    ]
    next_cursor = ""
    if has_more and selected:
        next_cursor = _encode_remote_backup_inventory_cursor(selected[-1][0])
    return {
        "schema_version": REMOTE_BACKUP_INVENTORY_PAGE_SCHEMA_VERSION,
        "status": "ok",
        "total": total,
        "backups": backups,
        "window": {
            "max_items": max_items,
            "total": total,
            "returned": len(backups),
            "has_more": has_more,
            "next_cursor": next_cursor,
        },
    }


def _redacted_remote_backup_item(
    candidate: Path, metadata: Dict[str, object]
) -> Dict[str, object]:
    item = dict(metadata)
    try:
        manifest = _verify_backup_directory(candidate)
        item.update(_backup_inventory_summary(manifest))
        item["status"] = "valid"
    except (OSError, sqlite3.Error, ValueError):
        item["status"] = "invalid"
    return {
        "status": str(item["status"]),
        "created_at": str(item["created_at"]),
        "state_layout_version": str(item["state_layout_version"]),
        "workflow_artifact_count": int(item["workflow_artifact_count"]),
        "file_count": int(item["file_count"]),
        "total_bytes": int(item["total_bytes"]),
    }


def _remote_backup_inventory_order_key(
    candidate: Path, sort_key: Tuple[object, object, str]
) -> Tuple[int, str, str]:
    rank = int(sort_key[0])
    value = sort_key[1]
    if rank == 1 and isinstance(value, datetime):
        sort_value = value.astimezone(timezone.utc).isoformat()
    else:
        sort_value = str(value)
    name_digest = hashlib.sha256(candidate.name.encode("utf-8")).hexdigest()
    return rank, sort_value, name_digest


def _encode_remote_backup_inventory_cursor(
    value: Tuple[int, str, str]
) -> str:
    rank, sort_value, name_digest = value
    raw = json.dumps(
        {"rank": rank, "sort_value": sort_value, "name_digest": name_digest},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_remote_backup_inventory_cursor(
    cursor: str,
) -> Optional[Tuple[int, str, str]]:
    if not isinstance(cursor, str):
        raise ValueError("remote backup inventory cursor is invalid")
    normalized = cursor
    if not normalized:
        return None
    if len(normalized) > 512 or any(
        character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        for character in normalized
    ):
        raise ValueError("remote backup inventory cursor is invalid")
    try:
        raw = base64.urlsafe_b64decode(normalized + "=" * (-len(normalized) % 4))
        value = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("remote backup inventory cursor is invalid") from error
    if not isinstance(value, dict) or set(value) != {"rank", "sort_value", "name_digest"}:
        raise ValueError("remote backup inventory cursor is invalid")
    rank = value.get("rank")
    sort_value = value.get("sort_value")
    name_digest = value.get("name_digest")
    if (
        isinstance(rank, bool)
        or not isinstance(rank, int)
        or rank not in {0, 1}
        or not isinstance(sort_value, str)
        or not sort_value
        or len(sort_value) > 128
        or not isinstance(name_digest, str)
        or len(name_digest) != 64
        or any(character not in "0123456789abcdef" for character in name_digest)
    ):
        raise ValueError("remote backup inventory cursor is invalid")
    return rank, sort_value, name_digest


def normalize_backup_retention_policy(policy: object) -> Dict[str, object]:
    """Validate and canonicalize the deliberately narrow backup policy."""

    if not isinstance(policy, dict) or set(policy) != {"schema_version", "retention"}:
        raise ValueError(
            "backup retention policy must contain only schema_version and retention"
        )
    if policy.get("schema_version") != BACKUP_RETENTION_POLICY_SCHEMA_VERSION:
        raise ValueError(
            "backup retention policy schema_version must be "
            f"{BACKUP_RETENTION_POLICY_SCHEMA_VERSION}"
        )
    retention = policy.get("retention")
    if not isinstance(retention, dict) or set(retention) != {
        "expire_before",
        "minimum_keep",
    }:
        raise ValueError("backup retention policy retention section has an invalid shape")
    minimum_keep = retention.get("minimum_keep")
    if (
        isinstance(minimum_keep, bool)
        or not isinstance(minimum_keep, int)
        or not 1 <= minimum_keep <= MAX_BACKUP_LIST_ITEMS
    ):
        raise ValueError(
            "backup retention minimum_keep must be an integer from 1 through "
            f"{MAX_BACKUP_LIST_ITEMS}"
        )
    return {
        "schema_version": BACKUP_RETENTION_POLICY_SCHEMA_VERSION,
        "retention": {
            "expire_before": _aware_timestamp(
                retention.get("expire_before"), "backup retention expire_before"
            ),
            "minimum_keep": minimum_keep,
        },
    }


def build_backup_retention_plan(
    parent_dir: Path,
    policy: object,
    limit: int = MAX_BACKUP_LIST_ITEMS,
) -> Dict[str, object]:
    """Return a bounded, read-only plan for expiring old valid backups."""

    _validate_backup_list_limit(limit)
    normalized = normalize_backup_retention_policy(policy)
    # Retention planning fails closed once the fixed inventory budget is
    # exceeded.  Stop enumerating after the first over-budget directory so a
    # remote request cannot spend unbounded time walking a hostile or simply
    # overgrown backup parent before returning the already-determined block.
    inventory = list_state_backups(parent_dir, limit=limit, scan_limit=limit)
    base = {
        "schema_version": BACKUP_RETENTION_PLAN_SCHEMA_VERSION,
        "storage": "filesystem",
        "policy_sha256": _policy_checksum(normalized),
        "expire_before": normalized["retention"]["expire_before"],
        "minimum_keep": normalized["retention"]["minimum_keep"],
        "inventory": inventory["window"],
        "candidates": [],
        "preserved": [],
    }
    if inventory["window"]["truncated"]:
        return {
            **base,
            "status": "blocked",
            "blocking_reasons": ["inventory_truncated"],
            "summary": {
                "valid_backups": None,
                "invalid_backups": None,
                "eligible_backups": None,
                "eligible_bytes": None,
                "preserved_backups": None,
                "preserved_bytes": None,
            },
        }

    expire_before = str(normalized["retention"]["expire_before"])
    minimum_keep = int(normalized["retention"]["minimum_keep"])
    valid = [item for item in inventory["backups"] if item["status"] == "valid"]
    valid_newest_first = sorted(
        valid,
        key=lambda item: (
            _aware_timestamp(item["created_at"], "backup created_at"),
            str(item["name"]),
        ),
        reverse=True,
    )
    protected_names = {str(item["name"]) for item in valid_newest_first[:minimum_keep]}
    candidates = []
    preserved = []
    for item in sorted(
        inventory["backups"],
        key=lambda value: (str(value["created_at"]), str(value["name"])),
    ):
        name = str(item["name"])
        entry = {
            "name": name,
            "status": str(item["status"]),
            "created_at": str(item["created_at"]),
            "total_bytes": int(item["total_bytes"]),
        }
        if item["status"] != "valid":
            entry["reason"] = "invalid_backup"
            preserved.append(entry)
            continue
        created_at = _aware_timestamp(item["created_at"], "backup created_at")
        if name in protected_names:
            entry["reason"] = "minimum_keep"
            preserved.append(entry)
        elif created_at < expire_before:
            entry["reason"] = "expired_beyond_minimum_keep"
            candidates.append(entry)
        else:
            entry["reason"] = "newer_than_expire_before"
            preserved.append(entry)

    return {
        **base,
        "status": "ready",
        "blocking_reasons": [],
        "summary": {
            "valid_backups": len(valid),
            "invalid_backups": len(inventory["backups"]) - len(valid),
            "eligible_backups": len(candidates),
            "eligible_bytes": sum(item["total_bytes"] for item in candidates),
            "preserved_backups": len(preserved),
            "preserved_bytes": sum(item["total_bytes"] for item in preserved),
        },
        "candidates": candidates,
        "preserved": preserved,
    }


def build_remote_backup_retention_plan(
    parent_dir: Path,
    policy: object,
    limit: int = MAX_BACKUP_LIST_ITEMS,
) -> Dict[str, object]:
    """Return a redacted aggregate backup-expiration plan for remote operators.

    The local plan intentionally includes operator-chosen backup names so a
    shell operator can act on a specific set.  The service projection keeps
    only policy, completeness, counts, and byte totals; names, paths, and
    per-backup reasons never cross the authenticated service boundary.
    """

    plan = build_backup_retention_plan(parent_dir, policy, limit=limit)
    inventory = dict(plan["inventory"])
    inventory.pop("backups", None)
    summary = dict(plan["summary"])
    return {
        "schema_version": REMOTE_BACKUP_RETENTION_PLAN_SCHEMA_VERSION,
        "status": str(plan["status"]),
        "storage": "filesystem",
        "policy_sha256": str(plan["policy_sha256"]),
        "expire_before": str(plan["expire_before"]),
        "minimum_keep": int(plan["minimum_keep"]),
        "inventory": {
            "max_items": int(inventory["max_items"]),
            "returned": int(inventory["returned"]),
            "truncated": bool(inventory["truncated"]),
        },
        "summary": {
            "valid_backups": summary["valid_backups"],
            "invalid_backups": summary["invalid_backups"],
            "eligible_backups": summary["eligible_backups"],
            "eligible_bytes": summary["eligible_bytes"],
            "preserved_backups": summary["preserved_backups"],
            "preserved_bytes": summary["preserved_bytes"],
        },
        "blocking_reasons": [
            str(reason) for reason in plan.get("blocking_reasons", [])
        ],
    }


def restore_state_backup(backup_dir: Path, state_dir: Path) -> Dict[str, object]:
    """Restore a verified backup atomically into a destination that does not exist."""

    backup = _existing_directory(backup_dir, "backup directory")
    manifest = _verify_backup_directory(backup)
    destination = _new_path(state_dir, "restore state directory")
    if _is_within(destination, backup):
        raise ValueError("restore state directory must be outside the backup directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.restore-", dir=str(destination.parent)
        )
    )
    staging.chmod(0o700)
    completed = False
    try:
        for entry in manifest["files"]:
            relative = PurePosixPath(str(entry["path"]))
            source = backup.joinpath(*relative.parts)
            target = staging.joinpath(*relative.parts)
            _make_owner_only_parents(staging, relative)
            shutil.copyfile(source, target)
            target.chmod(0o600)
            if (
                target.stat().st_size != entry["size_bytes"]
                or _file_checksum(target) != entry["sha256"]
            ):
                raise ValueError("backup file changed during restore")
        _validate_runtime_state(
            staging,
            expected_layout=str(manifest["state_layout_version"]),
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging.rename(destination)
        completed = True
    finally:
        if not completed and staging.exists():
            shutil.rmtree(staging)
    return _state_summary("restored", manifest)


def _lock_databases(
    state_dir: Path,
    stack: ExitStack,
    allow_missing_scheduler: bool = False,
):
    guards = {}
    for name in ("scheduler.sqlite3", "control.sqlite3", "runs.sqlite3"):
        if (
            name == "scheduler.sqlite3"
            and allow_missing_scheduler
            and not (state_dir / name).exists()
        ):
            continue
        connection = stack.enter_context(closing(sqlite3.connect(state_dir / name, timeout=5)))
        connection.execute("begin immediate")
        _require_tables(connection, name)
        guards[name] = connection
    return guards


def _backup_database(source_path: Path, destination_path: Path) -> None:
    with closing(sqlite3.connect(source_path, timeout=5)) as source:
        with closing(sqlite3.connect(destination_path)) as destination:
            source.backup(destination)


def _initialize_empty_scheduler_database(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            """
            create table recurring_schedules (
                schedule_id text primary key,
                definition_json text not null,
                updated_at text not null
            )
            """
        )
        connection.execute(
            """
            create table schedule_dispatches (
                dispatch_id text primary key,
                schedule_id text not null,
                scheduled_for text not null,
                status text not null,
                owner_id text not null,
                claim_expires_at real not null,
                record_json text not null,
                unique(schedule_id, scheduled_for)
            )
            """
        )
        connection.execute(
            """
            create table scheduler_leases (
                lease_name text primary key,
                owner_id text not null,
                expires_at real not null
            )
            """
        )
        connection.execute(
            """
            create table recurring_schedule_summaries (
                schedule_id text primary key,
                workflow_id text not null,
                workflow_version text not null,
                status text not null,
                enabled integer not null,
                starts_at text not null,
                next_run_at text not null,
                interval_seconds integer not null,
                missed_run_policy text not null,
                last_activity_at text not null,
                last_scheduled_for text not null,
                last_run_id text not null,
                last_trigger_id text not null,
                updated_at text not null,
                foreign key (schedule_id) references recurring_schedules(schedule_id) on delete cascade
            )
            """
        )
        connection.commit()


def _iter_workflow_artifact_records(connection):
    """Stream validated artifact references in stable path order."""

    rows = connection.execute(
        "select artifact, checksum from workflow_versions order by artifact"
    )
    previous_path = None
    for raw_path, raw_checksum in rows:
        path = str(raw_path)
        checksum = str(raw_checksum)
        _safe_relative_path(path, expected_prefix="workflows", expected_suffix=".json")
        if path == previous_path:
            continue
        if len(checksum) != 64 or any(char not in "0123456789abcdef" for char in checksum):
            raise ValueError("workflow record has an invalid checksum")
        previous_path = path
        yield path, checksum


def _workflow_artifact_records(connection) -> List[Tuple[str, str]]:
    """Return the compatibility list form for callers that need all records."""

    return list(_iter_workflow_artifact_records(connection))


def _copy_workflow_artifact(
    source_root: Path,
    target_root: Path,
    relative_path: str,
    expected_checksum: str,
) -> None:
    source, relative = _validate_workflow_artifact(
        source_root, relative_path, expected_checksum
    )
    target = target_root.joinpath(*relative.parts)
    _make_owner_only_parents(target_root, relative)
    shutil.copyfile(source, target)
    target.chmod(0o600)


def _validate_workflow_artifact(
    source_root: Path,
    relative_path: str,
    expected_checksum: str,
):
    relative = _safe_relative_path(
        relative_path, expected_prefix="workflows", expected_suffix=".json"
    )
    source = source_root.joinpath(*relative.parts)
    _require_regular_no_symlink(source, "workflow artifact")
    _require_no_symlink_components(source_root, relative)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("workflow artifact is not valid UTF-8 JSON") from error
    if _json_checksum(payload) != expected_checksum:
        raise ValueError("workflow artifact checksum does not match control state")
    return source, relative


def _copy_state_layout_marker(source_root: Path, target_root: Path) -> None:
    validate_current_state_marker(source_root)
    source = source_root / STATE_LAYOUT_MARKER
    target = target_root / STATE_LAYOUT_MARKER
    shutil.copyfile(source, target)
    target.chmod(0o600)


def _manifest_entries(root: Path) -> List[Dict[str, object]]:
    paths = [root / name for name in _DATABASES]
    if (root / STATE_LAYOUT_MARKER).exists():
        paths.append(root / STATE_LAYOUT_MARKER)
    paths.extend(sorted((root / "workflows").rglob("*.json")) if (root / "workflows").exists() else [])
    entries = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        entries.append(
            {
                "path": relative,
                "kind": (
                    "sqlite"
                    if relative in _DATABASES
                    else "state_layout"
                    if relative == STATE_LAYOUT_MARKER
                    else "workflow_artifact"
                ),
                "size_bytes": path.stat().st_size,
                "sha256": _file_checksum(path),
            }
        )
    return sorted(entries, key=lambda entry: str(entry["path"]))


def _verify_backup_directory(backup: Path) -> Dict[str, object]:
    _require_owner_only_directory(backup, "backup directory")
    manifest_path = backup / "manifest.json"
    _require_regular_no_symlink(manifest_path, "backup manifest")
    _require_owner_only_file(manifest_path, "backup manifest")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("backup manifest is not valid UTF-8 JSON") from error
    _validate_manifest_shape(manifest)
    declared_paths = set()
    database_paths = set()
    workflow_paths = set()
    state_layout_paths = set()
    for entry in manifest["files"]:
        relative = _validate_file_entry(entry)
        path_text = relative.as_posix()
        if path_text in declared_paths:
            raise ValueError("backup manifest contains duplicate paths")
        declared_paths.add(path_text)
        if entry["kind"] == "sqlite":
            database_paths.add(path_text)
        elif entry["kind"] == "workflow_artifact":
            workflow_paths.add(path_text)
        else:
            state_layout_paths.add(path_text)
        path = backup.joinpath(*relative.parts)
        _require_regular_no_symlink(path, "backup file")
        _require_no_symlink_components(backup, relative)
        _require_owner_only_parent_directories(backup, relative)
        _require_owner_only_file(path, "backup file")
        if path.stat().st_size != entry["size_bytes"]:
            raise ValueError(f"backup file size mismatch: {path_text}")
        if _file_checksum(path) != entry["sha256"]:
            raise ValueError(f"backup file checksum mismatch: {path_text}")
    if database_paths != set(_DATABASES):
        raise ValueError("backup manifest must contain exactly the three SQLite databases")
    if len(workflow_paths) != manifest["workflow_artifact_count"]:
        raise ValueError("backup workflow artifact count does not match manifest")
    expected_layout_paths = (
        {STATE_LAYOUT_MARKER}
        if manifest["state_layout_version"] == CURRENT_STATE_LAYOUT_VERSION
        else set()
    )
    if state_layout_paths != expected_layout_paths:
        raise ValueError("backup state layout marker does not match manifest")
    actual_paths = {
        path.relative_to(backup).as_posix()
        for path in backup.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if actual_paths != declared_paths:
        raise ValueError("backup directory contains undeclared or missing files")
    _validate_runtime_state(
        backup,
        expected_artifacts=workflow_paths,
        expected_layout=str(manifest["state_layout_version"]),
    )
    if manifest["scheduler_database_synthesized"]:
        _require_empty_synthesized_scheduler(backup / "scheduler.sqlite3")
    return manifest


def _validate_manifest_shape(manifest: object) -> None:
    if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_KEYS:
        raise ValueError("backup manifest has an invalid shape")
    if manifest.get("schema_version") != BACKUP_SCHEMA_VERSION:
        raise ValueError(f"backup schema_version must be {BACKUP_SCHEMA_VERSION}")
    if manifest.get("state_layout_version") not in {
        CURRENT_STATE_LAYOUT_VERSION,
        LEGACY_STATE_LAYOUT_VERSION,
    }:
        raise ValueError("backup state_layout_version is unsupported")
    if manifest.get("storage") != "sqlite":
        raise ValueError("backup storage must be sqlite")
    if type(manifest.get("database_count")) is not int or manifest["database_count"] != 3:
        raise ValueError("backup database_count must be 3")
    if type(manifest.get("workflow_artifact_count")) is not int or manifest["workflow_artifact_count"] < 0:
        raise ValueError("backup workflow_artifact_count must be a non-negative integer")
    if manifest.get("scheduler_leases_cleared") is not True:
        raise ValueError("backup must declare cleared scheduler leases")
    if type(manifest.get("scheduler_database_synthesized")) is not bool:
        raise ValueError("backup scheduler_database_synthesized must be a boolean")
    if (
        manifest.get("state_layout_version") == CURRENT_STATE_LAYOUT_VERSION
        and manifest["scheduler_database_synthesized"]
    ):
        raise ValueError("current-layout backup cannot claim a synthesized scheduler database")
    if not isinstance(manifest.get("files"), list):
        raise ValueError("backup files must be a list")
    _aware_timestamp(manifest.get("created_at"), "backup created_at")


def _validate_file_entry(entry: object) -> PurePosixPath:
    if not isinstance(entry, dict) or set(entry) != _FILE_KEYS:
        raise ValueError("backup file entry has an invalid shape")
    path = str(entry.get("path") or "")
    kind = entry.get("kind")
    if kind == "sqlite":
        relative = _safe_relative_path(path)
        if relative.as_posix() not in _DATABASES:
            raise ValueError("unsafe backup path")
    elif kind == "workflow_artifact":
        relative = _safe_relative_path(
            path, expected_prefix="workflows", expected_suffix=".json"
        )
    elif kind == "state_layout":
        relative = _safe_relative_path(path)
        if relative.as_posix() != STATE_LAYOUT_MARKER:
            raise ValueError("unsafe backup path")
    else:
        raise ValueError(
            "backup file kind must be sqlite, workflow_artifact, or state_layout"
        )
    if type(entry.get("size_bytes")) is not int or entry["size_bytes"] < 0:
        raise ValueError("backup file size_bytes must be a non-negative integer")
    checksum = entry.get("sha256")
    if not isinstance(checksum, str) or len(checksum) != 64 or any(
        char not in "0123456789abcdef" for char in checksum
    ):
        raise ValueError("backup file sha256 must be a lowercase SHA-256 digest")
    return relative


def _validate_runtime_state(
    root: Path,
    expected_artifacts=None,
    expected_layout: str = CURRENT_STATE_LAYOUT_VERSION,
) -> None:
    actual_layout = inspect_state_layout(root)
    if actual_layout != expected_layout:
        raise ValueError("backup state layout marker does not match manifest")
    if actual_layout == CURRENT_STATE_LAYOUT_VERSION:
        validate_current_state_marker(root)
    for database in _DATABASES:
        _validate_database(root / database, database)
    with closing(sqlite3.connect(root / "scheduler.sqlite3")) as connection:
        leases = connection.execute("select count(*) from scheduler_leases").fetchone()
        if leases and int(leases[0]) != 0:
            raise ValueError("backup scheduler lease table must be empty")
    remaining = set(expected_artifacts) if expected_artifacts is not None else None
    with closing(sqlite3.connect(root / "control.sqlite3")) as connection:
        records = _iter_workflow_artifact_records(connection)
        for relative_path, expected_checksum in records:
            if remaining is not None:
                if relative_path not in remaining:
                    raise ValueError("backup workflow artifacts do not match control state")
                remaining.remove(relative_path)
            path = root.joinpath(*PurePosixPath(relative_path).parts)
            _require_regular_no_symlink(path, "workflow artifact")
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError("workflow artifact is not valid UTF-8 JSON") from error
            if _json_checksum(payload) != expected_checksum:
                raise ValueError("workflow artifact checksum does not match control state")
    if remaining:
        raise ValueError("backup workflow artifacts do not match control state")


def _validate_database(path: Path, name: str) -> None:
    _require_regular_no_symlink(path, "SQLite database")
    try:
        with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as connection:
            integrity = connection.execute("pragma integrity_check").fetchone()
            if not integrity or str(integrity[0]).lower() != "ok":
                raise ValueError(f"SQLite integrity check failed: {name}")
            _require_tables(connection, name)
            if name == "control.sqlite3":
                audit_result = verify_audit_integrity(path)
                if audit_result.get("status") == "invalid":
                    raise ValueError("SQLite audit integrity check failed")
    except sqlite3.Error as error:
        raise ValueError(f"SQLite validation failed: {name}") from error


def _require_empty_synthesized_scheduler(path: Path) -> None:
    try:
        with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as connection:
            counts = [
                int(connection.execute(f'select count(*) from "{table}"').fetchone()[0])
                for table in (
                    "recurring_schedules",
                    "schedule_dispatches",
                    "scheduler_leases",
                )
            ]
    except sqlite3.Error as error:
        raise ValueError("synthesized scheduler database could not be validated") from error
    if any(counts):
        raise ValueError("synthesized scheduler database must be empty")


def _require_tables(connection, name: str) -> None:
    rows = connection.execute(
        "select name from sqlite_master where type = 'table'"
    ).fetchall()
    names = {str(row[0]) for row in rows}
    missing = _REQUIRED_TABLES[name] - names
    if missing:
        raise ValueError(f"SQLite database is missing required tables: {name}")
    for table, required_columns in _REQUIRED_COLUMNS[name].items():
        columns = {
            str(row[1])
            for row in connection.execute(f'pragma table_info("{table}")').fetchall()
        }
        if name == "control.sqlite3" and table == "audit_events":
            audit_columns = {
                *required_columns,
                "prev_digest",
                "digest",
            }
            if columns not in {frozenset(required_columns), frozenset(audit_columns)}:
                raise ValueError(f"SQLite table has an incompatible layout: {name}:{table}")
            continue
        if columns != required_columns:
            raise ValueError(f"SQLite table has an incompatible layout: {name}:{table}")
    for table, required_columns in _OPTIONAL_COLUMNS.get(name, {}).items():
        if table not in names:
            continue
        columns = {
            str(row[1])
            for row in connection.execute(f'pragma table_info("{table}")').fetchall()
        }
        if (
            name == "runs.sqlite3"
            and table == "run_summaries"
            and columns == required_columns - {"detail_projection_json"}
        ):
            # A pre-detail-projection backup is still a valid optional
            # summary layout; opening it with the current runtime upgrades the
            # projection in place before serving detail reads.
            continue
        if columns != required_columns:
            raise ValueError(f"SQLite table has an incompatible layout: {name}:{table}")
    if name == "runs.sqlite3" and "run_executions" in names:
        _validate_run_execution_ledger(connection)


def _validate_run_execution_ledger(connection) -> None:
    row = connection.execute(
        """
        select count(*)
        from run_executions e left join runs r on r.run_id = e.run_id
        where r.run_id is null
           or e.owner_id = ''
           or e.execution_id = ''
           or e.claimed_at = ''
           or e.updated_at = ''
           or e.status not in ('active', 'released', 'interrupted')
           or (e.status = 'active' and r.status not in ('created', 'running'))
           or (
                e.status = 'released'
                and r.status not in ('waiting', 'completed', 'failed', 'cancelled')
           )
           or (e.status = 'interrupted' and r.status != 'interrupted')
        """
    ).fetchone()
    if row and int(row[0]) != 0:
        raise ValueError("SQLite run execution ledger is invalid")


def _require_database_files(
    state_dir: Path,
    allow_missing_scheduler: bool = False,
) -> bool:
    scheduler_synthesized = False
    for name in _DATABASES:
        path = state_dir / name
        if (
            name == "scheduler.sqlite3"
            and allow_missing_scheduler
            and not path.exists()
            and not path.is_symlink()
        ):
            scheduler_synthesized = True
            continue
        _require_regular_no_symlink(path, "SQLite database")
    return scheduler_synthesized


def _safe_relative_path(
    value: str,
    expected_prefix: str = "",
    expected_suffix: str = "",
) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("unsafe backup path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("unsafe backup path")
    if path.as_posix() != value:
        raise ValueError("unsafe backup path")
    if expected_prefix and (not path.parts or path.parts[0] != expected_prefix):
        raise ValueError("unsafe backup path")
    if expected_prefix == "workflows":
        if len(path.parts) != 3 or any(
            not part
            or any(
                not (char.isalnum() or char in {"-", "_", "."})
                for char in part
            )
            for part in path.parts[1:]
        ):
            raise ValueError("unsafe backup path")
    if expected_suffix and not value.endswith(expected_suffix):
        raise ValueError("unsafe backup path")
    return path


def _require_no_symlink_components(root: Path, relative: PurePosixPath) -> None:
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("backup paths must not contain symbolic links")


def _require_owner_only_parent_directories(
    root: Path, relative: PurePosixPath
) -> None:
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if not current.is_dir():
            raise ValueError("backup parent path must be a directory")
        _require_owner_only_directory(current, "backup directory")


def _make_owner_only_parents(root: Path, relative: PurePosixPath) -> None:
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        current.mkdir(exist_ok=True)
        current.chmod(0o700)


def _existing_directory(path: Path, label: str) -> Path:
    value = Path(path)
    if value.is_symlink() or not value.exists() or not value.is_dir():
        raise ValueError(f"{label} must be an existing non-symlink directory")
    return value.resolve()


def _new_path(path: Path, label: str) -> Path:
    value = Path(path).expanduser()
    absolute = value if value.is_absolute() else Path.cwd() / value
    resolved = absolute.resolve(strict=False)
    if resolved.exists() or absolute.is_symlink():
        raise ValueError(f"{label} must not already exist")
    return resolved


def _require_regular_no_symlink(path: Path, label: str) -> None:
    try:
        details = path.lstat()
    except OSError as error:
        raise ValueError(f"{label} is missing") from error
    if stat.S_ISLNK(details.st_mode) or not stat.S_ISREG(details.st_mode):
        raise ValueError(f"{label} must be a regular non-symlink file")


def _require_owner_only_file(path: Path, label: str) -> None:
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError(f"{label} must not be accessible by group or others")


def _require_owner_only_directory(path: Path, label: str) -> None:
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError(f"{label} must not be accessible by group or others")


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _policy_checksum(policy: Dict[str, object]) -> str:
    payload = json.dumps(
        policy,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _json_checksum(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _aware_timestamp(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a timezone-aware ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{label} must be a timezone-aware ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must be a timezone-aware ISO-8601 timestamp")
    return parsed.astimezone(timezone.utc).isoformat()


def _validate_backup_list_limit(limit: object) -> None:
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_BACKUP_LIST_ITEMS
    ):
        raise ValueError(
            f"backup list limit must be an integer from 1 through {MAX_BACKUP_LIST_ITEMS}"
        )


def _backup_inventory_metadata(backup: Path):
    metadata = {
        "status": "invalid",
        "created_at": "",
        "state_layout_version": "",
        "workflow_artifact_count": 0,
        "file_count": 0,
        "total_bytes": 0,
    }
    try:
        manifest = _read_backup_manifest(backup)
        metadata.update(_backup_inventory_summary(manifest))
        sort_key = (
            1,
            _aware_timestamp(manifest["created_at"], "backup created_at"),
            backup.name,
        )
        return metadata, sort_key
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        try:
            fallback = f"{backup.stat().st_mtime_ns:020d}"
        except OSError:
            fallback = ""
        return metadata, (0, fallback, backup.name)


def _read_backup_manifest(backup: Path) -> Dict[str, object]:
    _require_owner_only_directory(backup, "backup directory")
    manifest_path = backup / "manifest.json"
    _require_regular_no_symlink(manifest_path, "backup manifest")
    _require_owner_only_file(manifest_path, "backup manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_manifest_shape(manifest)
    for entry in manifest["files"]:
        _validate_file_entry(entry)
    return manifest


def _backup_inventory_summary(manifest: Dict[str, object]) -> Dict[str, object]:
    return {
        "created_at": str(manifest["created_at"]),
        "state_layout_version": str(manifest["state_layout_version"]),
        "workflow_artifact_count": int(manifest["workflow_artifact_count"]),
        "file_count": len(manifest["files"]),
        "total_bytes": sum(int(entry["size_bytes"]) for entry in manifest["files"]),
    }


def _summary(status: str, backup_dir: Path) -> Dict[str, object]:
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
    return _state_summary(status, manifest)


def _state_summary(status: str, manifest: Dict[str, object]):
    return {
        "schema_version": BACKUP_SCHEMA_VERSION,
        "state_layout_version": str(manifest["state_layout_version"]),
        "status": status,
        "database_count": int(manifest["database_count"]),
        "workflow_artifact_count": int(manifest["workflow_artifact_count"]),
        "scheduler_database_synthesized": bool(
            manifest["scheduler_database_synthesized"]
        ),
        "file_count": len(manifest["files"]),
        "total_bytes": sum(int(entry["size_bytes"]) for entry in manifest["files"]),
    }
