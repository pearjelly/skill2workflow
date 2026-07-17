"""Exact schema and cross-pack validation for controlled pilot evidence."""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Dict, List, Set


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
PRESENCE_FIELDS = (
    "task_title_present",
    "task_description_present",
    "assignee_present",
    "due_at_present",
    "idempotency_key_present",
    "lark_task_id_present",
)


def aware_datetime(value: object, label: str, allow_empty: bool = False):
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


def validate_run(run: object) -> None:
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
    started = aware_datetime(value.get("started_at"), "started_at")
    completed = aware_datetime(value.get("completed_at"), "completed_at", allow_empty=True)
    if value["run_status"] in ("completed", "failed", "rejected"):
        if completed is None:
            raise ValueError("completed_at is required for terminal run evidence")
        if completed < started:
            raise ValueError("completed_at must not precede started_at")
    elif completed is not None:
        raise ValueError("completed_at must be empty for nonterminal run evidence")
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
        ) and all(value[field] is False for field in PRESENCE_FIELDS)
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
        if value["passed"] is not True:
            raise ValueError("rejection exercise passed contradicts its facts")
    elif name == "failure":
        if value.get("exercise") != "disabled_live" or value.get("provider_status") not in PROVIDER_STATUSES:
            raise ValueError("failure exercise values are invalid")
        _require_bool(value.get("credential_resolution_attempted"), "failure credential attempt")
        _require_bool(value.get("transport_attempted"), "failure transport attempt")
        fact = bool(
            value["provider_status"] == "live_disabled"
            and value["credential_resolution_attempted"] is False
            and value["transport_attempted"] is False
        )
        if value["passed"] is not fact:
            raise ValueError("failure exercise passed contradicts its facts")
    else:
        if value.get("exercise") != "rollback" or value.get("dry_run_status") not in ("", "completed", "failed"):
            raise ValueError("rollback exercise values are invalid")
        _require_bool(value.get("live_switch_enabled"), "rollback live switch")
        _require_bool(value.get("live_approval_blocked"), "rollback approval")
        fact = bool(
            value["live_switch_enabled"] is False
            and value["live_approval_blocked"] is True
            and value["dry_run_status"] == "completed"
        )
        if value["passed"] is not fact:
            raise ValueError("rollback exercise passed contradicts its facts")


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
    if tuple(seen) != VERIFICATION_COMMAND_IDS:
        raise ValueError("verification must contain the exact seven commands in order")
    if value["all_passed"] != all(command["passed"] for command in commands):
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
    aware_datetime(value.get("generated_at"), "generated_at")
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


def validate_evidence_pack(
    pack: Dict[str, object],
    forbidden_values: List[str],
    run_sort_key: Callable[[Dict[str, object]], tuple],
    rejection_exercise: Callable[[List[Dict[str, object]]], object],
    build_summary: Callable[..., Dict[str, object]],
) -> None:
    value = _require_keys(pack, TOP_LEVEL_KEYS, "evidence pack")
    _validate_charter(value["charter"])
    if not isinstance(value["runs"], list):
        raise ValueError("evidence pack runs must be a list")
    for run in value["runs"]:
        validate_run(run)
    if value["runs"] != sorted(value["runs"], key=run_sort_key):
        raise ValueError("evidence pack runs are not in stable order")
    exercises = _require_keys(value["exercises"], EXERCISE_SLOT_KEYS, "exercises")
    for name in ("rejection", "failure", "rollback"):
        _validate_exercise(name, exercises[name])
    _validate_verification(value["verification"])
    _validate_decision(value["decision"])
    _validate_index(value["index"])
    if exercises["rejection"] != rejection_exercise(value["runs"]):
        raise ValueError("rejection exercise does not match the first rejected run")
    expected_summary = build_summary(
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
    leaf_strings = _all_string_leaves(value)
    for forbidden in forbidden_values:
        if not isinstance(forbidden, str) or not forbidden:
            continue
        if any(forbidden in leaf for leaf in leaf_strings):
            raise ValueError("evidence pack contains a forbidden private value")
