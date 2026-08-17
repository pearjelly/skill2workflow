"""Generate one least-privilege systemd unit for a self-hosted service."""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
from typing import Dict, Optional

from .service import ServiceConfig, parse_service_config


SYSTEMD_SERVICE_UNIT_RESULT_SCHEMA_VERSION = (
    "skill2workflow-systemd-service-unit-result-0.1.0"
)
MAX_SYSTEMD_SERVICE_CONFIG_BYTES = 64 * 1024
_IDENTITY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,63}\Z")
_UNIT_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\.service\Z")
_UNSAFE_UNIT_ARGUMENT_CHARACTERS = {"\x00", "\r", "\n", "\t", " ", '"', "'", "\\", "$", "%"}


def write_systemd_service_unit(
    config_path: Path,
    output_path: Path,
    *,
    service_user: str,
    executable: Path,
    service_group: Optional[str] = None,
) -> Dict[str, str]:
    """Write a non-overwriting hardened systemd unit for one service workspace.

    The caller remains responsible for placing the unit under systemd, selecting
    an existing OS identity, and explicitly enabling it.  This function neither
    runs systemctl nor reads a credential value.
    """

    config_file, payload = _read_private_service_config(config_path)
    loaded = parse_service_config(payload)
    config = ServiceConfig(
        host=loaded.host,
        port=loaded.port,
        state_dir=_private_directory(loaded.state_dir, "service state directory"),
        storage=loaded.storage,
        auth_token_file=_private_regular_file(
            loaded.auth_token_file,
            "service auth token",
        ),
        credential_dir=_private_directory(
            loaded.credential_dir,
            "service credential directory",
        ),
        backup_parent_dir=(
            _private_directory(loaded.backup_parent_dir, "service backup parent directory")
            if loaded.backup_parent_dir is not None
            else None
        ),
        http_allowed_origins=loaded.http_allowed_origins,
    )
    unit_file = _new_unit_file(output_path)
    user = _identity(service_user, "service user")
    group = _identity(service_group or user, "service group")
    command = _regular_executable(executable)
    _validate_unit_paths(config_file, config, command)
    rendered = _render_unit(
        unit_name=unit_file.name,
        config_file=config_file,
        config=config,
        service_user=user,
        service_group=group,
        executable=command,
    )
    _write_new_unit(unit_file, rendered)
    return {
        "schema_version": SYSTEMD_SERVICE_UNIT_RESULT_SCHEMA_VERSION,
        "status": "written",
        "unit_name": unit_file.name,
        "unit_file": str(unit_file),
        "service_user": user,
        "service_group": group,
        "config_file": str(config_file),
        "state_dir": str(config.state_dir),
    }


def _private_regular_file(path: Path, label: str) -> Path:
    candidate, _ = _private_regular_file_details(path, label)
    try:
        return candidate.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"{label} is unavailable") from error


def _read_private_service_config(path: Path):
    """Read one bounded config through the checked no-follow file descriptor."""

    candidate, before = _private_regular_file_details(path, "service config")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(candidate, flags)
    except OSError as error:
        raise ValueError("service config is unavailable") from error
    try:
        try:
            opened = os.fstat(descriptor)
            if not _same_entry(before, opened) or not stat.S_ISREG(opened.st_mode):
                raise ValueError("service config changed while being read")
            if stat.S_IMODE(opened.st_mode) & 0o077:
                raise ValueError("service config must not be accessible by group or others")
            if opened.st_size > MAX_SYSTEMD_SERVICE_CONFIG_BYTES:
                raise ValueError("service config exceeds the size limit")
            chunks = []
            remaining = MAX_SYSTEMD_SERVICE_CONFIG_BYTES + 1
            while remaining:
                chunk = os.read(descriptor, min(4096, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            if len(raw) > MAX_SYSTEMD_SERVICE_CONFIG_BYTES:
                raise ValueError("service config exceeds the size limit")
            after = candidate.lstat()
            if not _same_entry(before, after):
                raise ValueError("service config changed while being read")
        except OSError as error:
            raise ValueError("service config is unavailable") from error
    finally:
        os.close(descriptor)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("service config is unavailable") from error
    try:
        return candidate.resolve(strict=True), payload
    except OSError as error:
        raise ValueError("service config is unavailable") from error


def _private_regular_file_details(path: Path, label: str):
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ValueError(f"{label} must be an absolute path")
    try:
        details = candidate.lstat()
    except OSError as error:
        raise ValueError(f"{label} is unavailable") from error
    if stat.S_ISLNK(details.st_mode) or not stat.S_ISREG(details.st_mode):
        raise ValueError(f"{label} must be a regular non-symlink file")
    if stat.S_IMODE(details.st_mode) & 0o077:
        raise ValueError(f"{label} must not be accessible by group or others")
    return candidate, details


def _same_entry(first, second) -> bool:
    return first.st_dev == second.st_dev and first.st_ino == second.st_ino


def _new_unit_file(path: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ValueError("systemd unit output must be an absolute path")
    if not _UNIT_NAME_PATTERN.fullmatch(candidate.name):
        raise ValueError("systemd unit output name must end with .service")
    try:
        parent = candidate.parent.resolve(strict=True)
    except OSError as error:
        raise ValueError("systemd unit output parent is unavailable") from error
    if not parent.is_dir():
        raise ValueError("systemd unit output parent must be a directory")
    output = parent / candidate.name
    try:
        output.lstat()
    except FileNotFoundError:
        return output
    except OSError as error:
        raise ValueError("systemd unit output is unavailable") from error
    raise ValueError("systemd unit output must not already exist")


def _private_directory(path: Path, label: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ValueError(f"{label} must be an absolute path")
    try:
        details = candidate.lstat()
    except OSError as error:
        raise ValueError(f"{label} is unavailable") from error
    if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
        raise ValueError(f"{label} must be a directory and not a symbolic link")
    if stat.S_IMODE(details.st_mode) & 0o077:
        raise ValueError(f"{label} must not be accessible by group or others")
    try:
        return candidate.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"{label} is unavailable") from error


def _identity(value: object, label: str) -> str:
    if not isinstance(value, str) or not _IDENTITY_PATTERN.fullmatch(value):
        raise ValueError(f"{label} must be a simple POSIX account name")
    return value


def _regular_executable(path: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ValueError("service executable must be an absolute path")
    try:
        details = candidate.lstat()
    except OSError as error:
        raise ValueError("service executable must be a regular executable file") from error
    if (
        stat.S_ISLNK(details.st_mode)
        or not stat.S_ISREG(details.st_mode)
        or not details.st_mode & 0o111
    ):
        raise ValueError("service executable must be a regular executable file")
    try:
        return candidate.resolve(strict=True)
    except OSError as error:
        raise ValueError("service executable must be a regular executable file") from error


def _validate_unit_paths(config_file: Path, config: ServiceConfig, executable: Path) -> None:
    values = {
        "service config": config_file,
        "service state directory": config.state_dir,
        "service auth token": config.auth_token_file,
        "service credential directory": config.credential_dir,
        "service executable": executable,
    }
    if config.backup_parent_dir is not None:
        values["service backup parent directory"] = config.backup_parent_dir
    for label, path in values.items():
        _unit_argument(label, path)

    if config.port == 0:
        raise ValueError("service config port must be nonzero for a supervised service")

    writable = config.state_dir
    for label, protected in (
        ("service config", config_file),
        ("service auth token", config.auth_token_file),
        ("service credential directory", config.credential_dir),
        ("service executable", executable),
    ):
        if _paths_overlap(writable, protected):
            raise ValueError(f"{label} must not overlap the writable service state directory")
    if config.backup_parent_dir is not None and _paths_overlap(
        writable, config.backup_parent_dir
    ):
        raise ValueError(
            "service backup parent directory must not overlap the writable service state directory"
        )


def _unit_argument(label: str, path: Path) -> str:
    value = str(path)
    if not Path(value).is_absolute():
        raise ValueError(f"{label} must be an absolute path")
    if any(character in _UNSAFE_UNIT_ARGUMENT_CHARACTERS for character in value):
        raise ValueError(f"{label} contains characters unsafe for a systemd unit")
    return value


def _paths_overlap(first: Path, second: Path) -> bool:
    try:
        first.relative_to(second)
        return True
    except ValueError:
        pass
    try:
        second.relative_to(first)
        return True
    except ValueError:
        return False


def _render_unit(
    *,
    unit_name: str,
    config_file: Path,
    config: ServiceConfig,
    service_user: str,
    service_group: str,
    executable: Path,
) -> str:
    """Return a deterministic unit with no credential values or environment."""

    config_value = _unit_argument("service config", config_file)
    state_value = _unit_argument("service state directory", config.state_dir)
    token_value = _unit_argument("service auth token", config.auth_token_file)
    credential_value = _unit_argument(
        "service credential directory", config.credential_dir
    )
    backup_value = (
        _unit_argument("service backup parent directory", config.backup_parent_dir)
        if config.backup_parent_dir is not None
        else ""
    )
    executable_value = _unit_argument("service executable", executable)
    return "\n".join(
        (
            "[Unit]",
            f"Description=skill2workflow self-hosted service ({unit_name})",
            "Documentation=https://github.com/pearjelly/skill2workflow/tree/main/docs",
            "After=network-online.target",
            "Wants=network-online.target",
            "StartLimitIntervalSec=60",
            "StartLimitBurst=3",
            "",
            "[Service]",
            "Type=simple",
            f"User={service_user}",
            f"Group={service_group}",
            "UMask=0077",
            "WorkingDirectory=/",
            f"ExecStart={executable_value} service --config {config_value}",
            "StandardOutput=journal",
            "StandardError=journal",
            "Restart=on-failure",
            "RestartSec=5s",
            "TimeoutStartSec=60s",
            "TimeoutStopSec=60s",
            "KillSignal=SIGTERM",
            "SendSIGKILL=no",
            "NoNewPrivileges=yes",
            "PrivateTmp=yes",
            "PrivateDevices=yes",
            "ProtectSystem=strict",
            "ProtectHome=read-only",
            "ProtectControlGroups=yes",
            "ProtectKernelTunables=yes",
            "ProtectKernelModules=yes",
            "ProtectKernelLogs=yes",
            "ProtectClock=yes",
            "ProtectHostname=yes",
            "LockPersonality=yes",
            "MemoryDenyWriteExecute=yes",
            "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6",
            "RestrictNamespaces=yes",
            "RestrictRealtime=yes",
            "SystemCallArchitectures=native",
            "CapabilityBoundingSet=",
            "AmbientCapabilities=",
            f"ReadWritePaths={state_value}",
            f"ReadOnlyPaths={config_value} {token_value} {credential_value}"
            + (f" {backup_value}" if backup_value else ""),
            "",
            "[Install]",
            "WantedBy=multi-user.target",
            "",
        )
    )


def _write_new_unit(path: Path, content: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o644)
    except FileExistsError as error:
        raise ValueError("systemd unit output must not already exist") from error
    except OSError as error:
        raise ValueError("systemd unit output could not be created") from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            os.fchmod(handle.fileno(), 0o644)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
