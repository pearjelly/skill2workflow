"""Copy-on-write upgrade path for self-hosted SQLite state."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Dict

from .backup import (
    create_state_backup,
    inspect_state_backup_readiness,
    restore_state_backup,
    verify_state_backup,
)
from .state_layout import (
    CURRENT_STATE_LAYOUT_VERSION,
    LEGACY_STATE_LAYOUT_VERSION,
    inspect_state_layout,
    write_state_layout_marker,
)


UPGRADE_EVIDENCE_SCHEMA_VERSION = "skill2workflow-state-upgrade-0.1.0"


def inspect_state_upgrade(
    state_dir: Path,
    now_epoch: float = None,
) -> Dict[str, object]:
    """Return a compact, read-only upgrade decision for one state directory."""

    source = _existing_directory(state_dir, "state directory")
    layout = inspect_state_layout(source)
    if layout == CURRENT_STATE_LAYOUT_VERSION:
        status = "current"
    elif layout == LEGACY_STATE_LAYOUT_VERSION:
        status = "upgrade_required"
    else:
        raise ValueError("state upgrade requires initialized SQLite state")
    readiness = inspect_state_backup_readiness(source, now_epoch=now_epoch)
    return {
        "schema_version": UPGRADE_EVIDENCE_SCHEMA_VERSION,
        "status": status,
        "source_layout_version": layout,
        "target_layout_version": CURRENT_STATE_LAYOUT_VERSION,
        "strategy": "copy_on_write",
        "source_preserved": True,
        "preupgrade_backup_required": True,
        "database_count": int(readiness["database_count"]),
        "workflow_artifact_count": int(readiness["workflow_artifact_count"]),
        "scheduler_database_synthesized": bool(
            readiness["scheduler_database_synthesized"]
        ),
    }


def upgrade_state(
    state_dir: Path,
    output_dir: Path,
    backup_dir: Path,
    now_epoch: float = None,
) -> Dict[str, object]:
    """Back up legacy state and atomically publish an upgraded copy."""

    source = _existing_directory(state_dir, "state directory")
    plan = inspect_state_upgrade(source, now_epoch=now_epoch)
    if plan["status"] == "current":
        raise ValueError("state layout is already current; no upgrade is required")
    output = _new_path(output_dir, "upgrade output directory")
    backup = _new_path(backup_dir, "pre-upgrade backup directory")
    if _is_within(output, source) or _is_within(backup, source):
        raise ValueError("upgrade output and backup directories must be outside the source state")
    if _is_within(output, backup) or _is_within(backup, output):
        raise ValueError("upgrade output and backup directories must be separate")

    backup_summary = create_state_backup(source, backup, now_epoch=now_epoch)
    if backup_summary["state_layout_version"] != plan["source_layout_version"]:
        raise ValueError("source layout changed during state upgrade")
    verify_state_backup(backup)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging_root = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.upgrade-", dir=str(output.parent))
    )
    staging_root.chmod(0o700)
    upgraded = staging_root / "state"
    verification_backup = staging_root / "verification-backup"
    completed = False
    try:
        restore_state_backup(backup, upgraded)
        write_state_layout_marker(upgraded, service_initialized=True)
        current_backup = create_state_backup(upgraded, verification_backup)
        if current_backup["state_layout_version"] != CURRENT_STATE_LAYOUT_VERSION:
            raise ValueError("upgraded state did not reach the current layout")
        verify_state_backup(verification_backup)
        shutil.rmtree(verification_backup)
        upgraded.rename(output)
        completed = True
    finally:
        if staging_root.exists():
            try:
                shutil.rmtree(staging_root)
            except OSError:
                # The output rename is the commit point. A private staging cleanup
                # failure must not turn a published upgrade into ambiguous failure.
                pass

    if not completed:
        raise ValueError("state upgrade did not publish an output directory")
    return {
        "schema_version": UPGRADE_EVIDENCE_SCHEMA_VERSION,
        "status": "upgraded",
        "source_layout_version": LEGACY_STATE_LAYOUT_VERSION,
        "target_layout_version": CURRENT_STATE_LAYOUT_VERSION,
        "strategy": "copy_on_write",
        "source_preserved": True,
        "preupgrade_backup_status": "valid",
        "database_count": int(backup_summary["database_count"]),
        "workflow_artifact_count": int(backup_summary["workflow_artifact_count"]),
        "scheduler_database_synthesized": bool(
            backup_summary["scheduler_database_synthesized"]
        ),
    }


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
