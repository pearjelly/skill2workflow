"""Read-only operational readiness diagnostics for the self-hosted service."""

from __future__ import annotations

import socket
import sqlite3
from pathlib import Path
from typing import Dict, List

from .credentials import DirectoryCredentialProvider
from .service import (
    FileBearerTokenAuthenticator,
    ServiceConfig,
    _require_private_directory,
    load_service_config,
    validate_service_state_environment,
)
from .state_layout import EMPTY_STATE_LAYOUT


SERVICE_DOCTOR_RESULT_SCHEMA_VERSION = (
    "skill2workflow-service-doctor-result-0.1.0"
)
_CHECK_IDS = ("config", "auth", "credentials", "state", "bind")


def diagnose_service(config_path: Path) -> Dict[str, object]:
    """Return a fixed, secret-free startup report without mutating the workspace."""

    try:
        config = load_service_config(config_path)
    except (OSError, ValueError):
        return _result(
            [_check("config", "failed", "invalid")]
            + [_check(check_id, "skipped", "blocked_by_config") for check_id in _CHECK_IDS[1:]]
        )

    checks = [_check("config", "passed", "valid")]
    checks.append(_auth_check(config))
    checks.append(_credential_check(config))
    checks.append(_state_check(config))
    checks.append(_bind_check(config))
    return _result(checks)


def _auth_check(config: ServiceConfig) -> Dict[str, str]:
    try:
        FileBearerTokenAuthenticator(config.auth_token_file)
        return _check("auth", "passed", "ready")
    except (OSError, ValueError) as error:
        return _check("auth", "failed", _failure_code(error))


def _credential_check(config: ServiceConfig) -> Dict[str, str]:
    try:
        _require_private_directory(
            config.credential_dir,
            "service credential directory",
        )
        DirectoryCredentialProvider(config.credential_dir)
        return _check("credentials", "passed", "ready")
    except (OSError, ValueError) as error:
        return _check("credentials", "failed", _failure_code(error))


def _state_check(config: ServiceConfig) -> Dict[str, str]:
    try:
        layout = validate_service_state_environment(config)
        code = "initializable" if layout == EMPTY_STATE_LAYOUT else "ready"
        return _check("state", "passed", code)
    except (OSError, sqlite3.Error, ValueError) as error:
        return _check("state", "failed", _failure_code(error, default="invalid"))


def _bind_check(config: ServiceConfig) -> Dict[str, str]:
    family = socket.AF_INET6 if config.host == "::1" else socket.AF_INET
    listener = None
    try:
        listener = socket.socket(family, socket.SOCK_STREAM)
        listener.bind((config.host, config.port))
    except OSError:
        return _check("bind", "failed", "address_unavailable")
    finally:
        if listener is not None:
            try:
                listener.close()
            except OSError:
                pass
    return _check(
        "bind",
        "passed",
        "ephemeral_available" if config.port == 0 else "address_available",
    )


def _failure_code(error: Exception, default: str = "unavailable") -> str:
    message = str(error)
    if "group or others" in message:
        return "unsafe_permissions"
    if "non-symlink" in message or "symbolic link" in message:
        return "unsafe_path"
    if "size limit" in message:
        return "oversized"
    return default


def _check(check_id: str, status: str, code: str) -> Dict[str, str]:
    return {"id": check_id, "status": status, "code": code}


def _result(checks: List[Dict[str, str]]) -> Dict[str, object]:
    ready = all(check["status"] == "passed" for check in checks)
    return {
        "schema_version": SERVICE_DOCTOR_RESULT_SCHEMA_VERSION,
        "status": "ready" if ready else "not_ready",
        "checks": checks,
    }
