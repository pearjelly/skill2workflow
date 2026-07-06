import json
import threading
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.cli import main


class CliTests(TestCase):
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

        self.assertEqual(publish_exit, 0)
        self.assertEqual(run_exit, 0)
        self.assertEqual(snapshot_exit, 0)
        self.assertEqual(snapshot["schema_version"], "skill2workflow-control-snapshot-0.1.0")
        self.assertEqual(snapshot["summary"]["workflow_count"], 1)
        self.assertEqual(snapshot["summary"]["run_count"], 1)
        self.assertEqual(snapshot["workflows"][0]["workflow_id"], "workflow_demo")
        self.assertEqual(snapshot["runs"][0]["workflow_id"], "workflow_demo")
        self.assertIn("run_completed", {event["type"] for event in snapshot["audit_events"]})

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


class _CliConnectorRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requests.append({"headers": dict(self.headers.items())})
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
