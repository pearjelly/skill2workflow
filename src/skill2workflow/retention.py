"""Copy-on-write retention for sensitive self-hosted SQLite runtime state."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from .backup import (
    create_state_backup,
    inspect_state_backup_readiness,
    restore_state_backup,
    verify_state_backup,
)
from .state_layout import CURRENT_STATE_LAYOUT_VERSION, inspect_state_layout


LEGACY_RETENTION_POLICY_SCHEMA_VERSION = "skill2workflow-retention-policy-0.1.0"
CANCELLATION_RETENTION_POLICY_SCHEMA_VERSION = "skill2workflow-retention-policy-0.2.0"
RETENTION_POLICY_SCHEMA_VERSION = "skill2workflow-retention-policy-0.3.0"
RETENTION_EVIDENCE_SCHEMA_VERSION = "skill2workflow-state-retention-0.3.0"
LEGACY_TERMINAL_RUN_STATUSES = ("completed", "failed")
CANCELLATION_TERMINAL_RUN_STATUSES = ("completed", "failed", "cancelled")
TERMINAL_RUN_STATUSES = ("completed", "failed", "cancelled", "interrupted")
TERMINAL_DISPATCH_STATUSES = ("completed", "failed", "skipped", "uncertain")
_POLICY_KEYS = {"schema_version", "retention"}
_RETENTION_KEYS = {
    "delete_before",
    "terminal_run_statuses",
    "terminal_dispatch_statuses",
}


def normalize_retention_policy(policy: object) -> Dict[str, object]:
    """Validate and canonicalize the deliberately narrow retention policy."""

    if not isinstance(policy, dict) or set(policy) != _POLICY_KEYS:
        raise ValueError("retention policy must contain only schema_version and retention")
    schema_version = policy.get("schema_version")
    if schema_version not in {
        LEGACY_RETENTION_POLICY_SCHEMA_VERSION,
        CANCELLATION_RETENTION_POLICY_SCHEMA_VERSION,
        RETENTION_POLICY_SCHEMA_VERSION,
    }:
        raise ValueError(
            "retention policy schema_version must be a supported version"
        )
    retention = policy.get("retention")
    if not isinstance(retention, dict) or set(retention) != _RETENTION_KEYS:
        raise ValueError("retention policy retention section has an invalid shape")
    cutoff = _normalize_cutoff(retention.get("delete_before"))
    if schema_version == LEGACY_RETENTION_POLICY_SCHEMA_VERSION:
        run_statuses = LEGACY_TERMINAL_RUN_STATUSES
    elif schema_version == CANCELLATION_RETENTION_POLICY_SCHEMA_VERSION:
        run_statuses = CANCELLATION_TERMINAL_RUN_STATUSES
    else:
        run_statuses = TERMINAL_RUN_STATUSES
    if retention.get("terminal_run_statuses") != list(run_statuses):
        raise ValueError(
            "retention terminal_run_statuses do not match the policy version"
        )
    if retention.get("terminal_dispatch_statuses") != list(
        TERMINAL_DISPATCH_STATUSES
    ):
        raise ValueError(
            "retention terminal_dispatch_statuses must be completed, failed, skipped, and uncertain"
        )
    return {
        "schema_version": schema_version,
        "retention": {
            "delete_before": cutoff,
            "terminal_run_statuses": list(run_statuses),
            "terminal_dispatch_statuses": list(TERMINAL_DISPATCH_STATUSES),
        },
    }


def inspect_state_retention(
    state_dir: Path,
    policy: object,
    now_epoch: float = None,
) -> Dict[str, object]:
    """Return a read-only aggregate deletion plan for stopped current state."""

    source = _existing_directory(state_dir, "state directory")
    normalized = normalize_retention_policy(policy)
    if inspect_state_layout(source) != CURRENT_STATE_LAYOUT_VERSION:
        raise ValueError("state retention requires the current SQLite state layout")
    inspect_state_backup_readiness(source, now_epoch=now_epoch, require_stopped=True)
    cutoff = str(normalized["retention"]["delete_before"])
    run_statuses = tuple(normalized["retention"]["terminal_run_statuses"])
    dispatch_statuses = tuple(normalized["retention"]["terminal_dispatch_statuses"])
    run_database = source / "runs.sqlite3"
    return {
        "schema_version": RETENTION_EVIDENCE_SCHEMA_VERSION,
        "status": "ready",
        "strategy": "copy_on_write",
        "source_preserved": True,
        "policy_sha256": _policy_checksum(normalized),
        "delete_before": cutoff,
        "eligible_terminal_runs": _eligible_run_count(run_database, cutoff, run_statuses),
        "eligible_run_events": _eligible_run_event_count(run_database, cutoff, run_statuses),
        "eligible_run_cancellations": _eligible_run_cancellation_count(
            run_database, cutoff, run_statuses
        ),
        "eligible_run_executions": _eligible_run_execution_count(
            run_database, cutoff, run_statuses
        ),
        "eligible_run_audit_events": _eligible_run_audit_count(
            source / "control.sqlite3", run_database, cutoff, run_statuses
        ),
        "eligible_terminal_dispatches": _eligible_dispatch_count(
            source / "scheduler.sqlite3", cutoff, dispatch_statuses
        ),
        "preserved_nonterminal_runs": _nonterminal_run_count(
            source / "runs.sqlite3", run_statuses
        ),
        "preserved_claimed_dispatches": _claimed_dispatch_count(
            source / "scheduler.sqlite3"
        ),
    }


def apply_state_retention(
    state_dir: Path,
    output_dir: Path,
    policy: object,
    now_epoch: float = None,
) -> Dict[str, object]:
    """Atomically publish a verified retained copy while preserving the source."""

    source = _existing_directory(state_dir, "state directory")
    normalized = normalize_retention_policy(policy)
    inspect_state_retention(source, normalized, now_epoch=now_epoch)
    output = _new_path(output_dir, "retention output directory")
    if _is_within(output, source):
        raise ValueError("retention output directory must be outside the source state")

    output.parent.mkdir(parents=True, exist_ok=True)
    staging_root = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.retention-", dir=str(output.parent))
    )
    staging_root.chmod(0o700)
    source_backup = staging_root / "source-backup"
    retained = staging_root / "retained-state"
    verification_backup = staging_root / "verification-backup"
    published = False
    counts = None
    snapshot_plan = None
    try:
        create_state_backup(source, source_backup, now_epoch=now_epoch)
        verify_state_backup(source_backup)
        restore_state_backup(source_backup, retained)
        snapshot_plan = inspect_state_retention(
            retained,
            normalized,
            now_epoch=now_epoch,
        )
        counts = _purge_retained_copy(
            retained,
            str(normalized["retention"]["delete_before"]),
            tuple(normalized["retention"]["terminal_run_statuses"]),
            tuple(normalized["retention"]["terminal_dispatch_statuses"]),
        )
        expected = {
            "deleted_terminal_runs": snapshot_plan["eligible_terminal_runs"],
            "deleted_run_events": snapshot_plan["eligible_run_events"],
            "deleted_run_cancellations": snapshot_plan[
                "eligible_run_cancellations"
            ],
            "deleted_run_executions": snapshot_plan[
                "eligible_run_executions"
            ],
            "deleted_run_audit_events": snapshot_plan["eligible_run_audit_events"],
            "deleted_terminal_dispatches": snapshot_plan[
                "eligible_terminal_dispatches"
            ],
        }
        if counts != expected:
            raise ValueError("retention result did not match the verified deletion plan")
        inspect_state_backup_readiness(retained, require_stopped=True)
        create_state_backup(retained, verification_backup)
        verify_state_backup(verification_backup)
        shutil.rmtree(source_backup)
        shutil.rmtree(verification_backup)
        retained.rename(output)
        published = True
    finally:
        if staging_root.exists():
            try:
                shutil.rmtree(staging_root)
            except OSError:
                # The requested output rename is the commit point. Cleanup failure
                # must not turn a published copy into an ambiguous result, and an
                # earlier operation error remains the authoritative failure.
                pass

    if not published or counts is None or snapshot_plan is None:
        raise ValueError("state retention did not publish an output directory")
    return {
        "schema_version": RETENTION_EVIDENCE_SCHEMA_VERSION,
        "status": "retained_copy_created",
        "strategy": "copy_on_write",
        "source_preserved": True,
        "policy_sha256": snapshot_plan["policy_sha256"],
        "delete_before": snapshot_plan["delete_before"],
        **counts,
        "preserved_nonterminal_runs": snapshot_plan["preserved_nonterminal_runs"],
        "preserved_claimed_dispatches": snapshot_plan[
            "preserved_claimed_dispatches"
        ],
    }


def _purge_retained_copy(
    state_dir: Path,
    cutoff: str,
    run_statuses,
    dispatch_statuses,
) -> Dict[str, int]:
    run_database = state_dir / "runs.sqlite3"
    control_database = state_dir / "control.sqlite3"
    scheduler_database = state_dir / "scheduler.sqlite3"
    with closing(sqlite3.connect(control_database)) as connection:
        connection.execute("pragma secure_delete = on")
        connection.execute(
            "attach database ? as run_state",
            (run_database.resolve().as_uri() + "?mode=ro",),
        )
        placeholders = ",".join("?" for _ in run_statuses)
        cursor = connection.execute(
            f"""
            delete from audit_events
            where exists (
                select 1 from run_state.runs
                where run_state.runs.run_id = audit_events.run_id
                  and run_state.runs.status in ({placeholders})
                  and julianday(run_state.runs.updated_at) < julianday(?)
            )
            """,
            (*run_statuses, cutoff),
        )
        deleted_audit = int(cursor.rowcount)
        connection.commit()
        connection.execute("detach database run_state")
        connection.execute("vacuum")
    with closing(sqlite3.connect(run_database)) as connection:
        connection.execute("pragma secure_delete = on")
        placeholders = ",".join("?" for _ in run_statuses)
        deleted_cancellations = 0
        if _table_exists(connection, "run_cancellations"):
            cursor = connection.execute(
                f"""
                delete from run_cancellations
                where run_id in (
                    select run_id from runs
                    where status in ({placeholders})
                      and julianday(updated_at) < julianday(?)
                )
                """,
                (*run_statuses, cutoff),
            )
            deleted_cancellations = int(cursor.rowcount)
        deleted_executions = 0
        if _table_exists(connection, "run_executions"):
            cursor = connection.execute(
                f"""
                delete from run_executions
                where run_id in (
                    select run_id from runs
                    where status in ({placeholders})
                      and julianday(updated_at) < julianday(?)
                )
                """,
                (*run_statuses, cutoff),
            )
            deleted_executions = int(cursor.rowcount)
        cursor = connection.execute(
            f"""
            delete from run_events
            where run_id in (
                select run_id from runs
                where status in ({placeholders})
                  and julianday(updated_at) < julianday(?)
            )
            """,
            (*run_statuses, cutoff),
        )
        deleted_events = int(cursor.rowcount)
        cursor = connection.execute(
            f"""
            delete from runs
            where status in ({placeholders})
              and julianday(updated_at) < julianday(?)
            """,
            (*run_statuses, cutoff),
        )
        deleted_runs = int(cursor.rowcount)
        connection.commit()
        connection.execute("vacuum")
    with closing(sqlite3.connect(scheduler_database)) as connection:
        connection.execute("pragma secure_delete = on")
        placeholders = ",".join("?" for _ in dispatch_statuses)
        cursor = connection.execute(
            f"""
            delete from schedule_dispatches
            where status in ({placeholders})
              and julianday(scheduled_for) < julianday(?)
            """,
            (*dispatch_statuses, cutoff),
        )
        deleted_dispatches = int(cursor.rowcount)
        connection.commit()
        connection.execute("vacuum")
    return {
        "deleted_terminal_runs": deleted_runs,
        "deleted_run_events": deleted_events,
        "deleted_run_cancellations": deleted_cancellations,
        "deleted_run_executions": deleted_executions,
        "deleted_run_audit_events": deleted_audit,
        "deleted_terminal_dispatches": deleted_dispatches,
    }


def _eligible_run_count(database: Path, cutoff: str, run_statuses) -> int:
    placeholders = ",".join("?" for _ in run_statuses)
    with _readonly(database) as connection:
        row = connection.execute(
            f"""
            select count(*) from runs
            where status in ({placeholders})
              and julianday(updated_at) < julianday(?)
            """,
            (*run_statuses, cutoff),
        ).fetchone()
    return int(row[0])


def _eligible_run_event_count(database: Path, cutoff: str, run_statuses) -> int:
    placeholders = ",".join("?" for _ in run_statuses)
    with _readonly(database) as connection:
        row = connection.execute(
            f"""
            select count(*) from run_events
            where run_id in (
                select run_id from runs
                where status in ({placeholders})
                  and julianday(updated_at) < julianday(?)
            )
            """,
            (*run_statuses, cutoff),
        ).fetchone()
    return int(row[0])


def _eligible_run_cancellation_count(database: Path, cutoff: str, run_statuses) -> int:
    placeholders = ",".join("?" for _ in run_statuses)
    with _readonly(database) as connection:
        if not _table_exists(connection, "run_cancellations"):
            return 0
        row = connection.execute(
            f"""
            select count(*) from run_cancellations
            where run_id in (
                select run_id from runs
                where status in ({placeholders})
                  and julianday(updated_at) < julianday(?)
            )
            """,
            (*run_statuses, cutoff),
        ).fetchone()
    return int(row[0])


def _eligible_run_execution_count(database: Path, cutoff: str, run_statuses) -> int:
    placeholders = ",".join("?" for _ in run_statuses)
    with _readonly(database) as connection:
        if not _table_exists(connection, "run_executions"):
            return 0
        row = connection.execute(
            f"""
            select count(*) from run_executions
            where run_id in (
                select run_id from runs
                where status in ({placeholders})
                  and julianday(updated_at) < julianday(?)
            )
            """,
            (*run_statuses, cutoff),
        ).fetchone()
    return int(row[0])


def _eligible_run_audit_count(
    control_database: Path, run_database: Path, cutoff: str, run_statuses
) -> int:
    placeholders = ",".join("?" for _ in run_statuses)
    with _readonly(control_database) as connection:
        connection.execute(
            "attach database ? as run_state",
            (run_database.resolve().as_uri() + "?mode=ro",),
        )
        row = connection.execute(
            f"""
            select count(*) from audit_events
            where exists (
                select 1 from run_state.runs
                where run_state.runs.run_id = audit_events.run_id
                  and run_state.runs.status in ({placeholders})
                  and julianday(run_state.runs.updated_at) < julianday(?)
            )
            """,
            (*run_statuses, cutoff),
        ).fetchone()
        connection.execute("detach database run_state")
    return int(row[0])


def _eligible_dispatch_count(database: Path, cutoff: str, dispatch_statuses) -> int:
    placeholders = ",".join("?" for _ in dispatch_statuses)
    with _readonly(database) as connection:
        row = connection.execute(
            f"""
            select count(*) from schedule_dispatches
            where status in ({placeholders})
              and julianday(scheduled_for) < julianday(?)
            """,
            (*dispatch_statuses, cutoff),
        ).fetchone()
    return int(row[0])


def _nonterminal_run_count(database: Path, run_statuses) -> int:
    placeholders = ",".join("?" for _ in run_statuses)
    with _readonly(database) as connection:
        row = connection.execute(
            f"select count(*) from runs where status not in ({placeholders})",
            run_statuses,
        ).fetchone()
    return int(row[0])


def _claimed_dispatch_count(database: Path) -> int:
    with _readonly(database) as connection:
        row = connection.execute(
            "select count(*) from schedule_dispatches where status = 'claimed'"
        ).fetchone()
    return int(row[0])


def _readonly(database: Path):
    return closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True))


def _table_exists(connection, table: str) -> bool:
    row = connection.execute(
        "select 1 from sqlite_master where type = 'table' and name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _policy_checksum(policy: Dict[str, object]) -> str:
    payload = json.dumps(
        policy,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalize_cutoff(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("retention delete_before must be an aware ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(
            "retention delete_before must be an aware ISO-8601 timestamp"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("retention delete_before must be an aware ISO-8601 timestamp")
    return parsed.astimezone(timezone.utc).isoformat()


def _existing_directory(path: Path, label: str) -> Path:
    value = Path(path).expanduser()
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


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
