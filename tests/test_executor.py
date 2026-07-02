import json
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.executor import LocalExecutor


class ExecutorTests(TestCase):
    def test_run_pauses_at_human_gate_and_resume_completes(self):
        workflow = {
            "schema_version": "0.1.0",
            "workflow": {
                "id": "workflow_approval",
                "name": "approval",
                "version": "0.1.0",
                "status": "published",
            },
            "entry": "start",
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "title": "Start",
                    "on_success": "review",
                },
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
            "edges": [],
        }

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp))
            waiting = executor.run(workflow)
            self.assertEqual(waiting["status"], "waiting")
            self.assertEqual(waiting["current_node"], "review")

            completed = executor.resume(waiting["run_id"], approved=True)

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["current_node"], "end")

    def test_resume_records_human_gate_result_and_terminal_result(self):
        workflow = _approval_workflow()

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp))
            waiting = executor.run(workflow)
            completed = executor.resume(waiting["run_id"], approved=True)

        review_result = completed["node_results"]["review"]
        self.assertEqual(review_result["status"], "approved")
        self.assertEqual(review_result["title"], "Review")
        self.assertEqual(review_result["approved"], True)
        self.assertIn("timestamp", review_result)
        self.assertEqual(completed["node_results"]["end"]["status"], "completed")
        self.assertEqual(completed["node_results"]["end"]["title"], "End")

    def test_resume_rejection_records_human_gate_result_and_fails(self):
        workflow = _approval_workflow()

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp))
            waiting = executor.run(workflow)
            failed = executor.resume(waiting["run_id"], approved=False)

        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["current_node"], "failure")
        review_result = failed["node_results"]["review"]
        self.assertEqual(review_result["status"], "rejected")
        self.assertEqual(review_result["title"], "Review")
        self.assertEqual(review_result["approved"], False)
        self.assertIn("timestamp", review_result)
        self.assertEqual(failed["node_results"]["failure"]["status"], "failed")

    def test_list_runs_returns_control_plane_summaries(self):
        workflow = _approval_workflow()

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp))
            waiting = executor.run(workflow)
            summary = executor.list_runs()[0]
            detail = executor.get_run(waiting["run_id"])

        self.assertEqual(
            summary,
            {
                "run_id": waiting["run_id"],
                "workflow_id": "workflow_approval",
                "workflow_version": "0.1.0",
                "status": "waiting",
                "current_node": "review",
                "event_count": 3,
                "node_result_count": 1,
            },
        )
        self.assertEqual(detail["run_id"], waiting["run_id"])
        self.assertIn("workflow", detail)
        self.assertIn("events", detail)
        self.assertIn("node_results", detail)

    def test_sqlite_storage_persists_run_state_and_event_rows_across_instances(self):
        workflow = _approval_workflow()

        with TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            waiting = LocalExecutor(state_dir, storage="sqlite").run(workflow)

            restarted = LocalExecutor(state_dir, storage="sqlite")
            detail = restarted.get_run(waiting["run_id"])
            completed = restarted.resume(waiting["run_id"], approved=True)
            summary = restarted.list_runs()[0]

            db_path = state_dir / "runs.sqlite3"
            with sqlite3.connect(db_path) as connection:
                event_rows = connection.execute(
                    "select event_type, node_id from run_events where run_id = ? order by sequence",
                    (waiting["run_id"],),
                ).fetchall()

        self.assertEqual(detail["status"], "waiting")
        self.assertEqual(detail["current_node"], "review")
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["event_count"], len(event_rows))
        self.assertEqual(
            [row[0] for row in event_rows],
            [
                "node_started",
                "node_completed",
                "human_gate_waiting",
                "human_gate_resumed",
                "run_completed",
            ],
        )

    def test_http_connector_executes_request_and_records_events(self):
        server = _ConnectorTestServer()
        workflow = _http_connector_workflow(server.url)

        try:
            with TemporaryDirectory() as tmp:
                state = LocalExecutor(Path(tmp), storage="sqlite").run(workflow)

                with sqlite3.connect(Path(tmp) / "runs.sqlite3") as connection:
                    event_rows = connection.execute(
                        "select event_type, node_id from run_events where run_id = ? order by sequence",
                        (state["run_id"],),
                    ).fetchall()
        finally:
            server.close()

        call_result = state["node_results"]["call_api"]
        self.assertEqual(state["status"], "completed")
        self.assertEqual(server.requests[0]["path"], "/connector")
        self.assertEqual(server.requests[0]["body"], {"account_id": "acct_123"})
        self.assertEqual(call_result["status"], "completed")
        self.assertEqual(call_result["connector"]["id"], "http")
        self.assertEqual(call_result["connector"]["kind"], "http")
        self.assertEqual(call_result["output"]["status_code"], 200)
        self.assertEqual(json.loads(call_result["output"]["body"]), {"ok": True})
        self.assertIn(("connector_started", "call_api"), event_rows)
        self.assertIn(("connector_completed", "call_api"), event_rows)


def _approval_workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_approval",
            "name": "approval",
            "version": "0.1.0",
            "status": "published",
        },
        "entry": "start",
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "title": "Start",
                "on_success": "review",
            },
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
        "edges": [],
    }


def _http_connector_workflow(url: str):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_connector",
            "name": "connector",
            "version": "0.1.0",
            "status": "published",
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
                        "body": {"account_id": "acct_123"},
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
        self.server.requests.append({"path": self.path, "body": body})
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
