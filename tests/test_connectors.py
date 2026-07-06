import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import TestCase

from skill2workflow.connectors import ConnectorExecutionError, _timeout_seconds, execute_connector
from skill2workflow.credentials import StaticCredentialProvider


class ConnectorTests(TestCase):
    def test_http_connector_sends_method_headers_json_body_and_normalizes_response(self):
        server = _ConnectorTestServer()

        try:
            result = execute_connector(
                _http_node(
                    server.url("/success"),
                    method="PUT",
                    headers={"X-Workflow": "approval", "X-Attempt": 3},
                    body={"account_id": "acct_123"},
                    timeout_ms=1200,
                )
            )
        finally:
            server.close()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["connector"], {"id": "http", "kind": "http"})
        self.assertEqual(result["output"]["status_code"], 201)
        self.assertEqual(json.loads(result["output"]["body"]), {"ok": True})

        request = server.requests[0]
        self.assertEqual(request["method"], "PUT")
        self.assertEqual(request["path"], "/success")
        self.assertEqual(request["body"], {"account_id": "acct_123"})
        self.assertEqual(request["headers"]["X-Workflow"], "approval")
        self.assertEqual(request["headers"]["X-Attempt"], "3")
        self.assertEqual(request["headers"]["Content-Type"], "application/json")

    def test_http_connector_maps_context_input_into_body_without_mutating_binding(self):
        server = _ConnectorTestServer()
        node = _http_node(
            server.url("/success"),
            method="POST",
            body={"source": "static"},
            input_mapping=[
                {"from": "/input/customer_id", "to": "/body/customer_id", "required": True},
                {"from": "/input/account/tier", "to": "/body/account/tier", "required": True},
            ],
        )

        try:
            result = execute_connector(
                node,
                context={
                    "input": {
                        "customer_id": "customer_123",
                        "account": {"tier": "gold"},
                    }
                },
            )
        finally:
            server.close()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            server.requests[0]["body"],
            {
                "source": "static",
                "customer_id": "customer_123",
                "account": {"tier": "gold"},
            },
        )
        self.assertEqual(result["input_mapping"], {"status": "applied", "input_keys": ["account", "customer_id"]})
        self.assertEqual(node["connector"]["request"]["body"], {"source": "static"})

    def test_http_connector_missing_required_input_mapping_fails_before_network_call(self):
        server = _ConnectorTestServer()

        try:
            with self.assertRaisesRegex(ConnectorExecutionError, "required input mapping value missing: /input/customer_id"):
                execute_connector(
                    _http_node(
                        server.url("/success"),
                        method="POST",
                        body={"source": "static"},
                        input_mapping=[
                            {"from": "/input/customer_id", "to": "/body/customer_id", "required": True}
                        ],
                    ),
                    context={"input": {}},
                )
        finally:
            server.close()

        self.assertEqual(server.requests, [])

    def test_http_connector_optional_missing_input_mapping_keeps_static_body(self):
        server = _ConnectorTestServer()

        try:
            result = execute_connector(
                _http_node(
                    server.url("/success"),
                    method="POST",
                    body={"source": "static"},
                    input_mapping=[
                        {"from": "/input/customer_id", "to": "/body/customer_id", "required": False}
                    ],
                ),
                context={"input": {}},
            )
        finally:
            server.close()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["input_mapping"], {"status": "skipped", "input_keys": []})
        self.assertEqual(server.requests[0]["body"], {"source": "static"})

    def test_http_connector_returns_failed_result_for_http_error_response(self):
        server = _ConnectorTestServer()

        try:
            result = execute_connector(_http_node(server.url("/fail"), method="POST", body={"ok": False}))
        finally:
            server.close()

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["connector"], {"id": "http", "kind": "http"})
        self.assertEqual(result["output"]["status_code"], 503)
        self.assertEqual(json.loads(result["output"]["body"]), {"error": "unavailable"})
        self.assertEqual(result["error"], "HTTP 503")

    def test_http_connector_rejects_missing_request_and_invalid_url_before_network_call(self):
        cases = [
            ({"id": "http", "kind": "http"}, "requires connector.request"),
            (
                {"id": "http", "kind": "http", "request": {"url": "ftp://example.test/file"}},
                "request.url must be http:// or https://",
            ),
            (
                {"id": "http", "kind": "http", "request": {"method": "GET"}},
                "request.url must be http:// or https://",
            ),
        ]

        for binding, pattern in cases:
            with self.subTest(binding=binding):
                with self.assertRaisesRegex(ConnectorExecutionError, pattern):
                    execute_connector({"id": "call_api", "type": "tool_call", "connector": binding})

    def test_http_connector_rejects_non_json_body_before_network_call(self):
        with self.assertRaisesRegex(ConnectorExecutionError, "request.body must be JSON serializable"):
            execute_connector(
                _http_node(
                    "http://127.0.0.1:1/not-called",
                    method="POST",
                    body={"not_json": object()},
                )
            )

    def test_http_connector_resolves_header_credentials_without_returning_secret(self):
        server = _ConnectorTestServer()

        try:
            result = execute_connector(
                _credential_http_node(server.url("/success")),
                credential_provider=StaticCredentialProvider({"demo_api_token": "secret-token"}),
            )
        finally:
            server.close()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(server.requests[0]["headers"]["Authorization"], "Bearer secret-token")
        self.assertNotIn("secret-token", json.dumps(result))

    def test_http_connector_missing_credential_fails_before_network_call(self):
        with self.assertRaisesRegex(ConnectorExecutionError, "credential handle not found: missing_token"):
            execute_connector(_credential_http_node("http://127.0.0.1:1/not-called", handle="missing_token"))

    def test_http_connector_timeout_becomes_connector_execution_error(self):
        server = _ConnectorTestServer()

        try:
            with self.assertRaisesRegex(ConnectorExecutionError, "timed out|timeout"):
                execute_connector(_http_node(server.url("/slow"), timeout_ms=20))
        finally:
            server.close()

    def test_timeout_seconds_converts_positive_milliseconds_and_defaults_invalid_values(self):
        self.assertEqual(_timeout_seconds(2500), 2.5)
        self.assertEqual(_timeout_seconds(500), 0.5)
        self.assertEqual(_timeout_seconds(0), 5.0)
        self.assertEqual(_timeout_seconds(-100), 5.0)
        self.assertEqual(_timeout_seconds("2000"), 5.0)


def _http_node(url, method="GET", headers=None, body=None, timeout_ms=500, input_mapping=None):
    request = {
        "method": method,
        "url": url,
        "headers": headers or {},
        "timeout_ms": timeout_ms,
    }
    if body is not None:
        request["body"] = body
    if input_mapping is not None:
        request["input_mapping"] = input_mapping
    return {
        "id": "call_api",
        "type": "tool_call",
        "connector": {"id": "http", "kind": "http", "request": request},
    }


def _credential_http_node(url, handle="demo_api_token"):
    node = _http_node(url)
    node["connector"]["credentials"] = [
        {
            "target": "header",
            "name": "Authorization",
            "handle": handle,
            "prefix": "Bearer ",
        }
    ]
    return node


class _ConnectorRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_PUT(self):
        self._handle()

    def _handle(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        body = json.loads(raw_body) if raw_body else None
        self.server.requests.append(
            {
                "method": self.command,
                "path": self.path,
                "headers": dict(self.headers.items()),
                "body": body,
            }
        )

        if self.path == "/slow":
            time.sleep(0.25)
            self._send_json(200, {"ok": True})
            return

        if self.path == "/fail":
            self._send_json(503, {"error": "unavailable"})
            return

        self._send_json(201, {"ok": True})

    def _send_json(self, status_code, payload):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        try:
            self.wfile.write(raw)
        except BrokenPipeError:
            return

    def log_message(self, format, *args):
        return


class _ConnectorTestServer:
    def __init__(self):
        self._server = HTTPServer(("127.0.0.1", 0), _ConnectorRequestHandler)
        self._server.requests = []
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def url(self, path):
        host, port = self._server.server_address
        return f"http://{host}:{port}{path}"

    @property
    def requests(self):
        return self._server.requests

    def close(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)
