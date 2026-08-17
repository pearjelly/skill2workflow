import json
import threading
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.cli import MAX_CLI_JSON_DOCUMENT_BYTES, main
from skill2workflow.schedules import RecurringScheduleStore
from skill2workflow.state_layout import STATE_LAYOUT_MARKER
from skill2workflow.triggers import MAX_TRIGGER_INPUT_BYTES


class CliTests(TestCase):
    def test_cancel_run_command_cancels_waiting_published_run(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            workflow_path = root / "workflow.json"
            workflow_path.write_text(json.dumps(_approval_workflow()), encoding="utf-8")
            run_stdout = StringIO()
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    main(
                        [
                            "publish",
                            str(workflow_path),
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )
            with redirect_stdout(run_stdout):
                self.assertEqual(
                    main(
                        [
                            "run-published",
                            "workflow_demo",
                            "--version",
                            "0.1.0",
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )
            run_id = json.loads(run_stdout.getvalue())["run_id"]
            cancel_stdout = StringIO()

            with redirect_stdout(cancel_stdout):
                exit_code = main(
                    [
                        "cancel-run",
                        run_id,
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )

        self.assertEqual(exit_code, 0)
        cancellation = json.loads(cancel_stdout.getvalue())
        self.assertEqual(cancellation["status"], "cancelled")
        self.assertEqual(set(cancellation), {"run_id", "status"})

    def test_cancel_run_missing_id_uses_fixed_error_without_traceback(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            from skill2workflow.control_plane import LocalControlPlane

            LocalControlPlane(state_dir, storage="sqlite")
            stderr = StringIO()
            with redirect_stderr(stderr):
                exit_code = main(
                    [
                        "cancel-run",
                        "run_missing123",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue(), "run not found\n")

    def test_service_action_commands_keep_remote_operator_contract_compact(self):
        resume_stdout = StringIO()
        cancel_stdout = StringIO()
        token_file = Path("/private/ingress.token")
        with patch(
            "skill2workflow.cli.post_run_resume",
            return_value={"run_id": "run_remote_1", "status": "failed", "approved": False},
        ) as resume:
            with redirect_stdout(resume_stdout):
                resume_exit = main(
                    [
                        "service-resume",
                        "run_remote_1",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                        "--reject",
                    ]
                )
        with patch(
            "skill2workflow.cli.post_run_cancel",
            return_value={"run_id": "run_remote_1", "status": "cancelled"},
        ) as cancel:
            with redirect_stdout(cancel_stdout):
                cancel_exit = main(
                    [
                        "service-cancel",
                        "run_remote_1",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(resume_exit, 0)
        self.assertEqual(cancel_exit, 0)
        self.assertEqual(json.loads(resume_stdout.getvalue())["approved"], False)
        self.assertEqual(json.loads(cancel_stdout.getvalue())["status"], "cancelled")
        resume.assert_called_once_with(
            "https://service.example",
            token_file,
            "run_remote_1",
            approved=False,
        )
        cancel.assert_called_once_with("https://service.example", token_file, "run_remote_1")

    def test_service_show_command_prints_redacted_run_detail(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-run-detail-0.1.0",
            "run": {"run_id": "run_remote_1", "status": "waiting"},
            "events": [],
            "window": {"max_events": 50, "total": 0, "returned": 0, "truncated": False},
        }
        with patch(
            "skill2workflow.cli.fetch_run_detail",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-show",
                        "run_remote_1",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with("https://service.example", token_file, "run_remote_1")

    def test_service_runs_command_prints_redacted_run_list(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-run-list-0.1.0",
            "summary": {
                "total": 0,
                "status_counts": {
                    "created": 0,
                    "running": 0,
                    "waiting": 0,
                    "completed": 0,
                    "failed": 0,
                    "cancelled": 0,
                    "interrupted": 0,
                    "other": 0,
                },
            },
            "runs": [],
            "window": {"max_items": 100, "total": 0, "returned": 0, "truncated": False},
        }
        with patch(
            "skill2workflow.cli.fetch_run_list",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-runs",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with("https://service.example", token_file)

    def test_service_run_page_command_prints_filtered_cursor_page(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-run-list-0.2.0",
            "summary": {"total": 0, "status_counts": {
                "created": 0, "running": 0, "waiting": 0, "completed": 0,
                "failed": 0, "cancelled": 0, "interrupted": 0, "other": 0,
            }},
            "filters": {"status": "failed", "workflow_id": "workflow"},
            "runs": [],
            "window": {"max_items": 25, "total": 0, "returned": 0, "has_more": False, "next_cursor": None},
        }
        with patch(
            "skill2workflow.cli.fetch_run_page",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-run-page",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                        "--status",
                        "failed",
                        "--workflow-id",
                        "workflow",
                        "--cursor",
                        "cursor-token",
                        "--max-items",
                        "25",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with(
            "https://service.example",
            token_file,
            max_items=25,
            cursor="cursor-token",
            status="failed",
            workflow_id="workflow",
        )

    def test_service_recurring_schedules_command_prints_redacted_inventory(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-recurring-schedule-list-0.1.0",
            "summary": {
                "total": 0,
                "status_counts": {"active": 0, "disabled": 0, "other": 0},
            },
            "schedules": [],
            "window": {"max_items": 100, "total": 0, "returned": 0, "truncated": False},
        }
        with patch(
            "skill2workflow.cli.fetch_recurring_schedule_list",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-recurring-schedules",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with("https://service.example", token_file)

    def test_service_recurring_dispatches_command_supports_schedule_filter(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-recurring-schedule-dispatch-list-0.1.0",
            "schedule_id": "schedule_hourly_report",
            "summary": {
                "total": 0,
                "status_counts": {
                    "claimed": 0,
                    "completed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "uncertain": 0,
                    "other": 0,
                },
            },
            "dispatches": [],
            "window": {"max_items": 100, "total": 0, "returned": 0, "truncated": False},
        }
        with patch(
            "skill2workflow.cli.fetch_recurring_schedule_dispatches",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-recurring-dispatches",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                        "--schedule-id",
                        "schedule_hourly_report",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with(
            "https://service.example", token_file, "schedule_hourly_report"
        )

    def test_service_recurring_dispatch_page_command_supports_cursor(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-recurring-schedule-dispatch-page-0.1.0",
            "schedule_id": "schedule_hourly_report",
            "summary": {
                "total": 1,
                "status_counts": {
                    "claimed": 0, "completed": 1, "failed": 0,
                    "skipped": 0, "uncertain": 0, "other": 0,
                },
            },
            "dispatches": [],
            "window": {
                "max_items": 1, "total": 1, "returned": 0,
                "has_more": True, "next_cursor": "next-page",
            },
        }
        with patch(
            "skill2workflow.cli.fetch_recurring_schedule_dispatch_page",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-recurring-dispatch-page",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                        "--schedule-id",
                        "schedule_hourly_report",
                        "--cursor",
                        "cursor-token",
                        "--max-items",
                        "1",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with(
            "https://service.example",
            token_file,
            schedule_id="schedule_hourly_report",
            max_items=1,
            cursor="cursor-token",
        )

    def test_service_workflow_artifacts_command_prints_report(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-workflow-artifact-report-0.1.0",
            "status": "clean",
            "summary": {
                "registry_records": 0,
                "referenced_artifacts": 0,
                "filesystem_artifacts": 0,
                "healthy": 0,
                "issue_count": 0,
                "missing": 0,
                "unsafe_reference": 0,
                "unsafe_artifact": 0,
                "invalid_json": 0,
                "oversized": 0,
                "checksum_mismatch": 0,
                "orphaned": 0,
                "truncated": False,
            },
            "issues": [],
        }
        with patch(
            "skill2workflow.cli.fetch_workflow_artifact_report",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-workflow-artifacts",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with("https://service.example", token_file)

    def test_service_backup_readiness_command_prints_report(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-backup-readiness-0.1.0",
            "status": "blocked",
            "storage": "sqlite",
            "state_layout_version": "skill2workflow-sqlite-layout-0.1.0",
            "database_count": 3,
            "workflow_artifact_count": 0,
            "active_scheduler_lease": True,
            "scheduler_database_synthesized": False,
            "backup_allowed": False,
            "blocking_reasons": ["active_scheduler_lease"],
        }
        with patch(
            "skill2workflow.cli.fetch_backup_readiness",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-backup-readiness",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with("https://service.example", token_file)

    def test_service_backup_inventory_command_prints_inventory(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-remote-backup-inventory-0.1.0",
            "status": "ok",
            "total": 1,
            "backups": [],
            "window": {"max_items": 7, "returned": 0, "truncated": True},
        }
        with patch(
            "skill2workflow.cli.fetch_backup_inventory",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-backup-inventory",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                        "--max-items",
                        "7",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with(
            "https://service.example", token_file, max_items=7
        )

    def test_service_backup_inventory_page_command_prints_page(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-remote-backup-inventory-page-0.1.0",
            "status": "ok",
            "total": 2,
            "backups": [],
            "window": {
                "max_items": 7,
                "total": 2,
                "returned": 0,
                "has_more": True,
                "next_cursor": "cursor-next",
            },
        }
        with patch(
            "skill2workflow.cli.fetch_backup_inventory_page",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-backup-inventory-page",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                        "--max-items",
                        "7",
                        "--cursor",
                        "cursor-token",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with(
            "https://service.example",
            token_file,
            max_items=7,
            cursor="cursor-token",
        )

    def test_service_backup_retention_plan_command_prints_plan(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        policy_file = Path("/private/backup-retention.json")
        expected = {
            "schema_version": "skill2workflow-remote-backup-retention-plan-0.1.0",
            "status": "blocked",
            "storage": "filesystem",
            "policy_sha256": "a" * 64,
            "expire_before": "2026-08-14T00:00:03+00:00",
            "minimum_keep": 1,
            "inventory": {"max_items": 1000, "returned": 1000, "truncated": True},
            "summary": {
                "valid_backups": None,
                "invalid_backups": None,
                "eligible_backups": None,
                "eligible_bytes": None,
                "preserved_backups": None,
                "preserved_bytes": None,
            },
            "blocking_reasons": ["inventory_truncated"],
        }
        with patch(
            "skill2workflow.cli.fetch_backup_retention_plan", return_value=expected
        ) as fetch, patch(
            "skill2workflow.cli._load_json", return_value={"policy": "value"}
        ):
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-backup-retention-plan",
                        str(policy_file),
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with(
            "https://service.example", token_file, {"policy": "value"}
        )

    def test_service_retention_readiness_command_loads_policy_and_prints_report(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        policy_file = Path("/private/retention.json")
        policy = {"schema_version": "skill2workflow-retention-policy-0.3.0"}
        expected = {
            "schema_version": "skill2workflow-retention-readiness-0.1.0",
            "status": "blocked",
        }
        with patch("skill2workflow.cli._load_json", return_value=policy) as load, patch(
            "skill2workflow.cli.fetch_retention_readiness",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-retention-readiness",
                        str(policy_file),
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        load.assert_called_once_with(policy_file)
        fetch.assert_called_once_with("https://service.example", token_file, policy)

    def test_service_operational_readiness_command_prints_report(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-operational-readiness-0.1.0",
            "status": "ready",
        }
        with patch(
            "skill2workflow.cli.fetch_operational_readiness",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-operational-readiness",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with("https://service.example", token_file)

    def test_service_probe_command_prints_contract_and_maps_ready_exit_code(self):
        stdout = StringIO()
        expected = {
            "schema_version": "skill2workflow-service-probe-0.1.0",
            "status": "ready",
            "health": {"status": "ok", "http_status": 200},
            "readiness": {"status": "ready", "http_status": 200},
        }
        with patch("skill2workflow.cli.fetch_service_probe", return_value=expected) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    ["service-probe", "--service-url", "https://service.example"]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with("https://service.example")

    def test_service_probe_command_maps_not_ready_exit_code(self):
        stdout = StringIO()
        expected = {
            "schema_version": "skill2workflow-service-probe-0.1.0",
            "status": "not_ready",
            "health": {"status": "ok", "http_status": 200},
            "readiness": {"status": "not_ready", "http_status": 503},
        }
        with patch("skill2workflow.cli.fetch_service_probe", return_value=expected):
            with redirect_stdout(stdout):
                exit_code = main(
                    ["service-probe", "--service-url", "https://service.example"]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(json.loads(stdout.getvalue()), expected)

    def test_service_wait_command_prints_ready_contract_and_options(self):
        stdout = StringIO()
        expected = {
            "schema_version": "skill2workflow-service-probe-0.1.0",
            "status": "ready",
            "health": {"status": "ok", "http_status": 200},
            "readiness": {"status": "ready", "http_status": 200},
        }
        with patch("skill2workflow.cli.wait_for_service_ready", return_value=expected) as wait:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-wait",
                        "--service-url",
                        "https://service.example",
                        "--timeout-seconds",
                        "12",
                        "--poll-interval-seconds",
                        "0.25",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        wait.assert_called_once_with(
            "https://service.example",
            timeout_seconds=12.0,
            poll_interval_seconds=0.25,
        )

    def test_service_wait_command_maps_unavailable_exit_code(self):
        stdout = StringIO()
        expected = {
            "schema_version": "skill2workflow-service-probe-0.1.0",
            "status": "unavailable",
            "health": {"status": "unavailable", "http_status": 0},
            "readiness": {"status": "unavailable", "http_status": 0},
        }
        with patch("skill2workflow.cli.wait_for_service_ready", return_value=expected):
            with redirect_stdout(stdout):
                exit_code = main(
                    ["service-wait", "--service-url", "https://service.example"]
                )

        self.assertEqual(exit_code, 2)
        self.assertEqual(json.loads(stdout.getvalue()), expected)

    def test_service_audit_integrity_command_prints_report(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-audit-integrity-0.1.0",
            "status": "valid",
            "algorithm": "sha256-chain-v1",
            "event_count": 3,
            "head_digest": "a" * 64,
            "first_invalid_sequence": 0,
            "reason": "",
        }
        with patch(
            "skill2workflow.cli.fetch_audit_integrity",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-audit-integrity",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with("https://service.example", token_file)

    def test_service_runtime_info_command_prints_report(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-runtime-info-0.1.0",
            "package_version": "0.1.0",
            "compatibility_line": "0.1.x",
            "service_schema_version": "skill2workflow-service-0.2.0",
            "workflow_dsl_schema_version": "0.1.0",
            "storage": "sqlite",
            "state_layout_version": "skill2workflow-sqlite-layout-0.1.0",
            "service_status": "ready",
            "service_ready": True,
            "scheduler_lease_owned": True,
        }
        with patch(
            "skill2workflow.cli.fetch_runtime_info",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-runtime-info",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with("https://service.example", token_file)

    def test_service_trigger_command_loads_input_and_requires_retry_key(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "trigger_id": "trigger_remote_001",
            "workflow_id": "workflow_remote",
            "workflow_version": "0.1.0",
            "run_id": "run_remote_001",
            "run_status": "waiting",
            "source": "service-cli",
            "idempotency_key": "remote-001",
            "input_keys": ["customer_id"],
        }
        with TemporaryDirectory() as tmp:
            input_file = Path(tmp) / "input.json"
            input_file.write_text(
                json.dumps({"customer_id": "customer_123"}), encoding="utf-8"
            )
            with patch(
                "skill2workflow.cli.post_workflow_trigger",
                return_value=expected,
            ) as trigger:
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "service-trigger",
                            "workflow_remote",
                            "--version",
                            "production",
                            "--service-url",
                            "https://service.example",
                            "--auth-token-file",
                            str(token_file),
                            "--idempotency-key",
                            "remote-001",
                            "--input",
                            str(input_file),
                        ]
                    )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        trigger.assert_called_once_with(
            "https://service.example",
            token_file,
            "workflow_remote",
            "production",
            idempotency_key="remote-001",
            source="service-cli",
            trigger_input={"customer_id": "customer_123"},
        )

    def test_service_workflow_publish_command_loads_workflow(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        workflow = _approval_workflow()
        expected = {
            "schema_version": "skill2workflow-workflow-release-0.1.0",
            "workflow_id": "workflow_demo",
            "version": "0.1.0",
            "status": "published",
            "checksum": "a" * 64,
        }
        with TemporaryDirectory() as tmp:
            workflow_file = Path(tmp) / "workflow.json"
            workflow_file.write_text(json.dumps(workflow), encoding="utf-8")
            with patch(
                "skill2workflow.cli.post_workflow_release",
                return_value=expected,
            ) as publish:
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "service-workflow-publish",
                            str(workflow_file),
                            "--service-url",
                            "https://service.example",
                            "--auth-token-file",
                            str(token_file),
                        ]
                    )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        publish.assert_called_once_with("https://service.example", token_file, workflow)

    def test_service_workflow_promote_command_uses_cas_options(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-workflow-promotion-0.1.0",
            "workflow_id": "workflow_demo",
            "version": "0.2.0",
            "alias": "production",
            "status": "promoted",
            "checksum": "b" * 64,
        }
        with patch(
            "skill2workflow.cli.post_workflow_promotion",
            return_value=expected,
        ) as promote:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-workflow-promote",
                        "workflow_demo",
                        "--version",
                        "0.2.0",
                        "--alias",
                        "production",
                        "--expected-current-version",
                        "0.1.0",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        promote.assert_called_once_with(
            "https://service.example",
            token_file,
            "workflow_demo",
            "0.2.0",
            alias="production",
            expected_current_version="0.1.0",
        )

    def test_service_workflow_diff_command_uses_version_options(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-workflow-diff-0.1.0",
            "workflow_id": "workflow_demo",
            "from": {"version": "0.1.0", "status": "published", "checksum": "a" * 64, "aliases": []},
            "to": {"version": "0.2.0", "status": "published", "checksum": "b" * 64, "aliases": ["production"]},
            "changed": False,
            "changes": {
                "sections": [],
                "workflow_changed": False,
                "entry_changed": False,
                "input_schema_changed": False,
                "policies_changed": False,
                "other_changed": False,
                "nodes": {"added": [], "removed": [], "changed": []},
                "edges": {"added": [], "removed": [], "changed": []},
            },
        }
        with patch(
            "skill2workflow.cli.fetch_workflow_diff",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-workflow-diff",
                        "workflow_demo",
                        "--from-version",
                        "0.1.0",
                        "--to-version",
                        "0.2.0",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with(
            "https://service.example",
            token_file,
            "workflow_demo",
            "0.1.0",
            "0.2.0",
        )

    def test_service_workflows_command_prints_inventory(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-workflow-inventory-0.1.0",
            "summary": {
                "total": 1,
                "status_counts": {"published": 1, "deprecated": 0, "other": 0},
            },
            "versions": [
                {
                    "workflow_id": "workflow_demo",
                    "version": "0.1.0",
                    "status": "published",
                    "aliases": ["production"],
                    "checksum": "a" * 64,
                }
            ],
            "window": {"max_items": 100, "total": 1, "returned": 1, "truncated": False},
        }
        with patch(
            "skill2workflow.cli.fetch_workflow_inventory",
            return_value=expected,
        ) as inventory:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-workflows",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        inventory.assert_called_once_with("https://service.example", token_file)

    def test_service_workflow_deprecate_command_uses_version_options(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-workflow-deprecation-0.1.0",
            "workflow_id": "workflow_demo",
            "version": "0.1.0",
            "status": "deprecated",
            "checksum": "a" * 64,
        }
        with patch(
            "skill2workflow.cli.post_workflow_deprecation",
            return_value=expected,
        ) as deprecate:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-workflow-deprecate",
                        "workflow_demo",
                        "--version",
                        "0.1.0",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        deprecate.assert_called_once_with(
            "https://service.example",
            token_file,
            "workflow_demo",
            "0.1.0",
        )

    def test_service_schedule_state_command_prints_action(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-recurring-schedule-action-0.1.0",
            "schedule_id": "schedule_hourly_report",
            "enabled": False,
            "status": "disabled",
            "changed": True,
        }
        with patch(
            "skill2workflow.cli.post_recurring_schedule_state",
            return_value=expected,
        ) as action:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-schedule-disable",
                        "schedule_hourly_report",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        action.assert_called_once_with(
            "https://service.example",
            token_file,
            "schedule_hourly_report",
            enabled=False,
        )

    def test_service_schedule_state_command_accepts_expected_next_run_at(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-recurring-schedule-action-0.1.0",
            "schedule_id": "schedule_hourly_report",
            "enabled": True,
            "status": "active",
            "changed": True,
        }
        with patch(
            "skill2workflow.cli.post_recurring_schedule_state",
            return_value=expected,
        ) as action:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-schedule-enable",
                        "schedule_hourly_report",
                        "--expected-next-run-at",
                        "2026-08-11T00:00:00Z",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        action.assert_called_once_with(
            "https://service.example",
            token_file,
            "schedule_hourly_report",
            enabled=True,
            expected_next_run_at="2026-08-11T00:00:00Z",
        )

    def test_service_recurring_schedule_add_command_prints_create_result(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        schedule_file = Path("/private/schedule.json")
        definition = {
            "schema_version": "skill2workflow-schedule-0.2.0",
            "schedule": {"id": "schedule_remote", "workflow_id": "workflow", "version": "1.0.0"},
            "trigger": {"input": {}},
        }
        expected = {
            "schema_version": "skill2workflow-recurring-schedule-create-0.1.0",
            "schedule_id": "schedule_remote",
            "workflow_id": "workflow",
            "workflow_version": "1.0.0",
            "status": "active",
            "enabled": True,
            "starts_at": "2026-08-11T00:00:00+00:00",
            "next_run_at": "2026-08-11T00:00:00+00:00",
            "interval_seconds": 60,
            "missed_run_policy": "latest",
            "created": True,
        }
        with patch("skill2workflow.cli._load_json", return_value=definition), patch(
            "skill2workflow.cli.post_recurring_schedule_create",
            return_value=expected,
        ) as create:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-recurring-schedule-add",
                        str(schedule_file),
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        create.assert_called_once_with("https://service.example", token_file, definition)

    def test_service_recurring_schedule_update_command_prints_update_result(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        schedule_file = Path("/private/schedule-update.json")
        definition = {
            "schema_version": "skill2workflow-schedule-0.2.0",
            "schedule": {
                "id": "schedule_remote",
                "workflow_id": "workflow",
                "version": "1.0.0",
                "starts_at": "2026-08-11T00:00:00Z",
                "interval_seconds": 120,
                "missed_run_policy": "latest",
                "enabled": True,
            },
            "trigger": {"input": {}},
        }
        expected = {
            "schema_version": "skill2workflow-recurring-schedule-update-0.1.0",
            "schedule_id": "schedule_remote",
            "workflow_id": "workflow",
            "workflow_version": "1.0.0",
            "status": "active",
            "enabled": True,
            "starts_at": "2026-08-11T00:00:00+00:00",
            "next_run_at": "2026-08-11T00:00:00+00:00",
            "interval_seconds": 120,
            "missed_run_policy": "latest",
            "changed": True,
        }
        with patch("skill2workflow.cli._load_json", return_value=definition), patch(
            "skill2workflow.cli.put_recurring_schedule_update",
            return_value=expected,
        ) as update:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-recurring-schedule-update",
                        "schedule_remote",
                        str(schedule_file),
                        "--expected-next-run-at",
                        "2026-08-11T00:00:00+00:00",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        update.assert_called_once_with(
            "https://service.example",
            token_file,
            "schedule_remote",
            definition,
            expected_next_run_at="2026-08-11T00:00:00+00:00",
        )

    def test_service_recurring_schedule_patch_command_prints_patch_result(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        schedule_file = Path("/private/schedule-patch.json")
        patch_fields = {
            "workflow_id": "workflow_v2",
            "version": "2.0.0",
            "interval_seconds": 120,
        }
        expected = {
            "schema_version": "skill2workflow-recurring-schedule-patch-0.1.0",
            "schedule_id": "schedule_remote",
            "workflow_id": "workflow_v2",
            "workflow_version": "2.0.0",
            "status": "active",
            "enabled": True,
            "starts_at": "2026-08-11T00:00:00+00:00",
            "next_run_at": "2026-08-11T00:01:00+00:00",
            "interval_seconds": 120,
            "missed_run_policy": "latest",
            "changed": True,
        }
        with patch("skill2workflow.cli._load_json", return_value=patch_fields), patch(
            "skill2workflow.cli.patch_recurring_schedule",
            return_value=expected,
        ) as patch_schedule:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-recurring-schedule-patch",
                        "schedule_remote",
                        str(schedule_file),
                        "--expected-next-run-at",
                        "2026-08-11T00:00:00+00:00",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        patch_schedule.assert_called_once_with(
            "https://service.example",
            token_file,
            "schedule_remote",
            patch_fields,
            expected_next_run_at="2026-08-11T00:00:00+00:00",
        )

    def test_service_recurring_schedule_delete_command_prints_delete_result(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-recurring-schedule-delete-0.1.0",
            "schedule_id": "schedule_remote",
            "deleted": True,
        }
        with patch(
            "skill2workflow.cli.delete_recurring_schedule",
            return_value=expected,
        ) as delete:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-recurring-schedule-delete",
                        "schedule_remote",
                        "--expected-next-run-at",
                        "2026-08-11T00:00:00+00:00",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        delete.assert_called_once_with(
            "https://service.example",
            token_file,
            "schedule_remote",
            expected_next_run_at="2026-08-11T00:00:00+00:00",
        )

    def test_service_audit_consistency_command_prints_report(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-run-audit-report-0.1.0",
            "status": "clean",
            "summary": {
                "run_count": 0,
                "checked_runs": 0,
                "attention_runs": 0,
                "missing_events": 0,
                "duplicate_events": 0,
                "unexpected_events": 0,
                "truncated": False,
            },
            "runs": [],
        }
        with patch(
            "skill2workflow.cli.fetch_audit_consistency",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-audit-consistency",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with("https://service.example", token_file)

    def test_service_audit_consistency_command_accepts_one_run_id(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = {
            "schema_version": "skill2workflow-run-audit-report-0.1.0",
            "status": "clean",
            "summary": {
                "run_count": 1,
                "checked_runs": 1,
                "attention_runs": 0,
                "missing_events": 0,
                "duplicate_events": 0,
                "unexpected_events": 0,
                "truncated": False,
            },
            "runs": [],
        }
        with patch(
            "skill2workflow.cli.fetch_audit_consistency",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-audit-consistency",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        str(token_file),
                        "--run-id",
                        "run_remote_1",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with("https://service.example", token_file, "run_remote_1")

    def test_service_audit_events_command_prints_filtered_page(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        expected = _audit_event_page_fixture()
        with patch("skill2workflow.cli.fetch_audit_events", return_value=expected) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-audit-events",
                        "--service-url", "https://service.example",
                        "--auth-token-file", str(token_file),
                        "--max-items", "10",
                        "--cursor", "cursor-token",
                        "--workflow-id", "workflow",
                        "--workflow-version", "0.1.0",
                        "--run-id", "run_remote_1",
                        "--event-type", "connector_failed",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with(
            "https://service.example",
            token_file,
            max_items=10,
            cursor="cursor-token",
            workflow_id="workflow",
            workflow_version="0.1.0",
            run_id="run_remote_1",
            event_type="connector_failed",
        )

    def test_service_support_bundle_writes_private_output(self):
        stdout = StringIO()
        token_file = Path("/private/ingress.token")
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "support-bundle.json"
            expected = {
                "schema_version": "skill2workflow-support-bundle-0.1.0",
                "service": {"status": "ready"},
                "run_list": {"runs": []},
                "observability": {"audit_event_count": 0},
            }
            with patch(
                "skill2workflow.cli.fetch_support_bundle",
                return_value=expected,
            ) as fetch:
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "service-support-bundle",
                            "--service-url",
                            "https://service.example",
                            "--auth-token-file",
                            str(token_file),
                            "--output",
                            str(output),
                        ]
                    )

            written = json.loads(output.read_text(encoding="utf-8"))
            output_mode = output.stat().st_mode & 0o777

        self.assertEqual(exit_code, 0)
        self.assertEqual(written, expected)
        self.assertEqual(output_mode, 0o600)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "schema_version": "skill2workflow-support-bundle-0.1.0",
                "output": str(output),
            },
        )
        fetch.assert_called_once_with("https://service.example", token_file)

    def test_state_retention_plan_and_apply_commands_publish_new_copy(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            output_dir = root / "retained"
            workflow_path = root / "workflow.json"
            policy_path = root / "retention.json"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            policy_path.write_text(
                json.dumps(
                    {
                        "schema_version": "skill2workflow-retention-policy-0.1.0",
                        "retention": {
                            "delete_before": "2026-01-01T00:00:00Z",
                            "terminal_run_statuses": ["completed", "failed"],
                            "terminal_dispatch_statuses": [
                                "completed",
                                "failed",
                                "skipped",
                                "uncertain",
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    main(
                        [
                            "publish",
                            str(workflow_path),
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )
            RecurringScheduleStore(state_dir)
            plan_stdout = StringIO()
            with redirect_stdout(plan_stdout):
                plan_exit = main(
                    [
                        "state-retention-plan",
                        str(policy_path),
                        "--state-dir",
                        str(state_dir),
                    ]
                )
            apply_stdout = StringIO()
            with redirect_stdout(apply_stdout):
                apply_exit = main(
                    [
                        "state-retention-apply",
                        str(policy_path),
                        "--state-dir",
                        str(state_dir),
                        "--output-dir",
                        str(output_dir),
                    ]
                )

        self.assertEqual(plan_exit, 0)
        self.assertEqual(apply_exit, 0)
        self.assertEqual(json.loads(plan_stdout.getvalue())["status"], "ready")
        self.assertEqual(
            json.loads(apply_stdout.getvalue())["status"],
            "retained_copy_created",
        )

    def test_state_retention_command_normalizes_unexpected_storage_failure(self):
        stderr = StringIO()
        with patch(
            "skill2workflow.cli.apply_state_retention",
            side_effect=OSError("private retention filesystem detail"),
        ):
            with redirect_stderr(stderr):
                exit_code = main(
                    [
                        "state-retention-apply",
                        "/private/policy.json",
                        "--state-dir",
                        "/private/state",
                        "--output-dir",
                        "/private/output",
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue(), "state retention operation failed\n")
        self.assertNotIn("private retention filesystem detail", stderr.getvalue())

    def test_state_upgrade_plan_and_upgrade_commands_migrate_legacy_copy(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow_path = root / "workflow.json"
            source = root / "legacy"
            output = root / "upgraded"
            backup = root / "pre-upgrade-backup"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    main(
                        [
                            "publish",
                            str(workflow_path),
                            "--state-dir",
                            str(source),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )
            RecurringScheduleStore(source)
            (source / STATE_LAYOUT_MARKER).unlink()

            plan_stdout = StringIO()
            with redirect_stdout(plan_stdout):
                self.assertEqual(
                    main(["state-upgrade-plan", "--state-dir", str(source)]), 0
                )
            upgrade_stdout = StringIO()
            with redirect_stdout(upgrade_stdout):
                self.assertEqual(
                    main(
                        [
                            "state-upgrade",
                            "--state-dir",
                            str(source),
                            "--output-dir",
                            str(output),
                            "--backup-dir",
                            str(backup),
                        ]
                    ),
                    0,
                )
            plan = json.loads(plan_stdout.getvalue())
            upgraded = json.loads(upgrade_stdout.getvalue())

        self.assertEqual(plan["status"], "upgrade_required")
        self.assertEqual(upgraded["status"], "upgraded")

    def test_backup_verify_and_restore_commands_round_trip_sqlite_state(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow_path = root / "workflow.json"
            schedule_path = root / "schedule.json"
            state_dir = root / "state"
            backup_dir = root / "backup"
            restored_dir = root / "restored"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            schedule_path.write_text(
                json.dumps(
                    {
                        "schema_version": "skill2workflow-schedule-0.2.0",
                        "schedule": {
                            "id": "schedule_backup_cli",
                            "workflow_id": "workflow_demo",
                            "version": "0.1.0",
                            "starts_at": "2026-08-11T00:00:00Z",
                            "interval_seconds": 3600,
                            "missed_run_policy": "latest",
                        },
                        "trigger": {"input": {}},
                    }
                ),
                encoding="utf-8",
            )
            outputs = []
            for arguments in (
                ["publish", str(workflow_path), "--state-dir", str(state_dir), "--storage", "sqlite"],
                ["schedule-add", str(schedule_path), "--state-dir", str(state_dir), "--storage", "sqlite"],
                ["backup", "--state-dir", str(state_dir), "--output-dir", str(backup_dir)],
                ["backup-verify", "--backup-dir", str(backup_dir)],
                ["restore", "--backup-dir", str(backup_dir), "--state-dir", str(restored_dir)],
            ):
                stdout = StringIO()
                with redirect_stdout(stdout):
                    self.assertEqual(main(arguments), 0)
                outputs.append(json.loads(stdout.getvalue()))
            restored_stdout = StringIO()
            with redirect_stdout(restored_stdout):
                self.assertEqual(
                    main(["workflows", "--state-dir", str(restored_dir), "--storage", "sqlite"]),
                    0,
                )
            restored_workflows = json.loads(restored_stdout.getvalue())

        self.assertEqual(outputs[2]["status"], "created")
        self.assertEqual(outputs[3]["status"], "valid")
        self.assertEqual(outputs[4]["status"], "restored")
        self.assertEqual(restored_workflows[0]["workflow_id"], "workflow_demo")

    def test_backup_list_command_reports_bounded_verified_inventory(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow_path = root / "workflow.json"
            state_dir = root / "state"
            backup_parent = root / "backups"
            backup_dir = backup_parent / "backup-2026-08-14"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            backup_parent.mkdir()
            backup_parent.chmod(0o700)
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    main(
                        [
                            "publish",
                            str(workflow_path),
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )
                RecurringScheduleStore(state_dir)
                self.assertEqual(
                    main(
                        [
                            "backup",
                            "--state-dir",
                            str(state_dir),
                            "--output-dir",
                            str(backup_dir),
                        ]
                    ),
                    0,
                )
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "backup-list",
                        "--parent-dir",
                        str(backup_parent),
                        "--limit",
                        "1",
                    ]
                )

        inventory = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(inventory["status"], "ok")
        self.assertEqual(inventory["window"]["max_items"], 1)
        self.assertEqual(inventory["backups"][0]["status"], "valid")

    def test_backup_retention_plan_command_is_read_only_and_bounded(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow_path = root / "workflow.json"
            state_dir = root / "state"
            backup_parent = root / "backups"
            backup_dir = backup_parent / "backup-2026-08-14"
            policy_path = root / "backup-retention.json"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            backup_parent.mkdir()
            backup_parent.chmod(0o700)
            policy_path.write_text(
                json.dumps(
                    {
                        "schema_version": "skill2workflow-backup-retention-policy-0.1.0",
                        "retention": {
                            "expire_before": "2026-08-14T00:00:03Z",
                            "minimum_keep": 1,
                        },
                    }
                ),
                encoding="utf-8",
            )
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    main(
                        [
                            "publish",
                            str(workflow_path),
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )
                RecurringScheduleStore(state_dir)
                self.assertEqual(
                    main(
                        [
                            "backup",
                            "--state-dir",
                            str(state_dir),
                            "--output-dir",
                            str(backup_dir),
                        ]
                    ),
                    0,
                )
            before = sorted(path.name for path in backup_parent.iterdir())
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "backup-retention-plan",
                        str(policy_path),
                        "--parent-dir",
                        str(backup_parent),
                    ]
                )
            after = sorted(path.name for path in backup_parent.iterdir())

        plan = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(plan["status"], "ready")
        self.assertEqual(plan["summary"]["eligible_backups"], 0)
        self.assertEqual(before, after)

    def test_backup_command_normalizes_unexpected_storage_failure(self):
        stderr = StringIO()
        with patch(
            "skill2workflow.cli.create_state_backup",
            side_effect=OSError("private filesystem detail"),
        ):
            with redirect_stderr(stderr):
                exit_code = main(
                    [
                        "backup",
                        "--state-dir",
                        "/private/state",
                        "--output-dir",
                        "/private/backup",
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue(), "state backup operation failed\n")
        self.assertNotIn("private filesystem detail", stderr.getvalue())

    def test_state_upgrade_command_normalizes_unexpected_storage_failure(self):
        stderr = StringIO()
        with patch(
            "skill2workflow.cli.upgrade_state",
            side_effect=OSError("private migration filesystem detail"),
        ):
            with redirect_stderr(stderr):
                exit_code = main(
                    [
                        "state-upgrade",
                        "--state-dir",
                        "/private/state",
                        "--backup-dir",
                        "/private/backup",
                        "--output-dir",
                        "/private/output",
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue(), "state upgrade operation failed\n")
        self.assertNotIn("private migration filesystem detail", stderr.getvalue())

    def test_service_command_loads_validated_configuration(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "service.json"
            state_dir = root / "state"
            token_file = root / "ingress.token"
            credential_dir = root / "credentials"
            config_path.write_text(
                json.dumps(
                    {
                        "schema_version": "skill2workflow-service-0.2.0",
                        "service": {"host": "127.0.0.1", "port": 8080},
                        "runtime": {"state_dir": str(state_dir), "storage": "sqlite"},
                        "auth": {
                            "provider": "bearer_token_file",
                            "token_file": str(token_file),
                        },
                        "credentials": {
                            "provider": "directory",
                            "directory": str(credential_dir),
                        },
                    }
                ),
                encoding="utf-8",
            )
            captured = {}

            def fake_service(config, event_logger=None):
                captured["config"] = config
                captured["event_logger"] = event_logger

            with patch("skill2workflow.cli.serve_runtime_service", side_effect=fake_service):
                exit_code = main(["service", "--config", str(config_path)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(captured["config"].state_dir, state_dir)
        self.assertEqual(captured["config"].storage, "sqlite")
        self.assertEqual(captured["config"].auth_token_file, token_file)
        self.assertEqual(captured["config"].credential_dir, credential_dir)
        self.assertIsNotNone(captured["event_logger"])

    def test_visualize_command_writes_litegraph_json(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workflow_path = tmp_path / "workflow.json"
            run_state_path = tmp_path / "run.json"
            output_path = tmp_path / "graph.json"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            run_state_path.write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "current_node": "end",
                        "node_results": {"end": {"status": "completed"}},
                    }
                ),
                encoding="utf-8",
            )

            exit_code = main(
                [
                    "visualize",
                    str(workflow_path),
                    "--run-state",
                    str(run_state_path),
                    "-o",
                    str(output_path),
                ]
            )

            graph = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(graph["version"], "skill2workflow-litegraph-0.1.0")
        self.assertEqual(graph["nodes"][-1]["properties"]["run_status"], "completed")

    def test_control_plane_commands_publish_list_and_run_published_workflow(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workflow_path = tmp_path / "workflow.json"
            state_dir = tmp_path / "state"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")

            with redirect_stdout(StringIO()):
                publish_exit = main(["publish", str(workflow_path), "--state-dir", str(state_dir)])
                workflows_exit = main(["workflows", "--state-dir", str(state_dir)])
                run_exit = main(
                    [
                        "run-published",
                        "workflow_demo",
                        "--version",
                        "0.1.0",
                        "--state-dir",
                        str(state_dir),
                    ]
                )

            from skill2workflow.control_plane import LocalControlPlane

            control = LocalControlPlane(state_dir)
            workflow_records = control.list_workflows()
            run_summary = control.list_runs()[0]

        self.assertEqual(publish_exit, 0)
        self.assertEqual(workflows_exit, 0)
        self.assertEqual(run_exit, 0)
        self.assertEqual(workflow_records[0]["workflow_id"], "workflow_demo")
        self.assertEqual(workflow_records[0]["status"], "published")
        self.assertEqual(run_summary["workflow_version"], "0.1.0")

    def test_workflows_command_supports_bounded_redacted_inventory_window(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            first_path = root / "workflow-v1.json"
            second = _workflow()
            second["workflow"]["version"] = "0.2.0"
            second["nodes"][0]["title"] = "private workflow title"
            second_path = root / "workflow-v2.json"
            first_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            second_path.write_text(json.dumps(second), encoding="utf-8")

            with redirect_stdout(StringIO()):
                self.assertEqual(
                    main(
                        [
                            "publish",
                            str(first_path),
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )
                self.assertEqual(
                    main(
                        [
                            "publish",
                            str(second_path),
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )

            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "workflows",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                        "--limit",
                        "1",
                    ]
                )

        self.assertEqual(exit_code, 0)
        inventory = json.loads(output.getvalue())
        self.assertEqual(
            inventory["schema_version"],
            "skill2workflow-workflow-inventory-0.1.0",
        )
        self.assertEqual(inventory["summary"]["total"], 2)
        self.assertEqual(inventory["window"], {
            "max_items": 1,
            "total": 2,
            "returned": 1,
            "truncated": True,
        })
        self.assertEqual(inventory["versions"][0]["version"], "0.2.0")
        self.assertEqual(
            set(inventory["versions"][0]),
            {"workflow_id", "version", "status", "aliases", "checksum"},
        )
        self.assertNotIn("private workflow title", output.getvalue())

    def test_workflows_command_rejects_invalid_bounded_inventory_limit(self):
        with TemporaryDirectory() as tmp:
            error = StringIO()
            with redirect_stderr(error):
                exit_code = main(
                    [
                        "workflows",
                        "--state-dir",
                        str(Path(tmp) / "state"),
                        "--limit",
                        "101",
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(error.getvalue().strip(), "max_items must be a positive bounded integer")

    def test_trigger_command_starts_published_workflow_with_input_metadata(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workflow_path = tmp_path / "workflow.json"
            input_path = tmp_path / "trigger-input.json"
            state_dir = tmp_path / "state"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            input_path.write_text(json.dumps({"customer_id": "customer_123"}), encoding="utf-8")
            trigger_stdout = StringIO()
            detail_stdout = StringIO()

            with redirect_stdout(StringIO()):
                publish_exit = main(["publish", str(workflow_path), "--state-dir", str(state_dir)])
            with redirect_stdout(trigger_stdout):
                trigger_exit = main(
                    [
                        "trigger",
                        "workflow_demo",
                        "--version",
                        "0.1.0",
                        "--state-dir",
                        str(state_dir),
                        "--source",
                        "local-cli",
                        "--idempotency-key",
                        "demo-1",
                        "--input",
                        str(input_path),
                    ]
                )
            result = json.loads(trigger_stdout.getvalue())
            with redirect_stdout(detail_stdout):
                detail_exit = main(["control-run", result["run_id"], "--state-dir", str(state_dir)])

            from skill2workflow.control_plane import LocalControlPlane

            detail = json.loads(detail_stdout.getvalue())
            audit_events = LocalControlPlane(state_dir).list_audit_events(run_id=result["run_id"])

        self.assertEqual(publish_exit, 0)
        self.assertEqual(trigger_exit, 0)
        self.assertEqual(detail_exit, 0)
        self.assertTrue(result["trigger_id"].startswith("trigger_"))
        self.assertEqual(result["workflow_id"], "workflow_demo")
        self.assertEqual(result["workflow_version"], "0.1.0")
        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(result["source"], "local-cli")
        self.assertEqual(result["idempotency_key"], "demo-1")
        self.assertEqual(result["input_keys"], ["customer_id"])
        self.assertEqual(detail["context"]["input"], {"customer_id": "customer_123"})
        self.assertEqual(detail["context"]["trigger"]["trigger_id"], result["trigger_id"])
        self.assertEqual(detail["context"]["trigger"]["source"], "local-cli")
        self.assertEqual([event["type"] for event in audit_events], ["run_started", "run_completed"])
        self.assertEqual(audit_events[0]["trigger_id"], result["trigger_id"])
        self.assertNotIn("input", audit_events[0])

    def test_trigger_command_maps_input_into_http_connector_body(self):
        server = _CliConnectorTestServer()

        try:
            with TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                workflow_path = tmp_path / "mapped-workflow.json"
                input_path = tmp_path / "trigger-input.json"
                state_dir = tmp_path / "state"
                workflow_path.write_text(json.dumps(_mapped_connector_workflow(server.url)), encoding="utf-8")
                input_path.write_text(json.dumps({"customer_id": "customer_123"}), encoding="utf-8")
                trigger_stdout = StringIO()

                with redirect_stdout(StringIO()):
                    publish_exit = main(["publish", str(workflow_path), "--state-dir", str(state_dir)])
                with redirect_stdout(trigger_stdout):
                    trigger_exit = main(
                        [
                            "trigger",
                            "workflow_mapped_connector",
                            "--version",
                            "0.1.0",
                            "--state-dir",
                            str(state_dir),
                            "--source",
                            "local-cli",
                            "--input",
                            str(input_path),
                        ]
                    )

                result = json.loads(trigger_stdout.getvalue())
        finally:
            server.close()

        self.assertEqual(publish_exit, 0)
        self.assertEqual(trigger_exit, 0)
        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(
            server.requests[0]["body"],
            {
                "source": "skill2workflow",
                "customer_id": "customer_123",
            },
        )

    def test_trigger_command_rejects_non_object_input_json(self):
        with TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "trigger-input.json"
            input_path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "trigger",
                        "workflow_demo",
                        "--version",
                        "0.1.0",
                        "--input",
                        str(input_path),
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("trigger input must be a JSON object", stderr.getvalue())

    def test_trigger_command_rejects_oversized_input_before_opening_state(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "trigger-input.json"
            state_dir = root / "state"
            input_path.write_text(
                json.dumps({"payload": "x" * MAX_TRIGGER_INPUT_BYTES}),
                encoding="utf-8",
            )
            stderr = StringIO()
            with redirect_stdout(StringIO()), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "trigger",
                        "workflow_demo",
                        "--version",
                        "0.1.0",
                        "--state-dir",
                        str(state_dir),
                        "--input",
                        str(input_path),
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertIn("trigger input exceeds", stderr.getvalue())
        self.assertFalse(state_dir.exists())

    def test_validate_command_rejects_oversized_json_without_traceback(self):
        with TemporaryDirectory() as tmp:
            workflow_path = Path(tmp) / "oversized-workflow.json"
            workflow_path.write_text(
                json.dumps({"payload": "x" * MAX_CLI_JSON_DOCUMENT_BYTES}),
                encoding="utf-8",
            )
            stdout = StringIO()
            stderr = StringIO()

            with patch("pathlib.Path.open") as open_file:
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = main(["validate", str(workflow_path)])
            open_file.assert_not_called()

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn(
            f"JSON document exceeds {MAX_CLI_JSON_DOCUMENT_BYTES} bytes",
            stderr.getvalue(),
        )
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_validate_command_rejects_json_that_grows_after_size_check(self):
        with TemporaryDirectory() as tmp:
            workflow_path = Path(tmp) / "growing-workflow.json"
            workflow_path.write_text("{}", encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()
            growing_bytes = BytesIO(b"{}" + b"x" * MAX_CLI_JSON_DOCUMENT_BYTES)

            with patch("pathlib.Path.open", return_value=growing_bytes):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = main(["validate", str(workflow_path)])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn(
            f"JSON document exceeds {MAX_CLI_JSON_DOCUMENT_BYTES} bytes",
            stderr.getvalue(),
        )
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_validate_command_rejects_non_object_json_without_traceback(self):
        with TemporaryDirectory() as tmp:
            workflow_path = Path(tmp) / "non-object-workflow.json"
            workflow_path.write_text(json.dumps(["not", "a", "workflow"]), encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["validate", str(workflow_path)])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("workflow document must be a JSON object", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_schedule_commands_add_list_and_run_due(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workflow_path = tmp_path / "workflow.json"
            schedule_path = tmp_path / "schedule.json"
            state_dir = tmp_path / "state"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            schedule_path.write_text(
                json.dumps(
                    {
                        "schema_version": "skill2workflow-schedule-0.1.0",
                        "schedule": {
                            "id": "schedule_daily_report",
                            "workflow_id": "workflow_demo",
                            "version": "0.1.0",
                            "run_at": "2026-07-06T00:00:00Z",
                        },
                        "trigger": {"input": {"customer_id": "customer_123"}},
                    }
                ),
                encoding="utf-8",
            )
            schedules_stdout = StringIO()
            run_due_stdout = StringIO()

            with redirect_stdout(StringIO()):
                publish_exit = main(["publish", str(workflow_path), "--state-dir", str(state_dir)])
                add_exit = main(["schedule-add", str(schedule_path), "--state-dir", str(state_dir)])
            with redirect_stdout(schedules_stdout):
                schedules_exit = main(["schedules", "--state-dir", str(state_dir)])
            with redirect_stdout(run_due_stdout):
                run_due_exit = main(
                    [
                        "schedule-run-due",
                        "--state-dir",
                        str(state_dir),
                        "--now",
                        "2026-07-06T00:00:00Z",
                    ]
                )
            result = json.loads(run_due_stdout.getvalue())
            schedules = json.loads(schedules_stdout.getvalue())

            from skill2workflow.control_plane import LocalControlPlane

            control = LocalControlPlane(state_dir)
            detail = control.get_run(result["runs"][0]["run_id"])
            audit_events = control.list_audit_events(run_id=result["runs"][0]["run_id"])

        self.assertEqual(publish_exit, 0)
        self.assertEqual(add_exit, 0)
        self.assertEqual(schedules_exit, 0)
        self.assertEqual(run_due_exit, 0)
        self.assertEqual(schedules[0]["schedule"]["id"], "schedule_daily_report")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["runs"][0]["schedule_id"], "schedule_daily_report")
        self.assertEqual(result["runs"][0]["source"], "local-schedule:schedule_daily_report")
        self.assertEqual(detail["context"]["input"], {"customer_id": "customer_123"})
        self.assertEqual(audit_events[0]["trigger_source"], "local-schedule:schedule_daily_report")
        self.assertNotIn("input", audit_events[0])

    def test_schedule_list_command_supports_bounded_compact_window(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            definitions = []
            for schedule_id, run_at in (
                ("schedule_old", "2026-07-06T00:00:00Z"),
                ("schedule_new", "2026-07-07T00:00:00Z"),
            ):
                path = root / f"{schedule_id}.json"
                path.write_text(
                    json.dumps(
                        {
                            "schema_version": "skill2workflow-schedule-0.1.0",
                            "schedule": {
                                "id": schedule_id,
                                "workflow_id": "workflow_demo",
                                "version": "0.1.0",
                                "run_at": run_at,
                            },
                            "trigger": {"input": {"private": "not-in-bounded-output"}},
                        }
                    ),
                    encoding="utf-8",
                )
                definitions.append(path)
            with redirect_stdout(StringIO()):
                for definition in definitions:
                    self.assertEqual(
                        main(["schedule-add", str(definition), "--state-dir", str(state_dir)]),
                        0,
                    )
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    ["schedules", "--state-dir", str(state_dir), "--limit", "1"]
                )

        inventory = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(inventory["schema_version"], "skill2workflow-local-schedule-list-0.1.0")
        self.assertEqual(inventory["window"]["total"], 2)
        self.assertEqual(inventory["schedules"][0]["schedule_id"], "schedule_new")
        self.assertNotIn("not-in-bounded-output", stdout.getvalue())

    def test_schedule_run_due_command_supports_bounded_batch_budget(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            workflow_path = root / "workflow.json"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    main(["publish", str(workflow_path), "--state-dir", str(state_dir)]),
                    0,
                )
                for schedule_id in ("schedule_a", "schedule_b"):
                    schedule_path = root / f"{schedule_id}.json"
                    schedule_path.write_text(
                        json.dumps(
                            {
                                "schema_version": "skill2workflow-schedule-0.1.0",
                                "schedule": {
                                    "id": schedule_id,
                                    "workflow_id": "workflow_demo",
                                    "version": "0.1.0",
                                    "run_at": "2026-07-06T00:00:00Z",
                                },
                                "trigger": {"input": {"private": schedule_id}},
                            }
                        ),
                        encoding="utf-8",
                    )
                    self.assertEqual(
                        main(["schedule-add", str(schedule_path), "--state-dir", str(state_dir)]),
                        0,
                    )

            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "schedule-run-due",
                        "--state-dir",
                        str(state_dir),
                        "--now",
                        "2026-07-06T00:00:00Z",
                        "--max-items",
                        "1",
                    ]
                )

        self.assertEqual(exit_code, 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["window"], {
            "max_items": 1,
            "processed": 1,
            "budget_exhausted": True,
        })
        self.assertEqual(result["runs"][0]["schedule_id"], "schedule_a")

    def test_schedule_commands_support_sqlite_recurring_definitions_and_dispatch_records(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow_path = root / "workflow.json"
            schedule_path = root / "recurring.json"
            state_dir = root / "state"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            schedule_path.write_text(
                json.dumps(
                    {
                        "schema_version": "skill2workflow-schedule-0.2.0",
                        "schedule": {
                            "id": "schedule_recurring_cli",
                            "workflow_id": "workflow_demo",
                            "version": "0.1.0",
                            "starts_at": "2026-08-11T00:00:00Z",
                            "interval_seconds": 60,
                            "missed_run_policy": "latest",
                        },
                        "trigger": {"input": {}},
                    }
                ),
                encoding="utf-8",
            )
            dispatch_stdout = StringIO()
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    main(["publish", str(workflow_path), "--state-dir", str(state_dir), "--storage", "sqlite"]),
                    0,
                )
                self.assertEqual(
                    main(["schedule-add", str(schedule_path), "--state-dir", str(state_dir), "--storage", "sqlite"]),
                    0,
                )
                self.assertEqual(
                    main(
                        [
                            "schedule-disable",
                            "schedule_recurring_cli",
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )
                self.assertEqual(
                    main(
                        [
                            "schedule-enable",
                            "schedule_recurring_cli",
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )
                self.assertEqual(
                    main(
                        [
                            "schedule-run-due",
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                            "--now",
                            "2026-08-11T00:00:00Z",
                        ]
                    ),
                    0,
                )
            with redirect_stdout(dispatch_stdout):
                exit_code = main(
                    [
                        "schedule-dispatches",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                        "--schedule-id",
                        "schedule_recurring_cli",
                    ]
                )

        self.assertEqual(exit_code, 0)
        dispatches = json.loads(dispatch_stdout.getvalue())
        self.assertEqual(len(dispatches), 1)
        self.assertEqual(dispatches[0]["status"], "completed")
        self.assertNotIn("input", dispatches[0])

    def test_webhook_server_command_wires_local_control_plane(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            captured = {}

            def fake_server(host, port, control_plane, once=False):
                captured["host"] = host
                captured["port"] = port
                captured["state_dir"] = control_plane.state_dir
                captured["once"] = once

            with patch("skill2workflow.cli.serve_webhook_requests", side_effect=fake_server):
                with redirect_stdout(StringIO()):
                    exit_code = main(
                        [
                            "webhook-server",
                            "--host",
                            "127.0.0.1",
                            "--port",
                            "0",
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                            "--once",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        self.assertEqual(captured["host"], "127.0.0.1")
        self.assertEqual(captured["port"], 0)
        self.assertEqual(captured["state_dir"], state_dir)
        self.assertEqual(captured["once"], True)

    def test_run_published_command_can_use_sqlite_storage(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workflow_path = tmp_path / "workflow.json"
            state_dir = tmp_path / "state"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")

            with redirect_stdout(StringIO()):
                publish_exit = main(["publish", str(workflow_path), "--state-dir", str(state_dir)])
                run_exit = main(
                    [
                        "run-published",
                        "workflow_demo",
                        "--version",
                        "0.1.0",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )
                runs_exit = main(["runs", "--state-dir", str(state_dir), "--storage", "sqlite"])

            from skill2workflow.control_plane import LocalControlPlane

            run_summary = LocalControlPlane(state_dir, storage="sqlite").list_runs()[0]
            db_exists = (state_dir / "runs.sqlite3").exists()

        self.assertEqual(publish_exit, 0)
        self.assertEqual(run_exit, 0)
        self.assertEqual(runs_exit, 0)
        self.assertEqual(run_summary["workflow_id"], "workflow_demo")
        self.assertTrue(db_exists)

    def test_control_plane_commands_can_use_sqlite_storage(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workflow_path = tmp_path / "workflow.json"
            state_dir = tmp_path / "state"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            workflows_stdout = StringIO()
            workflow_stdout = StringIO()
            audit_stdout = StringIO()

            with redirect_stdout(StringIO()):
                publish_exit = main(
                    ["publish", str(workflow_path), "--state-dir", str(state_dir), "--storage", "sqlite"]
                )
            with redirect_stdout(workflows_stdout):
                workflows_exit = main(["workflows", "--state-dir", str(state_dir), "--storage", "sqlite"])
            with redirect_stdout(workflow_stdout):
                workflow_exit = main(
                    [
                        "workflow",
                        "workflow_demo",
                        "--version",
                        "0.1.0",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )
            with redirect_stdout(StringIO()):
                deprecate_exit = main(
                    [
                        "deprecate",
                        "workflow_demo",
                        "--version",
                        "0.1.0",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )
            with redirect_stdout(audit_stdout):
                audit_exit = main(["audit", "--state-dir", str(state_dir), "--storage", "sqlite"])

            workflow_records = json.loads(workflows_stdout.getvalue())
            workflow_detail = json.loads(workflow_stdout.getvalue())
            audit_events = json.loads(audit_stdout.getvalue())
            control_db_exists = (state_dir / "control.sqlite3").exists()

        self.assertEqual(publish_exit, 0)
        self.assertEqual(workflows_exit, 0)
        self.assertEqual(workflow_exit, 0)
        self.assertEqual(deprecate_exit, 0)
        self.assertEqual(audit_exit, 0)
        self.assertEqual(workflow_records[0]["workflow_id"], "workflow_demo")
        self.assertEqual(workflow_detail["workflow"]["id"], "workflow_demo")
        self.assertEqual([event["type"] for event in audit_events], ["workflow_published", "workflow_deprecated"])
        self.assertTrue(control_db_exists)

    def test_promote_command_assigns_alias_and_trigger_resolves_it(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            first_path = root / "workflow-v1.json"
            second_path = root / "workflow-v2.json"
            first_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            second = _workflow()
            second["workflow"]["version"] = "0.2.0"
            second_path.write_text(json.dumps(second), encoding="utf-8")

            with redirect_stdout(StringIO()):
                self.assertEqual(
                    main(
                        [
                            "publish",
                            str(first_path),
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )
                self.assertEqual(
                    main(
                        [
                            "publish",
                            str(second_path),
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )

            promote_stdout = StringIO()
            with redirect_stdout(promote_stdout):
                promote_exit = main(
                    [
                        "promote",
                        "workflow_demo",
                        "--version",
                        "0.1.0",
                        "--alias",
                        "production",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )
            trigger_stdout = StringIO()
            with redirect_stdout(trigger_stdout):
                trigger_exit = main(
                    [
                        "trigger",
                        "workflow_demo",
                        "--version",
                        "production",
                        "--idempotency-key",
                        "cli-production-001",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )

        self.assertEqual(promote_exit, 0)
        self.assertEqual(json.loads(promote_stdout.getvalue())["aliases"], ["production"])
        self.assertEqual(trigger_exit, 0)
        self.assertEqual(json.loads(trigger_stdout.getvalue())["workflow_version"], "0.1.0")

    def test_workflow_artifacts_command_reports_bounded_consistency_without_values(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            workflow_path = root / "workflow.json"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            with redirect_stdout(StringIO()):
                publish_exit = main(
                    [
                        "publish",
                        str(workflow_path),
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )
            output = StringIO()
            with redirect_stdout(output):
                report_exit = main(
                    [
                        "workflow-artifacts",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )

        report = json.loads(output.getvalue())
        self.assertEqual(publish_exit, 0)
        self.assertEqual(report_exit, 0)
        self.assertEqual(
            report["schema_version"],
            "skill2workflow-workflow-artifact-report-0.1.0",
        )
        self.assertEqual(report["status"], "clean")
        self.assertNotIn("Start", output.getvalue())
        self.assertNotIn("Sensitive", output.getvalue())

    def test_audit_consistency_command_reports_run_evidence_without_values(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            workflow_path = root / "workflow.json"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    main(
                        [
                            "publish",
                            str(workflow_path),
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )
                self.assertEqual(
                    main(
                        [
                            "run-published",
                            "workflow_demo",
                            "--version",
                            "0.1.0",
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )

            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "audit-consistency",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )

        report = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            report["schema_version"],
            "skill2workflow-run-audit-report-0.1.0",
        )
        self.assertEqual(report["status"], "clean")
        self.assertNotIn("Start", output.getvalue())

    def test_workflow_diff_and_expected_promotion_version_are_safe_cli_contracts(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            first_path = root / "workflow-v1.json"
            second_path = root / "workflow-v2.json"
            first_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            second = _workflow()
            second["workflow"]["version"] = "0.2.0"
            second["nodes"][0]["title"] = "Sensitive customer instruction"
            second_path.write_text(json.dumps(second), encoding="utf-8")

            with redirect_stdout(StringIO()):
                self.assertEqual(
                    main(
                        [
                            "publish",
                            str(first_path),
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )
                self.assertEqual(
                    main(
                        [
                            "publish",
                            str(second_path),
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            "sqlite",
                        ]
                    ),
                    0,
                )

            diff_stdout = StringIO()
            with redirect_stdout(diff_stdout):
                diff_exit = main(
                    [
                        "workflow-diff",
                        "workflow_demo",
                        "--from-version",
                        "0.1.0",
                        "--to-version",
                        "0.2.0",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )
            with redirect_stdout(StringIO()):
                first_promote_exit = main(
                    [
                        "promote",
                        "workflow_demo",
                        "--version",
                        "0.1.0",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )
                second_promote_exit = main(
                    [
                        "promote",
                        "workflow_demo",
                        "--version",
                        "0.2.0",
                        "--expected-current-version",
                        "0.1.0",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )
            stale_stderr = StringIO()
            with redirect_stderr(stale_stderr):
                stale_exit = main(
                    [
                        "promote",
                        "workflow_demo",
                        "--version",
                        "0.1.0",
                        "--expected-current-version",
                        "0.1.0",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )

        diff = json.loads(diff_stdout.getvalue())
        self.assertEqual(diff_exit, 0)
        self.assertTrue(diff["changed"])
        self.assertEqual(diff["changes"]["nodes"]["changed"], ["start"])
        self.assertNotIn("Sensitive customer instruction", diff_stdout.getvalue())
        self.assertEqual(first_promote_exit, 0)
        self.assertEqual(second_promote_exit, 0)
        self.assertEqual(stale_exit, 1)
        self.assertIn("workflow alias precondition failed", stale_stderr.getvalue())

    def test_published_run_resume_detail_and_audit_filters(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workflow_path = tmp_path / "approval-workflow.json"
            state_dir = tmp_path / "state"
            workflow_path.write_text(json.dumps(_approval_workflow()), encoding="utf-8")
            run_stdout = StringIO()
            resume_stdout = StringIO()
            runs_stdout = StringIO()
            detail_stdout = StringIO()
            audit_stdout = StringIO()

            with redirect_stdout(StringIO()):
                publish_exit = main(
                    ["publish", str(workflow_path), "--state-dir", str(state_dir), "--storage", "sqlite"]
                )
            with redirect_stdout(run_stdout):
                run_exit = main(
                    [
                        "run-published",
                        "workflow_demo",
                        "--version",
                        "0.1.0",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )
            run_state = json.loads(run_stdout.getvalue())
            with redirect_stdout(resume_stdout):
                resume_exit = main(
                    [
                        "resume-published",
                        run_state["run_id"],
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )
            with redirect_stdout(runs_stdout):
                runs_exit = main(["control-runs", "--state-dir", str(state_dir), "--storage", "sqlite"])
            with redirect_stdout(detail_stdout):
                detail_exit = main(
                    ["control-run", run_state["run_id"], "--state-dir", str(state_dir), "--storage", "sqlite"]
                )
            with redirect_stdout(audit_stdout):
                audit_exit = main(
                    [
                        "audit",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                        "--run-id",
                        run_state["run_id"],
                        "--event-type",
                        "run_completed",
                    ]
                )

            resumed = json.loads(resume_stdout.getvalue())
            run_summaries = json.loads(runs_stdout.getvalue())
            detail = json.loads(detail_stdout.getvalue())
            audit_events = json.loads(audit_stdout.getvalue())

        self.assertEqual(publish_exit, 0)
        self.assertEqual(run_exit, 0)
        self.assertEqual(resume_exit, 0)
        self.assertEqual(runs_exit, 0)
        self.assertEqual(detail_exit, 0)
        self.assertEqual(audit_exit, 0)
        self.assertEqual(run_state["status"], "waiting")
        self.assertEqual(resumed["status"], "completed")
        self.assertEqual(run_summaries[0]["run_id"], run_state["run_id"])
        self.assertEqual(detail["status"], "completed")
        self.assertEqual([event["type"] for event in audit_events], ["run_completed"])
        self.assertEqual(audit_events[0]["run_id"], run_state["run_id"])

    def test_local_run_commands_support_bounded_windows_for_json_and_sqlite(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow_path = root / "workflow.json"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")

            for storage in ("json", "sqlite"):
                state_dir = root / storage
                with redirect_stdout(StringIO()):
                    self.assertEqual(
                        main(
                            [
                                "run",
                                str(workflow_path),
                                "--state-dir",
                                str(state_dir),
                                "--storage",
                                storage,
                            ]
                        ),
                        0,
                    )
                    self.assertEqual(
                        main(
                            [
                                "run",
                                str(workflow_path),
                                "--state-dir",
                                str(state_dir),
                                "--storage",
                                storage,
                            ]
                        ),
                        0,
                    )
                runs_stdout = StringIO()
                control_runs_stdout = StringIO()
                with redirect_stdout(runs_stdout):
                    runs_exit = main(
                        [
                            "runs",
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            storage,
                            "--limit",
                            "1",
                        ]
                    )
                with redirect_stdout(control_runs_stdout):
                    control_runs_exit = main(
                        [
                            "control-runs",
                            "--state-dir",
                            str(state_dir),
                            "--storage",
                            storage,
                            "--limit",
                            "1",
                        ]
                    )

                self.assertEqual(runs_exit, 0)
                self.assertEqual(control_runs_exit, 0)
                self.assertEqual(len(json.loads(runs_stdout.getvalue())), 1)
                self.assertEqual(len(json.loads(control_runs_stdout.getvalue())), 1)

    def test_local_run_commands_reject_invalid_limit_without_traceback(self):
        with TemporaryDirectory() as tmp:
            stderr = StringIO()
            with redirect_stderr(stderr):
                exit_code = main(
                    [
                        "runs",
                        "--state-dir",
                        str(Path(tmp) / "state"),
                        "--limit",
                        "0",
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue(), "run list limit must be an integer from 1 through 1000\n")

    def test_audit_command_supports_bounded_tail_after_filters(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            from skill2workflow.control_plane import LocalControlPlane

            control = LocalControlPlane(state_dir, storage="sqlite")
            for index, event_type in enumerate(
                ("run_started", "connector_started", "connector_failed", "run_completed")
            ):
                control.store.append_audit(
                    {
                        "type": event_type,
                        "workflow_id": "workflow_audit",
                        "workflow_version": "0.1.0",
                        "run_id": "run_audit",
                        "timestamp": f"2026-08-14T00:00:{index:02d}Z",
                    }
                )
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "audit",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                        "--run-id",
                        "run_audit",
                        "--limit",
                        "2",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            [event["type"] for event in json.loads(stdout.getvalue())],
            ["connector_failed", "run_completed"],
        )

    def test_audit_command_rejects_unbounded_limit_without_traceback(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            stderr = StringIO()
            with redirect_stderr(stderr):
                exit_code = main(
                    [
                        "audit",
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                        "--limit",
                        "1001",
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue(), "audit event limit must be an integer from 1 to 1000\n")

    def test_control_snapshot_command_writes_operator_snapshot(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workflow_path = tmp_path / "workflow.json"
            state_dir = tmp_path / "state"
            output_path = tmp_path / "snapshot.json"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")

            with redirect_stdout(StringIO()):
                publish_exit = main(["publish", str(workflow_path), "--state-dir", str(state_dir)])
                run_exit = main(
                    [
                        "run-published",
                        "workflow_demo",
                        "--version",
                        "0.1.0",
                        "--state-dir",
                        str(state_dir),
                    ]
                )
                snapshot_exit = main(
                    [
                        "control-snapshot",
                        "--state-dir",
                        str(state_dir),
                        "-o",
                        str(output_path),
                    ]
                )

            snapshot = json.loads(output_path.read_text(encoding="utf-8"))
            output_mode = output_path.stat().st_mode & 0o777

        self.assertEqual(publish_exit, 0)
        self.assertEqual(run_exit, 0)
        self.assertEqual(snapshot_exit, 0)
        self.assertEqual(snapshot["schema_version"], "skill2workflow-control-snapshot-0.1.0")
        self.assertEqual(snapshot["summary"]["workflow_count"], 1)
        self.assertEqual(snapshot["summary"]["run_count"], 1)
        self.assertEqual(snapshot["workflows"][0]["workflow_id"], "workflow_demo")
        self.assertEqual(snapshot["runs"][0]["workflow_id"], "workflow_demo")
        self.assertIn("run_completed", {event["type"] for event in snapshot["audit_events"]})
        self.assertEqual(output_mode, 0o600)

    def test_control_snapshot_command_accepts_bounded_offline_window(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            first = root / "first.json"
            second = root / "second.json"
            first.write_text(json.dumps(_workflow()), encoding="utf-8")
            second_workflow = _workflow()
            second_workflow["workflow"]["version"] = "0.2.0"
            second.write_text(json.dumps(second_workflow), encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["publish", str(first), "--state-dir", str(state_dir)]), 0)
                self.assertEqual(main(["publish", str(second), "--state-dir", str(state_dir)]), 0)
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "control-snapshot",
                        "--state-dir",
                        str(state_dir),
                        "--max-items",
                        "1",
                    ]
                )

        snapshot = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(snapshot["window"]["max_items"], 1)
        self.assertEqual(len(snapshot["workflows"]), 1)
        self.assertEqual(snapshot["window"]["workflows"]["truncated"], True)

    def test_control_snapshot_command_rejects_max_items_for_live_service(self):
        stderr = StringIO()
        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "control-snapshot",
                    "--service-url",
                    "https://workflow.example.test",
                    "--auth-token-file",
                    "/private/ingress.token",
                    "--max-items",
                    "1",
                ]
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue(), "--max-items is only valid for offline snapshots\n")

    def test_control_snapshot_command_fetches_live_service_without_printing_token(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            token_file = root / "ingress.token"
            output_path = root / "live-snapshot.json"
            token_file.write_text("t" * 48, encoding="utf-8")
            token_file.chmod(0o600)
            snapshot = {
                "schema_version": "skill2workflow-control-snapshot-0.1.0",
                "window": {"max_items": 100},
            }

            with patch(
                "skill2workflow.cli.fetch_live_control_snapshot",
                return_value=snapshot,
            ) as fetch:
                exit_code = main(
                    [
                        "control-snapshot",
                        "--service-url",
                        "https://workflow.example.test",
                        "--auth-token-file",
                        str(token_file),
                        "-o",
                        str(output_path),
                    ]
                )
                fetched_call = fetch.call_args
            written_snapshot = json.loads(output_path.read_text(encoding="utf-8"))
            written_mode = output_path.stat().st_mode & 0o777

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            fetched_call.args,
            ("https://workflow.example.test", token_file),
        )
        self.assertEqual(written_snapshot, snapshot)
        self.assertEqual(written_mode, 0o600)

    def test_systemd_unit_command_writes_a_redacted_hardened_unit(self):
        from skill2workflow.service_bootstrap import initialize_service_workspace

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialized = initialize_service_workspace(
                root / "workspace",
                token_factory=lambda: "t" * 48,
            )
            executable = root / "bin" / "skill2workflow"
            executable.parent.mkdir()
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o700)
            output = root / "skill2workflow.service"
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "systemd-unit",
                        "--config",
                        str(initialized["config_file"]),
                        "--output",
                        str(output),
                        "--service-user",
                        "workflow",
                        "--executable",
                        str(executable),
                    ]
                )

            result = json.loads(stdout.getvalue())
            content = output.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(result["status"], "written")
        self.assertEqual(result["unit_name"], "skill2workflow.service")
        self.assertIn("ExecStart=", content)
        self.assertIn("ProtectSystem=strict", content)
        self.assertNotIn("t" * 48, stdout.getvalue())
        self.assertNotIn("t" * 48, content)

    def test_run_and_list_runs_can_use_sqlite_storage(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workflow_path = tmp_path / "workflow.json"
            state_dir = tmp_path / "state"
            workflow_path.write_text(json.dumps(_workflow()), encoding="utf-8")
            run_stdout = StringIO()
            runs_stdout = StringIO()

            with redirect_stdout(run_stdout):
                run_exit = main(
                    [
                        "run",
                        str(workflow_path),
                        "--state-dir",
                        str(state_dir),
                        "--storage",
                        "sqlite",
                    ]
                )
            with redirect_stdout(runs_stdout):
                runs_exit = main(["runs", "--state-dir", str(state_dir), "--storage", "sqlite"])

            run_state = json.loads(run_stdout.getvalue())
            run_summaries = json.loads(runs_stdout.getvalue())
            db_exists = (state_dir / "runs.sqlite3").exists()

        self.assertEqual(run_exit, 0)
        self.assertEqual(runs_exit, 0)
        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(run_summaries[0]["run_id"], run_state["run_id"])
        self.assertEqual(run_summaries[0]["status"], "completed")
        self.assertTrue(db_exists)

    def test_run_command_uses_local_credential_file_without_printing_secret(self):
        server = _CliConnectorTestServer()

        try:
            with TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                workflow_path = tmp_path / "credential-workflow.json"
                credentials_path = tmp_path / "credentials.json"
                state_dir = tmp_path / "state"
                workflow_path.write_text(json.dumps(_credential_workflow(server.url)), encoding="utf-8")
                credentials_path.write_text(
                    json.dumps({"credentials": {"demo_api_token": "secret-token"}}),
                    encoding="utf-8",
                )
                stdout = StringIO()

                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "run",
                            str(workflow_path),
                            "--state-dir",
                            str(state_dir),
                            "--credential-file",
                            str(credentials_path),
                        ]
                    )

                run_state = json.loads(stdout.getvalue())
        finally:
            server.close()

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(server.requests[0]["headers"]["Authorization"], "Bearer secret-token")
        self.assertNotIn("secret-token", stdout.getvalue())

    def test_validate_command_can_emit_structured_json_errors(self):
        with TemporaryDirectory() as tmp:
            workflow_path = Path(tmp) / "workflow.json"
            invalid = _workflow()
            invalid["edges"][0]["to"] = "missing"
            workflow_path.write_text(json.dumps(invalid), encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["validate", str(workflow_path), "--format", "json"])

        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(payload["valid"], False)
        self.assertEqual(payload["schema_version"], "0.1.0")
        self.assertIn("errors", payload)
        self.assertTrue(any(error["code"] == "edge_target_missing" for error in payload["errors"]))

    def test_write_back_command_writes_edited_workflow_dsl(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workflow_path = tmp_path / "workflow.json"
            graph_path = tmp_path / "graph.json"
            output_path = tmp_path / "edited-workflow.json"
            workflow = _workflow()
            workflow_path.write_text(json.dumps(workflow), encoding="utf-8")

            from skill2workflow.visualizer import workflow_to_litegraph

            graph = workflow_to_litegraph(workflow)
            graph["nodes"][0]["title"] = "Edited Start"
            graph["nodes"][0]["properties"]["description"] = "Edited entry point."
            graph_path.write_text(json.dumps(graph), encoding="utf-8")
            stdout = StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "write-back",
                        str(workflow_path),
                        str(graph_path),
                        "-o",
                        str(output_path),
                    ]
                )

            edited = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(edited["nodes"][0]["title"], "Edited Start")
        self.assertEqual(edited["nodes"][0]["description"], "Edited entry point.")
        self.assertEqual(edited["edges"], workflow["edges"])

    def test_bundle_commands_create_and_verify_a_portable_artifact(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow_path = root / "workflow.json"
            bundle_path = root / "workflow.s2w"
            workflow_path.write_text(json.dumps(_approval_workflow()), encoding="utf-8")
            created = StringIO()
            with redirect_stdout(created):
                create_exit = main(
                    [
                        "bundle-create",
                        str(workflow_path),
                        "--output",
                        str(bundle_path),
                    ]
                )
            verified = StringIO()
            with redirect_stdout(verified):
                verify_exit = main(["bundle-verify", str(bundle_path)])

        self.assertEqual(create_exit, 0)
        self.assertEqual(verify_exit, 0)
        self.assertTrue(json.loads(created.getvalue())["valid"])
        self.assertTrue(json.loads(verified.getvalue())["valid"])

    def test_bundle_verify_maps_invalid_artifact_to_nonzero_without_traceback(self):
        with TemporaryDirectory() as tmp:
            bundle_path = Path(tmp) / "invalid.s2w"
            bundle_path.write_bytes(b"not a zip")
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["bundle-verify", str(bundle_path)])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue(), "")
        report = json.loads(stdout.getvalue())
        self.assertFalse(report["valid"])
        self.assertEqual(report["errors"][0]["code"], "bundle_unreadable")


def _workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {"id": "workflow_demo", "name": "demo", "version": "0.1.0", "status": "draft"},
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "end"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [{"id": "edge_start_end", "from": "start", "to": "end", "label": "next"}],
    }


def _approval_workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {"id": "workflow_demo", "name": "demo", "version": "0.1.0", "status": "draft"},
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "review"},
            {
                "id": "review",
                "type": "human_gate",
                "title": "Review",
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "failure", "type": "failure", "title": "Failure"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "edge_start_review", "from": "start", "to": "review", "label": "next"},
            {"id": "edge_review_end", "from": "review", "to": "end", "label": "next"},
            {"id": "edge_review_failure", "from": "review", "to": "failure", "label": "failure"},
        ],
    }


def _credential_workflow(url: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {"id": "workflow_credential", "name": "credential", "version": "0.1.0", "status": "draft"},
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "call_api"},
            {
                "id": "call_api",
                "type": "tool_call",
                "title": "Call API",
                "connector": {
                    "id": "http",
                    "kind": "http",
                    "request": {
                        "method": "GET",
                        "url": url,
                        "timeout_ms": 2000,
                    },
                    "credentials": [
                        {
                            "target": "header",
                            "name": "Authorization",
                            "handle": "demo_api_token",
                            "prefix": "Bearer ",
                        }
                    ],
                },
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "failure", "type": "failure", "title": "Failure"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "edge_start_call", "from": "start", "to": "call_api", "label": "next"},
            {"id": "edge_call_end", "from": "call_api", "to": "end", "label": "next"},
            {"id": "edge_call_failure", "from": "call_api", "to": "failure", "label": "failure"},
        ],
    }


def _mapped_connector_workflow(url: str):
    workflow = _credential_workflow(url)
    workflow["workflow"] = {
        "id": "workflow_mapped_connector",
        "name": "mapped-connector",
        "version": "0.1.0",
        "status": "draft",
    }
    connector = workflow["nodes"][1]["connector"]
    connector.pop("credentials")
    connector["request"] = {
        "method": "POST",
        "url": url,
        "headers": {"Content-Type": "application/json"},
        "body": {"source": "skill2workflow"},
        "input_mapping": [
            {"from": "/input/customer_id", "to": "/body/customer_id", "required": True},
        ],
        "timeout_ms": 2000,
    }
    return workflow


def _audit_event_page_fixture():
    return {
        "schema_version": "skill2workflow-audit-event-list-0.1.0",
        "filters": {
            "workflow_id": "workflow",
            "workflow_version": "0.1.0",
            "run_id": "run_remote_1",
            "event_type": "connector_failed",
        },
        "events": [],
        "window": {
            "max_items": 10,
            "total": 0,
            "returned": 0,
            "truncated": False,
            "next_cursor": "",
        },
    }


class _CliConnectorRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requests.append({"headers": dict(self.headers.items())})
        payload = json.dumps({"ok": True}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        body = json.loads(raw_body) if raw_body else None
        self.server.requests.append({"headers": dict(self.headers.items()), "body": body})
        payload = json.dumps({"ok": True}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


class _CliConnectorTestServer:
    def __init__(self):
        self._server = HTTPServer(("127.0.0.1", 0), _CliConnectorRequestHandler)
        self._server.requests = []
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/credential"

    @property
    def requests(self):
        return self._server.requests

    def close(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)
