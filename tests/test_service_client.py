import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.service_client import (
    MAX_SERVICE_ACTION_RESPONSE_BYTES,
    ServiceActionError,
    post_run_cancel,
    post_run_resume,
    fetch_run_detail,
)


AUTH_TOKEN = "service-client-test-token-0123456789abcdef"
RUN_ID = "run_service_client_001"


class ServiceClientTests(TestCase):
    def test_run_detail_uses_authenticated_get_and_validates_redacted_contract(self):
        observed = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                        "content_length": self.headers.get("Content-Length"),
                    }
                )
                _send_json(
                    self,
                    200,
                    {
                        "schema_version": "skill2workflow-run-detail-0.1.0",
                        "run": {
                            "run_id": RUN_ID,
                            "workflow_id": "workflow",
                            "workflow_version": "0.1.0",
                            "status": "waiting",
                            "current_node": "review",
                            "event_count": 1,
                            "node_result_count": 0,
                            "node_overlays": {},
                            "created_at": "",
                            "updated_at": "",
                        },
                        "events": [
                            {
                                "sequence": 1,
                                "type": "human_gate_waiting",
                                "has_error": False,
                            }
                        ],
                        "window": {
                            "max_events": 50,
                            "total": 1,
                            "returned": 1,
                            "truncated": False,
                        },
                    },
                )

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            detail = fetch_run_detail(
                f"http://127.0.0.1:{server.server_port}",
                token_file,
                RUN_ID,
            )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(detail["run"]["run_id"], RUN_ID)
        self.assertEqual(
            observed,
            [
                {
                    "path": f"/runs/{RUN_ID}",
                    "authorization": f"Bearer {AUTH_TOKEN}",
                    "content_length": None,
                }
            ],
        )
        self.assertFalse(thread.is_alive())

    def test_run_detail_rejects_extra_fields_in_provider_response(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                _send_json(
                    self,
                    200,
                    {
                        "schema_version": "skill2workflow-run-detail-0.1.0",
                        "run": {"run_id": RUN_ID},
                        "events": [],
                        "window": {},
                        "private": "must-not-be-accepted",
                    },
                )

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
                fetch_run_detail(
                    f"http://127.0.0.1:{server.server_port}",
                    token_file,
                    RUN_ID,
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertFalse(thread.is_alive())

    def test_resume_and_cancel_send_bearer_token_and_exact_json_contracts(self):
        observed = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                observed.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                        "body": json.loads(self.rfile.read(length).decode("utf-8")),
                    }
                )
                if self.path.endswith("/resume"):
                    payload = {"run_id": RUN_ID, "status": "completed", "approved": True}
                else:
                    payload = {"run_id": RUN_ID, "status": "cancelled"}
                _send_json(self, 200, payload)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"

            resumed = post_run_resume(base_url, token_file, RUN_ID, approved=True)
            cancelled = post_run_cancel(base_url, token_file, RUN_ID)

            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(resumed["approved"], True)
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(
            observed,
            [
                {
                    "path": f"/runs/{RUN_ID}/resume",
                    "authorization": f"Bearer {AUTH_TOKEN}",
                    "body": {"approved": True},
                },
                {
                    "path": f"/runs/{RUN_ID}/cancel",
                    "authorization": f"Bearer {AUTH_TOKEN}",
                    "body": {},
                },
            ],
        )
        self.assertFalse(thread.is_alive())

    def test_invalid_origin_and_run_id_fail_before_network_access(self):
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "service URL"):
                post_run_cancel("http://example.com", token_file, RUN_ID)
            with self.assertRaisesRegex(ValueError, "safe run identifier"):
                post_run_cancel("http://127.0.0.1:1", token_file, "run_bad/segment")

    def test_http_error_is_fixed_and_does_not_echo_provider_body(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = b'{"error":"private provider response"}'
                self.send_response(409)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError) as caught:
                post_run_resume(
                    f"http://127.0.0.1:{server.server_port}",
                    token_file,
                    RUN_ID,
                    approved=True,
                )
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(str(caught.exception), "run is not waiting")
        self.assertEqual(caught.exception.status_code, 409)
        self.assertNotIn("private provider response", str(caught.exception))

    def test_redirect_and_oversized_response_are_rejected(self):
        contacted = threading.Event()

        class TargetHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                contacted.set()
                self.send_response(200)
                self.end_headers()

            def log_message(self, *_args):
                return

        target = HTTPServer(("127.0.0.1", 0), TargetHandler)

        class RedirectHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{target.server_port}/target")
                self.end_headers()

            def log_message(self, *_args):
                return

        redirect = HTTPServer(("127.0.0.1", 0), RedirectHandler)
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            redirect_thread = threading.Thread(target=redirect.handle_request, daemon=True)
            redirect_thread.start()
            with self.assertRaises(ServiceActionError):
                post_run_cancel(
                    f"http://127.0.0.1:{redirect.server_port}",
                    token_file,
                    RUN_ID,
                )
            redirect_thread.join(timeout=2)

        redirect.server_close()
        target.server_close()
        self.assertFalse(contacted.is_set())

        class OversizedHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = b"x" * (MAX_SERVICE_ACTION_RESPONSE_BYTES + 1)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(AUTH_TOKEN, encoding="utf-8")
            token_file.chmod(0o600)
            server = HTTPServer(("127.0.0.1", 0), OversizedHandler)
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            with self.assertRaises(ServiceActionError):
                post_run_cancel(
                    f"http://127.0.0.1:{server.server_port}",
                    token_file,
                    RUN_ID,
                )
            thread.join(timeout=2)
            server.server_close()
        self.assertFalse(thread.is_alive())


def _send_json(handler, status_code, payload):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
