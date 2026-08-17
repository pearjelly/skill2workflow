import json
import threading
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.cli import main
from skill2workflow.service_client import (
    ServiceActionError,
    fetch_workflow_explanation,
)


AUTH_TOKEN = "explain-client-test-token-0123456789abcdef"


class WorkflowExplanationClientTests(TestCase):
    def test_cli_service_workflow_explain_uses_versioned_remote_read(self):
        stdout = StringIO()
        expected = _explanation()
        with patch(
            "skill2workflow.cli.fetch_workflow_explanation",
            return_value=expected,
        ) as fetch:
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "service-workflow-explain",
                        "workflow_private",
                        "--version",
                        "0.1.0",
                        "--service-url",
                        "https://service.example",
                        "--auth-token-file",
                        "/private/token",
                    ]
                )
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        fetch.assert_called_once_with(
            "https://service.example",
            Path("/private/token"),
            "workflow_private",
            "0.1.0",
        )

    def test_fetch_workflow_explanation_uses_authenticated_value_free_route(self):
        observed = {}
        expected = _explanation()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed["path"] = self.path
                observed["authorization"] = self.headers.get("Authorization")
                observed["content_length"] = self.headers.get("Content-Length", "0")
                payload = json.dumps(expected).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            result = fetch_workflow_explanation(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                "workflow_private",
                "0.1.0",
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(result, expected)
        self.assertEqual(
            observed["path"],
            "/api/v1/workflow-explanations/workflow_private/0.1.0",
        )
        self.assertEqual(observed["authorization"], f"Bearer {AUTH_TOKEN}")
        self.assertEqual(observed["content_length"], "0")

    def test_fetch_workflow_explanation_rejects_unexpected_contract(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                payload = json.dumps({"schema_version": "wrong"}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                fetch_workflow_explanation(
                    f"http://127.0.0.1:{server.server_port}",
                    token_file,
                    "workflow_private",
                    "0.1.0",
                )
            thread.join(timeout=2)
            server.server_close()


def _explanation():
    return {
        "schema_version": "skill2workflow-workflow-explanation-0.1.0",
        "workflow": {
            "id": "workflow_private",
            "version": "0.1.0",
            "status": "published",
        },
        "entry": "start",
        "summary": {
            "node_count": 2,
            "edge_count": 1,
            "human_gate_count": 0,
            "connector_node_count": 0,
            "side_effecting_node_count": 0,
            "terminal_node_count": 1,
            "retrying_node_count": 0,
            "timed_node_count": 0,
            "input_property_count": 0,
            "required_input_count": 0,
        },
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "transitions": {"success": "end", "failure": None, "fallback": None},
                "connector": None,
                "external_side_effect": False,
                "retry": {"max_attempts": 0, "backoff_ms": 0},
                "timeout_ms": None,
            },
            {
                "id": "end",
                "type": "end",
                "transitions": {"success": None, "failure": None, "fallback": None},
                "connector": None,
                "external_side_effect": False,
                "retry": {"max_attempts": 0, "backoff_ms": 0},
                "timeout_ms": None,
            },
        ],
        "edges": [{"from": "start", "to": "end", "label": "next", "conditioned": False}],
        "input_contract": {
            "present": False,
            "type": "object",
            "required": [],
            "properties": [],
            "additional_properties": True,
        },
        "policies": {
            "default_retry": {"max_attempts": 0, "backoff_ms": 0},
            "default_timeout_ms": None,
            "workflow_timeout_ms": None,
        },
        "safety": {
            "side_effect_free": True,
            "connector_calls": False,
            "credentials_resolved": False,
            "raw_values_included": False,
        },
    }
