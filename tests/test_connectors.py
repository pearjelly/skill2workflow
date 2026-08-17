import json
import importlib.util
import os
import threading
import time
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.connectors import (
    CONNECTOR_MANIFEST_VERSION,
    MAX_HTTP_PAYLOAD_BYTES,
    MAX_EXTERNAL_CONNECTOR_RESULT_BYTES,
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

    def test_external_connector_rejects_oversized_normalized_result(self):
        fixture = _load_local_echo_fixture()

        def execute(_binding, credential_provider=None, context=None):
            return {
                "status": "completed",
                "connector": {"id": "local_echo", "kind": "local_echo"},
                "output": {"payload": "x" * MAX_EXTERNAL_CONNECTOR_RESULT_BYTES},
            }

        runtime = ConnectorRuntime([ExternalConnector(fixture.MANIFEST, execute)])

        with self.assertRaisesRegex(
            ConnectorExecutionError,
            f"external connector result exceeds {MAX_EXTERNAL_CONNECTOR_RESULT_BYTES} bytes",
        ):
            runtime.execute_connector(_local_echo_node())

    def test_external_connector_rejects_non_json_normalized_result(self):
        fixture = _load_local_echo_fixture()

        def execute(_binding, credential_provider=None, context=None):
            return {
                "status": "completed",
                "connector": {"id": "local_echo", "kind": "local_echo"},
                "output": {"not_json": object()},
            }

        runtime = ConnectorRuntime([ExternalConnector(fixture.MANIFEST, execute)])

        with self.assertRaisesRegex(
            ConnectorExecutionError,
            "external connector result must be JSON serializable",
        ):
            runtime.execute_connector(_local_echo_node())

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

    def test_http_connector_metadata_response_discards_body_and_headers(self):
        server = _ConnectorTestServer()

        try:
            result = execute_connector(
                _http_node(server.url("/success"), response_mode="metadata")
            )
        finally:
            server.close()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            result["output"],
            {
                "status_code": 201,
                "header_count": 4,
                "body_bytes": len(json.dumps({"ok": True}).encode("utf-8")),
                "body_discarded": True,
            },
        )
        self.assertNotIn("ok", json.dumps(result))

    def test_http_connector_metadata_response_preserves_error_status_without_body(self):
        server = _ConnectorTestServer()

        try:
            result = execute_connector(
                _http_node(server.url("/fail"), response_mode="metadata")
            )
        finally:
            server.close()

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "HTTP 503")
        self.assertEqual(result["output"]["status_code"], 503)
        self.assertTrue(result["output"]["body_discarded"])
        self.assertNotIn("unavailable", json.dumps(result))

    def test_http_connector_rejects_unknown_response_mode_before_network_call(self):
        with patch("skill2workflow.connectors._open_http_request") as urlopen:
            with self.assertRaisesRegex(
                ConnectorExecutionError,
                "request.response_mode must be full or metadata",
            ):
                execute_connector(
                    _http_node(
                        "http://127.0.0.1:1/not-called",
                        response_mode="raw",
                    )
                )
        urlopen.assert_not_called()

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

    def test_http_connector_maps_scalar_context_input_into_query_without_mutating_binding(self):
        server = _ConnectorTestServer()
        node = _http_node(
            server.url("/success?existing=1"),
            method="GET",
            input_mapping=[
                {"from": "/input/existing", "to": "/query/existing", "required": True},
                {"from": "/input/customer_id", "to": "/query/customer_id", "required": True},
                {"from": "/input/page", "to": "/query/page", "required": True},
                {"from": "/input/active", "to": "/query/active", "required": True},
            ],
        )

        try:
            result = execute_connector(
                node,
                context={
                    "input": {
                        "existing": 2,
                        "customer_id": "customer 123",
                        "page": 2,
                        "active": True,
                    }
                },
            )
        finally:
            server.close()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            server.requests[0]["path"],
            "/success?existing=2&customer_id=customer+123&page=2&active=true",
        )
        self.assertEqual(
            result["input_mapping"],
            {"status": "applied", "input_keys": ["active", "customer_id", "existing", "page"]},
        )
        self.assertEqual(node["connector"]["request"]["url"], server.url("/success?existing=1"))

    def test_http_connector_rejects_non_scalar_query_mapping_value_before_network_call(self):
        server = _ConnectorTestServer()
        try:
            with self.assertRaisesRegex(
                ConnectorExecutionError,
                "query input mapping value must be a string, number, or boolean",
            ):
                execute_connector(
                    _http_node(
                        server.url("/success"),
                        input_mapping=[
                            {"from": "/input/filter", "to": "/query/filter", "required": True}
                        ],
                    ),
                    context={"input": {"filter": {"status": "open"}}},
                )
        finally:
            server.close()

        self.assertEqual(server.requests, [])

    def test_http_connector_rejects_nested_query_mapping_target(self):
        with self.assertRaisesRegex(
            ConnectorExecutionError,
            "to must be /query/<name>",
        ):
            execute_connector(
                _http_node(
                    "http://127.0.0.1:1/not-called",
                    input_mapping=[
                        {"from": "/input/customer_id", "to": "/query/filter/customer_id", "required": True}
                    ],
                ),
                context={"input": {"customer_id": "customer_123"}},
            )

    def test_http_connector_rejects_malformed_query_mapping_url(self):
        with self.assertRaisesRegex(
            ConnectorExecutionError,
            "http connector request.url is invalid",
        ):
            execute_connector(
                _http_node(
                    "http://[invalid",
                    input_mapping=[
                        {"from": "/input/page", "to": "/query/page", "required": True}
                    ],
                ),
                context={"input": {"page": 2}},
            )

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

    def test_http_connector_closes_http_error_response(self):
        response_body = BytesIO(b'{"error":"unavailable"}')
        error = urllib.error.HTTPError(
            "https://example.test/fail",
            503,
            "Service Unavailable",
            {"Content-Type": "application/json"},
            response_body,
        )

        with patch(
            "skill2workflow.connectors._open_http_request",
            side_effect=error,
        ):
            result = execute_connector(
                _http_node("https://example.test/fail", method="POST")
            )

        self.assertEqual(result["status"], "failed")
        self.assertTrue(response_body.closed)

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

    def test_http_connector_rejects_oversized_request_body_before_network_call(self):
        oversized_body = {"payload": "x" * MAX_HTTP_PAYLOAD_BYTES}

        with self.assertRaisesRegex(
            ConnectorExecutionError,
            f"http connector request body exceeds {MAX_HTTP_PAYLOAD_BYTES} bytes",
        ):
            execute_connector(
                _http_node(
                    "http://127.0.0.1:1/not-called",
                    method="POST",
                    body=oversized_body,
                )
            )

    def test_http_connector_rejects_oversized_success_response_before_persisting_it(self):
        response = _FakeHTTPResponse(200, b"x" * (MAX_HTTP_PAYLOAD_BYTES + 1))

        with patch("skill2workflow.connectors._open_http_request", return_value=response):
            with self.assertRaisesRegex(
                ConnectorExecutionError,
                f"http connector response body exceeds {MAX_HTTP_PAYLOAD_BYTES} bytes",
            ):
                execute_connector(_http_node("https://example.test/large"))

        self.assertTrue(response.closed)

    def test_http_connector_rejects_oversized_error_response_before_persisting_it(self):
        response_body = BytesIO(b"x" * (MAX_HTTP_PAYLOAD_BYTES + 1))
        error = urllib.error.HTTPError(
            "https://example.test/large-error",
            503,
            "Service Unavailable",
            {"Content-Type": "text/plain"},
            response_body,
        )

        with patch(
            "skill2workflow.connectors._open_http_request",
            side_effect=error,
        ):
            with self.assertRaisesRegex(
                ConnectorExecutionError,
                f"http connector response body exceeds {MAX_HTTP_PAYLOAD_BYTES} bytes",
            ):
                execute_connector(_http_node("https://example.test/large-error"))

        self.assertTrue(response_body.closed)

    def test_http_connector_normalizes_invalid_utf8_response(self):
        response = _FakeHTTPResponse(200, b"\xff\xfe")

        with patch("skill2workflow.connectors._open_http_request", return_value=response):
            with self.assertRaisesRegex(
                ConnectorExecutionError,
                "http connector response body must be valid UTF-8",
            ):
                execute_connector(_http_node("https://example.test/invalid"))

        self.assertTrue(response.closed)

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

    def test_http_connector_rejects_redirect_before_replaying_credentials(self):
        target = _ConnectorTestServer()
        redirect = _RedirectConnectorTestServer(target.url("/success"))

        try:
            with self.assertRaisesRegex(
                ConnectorExecutionError,
                "http connector redirects are disabled",
            ):
                execute_connector(
                    _credential_http_node(redirect.url()),
                    credential_provider=StaticCredentialProvider({"demo_api_token": "secret-token"}),
                )
        finally:
            redirect.close()
            target.close()

        self.assertEqual(target.requests, [])

    def test_http_connector_ignores_ambient_proxy_for_credentialed_request(self):
        target = _ConnectorTestServer()
        proxy = _ProxyConnectorTestServer()
        proxy_url = proxy.url()
        proxy_environment = {
            "http_proxy": proxy_url,
            "https_proxy": proxy_url,
            "HTTP_PROXY": proxy_url,
            "HTTPS_PROXY": proxy_url,
            "all_proxy": proxy_url,
            "ALL_PROXY": proxy_url,
            "no_proxy": "",
            "NO_PROXY": "",
        }

        try:
            with patch.dict(os.environ, proxy_environment):
                result = execute_connector(
                    _credential_http_node(target.url("/success")),
                    credential_provider=StaticCredentialProvider({"demo_api_token": "secret-token"}),
                )
        finally:
            proxy.close()
            target.close()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(target.requests), 1)
        self.assertEqual(target.requests[0]["headers"]["Authorization"], "Bearer secret-token")
        self.assertEqual(proxy.requests, [])

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


def _http_node(
    url,
    method="GET",
    headers=None,
    body=None,
    timeout_ms=500,
    input_mapping=None,
    response_mode=None,
):
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
    if response_mode is not None:
        request["response_mode"] = response_mode
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
        except (BrokenPipeError, ConnectionResetError):
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


class _RedirectConnectorRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", self.server.target_url)
        self.end_headers()

    def log_message(self, format, *args):
        return


class _RedirectConnectorTestServer:
    def __init__(self, target_url):
        self._server = HTTPServer(("127.0.0.1", 0), _RedirectConnectorRequestHandler)
        self._server.target_url = target_url
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def url(self):
        host, port = self._server.server_address
        return f"http://{host}:{port}/redirect"

    def close(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


class _ProxyConnectorRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requests.append({"method": self.command, "path": self.path})
        raw = b"ambient proxy should not receive connector requests"
        self.send_response(502)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args):
        return


class _ProxyConnectorTestServer:
    def __init__(self):
        self._server = HTTPServer(("127.0.0.1", 0), _ProxyConnectorRequestHandler)
        self._server.requests = []
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def url(self):
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    @property
    def requests(self):
        return self._server.requests

    def close(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


class _FakeHTTPResponse:
    def __init__(self, status, payload):
        self.status = status
        self.headers = {"Content-Type": "application/octet-stream"}
        self._payload = payload
        self._offset = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def read(self, amount=-1):
        if amount is None or amount < 0:
            amount = len(self._payload) - self._offset
        start = self._offset
        self._offset += amount
        return self._payload[start:self._offset]

    def close(self):
        self.closed = True
