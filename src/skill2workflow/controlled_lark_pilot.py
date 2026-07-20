from __future__ import annotations

import argparse
import json
import os
import secrets
import stat
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo

from .connectors import ConnectorRuntime, ExternalConnector
from .control_plane import LocalControlPlane
from .credentials import StaticCredentialProvider
from ._controlled_lark_pilot_operations import (
    FINALIZATION_KEYS,
    FINALIZATION_SCHEMA_VERSION,
    LIVE_SWITCH,
    TOKEN_ENVIRONMENT,
    Task6Dependencies,
    exercise_disabled_live_operation,
    exercise_rollback_operation,
    finalize_pilot_operation,
    validate_final_decision,
    verify_pilot_operation,
)
from .controlled_lark_pilot_evidence import (
    INDEX_SCHEMA_VERSION,
    _is_approved_live_run,
    _rejection_exercise,
    _run_sort_key,
    build_acceptance_summary,
    build_run_evidence,
    validate_evidence_pack,
    prepare_evidence_pack_transaction,
    write_evidence_pack,
)
from ._controlled_lark_pilot_private_authorization import (
    PrivateFinalizationBundle,
    open_private_session,
)
from ._controlled_lark_pilot_evidence_writer import (
    finish_durable_resources,
    read_json_anchored,
)
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

SOURCE_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_OPERATOR_ERROR = "controlled pilot command failed"
_REJECT_CONFIRMATION_ERROR = (
    "controlled pilot rejection does not use live confirmation"
)


class _OperatorCLIError(Exception):
    def __init__(self, message: str = _OPERATOR_ERROR):
        super().__init__(message)
        self.message = message


class _RedactedArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs["allow_abbrev"] = False
        super().__init__(*args, **kwargs)

    def error(self, message):
        del message
        raise _OperatorCLIError()


def _build_controlled_pilot_parser() -> argparse.ArgumentParser:
    parser = _RedactedArgumentParser(
        prog="controlled_lark_pilot.py",
        description="Operate the fixed controlled Lark/Feishu pilot.",
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=_RedactedArgumentParser,
    )

    initialize = commands.add_parser("init")
    initialize.add_argument("--work-dir", type=Path, required=True)
    initialize.add_argument("--starts-on", required=True)
    initialize.add_argument("--expires-on", required=True)
    initialize.add_argument(
        "--confirm-team-consent",
        action="store_true",
        required=True,
    )
    initialize.add_argument(
        "--confirm-assignee-consent",
        action="store_true",
        required=True,
    )
    initialize.add_argument(
        "--confirm-commercial-engagement",
        action="store_true",
        required=True,
    )

    start = commands.add_parser("start")
    start.add_argument("--work-dir", type=Path, required=True)
    start.add_argument("--input", type=Path, required=True)

    decide = commands.add_parser("decide")
    decide.add_argument("--work-dir", type=Path, required=True)
    decide.add_argument("--run-id", required=True)
    decision = decide.add_mutually_exclusive_group(required=True)
    decision.add_argument("--approve", action="store_true")
    decision.add_argument("--reject", action="store_true")
    decide.add_argument("--confirm-live-create", action="store_true")

    evidence = commands.add_parser("evidence")
    evidence.add_argument("--work-dir", type=Path, required=True)
    evidence.add_argument("--output-dir", type=Path)

    failure = commands.add_parser("exercise-failure")
    failure.add_argument("--work-dir", type=Path, required=True)

    rollback = commands.add_parser("exercise-rollback")
    rollback.add_argument("--work-dir", type=Path, required=True)

    verify = commands.add_parser("verify")
    verify.add_argument("--work-dir", type=Path, required=True)

    finalize = commands.add_parser("finalize")
    finalize.add_argument("--work-dir", type=Path, required=True)
    finalize.add_argument("--decision-file", type=Path, required=True)
    finalize.add_argument("--output-dir", type=Path)
    return parser


def _fixed_charter(arguments) -> Dict[str, object]:
    return {
        "schema_version": PILOT_SCHEMA_VERSION,
        "scenario_id": SCENARIO_ID,
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "support_model": "assisted",
        "timezone": PILOT_TIMEZONE,
        "starts_on": arguments.starts_on,
        "expires_on": arguments.expires_on,
        "team_consent_confirmed": arguments.confirm_team_consent,
        "assignee_consent_confirmed": arguments.confirm_assignee_consent,
        "commercial_engagement_confirmed": (
            arguments.confirm_commercial_engagement
        ),
        "required_approved_runs": 5,
        "required_distinct_days": 5,
        "required_distinct_cases": 2,
    }


def _select_summary_fields(
    result: object,
    fields: Tuple[str, ...],
) -> Dict[str, object]:
    if not isinstance(result, dict):
        raise ValueError("controlled pilot operation returned an invalid summary")
    return {key: result[key] for key in fields if key in result}


def _command_summary(
    command: str,
    result: object,
    charter: Dict[str, object] = None,
) -> Dict[str, object]:
    if command == "init":
        summary = _select_summary_fields(
            result,
            (
                "status",
                "scenario_id",
                "workflow_id",
                "workflow_version",
            ),
        )
        summary.update(
            {
                "team_consent_confirmed": charter["team_consent_confirmed"],
                "assignee_consent_confirmed": charter[
                    "assignee_consent_confirmed"
                ],
                "commercial_engagement_confirmed": charter[
                    "commercial_engagement_confirmed"
                ],
            }
        )
        return summary
    if command == "start":
        return _select_summary_fields(
            result,
            (
                "run_id",
                "workflow_id",
                "workflow_version",
                "run_status",
                "current_node",
                "input_keys",
            ),
        )
    if command == "decide":
        return _select_summary_fields(
            result,
            (
                "run_id",
                "workflow_id",
                "workflow_version",
                "run_status",
                "gate_decision",
                "connector_invoked",
                "connector_status",
                "credential_status",
                "provider_status",
                "idempotency_key_present",
                "lark_task_id_present",
            ),
        )
    if command == "evidence":
        return _select_summary_fields(
            result,
            (
                "status",
                "file_count",
                "run_count",
                "approved_live_runs",
                "distinct_calendar_days",
                "distinct_private_cases",
                "rejected_runs",
                "unmet_conditions",
            ),
        )
    if command == "exercise-failure":
        return _select_summary_fields(
            result,
            (
                "exercise",
                "passed",
                "provider_status",
                "credential_resolution_attempted",
                "transport_attempted",
            ),
        )
    if command == "exercise-rollback":
        return _select_summary_fields(
            result,
            (
                "exercise",
                "passed",
                "live_switch_enabled",
                "live_approval_blocked",
                "dry_run_status",
            ),
        )
    if command == "verify":
        summary = _select_summary_fields(result, ("all_passed",))
        commands = result.get("commands", [])
        if not isinstance(commands, list):
            raise ValueError("controlled pilot verification summary is invalid")
        summary["commands"] = [
            _select_summary_fields(
                item,
                ("id", "exit_code", "passed", "duration_ms"),
            )
            for item in commands
        ]
        return summary
    if command == "finalize":
        return _select_summary_fields(
            result,
            (
                "status",
                "decision",
                "approved_live_runs",
                "distinct_calendar_days",
                "distinct_private_cases",
                "rejected_runs",
            ),
        )
    raise ValueError("controlled pilot command is invalid")


def _load_private_decision(decision_file: Path) -> Dict[str, object]:
    declared = Path(os.path.abspath(os.fspath(decision_file)))
    _require_outside_repository(
        SOURCE_REPOSITORY_ROOT,
        declared,
        "private decision file",
    )
    _require_outside_repository(
        SOURCE_REPOSITORY_ROOT,
        declared.resolve(),
        "private decision file",
    )
    value = read_json_anchored(declared, owner_only=True)
    if not isinstance(value, dict):
        raise ValueError("private decision file must contain a JSON object")
    return value


def _dispatch_controlled_pilot(arguments) -> Tuple[Dict[str, object], object]:
    command = arguments.command
    if command == "init":
        charter = _fixed_charter(arguments)
        result = initialize_pilot(
            SOURCE_REPOSITORY_ROOT,
            arguments.work_dir,
            charter,
        )
        return _command_summary(command, result, charter=charter), result
    if command == "start":
        result = start_pilot_run(
            SOURCE_REPOSITORY_ROOT,
            arguments.work_dir,
            arguments.input,
        )
    elif command == "decide":
        if arguments.reject and arguments.confirm_live_create:
            raise _OperatorCLIError(_REJECT_CONFIRMATION_ERROR)
        result = decide_pilot_run(
            SOURCE_REPOSITORY_ROOT,
            arguments.work_dir,
            arguments.run_id,
            approved=bool(arguments.approve),
            confirmed_live=bool(arguments.confirm_live_create),
        )
    elif command == "evidence":
        result = generate_pilot_evidence(
            SOURCE_REPOSITORY_ROOT,
            arguments.work_dir,
            output_dir=arguments.output_dir,
        )
    elif command == "exercise-failure":
        result = exercise_disabled_live(
            SOURCE_REPOSITORY_ROOT,
            arguments.work_dir,
        )
    elif command == "exercise-rollback":
        result = exercise_rollback(
            SOURCE_REPOSITORY_ROOT,
            arguments.work_dir,
        )
    elif command == "verify":
        result = verify_pilot(
            SOURCE_REPOSITORY_ROOT,
            arguments.work_dir,
        )
    elif command == "finalize":
        decision = _load_private_decision(arguments.decision_file)
        result = finalize_pilot(
            SOURCE_REPOSITORY_ROOT,
            arguments.work_dir,
            decision,
            output_dir=arguments.output_dir,
        )
    else:
        raise _OperatorCLIError()
    return _command_summary(command, result), result


def main(argv=None) -> int:
    try:
        arguments = _build_controlled_pilot_parser().parse_args(argv)
        summary, _result = _dispatch_controlled_pilot(arguments)
    except _OperatorCLIError as error:
        print(error.message, file=sys.stderr)
        return 2
    except (OSError, RuntimeError, ValueError):
        print(_OPERATOR_ERROR, file=sys.stderr)
        return 1
    print(
        json.dumps(summary, ensure_ascii=False, separators=(",", ":")),
        flush=True,
    )
    return 0


def _task6_dependencies() -> Task6Dependencies:
    return Task6Dependencies(
        require_outside_repository=_require_outside_repository,
        load_charter=load_pilot_charter,
        initialize=initialize_pilot,
        start=start_pilot_run,
        decide=decide_pilot_run,
        control_plane=_pilot_control_plane,
        build_evidence=_build_pilot_evidence,
        evidence_output=_evidence_output,
        prepare_evidence_pack=prepare_evidence_pack_transaction,
        open_private_session=open_private_session,
        finalization_bundle=PrivateFinalizationBundle,
        pilot_timezone=PILOT_TIMEZONE,
    )


def exercise_disabled_live(
    repo_root: Path,
    work_dir: Path,
    now: datetime = None,
) -> Dict[str, object]:
    return exercise_disabled_live_operation(
        repo_root,
        work_dir,
        now,
        _task6_dependencies(),
    )


def exercise_rollback(
    repo_root: Path,
    work_dir: Path,
    now: datetime = None,
) -> Dict[str, object]:
    return exercise_rollback_operation(
        repo_root,
        work_dir,
        now,
        _task6_dependencies(),
    )


def verify_pilot(
    repo_root: Path,
    work_dir: Path,
    command_runner=None,
) -> Dict[str, object]:
    return verify_pilot_operation(
        repo_root,
        work_dir,
        command_runner,
        _task6_dependencies(),
    )


def finalize_pilot(
    repo_root: Path,
    work_dir: Path,
    decision: Dict[str, object],
    output_dir: Path = None,
    now: datetime = None,
) -> Dict[str, object]:
    return finalize_pilot_operation(
        repo_root,
        work_dir,
        decision,
        output_dir,
        now,
        _task6_dependencies(),
    )


def generate_pilot_evidence(
    repo_root: Path,
    work_dir: Path,
    output_dir: Path = None,
    now: datetime = None,
) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    _require_outside_repository(repo_root, work_dir, "pilot work directory")
    output, repository_export = _evidence_output(repo_root, work_dir, output_dir)
    if repository_export:
        private_session = open_private_session(work_dir / "private")
        authorization_snapshot = None
        transaction = None
        durable_success = False
        try:
            try:
                authorization_snapshot = (
                    private_session.authorization_bundle_snapshot()
                )
            except FileNotFoundError as error:
                raise ValueError(
                    "successful private finalization is required for repository export"
                ) from error
            decision = authorization_snapshot.decision
            marker = authorization_snapshot.marker
            authorization_snapshot.validate()
            private_session.check_identity()
            pack = _build_pilot_evidence(
                repo_root,
                work_dir,
                decision_override=decision,
                now=now,
                private_session=private_session,
                historical_authorization=(decision, marker),
            )
            _require_finalized_export(pack, marker, decision)
            authorization_snapshot.validate()
            transaction = prepare_evidence_pack_transaction(output, pack)
            authorization_snapshot.validate()
            transaction.commit()
            transaction.validate_durable_commit()
            private_session.check_identity()
            authorization_snapshot.validate()

            # Irreversible durable-success commit point for repository export.
            durable_success = True
            written = {
                "status": "written",
                "file_count": transaction.file_count,
                "output_dir": str(transaction.output),
            }
        except BaseException:
            cleanup_errors = []
            if transaction is not None:
                try:
                    transaction.abort()
                except BaseException as cleanup_error:
                    cleanup_errors.append(cleanup_error)
            if authorization_snapshot is not None:
                try:
                    authorization_snapshot.close()
                except BaseException as cleanup_error:
                    cleanup_errors.append(cleanup_error)
            try:
                private_session.close()
            except BaseException as cleanup_error:
                cleanup_errors.append(cleanup_error)
            if cleanup_errors:
                raise RuntimeError(
                    "repository evidence export rollback failed"
                ) from cleanup_errors[0]
            raise
        if durable_success:
            finish_durable_resources(
                (authorization_snapshot, "close"),
                (transaction, "finish"),
                (private_session, "close"),
            )
    else:
        pack = _build_pilot_evidence(repo_root, work_dir, now=now)
        written = write_evidence_pack(output, pack)
    index = pack["index"]
    return {
        "status": written["status"],
        "file_count": written["file_count"],
        "run_count": len(pack["runs"]),
        "approved_live_runs": index["approved_live_runs"],
        "distinct_calendar_days": index["distinct_calendar_days"],
        "distinct_private_cases": index["distinct_private_cases"],
        "rejected_runs": index["rejected_runs"],
        "unmet_conditions": list(index["unmet_conditions"]),
        "output_dir": written["output_dir"],
    }


def _build_pilot_evidence(
    repo_root: Path,
    work_dir: Path,
    decision_override: Dict[str, object] = None,
    now: datetime = None,
    private_session=None,
    historical_authorization=None,
) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    _require_outside_repository(repo_root, work_dir, "pilot work directory")
    if historical_authorization is None:
        charter = load_pilot_charter(work_dir, now=now)
    else:
        if private_session is None:
            raise ValueError("historical charter requires private authorization")
        authorization_decision, authorization_marker = historical_authorization
        private_session.check_identity()
        charter = _validate_historical_repository_charter(
            private_session.read_json(Path("charter.json")),
            authorization_decision,
            authorization_marker,
            now=now,
        )
        private_session.check_identity()
    control = _pilot_control_plane(
        repo_root,
        work_dir,
        credential_provider=StaticCredentialProvider({}),
    )
    private_runs = []
    forbidden_values: List[str] = []
    for summary in control.list_runs():
        if (
            not isinstance(summary, dict)
            or summary.get("workflow_id") != WORKFLOW_ID
            or summary.get("workflow_version") != WORKFLOW_VERSION
        ):
            continue
        requested_run_id = str(summary.get("run_id", ""))
        run = control.get_run(requested_run_id)
        if not isinstance(run, dict) or run.get("run_id") != requested_run_id:
            raise ValueError("controlled pilot run identity is invalid")
        audit = control.list_audit_events(run_id=requested_run_id)
        evidence = build_run_evidence(run, audit)
        private_runs.append((evidence, run))
        context = run.get("context", {})
        trigger_input = context.get("input", {}) if isinstance(context, dict) else {}
        forbidden_values.extend(_private_string_values(trigger_input))
    private_runs.sort(key=lambda item: _run_sort_key(item[0]))
    runs = [item[0] for item in private_runs]
    private_case_ids = set()
    for evidence, run in private_runs:
        if not _is_approved_live_run(evidence):
            continue
        context = run.get("context", {})
        trigger_input = context.get("input", {}) if isinstance(context, dict) else {}
        case_id = trigger_input.get("pilot_case_id", "") if isinstance(trigger_input, dict) else ""
        if isinstance(case_id, str) and case_id.strip():
            private_case_ids.add(case_id)
    distinct_private_cases = len(private_case_ids)
    del private_case_ids
    del private_runs

    private_dir = work_dir / "private"
    exercise_dir = private_dir / "exercises"
    if private_session is not None:
        private_session.check_identity()
    exercises = {
        "rejection": _rejection_exercise(runs),
        "failure": (
            private_session.read_json(Path("exercises/failure.json"), required=False)
            if private_session is not None
            else _load_optional_private_json(exercise_dir / "failure.json")
        ),
        "rollback": (
            private_session.read_json(Path("exercises/rollback.json"), required=False)
            if private_session is not None
            else _load_optional_private_json(exercise_dir / "rollback.json")
        ),
    }
    verification = (
        private_session.read_json(Path("verification.json"), required=False)
        if private_session is not None
        else _load_optional_private_json(private_dir / "verification.json")
    )
    decision = (
        json.loads(json.dumps(decision_override, ensure_ascii=False))
        if decision_override is not None
        else (
            private_session.read_json(Path("decision.json"), required=False)
            if private_session is not None
            else _load_optional_private_json(private_dir / "decision.json")
        )
    )
    if private_session is not None:
        private_session.check_identity()
    summary = build_acceptance_summary(
        charter,
        runs,
        distinct_private_cases,
        exercises,
        verification,
        decision,
    )
    generated = now or datetime.now(timezone.utc)
    if generated.tzinfo is None or generated.utcoffset() is None:
        raise ValueError("evidence generation time must include a timezone")
    index = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "generated_at": generated.astimezone(ZoneInfo(PILOT_TIMEZONE)).isoformat(),
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "timezone": PILOT_TIMEZONE,
        **summary,
    }
    pack = {
        "charter": charter,
        "runs": runs,
        "exercises": exercises,
        "verification": verification,
        "decision": decision,
        "index": index,
    }
    validate_evidence_pack(pack, forbidden_values)
    return pack


def _private_string_values(value: object) -> List[str]:
    values: List[str] = []
    if isinstance(value, dict):
        for item in value.values():
            values.extend(_private_string_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_private_string_values(item))
    elif isinstance(value, str) and value:
        values.append(value)
    return values


def _load_optional_private_json(path: Path):
    try:
        value = read_json_anchored(path)
    except FileNotFoundError:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"private pilot artifact {path.name} must be an object")
    return value


def _evidence_output(
    repo_root: Path, work_dir: Path, output_dir: Path
) -> Tuple[Path, bool]:
    if output_dir is None:
        return work_dir / "evidence", False
    output = Path(os.path.abspath(os.fspath(output_dir)))
    resolved = output.resolve()
    declared_in_repository = output == repo_root or repo_root in output.parents
    resolved_in_repository = resolved == repo_root or repo_root in resolved.parents
    if not declared_in_repository and not resolved_in_repository:
        return output, False
    allowed = repo_root / "docs" / "pilot-evidence" / "loop-40"
    if output != allowed or resolved != allowed:
        raise ValueError("repository evidence output must equal docs/pilot-evidence/loop-40")
    return output, True


def _require_finalized_export(
    pack: Dict[str, object],
    marker: object,
    decision: object,
) -> None:
    _validate_finalization_marker(marker)
    pack_decision = pack.get("decision")
    index = pack.get("index")
    if (
        not isinstance(decision, dict)
        or marker["decision"] != decision.get("decision")
        or decision != pack_decision
        or not isinstance(index, dict)
        or index.get("ready_to_finalize") is not True
    ):
        raise ValueError("private finalization does not authorize this evidence pack")


def _validate_finalization_marker(marker: object) -> datetime:
    if not isinstance(marker, dict) or set(marker) != FINALIZATION_KEYS:
        raise ValueError("private finalization marker is invalid")
    if (
        marker.get("schema_version") != FINALIZATION_SCHEMA_VERSION
        or marker.get("finalized") is not True
        or marker.get("decision") not in ("continue", "harden", "defer")
    ):
        raise ValueError("private finalization marker is invalid")
    return _require_aware_iso(
        marker.get("finalized_at"),
        "private finalization timestamp",
    )


def _require_aware_iso(value: object, label: str) -> datetime:
    if type(value) is not str:
        raise ValueError(f"{label} must be an ISO timestamp with timezone")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{label} must be an ISO timestamp with timezone") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must be an ISO timestamp with timezone")
    return parsed


def decide_pilot_run(
    repo_root: Path,
    work_dir: Path,
    run_id: str,
    approved: bool,
    confirmed_live: bool = False,
    now: datetime = None,
    transport=None,
) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    _require_outside_repository(repo_root, work_dir, "pilot work directory")
    if type(approved) is not bool:
        raise ValueError("approved must be a boolean")
    load_pilot_charter(work_dir, now=now)

    preflight = _pilot_control_plane(
        repo_root,
        work_dir,
        credential_provider=StaticCredentialProvider({}),
    )
    requested_run_id = str(run_id)
    current = preflight.get_run(requested_run_id)
    if (
        not isinstance(current, dict)
        or current.get("run_id") != requested_run_id
    ):
        raise ValueError("controlled pilot run identity is invalid")
    workflow = preflight.get_workflow(WORKFLOW_ID, WORKFLOW_VERSION)
    _validate_controlled_live_binding(workflow, current)

    token = ""
    if approved:
        if type(confirmed_live) is not bool or confirmed_live is not True:
            raise ValueError("live approval requires explicit boolean confirmation")
        if os.environ.get(LIVE_SWITCH) != "1":
            raise ValueError("SKILL2WORKFLOW_LARK_TASK_LIVE=1 is required")
        token = os.environ.get(TOKEN_ENVIRONMENT, "")
        if not token:
            raise ValueError("LARK_BOT_ACCESS_TOKEN is required")

    credentials = {"lark_bot_access_token": token} if approved else {}
    control = _pilot_control_plane(
        repo_root,
        work_dir,
        credential_provider=StaticCredentialProvider(credentials),
        transport=transport,
    )
    state = control.resume_published_run(requested_run_id, approved=approved)
    events = control.list_audit_events(run_id=requested_run_id)
    connector_events = [
        event
        for event in events
        if event.get("type")
        in ("connector_started", "connector_completed", "connector_failed")
        and event.get("node_id") == "create_lark_task"
    ]
    connector_metadata = {}
    for event in reversed(connector_events):
        metadata = event.get("connector_metadata")
        if isinstance(metadata, dict):
            connector_metadata = metadata
            break
    return {
        "run_id": requested_run_id,
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "run_status": str(state.get("status", "")),
        "gate_decision": "approved" if approved else "rejected",
        "connector_invoked": bool(connector_events),
        "connector_status": (
            str(connector_events[-1].get("connector_status", ""))
            if connector_events
            else ""
        ),
        "credential_status": (
            str(connector_events[-1].get("credential_status", ""))
            if connector_events
            else ""
        ),
        "provider_status": str(connector_metadata.get("provider_status", "")),
        "idempotency_key_present": bool(
            connector_metadata.get("idempotency_key_present")
        ),
        "lark_task_id_present": bool(
            connector_metadata.get("lark_task_id_present")
        ),
    }


def _validate_controlled_live_binding(
    workflow: Dict[str, object],
    run: Dict[str, object],
) -> None:
    invalid = "controlled pilot live binding is invalid"
    if not isinstance(workflow, dict) or not isinstance(run, dict):
        raise ValueError(invalid)
    if run.get("status") != "waiting":
        raise ValueError("controlled pilot run is not waiting")

    metadata = workflow.get("workflow")
    if not isinstance(metadata, dict):
        raise ValueError(invalid)
    if (
        metadata.get("id") != WORKFLOW_ID
        or metadata.get("version") != WORKFLOW_VERSION
        or run.get("workflow_id") != WORKFLOW_ID
        or run.get("workflow_version") != WORKFLOW_VERSION
    ):
        raise ValueError(invalid)
    if not isinstance(run.get("run_id"), str) or not str(run["run_id"]).strip():
        raise ValueError(invalid)
    if run.get("current_node") != "review_renewal_risk":
        raise ValueError(invalid)

    expected_workflow = build_lark_task_pilot_workflow(
        mode="live",
        workflow_id=WORKFLOW_ID,
        workflow_version=WORKFLOW_VERSION,
        workflow_name="controlled-lark-task-sales-renewal-pilot",
    )
    expected_workflow["workflow"]["status"] = "published"
    if workflow != expected_workflow:
        raise ValueError(invalid)
    durable_workflow = run.get("workflow")
    if not isinstance(durable_workflow, dict) or durable_workflow != workflow:
        raise ValueError(invalid)


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
    work_dir = Path(os.path.abspath(os.fspath(work_dir)))
    path = work_dir / "private" / "charter.json"
    payload = read_json_anchored(path)
    return _validate_charter(payload, now=now)


def load_private_case(repo_root: Path, input_path: Path) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    input_path = Path(os.path.abspath(os.fspath(input_path)))
    resolved_input = input_path.resolve()
    _require_outside_repository(repo_root, input_path, "private case input")
    _require_outside_repository(repo_root, resolved_input, "private case input")
    payload = read_json_anchored(input_path, owner_only=True)
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
    normalized = _validate_charter_schema_and_range(charter)
    _require_active_charter_window(normalized, now=now)
    return normalized


def _validate_charter_schema_and_range(charter: object) -> Dict[str, object]:
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
    if starts_on > expires_on:
        raise ValueError("pilot charter date range is invalid")
    return normalized


def _require_active_charter_window(
    charter: Dict[str, object],
    now: datetime = None,
) -> None:
    starts_on = date.fromisoformat(charter["starts_on"])
    expires_on = date.fromisoformat(charter["expires_on"])
    current = (now or datetime.now(timezone.utc)).astimezone(
        ZoneInfo(PILOT_TIMEZONE)
    ).date()
    if current < starts_on:
        raise ValueError("pilot charter has not started")
    if current > expires_on:
        raise ValueError("pilot charter expired")


def _validate_historical_repository_charter(
    charter: object,
    decision: object,
    marker: object,
    now: datetime = None,
) -> Dict[str, object]:
    normalized = _validate_charter_schema_and_range(charter)
    starts_on = date.fromisoformat(normalized["starts_on"])
    expires_on = date.fromisoformat(normalized["expires_on"])
    current = (now or datetime.now(timezone.utc)).astimezone(
        ZoneInfo(PILOT_TIMEZONE)
    ).date()
    if current < starts_on:
        raise ValueError("pilot charter has not started")
    if current <= expires_on:
        return normalized

    normalized_decision = validate_final_decision(decision)
    finalized_at = _validate_finalization_marker(marker)
    if marker["decision"] != normalized_decision["decision"]:
        raise ValueError("private finalization marker is invalid")
    finalized_on = finalized_at.astimezone(ZoneInfo(PILOT_TIMEZONE)).date()
    if not starts_on <= finalized_on <= expires_on:
        raise ValueError(
            "private finalization does not authorize an expired pilot charter"
        )
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
