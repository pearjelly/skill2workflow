"""Strict redacted evidence boundary for the controlled Lark pilot."""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Set
from zoneinfo import ZoneInfo


EVIDENCE_SCHEMA_VERSION = "controlled-lark-pilot-evidence-0.1.0"
EXERCISE_SCHEMA_VERSION = "controlled-lark-pilot-exercise-0.1.0"
VERIFICATION_SCHEMA_VERSION = "controlled-lark-pilot-verification-0.1.0"
DECISION_SCHEMA_VERSION = "controlled-lark-pilot-decision-0.1.0"
INDEX_SCHEMA_VERSION = "controlled-lark-pilot-index-0.1.0"
WORKFLOW_ID = "workflow_controlled_lark_pilot"
WORKFLOW_VERSION = "0.1.0"
CONNECTOR_ID = "lark_task"
CREDENTIAL_HANDLE = "lark_bot_access_token"
OPERATION = "create_task"
MODE = "live"
TIMEZONE = "Asia/Shanghai"

def _keys(names: str) -> Set[str]:
    """Keep large exact allowlists readable without repeating set syntax."""
    return set(names.split())


RUN_EVIDENCE_KEYS = _keys(
    "schema_version run_id workflow_id workflow_version started_at completed_at "
    "run_status gate_decision case_id_present connector_invoked connector_id "
    "connector_status credential_status credential_handles operation mode "
    "provider_status task_title_present task_description_present assignee_present "
    "due_at_present idempotency_key_present lark_task_id_present"
)
CHARTER_KEYS = _keys(
    "schema_version scenario_id workflow_id workflow_version support_model timezone "
    "starts_on expires_on team_consent_confirmed assignee_consent_confirmed "
    "commercial_engagement_confirmed required_approved_runs required_distinct_days "
    "required_distinct_cases"
)
TOP_LEVEL_KEYS = _keys("charter runs exercises verification decision index")
EXERCISE_SLOT_KEYS = _keys("rejection failure rollback")
REJECTION_EXERCISE_KEYS = _keys(
    "schema_version exercise passed run_id gate_decision connector_invoked"
)
FAILURE_EXERCISE_KEYS = _keys(
    "schema_version exercise passed provider_status credential_resolution_attempted "
    "transport_attempted"
)
ROLLBACK_EXERCISE_KEYS = _keys(
    "schema_version exercise passed live_switch_enabled live_approval_blocked "
    "dry_run_status"
)
VERIFICATION_KEYS = _keys("schema_version all_passed commands")
VERIFICATION_COMMAND_KEYS = _keys("id exit_code passed duration_ms")
DECISION_KEYS = _keys(
    "schema_version decision partner_acknowledged operator_acknowledged "
    "commercial_engagement_confirmed rationale"
)
INDEX_KEYS = _keys(
    "schema_version generated_at workflow_id workflow_version timezone "
    "approved_live_runs required_approved_runs distinct_calendar_days "
    "required_distinct_days distinct_private_cases required_distinct_cases "
    "rejected_runs rejection_passed failure_passed rollback_passed "
    "verification_passed decision_recorded decision partner_acknowledged "
    "operator_acknowledged commercial_engagement_confirmed ready_to_finalize "
    "unmet_conditions"
)
VERIFICATION_COMMAND_IDS = (
    "focused-tests",
    "full-tests",
    "compile",
    "secret-hygiene",
    "connector-smoke",
    "dry-run-pilot-smoke",
    "diff-check",
)
UNMET_CONDITIONS = (
    "approved_live_runs_threshold",
    "distinct_calendar_days_threshold",
    "distinct_private_cases_threshold",
    "human_rejection",
    "disabled_live_exercise",
    "rollback_exercise",
    "verification",
    "decision",
    "partner_acknowledgement",
    "operator_acknowledgement",
    "commercial_engagement_confirmation",
)
PROVIDER_STATUSES = {
    "",
    "authorization_failed",
    "completed",
    "credential_failed",
    "live_disabled",
    "malformed_response",
    "provider_unavailable",
    "validation_failed",
}


def _scan_event(
    events: object,
    event_types: tuple,
    reverse: bool = False,
    node_id: str = "",
) -> Dict[str, object]:
    if not isinstance(events, list):
        return {}
    candidates = reversed(events) if reverse else events
    for event in candidates:
        if (
            isinstance(event, dict)
            and event.get("type") in event_types
            and (not node_id or event.get("node_id") == node_id)
        ):
            return event
    return {}


def _first_event(events: object, event_type: str) -> Dict[str, object]:
    return _scan_event(events, (event_type,))


def _last_event(events: object, event_type: str) -> Dict[str, object]:
    return _scan_event(events, (event_type,), reverse=True)


def _last_connector_event(events: object) -> Dict[str, object]:
    return _scan_event(
        events,
        ("connector_started", "connector_completed", "connector_failed"),
        reverse=True,
        node_id="create_lark_task",
    )


def _terminal_event(events: object) -> Dict[str, object]:
    return _scan_event(
        events, ("run_completed", "run_failed", "run_rejected"), reverse=True
    )


def build_run_evidence(
    run: Dict[str, object], audit_events: List[Dict[str, object]]
) -> Dict[str, object]:
    if not isinstance(run, dict):
        raise ValueError("run must be an object")
    resumed = _last_event(audit_events, "run_resumed")
    connector = _last_connector_event(audit_events)
    metadata = connector.get("connector_metadata", {}) if connector else {}
    if not isinstance(metadata, dict):
        metadata = {}
    context = run.get("context", {})
    if not isinstance(context, dict):
        context = {}
    trigger_input = context.get("input", {})
    if not isinstance(trigger_input, dict):
        trigger_input = {}
    raw_handles = connector.get("credential_handles", []) if connector else []
    handles = list(raw_handles) if isinstance(raw_handles, list) else []
    evidence = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "run_id": str(run.get("run_id", "")),
        "workflow_id": str(run.get("workflow_id", "")),
        "workflow_version": str(run.get("workflow_version", "")),
        "started_at": str(_first_event(audit_events, "run_started").get("timestamp", "")),
        "completed_at": str(_terminal_event(audit_events).get("timestamp", "")),
        "run_status": str(run.get("status", "")),
        "gate_decision": (
            "approved"
            if resumed.get("approved") is True
            else "rejected"
            if resumed.get("approved") is False
            else "pending"
        ),
        "case_id_present": bool(str(trigger_input.get("pilot_case_id", "")).strip()),
        "connector_invoked": bool(connector),
        "connector_id": str(connector.get("connector_id", "")) if connector else "",
        "connector_status": str(connector.get("connector_status", "")) if connector else "",
        "credential_status": str(connector.get("credential_status", "")) if connector else "",
        "credential_handles": handles,
        "operation": str(metadata.get("operation", "")),
        "mode": str(metadata.get("mode", "")),
        "provider_status": str(metadata.get("provider_status", "")),
        "task_title_present": bool(metadata.get("task_title_present")),
        "task_description_present": bool(metadata.get("task_description_present")),
        "assignee_present": bool(metadata.get("assignee_present")),
        "due_at_present": bool(metadata.get("due_at_present")),
        "idempotency_key_present": bool(metadata.get("idempotency_key_present")),
        "lark_task_id_present": bool(metadata.get("lark_task_id_present")),
    }
    _validate_run(evidence)
    return evidence


def _aware_datetime(value: object, label: str, allow_empty: bool = False) -> datetime:
    if allow_empty and value == "":
        return None
    if type(value) is not str:
        raise ValueError(f"{label} must be a timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{label} must be an ISO timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed


def _is_approved_live_run(run: object) -> bool:
    if not isinstance(run, dict):
        return False
    expected = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "run_status": "completed",
        "gate_decision": "approved",
        "case_id_present": True,
        "connector_invoked": True,
        "connector_id": CONNECTOR_ID,
        "connector_status": "completed",
        "credential_status": "resolved",
        "credential_handles": [CREDENTIAL_HANDLE],
        "operation": OPERATION,
        "mode": MODE,
        "provider_status": "completed",
        "task_title_present": True,
        "task_description_present": True,
        "assignee_present": True,
        "due_at_present": True,
        "idempotency_key_present": True,
        "lark_task_id_present": True,
    }
    if any(run.get(key) != value for key, value in expected.items()):
        return False
    try:
        _aware_datetime(run.get("completed_at"), "completed_at")
    except ValueError:
        return False
    return True


def _is_human_rejection(run: object) -> bool:
    return bool(
        isinstance(run, dict)
        and run.get("workflow_id") == WORKFLOW_ID
        and run.get("workflow_version") == WORKFLOW_VERSION
        and run.get("run_status") in ("failed", "rejected")
        and run.get("gate_decision") == "rejected"
        and run.get("connector_invoked") is False
    )


def _rejection_exercise(runs: List[Dict[str, object]]):
    for run in runs:
        if _is_human_rejection(run):
            return {
                "schema_version": EXERCISE_SCHEMA_VERSION,
                "exercise": "rejection",
                "passed": True,
                "run_id": run["run_id"],
                "gate_decision": "rejected",
                "connector_invoked": False,
            }
    return None


def _run_sort_key(run: Dict[str, object]) -> tuple:
    return (_aware_datetime(run.get("started_at"), "started_at"), run.get("run_id", ""))


def _qualified_exercise(exercises: object, name: str) -> bool:
    if not isinstance(exercises, dict):
        return False
    exercise = exercises.get(name)
    if not isinstance(exercise, dict) or exercise.get("passed") is not True:
        return False
    if name == "failure" and len(exercise) > 1:
        return bool(
            exercise.get("provider_status") == "live_disabled"
            and exercise.get("credential_resolution_attempted") is False
            and exercise.get("transport_attempted") is False
        )
    if name == "rollback" and len(exercise) > 1:
        return bool(
            exercise.get("live_switch_enabled") is False
            and exercise.get("live_approval_blocked") is True
            and exercise.get("dry_run_status") == "completed"
        )
    return True


def build_acceptance_summary(
    charter: Dict[str, object],
    runs: List[Dict[str, object]],
    distinct_private_cases: int,
    exercises: Dict[str, object],
    verification: Dict[str, object],
    decision: Dict[str, object],
) -> Dict[str, object]:
    if type(distinct_private_cases) is not int or distinct_private_cases < 0:
        raise ValueError("distinct private cases must be a nonnegative integer")
    if not isinstance(charter, dict) or not isinstance(runs, list):
        raise ValueError("charter and runs must use the expected containers")
    approved = [run for run in runs if _is_approved_live_run(run)]
    days: Set[date] = set()
    for run in approved:
        completed = _aware_datetime(run["completed_at"], "completed_at")
        days.add(completed.astimezone(ZoneInfo(TIMEZONE)).date())
    rejected_runs = sum(1 for run in runs if _is_human_rejection(run))
    failure_passed = _qualified_exercise(exercises, "failure")
    rollback_passed = _qualified_exercise(exercises, "rollback")
    verification_passed = bool(
        isinstance(verification, dict) and verification.get("all_passed") is True
    )
    decision_recorded = bool(
        isinstance(decision, dict)
        and decision.get("decision") in ("continue", "harden", "defer")
        and type(decision.get("rationale")) is str
        and bool(decision["rationale"].strip())
    )
    partner_acknowledged = bool(
        decision_recorded and decision.get("partner_acknowledged") is True
    )
    operator_acknowledged = bool(
        decision_recorded and decision.get("operator_acknowledged") is True
    )
    charter_commercial = charter.get("commercial_engagement_confirmed") is True
    commercial_confirmed = bool(
        charter_commercial
        and (
            decision is None
            or (
                decision_recorded
                and decision.get("commercial_engagement_confirmed") is True
            )
        )
    )
    predicates = (
        len(approved) >= charter.get("required_approved_runs", 0),
        len(days) >= charter.get("required_distinct_days", 0),
        distinct_private_cases >= charter.get("required_distinct_cases", 0),
        rejected_runs >= 1,
        failure_passed,
        rollback_passed,
        verification_passed,
        decision_recorded,
        partner_acknowledged,
        operator_acknowledged,
        commercial_confirmed,
    )
    unmet = [name for name, passed in zip(UNMET_CONDITIONS, predicates) if not passed]
    return {
        "approved_live_runs": len(approved),
        "required_approved_runs": charter.get("required_approved_runs", 0),
        "distinct_calendar_days": len(days),
        "required_distinct_days": charter.get("required_distinct_days", 0),
        "distinct_private_cases": distinct_private_cases,
        "required_distinct_cases": charter.get("required_distinct_cases", 0),
        "rejected_runs": rejected_runs,
        "rejection_passed": rejected_runs >= 1,
        "failure_passed": failure_passed,
        "rollback_passed": rollback_passed,
        "verification_passed": verification_passed,
        "decision_recorded": decision_recorded,
        "decision": str(decision.get("decision", "")) if decision_recorded else "",
        "partner_acknowledged": partner_acknowledged,
        "operator_acknowledged": operator_acknowledged,
        "commercial_engagement_confirmed": commercial_confirmed,
        "ready_to_finalize": not unmet,
        "unmet_conditions": unmet,
    }


def _require_keys(value: object, keys: Set[str], label: str) -> Dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} keys do not match the allowlist")
    return value


def _require_bool(value: object, label: str) -> None:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a boolean")


def _require_nonnegative_int(value: object, label: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")


def _validate_charter(charter: object) -> None:
    value = _require_keys(charter, CHARTER_KEYS, "charter")
    exact = {
        "schema_version": "controlled-lark-pilot-0.1.0",
        "scenario_id": "sales_renewal_risk_followup",
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "support_model": "assisted",
        "timezone": TIMEZONE,
        "required_approved_runs": 5,
        "required_distinct_days": 5,
        "required_distinct_cases": 2,
    }
    if any(value.get(key) != expected for key, expected in exact.items()):
        raise ValueError("charter fixed values are invalid")
    for key in (
        "required_approved_runs required_distinct_days required_distinct_cases"
    ).split():
        _require_nonnegative_int(value.get(key), f"charter {key}")
    for key in (
        "team_consent_confirmed assignee_consent_confirmed "
        "commercial_engagement_confirmed"
    ).split():
        if value.get(key) is not True:
            raise ValueError(f"charter {key} must be true")
    if type(value.get("starts_on")) is not str or type(value.get("expires_on")) is not str:
        raise ValueError("charter dates must be strings")
    try:
        starts = date.fromisoformat(value["starts_on"])
        expires = date.fromisoformat(value["expires_on"])
    except ValueError as error:
        raise ValueError("charter dates must be ISO dates") from error
    if starts > expires:
        raise ValueError("charter date range is invalid")


def _validate_run(run: object) -> None:
    value = _require_keys(run, RUN_EVIDENCE_KEYS, "run evidence")
    if value.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise ValueError("run evidence schema is invalid")
    for key in ("run_id", "workflow_id", "workflow_version", "run_status", "gate_decision"):
        if type(value.get(key)) is not str:
            raise ValueError(f"run evidence {key} must be a string")
    if not value["run_id"].strip():
        raise ValueError("run evidence run_id must be nonempty")
    if value["workflow_id"] != WORKFLOW_ID or value["workflow_version"] != WORKFLOW_VERSION:
        raise ValueError("run evidence workflow identity is invalid")
    if value["run_status"] not in ("waiting", "completed", "failed", "rejected"):
        raise ValueError("run evidence status is invalid")
    if value["gate_decision"] not in ("pending", "approved", "rejected"):
        raise ValueError("run evidence gate decision is invalid")
    _aware_datetime(value.get("started_at"), "started_at")
    _aware_datetime(value.get("completed_at"), "completed_at", allow_empty=True)
    for key in (
        "case_id_present connector_invoked task_title_present "
        "task_description_present assignee_present due_at_present "
        "idempotency_key_present lark_task_id_present"
    ).split():
        _require_bool(value.get(key), f"run evidence {key}")
    if value.get("connector_id") not in ("", CONNECTOR_ID):
        raise ValueError("run evidence connector identity is invalid")
    if value.get("connector_status") not in ("", "running", "completed", "failed"):
        raise ValueError("run evidence connector status is invalid")
    if value.get("credential_status") not in ("", "resolved", "failed", "skipped"):
        raise ValueError("run evidence credential status is invalid")
    if value.get("credential_handles") not in ([], [CREDENTIAL_HANDLE]):
        raise ValueError("run evidence credential handles are invalid")
    if value.get("operation") not in ("", OPERATION) or value.get("mode") not in ("", MODE):
        raise ValueError("run evidence connector binding is invalid")
    if value.get("provider_status") not in PROVIDER_STATUSES:
        raise ValueError("run evidence provider status is invalid")
    if value["connector_invoked"] is False:
        empty = all(
            value[key] in ("", [])
            for key in (
                "connector_id connector_status credential_status credential_handles "
                "operation mode provider_status"
            ).split()
        )
        if not empty:
            raise ValueError("uninvoked connector evidence must be empty")


def _validate_exercise(name: str, exercise: object) -> None:
    if exercise is None:
        return
    schemas = {
        "rejection": REJECTION_EXERCISE_KEYS,
        "failure": FAILURE_EXERCISE_KEYS,
        "rollback": ROLLBACK_EXERCISE_KEYS,
    }
    value = _require_keys(exercise, schemas[name], f"{name} exercise")
    if value.get("schema_version") != EXERCISE_SCHEMA_VERSION:
        raise ValueError(f"{name} exercise schema is invalid")
    _require_bool(value.get("passed"), f"{name} exercise passed")
    if name == "rejection":
        if (
            value.get("exercise") != "rejection"
            or type(value.get("run_id")) is not str
            or not value["run_id"].strip()
            or value.get("gate_decision") != "rejected"
            or value.get("connector_invoked") is not False
        ):
            raise ValueError("rejection exercise values are invalid")
    elif name == "failure":
        if value.get("exercise") != "disabled_live" or value.get("provider_status") not in PROVIDER_STATUSES:
            raise ValueError("failure exercise values are invalid")
        _require_bool(value.get("credential_resolution_attempted"), "failure credential attempt")
        _require_bool(value.get("transport_attempted"), "failure transport attempt")
    else:
        if value.get("exercise") != "rollback" or value.get("dry_run_status") not in ("", "completed", "failed"):
            raise ValueError("rollback exercise values are invalid")
        _require_bool(value.get("live_switch_enabled"), "rollback live switch")
        _require_bool(value.get("live_approval_blocked"), "rollback approval")


def _validate_verification(verification: object) -> None:
    if verification is None:
        return
    value = _require_keys(verification, VERIFICATION_KEYS, "verification")
    if value.get("schema_version") != VERIFICATION_SCHEMA_VERSION:
        raise ValueError("verification schema is invalid")
    _require_bool(value.get("all_passed"), "verification all_passed")
    commands = value.get("commands")
    if not isinstance(commands, list):
        raise ValueError("verification commands must be a list")
    seen = []
    for command in commands:
        item = _require_keys(command, VERIFICATION_COMMAND_KEYS, "verification command")
        if item.get("id") not in VERIFICATION_COMMAND_IDS:
            raise ValueError("verification command identity is invalid")
        seen.append(item["id"])
        _require_nonnegative_int(item.get("exit_code"), "verification exit code")
        _require_nonnegative_int(item.get("duration_ms"), "verification duration")
        _require_bool(item.get("passed"), "verification command passed")
        if item["passed"] != (item["exit_code"] == 0):
            raise ValueError("verification command result is inconsistent")
    expected_prefix = [item for item in VERIFICATION_COMMAND_IDS if item in seen]
    if seen != expected_prefix or len(seen) != len(set(seen)):
        raise ValueError("verification command order is invalid")
    complete = tuple(seen) == VERIFICATION_COMMAND_IDS and all(
        command["passed"] for command in commands
    )
    if value["all_passed"] != complete:
        raise ValueError("verification aggregate is inconsistent")


def _validate_decision(decision: object) -> None:
    if decision is None:
        return
    value = _require_keys(decision, DECISION_KEYS, "decision")
    if value.get("schema_version") != DECISION_SCHEMA_VERSION:
        raise ValueError("decision schema is invalid")
    if value.get("decision") not in ("continue", "harden", "defer"):
        raise ValueError("decision value is invalid")
    for key in (
        "partner_acknowledged operator_acknowledged commercial_engagement_confirmed"
    ).split():
        _require_bool(value.get(key), f"decision {key}")
    if type(value.get("rationale")) is not str or not value["rationale"].strip():
        raise ValueError("decision rationale must be a nonempty string")


def _validate_index(index: object) -> None:
    value = _require_keys(index, INDEX_KEYS, "evidence index")
    if (
        value.get("schema_version") != INDEX_SCHEMA_VERSION
        or value.get("workflow_id") != WORKFLOW_ID
        or value.get("workflow_version") != WORKFLOW_VERSION
        or value.get("timezone") != TIMEZONE
    ):
        raise ValueError("evidence index identity is invalid")
    _aware_datetime(value.get("generated_at"), "generated_at")
    for key in (
        "approved_live_runs required_approved_runs distinct_calendar_days "
        "required_distinct_days distinct_private_cases required_distinct_cases "
        "rejected_runs"
    ).split():
        _require_nonnegative_int(value.get(key), f"evidence index {key}")
    for key in (
        "rejection_passed failure_passed rollback_passed verification_passed "
        "decision_recorded partner_acknowledged operator_acknowledged "
        "commercial_engagement_confirmed ready_to_finalize"
    ).split():
        _require_bool(value.get(key), f"evidence index {key}")
    if value.get("decision") not in ("", "continue", "harden", "defer"):
        raise ValueError("evidence index decision is invalid")
    unmet = value.get("unmet_conditions")
    if not isinstance(unmet, list) or any(type(item) is not str for item in unmet):
        raise ValueError("evidence index unmet conditions must be strings")
    if unmet != [item for item in UNMET_CONDITIONS if item in unmet]:
        raise ValueError("evidence index unmet conditions are invalid")
    if value["ready_to_finalize"] != (unmet == []):
        raise ValueError("evidence index readiness is inconsistent")


def _all_string_leaves(value: object) -> Set[str]:
    leaves: Set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            leaves.update(_all_string_leaves(item))
    elif isinstance(value, list):
        for item in value:
            leaves.update(_all_string_leaves(item))
    elif isinstance(value, str):
        leaves.add(value)
    return leaves


def validate_evidence_pack(pack: Dict[str, object], forbidden_values: List[str]) -> None:
    value = _require_keys(pack, TOP_LEVEL_KEYS, "evidence pack")
    _validate_charter(value["charter"])
    if not isinstance(value["runs"], list):
        raise ValueError("evidence pack runs must be a list")
    for run in value["runs"]:
        _validate_run(run)
    if value["runs"] != sorted(value["runs"], key=_run_sort_key):
        raise ValueError("evidence pack runs are not in stable order")
    exercises = _require_keys(value["exercises"], EXERCISE_SLOT_KEYS, "exercises")
    for name in ("rejection", "failure", "rollback"):
        _validate_exercise(name, exercises[name])
    _validate_verification(value["verification"])
    _validate_decision(value["decision"])
    _validate_index(value["index"])
    if exercises["rejection"] != _rejection_exercise(value["runs"]):
        raise ValueError("rejection exercise does not match the first rejected run")
    expected_summary = build_acceptance_summary(
        value["charter"],
        value["runs"],
        value["index"]["distinct_private_cases"],
        exercises,
        value["verification"],
        value["decision"],
    )
    if any(value["index"].get(key) != item for key, item in expected_summary.items()):
        raise ValueError("evidence index does not match the acceptance summary")
    if not isinstance(forbidden_values, list):
        raise ValueError("forbidden values must be a list")
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    leaf_strings = _all_string_leaves(value)
    for forbidden in forbidden_values:
        if not isinstance(forbidden, str) or not forbidden:
            continue
        if (len(forbidden) >= 4 and forbidden in encoded) or forbidden in leaf_strings:
            raise ValueError("evidence pack contains a forbidden private value")


def _safe_output_path(output_dir: Path) -> Path:
    path = Path(os.path.abspath(os.fspath(output_dir)))
    if path == Path(path.anchor):
        raise ValueError("evidence output must not be a filesystem root")
    for component in reversed((path,) + tuple(path.parents)):
        if component.is_symlink():
            raise ValueError("evidence output must not contain a symbolic link")
    if path.exists() and not path.is_dir():
        raise ValueError("evidence output must be a directory")
    return path


def _write_json_atomic(path: Path, value: object) -> None:
    parent = _safe_output_path(path.parent)
    parent.mkdir(parents=True, exist_ok=True)
    _safe_output_path(parent)
    temporary = path.with_name(f".{path.name}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = None
    try:
        descriptor = os.open(temporary, flags, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(path))
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _remove_stale_json_files(output_dir: Path, expected: Set[Path]) -> None:
    output = _safe_output_path(output_dir)
    if not output.exists():
        return
    expected_paths = {path.absolute() for path in expected}
    for path in output.rglob("*.json"):
        if path.is_symlink() or not path.is_file():
            continue
        candidate = path.absolute()
        if output not in candidate.parents:
            raise ValueError("stale evidence path escapes the output directory")
        if candidate not in expected_paths:
            path.unlink()


def write_evidence_pack(output_dir: Path, pack: Dict[str, object]) -> Dict[str, object]:
    validate_evidence_pack(pack, [])
    output = _safe_output_path(output_dir)
    files = {
        output / "pilot-charter.json": pack["charter"],
        output / "evidence-index.json": pack["index"],
    }
    for sequence, run in enumerate(pack["runs"], start=1):
        files[output / "runs" / f"{sequence:03d}.json"] = run
    for name in ("rejection", "failure", "rollback"):
        exercise = pack["exercises"][name]
        if exercise is not None:
            files[output / "exercises" / f"{name}.json"] = exercise
    if pack["verification"] is not None:
        files[output / "verification.json"] = pack["verification"]
    if pack["decision"] is not None:
        files[output / "decision.json"] = pack["decision"]
    for path in files:
        _safe_output_path(path.parent)
    for path, item in files.items():
        _write_json_atomic(path, item)
    _remove_stale_json_files(output, set(files))
    return {"status": "written", "file_count": len(files), "output_dir": str(output)}
