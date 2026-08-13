"""Explicit state-layout identity for the self-hosted SQLite runtime."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Dict


STATE_LAYOUT_MARKER = "state-layout.json"
STATE_LAYOUT_MARKER_SCHEMA = "skill2workflow-state-layout-marker-0.1.0"
CURRENT_STATE_LAYOUT_VERSION = "skill2workflow-sqlite-layout-0.1.0"
LEGACY_STATE_LAYOUT_VERSION = "skill2workflow-sqlite-layout-legacy-unversioned"
EMPTY_STATE_LAYOUT = "empty"
_DATABASES = ("control.sqlite3", "runs.sqlite3", "scheduler.sqlite3")
_MARKER_KEYS = {"schema_version", "state_layout_version", "service_initialized"}
MAX_STATE_LAYOUT_MARKER_BYTES = 16 * 1024


def inspect_state_layout(state_dir: Path) -> str:
    """Return the supported current, legacy, or empty state-layout identity."""

    root = Path(state_dir)
    if root.is_symlink():
        raise ValueError("state directory must not be a symbolic link")
    marker_path = root / STATE_LAYOUT_MARKER
    if marker_path.is_symlink():
        raise ValueError("state layout marker must be a regular non-symlink file")
    if marker_path.exists():
        marker = _read_marker(marker_path)
        version = marker["state_layout_version"]
        if version != CURRENT_STATE_LAYOUT_VERSION:
            raise ValueError(f"unsupported state layout: {version}")
        return CURRENT_STATE_LAYOUT_VERSION
    if any((root / name).exists() or (root / name).is_symlink() for name in _DATABASES):
        return LEGACY_STATE_LAYOUT_VERSION
    return EMPTY_STATE_LAYOUT


def ensure_current_state_layout(state_dir: Path) -> None:
    """Initialize a fresh state marker or reject state needing an explicit upgrade."""

    root = Path(state_dir)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    layout = inspect_state_layout(root)
    if layout == EMPTY_STATE_LAYOUT:
        write_state_layout_marker(root)
        return
    if layout == LEGACY_STATE_LAYOUT_VERSION:
        raise ValueError(
            "legacy SQLite state requires an explicit state-upgrade into a new directory"
        )


def ensure_service_state_layout(state_dir: Path) -> None:
    """Reject incompatible or partial existing state before service initialization."""

    root = Path(state_dir)
    layout = inspect_state_layout(root)
    if layout == EMPTY_STATE_LAYOUT:
        return
    if layout == LEGACY_STATE_LAYOUT_VERSION:
        raise ValueError(
            "legacy SQLite state requires an explicit state-upgrade into a new directory"
        )
    marker = _read_marker(root / STATE_LAYOUT_MARKER)
    for name in _DATABASES:
        path = root / name
        try:
            details = path.lstat()
        except OSError as error:
            if marker["service_initialized"]:
                raise ValueError(
                    "service refuses incomplete current state; restore or upgrade a verified copy"
                ) from error
            continue
        if stat.S_ISLNK(details.st_mode) or not stat.S_ISREG(details.st_mode):
            raise ValueError(
                "service refuses incomplete current state; SQLite databases must be regular files"
            )


def write_state_layout_marker(
    state_dir: Path,
    service_initialized: bool = False,
) -> Dict[str, object]:
    """Create the current owner-only marker without exposing a partial file."""

    root = Path(state_dir)
    if root.is_symlink():
        raise ValueError("state directory must not be a symbolic link")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    marker_path = root / STATE_LAYOUT_MARKER
    marker = {
        "schema_version": STATE_LAYOUT_MARKER_SCHEMA,
        "state_layout_version": CURRENT_STATE_LAYOUT_VERSION,
        "service_initialized": bool(service_initialized),
    }
    payload = (json.dumps(marker, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temporary_path = None
    temporary_descriptor = None
    try:
        temporary_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{STATE_LAYOUT_MARKER}.",
            dir=str(root),
        )
        temporary_path = Path(temporary_name)
        os.fchmod(temporary_descriptor, 0o600)
        with os.fdopen(temporary_descriptor, "wb") as handle:
            temporary_descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # Linking a fully-written temporary inode publishes the marker
            # without replacing a concurrently-created marker.
            os.link(temporary_path, marker_path)
        except FileExistsError:
            if inspect_state_layout(root) != CURRENT_STATE_LAYOUT_VERSION:
                raise ValueError("state layout marker already exists with an incompatible value")
            return validate_current_state_marker(root)
        return marker
    finally:
        if temporary_descriptor is not None:
            try:
                os.close(temporary_descriptor)
            except OSError:
                pass
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass


def mark_service_state_initialized(state_dir: Path) -> Dict[str, object]:
    """Durably record that all service databases were initialized successfully."""

    root = Path(state_dir)
    marker_path = root / STATE_LAYOUT_MARKER
    marker = _read_marker(marker_path)
    for name in _DATABASES:
        path = root / name
        try:
            details = path.lstat()
        except OSError as error:
            raise ValueError("service state cannot be marked initialized while incomplete") from error
        if stat.S_ISLNK(details.st_mode) or not stat.S_ISREG(details.st_mode):
            raise ValueError("service state databases must be regular non-symlink files")
    if marker["service_initialized"]:
        return marker
    marker["service_initialized"] = True
    payload = (json.dumps(marker, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{STATE_LAYOUT_MARKER}.", dir=str(root)
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, marker_path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()
    return marker


def validate_current_state_marker(state_dir: Path) -> Dict[str, object]:
    """Validate and return the current marker document."""

    root = Path(state_dir)
    if inspect_state_layout(root) != CURRENT_STATE_LAYOUT_VERSION:
        raise ValueError("state layout marker is not current")
    return _read_marker(root / STATE_LAYOUT_MARKER)


def _read_marker(path: Path) -> Dict[str, object]:
    try:
        details = path.lstat()
    except OSError as error:
        raise ValueError("state layout marker is not valid owner-only UTF-8 JSON") from error
    if not stat.S_ISREG(details.st_mode) or stat.S_ISLNK(details.st_mode):
        raise ValueError("state layout marker must be a regular non-symlink file")
    if stat.S_IMODE(details.st_mode) & 0o077:
        raise ValueError("state layout marker must not be accessible by group or others")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError("state layout marker changed or could not be opened safely") from error
    try:
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_dev != details.st_dev
                or opened.st_ino != details.st_ino
            ):
                raise ValueError(
                    "state layout marker changed or could not be opened safely"
                )
            if stat.S_IMODE(opened.st_mode) & 0o077:
                raise ValueError(
                    "state layout marker must not be accessible by group or others"
                )
            if opened.st_size > MAX_STATE_LAYOUT_MARKER_BYTES:
                raise ValueError("state layout marker exceeds the size limit")
            chunks = []
            remaining = MAX_STATE_LAYOUT_MARKER_BYTES + 1
            while remaining:
                chunk = os.read(descriptor, min(4096, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            payload = b"".join(chunks)
            if len(payload) > MAX_STATE_LAYOUT_MARKER_BYTES:
                raise ValueError("state layout marker exceeds the size limit")
        except OSError as error:
            raise ValueError(
                "state layout marker changed or could not be opened safely"
            ) from error
    finally:
        os.close(descriptor)

    try:
        marker = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("state layout marker is not valid owner-only UTF-8 JSON") from error
    if not isinstance(marker, dict) or set(marker) != _MARKER_KEYS:
        raise ValueError("state layout marker has an invalid shape")
    if marker.get("schema_version") != STATE_LAYOUT_MARKER_SCHEMA:
        raise ValueError("unsupported state layout marker schema")
    version = marker.get("state_layout_version")
    if not isinstance(version, str) or not version:
        raise ValueError("state layout marker version must be a non-empty string")
    if type(marker.get("service_initialized")) is not bool:
        raise ValueError("state layout marker service_initialized must be a boolean")
    return {
        "schema_version": str(marker["schema_version"]),
        "state_layout_version": version,
        "service_initialized": marker["service_initialized"],
    }
