from __future__ import annotations

import json
import os
import secrets
import stat
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, Tuple
from zoneinfo import ZoneInfo

from .connectors import ConnectorRuntime, ExternalConnector
from .control_plane import LocalControlPlane
from .credentials import StaticCredentialProvider
from .external_connectors import load_external_connector
from .lark_task_pilot import build_lark_task_pilot_workflow


PILOT_SCHEMA_VERSION = "controlled-lark-pilot-0.1.0"
WORKFLOW_ID = "workflow_controlled_lark_pilot"
WORKFLOW_VERSION = "0.1.0"
SCENARIO_ID = "sales_renewal_risk_followup"
PILOT_TIMEZONE = "Asia/Shanghai"
REQUIRED_CHARTER_KEYS = {
    "schema_version",
    "scenario_id",
    "workflow_id",
    "workflow_version",
    "support_model",
    "timezone",
    "starts_on",
    "expires_on",
    "team_consent_confirmed",
    "assignee_consent_confirmed",
    "commercial_engagement_confirmed",
    "required_approved_runs",
    "required_distinct_days",
    "required_distinct_cases",
}
REQUIRED_CASE_KEYS = {
    "pilot_case_id",
    "account_name",
    "renewal_risk",
    "owner_open_id",
    "due_at",
}


def start_pilot_run(
    repo_root: Path,
    work_dir: Path,
    input_path: Path,
    now: datetime = None,
    transport=None,
) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    _require_outside_repository(repo_root, work_dir, "pilot work directory")
    load_pilot_charter(work_dir, now=now)
    pilot_input = load_private_case(repo_root, input_path)
    control = _pilot_control_plane(
        repo_root,
        work_dir,
        credential_provider=StaticCredentialProvider({}),
        transport=transport,
    )
    workflow = build_lark_task_pilot_workflow(
        mode="live",
        workflow_id=WORKFLOW_ID,
        workflow_version=WORKFLOW_VERSION,
        workflow_name="controlled-lark-task-sales-renewal-pilot",
    )
    control.publish_workflow(workflow)
    response = control.trigger_workflow(
        {
            "workflow_id": WORKFLOW_ID,
            "version": WORKFLOW_VERSION,
            "source": "controlled-live-pilot",
            "idempotency_key": "",
            "input": pilot_input,
        }
    )
    run = control.get_run(str(response["run_id"]))
    if (
        run.get("status") != "waiting"
        or run.get("current_node") != "review_renewal_risk"
    ):
        raise ValueError("controlled pilot run did not stop at the expected human gate")
    return {
        "run_id": str(response["run_id"]),
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "run_status": "waiting",
        "current_node": "review_renewal_risk",
        "input_keys": sorted(pilot_input),
    }


def _pilot_control_plane(
    repo_root: Path,
    work_dir: Path,
    credential_provider,
    transport=None,
) -> LocalControlPlane:
    connector = load_external_connector(
        repo_root / "examples" / "connectors" / "lark_task_connector.py"
    )
    if transport is not None:
        original = connector

        def execute_with_transport(binding, credential_provider=None, context=None):
            return original.executor(
                binding,
                credential_provider=credential_provider,
                context=context,
                transport=transport,
            )

        connector = ExternalConnector(
            manifest=original.manifest,
            executor=execute_with_transport,
        )
    runtime = ConnectorRuntime([connector])
    return LocalControlPlane(
        work_dir / "state",
        storage="sqlite",
        credential_provider=credential_provider,
        connector_runtime=runtime,
    )


def initialize_pilot(
    repo_root: Path,
    work_dir: Path,
    charter: Dict[str, object],
    now: datetime = None,
) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(os.path.abspath(os.fspath(work_dir)))
    _require_outside_repository(
        repo_root,
        work_dir.resolve(),
        "pilot work directory",
    )
    normalized = _validate_charter(charter, now=now)

    private_dir = work_dir / "private"
    state_dir = work_dir / "state"
    evidence_dir = work_dir / "evidence"
    charter_path = private_dir / "charter.json"
    _require_directory_or_missing(work_dir)
    _require_directory_or_missing(private_dir)
    _require_directory_or_missing(state_dir)
    _require_directory_or_missing(evidence_dir)
    _require_regular_file_or_missing(charter_path)

    _mkdir_private(work_dir)
    _mkdir_private(private_dir)
    _mkdir_private(state_dir)
    _mkdir_private(evidence_dir)
    _write_private_json(charter_path, normalized)
    return {
        "status": "initialized",
        "scenario_id": SCENARIO_ID,
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "commercial_engagement_confirmed": True,
    }


def load_pilot_charter(work_dir: Path, now: datetime = None) -> Dict[str, object]:
    path = Path(work_dir).resolve() / "private" / "charter.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _validate_charter(payload, now=now)


def load_private_case(repo_root: Path, input_path: Path) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    input_path = Path(input_path).resolve()
    _require_outside_repository(repo_root, input_path, "private case input")
    _require_owner_only(input_path)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != REQUIRED_CASE_KEYS:
        raise ValueError("private case input must contain only the approved fields")
    normalized = {
        key: str(payload.get(key) or "").strip() for key in sorted(REQUIRED_CASE_KEYS)
    }
    if not all(normalized.values()):
        raise ValueError("private case input fields must be non-empty strings")
    if any(
        token in normalized["pilot_case_id"].lower()
        for token in ("account", "customer", "@", " ")
    ):
        raise ValueError("pilot_case_id must be an opaque identifier")
    return normalized


def _validate_charter(charter: object, now: datetime = None) -> Dict[str, object]:
    if not isinstance(charter, dict):
        raise ValueError("pilot charter must be a JSON object")
    if set(charter) != REQUIRED_CHARTER_KEYS:
        raise ValueError("pilot charter must contain only the approved fields")
    normalized = json.loads(json.dumps(charter, ensure_ascii=False))
    required_exact = {
        "schema_version": PILOT_SCHEMA_VERSION,
        "scenario_id": SCENARIO_ID,
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "support_model": "assisted",
        "timezone": PILOT_TIMEZONE,
        "required_approved_runs": 5,
        "required_distinct_days": 5,
        "required_distinct_cases": 2,
    }
    for key, expected in required_exact.items():
        if normalized.get(key) != expected:
            raise ValueError(f"pilot charter {key} must be {expected}")
    for key in (
        "team_consent_confirmed",
        "assignee_consent_confirmed",
        "commercial_engagement_confirmed",
    ):
        if normalized.get(key) is not True:
            raise ValueError(f"pilot charter {key} must be true")
    starts_on = date.fromisoformat(str(normalized.get("starts_on", "")))
    expires_on = date.fromisoformat(str(normalized.get("expires_on", "")))
    current = (now or datetime.now(timezone.utc)).astimezone(
        ZoneInfo(PILOT_TIMEZONE)
    ).date()
    if current < starts_on:
        raise ValueError("pilot charter has not started")
    if current > expires_on:
        raise ValueError("pilot charter expired")
    return normalized


def _require_outside_repository(repo_root: Path, path: Path, label: str) -> None:
    if path == repo_root or repo_root in path.parents:
        raise ValueError(f"{label} must be outside the repository")


def _mkdir_private(path: Path) -> None:
    _require_directory_or_missing(path)
    try:
        path.mkdir(parents=True, mode=0o700)
    except FileExistsError:
        pass
    _require_directory_or_missing(path)
    _chmod_private_directory(path)


def _write_private_json(path: Path, value: object) -> None:
    _require_regular_file_or_missing(path)
    serialized = json.dumps(value, ensure_ascii=False, indent=2)
    temp_path, file_descriptor = _open_private_temp(path)
    try:
        handle = os.fdopen(file_descriptor, "w", encoding="utf-8")
        file_descriptor = None
        with handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        _require_regular_file_or_missing(path)
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def _require_directory_or_missing(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"pilot workspace node {path.name} must not be a symbolic link")
    if path.exists() and not path.is_dir():
        raise ValueError(f"pilot workspace node {path.name} must be a directory")


def _require_regular_file_or_missing(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"pilot workspace node {path.name} must not be a symbolic link")
    if path.exists() and not path.is_file():
        raise ValueError(f"pilot workspace node {path.name} must be a regular file")


def _chmod_private_directory(path: Path) -> None:
    if os.name != "posix" or not hasattr(os, "O_DIRECTORY"):
        os.chmod(path, 0o700)
        return
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    file_descriptor = os.open(path, flags)
    try:
        if not stat.S_ISDIR(os.fstat(file_descriptor).st_mode):
            raise ValueError(f"pilot workspace node {path.name} must be a directory")
        os.fchmod(file_descriptor, 0o700)
    finally:
        os.close(file_descriptor)


def _open_private_temp(path: Path) -> Tuple[Path, int]:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    for _attempt in range(16):
        temp_path = path.parent / f".{path.name}.{secrets.token_hex(8)}.tmp"
        try:
            file_descriptor = os.open(temp_path, flags, 0o600)
        except FileExistsError:
            continue
        try:
            if os.name == "posix":
                os.fchmod(file_descriptor, 0o600)
        except BaseException:
            os.close(file_descriptor)
            temp_path.unlink()
            raise
        return temp_path, file_descriptor
    raise FileExistsError("could not allocate a private charter temporary file")


def _require_owner_only(path: Path) -> None:
    if os.name == "posix" and path.stat().st_mode & 0o077:
        raise ValueError("private case input must use owner-only permissions")
