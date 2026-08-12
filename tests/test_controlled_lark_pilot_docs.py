import io
import json
import os
import tempfile
import unittest
import warnings
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]

from skill2workflow.controlled_lark_pilot import main


class ControlledLarkPilotCLITests(unittest.TestCase):
    def _invoke(self, arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with warnings.catch_warnings(), redirect_stdout(
            stdout
        ), redirect_stderr(stderr):
            warnings.simplefilter("ignore", ResourceWarning)
            result = main(arguments)
        return result, stdout.getvalue(), stderr.getvalue()

    def _assert_compact_json_line(self, stdout):
        self.assertTrue(stdout.endswith("\n"))
        self.assertEqual(stdout.count("\n"), 1)
        payload = json.loads(stdout)
        self.assertEqual(
            stdout,
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        )
        return payload

    def _active_dates(self):
        today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        return today.isoformat(), (today + timedelta(days=30)).isoformat()

    def _init(self, work_dir):
        starts_on, expires_on = self._active_dates()
        return self._invoke(
            [
                "init",
                "--work-dir",
                str(work_dir),
                "--starts-on",
                starts_on,
                "--expires-on",
                expires_on,
                "--confirm-team-consent",
                "--confirm-assignee-consent",
                "--confirm-commercial-engagement",
            ]
        )

    def _write_case(self, path):
        path.write_text(
            json.dumps(
                {
                    "pilot_case_id": "case-opaque-001",
                    "account_name": "PRIVATE ACCOUNT VALUE",
                    "renewal_risk": "PRIVATE RISK VALUE",
                    "owner_open_id": "ou_private_assignee",
                    "due_at": "2026-08-15T09:00:00+08:00",
                }
            ),
            encoding="utf-8",
        )
        os.chmod(path, 0o600)

    def _write_decision(self, path, mode=0o600):
        path.write_text(
            json.dumps(
                {
                    "schema_version": "controlled-lark-pilot-decision-0.1.0",
                    "decision": "defer",
                    "partner_acknowledged": True,
                    "operator_acknowledged": True,
                    "commercial_engagement_confirmed": True,
                    "rationale": "REDACTED PRIVATE DECISION RATIONALE",
                }
            ),
            encoding="utf-8",
        )
        os.chmod(path, mode)

    def test_parser_dispatches_all_ten_commands_and_prints_only_compact_summaries(self):
        secret = "SHOULD-NOT-REACH-STDOUT"
        common = {
            "status": "ok",
            "run_id": "run_safe",
            "workflow_id": "workflow_controlled_lark_pilot",
            "workflow_version": "0.1.0",
            "run_status": "waiting",
            "current_node": "review_renewal_risk",
            "input_keys": ["pilot_case_id"],
            "preflight_ready": True,
            "connector_id": "lark_task",
            "operation": "create_task",
            "mode": "live",
            "task_title_present": True,
            "task_description_present": True,
            "assignee_present": True,
            "due_at_present": True,
            "provider_payload_constructed": True,
            "network_called": False,
            "gate_decision": "rejected",
            "connector_invoked": False,
            "connector_status": "",
            "credential_status": "",
            "provider_status": "",
            "idempotency_key_present": False,
            "lark_task_id_present": False,
            "file_count": 1,
            "run_count": 1,
            "approved_live_runs": 0,
            "distinct_calendar_days": 0,
            "distinct_private_cases": 0,
            "rejected_runs": 1,
            "unmet_conditions": ["approved_live_runs_threshold"],
            "exercise": "safe",
            "passed": True,
            "credential_resolution_attempted": False,
            "transport_attempted": False,
            "live_switch_enabled": False,
            "live_approval_blocked": True,
            "dry_run_status": "completed",
            "all_passed": True,
            "commands": [],
            "decision": "defer",
            "field_count": 5,
            "raw_private_value": secret,
            "rationale": secret,
            "token": secret,
            "provider_message": secret,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_dir = root / "pilot"
            case_path = root / "case.json"
            case_path.write_text("{}", encoding="utf-8")
            decision_path = root / "decision.json"
            self._write_decision(decision_path)
            starts_on, expires_on = self._active_dates()
            commands = (
                [
                    "init",
                    "--work-dir",
                    str(work_dir),
                    "--starts-on",
                    starts_on,
                    "--expires-on",
                    expires_on,
                    "--confirm-team-consent",
                    "--confirm-assignee-consent",
                    "--confirm-commercial-engagement",
                ],
                [
                    "case-template",
                    "--work-dir",
                    str(work_dir),
                    "--name",
                    "day-1",
                    "--case-id",
                    "case-opaque-001",
                ],
                ["start", "--work-dir", str(work_dir), "--input", str(case_path)],
                ["preflight", "--input", str(case_path)],
                [
                    "decide",
                    "--work-dir",
                    str(work_dir),
                    "--run-id",
                    "run_safe",
                    "--reject",
                ],
                ["evidence", "--work-dir", str(work_dir)],
                ["exercise-failure", "--work-dir", str(work_dir)],
                ["exercise-rollback", "--work-dir", str(work_dir)],
                ["verify", "--work-dir", str(work_dir)],
                [
                    "finalize",
                    "--work-dir",
                    str(work_dir),
                    "--decision-file",
                    str(decision_path),
                ],
            )
            targets = (
                "initialize_pilot",
                "create_private_case_template",
                "start_pilot_run",
                "preflight_pilot_case",
                "decide_pilot_run",
                "generate_pilot_evidence",
                "exercise_disabled_live",
                "exercise_rollback",
                "verify_pilot",
                "finalize_pilot",
            )
            for arguments, target in zip(commands, targets):
                with self.subTest(command=arguments[0]), patch(
                    "skill2workflow.controlled_lark_pilot." + target,
                    return_value=dict(common),
                ):
                    result, stdout, stderr = self._invoke(arguments)
                    self.assertEqual(result, 0)
                    self.assertEqual(stderr, "")
                    self._assert_compact_json_line(stdout)
                    self.assertNotIn(secret, stdout)

    def test_real_init_start_and_reject_flow_never_requires_vault_or_prints_private_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_dir = root / "pilot"
            case_path = root / "case.json"
            self._write_case(case_path)

            result, initialized_stdout, initialized_stderr = self._init(work_dir)
            self.assertEqual(result, 0)
            self.assertEqual(initialized_stderr, "")
            initialized = self._assert_compact_json_line(initialized_stdout)
            self.assertTrue(initialized["team_consent_confirmed"])
            self.assertTrue(initialized["assignee_consent_confirmed"])
            self.assertTrue(initialized["commercial_engagement_confirmed"])

            result, started_stdout, started_stderr = self._invoke(
                ["start", "--work-dir", str(work_dir), "--input", str(case_path)]
            )
            self.assertEqual(result, 0)
            self.assertEqual(started_stderr, "")
            started = self._assert_compact_json_line(started_stdout)
            self.assertEqual(started["run_status"], "waiting")
            self.assertTrue(started["preflight_ready"])

            original_get = os.environ.get

            def reject_without_token_access(key, default=None):
                if key == "LARK_BOT_ACCESS_TOKEN":
                    raise AssertionError("rejection must not read the token")
                return original_get(key, default)

            with patch.object(os.environ, "get", side_effect=reject_without_token_access):
                result, rejected_stdout, rejected_stderr = self._invoke(
                    [
                        "decide",
                        "--work-dir",
                        str(work_dir),
                        "--run-id",
                        started["run_id"],
                        "--reject",
                    ]
                )
            self.assertEqual(result, 0)
            self.assertEqual(rejected_stderr, "")
            rejected = self._assert_compact_json_line(rejected_stdout)
            self.assertEqual(rejected["gate_decision"], "rejected")
            self.assertFalse(rejected["connector_invoked"])
            combined = initialized_stdout + started_stdout + rejected_stdout
            for private_value in (
                "PRIVATE ACCOUNT VALUE",
                "PRIVATE RISK VALUE",
                "ou_private_assignee",
            ):
                self.assertNotIn(private_value, combined)

            charter = json.loads(
                (work_dir / "private" / "charter.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                set(charter),
                {
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
                },
            )

    def test_case_template_never_reads_vault_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_dir = root / "pilot"
            result, stdout, stderr = self._init(work_dir)
            self.assertEqual(result, 0)
            self.assertEqual(stderr, "")
            self._assert_compact_json_line(stdout)

            original_get = os.environ.get

            def reject_token_read(key, default=None):
                if key == "LARK_BOT_ACCESS_TOKEN":
                    raise AssertionError("case template must not read the token")
                return original_get(key, default)

            arguments = [
                "case-template",
                "--work-dir",
                str(work_dir),
                "--name",
                "day-1",
                "--case-id",
                "case-opaque-001",
            ]
            with patch.object(os.environ, "get", side_effect=reject_token_read):
                result, stdout, stderr = self._invoke(arguments)
            self.assertEqual(result, 0)
            self.assertEqual(stderr, "")
            summary = self._assert_compact_json_line(stdout)
            self.assertEqual(summary, {"status": "template_written", "field_count": 5})

            case_path = work_dir / "private" / "cases" / "day-1.json"
            original = case_path.read_bytes()
            self.assertEqual(case_path.stat().st_mode & 0o077, 0)
            self.assertNotIn("LARK_BOT_ACCESS_TOKEN", stdout)

            result, stdout, stderr = self._invoke(arguments)
            self.assertEqual(result, 1)
            self.assertEqual(stdout, "")
            self.assertEqual(stderr, "controlled pilot command failed\n")
            self.assertEqual(case_path.read_bytes(), original)

    def test_start_rejects_non_string_or_naive_case_values_with_fixed_error(self):
        invalid_cases = (
            ("account_name", 42),
            ("renewal_risk", ["private"]),
            ("owner_open_id", {"private": True}),
            ("pilot_case_id", False),
            ("due_at", None),
            ("due_at", "2026-08-15T09:00:00"),
        )
        for key, value in invalid_cases:
            with self.subTest(key=key, value=value), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                work_dir = root / "pilot"
                case_path = root / "case.json"
                case = {
                    "pilot_case_id": "case-opaque-001",
                    "account_name": "PRIVATE ACCOUNT VALUE",
                    "renewal_risk": "PRIVATE RISK VALUE",
                    "owner_open_id": "ou_private_assignee",
                    "due_at": "2026-08-15T09:00:00+08:00",
                }
                case[key] = value
                case_path.write_text(json.dumps(case), encoding="utf-8")
                os.chmod(case_path, 0o600)
                self.assertEqual(self._init(work_dir)[0], 0)

                result, stdout, stderr = self._invoke(
                    ["start", "--work-dir", str(work_dir), "--input", str(case_path)]
                )

                self.assertNotEqual(result, 0)
                self.assertEqual(stdout, "")
                self.assertEqual(stderr, "controlled pilot command failed\n")
                self.assertFalse((work_dir / "state" / "runs.sqlite3").exists())

    def test_approve_summary_and_parser_errors_do_not_echo_token_or_unknown_input(self):
        token = "vault-injected-secret-token"
        raw_provider_value = "raw-provider-task-value"
        response = {
            "run_id": "run_safe",
            "workflow_id": "workflow_controlled_lark_pilot",
            "workflow_version": "0.1.0",
            "run_status": "completed",
            "gate_decision": "approved",
            "connector_invoked": True,
            "connector_status": "completed",
            "credential_status": "resolved",
            "provider_status": "completed",
            "idempotency_key_present": True,
            "lark_task_id_present": True,
            "token": token,
            "provider_message": raw_provider_value,
        }
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ,
            {"LARK_BOT_ACCESS_TOKEN": token},
            clear=True,
        ), patch(
            "skill2workflow.controlled_lark_pilot.decide_pilot_run",
            return_value=response,
        ) as decide:
            result, stdout, stderr = self._invoke(
                [
                    "decide",
                    "--work-dir",
                    str(Path(temporary) / "pilot"),
                    "--run-id",
                    "run_safe",
                    "--approve",
                    "--confirm-live-create",
                ]
            )
        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self._assert_compact_json_line(stdout)
        self.assertNotIn(token, stdout + stderr)
        self.assertNotIn(raw_provider_value, stdout + stderr)
        self.assertTrue(decide.call_args.kwargs["approved"])
        self.assertTrue(decide.call_args.kwargs["confirmed_live"])

        result, stdout, stderr = self._invoke(["unknown-command", token])
        self.assertNotEqual(result, 0)
        self.assertEqual(stdout, "")
        self.assertNotIn(token, stderr)

    def test_reject_with_live_confirmation_is_a_fixed_error_before_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary, patch(
            "skill2workflow.controlled_lark_pilot.decide_pilot_run"
        ) as decide:
            result, stdout, stderr = self._invoke(
                [
                    "decide",
                    "--work-dir",
                    str(Path(temporary) / "pilot"),
                    "--run-id",
                    "run_safe",
                    "--reject",
                    "--confirm-live-create",
                ]
            )
        self.assertNotEqual(result, 0)
        self.assertEqual(stdout, "")
        self.assertEqual(
            stderr,
            "controlled pilot rejection does not use live confirmation\n",
        )
        decide.assert_not_called()

    def test_real_approve_path_fails_closed_when_each_live_guard_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_dir = root / "pilot"
            case_path = root / "case.json"
            self._write_case(case_path)
            self.assertEqual(self._init(work_dir)[0], 0)
            result, stdout, stderr = self._invoke(
                ["start", "--work-dir", str(work_dir), "--input", str(case_path)]
            )
            self.assertEqual(result, 0)
            self.assertEqual(stderr, "")
            run_id = self._assert_compact_json_line(stdout)["run_id"]
            base = [
                "decide",
                "--work-dir",
                str(work_dir),
                "--run-id",
                run_id,
                "--approve",
            ]
            cases = (
                ({}, base),
                ({}, base + ["--confirm-live-create"]),
                (
                    {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"},
                    base + ["--confirm-live-create"],
                ),
            )
            for environment, arguments in cases:
                with self.subTest(environment=environment), patch.dict(
                    os.environ,
                    environment,
                    clear=True,
                ):
                    result, stdout, stderr = self._invoke(arguments)
                    self.assertNotEqual(result, 0)
                    self.assertEqual(stdout, "")
                    self.assertEqual(stderr, "controlled pilot command failed\n")

    @unittest.skipUnless(os.name == "posix", "owner-only permissions require POSIX")
    def test_finalize_rejects_non_owner_only_and_symlink_decision_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_dir = root / "pilot"
            decision = root / "decision.json"
            self._write_decision(decision, mode=0o644)
            arguments = [
                "finalize",
                "--work-dir",
                str(work_dir),
                "--decision-file",
                str(decision),
            ]
            with patch("skill2workflow.controlled_lark_pilot.finalize_pilot") as finalize:
                result, stdout, stderr = self._invoke(arguments)
                self.assertNotEqual(result, 0)
                self.assertEqual(stdout, "")
                self.assertEqual(stderr, "controlled pilot command failed\n")
                finalize.assert_not_called()

                os.chmod(decision, 0o600)
                link = root / "decision-link.json"
                link.symlink_to(decision)
                arguments[-1] = str(link)
                result, stdout, stderr = self._invoke(arguments)
                self.assertNotEqual(result, 0)
                self.assertEqual(stdout, "")
                self.assertEqual(stderr, "controlled pilot command failed\n")
                finalize.assert_not_called()

    def test_finalize_rejects_decision_file_inside_repository(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary, \
                tempfile.TemporaryDirectory() as outside:
            decision = Path(temporary) / "decision.json"
            self._write_decision(decision)
            with patch("skill2workflow.controlled_lark_pilot.finalize_pilot") as finalize:
                result, stdout, stderr = self._invoke(
                    [
                        "finalize",
                        "--work-dir",
                        str(Path(outside) / "pilot"),
                        "--decision-file",
                        str(decision),
                    ]
                )
        self.assertNotEqual(result, 0)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "controlled pilot command failed\n")
        finalize.assert_not_called()

    def test_expected_operator_error_uses_fixed_redacted_stderr(self):
        private_error = "PRIVATE INPUT /private/path/provider-message"
        with tempfile.TemporaryDirectory() as temporary, patch(
            "skill2workflow.controlled_lark_pilot.start_pilot_run",
            side_effect=ValueError(private_error),
        ):
            result, stdout, stderr = self._invoke(
                [
                    "start",
                    "--work-dir",
                    str(Path(temporary) / "pilot"),
                    "--input",
                    private_error,
                ]
            )
        self.assertNotEqual(result, 0)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "controlled pilot command failed\n")
        self.assertNotIn(private_error, stderr)

    def test_start_invalid_utf8_uses_fixed_redacted_stderr_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_dir = root / "pilot"
            invalid_input = root / "invalid-case.json"
            invalid_input.write_bytes(b'\xff{"account_name":"private"}')
            os.chmod(invalid_input, 0o600)
            self.assertEqual(self._init(work_dir)[0], 0)

            result, stdout, stderr = self._invoke(
                [
                    "start",
                    "--work-dir",
                    str(work_dir),
                    "--input",
                    str(invalid_input),
                ]
            )

        self.assertNotEqual(result, 0)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "controlled pilot command failed\n")
        self.assertNotIn("Traceback", stderr)
        self.assertNotIn("account_name", stderr)

    def test_finalize_invalid_utf8_uses_fixed_redacted_stderr_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            decision = root / "invalid-decision.json"
            decision.write_bytes(b'\xff{"rationale":"private"}')
            os.chmod(decision, 0o600)

            with patch(
                "skill2workflow.controlled_lark_pilot.finalize_pilot"
            ) as finalize:
                result, stdout, stderr = self._invoke(
                    [
                        "finalize",
                        "--work-dir",
                        str(root / "pilot"),
                        "--decision-file",
                        str(decision),
                    ]
                )

        self.assertNotEqual(result, 0)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "controlled pilot command failed\n")
        self.assertNotIn("Traceback", stderr)
        self.assertNotIn("rationale", stderr)
        finalize.assert_not_called()


class ControlledLarkPilotDocumentationTests(unittest.TestCase):
    def test_controlled_pilot_runbook_documents_every_safe_phase(self):
        runbook = (ROOT / "docs" / "controlled-live-pilot.md").read_text(
            encoding="utf-8"
        )
        for command in (
            " init ",
            " case-template ",
            " preflight ",
            " start ",
            " decide ",
            " evidence ",
            " exercise-failure ",
            " exercise-rollback ",
            " verify ",
            " finalize ",
        ):
            self.assertIn(command, runbook)
        self.assertIn("paid assisted engagement", runbook)
        self.assertIn("vibe vault run --env LARK_APP_SECRET", runbook)
        self.assertIn("LARK_APP_ID", runbook)
        self.assertIn("chmod 600", runbook)
        self.assertIn("five distinct calendar days", runbook)
        self.assertIn("Asia/Shanghai", runbook)
        self.assertIn("case-001", runbook)
        self.assertIn("case-002", runbook)
        self.assertIn('"const": "case-002"', runbook)
        self.assertIn("Day 4 exact schema", runbook)
        self.assertIn("docs/pilot-evidence/loop-40", runbook)
        self.assertIn("continue", runbook)
        self.assertIn("harden", runbook)
        self.assertIn("defer", runbook)
        self.assertIn("must not advance Loop 40", runbook)

    def test_runbook_documents_exact_private_schemas_and_safety_boundaries(self):
        runbook = (ROOT / "docs" / "controlled-live-pilot.md").read_text(
            encoding="utf-8"
        )
        for field in (
            '"pilot_case_id"',
            '"account_name"',
            '"renewal_risk"',
            '"owner_open_id"',
            '"due_at"',
            '"schema_version"',
            '"partner_acknowledged"',
            '"operator_acknowledged"',
            '"commercial_engagement_confirmed"',
            '"rationale"',
        ):
            self.assertIn(field, runbook)
        self.assertIn("repo", runbook.lower())
        self.assertIn("owner-only", runbook)
        self.assertIn("fixed Feishu domestic", runbook)
        self.assertIn("one `create_task` action", runbook)
        self.assertIn("dry-run remains the default", runbook)
        self.assertIn("does not resolve Vault credentials", runbook)
        self.assertIn("does not make a network request", runbook)
        self.assertIn("runs the same no-network preflight", runbook)
        self.assertIn("new work directory", runbook)
        self.assertIn("rejects every later `--approve`", runbook)
        self.assertIn("rotate or delete", runbook)
        self.assertIn("stop", runbook.lower())

    def test_docs_preserve_dry_run_and_narrow_live_boundaries(self):
        connectors = (ROOT / "docs" / "connectors.md").read_text(encoding="utf-8")
        examples = (ROOT / "docs" / "examples.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/controlled-live-pilot.md", connectors)
        self.assertIn("dry-run remains the default", connectors)
        self.assertIn("controlled real-team pilot", examples)
        self.assertIn("docs/pilot-evidence/loop-40/", readme)
        self.assertIn("docs/controlled-live-pilot.md", readme)
        self.assertIn("Loop 40", readme)
        self.assertIn("Current maturity: Self-hosted Beta", readme)
        self.assertIn("Delivery Loops 1-55 are complete", readme)

    def test_deferral_review_records_only_supported_findings_and_reentry_gate(self):
        review = (ROOT / "docs" / "controlled-pilot-deferral-review.md").read_text(
            encoding="utf-8"
        )
        normalized = " ".join(review.split())

        self.assertIn("# Controlled Pilot Deferral Review", normalized)
        self.assertIn("`validation_failed`", normalized)
        self.assertIn("cannot attribute", normalized)
        self.assertIn("raw provider message", normalized)
        self.assertIn("no retry", normalized)
        self.assertIn("fresh partner and operator authorization", normalized)
        self.assertIn("new private work directory", normalized)
        self.assertIn("no-network `preflight`", normalized)
        self.assertIn("five approved live runs", normalized)
        self.assertNotIn("root cause was", normalized.lower())


if __name__ == "__main__":
    unittest.main()
