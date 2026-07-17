import json
import os
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.compiler import validate_workflow
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.controlled_lark_pilot import (
    _validate_controlled_live_binding,
    decide_pilot_run,
    exercise_disabled_live,
    exercise_rollback,
    initialize_pilot,
    load_pilot_charter,
    load_private_case,
    start_pilot_run,
    verify_pilot,
)
from skill2workflow.credentials import StaticCredentialProvider
from skill2workflow.lark_task_pilot import build_lark_task_pilot_workflow


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc)


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


class _FakeCommandResult:
    def __init__(self, returncode=0):
        self.returncode = returncode
        self.stdout = "private-command-stdout"
        self.stderr = "private-command-stderr"


class _FakeCommandRunner:
    def __init__(self, exit_codes=None):
        self.exit_codes = list(exit_codes or [0] * 7)
        self.arguments = []
        self.environments = []
        self.working_directories = []
        self.capture_output = []

    def __call__(self, arguments, *, cwd, env, capture_output):
        self.arguments.append(list(arguments))
        self.environments.append(dict(env))
        self.working_directories.append(cwd)
        self.capture_output.append(capture_output)
        return _FakeCommandResult(self.exit_codes[len(self.arguments) - 1])


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


def _valid_case():
    return {
        "pilot_case_id": "case-001",
        "account_name": "Private Account",
        "renewal_risk": "Private Risk",
        "owner_open_id": "ou_private",
        "due_at": "2026-08-15T09:00:00Z",
    }


def _write_private_case(path: Path, case_id: str = "case-001") -> None:
    path.write_text(
        json.dumps(
            {
                "pilot_case_id": case_id,
                "account_name": "Private Account",
                "renewal_risk": "Private Risk",
                "owner_open_id": "ou_private",
                "due_at": "2026-08-15T09:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    os.chmod(path, 0o600)


def _start_waiting_pilot(tmp: str, case_id: str = "case-001"):
    root = Path(tmp)
    work_dir = root / "pilot"
    input_path = root / "case.json"
    initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)
    _write_private_case(input_path, case_id=case_id)
    started = start_pilot_run(ROOT, work_dir, input_path, now=NOW)
    return work_dir, started


def _published_controlled_workflow():
    workflow = build_lark_task_pilot_workflow(
        mode="live",
        workflow_id="workflow_controlled_lark_pilot",
        workflow_version="0.1.0",
        workflow_name="controlled-lark-task-sales-renewal-pilot",
    )
    workflow["workflow"]["status"] = "published"
    return workflow


class ControlledLarkPilotTests(TestCase):
    def test_exercise_disabled_live_uses_real_boundary_without_credentials_or_transport(self):
        expected = {
            "exercise": "disabled_live",
            "passed": True,
            "provider_status": "live_disabled",
            "credential_resolution_attempted": False,
            "transport_attempted": False,
        }
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)
            environment = {
                "SKILL2WORKFLOW_LARK_TASK_LIVE": "1",
                "LARK_BOT_ACCESS_TOKEN": "private-token",
            }
            with patch.dict(os.environ, environment, clear=True):
                result = exercise_disabled_live(ROOT, work_dir, now=NOW)
                restored = {
                    key: os.environ.get(key)
                    for key in environment
                }

            exercise_path = work_dir / "private" / "exercises" / "failure.json"
            persisted = json.loads(exercise_path.read_text(encoding="utf-8"))
            exercise_mode = exercise_path.stat().st_mode & 0o077
            encoded = json.dumps({"result": result, "persisted": persisted})
            remaining_private_bytes = b"".join(
                path.read_bytes()
                for path in work_dir.rglob("*")
                if path.is_file()
            )

        self.assertEqual(result, expected)
        self.assertEqual(restored, environment)
        self.assertEqual(
            set(persisted),
            {
                "schema_version",
                "exercise",
                "passed",
                "provider_status",
                "credential_resolution_attempted",
                "transport_attempted",
            },
        )
        self.assertEqual({key: persisted[key] for key in expected}, expected)
        self.assertEqual(exercise_mode, 0)
        for forbidden in (
            "exercise-disabled-001",
            "Disabled Live Exercise Account",
            "Disabled Live Exercise Risk",
            "ou_disabled_live_exercise",
            "private-token",
        ):
            self.assertNotIn(forbidden, encoded)
            self.assertNotIn(forbidden.encode("utf-8"), remaining_private_bytes)

    def test_exercise_rollback_rejects_enabled_live_before_writes(self):
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)
            with patch.dict(
                os.environ,
                {
                    "SKILL2WORKFLOW_LARK_TASK_LIVE": "1",
                    "LARK_BOT_ACCESS_TOKEN": "private-token",
                },
                clear=True,
            ), patch(
                "skill2workflow.lark_task_pilot.run_lark_task_pilot",
                side_effect=AssertionError("dry run must not start"),
            ) as dry_run:
                with self.assertRaisesRegex(ValueError, "remove.*live switch"):
                    exercise_rollback(ROOT, work_dir, now=NOW)

            dry_run.assert_not_called()
            self.assertFalse(
                (work_dir / "private" / "exercises" / "rollback.json").exists()
            )
            self.assertFalse((work_dir / "private" / "rollback-live-probe").exists())

    def test_task6_operations_restore_live_environment_on_every_exception_path(self):
        environment = {
            "SKILL2WORKFLOW_LARK_TASK_LIVE": "0",
            "LARK_BOT_ACCESS_TOKEN": "private-token",
        }
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)
            with patch.dict(os.environ, environment, clear=True):
                with patch(
                    "skill2workflow.controlled_lark_pilot.start_pilot_run",
                    side_effect=RuntimeError("disabled exercise failed"),
                ), self.assertRaisesRegex(RuntimeError, "disabled exercise failed"):
                    exercise_disabled_live(ROOT, work_dir, now=NOW)
                disabled_restored = {
                    key: os.environ.get(key) for key in environment
                }

            with patch.dict(os.environ, environment, clear=True):
                with patch(
                    "skill2workflow.lark_task_pilot.run_lark_task_pilot",
                    side_effect=RuntimeError("rollback dry run failed"),
                ), self.assertRaisesRegex(RuntimeError, "rollback dry run failed"):
                    exercise_rollback(ROOT, work_dir, now=NOW)
                rollback_restored = {
                    key: os.environ.get(key) for key in environment
                }

            observed_environment = {}

            def failing_runner(arguments, *, cwd, env, capture_output):
                observed_environment.update(env)
                raise RuntimeError("verification runner failed")

            with patch.dict(os.environ, environment, clear=True):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "verification runner failed",
                ):
                    verify_pilot(ROOT, work_dir, command_runner=failing_runner)
                verification_restored = {
                    key: os.environ.get(key) for key in environment
                }

            self.assertFalse(
                (work_dir / "private" / "exercises" / "failure.json").exists()
            )
            self.assertFalse(
                (work_dir / "private" / "exercises" / "rollback.json").exists()
            )
            self.assertFalse((work_dir / "private" / "verification.json").exists())

        self.assertEqual(disabled_restored, environment)
        self.assertEqual(rollback_restored, environment)
        self.assertEqual(verification_restored, environment)
        self.assertNotIn("SKILL2WORKFLOW_LARK_TASK_LIVE", observed_environment)
        self.assertNotIn("LARK_BOT_ACCESS_TOKEN", observed_environment)

    def test_task6_operations_reject_repository_work_dir_before_side_effects(self):
        runner = _FakeCommandRunner()
        with patch(
            "skill2workflow.controlled_lark_pilot.load_pilot_charter",
            side_effect=AssertionError("charter must not be loaded"),
        ) as load_charter, patch(
            "skill2workflow.controlled_lark_pilot._pilot_control_plane",
            side_effect=AssertionError("control plane must not be created"),
        ) as control_plane:
            for operation in (
                lambda: exercise_disabled_live(ROOT, ROOT / "private", now=NOW),
                lambda: exercise_rollback(ROOT, ROOT / "private", now=NOW),
                lambda: verify_pilot(
                    ROOT,
                    ROOT / "private",
                    command_runner=runner,
                ),
            ):
                with self.subTest(operation=operation), self.assertRaisesRegex(
                    ValueError,
                    "outside the repository",
                ):
                    operation()

        load_charter.assert_not_called()
        control_plane.assert_not_called()
        self.assertEqual(runner.arguments, [])

    def test_exercise_rollback_proves_guard_preserves_waiting_run_and_dry_run(self):
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)
            with patch.dict(
                os.environ,
                {"LARK_BOT_ACCESS_TOKEN": "private-token"},
                clear=True,
            ):
                result = exercise_rollback(ROOT, work_dir, now=NOW)
                restored_token = os.environ.get("LARK_BOT_ACCESS_TOKEN")

            persisted_path = (
                work_dir / "private" / "exercises" / "rollback.json"
            )
            persisted = json.loads(persisted_path.read_text(encoding="utf-8"))
            persisted_mode = persisted_path.stat().st_mode & 0o077
            proof_control = LocalControlPlane(
                work_dir / "private" / "rollback-live-probe" / "state",
                storage="sqlite",
            )
            proof_runs = proof_control.list_runs()
            dry_run_artifact_exists = (
                work_dir
                / "private"
                / "rollback-dry-run"
                / "artifacts"
                / "run.json"
            ).is_file()

        self.assertEqual(
            result,
            {
                "exercise": "rollback",
                "passed": True,
                "live_switch_enabled": False,
                "live_approval_blocked": True,
                "dry_run_status": "completed",
            },
        )
        self.assertEqual(restored_token, "private-token")
        self.assertEqual({key: persisted[key] for key in result}, result)
        self.assertEqual(persisted_mode, 0)
        self.assertEqual(len(proof_runs), 1)
        self.assertEqual(proof_runs[0]["status"], "waiting")
        self.assertTrue(dry_run_artifact_exists)

    def test_verify_pilot_runs_exact_offline_commands_and_persists_compact_results(self):
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)
            runner = _FakeCommandRunner()
            with patch.dict(
                os.environ,
                {
                    "SKILL2WORKFLOW_LARK_TASK_LIVE": "1",
                    "LARK_BOT_ACCESS_TOKEN": "private-token",
                    "KEEP_ME": "yes",
                },
                clear=True,
            ):
                result = verify_pilot(ROOT, work_dir, command_runner=runner)
            resolved_work_dir = work_dir.resolve()

            verification_path = work_dir / "private" / "verification.json"
            persisted = json.loads(verification_path.read_text(encoding="utf-8"))
            verification_mode = verification_path.stat().st_mode & 0o077

        python = sys.executable
        sorted_source_files = sorted(
            str(path.relative_to(ROOT))
            for path in (ROOT / "src" / "skill2workflow").glob("*.py")
        )
        expected_arguments = [
            [
                python,
                "-m",
                "unittest",
                "tests.test_controlled_lark_pilot",
                "tests.test_controlled_lark_pilot_evidence",
                "tests.test_controlled_lark_pilot_docs",
                "-v",
            ],
            [python, "-m", "unittest", "discover", "-s", "tests", "-v"],
            [
                python,
                "-m",
                "py_compile",
                *sorted_source_files,
                "examples/connectors/lark_task_connector.py",
            ],
            [python, "scripts/secret_hygiene.py", "examples/workflows"],
            [
                python,
                "scripts/lark_task_connector_smoke.py",
                "--work-dir",
                str(resolved_work_dir / "private" / "connector-smoke"),
            ],
            [
                python,
                "scripts/lark_task_pilot_smoke.py",
                "--work-dir",
                str(resolved_work_dir / "private" / "dry-run-smoke"),
            ],
            ["git", "diff", "--check"],
        ]
        self.assertEqual(runner.arguments, expected_arguments)
        self.assertEqual(runner.working_directories, [ROOT] * 7)
        self.assertEqual(runner.capture_output, [True] * 7)
        for environment in runner.environments:
            self.assertNotIn("LARK_BOT_ACCESS_TOKEN", environment)
            self.assertNotIn("SKILL2WORKFLOW_LARK_TASK_LIVE", environment)
            self.assertEqual(environment["PYTHONPATH"], "src")
            self.assertEqual(environment["KEEP_ME"], "yes")
        self.assertTrue(result["all_passed"])
        self.assertEqual(
            [item["id"] for item in result["commands"]],
            [
                "focused-tests",
                "full-tests",
                "compile",
                "secret-hygiene",
                "connector-smoke",
                "dry-run-pilot-smoke",
                "diff-check",
            ],
        )
        self.assertEqual(result, persisted)
        self.assertEqual(
            set(result), {"schema_version", "all_passed", "commands"}
        )
        for item in result["commands"]:
            self.assertEqual(
                set(item), {"id", "exit_code", "passed", "duration_ms"}
            )
            self.assertIs(type(item["duration_ms"]), int)
            self.assertGreaterEqual(item["duration_ms"], 0)
        encoded = json.dumps(result)
        self.assertNotIn("private-command-stdout", encoded)
        self.assertNotIn("private-command-stderr", encoded)
        self.assertNotIn("private-token", encoded)
        self.assertEqual(verification_mode, 0)

    def test_verify_pilot_records_nonzero_command_without_short_circuiting(self):
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)
            runner = _FakeCommandRunner([1, 0, 0, 0, 0, 0, 0])

            result = verify_pilot(ROOT, work_dir, command_runner=runner)

        self.assertFalse(result["all_passed"])
        self.assertEqual(len(runner.arguments), 7)
        self.assertEqual(result["commands"][0]["exit_code"], 1)
        self.assertFalse(result["commands"][0]["passed"])

    def test_decide_approve_requires_all_live_guards_and_returns_redacted_summary(self):
        with TemporaryDirectory() as tmp:
            work_dir, started = _start_waiting_pilot(tmp)
            transport = _FakeTransport()
            environment = {
                "SKILL2WORKFLOW_LARK_TASK_LIVE": "1",
                "LARK_BOT_ACCESS_TOKEN": "private-token",
            }
            with patch.dict(os.environ, environment, clear=True):
                result = decide_pilot_run(
                    ROOT,
                    work_dir,
                    started["run_id"],
                    approved=True,
                    confirmed_live=True,
                    now=NOW,
                    transport=transport,
                )
            control = LocalControlPlane(work_dir / "state", storage="sqlite")
            run = control.get_run(started["run_id"])
            events = control.list_audit_events(run_id=started["run_id"])

        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(result["gate_decision"], "approved")
        self.assertTrue(result["connector_invoked"])
        self.assertEqual(result["connector_status"], "completed")
        self.assertEqual(result["credential_status"], "resolved")
        self.assertEqual(result["provider_status"], "completed")
        self.assertTrue(result["idempotency_key_present"])
        self.assertTrue(result["lark_task_id_present"])
        self.assertEqual(
            set(result),
            {
                "connector_invoked",
                "connector_status",
                "credential_status",
                "gate_decision",
                "idempotency_key_present",
                "lark_task_id_present",
                "provider_status",
                "run_id",
                "run_status",
                "workflow_id",
                "workflow_version",
            },
        )
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["context"]["input"], _valid_case())
        self.assertTrue(
            any(event.get("type") == "run_resumed" for event in events)
        )
        self.assertTrue(
            any(event.get("type") == "connector_completed" for event in events)
        )
        self.assertEqual(len(transport.calls), 1)
        encoded = json.dumps({"result": result, "events": events, "run": run})
        for forbidden in (
            "private-token",
            "private-task-guid",
            "private-provider-message",
        ):
            self.assertNotIn(forbidden, encoded)
        encoded_audit = json.dumps(events)
        for private_value in _valid_case().values():
            self.assertNotIn(private_value, encoded_audit)
        summary = json.dumps(result)
        for private_value in _valid_case().values():
            self.assertNotIn(private_value, summary)

    def test_decide_reject_needs_no_token_and_never_calls_transport(self):
        with TemporaryDirectory() as tmp:
            work_dir, started = _start_waiting_pilot(tmp)
            transport = _FakeTransport()
            with patch.dict(os.environ, {}, clear=True):
                result = decide_pilot_run(
                    ROOT,
                    work_dir,
                    started["run_id"],
                    approved=False,
                    now=NOW,
                    transport=transport,
                )
            control = LocalControlPlane(work_dir / "state", storage="sqlite")
            run = control.get_run(started["run_id"])
            events = control.list_audit_events(run_id=started["run_id"])

        self.assertEqual(result["run_status"], "failed")
        self.assertEqual(result["gate_decision"], "rejected")
        self.assertFalse(result["connector_invoked"])
        self.assertEqual(run["status"], "failed")
        self.assertTrue(
            any(
                event.get("type") == "run_resumed"
                and event.get("approved") is False
                for event in events
            )
        )
        self.assertFalse(
            any(str(event.get("type", "")).startswith("connector_") for event in events)
        )
        self.assertEqual(transport.calls, [])

    def test_decide_approve_fails_before_resume_when_confirmation_switch_or_token_is_missing(self):
        with TemporaryDirectory() as tmp:
            work_dir, started = _start_waiting_pilot(tmp)
            transport = _FakeTransport()
            cases = [
                (
                    {
                        "SKILL2WORKFLOW_LARK_TASK_LIVE": "1",
                        "LARK_BOT_ACCESS_TOKEN": "token",
                    },
                    False,
                    "confirmation",
                ),
                (
                    {"LARK_BOT_ACCESS_TOKEN": "token"},
                    True,
                    "SKILL2WORKFLOW_LARK_TASK_LIVE=1",
                ),
                (
                    {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"},
                    True,
                    "LARK_BOT_ACCESS_TOKEN",
                ),
                (
                    {
                        "SKILL2WORKFLOW_LARK_TASK_LIVE": "true",
                        "LARK_BOT_ACCESS_TOKEN": "token",
                    },
                    True,
                    "SKILL2WORKFLOW_LARK_TASK_LIVE=1",
                ),
                (
                    {
                        "SKILL2WORKFLOW_LARK_TASK_LIVE": "1 ",
                        "LARK_BOT_ACCESS_TOKEN": "token",
                    },
                    True,
                    "SKILL2WORKFLOW_LARK_TASK_LIVE=1",
                ),
            ]
            for environment, confirmed, expected in cases:
                with self.subTest(expected=expected), patch.dict(
                    os.environ,
                    environment,
                    clear=True,
                ):
                    with self.assertRaisesRegex(ValueError, expected):
                        decide_pilot_run(
                            ROOT,
                            work_dir,
                            started["run_id"],
                            approved=True,
                            confirmed_live=confirmed,
                            now=NOW,
                            transport=transport,
                        )
            control = LocalControlPlane(work_dir / "state", storage="sqlite")
            run = control.get_run(started["run_id"])

        self.assertEqual(run["status"], "waiting")
        self.assertEqual(transport.calls, [])

    def test_decide_requires_approved_to_be_an_exact_boolean(self):
        for approved in ("false", 1, 0, None):
            with self.subTest(approved=approved), TemporaryDirectory() as tmp:
                work_dir, started = _start_waiting_pilot(tmp)
                transport = _FakeTransport()
                environment = {
                    "SKILL2WORKFLOW_LARK_TASK_LIVE": "1",
                    "LARK_BOT_ACCESS_TOKEN": "private-token",
                }
                with patch.dict(os.environ, environment, clear=True):
                    with self.assertRaisesRegex(
                        ValueError,
                        "approved must be a boolean",
                    ):
                        decide_pilot_run(
                            ROOT,
                            work_dir,
                            started["run_id"],
                            approved=approved,
                            confirmed_live=True,
                            now=NOW,
                            transport=transport,
                        )
                control = LocalControlPlane(work_dir / "state", storage="sqlite")
                run = control.get_run(started["run_id"])
                self.assertEqual(run["status"], "waiting")
                self.assertEqual(transport.calls, [])

    def test_decide_approve_requires_confirmation_to_be_exact_boolean_true(self):
        for confirmed_live in ("true", 1):
            case = self.subTest(confirmed_live=confirmed_live)
            with case, TemporaryDirectory() as tmp:
                work_dir, started = _start_waiting_pilot(tmp)
                transport = _FakeTransport()
                environment = {
                    "SKILL2WORKFLOW_LARK_TASK_LIVE": "1",
                    "LARK_BOT_ACCESS_TOKEN": "private-token",
                }
                with patch.dict(os.environ, environment, clear=True):
                    with self.assertRaisesRegex(
                        ValueError,
                        "explicit boolean confirmation",
                    ):
                        decide_pilot_run(
                            ROOT,
                            work_dir,
                            started["run_id"],
                            approved=True,
                            confirmed_live=confirmed_live,
                            now=NOW,
                            transport=transport,
                        )
                control = LocalControlPlane(work_dir / "state", storage="sqlite")
                run = control.get_run(started["run_id"])
                self.assertEqual(run["status"], "waiting")
                self.assertEqual(transport.calls, [])

    def test_decide_rejects_second_decision_for_terminal_run_without_transport(self):
        with TemporaryDirectory() as tmp:
            work_dir, started = _start_waiting_pilot(tmp)
            transport = _FakeTransport()
            environment = {
                "SKILL2WORKFLOW_LARK_TASK_LIVE": "1",
                "LARK_BOT_ACCESS_TOKEN": "private-token",
            }
            with patch.dict(os.environ, environment, clear=True):
                decide_pilot_run(
                    ROOT,
                    work_dir,
                    started["run_id"],
                    approved=True,
                    confirmed_live=True,
                    now=NOW,
                    transport=transport,
                )
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ValueError, "not waiting"):
                    decide_pilot_run(
                        ROOT,
                        work_dir,
                        started["run_id"],
                        approved=True,
                        confirmed_live=True,
                        now=NOW,
                        transport=transport,
                    )

        self.assertEqual(len(transport.calls), 1)

    def test_validate_controlled_live_binding_rejects_each_fixed_property(self):
        workflow = _published_controlled_workflow()
        run = {
            "run_id": "run_controlled",
            "workflow_id": "workflow_controlled_lark_pilot",
            "workflow_version": "0.1.0",
            "status": "waiting",
            "current_node": "review_renewal_risk",
            "workflow": deepcopy(workflow),
        }
        _validate_controlled_live_binding(workflow, run)

        def workflow_meta(target, key, value):
            target["workflow"][key] = value

        def run_field(target, key, value):
            target[key] = value

        def connector_field(target, key, value):
            node = next(
                item for item in target["nodes"] if item["id"] == "create_lark_task"
            )
            node["connector"][key] = value

        def credential_handle(target, _key, value):
            node = next(
                item for item in target["nodes"] if item["id"] == "create_lark_task"
            )
            node["connector"]["credentials"][0]["handle"] = value

        def connector_node_id(target, _key, value):
            node = next(
                item for item in target["nodes"] if item["id"] == "create_lark_task"
            )
            node["id"] = value

        cases = [
            ("workflow id", "workflow", workflow_meta, "id", "workflow_other"),
            ("workflow version", "workflow", workflow_meta, "version", "9.9.9"),
            ("run workflow id", "run", run_field, "workflow_id", "workflow_other"),
            ("run workflow version", "run", run_field, "workflow_version", "9.9.9"),
            ("current gate", "run", run_field, "current_node", "other_gate"),
            ("connector id", "workflow", connector_field, "id", "http"),
            ("operation", "workflow", connector_field, "operation", "delete_task"),
            ("mode", "workflow", connector_field, "mode", "dry_run"),
            (
                "credential handle",
                "workflow",
                credential_handle,
                "handle",
                "other_secret",
            ),
            ("run id", "run", run_field, "run_id", ""),
            ("node id", "workflow", connector_node_id, "id", "other_node"),
        ]
        for label, target_name, mutate, key, value in cases:
            candidate_workflow = deepcopy(workflow)
            candidate_run = deepcopy(run)
            target = candidate_workflow if target_name == "workflow" else candidate_run
            mutate(target, key, value)
            if target_name == "workflow":
                mutate(candidate_run["workflow"], key, value)
            with self.subTest(property=label), self.assertRaisesRegex(
                ValueError,
                "controlled pilot live binding is invalid",
            ):
                _validate_controlled_live_binding(candidate_workflow, candidate_run)

    def test_validate_controlled_live_binding_rejects_synchronized_extra_live_action(self):
        workflow = _published_controlled_workflow()
        first_live_action = next(
            node for node in workflow["nodes"] if node["id"] == "create_lark_task"
        )
        extra_live_action = deepcopy(first_live_action)
        extra_live_action["id"] = "create_second_lark_task"
        first_live_action["on_success"] = "create_second_lark_task"
        workflow["nodes"].append(extra_live_action)
        first_success_edge = next(
            edge for edge in workflow["edges"] if edge["id"] == "edge_task_end"
        )
        first_success_edge["id"] = "edge_task_second"
        first_success_edge["to"] = "create_second_lark_task"
        workflow["edges"].append(
            {
                "id": "edge_second_task_end",
                "from": "create_second_lark_task",
                "to": "end",
                "label": "next",
            }
        )
        workflow["edges"].append(
            {
                "id": "edge_second_task_failure",
                "from": "create_second_lark_task",
                "to": "failure",
                "label": "failure",
            }
        )
        run = {
            "run_id": "run_controlled",
            "workflow_id": "workflow_controlled_lark_pilot",
            "workflow_version": "0.1.0",
            "status": "waiting",
            "current_node": "review_renewal_risk",
            "workflow": deepcopy(workflow),
        }

        self.assertEqual(validate_workflow(workflow), [])
        with self.assertRaisesRegex(
            ValueError,
            "controlled pilot live binding is invalid",
        ):
            _validate_controlled_live_binding(workflow, run)

    def test_decide_rechecks_external_work_dir_before_charter_or_state_access(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_root = root / "repo"
            work_dir = repo_root / "forged-pilot"
            transport = _FakeTransport()
            with patch(
                "skill2workflow.controlled_lark_pilot.load_pilot_charter",
                side_effect=AssertionError("charter must not be loaded"),
            ) as load_charter, patch(
                "skill2workflow.controlled_lark_pilot._pilot_control_plane",
                side_effect=AssertionError("state must not be accessed"),
            ) as control_plane:
                with self.assertRaisesRegex(ValueError, "outside the repository"):
                    decide_pilot_run(
                        repo_root,
                        work_dir,
                        "run_private",
                        approved=False,
                        now=NOW,
                        transport=transport,
                    )

            load_charter.assert_not_called()
            control_plane.assert_not_called()
            self.assertEqual(transport.calls, [])

    def test_decide_rejects_run_state_that_does_not_match_requested_identity(self):
        workflow = _published_controlled_workflow()
        current = {
            "run_id": "run_other",
            "workflow_id": "workflow_controlled_lark_pilot",
            "workflow_version": "0.1.0",
            "status": "waiting",
            "current_node": "review_renewal_risk",
            "workflow": deepcopy(workflow),
        }

        class MismatchedRunControl:
            def __init__(self):
                self.resume_calls = []

            def get_run(self, run_id):
                return deepcopy(current)

            def get_workflow(self, workflow_id, workflow_version):
                return deepcopy(workflow)

            def resume_published_run(self, run_id, approved=True):
                self.resume_calls.append((run_id, approved))
                return {"status": "failed"}

            def list_audit_events(self, run_id=""):
                return []

        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)
            control = MismatchedRunControl()
            with patch(
                "skill2workflow.controlled_lark_pilot._pilot_control_plane",
                return_value=control,
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "controlled pilot run identity is invalid",
                ):
                    decide_pilot_run(
                        ROOT,
                        work_dir,
                        "run_requested",
                        approved=False,
                        now=NOW,
                    )

        self.assertEqual(control.resume_calls, [])

    def test_start_pilot_run_publishes_live_workflow_and_stops_at_gate(self):
        with TemporaryDirectory() as tmp:
            work_dir, result = _start_waiting_pilot(tmp)
            control = LocalControlPlane(work_dir / "state", storage="sqlite")
            run = control.get_run(result["run_id"])
            workflow = control.get_workflow(
                "workflow_controlled_lark_pilot",
                "0.1.0",
            )
            node = next(
                item for item in workflow["nodes"] if item["id"] == "create_lark_task"
            )
            non_sqlite_state = b"".join(
                path.read_bytes()
                for path in (work_dir / "state").rglob("*")
                if path.is_file() and path.suffix != ".sqlite3"
            )
            runs_sqlite_exists = (work_dir / "state" / "runs.sqlite3").is_file()
            runs_dir_exists = (work_dir / "state" / "runs").exists()

        self.assertEqual(
            set(result),
            {
                "current_node",
                "input_keys",
                "run_id",
                "run_status",
                "workflow_id",
                "workflow_version",
            },
        )
        self.assertEqual(result["run_status"], "waiting")
        self.assertEqual(result["current_node"], "review_renewal_risk")
        self.assertEqual(
            result["input_keys"],
            [
                "account_name",
                "due_at",
                "owner_open_id",
                "pilot_case_id",
                "renewal_risk",
            ],
        )
        self.assertEqual(run["status"], "waiting")
        self.assertEqual(run["context"]["input"], _valid_case())
        self.assertTrue(runs_sqlite_exists)
        self.assertFalse(runs_dir_exists)
        self.assertEqual(node["connector"]["mode"], "live")
        self.assertNotIn("Private Account", json.dumps(result))
        self.assertNotIn(b"Private Account", non_sqlite_state)

    def test_start_pilot_run_does_not_resolve_credentials_or_call_transport(self):
        transport_calls = []

        def forbidden_transport(*args, **kwargs):
            transport_calls.append((args, kwargs))
            raise AssertionError("start must not call live transport")

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            work_dir = root / "pilot"
            input_path = root / "case.json"
            initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)
            _write_private_case(input_path)
            with patch.dict(
                os.environ,
                {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"},
            ), patch.object(
                StaticCredentialProvider,
                "resolve",
                side_effect=AssertionError("start must not resolve credentials"),
            ) as resolve_credential:
                result = start_pilot_run(
                    ROOT,
                    work_dir,
                    input_path,
                    now=NOW,
                    transport=forbidden_transport,
                )

        self.assertEqual(result["run_status"], "waiting")
        resolve_credential.assert_not_called()
        self.assertEqual(transport_calls, [])

    def test_start_pilot_run_rechecks_external_work_dir_before_creating_state(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_root = root / "repo"
            work_dir = repo_root / "forged-pilot"
            private_dir = work_dir / "private"
            private_dir.mkdir(parents=True)
            (private_dir / "charter.json").write_text(
                json.dumps(_valid_charter()),
                encoding="utf-8",
            )
            input_path = root / "case.json"
            _write_private_case(input_path)

            with self.assertRaisesRegex(ValueError, "outside the repository"):
                start_pilot_run(repo_root, work_dir, input_path, now=NOW)

            self.assertFalse((work_dir / "state").exists())

    def test_initialize_pilot_creates_owner_only_private_workspace(self):
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "controlled-pilot"
            result = initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)

            self.assertEqual(result["status"], "initialized")
            self.assertEqual(result["workflow_id"], "workflow_controlled_lark_pilot")
            self.assertEqual(work_dir.stat().st_mode & 0o077, 0)
            self.assertEqual(
                (work_dir / "private" / "charter.json").stat().st_mode & 0o077,
                0,
            )
            self.assertTrue((work_dir / "state").is_dir())
            self.assertTrue((work_dir / "evidence").is_dir())

    def test_initialize_pilot_rejects_repository_work_dir(self):
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            initialize_pilot(ROOT, ROOT / ".pilot-private", _valid_charter(), now=NOW)

    def test_initialize_pilot_rejects_private_subdirectory_symlinks(self):
        for child_name in ("private", "state", "evidence"):
            with self.subTest(child_name=child_name), TemporaryDirectory() as tmp:
                work_dir = Path(tmp) / "pilot"
                work_dir.mkdir()
                target = Path(tmp) / "symlink-target"
                target.mkdir()
                os.chmod(target, 0o755)
                (work_dir / child_name).symlink_to(
                    target,
                    target_is_directory=True,
                )

                with self.assertRaisesRegex(ValueError, "symbolic link"):
                    initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)

                self.assertEqual(target.stat().st_mode & 0o777, 0o755)
                self.assertEqual(list(target.iterdir()), [])

    def test_initialize_pilot_rejects_charter_symlink_without_changing_target(self):
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            private_dir = work_dir / "private"
            private_dir.mkdir(parents=True)
            target = Path(tmp) / "charter-target.json"
            target.write_text("sentinel", encoding="utf-8")
            os.chmod(target, 0o640)
            (private_dir / "charter.json").symlink_to(target)

            with self.assertRaisesRegex(ValueError, "symbolic link"):
                initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)

            self.assertEqual(target.read_text(encoding="utf-8"), "sentinel")
            self.assertEqual(target.stat().st_mode & 0o777, 0o640)

    def test_initialize_pilot_rejects_non_directory_workspace_nodes(self):
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            work_dir.mkdir()
            state_path = work_dir / "state"
            state_path.write_text("sentinel", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "directory"):
                initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)

            self.assertEqual(state_path.read_text(encoding="utf-8"), "sentinel")

    def test_initialize_pilot_uses_private_temp_and_cleans_up_replace_failure(self):
        observed = {}

        def fail_replace(source, destination):
            observed["mode"] = Path(source).stat().st_mode & 0o777
            observed["destination"] = Path(destination).name
            raise OSError("replace failed")

        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            with patch(
                "skill2workflow.controlled_lark_pilot.os.replace",
                side_effect=fail_replace,
            ):
                with self.assertRaisesRegex(OSError, "replace failed"):
                    initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)

            self.assertEqual(
                observed,
                {"mode": 0o600, "destination": "charter.json"},
            )
            self.assertEqual(list((work_dir / "private").iterdir()), [])

    def test_charter_requires_consent_commercial_status_thresholds_and_active_dates(self):
        invalid_values = [
            ("team_consent_confirmed", False),
            ("assignee_consent_confirmed", False),
            ("commercial_engagement_confirmed", False),
            ("required_approved_runs", 4),
            ("required_distinct_days", 4),
            ("required_distinct_cases", 1),
            ("timezone", "UTC"),
        ]
        for key, value in invalid_values:
            charter = _valid_charter()
            charter[key] = value
            with self.subTest(key=key), TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):
                    initialize_pilot(ROOT, Path(tmp) / "pilot", charter, now=NOW)

    def test_charter_rejects_unknown_fields(self):
        charter = _valid_charter()
        charter["account_name"] = "must stay private"
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "only the approved fields"):
                initialize_pilot(ROOT, Path(tmp) / "pilot", charter, now=NOW)

    def test_load_pilot_charter_rejects_expired_charter(self):
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)
            with self.assertRaisesRegex(ValueError, "expired"):
                load_pilot_charter(
                    work_dir,
                    now=datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc),
                )

    def test_load_private_case_requires_external_owner_only_exact_shape(self):
        payload = _valid_case()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            os.chmod(path, 0o600)
            self.assertEqual(load_private_case(ROOT, path), payload)

            os.chmod(path, 0o644)
            with self.assertRaisesRegex(ValueError, "owner-only"):
                load_private_case(ROOT, path)

    def test_load_private_case_rejects_extra_fields(self):
        payload = _valid_case()
        payload["lark_token"] = "must-not-enter-case"
        self._assert_private_case_rejected(payload, "only the approved fields")

    def test_load_private_case_rejects_missing_fields(self):
        for key in _valid_case():
            payload = _valid_case()
            del payload[key]
            with self.subTest(key=key):
                self._assert_private_case_rejected(
                    payload,
                    "only the approved fields",
                )

    def test_load_private_case_rejects_empty_fields(self):
        for key in _valid_case():
            payload = _valid_case()
            payload[key] = " "
            with self.subTest(key=key):
                self._assert_private_case_rejected(payload, "non-empty strings")

    def test_load_private_case_rejects_non_opaque_case_ids(self):
        for pilot_case_id in (
            "account-001",
            "customer-001",
            "owner@example.com",
            "case 001",
        ):
            payload = _valid_case()
            payload["pilot_case_id"] = pilot_case_id
            with self.subTest(pilot_case_id=pilot_case_id):
                self._assert_private_case_rejected(payload, "opaque identifier")

    def _assert_private_case_rejected(self, payload, message):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            os.chmod(path, 0o600)
            with self.assertRaisesRegex(ValueError, message):
                load_private_case(ROOT, path)
