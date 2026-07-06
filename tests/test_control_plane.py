import json
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.credentials import StaticCredentialProvider


class ControlPlaneTests(TestCase):
    def test_publish_workflow_persists_immutable_version_and_audit(self):
        workflow = _workflow(version="1.0.0")

        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp))
            record = control.publish_workflow(workflow)
            stored = control.get_workflow("workflow_control", "1.0.0")
            audit_events = control.list_audit_events()

            changed = _workflow(version="1.0.0")
            changed["nodes"][0]["title"] = "Changed Start"
            with self.assertRaisesRegex(ValueError, "immutable"):
                control.publish_workflow(changed)

        self.assertEqual(record["workflow_id"], "workflow_control")
        self.assertEqual(record["version"], "1.0.0")
        self.assertEqual(record["status"], "published")
        self.assertEqual(stored["workflow"]["status"], "published")
        self.assertEqual(audit_events[0]["type"], "workflow_published")
        self.assertEqual(audit_events[0]["workflow_id"], "workflow_control")
        self.assertIn("checksum", record)

    def test_deprecate_updates_registry_without_mutating_published_artifact(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp))
            control.publish_workflow(_workflow(version="1.0.0"))

            record = control.deprecate_workflow("workflow_control", "1.0.0")
            stored = control.get_workflow("workflow_control", "1.0.0")
            audit_types = [event["type"] for event in control.list_audit_events()]

        self.assertEqual(record["status"], "deprecated")
        self.assertEqual(stored["workflow"]["status"], "published")
        self.assertEqual(audit_types, ["workflow_published", "workflow_deprecated"])

    def test_run_published_workflow_binds_run_to_immutable_version_and_audit(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp))
            control.publish_workflow(_workflow(version="2.0.0"))

            run_state = control.run_published_workflow("workflow_control", "2.0.0")
            run_summary = control.list_runs()[0]
            audit_events = control.list_audit_events()
            audit_types = [event["type"] for event in audit_events]

        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(run_state["workflow_id"], "workflow_control")
        self.assertEqual(run_state["workflow_version"], "2.0.0")
        self.assertEqual(run_summary["workflow_version"], "2.0.0")
        self.assertIn("run_started", audit_types)
        self.assertIn("run_completed", audit_types)
        self.assertEqual(audit_events[1]["run_id"], run_state["run_id"])

    def test_trigger_workflow_starts_published_run_with_trigger_metadata(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_workflow(version="10.0.0"))

            result = control.trigger_workflow(
                {
                    "workflow_id": "workflow_control",
                    "version": "10.0.0",
                    "source": "local-test",
                    "idempotency_key": "demo-1",
                    "input": {"customer_id": "customer_123"},
                }
            )
            detail = control.get_run(result["run_id"])
            audit_events = control.list_audit_events(run_id=result["run_id"])
            started_events = control.list_audit_events(run_id=result["run_id"], event_type="run_started")

        self.assertTrue(result["trigger_id"].startswith("trigger_"))
        self.assertEqual(result["workflow_id"], "workflow_control")
        self.assertEqual(result["workflow_version"], "10.0.0")
        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(result["source"], "local-test")
        self.assertEqual(result["idempotency_key"], "demo-1")
        self.assertEqual(result["input_keys"], ["customer_id"])
        self.assertEqual(detail["context"]["input"], {"customer_id": "customer_123"})
        self.assertEqual(
            detail["context"]["trigger"],
            {
                "trigger_id": result["trigger_id"],
                "source": "local-test",
                "idempotency_key": "demo-1",
                "input_keys": ["customer_id"],
            },
        )
        self.assertEqual([event["type"] for event in audit_events], ["run_started", "run_completed"])
        self.assertEqual(started_events[0]["trigger_id"], result["trigger_id"])
        self.assertEqual(started_events[0]["trigger_source"], "local-test")
        self.assertEqual(started_events[0]["idempotency_key"], "demo-1")
        self.assertEqual(started_events[0]["input_keys"], ["customer_id"])
        self.assertNotIn("input", started_events[0])

    def test_run_published_workflow_can_use_sqlite_run_storage(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")
            control.publish_workflow(_workflow(version="2.0.0"))

            run_state = control.run_published_workflow("workflow_control", "2.0.0")
            run_summary = LocalControlPlane(state_dir, storage="sqlite").list_runs()[0]

        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(run_summary["run_id"], run_state["run_id"])
        self.assertEqual(run_summary["workflow_id"], "workflow_control")

    def test_sqlite_storage_persists_workflow_registry_and_audit_events(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            control = LocalControlPlane(state_dir, storage="sqlite")

            record = control.publish_workflow(_workflow(version="3.0.0"))
            deprecated = control.deprecate_workflow("workflow_control", "3.0.0")
            records = LocalControlPlane(state_dir, storage="sqlite").list_workflows()
            audit_types = [event["type"] for event in control.list_audit_events()]

            with sqlite3.connect(state_dir / "control.sqlite3") as connection:
                workflow_rows = connection.execute("select workflow_id, version, status from workflow_versions").fetchall()
                audit_rows = connection.execute("select event_type from audit_events order by sequence").fetchall()

        self.assertEqual(record["workflow_id"], "workflow_control")
        self.assertEqual(deprecated["status"], "deprecated")
        self.assertEqual(records[0]["status"], "deprecated")
        self.assertEqual(workflow_rows, [("workflow_control", "3.0.0", "deprecated")])
        self.assertEqual([row[0] for row in audit_rows], ["workflow_published", "workflow_deprecated"])
        self.assertEqual(audit_types, ["workflow_published", "workflow_deprecated"])

    def test_sqlite_storage_imports_existing_json_registry_and_audit(self):
        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            json_control = LocalControlPlane(state_dir)
            json_control.publish_workflow(_workflow(version="4.0.0"))

            sqlite_control = LocalControlPlane(state_dir, storage="sqlite")
            records = sqlite_control.list_workflows()
            audit_types_before_run = [event["type"] for event in sqlite_control.list_audit_events()]
            run_state = sqlite_control.run_published_workflow("workflow_control", "4.0.0")
            audit_types_after_run = [event["type"] for event in sqlite_control.list_audit_events()]

        self.assertEqual(records[0]["workflow_id"], "workflow_control")
        self.assertEqual(records[0]["version"], "4.0.0")
        self.assertEqual(audit_types_before_run, ["workflow_published"])
        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(audit_types_after_run, ["workflow_published", "run_started", "run_completed"])

    def test_resume_published_run_records_resume_and_terminal_audit(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_approval_workflow(version="5.0.0"))

            waiting = control.run_published_workflow("workflow_control", "5.0.0")
            completed = control.resume_published_run(waiting["run_id"], approved=True)
            detail = control.get_run(waiting["run_id"])
            audit_events = control.list_audit_events(run_id=waiting["run_id"])
            completed_events = control.list_audit_events(event_type="run_completed")

        self.assertEqual(waiting["status"], "waiting")
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(detail["status"], "completed")
        self.assertEqual(
            [event["type"] for event in audit_events],
            ["run_started", "run_waiting", "run_resumed", "run_completed"],
        )
        self.assertEqual(completed_events[0]["run_id"], waiting["run_id"])

    def test_audit_events_can_filter_by_workflow_version_and_run_id(self):
        with TemporaryDirectory() as tmp:
            control = LocalControlPlane(Path(tmp), storage="sqlite")
            control.publish_workflow(_workflow(version="6.0.0"))
            control.publish_workflow(_workflow(version="7.0.0"))

            first = control.run_published_workflow("workflow_control", "6.0.0")
            second = control.run_published_workflow("workflow_control", "7.0.0")
            version_events = control.list_audit_events(workflow_id="workflow_control", version="6.0.0")
            run_events = control.list_audit_events(run_id=second["run_id"])

        self.assertTrue(all(event.get("workflow_version") == "6.0.0" for event in version_events))
        self.assertEqual([event["type"] for event in run_events], ["run_started", "run_completed"])
        self.assertEqual(run_events[0]["run_id"], second["run_id"])
        self.assertNotEqual(first["run_id"], second["run_id"])

    def test_connector_registry_returns_active_connector_manifests(self):
        with TemporaryDirectory() as tmp:
            connectors = LocalControlPlane(Path(tmp)).list_connectors()

        connector_ids = {connector["id"] for connector in connectors}
        http_connector = next(connector for connector in connectors if connector["id"] == "http")
        self.assertIn("manual", connector_ids)
        self.assertIn("http", connector_ids)
        self.assertTrue(all(connector["status"] == "active" for connector in connectors))
        self.assertTrue(all("node_types" in connector for connector in connectors))
        self.assertIn("input_mapping", http_connector["config_schema"]["properties"]["request"]["properties"])

    def test_published_connector_run_records_connector_audit_events(self):
        server = _ConnectorTestServer()

        try:
            with TemporaryDirectory() as tmp:
                control = LocalControlPlane(Path(tmp), storage="sqlite")
                control.publish_workflow(_connector_workflow("8.0.0", server.url))

                run_state = control.run_published_workflow("workflow_connector", "8.0.0")
                started_events = control.list_audit_events(
                    run_id=run_state["run_id"],
                    event_type="connector_started",
                )
                completed_events = control.list_audit_events(
                    run_id=run_state["run_id"],
                    event_type="connector_completed",
                )
        finally:
            server.close()

        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(started_events[0]["workflow_id"], "workflow_connector")
        self.assertEqual(started_events[0]["workflow_version"], "8.0.0")
        self.assertEqual(started_events[0]["node_id"], "call_api")
        self.assertEqual(started_events[0]["connector_id"], "http")
        self.assertEqual(completed_events[0]["connector_status"], "completed")
        self.assertEqual(completed_events[0]["node_id"], "call_api")

    def test_published_connector_run_resolves_credentials_without_audit_leakage(self):
        server = _ConnectorTestServer()

        try:
            with TemporaryDirectory() as tmp:
                control = LocalControlPlane(
                    Path(tmp),
                    storage="sqlite",
                    credential_provider=StaticCredentialProvider({"demo_api_token": "secret-token"}),
                )
                control.publish_workflow(_credential_connector_workflow("11.0.0", server.url))

                run_state = control.run_published_workflow("workflow_connector", "11.0.0")
                audit_events = control.list_audit_events(run_id=run_state["run_id"])
        finally:
            server.close()

        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(server.requests[0]["headers"]["Authorization"], "Bearer secret-token")
        self.assertNotIn("secret-token", json.dumps(run_state["node_results"]))
        self.assertNotIn("secret-token", json.dumps(audit_events))

    def test_triggered_connector_mapping_promotes_compact_audit_metadata(self):
        server = _ConnectorTestServer()

        try:
            with TemporaryDirectory() as tmp:
                control = LocalControlPlane(Path(tmp), storage="sqlite")
                control.publish_workflow(_mapped_connector_workflow("12.0.0", server.url))

                result = control.trigger_workflow(
                    {
                        "workflow_id": "workflow_connector",
                        "version": "12.0.0",
                        "source": "local-test",
                        "input": {"customer_id": "customer_123"},
                    }
                )
                audit_events = control.list_audit_events(run_id=result["run_id"])
                completed_events = control.list_audit_events(
                    run_id=result["run_id"],
                    event_type="connector_completed",
                )
        finally:
            server.close()

        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(server.requests[0]["body"], {"approved": True, "customer_id": "customer_123"})
        self.assertEqual(completed_events[0]["input_mapping_status"], "applied")
        self.assertEqual(completed_events[0]["input_mapping_keys"], ["customer_id"])
        self.assertNotIn("customer_123", json.dumps(audit_events))

    def test_published_retry_policy_promotes_policy_events_to_audit(self):
        server = _FlakyConnectorTestServer()

        try:
            with TemporaryDirectory() as tmp:
                control = LocalControlPlane(Path(tmp), storage="sqlite")
                workflow = _connector_workflow("9.0.0", server.url)
                workflow["nodes"][1]["retry"] = {"max_attempts": 1}
                control.publish_workflow(workflow)

                run_state = control.run_published_workflow("workflow_connector", "9.0.0")
                retry_events = control.list_audit_events(
                    run_id=run_state["run_id"],
                    event_type="node_retrying",
                )
                recovered_events = control.list_audit_events(
                    run_id=run_state["run_id"],
                    event_type="node_recovered",
                )
        finally:
            server.close()

        self.assertEqual(run_state["status"], "completed")
        self.assertEqual(retry_events[0]["node_id"], "call_api")
        self.assertEqual(retry_events[0]["attempt"], 1)
        self.assertEqual(retry_events[0]["max_attempts"], 1)
        self.assertIn("HTTP 503", retry_events[0]["error"])
        self.assertEqual(recovered_events[0]["node_id"], "call_api")
        self.assertEqual(recovered_events[0]["attempt"], 2)


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


def _approval_workflow(version: str):
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


def _connector_workflow(version: str, url: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_connector",
            "name": "connector",
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
                        "body": {"approved": True},
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


def _credential_connector_workflow(version: str, url: str):
    workflow = _connector_workflow(version, url)
    workflow["nodes"][1]["connector"]["credentials"] = [
        {
            "target": "header",
            "name": "Authorization",
            "handle": "demo_api_token",
            "prefix": "Bearer ",
        }
    ]
    return workflow


def _mapped_connector_workflow(version: str, url: str):
    workflow = _connector_workflow(version, url)
    workflow["nodes"][1]["connector"]["request"]["input_mapping"] = [
        {"from": "/input/customer_id", "to": "/body/customer_id", "required": True},
    ]
    return workflow


class _ConnectorRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        body = json.loads(raw_body) if raw_body else None
        self.server.requests.append({"path": self.path, "headers": dict(self.headers.items()), "body": body})
        payload = json.dumps({"ok": True}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


class _FlakyConnectorRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        body = json.loads(raw_body) if raw_body else None
        self.server.requests.append({"path": self.path, "headers": dict(self.headers.items()), "body": body})

        if len(self.server.requests) == 1:
            payload = json.dumps({"error": "temporary"}).encode("utf-8")
            self.send_response(503)
        else:
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


class _FlakyConnectorTestServer(_ConnectorTestServer):
    def __init__(self):
        self._server = HTTPServer(("127.0.0.1", 0), _FlakyConnectorRequestHandler)
        self._server.requests = []
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
