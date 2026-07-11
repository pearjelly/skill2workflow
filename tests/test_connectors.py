import json
import importlib.util
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import TestCase

from skill2workflow.connectors import (
    CONNECTOR_MANIFEST_VERSION,
    ConnectorRuntime,
    ConnectorExecutionError,
    ExternalConnector,
    _timeout_seconds,
    default_connectors,
    execute_connector,
    validate_connector_manifest,
)
from skill2workflow.credentials import StaticCredentialProvider


class ConnectorTests(TestCase):
    def test_default_connector_manifests_follow_extension_contract(self):
        for manifest in default_connectors():
            with self.subTest(connector=manifest["id"]):
                self.assertEqual(validate_connector_manifest(manifest), [])
                self.assertEqual(manifest["manifest_version"], CONNECTOR_MANIFEST_VERSION)
                self.assertIn("execution_contract", manifest)
                self.assertIn("credential_contract", manifest)
                self.assertIn("audit_contract", manifest)

    def test_validate_connector_manifest_reports_contract_gaps(self):
        errors = validate_connector_manifest(
            {
                "id": "",
                "kind": "http",
                "status": "active",
                "node_types": "tool_call",
                "config_schema": [],
                "execution_contract": {"mode": "dynamic"},
                "credential_contract": {"supports_handles": "yes"},
                "audit_contract": {"value_policy": ""},
            }
        )

        self.assertIn("manifest_version must be skill2workflow-connector-0.1.0", errors)
        self.assertIn("id is required", errors)
        self.assertIn("node_types must be a non-empty list", errors)
        self.assertIn("config_schema must be an object", errors)
        self.assertIn("execution_contract.mode must be built_in or external", errors)
        self.assertIn("credential_contract.supports_handles must be a boolean", errors)
        self.assertIn("audit_contract.value_policy is required", errors)

    def test_connector_runtime_requires_explicit_external_registration(self):
        runtime = ConnectorRuntime()

        self.assertEqual([manifest["id"] for manifest in runtime.list_connectors()], ["manual", "http"])

        fixture = _load_local_echo_fixture()
        self.assertEqual(validate_connector_manifest(fixture.MANIFEST), [])
        external_runtime = ConnectorRuntime([ExternalConnector(fixture.MANIFEST, fixture.execute)])

        self.assertEqual(
            [manifest["id"] for manifest in external_runtime.list_connectors()],
            ["manual", "http", "local_echo"],
        )
        self.assertEqual([manifest["id"] for manifest in default_connectors()], ["manual", "http"])

    def test_explicit_external_connector_executes_normalized_result_without_secret(self):
        fixture = _load_local_echo_fixture()
        runtime = ConnectorRuntime([ExternalConnector(fixture.MANIFEST, fixture.execute)])

        result = runtime.execute_connector(
            _local_echo_node(handle="demo_api_token"),
            credential_provider=StaticCredentialProvider({"demo_api_token": "secret-token"}),
            context={"input": {"customer_id": "customer_123"}},
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["connector"], {"id": "local_echo", "kind": "local_echo"})
        self.assertEqual(result["output"]["body_keys"], ["customer_id", "source"])
        self.assertEqual(result["credentials"], {"status": "resolved", "handles": ["demo_api_token"]})
        self.assertEqual(result["input_mapping"], {"status": "applied", "input_keys": ["customer_id"]})
        self.assertNotIn("secret-token", json.dumps(result))
        self.assertNotIn("customer_123", json.dumps(result))

    def test_external_connector_missing_credential_fails_before_completion(self):
        fixture = _load_local_echo_fixture()
        runtime = ConnectorRuntime([ExternalConnector(fixture.MANIFEST, fixture.execute)])

        with self.assertRaisesRegex(ConnectorExecutionError, "credential handle not found: missing_token"):
            runtime.execute_connector(
                _local_echo_node(handle="missing_token"),
                context={"input": {"customer_id": "customer_123"}},
            )

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


def _local_echo_node(handle="demo_api_token"):
    return {
        "id": "call_echo",
        "type": "tool_call",
        "connector": {
            "id": "local_echo",
            "kind": "local_echo",
            "request": {
                "body": {"source": "connector-test"},
                "input_mapping": [
                    {"from": "/input/customer_id", "to": "/body/customer_id", "required": True},
                ],
            },
            "credentials": [
                {
                    "target": "header",
                    "name": "Authorization",
                    "handle": handle,
                    "prefix": "Bearer ",
                }
            ],
        },
    }


def _load_local_echo_fixture():
    path = Path(__file__).resolve().parents[1] / "examples" / "connectors" / "local_echo_connector.py"
    spec = importlib.util.spec_from_file_location("local_echo_connector", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
