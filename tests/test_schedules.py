import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.schedules import (
    LocalScheduleRunner,
    LocalScheduleStore,
    normalize_schedule_definition,
)


class ScheduleTests(TestCase):
    def test_normalize_schedule_definition_accepts_one_shot_trigger_template(self):
        schedule = normalize_schedule_definition(
            {
                "schema_version": "skill2workflow-schedule-0.1.0",
                "schedule": {
                    "id": "schedule_daily_report",
                    "workflow_id": "workflow_control",
                    "version": "1.0.0",
                    "run_at": "2026-07-06T00:00:00Z",
                },
                "trigger": {
                    "input": {
                        "customer_id": "customer_123",
                        "priority": "high",
                    }
                },
            }
        )

        self.assertEqual(schedule["schema_version"], "skill2workflow-schedule-0.1.0")
        self.assertEqual(
            schedule["schedule"],
            {
                "id": "schedule_daily_report",
                "workflow_id": "workflow_control",
                "version": "1.0.0",
                "run_at": "2026-07-06T00:00:00+00:00",
                "enabled": True,
                "status": "pending",
                "last_run_at": "",
                "last_run_id": "",
                "last_trigger_id": "",
            },
        )
        self.assertEqual(
            schedule["trigger"],
            {
                "source": "local-schedule:schedule_daily_report",
                "idempotency_key": "schedule_daily_report:2026-07-06T00:00:00+00:00",
                "input": {
                    "customer_id": "customer_123",
                    "priority": "high",
                },
            },
        )

    def test_normalize_schedule_definition_rejects_invalid_contracts(self):
        with self.assertRaisesRegex(ValueError, "schedule definition must be a JSON object"):
            normalize_schedule_definition([])
        with self.assertRaisesRegex(ValueError, "schedule.id is required"):
            normalize_schedule_definition(
                {
                    "schema_version": "skill2workflow-schedule-0.1.0",
                    "schedule": {"workflow_id": "workflow_control", "version": "1.0.0", "run_at": "2026-07-06T00:00:00Z"},
                }
            )
        with self.assertRaisesRegex(ValueError, "schedule.run_at must be an ISO-8601 timestamp"):
            normalize_schedule_definition(
                {
                    "schema_version": "skill2workflow-schedule-0.1.0",
                    "schedule": {
                        "id": "schedule_daily_report",
                        "workflow_id": "workflow_control",
                        "version": "1.0.0",
                        "run_at": "tomorrow",
                    },
                }
            )
        with self.assertRaisesRegex(ValueError, "schedule trigger input must be a JSON object"):
            normalize_schedule_definition(
                {
                    "schema_version": "skill2workflow-schedule-0.1.0",
                    "schedule": {
                        "id": "schedule_daily_report",
                        "workflow_id": "workflow_control",
                        "version": "1.0.0",
                        "run_at": "2026-07-06T00:00:00Z",
                    },
                    "trigger": {"input": []},
                }
            )

    def test_schedule_store_persists_json_documents_under_state_dir(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            store = LocalScheduleStore(state_dir)

            saved = store.save(_schedule_definition())
            loaded = LocalScheduleStore(state_dir).list_schedules()

        self.assertEqual(saved["schedule"]["id"], "schedule_daily_report")
        self.assertEqual([item["schedule"]["id"] for item in loaded], ["schedule_daily_report"])
        self.assertEqual(loaded[0]["trigger"]["input"], {"customer_id": "customer_123"})

    def test_runner_selects_due_schedules_without_wall_clock_waiting(self):
        with TemporaryDirectory() as tmp:
            runner = LocalScheduleRunner(Path(tmp))
            runner.add_schedule(_schedule_definition())

            before = runner.list_due_schedules("2026-07-05T23:59:59Z")
            due = runner.list_due_schedules("2026-07-06T00:00:00Z")

        self.assertEqual(before, [])
        self.assertEqual([item["schedule"]["id"] for item in due], ["schedule_daily_report"])

    def test_runner_executes_due_schedules_through_trigger_boundary(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="1.0.0"))
            runner = LocalScheduleRunner(state_dir, storage="sqlite")
            runner.add_schedule(_schedule_definition())

            result = runner.run_due("2026-07-06T00:00:00Z")
            second_result = runner.run_due("2026-07-06T00:00:01Z")
            stored_schedule = runner.get_schedule("schedule_daily_report")
            run_detail = control.get_run(result["runs"][0]["run_id"])
            started_event = control.list_audit_events(run_id=result["runs"][0]["run_id"], event_type="run_started")[0]

        self.assertEqual(result["count"], 1)
        self.assertEqual(second_result["count"], 0)
        self.assertEqual(result["runs"][0]["schedule_id"], "schedule_daily_report")
        self.assertEqual(result["runs"][0]["source"], "local-schedule:schedule_daily_report")
        self.assertEqual(run_detail["context"]["input"], {"customer_id": "customer_123"})
        self.assertEqual(run_detail["context"]["trigger"]["source"], "local-schedule:schedule_daily_report")
        self.assertEqual(started_event["trigger_source"], "local-schedule:schedule_daily_report")
        self.assertEqual(started_event["input_keys"], ["customer_id"])
        self.assertNotIn("input", started_event)
        self.assertEqual(stored_schedule["schedule"]["status"], "completed")
        self.assertEqual(stored_schedule["schedule"]["last_run_id"], result["runs"][0]["run_id"])
        self.assertEqual(stored_schedule["schedule"]["last_trigger_id"], result["runs"][0]["trigger_id"])

    def test_runner_maps_schedule_input_into_connector_body(self):
        server = _ConnectorTestServer()

        try:
            with TemporaryDirectory() as tmp:
                state_dir = Path(tmp)
                control = LocalControlPlane(state_dir, storage="sqlite")
                control.publish_workflow(_mapped_connector_workflow(version="1.0.0", url=server.url))
                runner = LocalScheduleRunner(state_dir, storage="sqlite")
                runner.add_schedule(_schedule_definition())

                result = runner.run_due("2026-07-06T00:00:00Z")
                completed_events = control.list_audit_events(
                    run_id=result["runs"][0]["run_id"],
                    event_type="connector_completed",
                )
        finally:
            server.close()

        self.assertEqual(result["count"], 1)
        self.assertEqual(server.requests[0]["body"], {"source": "schedule", "customer_id": "customer_123"})
        self.assertEqual(completed_events[0]["input_mapping_status"], "applied")
        self.assertEqual(completed_events[0]["input_mapping_keys"], ["customer_id"])


def _schedule_definition():
    return {
        "schema_version": "skill2workflow-schedule-0.1.0",
        "schedule": {
            "id": "schedule_daily_report",
            "workflow_id": "workflow_control",
            "version": "1.0.0",
            "run_at": "2026-07-06T00:00:00Z",
        },
        "trigger": {
            "input": {
                "customer_id": "customer_123",
            }
        },
    }


def _workflow(version: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_control",
            "name": "control",
            "version": version,
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "end"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [{"id": "edge_start_end", "from": "start", "to": "end", "label": "next"}],
    }


def _mapped_connector_workflow(version: str, url: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_control",
            "name": "control",
            "version": version,
            "status": "draft",
        },
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
                        "method": "POST",
                        "url": url,
                        "headers": {"Content-Type": "application/json"},
                        "body": {"source": "schedule"},
                        "input_mapping": [
                            {"from": "/input/customer_id", "to": "/body/customer_id", "required": True},
                        ],
                        "timeout_ms": 2000,
                    },
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


class _ConnectorRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        body = json.loads(raw_body) if raw_body else None
        self.server.requests.append({"body": body})
        payload = json.dumps({"ok": True}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


class _ConnectorTestServer:
    def __init__(self):
        self._server = HTTPServer(("127.0.0.1", 0), _ConnectorRequestHandler)
        self._server.requests = []
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/connector"

    @property
    def requests(self):
        return self._server.requests

    def close(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)
