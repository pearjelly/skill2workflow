import json
import os
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.controlled_lark_pilot import (
    decide_pilot_run,
    generate_pilot_evidence,
    initialize_pilot,
    start_pilot_run,
)
from skill2workflow.controlled_lark_pilot_evidence import (
    RUN_EVIDENCE_KEYS,
    build_acceptance_summary,
    build_run_evidence,
    validate_evidence_pack,
    write_evidence_pack,
)


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc)


class _FakeResponse:
    status = 200

    def read(self):
        return json.dumps(
            {
                "code": 0,
                "msg": "private-provider-message",
                "data": {"task": {"guid": "private-task-guid"}},
            }
        ).encode("utf-8")

    def close(self):
        return None


class _FakeTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append((request, timeout))
        return _FakeResponse()


def _valid_charter():
    return {
        "schema_version": "controlled-lark-pilot-0.1.0",
        "scenario_id": "sales_renewal_risk_followup",
        "workflow_id": "workflow_controlled_lark_pilot",
        "workflow_version": "0.1.0",
        "support_model": "assisted",
        "timezone": "Asia/Shanghai",
        "starts_on": "2026-07-18",
        "expires_on": "2026-08-15",
        "team_consent_confirmed": True,
        "assignee_consent_confirmed": True,
        "commercial_engagement_confirmed": True,
        "required_approved_runs": 5,
        "required_distinct_days": 5,
        "required_distinct_cases": 2,
    }


def _approved_run(sequence=1, completed_at=None):
    return {
        "schema_version": "controlled-lark-pilot-evidence-0.1.0",
        "run_id": f"run_{sequence:03d}",
        "workflow_id": "workflow_controlled_lark_pilot",
        "workflow_version": "0.1.0",
        "started_at": f"2026-07-{17 + sequence:02d}T00:59:00+00:00",
        "completed_at": completed_at
        or f"2026-07-{17 + sequence:02d}T01:00:00+00:00",
        "run_status": "completed",
        "gate_decision": "approved",
        "case_id_present": True,
        "connector_invoked": True,
        "connector_id": "lark_task",
        "connector_status": "completed",
        "credential_status": "resolved",
        "credential_handles": ["lark_bot_access_token"],
        "operation": "create_task",
        "mode": "live",
        "provider_status": "completed",
        "task_title_present": True,
        "task_description_present": True,
        "assignee_present": True,
        "due_at_present": True,
        "idempotency_key_present": True,
        "lark_task_id_present": True,
    }


def _rejected_run(sequence=6):
    return {
        "schema_version": "controlled-lark-pilot-evidence-0.1.0",
        "run_id": f"run_{sequence:03d}",
        "workflow_id": "workflow_controlled_lark_pilot",
        "workflow_version": "0.1.0",
        "started_at": "2026-07-23T00:59:00+00:00",
        "completed_at": "2026-07-23T01:00:00+00:00",
        "run_status": "failed",
        "gate_decision": "rejected",
        "case_id_present": True,
        "connector_invoked": False,
        "connector_id": "",
        "connector_status": "",
        "credential_status": "",
        "credential_handles": [],
        "operation": "",
        "mode": "",
        "provider_status": "",
        "task_title_present": False,
        "task_description_present": False,
        "assignee_present": False,
        "due_at_present": False,
        "idempotency_key_present": False,
        "lark_task_id_present": False,
    }


def _valid_exercises():
    return {
        "rejection": {
            "schema_version": "controlled-lark-pilot-exercise-0.1.0",
            "exercise": "rejection",
            "passed": True,
            "run_id": "run_006",
            "gate_decision": "rejected",
            "connector_invoked": False,
        },
        "failure": {
            "schema_version": "controlled-lark-pilot-exercise-0.1.0",
            "exercise": "disabled_live",
            "passed": True,
            "provider_status": "live_disabled",
            "credential_resolution_attempted": False,
            "transport_attempted": False,
        },
        "rollback": {
            "schema_version": "controlled-lark-pilot-exercise-0.1.0",
            "exercise": "rollback",
            "passed": True,
            "live_switch_enabled": False,
            "live_approval_blocked": True,
            "dry_run_status": "completed",
        },
    }


def _valid_verification():
    command_ids = (
        "focused-tests",
        "full-tests",
        "compile",
        "secret-hygiene",
        "connector-smoke",
        "dry-run-pilot-smoke",
        "diff-check",
    )
    return {
        "schema_version": "controlled-lark-pilot-verification-0.1.0",
        "all_passed": True,
        "commands": [
            {"id": command_id, "exit_code": 0, "passed": True, "duration_ms": 1}
            for command_id in command_ids
        ],
    }


def _valid_decision():
    return {
        "schema_version": "controlled-lark-pilot-decision-0.1.0",
        "decision": "continue",
        "partner_acknowledged": True,
        "operator_acknowledged": True,
        "commercial_engagement_confirmed": True,
        "rationale": "The controlled workflow delivered the agreed result.",
    }


def _valid_index():
    return {
        "schema_version": "controlled-lark-pilot-index-0.1.0",
        "generated_at": "2026-07-23T09:00:00+08:00",
        "workflow_id": "workflow_controlled_lark_pilot",
        "workflow_version": "0.1.0",
        "timezone": "Asia/Shanghai",
        "approved_live_runs": 5,
        "required_approved_runs": 5,
        "distinct_calendar_days": 5,
        "required_distinct_days": 5,
        "distinct_private_cases": 2,
        "required_distinct_cases": 2,
        "rejected_runs": 1,
        "rejection_passed": True,
        "failure_passed": True,
        "rollback_passed": True,
        "verification_passed": True,
        "decision_recorded": True,
        "decision": "continue",
        "partner_acknowledged": True,
        "operator_acknowledged": True,
        "commercial_engagement_confirmed": True,
        "ready_to_finalize": True,
        "unmet_conditions": [],
    }


def _valid_pack():
    return {
        "charter": _valid_charter(),
        "runs": [_approved_run(index) for index in range(1, 6)]
        + [_rejected_run()],
        "exercises": _valid_exercises(),
        "verification": _valid_verification(),
        "decision": _valid_decision(),
        "index": _valid_index(),
    }


def _raw_completed_run_and_audit():
    run = {
        "run_id": "run_raw",
        "workflow_id": "workflow_controlled_lark_pilot",
        "workflow_version": "0.1.0",
        "status": "completed",
        "context": {"input": {"pilot_case_id": "case-raw"}},
    }
    audit = [
        {
            "type": "run_started",
            "run_id": "run_raw",
            "timestamp": "2026-07-18T01:00:00+00:00",
        },
        {
            "type": "run_resumed",
            "run_id": "run_raw",
            "approved": True,
            "timestamp": "2026-07-18T01:01:00+00:00",
        },
        {
            "type": "connector_completed",
            "run_id": "run_raw",
            "node_id": "create_lark_task",
            "connector_id": "lark_task",
            "connector_status": "completed",
            "credential_status": "resolved",
            "credential_handles": ["lark_bot_access_token"],
            "connector_metadata": {
                "operation": "create_task",
                "mode": "live",
                "provider_status": "completed",
                "task_title_present": True,
                "task_description_present": True,
                "assignee_present": True,
                "due_at_present": True,
                "idempotency_key_present": True,
                "lark_task_id_present": True,
            },
            "timestamp": "2026-07-18T01:01:01+00:00",
        },
        {
            "type": "run_completed",
            "run_id": "run_raw",
            "timestamp": "2026-07-18T01:01:02+00:00",
        },
    ]
    return run, audit


def _prepare_repo(root):
    repo_root = root / "repo"
    connector_dir = repo_root / "examples" / "connectors"
    connector_dir.mkdir(parents=True)
    shutil.copyfile(
        ROOT / "examples" / "connectors" / "lark_task_connector.py",
        connector_dir / "lark_task_connector.py",
    )
    return repo_root


def _write_case(path, case_id):
    path.write_text(
        json.dumps(
            {
                "pilot_case_id": case_id,
                "account_name": f"Private Account {case_id}",
                "renewal_risk": f"Private Risk {case_id}",
                "owner_open_id": f"ou_private_{case_id}",
                "due_at": "2026-08-15T09:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    os.chmod(path, 0o600)


def _write_private_artifacts(work_dir):
    private = work_dir / "private"
    values = {
        "failure.json": _valid_exercises()["failure"],
        "rollback.json": _valid_exercises()["rollback"],
        "verification.json": _valid_verification(),
        "decision.json": _valid_decision(),
    }
    for name, value in values.items():
        path = private / name
        path.write_text(json.dumps(value), encoding="utf-8")
        os.chmod(path, 0o600)


def _build_ready_state(root):
    repo_root = _prepare_repo(root)
    work_dir = root / "pilot"
    initialize_pilot(repo_root, work_dir, _valid_charter(), now=NOW)
    transport = _FakeTransport()
    environment = {
        "SKILL2WORKFLOW_LARK_TASK_LIVE": "1",
        "LARK_BOT_ACCESS_TOKEN": "private-token",
    }
    for sequence in range(5):
        case_id = f"case-{1 + sequence % 2:03d}"
        input_path = root / f"approved-{sequence}.json"
        _write_case(input_path, case_id)
        started_at = f"2026-07-{18 + sequence:02d}T00:59:00+00:00"
        completed_at = f"2026-07-{18 + sequence:02d}T01:00:00+00:00"
        with patch(
            "skill2workflow.control_plane._now", return_value=started_at
        ), patch("skill2workflow.executor._now", return_value=started_at):
            started = start_pilot_run(
                repo_root, work_dir, input_path, now=NOW, transport=transport
            )
        with patch.dict(os.environ, environment, clear=True), patch(
            "skill2workflow.control_plane._now", return_value=completed_at
        ), patch(
            "skill2workflow.executor._now", return_value=completed_at
        ):
            decide_pilot_run(
                repo_root,
                work_dir,
                started["run_id"],
                approved=True,
                confirmed_live=True,
                now=NOW,
                transport=transport,
            )
    rejected_path = root / "rejected.json"
    _write_case(rejected_path, "case-rejected")
    with patch(
        "skill2workflow.control_plane._now",
        return_value="2026-07-23T00:59:00+00:00",
    ), patch(
        "skill2workflow.executor._now",
        return_value="2026-07-23T00:59:00+00:00",
    ):
        rejected = start_pilot_run(
            repo_root, work_dir, rejected_path, now=NOW, transport=transport
        )
    with patch.dict(os.environ, {}, clear=True), patch(
        "skill2workflow.control_plane._now",
        return_value="2026-07-23T01:00:00+00:00",
    ), patch(
        "skill2workflow.executor._now",
        return_value="2026-07-23T01:00:00+00:00",
    ):
        decide_pilot_run(
            repo_root,
            work_dir,
            rejected["run_id"],
            approved=False,
            now=NOW,
            transport=transport,
        )
    _write_private_artifacts(work_dir)
    return repo_root, work_dir, transport


class ControlledLarkPilotEvidenceTests(TestCase):
    def test_forbidden_scan_checks_raw_substrings_in_each_unescaped_leaf(self):
        forbidden_values = ("C1", 'line\n"quote"\\tail')
        for forbidden in forbidden_values:
            pack = _valid_pack()
            pack["decision"]["rationale"] = f"prefix {forbidden} suffix"
            with self.subTest(forbidden=repr(forbidden)), self.assertRaisesRegex(
                ValueError,
                "forbidden private value",
            ):
                validate_evidence_pack(pack, [forbidden])

    def test_build_run_evidence_requires_nonempty_exact_string_case_id(self):
        for invalid in ("", " ", 1, [], {}):
            run, audit = _raw_completed_run_and_audit()
            run["context"]["input"]["pilot_case_id"] = invalid
            with self.subTest(value=repr(invalid)), self.assertRaisesRegex(
                ValueError,
                "pilot_case_id",
            ):
                build_run_evidence(run, audit)

    def test_build_run_evidence_requires_exact_boolean_presence_metadata(self):
        fields = (
            "task_title_present",
            "task_description_present",
            "assignee_present",
            "due_at_present",
            "idempotency_key_present",
            "lark_task_id_present",
        )
        invalid_values = ("false", 1, {})
        for field in fields:
            for invalid in invalid_values:
                run, audit = _raw_completed_run_and_audit()
                audit[2]["connector_metadata"][field] = invalid
                with self.subTest(field=field, value=repr(invalid)), self.assertRaisesRegex(
                    ValueError,
                    "presence",
                ):
                    build_run_evidence(run, audit)

    def test_build_run_evidence_binds_terminal_events_to_run_status_and_time_order(self):
        mutations = []

        run, audit = _raw_completed_run_and_audit()
        audit[0]["run_id"] = "run_other"
        mutations.append(("mismatched start", run, audit))

        run, audit = _raw_completed_run_and_audit()
        audit[-1]["run_id"] = "run_other"
        mutations.append(("mismatched terminal", run, audit))

        run, audit = _raw_completed_run_and_audit()
        audit.pop()
        mutations.append(("missing terminal", run, audit))

        run, audit = _raw_completed_run_and_audit()
        audit[-1]["type"] = "run_failed"
        mutations.append(("wrong terminal type", run, audit))

        run, audit = _raw_completed_run_and_audit()
        audit[-1]["timestamp"] = "2026-07-18T00:59:59+00:00"
        mutations.append(("terminal before start", run, audit))

        for label, run, audit in mutations:
            with self.subTest(case=label), self.assertRaises(ValueError):
                build_run_evidence(run, audit)

    def test_build_run_evidence_rejects_any_conflicting_start_or_terminal_event(self):
        mutations = []

        run, audit = _raw_completed_run_and_audit()
        audit.insert(
            1,
            {
                "type": "run_started",
                "run_id": "run_other",
                "timestamp": "2026-07-18T01:00:01+00:00",
            },
        )
        mutations.append(("extra mismatched start", run, audit))

        run, audit = _raw_completed_run_and_audit()
        audit.insert(
            -1,
            {
                "type": "run_completed",
                "run_id": "run_other",
                "timestamp": "2026-07-18T01:01:01+00:00",
            },
        )
        mutations.append(("extra mismatched terminal", run, audit))

        run, audit = _raw_completed_run_and_audit()
        audit.insert(
            -1,
            {
                "type": "run_completed",
                "run_id": "run_raw",
                "timestamp": "not-a-time",
            },
        )
        mutations.append(("extra invalid terminal time", run, audit))

        for label, run, audit in mutations:
            with self.subTest(case=label), self.assertRaises(ValueError):
                build_run_evidence(run, audit)

    def test_build_run_evidence_rejects_invalid_or_naive_event_timestamps(self):
        for index in (0, -1):
            for invalid in ("not-a-time", "2026-07-18T01:00:00"):
                run, audit = _raw_completed_run_and_audit()
                audit[index]["timestamp"] = invalid
                with self.subTest(index=index, value=invalid), self.assertRaises(ValueError):
                    build_run_evidence(run, audit)

    def test_validate_pack_requires_terminal_timestamp_for_qualifying_rejection(self):
        pack = _valid_pack()
        pack["runs"][-1]["completed_at"] = ""

        with self.assertRaisesRegex(ValueError, "completed_at"):
            validate_evidence_pack(pack, [])

    def test_generate_evidence_from_real_sqlite_state_is_redacted_stable_and_ready(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo_root, work_dir, transport = _build_ready_state(root)
            with patch.dict(
                os.environ,
                {"LARK_BOT_ACCESS_TOKEN": "private-token"},
                clear=True,
            ):
                result = generate_pilot_evidence(
                    repo_root,
                    work_dir,
                    now=NOW,
                )

            evidence_dir = work_dir / "evidence"
            index = json.loads(
                (evidence_dir / "evidence-index.json").read_text(encoding="utf-8")
            )
            run_files = sorted((evidence_dir / "runs").glob("*.json"))
            runs = [json.loads(path.read_text(encoding="utf-8")) for path in run_files]
            encoded = "".join(
                path.read_text(encoding="utf-8")
                for path in evidence_dir.rglob("*.json")
            )
            native_tokens = [
                json.loads(request.data.decode("utf-8"))["client_token"]
                for request, _timeout in transport.calls
            ]

            self.assertEqual(result["output_dir"], str(evidence_dir))
            self.assertEqual(result["run_count"], 6)
            self.assertEqual(result["distinct_private_cases"], 2)
            self.assertEqual(result["unmet_conditions"], [])
            self.assertTrue(index["ready_to_finalize"])
            self.assertEqual(index["approved_live_runs"], 5)
            self.assertEqual(index["distinct_calendar_days"], 5)
            self.assertEqual(index["rejected_runs"], 1)
            self.assertEqual(index["generated_at"], "2026-07-23T17:00:00+08:00")
            self.assertEqual(len(run_files), 6)
            self.assertEqual(
                [(run["started_at"], run["run_id"]) for run in runs],
                sorted((run["started_at"], run["run_id"]) for run in runs),
            )
            self.assertEqual(len(transport.calls), 5)
            for forbidden in (
                "case-001",
                "case-002",
                "case-rejected",
                "Private Account",
                "Private Risk",
                "ou_private",
                "private-token",
                "private-provider-message",
                "private-task-guid",
                *native_tokens,
            ):
                self.assertNotIn(forbidden, encoded)
                self.assertNotIn(forbidden, json.dumps(result))

            finalization = work_dir / "private" / "finalization.json"
            repo_output = repo_root / "docs" / "pilot-evidence" / "loop-40"
            valid_marker = {
                "schema_version": "controlled-lark-pilot-finalization-0.1.0",
                "finalized": True,
                "decision": "continue",
                "finalized_at": "2026-07-23T17:00:00+08:00",
            }
            marker_target = root / "outside-finalization.json"
            marker_target.write_text(json.dumps(valid_marker), encoding="utf-8")
            finalization.symlink_to(marker_target)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                generate_pilot_evidence(
                    repo_root,
                    work_dir,
                    output_dir=repo_output,
                    now=NOW,
                )
            self.assertEqual(
                json.loads(marker_target.read_text(encoding="utf-8")), valid_marker
            )
            self.assertFalse(repo_output.exists())
            finalization.unlink()

            finalization.mkdir()
            with self.assertRaisesRegex(ValueError, "regular file"):
                generate_pilot_evidence(
                    repo_root,
                    work_dir,
                    output_dir=repo_output,
                    now=NOW,
                )
            self.assertFalse(repo_output.exists())
            finalization.rmdir()

            invalid_markers = [
                {
                    "schema_version": "controlled-lark-pilot-finalization-0.1.0",
                    "finalized": 1,
                    "decision": "continue",
                    "finalized_at": "2026-07-23T17:00:00+08:00",
                },
                {
                    "schema_version": "controlled-lark-pilot-finalization-0.1.0",
                    "finalized": True,
                    "decision": "defer",
                    "finalized_at": "2026-07-23T17:00:00+08:00",
                },
                {
                    "schema_version": "controlled-lark-pilot-finalization-0.1.0",
                    "finalized": True,
                    "decision": "continue",
                    "finalized_at": "2026-07-23T17:00:00",
                },
            ]
            for marker in invalid_markers:
                finalization.write_text(json.dumps(marker), encoding="utf-8")
                with self.subTest(marker=marker), self.assertRaises(ValueError):
                    generate_pilot_evidence(
                        repo_root,
                        work_dir,
                        output_dir=repo_output,
                        now=NOW,
                    )
                self.assertFalse(repo_output.exists())

            finalization.write_text(json.dumps(valid_marker), encoding="utf-8")
            exported = generate_pilot_evidence(
                repo_root,
                work_dir,
                output_dir=repo_output,
                now=NOW,
            )
            self.assertEqual(exported["output_dir"], str(repo_output))
            self.assertTrue((repo_output / "evidence-index.json").is_file())

    def test_generate_evidence_allows_external_explicit_output_without_finalization(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo_root = _prepare_repo(root)
            work_dir = root / "pilot"
            initialize_pilot(repo_root, work_dir, _valid_charter(), now=NOW)
            output = root / "external-evidence"

            result = generate_pilot_evidence(
                repo_root,
                work_dir,
                output_dir=output,
                now=NOW,
            )

            self.assertEqual(result["output_dir"], str(output))
            self.assertEqual(result["run_count"], 0)
            self.assertEqual(
                result["unmet_conditions"],
                [
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
                ],
            )
            self.assertTrue((output / "pilot-charter.json").is_file())
            self.assertFalse((work_dir / "private" / "finalization.json").exists())

    def test_generate_evidence_rejects_unfinalized_or_wrong_repository_output(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo_root = _prepare_repo(root)
            work_dir = root / "pilot"
            initialize_pilot(repo_root, work_dir, _valid_charter(), now=NOW)
            exact = repo_root / "docs" / "pilot-evidence" / "loop-40"

            with self.assertRaisesRegex(ValueError, "finalization"):
                generate_pilot_evidence(
                    repo_root,
                    work_dir,
                    output_dir=exact,
                    now=NOW,
                )
            with self.assertRaisesRegex(ValueError, "repository evidence output"):
                generate_pilot_evidence(
                    repo_root,
                    work_dir,
                    output_dir=repo_root / "docs" / "pilot-evidence" / "other",
                    now=NOW,
                )

            self.assertFalse(exact.exists())

    def test_build_run_evidence_uses_exact_allowlist_without_private_values(self):
        run = {
            "run_id": "run_001",
            "workflow_id": "workflow_controlled_lark_pilot",
            "workflow_version": "0.1.0",
            "status": "completed",
            "context": {
                "input": {
                    "pilot_case_id": "case-001",
                    "account_name": "Private Account",
                    "renewal_risk": "Private Risk",
                    "owner_open_id": "ou_private",
                    "due_at": "2026-08-15T09:00:00Z",
                }
            },
            "node_results": {
                "create_lark_task": {
                    "output": {
                        "message": "private-provider-message",
                        "task_id": "private-task-id",
                    }
                }
            },
        }
        audit = [
            {
                "type": "run_started",
                "run_id": "run_001",
                "timestamp": "2026-07-18T01:00:00+00:00",
            },
            {
                "type": "run_resumed",
                "run_id": "run_001",
                "approved": True,
                "timestamp": "2026-07-18T01:01:00+00:00",
            },
            {
                "type": "connector_completed",
                "run_id": "run_001",
                "node_id": "create_lark_task",
                "connector_id": "lark_task",
                "connector_status": "completed",
                "credential_status": "resolved",
                "credential_handles": ["lark_bot_access_token"],
                "connector_metadata": {
                    "operation": "create_task",
                    "mode": "live",
                    "provider_status": "completed",
                    "task_title_present": True,
                    "task_description_present": True,
                    "assignee_present": True,
                    "due_at_present": True,
                    "idempotency_key_present": True,
                    "lark_task_id_present": True,
                },
                "timestamp": "2026-07-18T01:01:01+00:00",
            },
            {
                "type": "run_completed",
                "run_id": "run_001",
                "timestamp": "2026-07-18T01:01:02+00:00",
            },
        ]

        evidence = build_run_evidence(run, audit)

        self.assertEqual(set(evidence), RUN_EVIDENCE_KEYS)
        self.assertEqual(evidence["run_id"], "run_001")
        self.assertEqual(evidence["gate_decision"], "approved")
        self.assertEqual(evidence["provider_status"], "completed")
        self.assertTrue(evidence["case_id_present"])
        encoded = json.dumps(evidence)
        for forbidden in (
            "case-001",
            "Private Account",
            "Private Risk",
            "ou_private",
            "2026-08-15T09:00:00Z",
            "private-provider-message",
            "private-task-id",
        ):
            self.assertNotIn(forbidden, encoded)

    def test_build_run_evidence_reports_human_rejection_without_connector_data(self):
        run = {
            "run_id": "run_rejected",
            "workflow_id": "workflow_controlled_lark_pilot",
            "workflow_version": "0.1.0",
            "status": "failed",
            "context": {"input": {"pilot_case_id": "case-rejected"}},
        }
        audit = [
            {
                "type": "run_started",
                "run_id": "run_rejected",
                "timestamp": "2026-07-18T01:00:00+00:00",
            },
            {
                "type": "run_resumed",
                "run_id": "run_rejected",
                "approved": False,
                "timestamp": "2026-07-18T01:01:00+00:00",
            },
            {
                "type": "run_failed",
                "run_id": "run_rejected",
                "timestamp": "2026-07-18T01:02:00+00:00",
            },
        ]

        evidence = build_run_evidence(run, audit)

        self.assertEqual(evidence["gate_decision"], "rejected")
        self.assertFalse(evidence["connector_invoked"])
        for key in (
            "connector_id",
            "connector_status",
            "credential_status",
            "operation",
            "mode",
            "provider_status",
        ):
            self.assertEqual(evidence[key], "")
        self.assertEqual(evidence["credential_handles"], [])

    def test_acceptance_summary_requires_complete_contract_over_five_shanghai_days(self):
        approved_runs = [_approved_run(index) for index in range(1, 6)]
        rejected_run = _rejected_run()

        summary = build_acceptance_summary(
            charter=_valid_charter(),
            runs=approved_runs + [rejected_run],
            distinct_private_cases=2,
            exercises={"failure": {"passed": True}, "rollback": {"passed": True}},
            verification={"all_passed": True},
            decision={
                "decision": "continue",
                "partner_acknowledged": True,
                "operator_acknowledged": True,
                "commercial_engagement_confirmed": True,
                "rationale": "The controlled workflow delivered the agreed result.",
            },
        )

        self.assertTrue(summary["ready_to_finalize"])
        self.assertEqual(summary["approved_live_runs"], 5)
        self.assertEqual(summary["distinct_calendar_days"], 5)
        self.assertEqual(summary["distinct_private_cases"], 2)
        self.assertEqual(summary["rejected_runs"], 1)
        self.assertEqual(summary["unmet_conditions"], [])

    def test_acceptance_summary_lists_every_unmet_condition_in_stable_order(self):
        summary = build_acceptance_summary(
            charter=_valid_charter(),
            runs=[],
            distinct_private_cases=0,
            exercises={"rejection": None, "failure": None, "rollback": None},
            verification=None,
            decision=None,
        )

        self.assertFalse(summary["ready_to_finalize"])
        self.assertEqual(
            summary["unmet_conditions"],
            [
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
            ],
        )
        self.assertTrue(summary["commercial_engagement_confirmed"])

    def test_acceptance_summary_does_not_count_partial_provider_success(self):
        fields = (
            ("workflow_id", "workflow_other"),
            ("workflow_version", "9.9.9"),
            ("gate_decision", "pending"),
            ("run_status", "failed"),
            ("case_id_present", False),
            ("connector_invoked", False),
            ("connector_id", ""),
            ("connector_status", "failed"),
            ("credential_status", "failed"),
            ("credential_handles", []),
            ("operation", ""),
            ("mode", ""),
            ("provider_status", "provider_unavailable"),
            ("task_title_present", False),
            ("task_description_present", False),
            ("assignee_present", False),
            ("due_at_present", False),
            ("idempotency_key_present", False),
            ("lark_task_id_present", False),
        )
        for field, value in fields:
            candidate = _approved_run()
            candidate[field] = value
            with self.subTest(field=field):
                summary = build_acceptance_summary(
                    _valid_charter(),
                    [candidate],
                    1,
                    {"failure": {"passed": True}, "rollback": {"passed": True}},
                    {"all_passed": True},
                    _valid_decision(),
                )
                self.assertEqual(summary["approved_live_runs"], 0)

    def test_acceptance_summary_rejects_non_integer_private_case_cardinality(self):
        for value in (True, 1.0, "2", -1):
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError,
                "distinct private cases",
            ):
                build_acceptance_summary(
                    _valid_charter(),
                    [],
                    value,
                    {},
                    None,
                    None,
                )

    def test_validate_pack_accepts_exact_schema_and_optional_none_slots(self):
        validate_evidence_pack(_valid_pack(), [])
        pack = _valid_pack()
        pack["runs"] = []
        pack["exercises"] = {"rejection": None, "failure": None, "rollback": None}
        pack["verification"] = None
        pack["decision"] = None
        pack["index"].update(
            build_acceptance_summary(
                pack["charter"],
                pack["runs"],
                0,
                pack["exercises"],
                pack["verification"],
                pack["decision"],
            )
        )
        validate_evidence_pack(pack, [])

    def test_validate_pack_rejects_equal_but_wrong_charter_threshold_type(self):
        pack = _valid_pack()
        pack["charter"]["required_approved_runs"] = 5.0

        with self.assertRaisesRegex(ValueError, "nonnegative integer"):
            validate_evidence_pack(pack, [])

    def test_validate_pack_rejects_index_or_rejection_artifact_contradictions(self):
        pack = _valid_pack()
        pack["index"]["approved_live_runs"] = 4
        with self.assertRaisesRegex(ValueError, "acceptance summary"):
            validate_evidence_pack(pack, [])

        pack = _valid_pack()
        pack["exercises"]["rejection"] = None
        with self.assertRaisesRegex(ValueError, "rejection exercise"):
            validate_evidence_pack(pack, [])

    def test_validate_pack_requires_all_seven_verification_commands_even_on_failure(self):
        pack = _valid_pack()
        pack["verification"]["commands"].pop()
        pack["verification"]["all_passed"] = False
        pack["index"].update(
            build_acceptance_summary(
                pack["charter"],
                pack["runs"],
                2,
                pack["exercises"],
                pack["verification"],
                pack["decision"],
            )
        )

        with self.assertRaisesRegex(ValueError, "seven commands"):
            validate_evidence_pack(pack, [])

    def test_validate_pack_requires_exercise_passed_to_equal_fact_predicate(self):
        mutations = (
            ("rejection", "passed", False),
            ("failure", "passed", False),
            ("failure", "provider_status", "provider_unavailable"),
            ("rollback", "passed", False),
            ("rollback", "live_switch_enabled", True),
        )
        for name, field, value in mutations:
            pack = _valid_pack()
            pack["exercises"][name][field] = value
            pack["index"].update(
                build_acceptance_summary(
                    pack["charter"],
                    pack["runs"],
                    2,
                    pack["exercises"],
                    pack["verification"],
                    pack["decision"],
                )
            )
            with self.subTest(exercise=name, field=field), self.assertRaisesRegex(
                ValueError,
                "passed",
            ):
                validate_evidence_pack(pack, [])

    def test_validate_pack_requires_all_connector_presence_false_when_not_invoked(self):
        fields = (
            "task_title_present",
            "task_description_present",
            "assignee_present",
            "due_at_present",
            "idempotency_key_present",
            "lark_task_id_present",
        )
        for field in fields:
            pack = _valid_pack()
            pack["runs"][-1][field] = True
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError,
                "uninvoked connector evidence",
            ):
                validate_evidence_pack(pack, [])

    def test_validate_pack_rejects_unknown_keys_in_every_artifact_category(self):
        paths = (
            ("top-level", ()),
            ("charter", ("charter",)),
            ("run", ("runs", 0)),
            ("index", ("index",)),
            ("rejection", ("exercises", "rejection")),
            ("failure", ("exercises", "failure")),
            ("rollback", ("exercises", "rollback")),
            ("verification", ("verification",)),
            ("verification-command", ("verification", "commands", 0)),
            ("decision", ("decision",)),
        )
        for label, path in paths:
            candidate = _valid_pack()
            target = candidate
            for component in path:
                target = target[component]
            target["private_raw_field"] = "private-value"
            with self.subTest(category=label), self.assertRaises(ValueError):
                validate_evidence_pack(candidate, [])

    def test_validate_pack_rejects_wrong_types_fixed_identities_and_credentials(self):
        cases = (
            ("boolean integer", ("index", "approved_live_runs"), True),
            ("workflow", ("runs", 0, "workflow_id"), "workflow_other"),
            ("connector", ("runs", 0, "connector_id"), "http"),
            ("operation", ("runs", 0, "operation"), "delete_task"),
            ("mode", ("runs", 0, "mode"), "dry_run"),
            ("credential", ("runs", 0, "credential_handles"), ["other_secret"]),
            ("decision boolean", ("decision", "partner_acknowledged"), 1),
        )
        for label, path, value in cases:
            pack = _valid_pack()
            target = pack
            for component in path[:-1]:
                target = target[component]
            target[path[-1]] = value
            with self.subTest(case=label), self.assertRaises(ValueError):
                validate_evidence_pack(pack, [])

    def test_validate_pack_orders_runs_by_timestamp_instant_then_run_id(self):
        first = _approved_run(1)
        first["started_at"] = "2026-07-18T09:00:00+08:00"
        first["completed_at"] = "2026-07-18T09:01:00+08:00"
        second = _approved_run(2)
        second["started_at"] = "2026-07-18T02:00:00+00:00"
        second["completed_at"] = "2026-07-18T02:01:00+00:00"
        pack = _valid_pack()
        pack["runs"] = [first, second]
        pack["exercises"]["rejection"] = None
        pack["index"].update(
            build_acceptance_summary(
                pack["charter"],
                pack["runs"],
                2,
                pack["exercises"],
                pack["verification"],
                pack["decision"],
            )
        )

        validate_evidence_pack(pack, [])

        pack["runs"].reverse()
        with self.assertRaisesRegex(ValueError, "stable order"):
            validate_evidence_pack(pack, [])

    def test_validate_pack_rejects_forbidden_private_value_anywhere(self):
        pack = _valid_pack()
        pack["decision"]["rationale"] = "Private Account was reviewed."

        with self.assertRaisesRegex(ValueError, "forbidden private value"):
            validate_evidence_pack(pack, ["Private Account"])

    def test_write_pack_is_atomic_idempotent_and_removes_only_stale_json(self):
        pack = _valid_pack()
        with TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "evidence"
            stale = output / "runs" / "999.json"
            stale.parent.mkdir(parents=True)
            stale.write_text("{}", encoding="utf-8")
            keep = output / "notes.txt"
            keep.write_text("keep", encoding="utf-8")

            first = write_evidence_pack(output, pack)
            second = write_evidence_pack(output, pack)

            self.assertEqual(first["file_count"], second["file_count"])
            self.assertFalse(stale.exists())
            self.assertEqual(keep.read_text(encoding="utf-8"), "keep")
            self.assertFalse(
                any(path.name.endswith(".tmp") for path in output.rglob("*"))
            )
            self.assertEqual(
                json.loads((output / "runs" / "001.json").read_text(encoding="utf-8")),
                pack["runs"][0],
            )

    def test_write_pack_omits_optional_none_and_removes_old_optional_json(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "evidence"
            write_evidence_pack(output, _valid_pack())
            pack = _valid_pack()
            pack["exercises"] = {
                "rejection": None,
                "failure": None,
                "rollback": None,
            }
            pack["runs"] = []
            pack["verification"] = None
            pack["decision"] = None
            pack["index"].update(
                build_acceptance_summary(
                    pack["charter"],
                    pack["runs"],
                    0,
                    pack["exercises"],
                    pack["verification"],
                    pack["decision"],
                )
            )

            result = write_evidence_pack(output, pack)

            self.assertEqual(result["file_count"], 2 + len(pack["runs"]))
            self.assertFalse((output / "verification.json").exists())
            self.assertFalse((output / "decision.json").exists())
            self.assertEqual(list((output / "exercises").glob("*.json")), [])

    def test_write_pack_anchors_open_when_parent_path_is_swapped_to_symlink(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            output = root / "evidence"
            output.mkdir()
            anchored = root / "anchored-evidence"
            outside = root / "outside"
            outside.mkdir()
            sentinel = outside / "sentinel.json"
            sentinel.write_text("sentinel", encoding="utf-8")
            real_open = os.open
            swapped = []

            def racing_open(path, flags, mode=0o777, *, dir_fd=None):
                name = os.fspath(path)
                if not swapped and name.endswith(".tmp"):
                    output.rename(anchored)
                    output.symlink_to(outside, target_is_directory=True)
                    swapped.append(True)
                if dir_fd is None:
                    return real_open(path, flags, mode)
                return real_open(path, flags, mode, dir_fd=dir_fd)

            with patch(
                "skill2workflow.controlled_lark_pilot_evidence.os.open",
                side_effect=racing_open,
            ):
                result = write_evidence_pack(output, _valid_pack())

            self.assertEqual(swapped, [True])
            self.assertEqual(result["status"], "written")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "sentinel")
            self.assertEqual(list(outside.glob("*.json")), [sentinel])
            self.assertTrue((anchored / "evidence-index.json").is_file())

    def test_write_pack_random_temp_does_not_block_on_crash_leftover(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "evidence"
            output.mkdir()
            leftover = output / ".pilot-charter.json.tmp"
            leftover.write_text("crash-leftover", encoding="utf-8")

            result = write_evidence_pack(output, _valid_pack())

            self.assertEqual(result["status"], "written")
            self.assertEqual(leftover.read_text(encoding="utf-8"), "crash-leftover")
            self.assertTrue((output / "pilot-charter.json").is_file())

    def test_write_pack_cleans_random_temp_when_atomic_replace_fails(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "evidence"

            with patch(
                "skill2workflow.controlled_lark_pilot_evidence.os.replace",
                side_effect=OSError("replace failed"),
            ), self.assertRaisesRegex(OSError, "replace failed"):
                write_evidence_pack(output, _valid_pack())

            self.assertEqual(
                [path for path in output.rglob("*") if path.name.endswith(".tmp")],
                [],
            )

    def test_write_pack_fails_closed_without_secure_directory_fd_support(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "evidence"

            with patch(
                "skill2workflow.controlled_lark_pilot_evidence._DIR_FD_SUPPORTED",
                False,
            ), self.assertRaisesRegex(ValueError, "directory-fd"):
                write_evidence_pack(output, _valid_pack())

            self.assertFalse(output.exists())

    def test_write_pack_rejects_stale_json_symlink_without_touching_target(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            output = root / "evidence"
            output.mkdir()
            target = root / "outside.json"
            target.write_text("sentinel", encoding="utf-8")
            (output / "stale.json").symlink_to(target)

            with self.assertRaisesRegex(ValueError, "symbolic link"):
                write_evidence_pack(output, _valid_pack())

            self.assertEqual(target.read_text(encoding="utf-8"), "sentinel")

    def test_write_pack_rejects_root_and_symlink_components_without_touching_target(self):
        with self.assertRaisesRegex(ValueError, "root"):
            write_evidence_pack(Path("/"), _valid_pack())

        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            target = root / "target"
            target.mkdir()
            sentinel = target / "stale.json"
            sentinel.write_text("sentinel", encoding="utf-8")
            linked = root / "linked"
            linked.symlink_to(target, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "symbolic link"):
                write_evidence_pack(linked, _valid_pack())

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "sentinel")

        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            output = root / "evidence"
            output.mkdir()
            target = root / "target"
            target.mkdir()
            sentinel = target / "sentinel.txt"
            sentinel.write_text("sentinel", encoding="utf-8")
            (output / "runs").symlink_to(target, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "symbolic link"):
                write_evidence_pack(output, _valid_pack())

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "sentinel")
            self.assertEqual(list(target.glob("*.json")), [])


if __name__ == "__main__":
    import unittest

    unittest.main()
