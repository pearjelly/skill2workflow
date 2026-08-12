"""Secure first-run workspace initialization for the self-hosted service."""

from __future__ import annotations

import json
import os
import secrets
import shutil
from pathlib import Path
from typing import Callable, Dict, Optional

from .service import SERVICE_SCHEMA_VERSION


SERVICE_BOOTSTRAP_RESULT_SCHEMA_VERSION = (
    "skill2workflow-service-bootstrap-result-0.1.0"
)
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def initialize_service_workspace(
    root: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
    token_factory: Optional[Callable[[], str]] = None,
) -> Dict[str, object]:
    """Create one complete, non-overwriting, owner-only service workspace."""

    requested_root = Path(root)
    if not requested_root.is_absolute():
        raise ValueError("service bootstrap root must be an absolute path")
    if host not in _LOOPBACK_HOSTS:
        raise ValueError("service bootstrap host must be an explicit loopback address")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("service bootstrap port must be an integer from 0 through 65535")
    if requested_root.exists() or requested_root.is_symlink():
        raise ValueError("service bootstrap root must not already exist")

    try:
        parent = requested_root.parent.resolve(strict=True)
    except OSError as error:
        raise ValueError("service bootstrap root parent must already exist") from error
    if not parent.is_dir():
        raise ValueError("service bootstrap root parent must be a directory")
    workspace = parent / requested_root.name
    if workspace.exists() or workspace.is_symlink():
        raise ValueError("service bootstrap root must not already exist")

    token = (token_factory or _new_ingress_token)()
    _validate_token(token)

    created = False
    try:
        workspace.mkdir(mode=0o700)
        created = True
        _owner_only_directory(workspace)
        config_dir = _private_directory(workspace / "config")
        state_dir = _private_directory(workspace / "state")
        secrets_dir = _private_directory(workspace / "secrets")
        credential_dir = _private_directory(secrets_dir / "connectors")
        token_file = secrets_dir / "ingress-token"
        _write_private_file(token_file, token + "\n")

        config_file = config_dir / "service.json"
        config = {
            "schema_version": SERVICE_SCHEMA_VERSION,
            "service": {"host": host, "port": port},
            "runtime": {"state_dir": str(state_dir), "storage": "sqlite"},
            "auth": {
                "provider": "bearer_token_file",
                "token_file": str(token_file),
            },
            "credentials": {
                "provider": "directory",
                "directory": str(credential_dir),
            },
        }
        temporary_config = config_dir / f".service.json.tmp-{secrets.token_hex(8)}"
        _write_private_file(
            temporary_config,
            json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        )
        os.replace(temporary_config, config_file)
        os.chmod(config_file, 0o600)
    except Exception:
        if created:
            shutil.rmtree(workspace, ignore_errors=True)
        raise

    return {
        "schema_version": SERVICE_BOOTSTRAP_RESULT_SCHEMA_VERSION,
        "status": "initialized",
        "root": str(workspace),
        "config_file": str(config_file),
        "state_dir": str(state_dir),
        "token_file": str(token_file),
        "credential_directory": str(credential_dir),
    }


def _new_ingress_token() -> str:
    return secrets.token_urlsafe(32)


def _validate_token(token: object) -> None:
    if not isinstance(token, str):
        raise ValueError("service bootstrap token factory must return a string")
    if len(token.encode("utf-8")) < 32 or "\r" in token or "\n" in token:
        raise ValueError(
            "service bootstrap token must be one line with at least 32 UTF-8 bytes"
        )


def _private_directory(path: Path) -> Path:
    path.mkdir(mode=0o700)
    _owner_only_directory(path)
    return path.resolve()


def _owner_only_directory(path: Path) -> None:
    os.chmod(path, 0o700)


def _write_private_file(path: Path, value: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    os.chmod(path, 0o600)
