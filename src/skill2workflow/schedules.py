"""Deterministic local schedule helpers for published workflow triggers."""

from __future__ import annotations

import copy
import heapq
import hashlib
import json
import secrets
import sqlite3
import time
from collections import deque
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .control_plane import LocalControlPlane
from .state_layout import ensure_current_state_layout
from .triggers import normalize_trigger_input


SCHEDULE_SCHEMA_VERSION = "skill2workflow-schedule-0.1.0"
RECURRING_SCHEDULE_SCHEMA_VERSION = "skill2workflow-schedule-0.2.0"
LOCAL_SCHEDULE_LIST_SCHEMA_VERSION = "skill2workflow-local-schedule-list-0.1.0"
LOCAL_SCHEDULE_DISPATCH_LIST_SCHEMA_VERSION = "skill2workflow-local-schedule-dispatch-list-0.1.0"
MAX_LOCAL_SCHEDULE_LIST_ITEMS = 1000
MAX_LOCAL_SCHEDULE_DISPATCH_LIST_ITEMS = 1000
MAX_SCHEDULE_RUN_DUE_ITEMS = 100

Schedule = Dict[str, object]
ScheduleRunResult = Dict[str, object]


class SchedulerLeaseError(ValueError):
    """Raised when dispatch is attempted without the persisted scheduler lease."""


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

    def list_compact_bounded(self, max_items: int) -> Dict[str, object]:
        """Stream one-shot schedules into a bounded value-free projection."""

        _validate_local_window(max_items, "schedule list limit")
        selected = []
        total = 0
        status_counts = _empty_schedule_status_counts()
        for path in sorted(self.schedules_dir.glob("*.json")):
            schedule = normalize_schedule_definition(
                json.loads(path.read_text(encoding="utf-8"))
            )
            total += 1
            compact, sort_key = _compact_schedule(schedule, "one_shot")
            status_counts[_schedule_status_bucket(compact["status"])] += 1
            item = (sort_key, compact["schedule_id"], "one_shot", compact)
            if len(selected) < max_items:
                heapq.heappush(selected, item)
            elif item[:3] > selected[0][:3]:
                heapq.heapreplace(selected, item)
        return {
            "items": [item[3] for item in sorted(selected, key=lambda value: value[:3])],
            "total": total,
            "status_counts": status_counts,
        }

    def _schedule_path(self, schedule_id: str) -> Path:
        return self.schedules_dir / f"{_safe_schedule_id(schedule_id)}.json"


class LocalScheduleRunner:
    """Execute due local schedules through the existing trigger boundary."""

    def __init__(self, state_dir: Path, storage: str = "json", credential_provider=None):
        self.state_dir = Path(state_dir)
        self.storage = storage
        self.store = LocalScheduleStore(self.state_dir)
        self.recurring_store = RecurringScheduleStore(self.state_dir) if storage == "sqlite" else None
        self.credential_provider = credential_provider
        self.control_plane = LocalControlPlane(
            self.state_dir,
            storage=storage,
            credential_provider=credential_provider,
        )

    def add_schedule(self, definition: object) -> Schedule:
        if isinstance(definition, dict) and definition.get("schema_version") == RECURRING_SCHEDULE_SCHEMA_VERSION:
            if self.recurring_store is None:
                raise ValueError("recurring schedules requires sqlite storage")
            schedule_id = str(definition.get("schedule", {}).get("id", ""))
            if schedule_id:
                try:
                    self.store.get_schedule(schedule_id)
                except ValueError:
                    pass
                else:
                    raise ValueError(f"schedule already exists: {schedule_id}")
            return self.recurring_store.add(definition)
        if self.recurring_store is not None and isinstance(definition, dict):
            schedule_id = str(definition.get("schedule", {}).get("id", ""))
            if schedule_id:
                try:
                    self.recurring_store.get(schedule_id)
                except ValueError:
                    pass
                else:
                    raise ValueError(f"schedule already exists: {schedule_id}")
        return self.store.save(definition)

    def get_schedule(self, schedule_id: str) -> Schedule:
        try:
            return self.store.get_schedule(schedule_id)
        except ValueError:
            if self.recurring_store is None:
                raise
            return self.recurring_store.get(schedule_id)

    def list_schedules(self) -> List[Schedule]:
        schedules = self.store.list_schedules()
        if self.recurring_store is not None:
            schedules.extend(self.recurring_store.list())
        return sorted(schedules, key=lambda item: str(item["schedule"]["id"]))

    def list_schedules_bounded(self, max_items: int) -> Dict[str, object]:
        """Return a bounded local schedule inventory without trigger inputs."""

        _validate_local_window(max_items, "schedule list limit")
        inventories = [self.store.list_compact_bounded(max_items)]
        if self.recurring_store is not None:
            inventories.append(self.recurring_store.list_compact_bounded(max_items))
        items = [item for inventory in inventories for item in inventory["items"]]
        items.sort(key=lambda item: (str(item["last_activity_at"]), str(item["schedule_id"]), str(item["kind"])))
        selected = items[-max_items:]
        total = sum(int(inventory["total"]) for inventory in inventories)
        status_counts = _empty_schedule_status_counts()
        for inventory in inventories:
            for status, count in inventory["status_counts"].items():
                status_counts[status] += int(count)
        return {
            "schema_version": LOCAL_SCHEDULE_LIST_SCHEMA_VERSION,
            "summary": {"total": total, "status_counts": status_counts},
            "schedules": selected,
            "window": {
                "max_items": max_items,
                "total": total,
                "returned": len(selected),
                "truncated": len(selected) < total,
            },
        }

    def list_dispatches(self, schedule_id: str = "") -> List[Dict[str, object]]:
        if self.recurring_store is None:
            raise ValueError("recurring dispatch records requires sqlite storage")
        return self.recurring_store.list_dispatches(schedule_id=schedule_id)

    def list_dispatches_bounded(
        self, max_items: int, schedule_id: str = ""
    ) -> Dict[str, object]:
        """Return a bounded local dispatch inventory with no trigger payloads."""

        _validate_local_window(max_items, "schedule dispatch list limit")
        if self.recurring_store is None:
            raise ValueError("recurring dispatch records requires sqlite storage")
        bounded = self.recurring_store.list_dispatches_bounded(
            max_items, schedule_id=schedule_id
        )
        dispatches = [_compact_dispatch(record) for record in bounded["items"]]
        return {
            "schema_version": LOCAL_SCHEDULE_DISPATCH_LIST_SCHEMA_VERSION,
            "schedule_id": str(schedule_id),
            "summary": {
                "total": int(bounded["total"]),
                "status_counts": dict(bounded["status_counts"]),
            },
            "dispatches": dispatches,
            "window": {
                "max_items": max_items,
                "total": int(bounded["total"]),
                "returned": len(dispatches),
                "truncated": len(dispatches) < int(bounded["total"]),
            },
        }

    def set_recurring_enabled(self, schedule_id: str, enabled: bool) -> Schedule:
        if self.recurring_store is None:
            raise ValueError("recurring schedules requires sqlite storage")
        return self.recurring_store.set_enabled(schedule_id, enabled)

    def list_due_schedules(self, now: str, max_items: int = None) -> List[Schedule]:
        now_at = _normalize_timestamp(now, "now")
        if max_items is not None:
            _validate_dispatch_limit(max_items)
        due = []
        for path in sorted(self.store.schedules_dir.glob("*.json")):
            schedule = normalize_schedule_definition(
                json.loads(path.read_text(encoding="utf-8"))
            )
            if not _is_due(schedule, now_at):
                continue
            due.append(schedule)
            if max_items is not None and len(due) >= max_items:
                break
        return due

    def run_due(
        self,
        now: str,
        lease_now_epoch: float = None,
        max_items: int = None,
    ) -> ScheduleRunResult:
        now_at = _normalize_timestamp(now, "now")
        if max_items is not None:
            _validate_dispatch_limit(max_items)
        dispatcher = None
        lease_now = time.time() if lease_now_epoch is None else float(lease_now_epoch)
        if self.recurring_store is not None:
            dispatcher = RecurringScheduleDispatcher(
                self.state_dir,
                credential_provider=self.credential_provider,
                lease_seconds=60,
            )
            if not dispatcher.try_acquire(now_epoch=lease_now):
                raise SchedulerLeaseError("scheduler lease is held by another dispatcher")
            dispatcher.recover_stale_claims(now_epoch=lease_now)
        runs = []
        skipped = 0
        failures = 0
        processed = 0
        try:
            for schedule in self.list_due_schedules(now_at, max_items=max_items):
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
                processed += 1

            remaining = None if max_items is None else max_items - processed
            if dispatcher is not None and (remaining is None or remaining > 0):
                recurring_result = dispatcher.dispatch_due(
                    now_at,
                    now_epoch=time.time() if lease_now_epoch is None else lease_now,
                    max_items=remaining,
                )
                runs.extend(recurring_result["runs"])
                skipped = int(recurring_result["skipped"])
                failures = int(recurring_result["failures"])
                processed += int(recurring_result.get("processed", len(recurring_result["runs"])))
        finally:
            if dispatcher is not None:
                dispatcher.release()

        result = {
            "now": now_at,
            "count": len(runs),
            "skipped": skipped,
            "failures": failures,
            "runs": runs,
        }
        if max_items is not None:
            result["window"] = {
                "max_items": max_items,
                "processed": processed,
                "budget_exhausted": processed >= max_items,
            }
        return result


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
    normalized_input = normalize_trigger_input(trigger_input, "schedule trigger input")

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


def _validate_local_window(value: object, label: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= MAX_LOCAL_SCHEDULE_LIST_ITEMS
    ):
        raise ValueError(
            f"{label} must be an integer from 1 through {MAX_LOCAL_SCHEDULE_LIST_ITEMS}"
        )


def _validate_dispatch_limit(value: object) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= MAX_SCHEDULE_RUN_DUE_ITEMS
    ):
        raise ValueError(
            "schedule run limit must be an integer from 1 through "
            f"{MAX_SCHEDULE_RUN_DUE_ITEMS}"
        )


def _empty_schedule_status_counts() -> Dict[str, int]:
    return {
        "active": 0,
        "pending": 0,
        "completed": 0,
        "disabled": 0,
        "other": 0,
    }


def _schedule_status_bucket(status: object) -> str:
    value = str(status)
    return value if value in {"active", "pending", "completed", "disabled"} else "other"


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, number)


def _compact_schedule(schedule: Schedule, kind: str):
    meta = schedule.get("schedule")
    if not isinstance(meta, dict):
        raise ValueError("schedule metadata must be an object")
    last_run_at = _optional_text(meta, "last_run_at")
    last_scheduled_for = _optional_text(meta, "last_scheduled_for")
    next_run_at = _optional_text(meta, "next_run_at")
    run_at = _optional_text(meta, "run_at")
    starts_at = _optional_text(meta, "starts_at")
    last_activity_at = (
        last_run_at
        or last_scheduled_for
        or next_run_at
        or run_at
        or starts_at
    )
    compact = {
        "kind": kind,
        "schedule_id": _optional_text(meta, "id"),
        "workflow_id": _optional_text(meta, "workflow_id"),
        "workflow_version": _optional_text(meta, "version"),
        "status": _optional_text(meta, "status"),
        "enabled": bool(meta.get("enabled", False)),
        "run_at": run_at,
        "starts_at": starts_at,
        "next_run_at": next_run_at,
        "interval_seconds": _non_negative_int(meta.get("interval_seconds", 0)),
        "missed_run_policy": _optional_text(meta, "missed_run_policy"),
        "last_activity_at": last_activity_at,
        "last_run_at": last_run_at,
        "last_scheduled_for": last_scheduled_for,
        "last_run_id": _optional_text(meta, "last_run_id"),
        "last_trigger_id": _optional_text(meta, "last_trigger_id"),
    }
    return compact, (last_activity_at, compact["schedule_id"])


def _compact_recurring_summary(row) -> Dict[str, object]:
    """Convert one durable recurring summary row to the public compact shape."""

    return {
        "kind": "recurring",
        "schedule_id": str(row[0]),
        "workflow_id": str(row[1]),
        "workflow_version": str(row[2]),
        "status": str(row[3]),
        "enabled": bool(row[4]),
        "run_at": "",
        "starts_at": str(row[5]),
        "next_run_at": str(row[6]),
        "interval_seconds": max(0, int(row[7])),
        "missed_run_policy": str(row[8]),
        "last_activity_at": str(row[9]),
        "last_run_at": "",
        "last_scheduled_for": str(row[10]),
        "last_run_id": str(row[11]),
        "last_trigger_id": str(row[12]),
    }


def _compact_dispatch(record: object) -> Dict[str, object]:
    if not isinstance(record, dict):
        raise ValueError("schedule dispatch record must be an object")
    return {
        "dispatch_id": _optional_text(record, "dispatch_id"),
        "schedule_id": _optional_text(record, "schedule_id"),
        "scheduled_for": _optional_text(record, "scheduled_for"),
        "status": _optional_text(record, "status"),
        "coalesced_occurrences": _non_negative_int(
            record.get("coalesced_occurrences", 0)
        ),
        "run_id": _optional_text(record, "run_id"),
        "trigger_id": _optional_text(record, "trigger_id"),
        "error_type": _optional_text(record, "error_type"),
        "completed_at": _optional_text(record, "completed_at"),
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


def _safe_schedule_id(schedule_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in str(schedule_id))
    if not safe or safe != str(schedule_id):
        raise ValueError("schedule.id may only contain letters, numbers, '-', '_', and '.'")
    return safe


class RecurringScheduleStore:
    """Persist recurring definitions, dispatch records, and the global lease in SQLite."""

    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        ensure_current_state_layout(self.state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.state_dir / "scheduler.sqlite3"
        self._initialize()

    def add(self, definition: object) -> Schedule:
        normalized, created = self.add_with_result(definition)
        if not created:
            schedule_id = str(normalized["schedule"]["id"])
            raise ValueError(f"recurring schedule already exists: {schedule_id}")
        return normalized

    def add_with_result(self, definition: object) -> Tuple[Schedule, bool]:
        """Create one recurring schedule, or replay an identical definition.

        The transaction is serialized with dispatcher claims.  An identical
        retry is a no-op and returns the persisted definition; a changed
        definition for an existing id is rejected so a retry can never reset
        durable progress such as ``next_run_at``.
        """

        normalized = normalize_recurring_schedule_definition(definition)
        schedule_id = str(normalized["schedule"]["id"])
        with self._connection() as connection:
            connection.execute("begin immediate")
            retired = connection.execute(
                "select 1 from recurring_schedule_tombstones where schedule_id = ?",
                (schedule_id,),
            ).fetchone()
            if retired is not None:
                raise ValueError(f"recurring schedule id was retired: {schedule_id}")
            row = connection.execute(
                "select definition_json from recurring_schedules where schedule_id = ?",
                (schedule_id,),
            ).fetchone()
            if row is not None:
                existing = _load_recurring_definition(row[0])
                if _json_text(existing) == _json_text(normalized):
                    return existing, False
                raise ValueError(f"recurring schedule already exists: {schedule_id}")
            connection.execute(
                "insert into recurring_schedules (schedule_id, definition_json, updated_at) values (?, ?, ?)",
                (schedule_id, _json_text(normalized), _utc_now()),
            )
            _upsert_recurring_schedule_summary(connection, normalized)
        return normalized, True

    def update_with_result(
        self,
        schedule_id: str,
        definition: object,
        *,
        expected_next_run_at: str,
    ) -> Tuple[Schedule, bool]:
        """Update one definition without resetting durable dispatch progress.

        The caller must provide the ``next_run_at`` value it last observed.
        ``BEGIN IMMEDIATE`` serializes this compare-and-swap with scheduler
        claims, so a stale operator cannot silently move a schedule backwards
        or overwrite a concurrent update.  Runtime progress fields are always
        copied from the persisted row; only author-controlled definition and
        trigger fields are replaced.
        """

        normalized_id = str(schedule_id)
        _safe_schedule_id(normalized_id)
        if not isinstance(expected_next_run_at, str) or not expected_next_run_at:
            raise ValueError("expected_next_run_at must be an ISO-8601 timestamp")
        expected = _normalize_aware_timestamp(
            expected_next_run_at,
            "expected_next_run_at",
        )
        if not isinstance(definition, dict):
            raise ValueError("recurring schedule definition must be a JSON object")
        raw_schedule = definition.get("schedule")
        if not isinstance(raw_schedule, dict) or "enabled" not in raw_schedule:
            raise ValueError("recurring schedule update requires schedule.enabled")
        normalized = normalize_recurring_schedule_definition(definition)
        if str(normalized["schedule"]["id"]) != normalized_id:
            raise ValueError("recurring schedule definition id does not match path")
        with self._connection() as connection:
            connection.execute("begin immediate")
            row = connection.execute(
                "select definition_json from recurring_schedules where schedule_id = ?",
                (normalized_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"recurring schedule not found: {normalized_id}")
            existing = _load_recurring_definition(row[0])
            current_next_run_at = str(existing["schedule"]["next_run_at"])
            if current_next_run_at != expected:
                raise ValueError("recurring schedule update precondition failed")

            effective = copy.deepcopy(normalized)
            existing_schedule = existing["schedule"]
            effective_schedule = effective["schedule"]
            for state_key in (
                "next_run_at",
                "last_scheduled_for",
                "last_run_id",
                "last_trigger_id",
            ):
                effective_schedule[state_key] = existing_schedule[state_key]
            changed = _json_text(existing) != _json_text(effective)
            if changed:
                connection.execute(
                    "update recurring_schedules set definition_json = ?, updated_at = ? where schedule_id = ?",
                    (_json_text(effective), _utc_now(), normalized_id),
                )
                _upsert_recurring_schedule_summary(connection, effective)
        return effective, changed

    def delete_with_result(
        self,
        schedule_id: str,
        *,
        expected_next_run_at: str,
    ) -> bool:
        """Retire one disabled schedule without deleting dispatch history.

        The compare-and-swap token and ``BEGIN IMMEDIATE`` transaction serialize
        deletion with dispatcher claims.  A schedule must already be disabled
        and have no in-flight claim.  A tombstone makes a retry after an
        ambiguous audit failure a durable no-op while preventing unsafe ID
        reuse.
        """

        normalized_id = str(schedule_id)
        _safe_schedule_id(normalized_id)
        if not isinstance(expected_next_run_at, str) or not expected_next_run_at:
            raise ValueError("expected_next_run_at must be an ISO-8601 timestamp")
        expected = _normalize_aware_timestamp(
            expected_next_run_at,
            "expected_next_run_at",
        )
        with self._connection() as connection:
            connection.execute("begin immediate")
            tombstone = connection.execute(
                "select 1 from recurring_schedule_tombstones where schedule_id = ?",
                (normalized_id,),
            ).fetchone()
            if tombstone is not None:
                return False
            row = connection.execute(
                "select definition_json from recurring_schedules where schedule_id = ?",
                (normalized_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"recurring schedule not found: {normalized_id}")
            existing = _load_recurring_definition(row[0])
            current_schedule = existing["schedule"]
            if str(current_schedule["next_run_at"]) != expected:
                raise ValueError("recurring schedule delete precondition failed")
            if bool(current_schedule.get("enabled")) or str(
                current_schedule.get("status", "")
            ) != "disabled":
                raise ValueError("recurring schedule must be disabled before deletion")
            active_claim = connection.execute(
                "select 1 from schedule_dispatches where schedule_id = ? and status = 'claimed' limit 1",
                (normalized_id,),
            ).fetchone()
            if active_claim is not None:
                raise ValueError("recurring schedule has active dispatch")
            connection.execute(
                "insert into recurring_schedule_tombstones (schedule_id, deleted_at) values (?, ?)",
                (normalized_id, _utc_now()),
            )
            connection.execute(
                "delete from recurring_schedule_summaries where schedule_id = ?",
                (normalized_id,),
            )
            connection.execute(
                "delete from recurring_schedules where schedule_id = ?",
                (normalized_id,),
            )
        return True

    def get(self, schedule_id: str) -> Schedule:
        with self._connection() as connection:
            row = connection.execute(
                "select definition_json from recurring_schedules where schedule_id = ?",
                (str(schedule_id),),
            ).fetchone()
        if row is None:
            raise ValueError(f"recurring schedule not found: {schedule_id}")
        return _load_recurring_definition(row[0])

    def list(self) -> List[Schedule]:
        with self._connection() as connection:
            rows = connection.execute(
                "select definition_json from recurring_schedules order by schedule_id"
            ).fetchall()
        return [_load_recurring_definition(row[0]) for row in rows]

    def list_bounded(self, max_items: int) -> Dict[str, object]:
        """Stream definitions and retain only a bounded tail for read-only projections."""

        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items <= 0:
            raise ValueError("max_items must be a positive integer")
        selected = deque(maxlen=max_items)
        total = 0
        status_counts = {"active": 0, "disabled": 0, "other": 0}
        with self._connection() as connection:
            rows = connection.execute(
                "select definition_json from recurring_schedules order by schedule_id"
            )
            for row in rows:
                definition = _load_recurring_definition(row[0])
                total += 1
                status = str(definition["schedule"].get("status", ""))
                status_counts[status if status in {"active", "disabled"} else "other"] += 1
                selected.append(definition)
        return {
            "items": list(selected),
            "total": total,
            "status_counts": status_counts,
        }

    def list_compact_bounded(self, max_items: int) -> Dict[str, object]:
        """Read a bounded value-free projection without parsing trigger input."""

        _validate_local_window(max_items, "schedule list limit")
        status_counts = _empty_schedule_status_counts()
        with self._connection() as connection:
            total = int(
                connection.execute("select count(*) from recurring_schedule_summaries").fetchone()[0]
            )
            rows = connection.execute(
                "select status, count(*) from recurring_schedule_summaries group by status"
            ).fetchall()
            for status, count in rows:
                status_counts[_schedule_status_bucket(status)] += int(count)
            recent = connection.execute(
                """
                select schedule_id, workflow_id, workflow_version, status, enabled,
                       starts_at, next_run_at, interval_seconds, missed_run_policy,
                       last_activity_at, last_scheduled_for, last_run_id, last_trigger_id
                from recurring_schedule_summaries
                order by last_activity_at desc, schedule_id desc
                limit ?
                """,
                (max_items,),
            ).fetchall()
        selected = [_compact_recurring_summary(row) for row in reversed(recent)]
        return {
            "items": selected,
            "total": total,
            "status_counts": status_counts,
        }

    def set_enabled(self, schedule_id: str, enabled: bool) -> Schedule:
        definition, _changed = self.set_enabled_with_result(schedule_id, enabled)
        return definition

    def set_enabled_with_result(
        self,
        schedule_id: str,
        enabled: bool,
        *,
        expected_next_run_at: Optional[str] = None,
    ) -> Tuple[Schedule, bool]:
        """Set one recurring schedule state and report whether it changed.

        The state transition remains serialized with dispatcher claims by the
        same ``BEGIN IMMEDIATE`` transaction used by :meth:`set_enabled`.
        ``changed`` lets a remote operator retry an idempotent action without
        manufacturing a second state transition.  When ``expected_next_run_at``
        is supplied, the same transaction also performs a compare-and-swap so
        an operator cannot apply an intent based on an obsolete inventory read.
        """

        if not isinstance(enabled, bool):
            raise ValueError("schedule enabled state must be a boolean")
        expected = None
        if expected_next_run_at is not None:
            if not isinstance(expected_next_run_at, str) or not expected_next_run_at:
                raise ValueError("expected_next_run_at must be an ISO-8601 timestamp")
            expected = _normalize_aware_timestamp(
                expected_next_run_at,
                "expected_next_run_at",
            )
        with self._connection() as connection:
            connection.execute("begin immediate")
            row = connection.execute(
                "select definition_json from recurring_schedules where schedule_id = ?",
                (str(schedule_id),),
            ).fetchone()
            if row is None:
                raise ValueError(f"recurring schedule not found: {schedule_id}")
            definition = _load_recurring_definition(row[0])
            if expected is not None and str(
                definition["schedule"]["next_run_at"]
            ) != expected:
                raise ValueError("recurring schedule action precondition failed")
            previous_enabled = bool(definition["schedule"].get("enabled", False))
            changed = previous_enabled != enabled
            if changed:
                definition["schedule"]["enabled"] = enabled
                definition["schedule"]["status"] = "active" if enabled else "disabled"
                connection.execute(
                    "update recurring_schedules set definition_json = ?, updated_at = ? where schedule_id = ?",
                    (_json_text(definition), _utc_now(), str(schedule_id)),
                )
                _upsert_recurring_schedule_summary(connection, definition)
        return definition, changed

    def list_dispatches(self, schedule_id: str = "") -> List[Dict[str, object]]:
        query = "select record_json from schedule_dispatches"
        parameters = ()
        if schedule_id:
            query += " where schedule_id = ?"
            parameters = (str(schedule_id),)
        query += " order by scheduled_for, dispatch_id"
        with self._connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [json.loads(str(row[0])) for row in rows]

    def list_dispatches_bounded(
        self, max_items: int, schedule_id: str = ""
    ) -> Dict[str, object]:
        """Return bounded recent dispatch records and aggregate status counts."""

        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items <= 0:
            raise ValueError("max_items must be a positive integer")
        normalized_schedule_id = str(schedule_id)
        where = ""
        parameters = ()
        if normalized_schedule_id:
            where = " where schedule_id = ?"
            parameters = (normalized_schedule_id,)
        status_counts = {
            "claimed": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0,
            "uncertain": 0,
            "other": 0,
        }
        with self._connection() as connection:
            total = int(
                connection.execute(
                    f"select count(*) from schedule_dispatches{where}", parameters
                ).fetchone()[0]
            )
            rows = connection.execute(
                f"select status, count(*) from schedule_dispatches{where} group by status",
                parameters,
            ).fetchall()
            for status, count in rows:
                normalized_status = str(status)
                if normalized_status not in status_counts:
                    normalized_status = "other"
                status_counts[normalized_status] += int(count)
            recent = connection.execute(
                f"""
                select record_json from schedule_dispatches{where}
                order by scheduled_for desc, dispatch_id desc limit ?
                """,
                parameters + (max_items,),
            ).fetchall()
        records = [json.loads(str(row[0])) for row in recent]
        records.reverse()
        return {
            "items": records,
            "total": total,
            "status_counts": status_counts,
        }

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                create table if not exists recurring_schedules (
                    schedule_id text primary key,
                    definition_json text not null,
                    updated_at text not null
                )
                """
            )
            connection.execute(
                """
                create table if not exists recurring_schedule_tombstones (
                    schedule_id text primary key,
                    deleted_at text not null
                )
                """
            )
            connection.execute(
                """
                create table if not exists recurring_schedule_summaries (
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
            connection.execute(
                """
                create index if not exists recurring_schedule_summaries_activity_idx
                on recurring_schedule_summaries (last_activity_at, schedule_id)
                """
            )
            connection.execute(
                "delete from recurring_schedule_summaries where schedule_id not in (select schedule_id from recurring_schedules)"
            )
            summary_count = int(
                connection.execute(
                    "select count(*) from recurring_schedule_summaries"
                ).fetchone()[0]
            )
            schedule_count = int(
                connection.execute("select count(*) from recurring_schedules").fetchone()[0]
            )
            if summary_count < schedule_count:
                rows = connection.execute(
                    """
                    select recurring_schedules.schedule_id, recurring_schedules.definition_json
                    from recurring_schedules
                    left join recurring_schedule_summaries
                      on recurring_schedule_summaries.schedule_id = recurring_schedules.schedule_id
                    where recurring_schedule_summaries.schedule_id is null
                    order by recurring_schedules.schedule_id
                    """
                )
                for schedule_id, raw_definition in rows:
                    try:
                        definition = _load_recurring_definition(raw_definition)
                    except (TypeError, ValueError, json.JSONDecodeError) as error:
                        raise ValueError("SQLite recurring schedule is not valid JSON") from error
                    _upsert_recurring_schedule_summary(connection, definition)
            connection.execute(
                """
                create table if not exists schedule_dispatches (
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
                create table if not exists scheduler_leases (
                    lease_name text primary key,
                    owner_id text not null,
                    expires_at real not null
                )
                """
            )

    def _connection(self):
        return _scheduler_connection(self.db_path)


class RecurringScheduleDispatcher:
    """Claim and execute recurring occurrences under one persisted SQLite lease."""

    LEASE_NAME = "recurring-dispatcher"

    def __init__(
        self,
        state_dir: Path,
        credential_provider=None,
        owner_id: str = "",
        lease_seconds: int = 10,
    ):
        self.state_dir = Path(state_dir)
        self.store = RecurringScheduleStore(self.state_dir)
        self.owner_id = str(owner_id or f"owner_{secrets.token_hex(8)}")
        if isinstance(lease_seconds, bool) or not isinstance(lease_seconds, int) or lease_seconds < 2:
            raise ValueError("scheduler lease_seconds must be an integer of at least 2")
        self.lease_seconds = lease_seconds
        self.control_plane = LocalControlPlane(
            self.state_dir,
            storage="sqlite",
            credential_provider=credential_provider,
            execution_owner=self.owner_id,
        )

    def try_acquire(self, now_epoch: float) -> bool:
        now_value = float(now_epoch)
        with self.store._connection() as connection:
            connection.execute("begin immediate")
            row = connection.execute(
                "select owner_id, expires_at from scheduler_leases where lease_name = ?",
                (self.LEASE_NAME,),
            ).fetchone()
            if row and str(row[0]) != self.owner_id and float(row[1]) > now_value:
                return False
            connection.execute(
                """
                insert into scheduler_leases (lease_name, owner_id, expires_at)
                values (?, ?, ?)
                on conflict(lease_name) do update set
                    owner_id = excluded.owner_id,
                    expires_at = excluded.expires_at
                """,
                (self.LEASE_NAME, self.owner_id, now_value + self.lease_seconds),
            )
        return True

    def renew(self, now_epoch: float) -> bool:
        now_value = float(now_epoch)
        with self.store._connection() as connection:
            cursor = connection.execute(
                """
                update scheduler_leases
                set expires_at = ?
                where lease_name = ? and owner_id = ? and expires_at > ?
                """,
                (now_value + self.lease_seconds, self.LEASE_NAME, self.owner_id, now_value),
            )
        return cursor.rowcount == 1

    def has_lease(self, now_epoch: float) -> bool:
        with self.store._connection() as connection:
            row = connection.execute(
                "select owner_id, expires_at from scheduler_leases where lease_name = ?",
                (self.LEASE_NAME,),
            ).fetchone()
        return bool(row and str(row[0]) == self.owner_id and float(row[1]) > float(now_epoch))

    def release(self) -> None:
        with self.store._connection() as connection:
            connection.execute(
                "delete from scheduler_leases where lease_name = ? and owner_id = ?",
                (self.LEASE_NAME, self.owner_id),
            )

    def claim_due(
        self, now: str, now_epoch: float, max_items: int = None
    ) -> List[Dict[str, object]]:
        now_at = _normalize_timestamp(now, "now")
        now_value = float(now_epoch)
        if max_items is not None:
            _validate_dispatch_limit(max_items)
        with self.store._connection() as connection:
            connection.execute("begin immediate")
            if not self._owns_lease(connection, now_value):
                raise SchedulerLeaseError("scheduler lease is not held by this dispatcher")
            rows = connection.execute(
                "select schedule_id, definition_json from recurring_schedules order by schedule_id"
            )
            claimed = []
            for schedule_id, raw_definition in rows:
                definition = _load_recurring_definition(raw_definition)
                schedule = definition["schedule"]
                if not schedule["enabled"] or schedule["status"] != "active":
                    continue
                next_at = _parse_timestamp(str(schedule["next_run_at"]))
                current_at = _parse_timestamp(now_at)
                if next_at > current_at:
                    continue
                interval = int(schedule["interval_seconds"])
                due_count = int((current_at - next_at).total_seconds() // interval) + 1
                latest_at = next_at + timedelta(seconds=(due_count - 1) * interval)
                future_at = next_at + timedelta(seconds=due_count * interval)
                scheduled_for = _format_timestamp(latest_at)
                next_run_at = _format_timestamp(future_at)
                policy = str(schedule["missed_run_policy"])
                status = "skipped" if policy == "skip" and due_count > 1 else "claimed"
                coalesced = due_count if status == "skipped" else due_count - 1
                record = {
                    "dispatch_id": _dispatch_id(str(schedule_id), scheduled_for),
                    "schedule_id": str(schedule_id),
                    "scheduled_for": scheduled_for,
                    "status": status,
                    "owner_id": self.owner_id,
                    "claim_expires_at": now_value + self.lease_seconds,
                    "coalesced_occurrences": coalesced,
                    "run_id": "",
                    "trigger_id": "",
                    "error_type": "",
                    "completed_at": _utc_now() if status == "skipped" else "",
                }
                try:
                    connection.execute(
                        """
                        insert into schedule_dispatches (
                            dispatch_id, schedule_id, scheduled_for, status,
                            owner_id, claim_expires_at, record_json
                        ) values (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            record["dispatch_id"],
                            record["schedule_id"],
                            record["scheduled_for"],
                            record["status"],
                            record["owner_id"],
                            record["claim_expires_at"],
                            _json_text(record),
                        ),
                    )
                except sqlite3.IntegrityError:
                    continue
                schedule["next_run_at"] = next_run_at
                schedule["last_scheduled_for"] = scheduled_for
                connection.execute(
                    "update recurring_schedules set definition_json = ?, updated_at = ? where schedule_id = ?",
                    (_json_text(definition), _utc_now(), str(schedule_id)),
                )
                _upsert_recurring_schedule_summary(connection, definition)
                claimed.append(record)
                if max_items is not None and len(claimed) >= max_items:
                    break
        return claimed

    def dispatch_due(
        self, now: str, now_epoch: float, max_items: int = None
    ) -> ScheduleRunResult:
        if max_items is not None:
            _validate_dispatch_limit(max_items)
        claims = self.claim_due(now, now_epoch, max_items=max_items)
        runs = []
        skipped = 0
        failures = 0
        for claim in claims:
            if claim["status"] == "skipped":
                skipped += int(claim["coalesced_occurrences"])
                continue
            schedule = self.store.get(str(claim["schedule_id"]))
            request = _recurring_trigger_request(schedule, str(claim["scheduled_for"]))
            try:
                response = self.control_plane.trigger_workflow(request)
            except Exception as error:
                failures += 1
                self._finish_claim(claim, "failed", error_type=type(error).__name__)
                continue
            self._finish_claim(
                claim,
                "completed",
                run_id=str(response["run_id"]),
                trigger_id=str(response["trigger_id"]),
            )
            result = dict(response)
            result.update(
                {
                    "schedule_id": claim["schedule_id"],
                    "scheduled_for": claim["scheduled_for"],
                    "coalesced_occurrences": claim["coalesced_occurrences"],
                    "dispatch_id": claim["dispatch_id"],
                }
            )
            runs.append(result)
        result = {
            "now": _normalize_timestamp(now, "now"),
            "count": len(runs),
            "skipped": skipped,
            "failures": failures,
            "runs": runs,
        }
        if max_items is not None:
            result["processed"] = len(claims)
        return result

    def recover_stale_claims(self, now_epoch: float, max_items: int = None) -> int:
        now_value = float(now_epoch)
        if max_items is not None:
            _validate_dispatch_limit(max_items)
        with self.store._connection() as connection:
            connection.execute("begin immediate")
            if not self._owns_lease(connection, now_value):
                raise SchedulerLeaseError("scheduler lease is not held by this dispatcher")
            rows = _iter_stale_claim_rows(connection, now_value)
            recovered = 0
            for dispatch_id, raw_record in rows:
                record = json.loads(str(raw_record))
                record["status"] = "uncertain"
                record["completed_at"] = _utc_now()
                connection.execute(
                    "update schedule_dispatches set status = 'uncertain', record_json = ? where dispatch_id = ?",
                    (_json_text(record), str(dispatch_id)),
                )
                recovered += 1
                if max_items is not None and recovered >= max_items:
                    break
        return recovered

    def _finish_claim(
        self,
        claim: Dict[str, object],
        status: str,
        run_id: str = "",
        trigger_id: str = "",
        error_type: str = "",
    ) -> None:
        record = dict(claim)
        record.update(
            {
                "status": status,
                "run_id": run_id,
                "trigger_id": trigger_id,
                "error_type": error_type,
                "completed_at": _utc_now(),
            }
        )
        with self.store._connection() as connection:
            connection.execute("begin immediate")
            cursor = connection.execute(
                """
                update schedule_dispatches
                set status = ?, record_json = ?
                where dispatch_id = ? and status = 'claimed' and owner_id = ?
                """,
                (status, _json_text(record), str(claim["dispatch_id"]), self.owner_id),
            )
            if cursor.rowcount != 1:
                return
            definition = self.store.get(str(claim["schedule_id"]))
            schedule = definition["schedule"]
            if str(schedule["last_scheduled_for"]) == str(claim["scheduled_for"]):
                schedule["last_run_id"] = run_id
                schedule["last_trigger_id"] = trigger_id
                connection.execute(
                    "update recurring_schedules set definition_json = ?, updated_at = ? where schedule_id = ?",
                    (_json_text(definition), _utc_now(), str(claim["schedule_id"])),
                )
                _upsert_recurring_schedule_summary(connection, definition)

    def _owns_lease(self, connection, now_epoch: float) -> bool:
        row = connection.execute(
            "select owner_id, expires_at from scheduler_leases where lease_name = ?",
            (self.LEASE_NAME,),
        ).fetchone()
        return bool(
            row
            and str(row[0]) == self.owner_id
            and float(row[1]) > float(now_epoch)
        )


def normalize_recurring_schedule_definition(definition: object, persisted: bool = False) -> Schedule:
    """Validate a durable interval schedule and its explicit missed-run policy."""

    if not isinstance(definition, dict):
        raise ValueError("recurring schedule definition must be a JSON object")
    if set(definition) != {"schema_version", "schedule", "trigger"}:
        raise ValueError("recurring schedule requires only schema_version, schedule, and trigger")
    if definition.get("schema_version") != RECURRING_SCHEDULE_SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {RECURRING_SCHEDULE_SCHEMA_VERSION}")
    schedule = definition.get("schedule")
    trigger = definition.get("trigger")
    if not isinstance(schedule, dict):
        raise ValueError("recurring schedule.schedule must be an object")
    if not isinstance(trigger, dict):
        raise ValueError("recurring schedule.trigger must be an object")
    base_keys = {
        "id", "workflow_id", "version", "starts_at", "interval_seconds",
        "missed_run_policy", "enabled",
    }
    state_keys = {"status", "next_run_at", "last_scheduled_for", "last_run_id", "last_trigger_id"}
    allowed_schedule_keys = base_keys | (state_keys if persisted else set())
    unknown_schedule = set(schedule) - allowed_schedule_keys
    required_schedule = {"id", "workflow_id", "version", "starts_at", "interval_seconds", "missed_run_policy"}
    if unknown_schedule:
        raise ValueError(f"recurring schedule.schedule has unknown fields: {sorted(unknown_schedule)}")
    if not required_schedule.issubset(schedule):
        raise ValueError("recurring schedule.schedule is missing required fields")
    allowed_trigger_keys = {"idempotency_key_prefix", "input"}
    if persisted:
        allowed_trigger_keys.add("source")
    if set(trigger) - allowed_trigger_keys:
        raise ValueError("recurring schedule.trigger has unknown fields")

    schedule_id = _required_text(schedule, "id", "schedule.id")
    _safe_schedule_id(schedule_id)
    derived_source = f"recurring-schedule:{schedule_id}"
    if persisted and str(trigger.get("source") or "") != derived_source:
        raise ValueError("recurring schedule.trigger source does not match schedule.id")
    interval = schedule.get("interval_seconds")
    if isinstance(interval, bool) or not isinstance(interval, int) or not 1 <= interval <= 31536000:
        raise ValueError("schedule.interval_seconds must be an integer from 1 through 31536000")
    policy = str(schedule.get("missed_run_policy") or "")
    if policy not in {"latest", "skip"}:
        raise ValueError("schedule.missed_run_policy must be latest or skip")
    enabled = schedule.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError("schedule.enabled must be a boolean")
    starts_at = _normalize_aware_timestamp(
        _required_text(schedule, "starts_at", "schedule.starts_at"),
        "schedule.starts_at",
    )
    prefix = str(trigger.get("idempotency_key_prefix") or schedule_id)
    if (
        not 1 <= len(prefix) <= 128
        or any(not (char.isalnum() or char in {"-", "_", ".", ":"}) for char in prefix)
    ):
        raise ValueError(
            "trigger.idempotency_key_prefix must contain 1-128 safe characters"
        )
    input_value = trigger.get("input", {})
    if not isinstance(input_value, dict):
        raise ValueError("recurring schedule trigger input must be an object")

    status = str(schedule.get("status") or ("active" if enabled else "disabled"))
    if status not in {"active", "disabled"}:
        raise ValueError("schedule.status must be active or disabled")
    if (status == "active") != enabled:
        raise ValueError("schedule.status must agree with schedule.enabled")
    next_run_at = _normalize_aware_timestamp(
        str(schedule.get("next_run_at") or starts_at),
        "schedule.next_run_at",
    )
    last_scheduled_for = str(schedule.get("last_scheduled_for") or "")
    if last_scheduled_for:
        last_scheduled_for = _normalize_aware_timestamp(
            last_scheduled_for,
            "schedule.last_scheduled_for",
        )

    return {
        "schema_version": RECURRING_SCHEDULE_SCHEMA_VERSION,
        "schedule": {
            "id": schedule_id,
            "workflow_id": _required_text(schedule, "workflow_id", "schedule.workflow_id"),
            "version": _required_text(schedule, "version", "schedule.version"),
            "starts_at": starts_at,
            "interval_seconds": interval,
            "missed_run_policy": policy,
            "enabled": enabled,
            "status": status,
            "next_run_at": next_run_at,
            "last_scheduled_for": last_scheduled_for,
            "last_run_id": str(schedule.get("last_run_id") or ""),
            "last_trigger_id": str(schedule.get("last_trigger_id") or ""),
        },
        "trigger": {
            "source": derived_source,
            "idempotency_key_prefix": prefix,
            "input": normalize_trigger_input(input_value, "recurring schedule trigger input"),
        },
    }


def _recurring_trigger_request(schedule: Schedule, scheduled_for: str) -> Dict[str, object]:
    meta = schedule["schedule"]
    trigger = schedule["trigger"]
    return {
        "workflow_id": str(meta["workflow_id"]),
        "version": str(meta["version"]),
        "source": str(trigger["source"]),
        "idempotency_key": f"{trigger['idempotency_key_prefix']}:{scheduled_for}",
        "input": copy.deepcopy(trigger["input"]),
    }


def _iter_stale_claim_rows(connection, now_epoch: float):
    """Return a cursor for stale claims without materializing the result set."""

    return connection.execute(
        """
        select dispatch_id, record_json from schedule_dispatches
        where status = 'claimed' and claim_expires_at <= ?
        """,
        (float(now_epoch),),
    )


def _load_recurring_definition(value: object) -> Schedule:
    payload = json.loads(str(value))
    return normalize_recurring_schedule_definition(payload, persisted=True)


def _normalize_aware_timestamp(value: str, field: str) -> str:
    normalized = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO-8601 timestamp: {error}")
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return _format_timestamp(parsed)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _dispatch_id(schedule_id: str, scheduled_for: str) -> str:
    digest = hashlib.sha256(f"{schedule_id}\0{scheduled_for}".encode("utf-8")).hexdigest()[:16]
    return f"dispatch_{digest}"


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _upsert_recurring_schedule_summary(connection, definition: Schedule) -> None:
    """Maintain the compact recurring projection in the same transaction as its definition."""

    meta = definition["schedule"]
    last_scheduled_for = str(meta.get("last_scheduled_for", ""))
    last_activity_at = last_scheduled_for or str(meta.get("next_run_at", "")) or str(
        meta.get("starts_at", "")
    )
    connection.execute(
        """
        insert into recurring_schedule_summaries (
            schedule_id, workflow_id, workflow_version, status, enabled,
            starts_at, next_run_at, interval_seconds, missed_run_policy,
            last_activity_at, last_scheduled_for, last_run_id, last_trigger_id,
            updated_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(schedule_id) do update set
            workflow_id = excluded.workflow_id,
            workflow_version = excluded.workflow_version,
            status = excluded.status,
            enabled = excluded.enabled,
            starts_at = excluded.starts_at,
            next_run_at = excluded.next_run_at,
            interval_seconds = excluded.interval_seconds,
            missed_run_policy = excluded.missed_run_policy,
            last_activity_at = excluded.last_activity_at,
            last_scheduled_for = excluded.last_scheduled_for,
            last_run_id = excluded.last_run_id,
            last_trigger_id = excluded.last_trigger_id,
            updated_at = excluded.updated_at
        """,
        (
            str(meta["id"]),
            str(meta["workflow_id"]),
            str(meta["version"]),
            str(meta["status"]),
            1 if bool(meta["enabled"]) else 0,
            str(meta["starts_at"]),
            str(meta["next_run_at"]),
            int(meta["interval_seconds"]),
            str(meta["missed_run_policy"]),
            last_activity_at,
            last_scheduled_for,
            str(meta.get("last_run_id", "")),
            str(meta.get("last_trigger_id", "")),
            _utc_now(),
        ),
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _scheduler_connection(path: Path):
    with closing(sqlite3.connect(path, timeout=5)) as connection:
        with connection:
            yield connection
