from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict
from zoneinfo import ZoneInfo


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


def initialize_pilot(
    repo_root: Path,
    work_dir: Path,
    charter: Dict[str, object],
    now: datetime = None,
) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    _require_outside_repository(repo_root, work_dir, "pilot work directory")
    normalized = _validate_charter(charter, now=now)

    _mkdir_private(work_dir)
    _mkdir_private(work_dir / "private")
    _mkdir_private(work_dir / "state")
    _mkdir_private(work_dir / "evidence")
    _write_private_json(work_dir / "private" / "charter.json", normalized)
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
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)


def _write_private_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.chmod(path, 0o600)


def _require_owner_only(path: Path) -> None:
    if os.name == "posix" and path.stat().st_mode & 0o077:
        raise ValueError("private case input must use owner-only permissions")
