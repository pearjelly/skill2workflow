import io
import json
import os
import socket
from datetime import datetime
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from urllib import error as urllib_error

from skill2workflow.connectors import (
    ConnectorExecutionError,
    ConnectorRuntime,
    ExternalConnector,
    validate_connector_manifest,
)
from skill2workflow.credentials import StaticCredentialProvider
from skill2workflow.external_connectors import load_external_connector


ROOT = Path(__file__).resolve().parents[1]


class LarkTaskConnectorTests(TestCase):
    def test_lark_task_manifest_is_explicit_external_connector(self):
        connector = _load_lark_task_connector()

        self.assertEqual(validate_connector_manifest(connector.manifest), [])
        self.assertEqual(connector.manifest["id"], "lark_task")
        self.assertEqual(connector.manifest["kind"], "lark_task")
        self.assertEqual(connector.manifest["execution_contract"]["mode"], "external")
        self.assertEqual(
            connector.manifest["execution_contract"]["entrypoint"],
            "examples/connectors/lark_task_connector.py:execute",
        )
        self.assertEqual([manifest["id"] for manifest in ConnectorRuntime().list_connectors()], ["manual", "http"])
        self.assertEqual(
            [manifest["id"] for manifest in ConnectorRuntime([connector]).list_connectors()],
            ["manual", "http", "lark_task"],
        )
        self.assertEqual(
            connector.manifest["config_schema"]["properties"]["mode"]["enum"],
            ["dry_run", "live"],
        )
        self.assertIn("dry-run-default", connector.manifest["description"])

    def test_lark_task_dry_run_returns_compact_metadata_without_payload_values(self):
        runtime = ConnectorRuntime([_load_lark_task_connector()])

        result = runtime.execute_connector(
            _lark_task_node(),
            credential_provider=StaticCredentialProvider({"lark_bot_access_token": "local-lark-secret"}),
            context={
                "input": {
                    "title": "Renewal risk follow-up",
                    "description": "Customer ACME needs executive review",
                    "assignee_open_id": "ou_123456",
                    "due_at": "2026-07-09T09:00:00Z",
                }
            },
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["connector"], {"id": "lark_task", "kind": "lark_task"})
        self.assertEqual(result["credentials"], {"status": "resolved", "handles": ["lark_bot_access_token"]})
        self.assertEqual(
            result["input_mapping"],
            {"status": "applied", "input_keys": ["assignee_open_id", "description", "due_at", "title"]},
        )
        self.assertEqual(
            result["audit"],
            {
                "operation": "create_task",
                "mode": "dry_run",
                "task_title_present": True,
                "task_description_present": True,
                "assignee_present": True,
                "due_at_present": True,
            },
        )
        self.assertEqual(result["output"]["operation"], "create_task")
        self.assertEqual(result["output"]["mode"], "dry_run")
        self.assertTrue(result["output"]["task_title_present"])

        encoded = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("local-lark-secret", encoded)
        self.assertNotIn("Renewal risk follow-up", encoded)
        self.assertNotIn("Customer ACME needs executive review", encoded)
        self.assertNotIn("ou_123456", encoded)
        self.assertNotIn("2026-07-09T09:00:00Z", encoded)

    def test_lark_task_rejects_live_mode_and_missing_credentials(self):
        runtime = ConnectorRuntime([_load_lark_task_connector()])

        with self.assertRaisesRegex(ConnectorExecutionError, "credential handle not found: lark_bot_access_token"):
            runtime.execute_connector(_lark_task_node(), context={"input": {"title": "Task"}})

    def test_lark_task_live_mode_requires_exact_environment_opt_in(self):
        transport = _FakeTransport()
        runtime = ConnectorRuntime([_load_lark_task_connector(transport)])

        for value in (None, "", "true", "yes", "0"):
            environment = {} if value is None else {"SKILL2WORKFLOW_LARK_TASK_LIVE": value}
            with self.subTest(value=value), patch.dict(os.environ, environment, clear=True):
                result = runtime.execute_connector(
                    _lark_task_node(mode="live"),
                    credential_provider=_FailIfResolvedCredentialProvider(),
                    context=_execution_context(),
                )

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["audit"]["provider_status"], "live_disabled")

        self.assertEqual(transport.calls, [])

    def test_lark_task_live_mode_sends_fixed_redacted_idempotent_request(self):
        transport = _FakeTransport()
        runtime = ConnectorRuntime([_load_lark_task_connector(transport)])

        with patch.dict(os.environ, {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"}, clear=True):
            result = runtime.execute_connector(
                _lark_task_node(mode="live"),
                credential_provider=StaticCredentialProvider(
                    {"lark_bot_access_token": "local-lark-secret"}
                ),
                context=_execution_context(),
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(transport.calls), 1)
        call = transport.calls[0]
        request = call["request"]
        request_body = json.loads(request.data.decode("utf-8"))
        expected_due = str(int(datetime.fromisoformat("2026-07-09T09:00:00+00:00").timestamp() * 1000))

        self.assertEqual(request.method, "POST")
        self.assertEqual(
            request.full_url,
            "https://open.feishu.cn/open-apis/task/v2/tasks?user_id_type=open_id",
        )
        self.assertEqual(request.get_header("Authorization"), "Bearer local-lark-secret")
        self.assertEqual(request.get_header("Content-type"), "application/json; charset=utf-8")
        self.assertEqual(request_body["summary"], "Renewal risk follow-up")
        self.assertEqual(request_body["description"], "Customer ACME needs executive review")
        self.assertEqual(
            request_body["members"],
            [{"id": "ou_123456", "type": "user", "role": "assignee"}],
        )
        self.assertEqual(request_body["due"], {"timestamp": expected_due, "is_all_day": False})
        self.assertEqual(len(request_body["client_token"]), 64)
        self.assertNotIn("source", request_body)
        self.assertEqual(call["timeout"], 10.0)
        self.assertEqual(result["audit"]["provider_status"], "completed")
        self.assertTrue(result["audit"]["idempotency_key_present"])
        self.assertTrue(result["audit"]["lark_task_id_present"])

        encoded = json.dumps(result, ensure_ascii=False)
        for forbidden in (
            "local-lark-secret",
            "Renewal risk follow-up",
            "Customer ACME needs executive review",
            "ou_123456",
            "2026-07-09T09:00:00Z",
            "task-guid-must-not-leak",
            request_body["client_token"],
        ):
            self.assertNotIn(forbidden, encoded)

    def test_lark_task_live_mode_resolves_only_approved_credential_handle(self):
        transport = _FakeTransport()
        runtime = ConnectorRuntime([_load_lark_task_connector(transport)])
        node = _lark_task_node(mode="live")
        node["connector"]["credentials"].append(
            {
                "target": "header",
                "name": "X-Unrelated-Secret",
                "handle": "unrelated_header_secret",
            }
        )
        provider = _RecordingCredentialProvider(
            {
                "lark_bot_access_token": "local-lark-secret",
                "unrelated_header_secret": "must-not-be-materialized",
            }
        )

        with patch.dict(os.environ, {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"}, clear=True):
            result = runtime.execute_connector(
                node,
                credential_provider=provider,
                context=_execution_context(),
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(provider.calls, ["lark_bot_access_token"])
        self.assertEqual(
            result["credentials"],
            {"status": "resolved", "handles": ["lark_bot_access_token"]},
        )
        self.assertNotIn("must-not-be-materialized", json.dumps(result))

    def test_lark_task_live_mode_normalizes_provider_failures_without_leakage(self):
        cases = [
            (401, {"code": 999, "msg": "raw-auth-detail"}, "authorization_failed"),
            (403, {"code": 1470403, "msg": "raw-permission-detail"}, "permission_denied"),
            (429, {"code": 999, "msg": "raw-rate-detail"}, "rate_limited"),
            (400, {"code": 1470400, "msg": "raw-validation-detail"}, "validation_failed"),
            (404, {"code": 1470404, "msg": "raw-resource-detail"}, "resource_not_found"),
            (500, {"code": 1470422, "msg": "raw-idempotency-detail"}, "idempotency_conflict"),
            (500, {"code": 1470500, "msg": "raw-provider-detail"}, "provider_unavailable"),
            (500, b"not-json-provider-body", "provider_unavailable"),
        ]

        for status, payload, expected_status in cases:
            with self.subTest(status=status, expected_status=expected_status):
                transport = _FakeTransport(status=status, payload=payload)
                runtime = ConnectorRuntime([_load_lark_task_connector(transport)])
                with patch.dict(os.environ, {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"}, clear=True):
                    result = runtime.execute_connector(
                        _lark_task_node(mode="live"),
                        credential_provider=StaticCredentialProvider(
                            {"lark_bot_access_token": "local-lark-secret"}
                        ),
                        context=_execution_context(),
                    )

                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["audit"]["provider_status"], expected_status)
                self.assertTrue(result["audit"]["idempotency_key_present"])
                self.assertFalse(result["audit"]["lark_task_id_present"])
                self.assertEqual(
                    result["error"],
                    f"lark_task live request failed: {expected_status}",
                )
                self.assertEqual(result["output"], result["audit"])
                encoded = json.dumps(result, ensure_ascii=False)
                self.assertNotIn("local-lark-secret", encoded)
                self.assertNotIn("raw-", encoded)
                self.assertNotIn("not-json-provider-body", encoded)

    def test_lark_task_live_mode_normalizes_timeout_and_malformed_success(self):
        cases = [
            (_FakeTransport(error=TimeoutError("raw timeout body")), "timeout"),
            (_FakeTransport(error=urllib_error.URLError(socket.timeout("raw socket timeout"))), "timeout"),
            (_FakeTransport(error=urllib_error.URLError("raw network failure")), "provider_unavailable"),
            (
                _FakeTransport(
                    error=urllib_error.HTTPError(
                        "https://open.feishu.cn/open-apis/task/v2/tasks",
                        403,
                        "raw http reason",
                        {},
                        io.BytesIO(b'{"code":1470403,"msg":"raw-http-body"}'),
                    )
                ),
                "permission_denied",
            ),
            (_FakeTransport(payload=b"not-json-success-body"), "malformed_response"),
            (_FakeTransport(payload={"code": 0, "data": {}}), "malformed_response"),
            (_FakeTransport(payload={"code": 0, "data": {"task": {"guid": ""}}}), "malformed_response"),
        ]

        for transport, expected_status in cases:
            with self.subTest(expected_status=expected_status):
                runtime = ConnectorRuntime([_load_lark_task_connector(transport)])
                with patch.dict(os.environ, {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"}, clear=True):
                    result = runtime.execute_connector(
                        _lark_task_node(mode="live"),
                        credential_provider=StaticCredentialProvider(
                            {"lark_bot_access_token": "local-lark-secret"}
                        ),
                        context=_execution_context(),
                    )

                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["audit"]["provider_status"], expected_status)
                self.assertTrue(result["audit"]["idempotency_key_present"])
                self.assertFalse(result["audit"]["lark_task_id_present"])
                self.assertEqual(
                    result["error"],
                    f"lark_task live request failed: {expected_status}",
                )
                encoded = json.dumps(result, ensure_ascii=False)
                self.assertNotIn("local-lark-secret", encoded)
                self.assertNotIn("raw timeout body", encoded)
                self.assertNotIn("raw socket timeout", encoded)
                self.assertNotIn("raw network failure", encoded)
                self.assertNotIn("raw http reason", encoded)
                self.assertNotIn("raw-http-body", encoded)
                self.assertNotIn("not-json-success-body", encoded)

    def test_lark_task_live_mode_normalizes_response_read_failures_and_closes(self):
        timeout_response = _FakeResponse(
            200,
            {},
            error=TimeoutError("raw response read timeout"),
        )
        http_error_body = _ReadErrorBody(
            urllib_error.URLError(socket.timeout("raw http error read timeout"))
        )
        http_error = urllib_error.HTTPError(
            "https://open.feishu.cn/open-apis/task/v2/tasks",
            503,
            "raw http error reason",
            {},
            http_error_body,
        )
        url_error_response = _FakeResponse(
            200,
            {},
            error=urllib_error.URLError("raw response read network failure"),
        )
        cases = [
            (_FakeTransport(response=timeout_response), timeout_response, "timeout"),
            (_FakeTransport(error=http_error), http_error_body, "timeout"),
            (
                _FakeTransport(response=url_error_response),
                url_error_response,
                "provider_unavailable",
            ),
        ]

        for transport, close_target, expected_status in cases:
            with self.subTest(expected_status=expected_status):
                runtime = ConnectorRuntime([_load_lark_task_connector(transport)])
                with patch.dict(os.environ, {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"}, clear=True):
                    result = runtime.execute_connector(
                        _lark_task_node(mode="live"),
                        credential_provider=StaticCredentialProvider(
                            {"lark_bot_access_token": "local-lark-secret"}
                        ),
                        context=_execution_context(),
                    )

                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["audit"]["provider_status"], expected_status)
                self.assertTrue(result["audit"]["idempotency_key_present"])
                self.assertFalse(result["audit"]["lark_task_id_present"])
                self.assertEqual(
                    result["error"],
                    f"lark_task live request failed: {expected_status}",
                )
                self.assertTrue(close_target.closed)
                encoded = json.dumps(result, ensure_ascii=False)
                self.assertNotIn("local-lark-secret", encoded)
                self.assertNotIn("raw response read timeout", encoded)
                self.assertNotIn("raw http error read timeout", encoded)
                self.assertNotIn("raw http error reason", encoded)
                self.assertNotIn("raw response read network failure", encoded)

    def test_lark_task_live_mode_normalizes_ordinary_transport_failures_without_leakage(self):
        token = "dummy-transport-token"

        def transport(request, timeout):
            raise ValueError(f"raw transport failure: {request.get_header('Authorization')}")

        runtime = ConnectorRuntime([_load_lark_task_connector(transport)])
        with patch.dict(os.environ, {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"}, clear=True):
            result = runtime.execute_connector(
                _lark_task_node(mode="live"),
                credential_provider=StaticCredentialProvider({"lark_bot_access_token": token}),
                context=_execution_context(),
            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["audit"]["provider_status"], "provider_unavailable")
        self.assertEqual(result["error"], "lark_task live request failed: provider_unavailable")
        encoded = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(token, encoded)
        self.assertNotIn("raw transport failure", encoded)

    def test_lark_task_live_mode_normalizes_ordinary_response_read_failures_and_closes(self):
        token = "dummy-read-token"
        response = _FakeResponse(200, {}, error=ValueError(f"raw response read failure: {token}"))
        runtime = ConnectorRuntime([_load_lark_task_connector(_FakeTransport(response=response))])

        with patch.dict(os.environ, {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"}, clear=True):
            result = runtime.execute_connector(
                _lark_task_node(mode="live"),
                credential_provider=StaticCredentialProvider({"lark_bot_access_token": token}),
                context=_execution_context(),
            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["audit"]["provider_status"], "provider_unavailable")
        self.assertEqual(result["error"], "lark_task live request failed: provider_unavailable")
        self.assertTrue(response.closed)
        encoded = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(token, encoded)
        self.assertNotIn("raw response read failure", encoded)

    def test_lark_task_live_mode_normalizes_ordinary_status_failures_and_closes(self):
        token = "dummy-status-token"
        response = _StatusErrorResponse(ValueError(f"raw status failure: {token}"))
        runtime = ConnectorRuntime([_load_lark_task_connector(_FakeTransport(response=response))])

        with patch.dict(os.environ, {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"}, clear=True):
            result = runtime.execute_connector(
                _lark_task_node(mode="live"),
                credential_provider=StaticCredentialProvider({"lark_bot_access_token": token}),
                context=_execution_context(),
            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["audit"]["provider_status"], "malformed_response")
        self.assertEqual(result["error"], "lark_task live request failed: malformed_response")
        self.assertTrue(response.closed)
        encoded = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(token, encoded)
        self.assertNotIn("raw status failure", encoded)

    def test_lark_task_live_mode_normalizes_request_construction_failures_without_leakage(self):
        token = "dummy-construction-token"
        connector = _load_lark_task_connector()
        request_module = connector.executor.__globals__["urllib_request"]
        runtime = ConnectorRuntime([connector])

        with patch.object(
            request_module,
            "Request",
            side_effect=ValueError(f"raw request construction failure: {token}"),
        ), patch.dict(os.environ, {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"}, clear=True):
            result = runtime.execute_connector(
                _lark_task_node(mode="live"),
                credential_provider=StaticCredentialProvider({"lark_bot_access_token": token}),
                context=_execution_context(),
            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["audit"]["provider_status"], "credential_failed")
        self.assertEqual(result["error"], "lark_task live request failed: credential_failed")
        encoded = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(token, encoded)
        self.assertNotIn("raw request construction failure", encoded)

    def test_lark_task_live_mode_requires_2xx_for_provider_success(self):
        cases = [
            (401, "authorization_failed"),
            (403, "permission_denied"),
            (429, "rate_limited"),
            (500, "provider_unavailable"),
        ]

        for status, expected_status in cases:
            with self.subTest(status=status, expected_status=expected_status):
                transport = _FakeTransport(
                    status=status,
                    payload={
                        "code": 0,
                        "msg": "raw false success detail",
                        "data": {"task": {"guid": "raw-false-success-guid"}},
                    },
                )
                runtime = ConnectorRuntime([_load_lark_task_connector(transport)])
                with patch.dict(os.environ, {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"}, clear=True):
                    result = runtime.execute_connector(
                        _lark_task_node(mode="live"),
                        credential_provider=StaticCredentialProvider(
                            {"lark_bot_access_token": "local-lark-secret"}
                        ),
                        context=_execution_context(),
                    )

                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["audit"]["provider_status"], expected_status)
                self.assertTrue(result["audit"]["idempotency_key_present"])
                self.assertFalse(result["audit"]["lark_task_id_present"])
                encoded = json.dumps(result, ensure_ascii=False)
                self.assertNotIn("raw false success detail", encoded)
                self.assertNotIn("raw-false-success-guid", encoded)

    def test_lark_task_live_preflight_failures_never_call_transport(self):
        missing_execution = {"input": dict(_execution_context()["input"])}
        invalid_due = json.loads(json.dumps(_execution_context()))
        invalid_due["input"]["due_at"] = "2026-07-09T09:00:00"
        cases = [
            (
                missing_execution,
                StaticCredentialProvider({"lark_bot_access_token": "secret"}),
                "validation_failed",
                False,
            ),
            (
                invalid_due,
                StaticCredentialProvider({"lark_bot_access_token": "secret"}),
                "validation_failed",
                False,
            ),
            (_execution_context(), StaticCredentialProvider({}), "credential_failed", True),
        ]

        for context, provider, expected_status, idempotency_key_present in cases:
            with self.subTest(expected_status=expected_status):
                transport = _FakeTransport()
                runtime = ConnectorRuntime([_load_lark_task_connector(transport)])
                with patch.dict(os.environ, {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"}, clear=True):
                    result = runtime.execute_connector(
                        _lark_task_node(mode="live"),
                        credential_provider=provider,
                        context=context,
                    )

                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["audit"]["provider_status"], expected_status)
                self.assertEqual(
                    result["audit"]["idempotency_key_present"],
                    idempotency_key_present,
                )
                self.assertFalse(result["audit"]["lark_task_id_present"])
                self.assertEqual(
                    result["error"],
                    f"lark_task live request failed: {expected_status}",
                )
                self.assertEqual(transport.calls, [])
                encoded = json.dumps(result, ensure_ascii=False)
                self.assertNotIn("secret", encoded)

    def test_lark_task_client_token_is_stable_per_execution_identity(self):
        transport = _FakeTransport()
        runtime = ConnectorRuntime([_load_lark_task_connector(transport)])

        with patch.dict(os.environ, {"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"}, clear=True):
            runtime.execute_connector(
                _lark_task_node(mode="live"),
                credential_provider=StaticCredentialProvider(
                    {"lark_bot_access_token": "local-lark-secret"}
                ),
                context=_execution_context(),
            )
            runtime.execute_connector(
                _lark_task_node(mode="live"),
                credential_provider=StaticCredentialProvider(
                    {"lark_bot_access_token": "local-lark-secret"}
                ),
                context=_execution_context(),
            )
            runtime.execute_connector(
                _lark_task_node(mode="live"),
                credential_provider=StaticCredentialProvider(
                    {"lark_bot_access_token": "local-lark-secret"}
                ),
                context=_execution_context(run_id="run_other"),
            )
            runtime.execute_connector(
                _lark_task_node(mode="live"),
                credential_provider=StaticCredentialProvider(
                    {"lark_bot_access_token": "local-lark-secret"}
                ),
                context=_execution_context(node_id="create_other_lark_task"),
            )

        tokens = [json.loads(call["request"].data.decode("utf-8"))["client_token"] for call in transport.calls]
        self.assertEqual(tokens[0], tokens[1])
        self.assertNotEqual(tokens[0], tokens[2])
        self.assertNotEqual(tokens[0], tokens[3])

    def test_lark_task_missing_mode_remains_dry_run(self):
        node = _lark_task_node()
        del node["connector"]["mode"]
        runtime = ConnectorRuntime([_load_lark_task_connector()])

        result = runtime.execute_connector(
            node,
            credential_provider=StaticCredentialProvider(
                {"lark_bot_access_token": "local-lark-secret"}
            ),
            context={"input": {"title": "Task"}},
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["audit"]["mode"], "dry_run")


def _load_lark_task_connector(transport=None):
    connector = load_external_connector(ROOT / "examples" / "connectors" / "lark_task_connector.py")
    if transport is None:
        return connector

    def execute_with_transport(binding, credential_provider=None, context=None):
        return connector.executor(
            binding,
            credential_provider=credential_provider,
            context=context,
            transport=transport,
        )

    return ExternalConnector(manifest=connector.manifest, executor=execute_with_transport)


class _FakeResponse:
    def __init__(self, status, payload, error=None):
        self.status = status
        self._payload = payload
        self.error = error
        self.closed = False

    def read(self):
        if self.error is not None:
            raise self.error
        if isinstance(self._payload, bytes):
            return self._payload
        return json.dumps(self._payload).encode("utf-8")

    def close(self):
        self.closed = True


class _ReadErrorBody:
    def __init__(self, error):
        self.error = error
        self.closed = False

    def read(self):
        raise self.error

    def close(self):
        self.closed = True


class _StatusErrorResponse:
    def __init__(self, error):
        self.error = error
        self.closed = False

    @property
    def status(self):
        raise self.error

    def close(self):
        self.closed = True


class _FakeTransport:
    def __init__(self, status=200, payload=None, error=None, response=None):
        self.status = status
        self.payload = payload if payload is not None else {
            "code": 0,
            "msg": "success",
            "data": {"task": {"guid": "task-guid-must-not-leak"}},
        }
        self.error = error
        self.response = response
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append({"request": request, "timeout": timeout})
        if self.error is not None:
            raise self.error
        if self.response is not None:
            return self.response
        return _FakeResponse(self.status, self.payload)


class _FailIfResolvedCredentialProvider:
    def resolve(self, handle):
        raise AssertionError(f"credential resolution must not run: {handle}")


class _RecordingCredentialProvider:
    def __init__(self, values):
        self.values = values
        self.calls = []

    def resolve(self, handle):
        self.calls.append(handle)
        return self.values[handle]


def _execution_context(run_id="run_live", node_id="create_lark_task"):
    return {
        "input": {
            "title": "Renewal risk follow-up",
            "description": "Customer ACME needs executive review",
            "assignee_open_id": "ou_123456",
            "due_at": "2026-07-09T09:00:00Z",
        },
        "_execution": {
            "workflow_id": "workflow_lark_live",
            "workflow_version": "0.1.0",
            "run_id": run_id,
            "node_id": node_id,
        },
    }


def _lark_task_node(operation="create_task", mode="dry_run"):
    return {
        "id": "create_lark_task",
        "type": "tool_call",
        "connector": {
            "id": "lark_task",
            "kind": "lark_task",
            "operation": operation,
            "mode": mode,
            "request": {
                "body": {"source": "unit-test"},
                "input_mapping": [
                    {"from": "/input/title", "to": "/body/title", "required": True},
                    {"from": "/input/description", "to": "/body/description", "required": False},
                    {"from": "/input/assignee_open_id", "to": "/body/assignee_open_id", "required": False},
                    {"from": "/input/due_at", "to": "/body/due_at", "required": False},
                ],
            },
            "credentials": [
                {
                    "target": "header",
                    "name": "Authorization",
                    "handle": "lark_bot_access_token",
                    "prefix": "Bearer ",
                }
            ],
        },
    }
