"""Deterministic local schedule helpers for published workflow triggers."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .control_plane import LocalControlPlane


SCHEDULE_SCHEMA_VERSION = "skill2workflow-schedule-0.1.0"

Schedule = Dict[str, object]
ScheduleRunResult = Dict[str, object]


class LocalScheduleStore:
    """Persist local schedule definitions as inspectable JSON documents."""

    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.schedules_dir = self.state_dir / "schedules"
        self.schedules_dir.mkdir(parents=True, exist_ok=True)

    def save(self, definition: object) -> Schedule:
        schedule = normalize_schedule_definition(definition)
        schedule_id = str(schedule["schedule"]["id"])
        path = self._schedule_path(schedule_id)
        path.write_text(json.dumps(schedule, ensure_ascii=False, indent=2), encoding="utf-8")
        return schedule

    def get_schedule(self, schedule_id: str) -> Schedule:
        path = self._schedule_path(schedule_id)
        if not path.exists():
            raise ValueError(f"schedule not found: {schedule_id}")
        return normalize_schedule_definition(json.loads(path.read_text(encoding="utf-8")))

    def list_schedules(self) -> List[Schedule]:
        schedules = []
        for path in sorted(self.schedules_dir.glob("*.json")):
            schedules.append(normalize_schedule_definition(json.loads(path.read_text(encoding="utf-8"))))
        return schedules

    def _schedule_path(self, schedule_id: str) -> Path:
        return self.schedules_dir / f"{_safe_schedule_id(schedule_id)}.json"


class LocalScheduleRunner:
    """Execute due local schedules through the existing trigger boundary."""

    def __init__(self, state_dir: Path, storage: str = "json", credential_provider=None):
        self.state_dir = Path(state_dir)
        self.store = LocalScheduleStore(self.state_dir)
        self.control_plane = LocalControlPlane(
            self.state_dir,
            storage=storage,
            credential_provider=credential_provider,
        )

    def add_schedule(self, definition: object) -> Schedule:
        return self.store.save(definition)

    def get_schedule(self, schedule_id: str) -> Schedule:
        return self.store.get_schedule(schedule_id)

    def list_schedules(self) -> List[Schedule]:
        return self.store.list_schedules()

    def list_due_schedules(self, now: str) -> List[Schedule]:
        now_at = _normalize_timestamp(now, "now")
        return [schedule for schedule in self.list_schedules() if _is_due(schedule, now_at)]

    def run_due(self, now: str) -> ScheduleRunResult:
        now_at = _normalize_timestamp(now, "now")
        runs = []
        for schedule in self.list_due_schedules(now_at):
            trigger = _trigger_request(schedule)
            response = self.control_plane.trigger_workflow(trigger)
            updated = copy.deepcopy(schedule)
            updated_schedule = updated["schedule"]
            updated_schedule["status"] = "completed"
            updated_schedule["last_run_at"] = now_at
            updated_schedule["last_run_id"] = response["run_id"]
            updated_schedule["last_trigger_id"] = response["trigger_id"]
            self.store.save(updated)

            run = dict(response)
            run["schedule_id"] = str(schedule["schedule"]["id"])
            runs.append(run)

        return {
            "now": now_at,
            "count": len(runs),
            "runs": runs,
        }


def normalize_schedule_definition(definition: object) -> Schedule:
    """Validate and normalize a one-shot local schedule document."""

    if not isinstance(definition, dict):
        raise ValueError("schedule definition must be a JSON object")

    schema_version = _optional_text(definition, "schema_version") or SCHEDULE_SCHEMA_VERSION
    if schema_version != SCHEDULE_SCHEMA_VERSION:
        raise ValueError(f"unsupported schedule schema_version: {schema_version}")

    schedule_section = definition.get("schedule")
    if not isinstance(schedule_section, dict):
        raise ValueError("schedule must be a JSON object")

    schedule_id = _required_text(schedule_section, "id", "schedule.id")
    _safe_schedule_id(schedule_id)
    workflow_id = _required_text(schedule_section, "workflow_id", "schedule.workflow_id")
    version = _required_text(schedule_section, "version", "schedule.version")
    run_at = _normalize_timestamp(_required_text(schedule_section, "run_at", "schedule.run_at"), "schedule.run_at")
    enabled = schedule_section.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError("schedule.enabled must be a boolean")
    status = _optional_text(schedule_section, "status") or ("pending" if enabled else "disabled")
    if status not in {"pending", "completed", "disabled"}:
        raise ValueError("schedule.status must be pending, completed, or disabled")

    trigger_section = definition.get("trigger", {})
    if trigger_section is None:
        trigger_section = {}
    if not isinstance(trigger_section, dict):
        raise ValueError("schedule trigger must be a JSON object")
    trigger_input = trigger_section.get("input", {})
    if trigger_input is None:
        trigger_input = {}
    if not isinstance(trigger_input, dict):
        raise ValueError("schedule trigger input must be a JSON object")
    normalized_input = _json_object_copy(trigger_input)

    return {
        "schema_version": schema_version,
        "schedule": {
            "id": schedule_id,
            "workflow_id": workflow_id,
            "version": version,
            "run_at": run_at,
            "enabled": enabled,
            "status": status,
            "last_run_at": _optional_text(schedule_section, "last_run_at"),
            "last_run_id": _optional_text(schedule_section, "last_run_id"),
            "last_trigger_id": _optional_text(schedule_section, "last_trigger_id"),
        },
        "trigger": {
            "source": _schedule_source(schedule_id, _optional_text(trigger_section, "source")),
            "idempotency_key": _optional_text(trigger_section, "idempotency_key")
            or f"{schedule_id}:{run_at}",
            "input": normalized_input,
        },
    }


def _trigger_request(schedule: Schedule) -> Dict[str, object]:
    schedule_meta = schedule["schedule"]
    trigger = schedule["trigger"]
    return {
        "workflow_id": str(schedule_meta["workflow_id"]),
        "version": str(schedule_meta["version"]),
        "source": str(trigger["source"]),
        "idempotency_key": str(trigger["idempotency_key"]),
        "input": copy.deepcopy(trigger["input"]),
    }


def _is_due(schedule: Schedule, now_at: str) -> bool:
    schedule_meta = schedule["schedule"]
    if not bool(schedule_meta.get("enabled", True)):
        return False
    if str(schedule_meta.get("status", "")) == "completed":
        return False
    if str(schedule_meta.get("last_run_id", "")):
        return False
    return _parse_timestamp(str(schedule_meta["run_at"])) <= _parse_timestamp(now_at)


def _normalize_timestamp(value: str, field: str) -> str:
    try:
        parsed = _parse_timestamp(value)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO-8601 timestamp: {error}")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_timestamp(value: str) -> datetime:
    if str(value).strip() == "":
        raise ValueError("empty timestamp")
    normalized = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _schedule_source(schedule_id: str, source: str) -> str:
    base = f"local-schedule:{schedule_id}"
    if source == base or source.startswith(f"{base}:"):
        return source
    return base if not source else f"{base}:{source}"


def _required_text(mapping: Dict[str, object], key: str, label: str) -> str:
    value = mapping.get(key)
    if value is None or str(value).strip() == "":
        raise ValueError(f"{label} is required")
    return str(value)


def _optional_text(mapping: Dict[str, object], key: str) -> str:
    value = mapping.get(key, "")
    if value is None:
        return ""
    return str(value)


def _json_object_copy(value: Dict[str, object]) -> Dict[str, object]:
    try:
        copied = json.loads(json.dumps(value, ensure_ascii=False))
    except (TypeError, ValueError) as error:
        raise ValueError(f"schedule trigger input must be JSON serializable: {error}")
    if not isinstance(copied, dict):
        raise ValueError("schedule trigger input must be a JSON object")
    return copied


def _safe_schedule_id(schedule_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in str(schedule_id))
    if not safe or safe != str(schedule_id):
        raise ValueError("schedule.id may only contain letters, numbers, '-', '_', and '.'")
    return safe
