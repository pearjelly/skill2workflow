"""Public facade and pure builders for controlled Lark pilot evidence."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Set
from zoneinfo import ZoneInfo

from ._controlled_lark_pilot_evidence_validation import (
    CHARTER_KEYS,
    CONNECTOR_ID,
    CREDENTIAL_HANDLE,
    DECISION_KEYS,
    DECISION_SCHEMA_VERSION,
    EVIDENCE_SCHEMA_VERSION,
    EXERCISE_SCHEMA_VERSION,
    EXERCISE_SLOT_KEYS,
    FAILURE_EXERCISE_KEYS,
    INDEX_KEYS,
    INDEX_SCHEMA_VERSION,
    MODE,
    OPERATION,
    PRESENCE_FIELDS,
    PROVIDER_STATUSES,
    REJECTION_EXERCISE_KEYS,
    ROLLBACK_EXERCISE_KEYS,
    RUN_EVIDENCE_KEYS,
    TIMEZONE,
    TOP_LEVEL_KEYS,
    UNMET_CONDITIONS,
    VERIFICATION_COMMAND_IDS,
    VERIFICATION_COMMAND_KEYS,
    VERIFICATION_KEYS,
    VERIFICATION_SCHEMA_VERSION,
    WORKFLOW_ID,
    WORKFLOW_VERSION,
    aware_datetime as _aware_datetime,
    validate_evidence_pack as _validate_evidence_pack,
    validate_run as _validate_run,
)
from ._controlled_lark_pilot_evidence_writer import (
    write_evidence_pack as _write_evidence_pack,
)


CONNECTOR_EVENT_TYPES = (
    "connector_started",
    "connector_failed",
    "connector_completed",
)
TERMINAL_EVENT_TYPES = ("run_completed", "run_failed", "run_rejected")


def _indexed_events(events: List[Dict[str, object]], event_types: tuple) -> list:
    return [
        (index, event)
        for index, event in enumerate(events)
        if isinstance(event, dict) and event.get("type") in event_types
    ]


def _raw_string(value: object, label: str, nonempty: bool = False) -> str:
    if type(value) is not str or (nonempty and not value.strip()):
        suffix = " nonempty" if nonempty else ""
        raise ValueError(f"{label} must be a{suffix} string")
    return value


def _bound_event(event: object, run_id: str, label: str) -> datetime:
    if not isinstance(event, dict) or event.get("run_id") != run_id:
        raise ValueError(f"{label} must be bound to the controlled run")
    return _aware_datetime(event.get("timestamp"), f"{label} timestamp")


def _bound_event_in_window(
    event: object,
    run_id: str,
    label: str,
    started_at: datetime,
    completed_at: datetime,
) -> datetime:
    timestamp = _bound_event(event, run_id, label)
    if timestamp < started_at or timestamp > completed_at:
        raise ValueError(f"{label} timestamp must be within the run interval")
    return timestamp


def _validate_connector_sequence(
    candidates: list,
    retrying: list,
    run_id: str,
    resume_index: int,
    terminal_index: int,
    started_at: datetime,
    completed_at: datetime,
) -> Dict[str, object]:
    completed = {}
    attempt_open = False
    for index, event in candidates:
        if event.get("node_id") != "create_lark_task":
            raise ValueError("connector event must target the controlled node")
        if not resume_index < index < terminal_index:
            raise ValueError("connector event is out of semantic audit order")
        event_type = event["type"]
        _bound_event_in_window(
            event,
            run_id,
            event_type,
            started_at,
            completed_at,
        )
        connector_id = _raw_string(event.get("connector_id"), "connector id")
        if connector_id != CONNECTOR_ID:
            raise ValueError("connector event identity is invalid")
        connector_status = _raw_string(
            event.get("connector_status"), "connector status"
        )
        expected_status = {
            "connector_started": "running",
            "connector_failed": "failed",
            "connector_completed": "completed",
        }[event_type]
        if connector_status != expected_status:
            raise ValueError(f"{event_type} has an invalid connector status")
        if completed:
            raise ValueError("connector events must not follow connector completion")
        if event_type == "connector_started":
            if attempt_open:
                raise ValueError("connector attempt cannot start twice")
            attempt_open = True
        elif event_type == "connector_failed":
            if not attempt_open:
                raise ValueError("connector failure must follow a started attempt")
            attempt_open = False
        else:
            if not attempt_open:
                raise ValueError("connector completion must follow a started attempt")
            attempt_open = False
            completed = event
    if attempt_open:
        raise ValueError("connector attempt is missing a terminal connector event")

    expected_retry_pairs = {
        (previous[0], following[0])
        for previous, following in zip(candidates, candidates[1:])
        if previous[1].get("type") == "connector_failed"
        and following[1].get("type") == "connector_started"
    }
    retry_pairs = set()
    for index, event in retrying:
        if event.get("node_id") != "create_lark_task":
            raise ValueError("retry event must target the controlled node")
        if not resume_index < index < terminal_index:
            raise ValueError("retry event is out of semantic audit order")
        _bound_event_in_window(
            event,
            run_id,
            "node_retrying",
            started_at,
            completed_at,
        )
        previous = [item for item in candidates if item[0] < index]
        following = [item for item in candidates if item[0] > index]
        if (
            not previous
            or previous[-1][1].get("type") != "connector_failed"
            or not following
            or following[0][1].get("type") != "connector_started"
        ):
            raise ValueError("node_retrying must separate failed and started attempts")
        pair = (previous[-1][0], following[0][0])
        if pair in retry_pairs:
            raise ValueError("connector retry transition must not be duplicated")
        retry_pairs.add(pair)
    if retry_pairs != expected_retry_pairs:
        raise ValueError("connector retry events must exactly match retry transitions")
    return completed


def build_run_evidence(
    run: Dict[str, object], audit_events: List[Dict[str, object]]
) -> Dict[str, object]:
    if not isinstance(run, dict):
        raise ValueError("run must be an object")
    if not isinstance(audit_events, list):
        raise ValueError("audit events must be a list")
    run_id = _raw_string(run.get("run_id"), "run_id", nonempty=True)
    workflow_id = _raw_string(run.get("workflow_id"), "workflow_id")
    workflow_version = _raw_string(run.get("workflow_version"), "workflow_version")
    run_status = _raw_string(run.get("status"), "run status")

    started_events = _indexed_events(audit_events, ("run_started",))
    if len(started_events) != 1:
        raise ValueError("exactly one run_started event is required")
    started_index, started_event = started_events[0]
    started_at = _bound_event(started_event, run_id, "run_started")

    terminal_events = _indexed_events(audit_events, TERMINAL_EVENT_TYPES)
    expected_terminal = (
        "run_completed"
        if run_status == "completed"
        else "run_failed"
        if run_status in ("failed", "rejected")
        else ""
    )
    if expected_terminal:
        if (
            len(terminal_events) != 1
            or terminal_events[0][1].get("type") != expected_terminal
        ):
            raise ValueError("terminal event does not match the run status")
        terminal_index, terminal = terminal_events[0]
        completed_at = _bound_event(terminal, run_id, expected_terminal)
        if terminal_index <= started_index or completed_at < started_at:
            raise ValueError("terminal timestamp must not precede run_started")
    else:
        if terminal_events:
            raise ValueError("nonterminal run must not have a terminal event")
        terminal_index = len(audit_events)
        completed_at = started_at
        terminal = {}

    resumed_events = _indexed_events(audit_events, ("run_resumed",))
    connector_events = _indexed_events(audit_events, CONNECTOR_EVENT_TYPES)
    retrying_events = _indexed_events(audit_events, ("node_retrying",))
    if expected_terminal:
        if len(resumed_events) != 1:
            raise ValueError("exactly one run_resumed event is required")
        resume_index, resumed = resumed_events[0]
        _bound_event_in_window(
            resumed,
            run_id,
            "run_resumed",
            started_at,
            completed_at,
        )
        if not started_index < resume_index < terminal_index:
            raise ValueError("run_resumed is out of semantic audit order")
        if type(resumed.get("approved")) is not bool:
            raise ValueError("run_resumed approved must be a boolean")
    else:
        if resumed_events or connector_events or retrying_events:
            raise ValueError("waiting run must not contain decision or connector events")
        resume_index = terminal_index
        resumed = {}

    completed_connector = (
        _validate_connector_sequence(
            connector_events,
            retrying_events,
            run_id,
            resume_index,
            terminal_index,
            started_at,
            completed_at,
        )
        if connector_events or retrying_events
        else {}
    )
    if resumed.get("approved") is False:
        if run_status not in ("failed", "rejected") or connector_events:
            raise ValueError("rejected run must fail without connector events")
    elif resumed.get("approved") is True:
        if run_status == "completed":
            if not completed_connector:
                raise ValueError("completed approved run requires connector completion")
        elif not connector_events or completed_connector:
            raise ValueError("failed approved run requires connector failure")

    connector = completed_connector or (
        connector_events[-1][1] if connector_events else {}
    )
    metadata = connector.get("connector_metadata", {}) if completed_connector else {}
    context = run.get("context", {})
    if not isinstance(context, dict):
        context = {}
    trigger_input = context.get("input", {})
    if not isinstance(trigger_input, dict):
        trigger_input = {}
    case_id = trigger_input.get("pilot_case_id")
    if type(case_id) is not str or not case_id.strip():
        raise ValueError("pilot_case_id must be a nonempty string")

    raw_handles = connector.get("credential_handles", []) if connector else []
    if type(raw_handles) is not list or any(
        type(item) is not str for item in raw_handles
    ):
        raise ValueError("credential handles must be a list of strings")
    handles = list(raw_handles)
    if completed_connector:
        if not isinstance(metadata, dict):
            raise ValueError("connector metadata must be an object")
        for field in PRESENCE_FIELDS:
            if type(metadata.get(field)) is not bool:
                raise ValueError(f"connector presence field {field} must be a boolean")
        operation = _raw_string(metadata.get("operation"), "connector operation")
        mode = _raw_string(metadata.get("mode"), "connector mode")
        provider_status = _raw_string(
            metadata.get("provider_status"), "provider status"
        )
        connector_id = _raw_string(connector.get("connector_id"), "connector id")
        connector_status = _raw_string(
            connector.get("connector_status"), "connector status"
        )
        credential_status = _raw_string(
            connector.get("credential_status"), "credential status"
        )
    elif connector:
        operation = mode = provider_status = ""
        connector_id = _raw_string(connector.get("connector_id"), "connector id")
        connector_status = _raw_string(
            connector.get("connector_status"), "connector status"
        )
        credential_status = (
            _raw_string(connector.get("credential_status"), "credential status")
            if "credential_status" in connector
            else ""
        )
    else:
        operation = mode = provider_status = ""
        connector_id = connector_status = credential_status = ""

    evidence = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "run_id": run_id,
        "workflow_id": workflow_id,
        "workflow_version": workflow_version,
        "started_at": started_event["timestamp"],
        "completed_at": terminal.get("timestamp", ""),
        "run_status": run_status,
        "gate_decision": (
            "approved"
            if resumed.get("approved") is True
            else "rejected"
            if resumed.get("approved") is False
            else "pending"
        ),
        "case_id_present": True,
        "connector_invoked": bool(connector),
        "connector_id": connector_id,
        "connector_status": connector_status,
        "credential_status": credential_status,
        "credential_handles": handles,
        "operation": operation,
        "mode": mode,
        "provider_status": provider_status,
        **{
            field: metadata[field] if completed_connector else False
            for field in PRESENCE_FIELDS
        },
    }
    _validate_run(evidence)
    if run_status == "completed" and not _is_approved_live_run(evidence):
        raise ValueError("completed approved run has invalid success facts")
    return evidence


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
    if not (
        isinstance(run, dict)
        and run.get("workflow_id") == WORKFLOW_ID
        and run.get("workflow_version") == WORKFLOW_VERSION
        and run.get("run_status") in ("failed", "rejected")
        and run.get("gate_decision") == "rejected"
        and run.get("connector_invoked") is False
    ):
        return False
    try:
        started = _aware_datetime(run.get("started_at"), "started_at")
        completed = _aware_datetime(run.get("completed_at"), "completed_at")
    except ValueError:
        return False
    return completed >= started


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
    return (
        _aware_datetime(run.get("started_at"), "started_at"),
        run.get("run_id", ""),
    )


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


def validate_evidence_pack(
    pack: Dict[str, object], forbidden_values: List[str]
) -> None:
    _validate_evidence_pack(
        pack,
        forbidden_values,
        _run_sort_key,
        _rejection_exercise,
        build_acceptance_summary,
    )


def write_evidence_pack(output_dir: Path, pack: Dict[str, object]) -> Dict[str, object]:
    validate_evidence_pack(pack, [])
    return _write_evidence_pack(output_dir, pack)
