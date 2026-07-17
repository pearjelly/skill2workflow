"""Fail-closed local operations for the controlled Lark pilot facade."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict
from zoneinfo import ZoneInfo

from ._controlled_lark_pilot_evidence_validation import (
    DECISION_KEYS,
    DECISION_SCHEMA_VERSION,
    EXERCISE_SCHEMA_VERSION,
    VERIFICATION_COMMAND_IDS,
    VERIFICATION_SCHEMA_VERSION,
)
from ._controlled_lark_pilot_evidence_writer import (
    write_private_json_anchored,
)


LIVE_SWITCH = "SKILL2WORKFLOW_LARK_TASK_LIVE"
TOKEN_ENVIRONMENT = "LARK_BOT_ACCESS_TOKEN"
FINALIZATION_SCHEMA_VERSION = "controlled-lark-pilot-finalization-0.1.0"
FINALIZATION_KEYS = {"schema_version", "finalized", "decision", "finalized_at"}


@dataclass(frozen=True)
class Task6Dependencies:
    require_outside_repository: Callable
    load_charter: Callable
    initialize: Callable
    start: Callable
    decide: Callable
    control_plane: Callable
    build_evidence: Callable
    evidence_output: Callable
    prepare_evidence_pack: Callable
    open_private_session: Callable
    finalization_bundle: Callable
    pilot_timezone: str


@contextmanager
def live_environment_removed():
    """Remove the two live variables temporarily and restore their exact state."""
    previous = {
        name: (name in os.environ, os.environ.get(name, ""))
        for name in (LIVE_SWITCH, TOKEN_ENVIRONMENT)
    }
    for name in previous:
        os.environ.pop(name, None)
    try:
        yield
    finally:
        for name, (existed, value) in previous.items():
            if existed:
                os.environ[name] = value
            else:
                os.environ.pop(name, None)


class CredentialResolutionSpy:
    def __init__(self):
        self.calls = []

    def resolve(self, handle: str) -> str:
        self.calls.append(handle)
        raise AssertionError("disabled-live exercise attempted credential resolution")


class TransportSpy:
    def __init__(self):
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append((request, timeout))
        raise AssertionError("safe exercise attempted provider transport")


def persist_exercise(work_dir: Path, name: str, result: Dict[str, object]) -> None:
    artifact = {
        "schema_version": EXERCISE_SCHEMA_VERSION,
        **result,
    }
    write_private_json_anchored(
        Path(work_dir) / "private" / "exercises" / f"{name}.json",
        artifact,
    )


def exercise_disabled_live_operation(
    repo_root: Path,
    work_dir: Path,
    now: datetime,
    dependencies: Task6Dependencies,
) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    dependencies.require_outside_repository(
        repo_root,
        work_dir,
        "pilot work directory",
    )
    charter = dependencies.load_charter(work_dir, now=now)
    provider_status = ""
    credentials = CredentialResolutionSpy()
    transport = TransportSpy()
    with live_environment_removed():
        with tempfile.TemporaryDirectory(
            dir=str(work_dir / "private"),
            prefix=".disabled-live-exercise-",
        ) as temporary:
            exercise_work = Path(temporary) / "pilot"
            case_path = Path(temporary) / "case.json"
            dependencies.initialize(repo_root, exercise_work, charter, now=now)
            write_private_json_anchored(
                case_path,
                {
                    "pilot_case_id": "exercise-disabled-001",
                    "account_name": "Disabled Live Exercise Account",
                    "renewal_risk": "Disabled Live Exercise Risk",
                    "owner_open_id": "ou_disabled_live_exercise",
                    "due_at": "2026-08-15T09:00:00Z",
                },
            )
            started = dependencies.start(
                repo_root,
                exercise_work,
                case_path,
                now=now,
            )
            control = dependencies.control_plane(
                repo_root,
                exercise_work,
                credential_provider=credentials,
                transport=transport,
            )
            control.resume_published_run(started["run_id"], approved=True)
            events = control.list_audit_events(run_id=started["run_id"])
            for event in reversed(events):
                if (
                    isinstance(event, dict)
                    and event.get("node_id") == "create_lark_task"
                    and isinstance(event.get("connector_metadata"), dict)
                ):
                    provider_status = str(
                        event["connector_metadata"].get("provider_status", "")
                    )
                    break
    result = {
        "exercise": "disabled_live",
        "passed": (
            provider_status == "live_disabled"
            and not credentials.calls
            and not transport.calls
        ),
        "provider_status": provider_status,
        "credential_resolution_attempted": bool(credentials.calls),
        "transport_attempted": bool(transport.calls),
    }
    persist_exercise(work_dir, "failure", result)
    return result


def exercise_rollback_operation(
    repo_root: Path,
    work_dir: Path,
    now: datetime,
    dependencies: Task6Dependencies,
) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    dependencies.require_outside_repository(
        repo_root,
        work_dir,
        "pilot work directory",
    )
    if os.environ.get(LIVE_SWITCH) == "1":
        raise ValueError("remove the live switch before running rollback exercise")
    charter = dependencies.load_charter(work_dir, now=now)
    probe_work = work_dir / "private" / "rollback-live-probe"
    transport = TransportSpy()
    with live_environment_removed():
        dependencies.initialize(repo_root, probe_work, charter, now=now)
        case_path = probe_work / "private" / "rollback-case.json"
        write_private_json_anchored(
            case_path,
            {
                "pilot_case_id": "rollback-proof-001",
                "account_name": "Rollback Exercise Account",
                "renewal_risk": "Rollback Exercise Risk",
                "owner_open_id": "ou_rollback_exercise",
                "due_at": "2026-08-15T09:00:00Z",
            },
        )
        started = dependencies.start(
            repo_root,
            probe_work,
            case_path,
            now=now,
        )
        live_approval_blocked = False
        try:
            dependencies.decide(
                repo_root,
                probe_work,
                started["run_id"],
                approved=True,
                confirmed_live=True,
                now=now,
                transport=transport,
            )
        except ValueError as error:
            live_approval_blocked = (
                str(error) == "SKILL2WORKFLOW_LARK_TASK_LIVE=1 is required"
            )
        if not live_approval_blocked or transport.calls:
            raise ValueError("rollback did not prove the disabled live boundary")

        from .lark_task_pilot import run_lark_task_pilot

        dry_run = run_lark_task_pilot(
            repo_root=repo_root,
            work_dir=work_dir / "private" / "rollback-dry-run",
            reset=True,
        )
        result = {
            "exercise": "rollback",
            "passed": (
                live_approval_blocked
                and dry_run.get("run_status") == "completed"
            ),
            "live_switch_enabled": os.environ.get(LIVE_SWITCH) == "1",
            "live_approval_blocked": live_approval_blocked,
            "dry_run_status": str(dry_run.get("run_status", "")),
        }
    persist_exercise(work_dir, "rollback", result)
    return result


def verify_pilot_operation(
    repo_root: Path,
    work_dir: Path,
    command_runner,
    dependencies: Task6Dependencies,
) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    dependencies.require_outside_repository(
        repo_root,
        work_dir,
        "pilot work directory",
    )
    return run_fixed_verification(repo_root, work_dir, command_runner)


def finalize_pilot_operation(
    repo_root: Path,
    work_dir: Path,
    decision: Dict[str, object],
    output_dir: Path,
    now: datetime,
    dependencies: Task6Dependencies,
) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    dependencies.require_outside_repository(
        repo_root,
        work_dir,
        "pilot work directory",
    )
    output, _repository_export = dependencies.evidence_output(
        repo_root,
        work_dir,
        output_dir,
    )
    normalized_decision = validate_final_decision(decision)
    finalized = now or datetime.now(timezone.utc)
    if finalized.tzinfo is None or finalized.utcoffset() is None:
        raise ValueError("pilot finalization time must include a timezone")

    private_output = work_dir / "evidence"
    marker = {
        "schema_version": FINALIZATION_SCHEMA_VERSION,
        "finalized": True,
        "decision": normalized_decision["decision"],
        "finalized_at": finalized.astimezone(
            ZoneInfo(dependencies.pilot_timezone)
        ).isoformat(),
    }
    transactions = []
    with dependencies.open_private_session(
        work_dir / "private"
    ) as private_session:
        bundle = dependencies.finalization_bundle(private_session)
        try:
            pack = dependencies.build_evidence(
                repo_root,
                work_dir,
                decision_override=normalized_decision,
                now=now,
                private_session=private_session,
            )
            private_session.check_identity()
            index = pack.get("index")
            if not isinstance(index, dict):
                raise ValueError("pilot evidence index is invalid")
            if index.get("ready_to_finalize") is not True:
                unmet = index.get("unmet_conditions")
                if not isinstance(unmet, list) or any(
                    type(item) is not str for item in unmet
                ):
                    raise ValueError("pilot evidence unmet conditions are invalid")
                raise ValueError(
                    "pilot evidence is not ready to finalize: " + ", ".join(unmet)
                )

            transactions.append(
                dependencies.prepare_evidence_pack(private_output, pack)
            )
            if output != private_output:
                transactions.append(
                    dependencies.prepare_evidence_pack(output, pack)
                )
            private_session.check_identity()
            for transaction in transactions:
                transaction.commit()
                private_session.check_identity()
            bundle.publish_decision(normalized_decision)
            observed_decision, observed_marker = bundle.publish_marker(marker)
            if observed_decision != normalized_decision or observed_marker != marker:
                raise ValueError("private finalization bundle verification failed")
            private_session.check_identity()
        except BaseException as error:
            rollback_errors = []
            try:
                bundle.rollback()
            except BaseException as rollback_error:
                rollback_errors.append(rollback_error)
            for transaction in reversed(transactions):
                try:
                    transaction.abort()
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            if rollback_errors:
                raise RuntimeError(
                    "controlled pilot finalization rollback failed"
                ) from rollback_errors[0]
            raise error
        else:
            bundle.finish()
            for transaction in transactions:
                transaction.finish()
    return {
        "status": "finalized",
        "decision": normalized_decision["decision"],
        "approved_live_runs": index["approved_live_runs"],
        "distinct_calendar_days": index["distinct_calendar_days"],
        "distinct_private_cases": index["distinct_private_cases"],
        "rejected_runs": index["rejected_runs"],
        "output_dir": str(output),
    }


def validate_final_decision(decision: Dict[str, object]) -> Dict[str, object]:
    if type(decision) is not dict or set(decision) != DECISION_KEYS:
        raise ValueError("pilot decision keys do not match the allowlist")
    if decision.get("schema_version") != DECISION_SCHEMA_VERSION:
        raise ValueError("pilot decision schema is invalid")
    if decision.get("decision") not in ("continue", "harden", "defer"):
        raise ValueError("pilot decision value is invalid")
    for key in (
        "partner_acknowledged",
        "operator_acknowledged",
        "commercial_engagement_confirmed",
    ):
        if decision.get(key) is not True:
            raise ValueError(f"pilot decision {key} must be true")
    rationale = decision.get("rationale")
    if type(rationale) is not str or not rationale.strip():
        raise ValueError("pilot decision rationale must be a nonempty string")
    return json.loads(json.dumps(decision, ensure_ascii=False))


def run_fixed_verification(
    repo_root: Path,
    work_dir: Path,
    command_runner=None,
) -> Dict[str, object]:
    python = sys.executable
    source_files = sorted(
        str(path.relative_to(repo_root))
        for path in (repo_root / "src" / "skill2workflow").glob("*.py")
    )
    commands = [
        (
            "focused-tests",
            [
                python,
                "-m",
                "unittest",
                "tests.test_controlled_lark_pilot",
                "tests.test_controlled_lark_pilot_evidence",
                "tests.test_controlled_lark_pilot_docs",
                "-v",
            ],
        ),
        (
            "full-tests",
            [python, "-m", "unittest", "discover", "-s", "tests", "-v"],
        ),
        (
            "compile",
            [
                python,
                "-m",
                "py_compile",
                *source_files,
                "examples/connectors/lark_task_connector.py",
            ],
        ),
        (
            "secret-hygiene",
            [python, "scripts/secret_hygiene.py", "examples/workflows"],
        ),
        (
            "connector-smoke",
            [
                python,
                "scripts/lark_task_connector_smoke.py",
                "--work-dir",
                str(work_dir / "private" / "connector-smoke"),
            ],
        ),
        (
            "dry-run-pilot-smoke",
            [
                python,
                "scripts/lark_task_pilot_smoke.py",
                "--work-dir",
                str(work_dir / "private" / "dry-run-smoke"),
            ],
        ),
        ("diff-check", ["git", "diff", "--check"]),
    ]
    if tuple(command_id for command_id, _arguments in commands) != VERIFICATION_COMMAND_IDS:
        raise ValueError("fixed verification command identity is invalid")

    environment = dict(os.environ)
    environment.pop(LIVE_SWITCH, None)
    environment.pop(TOKEN_ENVIRONMENT, None)
    environment["PYTHONPATH"] = "src"
    runner = command_runner or subprocess.run
    records = []
    for command_id, arguments in commands:
        started = time.monotonic_ns()
        completed = runner(
            arguments,
            cwd=repo_root,
            env=dict(environment),
            capture_output=True,
        )
        duration_ms = max(0, (time.monotonic_ns() - started) // 1_000_000)
        exit_code = getattr(completed, "returncode", None)
        if type(exit_code) is not int or exit_code < 0:
            raise ValueError("verification runner returned an invalid exit code")
        records.append(
            {
                "id": command_id,
                "exit_code": exit_code,
                "passed": exit_code == 0,
                "duration_ms": duration_ms,
            }
        )
    result = {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "all_passed": all(item["passed"] for item in records),
        "commands": records,
    }
    write_private_json_anchored(
        work_dir / "private" / "verification.json",
        result,
    )
    return result
