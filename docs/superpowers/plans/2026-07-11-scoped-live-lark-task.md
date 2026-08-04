# Scoped Live Lark Task Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Loop 39 by adding one explicitly enabled, idempotent, redacted Feishu Task v2 `create_task` path and validating it once with a Vault-injected bot token.

**Architecture:** Keep live behavior inside the explicitly loaded `lark_task` external connector. `LocalExecutor` supplies ephemeral execution identity, the connector uses a fixed Feishu endpoint plus native `client_token`, and all CI coverage uses an injected standard-library-compatible transport; one separate guarded command performs the approved real write after offline verification.

**Tech Stack:** Python 3.9 standard library, `unittest`, `urllib.request`, existing external connector and credential-provider contracts, Avibe Vault.

## Global Constraints

- Workflow DSL remains the execution source of truth and stays at schema version `0.1.0`.
- Live scope is only `lark_task` / `create_task` / Feishu domestic `https://open.feishu.cn/open-apis/task/v2/tasks?user_id_type=open_id`.
- Dry-run remains the default when `mode` is missing or equals `dry_run`.
- Live network activity requires both `mode: live` and `SKILL2WORKFLOW_LARK_TASK_LIVE=1`.
- Only the exact environment value `1` enables live behavior.
- Live credentials use handle `lark_bot_access_token`; resolved values never enter workflow artifacts, state, events, audit, snapshots, validation artifacts, errors, or terminal output.
- Provider idempotency uses a SHA-256 hex `client_token` derived from canonical JSON for `[workflow_id, workflow_version, run_id, node_id]`.
- The connector may not accept a configurable API base, path, method, query, or arbitrary headers.
- Raw task values may remain only in the pre-existing durable `run.context.input`; the connector must not copy them into node results, events, audit, snapshots, output, or summaries.
- Runtime-owned `_execution` metadata is ephemeral and overwrites any user-provided value before connector invocation.
- No CI command may use live network access.
- The real validation write must use the already approved task content and current-user assignment from conversation context, without committing those raw values or user id.
- Keep Python runtime dependencies limited to the standard library.

---

## File Map

- `src/skill2workflow/executor.py`: create ephemeral connector context containing runtime-owned execution identity.
- `examples/connectors/lark_task_connector.py`: preserve dry-run and implement the fixed live create-task request, native idempotency, transport, failure mapping, and redaction.
- `src/skill2workflow/lark_task_live_validation.py`: guarded, compact, no-state live validation orchestration.
- `scripts/lark_task_live_validation.py`: source-checkout command wrapper.
- `tests/test_executor.py`: prove `_execution` delivery and non-persistence.
- `tests/test_lark_task_connector.py`: live activation, request shape, idempotency, failure matrix, and leakage tests.
- `tests/test_lark_task_live_validation.py`: validation command guard and compact-output tests.
- `docs/connectors.md`: public live connector contract.
- `docs/lark-live-connector-readiness.md`: native idempotency decision and durable-input clarification.
- `docs/lark-live-connector-validation.md`: redacted evidence from the approved real write.
- `tests/test_live_connector_readiness.py`: documentation contract for the implemented live boundary.
- `ROADMAP.md`, `README.md`, `tests/test_production_roadmap.py`, `tests/test_product_connector_pilot_roadmap.py`, `tests/test_first_product_connector_candidate_docs.py`: Loop 39 completion and Loop 40 transition.
- `docs/superpowers/plans/2026-07-11-scoped-live-lark-task.md`: execution checklist and verification record.

### Task 1: Ephemeral Connector Execution Identity

**Files:**
- Modify: `tests/test_executor.py`
- Modify: `src/skill2workflow/executor.py`

**Interfaces:**
- Consumes: `LocalExecutor._execute_connector_node(...)` and `ConnectorRuntime.execute_connector(node, credential_provider=None, context=None)`
- Produces: `_connector_context(state: RunState, node_id: str) -> Dict[str, object]`, consumed by every connector call and by Task 2 idempotency derivation

- [x] **Step 1: Write the failing executor test**

Add this test to `ExecutorTests`:

```python
    def test_connector_receives_ephemeral_execution_identity_without_persisting_it(self):
        runtime = _CapturingConnectorRuntime()
        original_context = {
            "input": {"title": "Durable title"},
            "_execution": {"workflow_id": "forged"},
        }

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp), connector_runtime=runtime)
            state = executor.run(_http_connector_workflow("https://unused.invalid"), context=original_context)
            persisted = executor.get_run(state["run_id"])

        self.assertEqual(len(runtime.contexts), 1)
        self.assertEqual(
            runtime.contexts[0]["_execution"],
            {
                "workflow_id": "workflow_connector",
                "workflow_version": "0.1.0",
                "run_id": state["run_id"],
                "node_id": "call_api",
            },
        )
        self.assertEqual(runtime.contexts[0]["input"], {"title": "Durable title"})
        self.assertEqual(state["context"], original_context)
        self.assertEqual(persisted["context"], original_context)
```

Add this helper after the test class:

```python
class _CapturingConnectorRuntime:
    def __init__(self):
        self.contexts = []

    def execute_connector(self, node, credential_provider=None, context=None):
        self.contexts.append(context)
        return {
            "status": "completed",
            "connector": {"id": "http", "kind": "http"},
            "output": {},
        }
```

- [x] **Step 2: Run the focused test and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_executor.ExecutorTests.test_connector_receives_ephemeral_execution_identity_without_persisting_it -v
```

Expected: FAIL because the connector receives only the durable context and the forged `_execution` object is not replaced.

- [x] **Step 3: Implement the runtime-owned connector context**

Replace the connector call's current `context=state.get("context", {})` argument with:

```python
                    context=_connector_context(state, current_id),
```

Add this helper before `_now()`:

```python
def _connector_context(state: RunState, node_id: str) -> Dict[str, object]:
    durable = state.get("context", {})
    context = copy.deepcopy(durable) if isinstance(durable, dict) else {}
    context["_execution"] = {
        "workflow_id": str(state.get("workflow_id", "")),
        "workflow_version": str(state.get("workflow_version", "")),
        "run_id": str(state.get("run_id", "")),
        "node_id": str(node_id),
    }
    return context
```

- [x] **Step 4: Run focused and executor tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_executor -v
```

Expected: all executor tests PASS.

- [x] **Step 5: Commit Task 1**

Run:

```bash
git add src/skill2workflow/executor.py tests/test_executor.py
git commit -m "feat: add connector execution identity"
```

Expected: one commit containing only the executor context change and its test.

### Task 2: Live Activation, Request Transformation, And Idempotency

**Files:**
- Modify: `examples/connectors/lark_task_connector.py`
- Modify: `tests/test_lark_task_connector.py`

**Interfaces:**
- Consumes: Task 1 `_execution` context and existing `StaticCredentialProvider`
- Produces: `execute(binding, credential_provider=None, context=None, transport=None)`, `_provider_request_body(...)`, `_client_token(...)`, and the injectable transport contract used by Tasks 3 and 4

- [x] **Step 1: Add deterministic test transport helpers**

Retain the existing `json` import and add:

```python
import os
from datetime import datetime
from unittest.mock import patch

from skill2workflow.connectors import ExternalConnector
```

Replace `_load_lark_task_connector()` with:

```python
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
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    def read(self):
        if isinstance(self._payload, bytes):
            return self._payload
        return json.dumps(self._payload).encode("utf-8")

    def close(self):
        return None


class _FakeTransport:
    def __init__(self, status=200, payload=None, error=None):
        self.status = status
        self.payload = payload if payload is not None else {
            "code": 0,
            "msg": "success",
            "data": {"task": {"guid": "task-guid-must-not-leak"}},
        }
        self.error = error
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append({"request": request, "timeout": timeout})
        if self.error is not None:
            raise self.error
        return _FakeResponse(self.status, self.payload)


class _FailIfResolvedCredentialProvider:
    def resolve(self, handle):
        raise AssertionError(f"credential resolution must not run: {handle}")


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
```

- [x] **Step 2: Write live-disabled and successful-request tests**

Add these tests to `LarkTaskConnectorTests`:

```python
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
```

Extend `test_lark_task_manifest_is_explicit_external_connector` with:

```python
        self.assertEqual(
            connector.manifest["config_schema"]["properties"]["mode"]["enum"],
            ["dry_run", "live"],
        )
        self.assertIn("dry-run-default", connector.manifest["description"])
```

- [x] **Step 3: Run live tests and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_task_connector -v
```

Expected: FAIL because `execute` rejects live mode and has no transport parameter.

- [x] **Step 4: Implement live activation and successful request construction**

Update the module docstring to describe a dry-run-default connector with scoped live support. Add these imports and constants:

```python
import hashlib
import json
import os
from datetime import datetime
from urllib import request as urllib_request
from typing import Dict, List, Tuple


LIVE_ENVIRONMENT_SWITCH = "SKILL2WORKFLOW_LARK_TASK_LIVE"
LIVE_URL = "https://open.feishu.cn/open-apis/task/v2/tasks?user_id_type=open_id"
LIVE_TIMEOUT_SECONDS = 10.0
REQUIRED_CREDENTIAL_HANDLE = "lark_bot_access_token"
```

Change the entrypoint signature to:

```python
def execute(binding: Dict[str, object], credential_provider=None, context=None, transport=None) -> Dict[str, object]:
```

Update only these manifest values; keep the connector id, kind, external entrypoint, credential policy, and audit event list unchanged:

```python
"description": "Explicit dry-run-default connector with opt-in scoped Feishu task creation.",
"mode": {"type": "string", "enum": ["dry_run", "live"]},
```

Preserve the complete current dry-run branch. For live mode, use these helpers and call order:

```python
def _live_enabled() -> bool:
    return os.environ.get(LIVE_ENVIRONMENT_SWITCH) == "1"


def _execution_identity(context: object) -> List[str]:
    context_root = context if isinstance(context, dict) else {}
    execution = context_root.get("_execution", {})
    if not isinstance(execution, dict):
        return []
    values = [
        str(execution.get("workflow_id") or ""),
        str(execution.get("workflow_version") or ""),
        str(execution.get("run_id") or ""),
        str(execution.get("node_id") or ""),
    ]
    return values if all(values) else []


def _client_token(context: object) -> str:
    identity = _execution_identity(context)
    if not identity:
        raise ConnectorExecutionError("lark_task live execution identity is required")
    canonical = json.dumps(identity, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _provider_request_body(body: Dict[str, object], context: object) -> Dict[str, object]:
    title = body.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ConnectorExecutionError("lark_task connector task title is required")

    payload: Dict[str, object] = {
        "summary": title,
        "client_token": _client_token(context),
    }
    description = body.get("description")
    if description is not None:
        if not isinstance(description, str):
            raise ConnectorExecutionError("lark_task connector description must be a string")
        payload["description"] = description

    assignee = body.get("assignee_open_id")
    if assignee is not None:
        if not isinstance(assignee, str) or not assignee.strip():
            raise ConnectorExecutionError("lark_task connector assignee_open_id must be a non-empty string")
        payload["members"] = [{"id": assignee, "type": "user", "role": "assignee"}]

    due_at = body.get("due_at")
    if due_at is not None:
        payload["due"] = {"timestamp": _due_timestamp(due_at), "is_all_day": False}
    return payload


def _due_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConnectorExecutionError("lark_task connector due_at must be an RFC 3339 string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        raise ConnectorExecutionError("lark_task connector due_at must be an RFC 3339 string")
    if parsed.tzinfo is None:
        raise ConnectorExecutionError("lark_task connector due_at must include a timezone")
    return str(int(parsed.timestamp() * 1000))


def _request(payload: Dict[str, object], token: str) -> urllib_request.Request:
    return urllib_request.Request(
        LIVE_URL,
        data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )


def _default_transport(request: urllib_request.Request, timeout: float):
    return urllib_request.urlopen(request, timeout=timeout)
```

Change credential resolution to return both compact metadata and an internal handle-to-value map:

```python
def _resolve_credentials(credentials: object, credential_provider) -> Tuple[Dict[str, object], Dict[str, str]]:
    if credentials in (None, []):
        return {"status": "skipped", "handles": []}, {}
    if not isinstance(credentials, list):
        raise ConnectorExecutionError("connector.credentials must be a list")

    handles: List[str] = []
    values: Dict[str, str] = {}
    for index, credential in enumerate(credentials):
        if not isinstance(credential, dict):
            raise ConnectorExecutionError(f"connector.credentials[{index}] must be an object")
        target = str(credential.get("target") or "")
        if target != "header":
            raise ConnectorExecutionError(f"connector.credentials[{index}].target must be header")
        handle = str(credential.get("handle") or "")
        if not handle:
            raise ConnectorExecutionError(f"connector.credentials[{index}].handle is required")
        if credential_provider is None:
            raise ConnectorExecutionError(f"credential handle not found: {handle}")
        try:
            values[handle] = credential_provider.resolve(handle)
        except CredentialResolutionError as error:
            raise ConnectorExecutionError(str(error))
        handles.append(handle)

    return {"status": "resolved", "handles": sorted(handles)}, values
```

After live resolution, enforce the approved handle exactly:

```python
if REQUIRED_CREDENTIAL_HANDLE not in credential_values:
    raise ConnectorExecutionError(
        f"credential handle not found: {REQUIRED_CREDENTIAL_HANDLE}"
    )
```

Dry-run uses only the summary. Live mode requires `REQUIRED_CREDENTIAL_HANDLE` in the internal values and passes it to `_request`.

Add this Task 2 success parser and compact result builder; Task 3 will extend the parser for failures without changing the result shape:

```python
def _successful_task_present(response) -> bool:
    try:
        status = int(getattr(response, "status", 0))
        raw = response.read()
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            close()
    if status < 200 or status >= 300:
        raise ConnectorExecutionError("lark_task live provider request failed")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ConnectorExecutionError("lark_task live provider response is invalid")
    if not isinstance(payload, dict) or payload.get("code") != 0:
        raise ConnectorExecutionError("lark_task live provider response is invalid")
    data = payload.get("data", {})
    task = data.get("task", {}) if isinstance(data, dict) else {}
    guid = task.get("guid") if isinstance(task, dict) else ""
    if not isinstance(guid, str) or not guid:
        raise ConnectorExecutionError("lark_task live provider response is invalid")
    return True


def _live_result(
    status: str,
    audit: Dict[str, object],
    provider_status: str,
    mapping_summary: Dict[str, object],
    credential_summary: Dict[str, object] = None,
    idempotency_key_present: bool = False,
    task_id_present: bool = False,
) -> Dict[str, object]:
    compact = dict(audit)
    compact.update(
        {
            "credential_status": str((credential_summary or {}).get("status") or "skipped"),
            "idempotency_key_present": idempotency_key_present,
            "provider_status": provider_status,
            "lark_task_id_present": task_id_present,
        }
    )
    result = {
        "status": status,
        "connector": {"id": "lark_task", "kind": "lark_task"},
        "output": dict(compact),
        "audit": compact,
        "input_mapping": mapping_summary,
    }
    if credential_summary:
        result["credentials"] = credential_summary
    if status == "failed":
        result["error"] = f"lark_task live request failed: {provider_status}"
    return result
```

Implement the live branch in this exact order:

1. map the existing request body and build presence-only audit metadata;
2. if `_live_enabled()` is false, return `_live_result("failed", ..., "live_disabled", ...)` without resolving credentials or calling transport;
3. build the provider payload and `client_token`;
4. resolve credentials and require `REQUIRED_CREDENTIAL_HANDLE`;
5. call `(transport or _default_transport)(_request(payload, token), LIVE_TIMEOUT_SECONDS)`;
6. require `_successful_task_present(response)`;
7. return `_live_result("completed", ..., "completed", ..., credential_summary, True, True)`.

Do not add live-only keys to the base `_task_audit_metadata`; `_live_result` adds them so existing dry-run audit equality remains unchanged.

- [x] **Step 5: Run the connector tests and verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_task_connector -v
```

Expected: all dry-run and new successful live tests PASS.

- [x] **Step 6: Commit Task 2**

Run:

```bash
git add examples/connectors/lark_task_connector.py tests/test_lark_task_connector.py
git commit -m "feat: add scoped live lark task request"
```

Expected: one commit containing the live happy path and its focused tests.

### Task 3: Failure Normalization And Leakage Coverage

**Files:**
- Modify: `examples/connectors/lark_task_connector.py`
- Modify: `tests/test_lark_task_connector.py`

**Interfaces:**
- Consumes: Task 2 transport, request builder, credential values, and compact audit metadata
- Produces: `_provider_outcome(status: int, raw: bytes)`, `_failed_live_result(...)`, and stable `provider_status` behavior consumed by runtime audit and Task 4

- [x] **Step 1: Add the table-driven provider failure tests**

Add this test:

```python
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
                encoded = json.dumps(result, ensure_ascii=False)
                self.assertNotIn("local-lark-secret", encoded)
                self.assertNotIn("raw-", encoded)
                self.assertNotIn("not-json-provider-body", encoded)
```

Add imports for provider exception coverage:

```python
import io
import socket
from urllib import error as urllib_error
```

Add malformed, timeout, and URL-error coverage:

```python
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
                encoded = json.dumps(result, ensure_ascii=False)
                self.assertNotIn("raw timeout body", encoded)
                self.assertNotIn("raw socket timeout", encoded)
                self.assertNotIn("raw network failure", encoded)
                self.assertNotIn("raw http reason", encoded)
                self.assertNotIn("raw-http-body", encoded)
                self.assertNotIn("not-json-success-body", encoded)
```

Add this preflight test proving the transport is not called for missing execution identity, invalid due time, or missing credential:

```python
    def test_lark_task_live_preflight_failures_never_call_transport(self):
        missing_execution = {"input": dict(_execution_context()["input"])}
        invalid_due = json.loads(json.dumps(_execution_context()))
        invalid_due["input"]["due_at"] = "2026-07-09T09:00:00"
        cases = [
            (missing_execution, StaticCredentialProvider({"lark_bot_access_token": "secret"}), "validation_failed"),
            (invalid_due, StaticCredentialProvider({"lark_bot_access_token": "secret"}), "validation_failed"),
            (_execution_context(), StaticCredentialProvider({}), "credential_failed"),
        ]

        for context, provider, expected_status in cases:
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
                self.assertEqual(transport.calls, [])
```

- [x] **Step 2: Run the new tests and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_task_connector -v
```

Expected: FAIL because provider and transport failures are not yet returned as compact failed results.

- [x] **Step 3: Implement fixed failure classification**

Add:

```python
PROVIDER_CODE_STATUS = {
    1470400: "validation_failed",
    1470403: "permission_denied",
    1470404: "resource_not_found",
    1470422: "idempotency_conflict",
    1470500: "provider_unavailable",
}


def _http_status(status: int) -> str:
    if status == 400:
        return "validation_failed"
    if status == 401:
        return "authorization_failed"
    if status == 403:
        return "permission_denied"
    if status == 404:
        return "resource_not_found"
    if status == 429:
        return "rate_limited"
    if status >= 500:
        return "provider_unavailable"
    return "malformed_response"


def _decode_provider(raw: bytes):
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _provider_outcome(status: int, raw: bytes) -> Tuple[str, bool]:
    payload = _decode_provider(raw)
    if payload is not None:
        code = payload.get("code")
        if code == 0:
            data = payload.get("data", {})
            task = data.get("task", {}) if isinstance(data, dict) else {}
            guid = task.get("guid") if isinstance(task, dict) else ""
            if isinstance(guid, str) and guid:
                return "completed", True
            return "malformed_response", False
        if isinstance(code, int) and code in PROVIDER_CODE_STATUS:
            return PROVIDER_CODE_STATUS[code], False
    return _http_status(status), False


def _failed_live_result(
    audit: Dict[str, object],
    provider_status: str,
    mapping_summary: Dict[str, object],
    credential_summary: Dict[str, object] = None,
    idempotency_key_present: bool = False,
) -> Dict[str, object]:
    compact = dict(audit)
    compact.update(
        {
            "credential_status": str((credential_summary or {}).get("status") or "skipped"),
            "idempotency_key_present": idempotency_key_present,
            "provider_status": provider_status,
            "lark_task_id_present": False,
        }
    )
    result = {
        "status": "failed",
        "connector": {"id": "lark_task", "kind": "lark_task"},
        "output": dict(compact),
        "error": f"lark_task live request failed: {provider_status}",
        "audit": compact,
        "input_mapping": mapping_summary,
    }
    if credential_summary:
        result["credentials"] = credential_summary
    return result
```

Add imports:

```python
import socket
from urllib import error as urllib_error
```

Add the complete transport wrapper:

```python
def _transport_outcome(request: urllib_request.Request, transport) -> Tuple[str, bool]:
    try:
        response = transport(request, LIVE_TIMEOUT_SECONDS)
    except urllib_error.HTTPError as error:
        try:
            raw = error.read()
        finally:
            error.close()
        return _provider_outcome(int(error.code), raw)
    except (TimeoutError, socket.timeout):
        return "timeout", False
    except urllib_error.URLError as error:
        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            return "timeout", False
        return "provider_unavailable", False

    try:
        status = int(getattr(response, "status", 0))
        raw = response.read()
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            close()
    return _provider_outcome(status, raw)
```

Replace the Task 2 live sender's direct response parsing with `_transport_outcome(request, transport or _default_transport)`. Build a completed result only for `("completed", True)`; return `_failed_live_result(..., idempotency_key_present=True)` for every post-transport failure.

Provider code classification must precede generic HTTP classification. Never include `msg`, response bytes, exception text, request JSON, token, or task guid in result or error text.

In the live branch, wrap `_provider_request_body(...)` in `except ConnectorExecutionError` and return `_failed_live_result(..., "validation_failed", ..., idempotency_key_present=False)`. Wrap `_resolve_credentials(...)` in a separate `except ConnectorExecutionError` and return `_failed_live_result(..., "credential_failed", ..., credential_summary={"status": "failed", "handles": [REQUIRED_CREDENTIAL_HANDLE]}, idempotency_key_present=True)` because the client token has already been derived. Preserve existing dry-run exceptions exactly.

- [x] **Step 4: Run focused connector and dry-run smoke tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_task_connector tests.test_lark_task_connector_smoke tests.test_lark_task_pilot -v
python3 scripts/lark_task_connector_smoke.py --work-dir /tmp/skill2workflow-lark-task-connector
python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot
```

Expected: all tests and both dry-run smokes PASS without live network access.

- [x] **Step 5: Commit Task 3**

Run:

```bash
git add examples/connectors/lark_task_connector.py tests/test_lark_task_connector.py
git commit -m "feat: normalize live lark task failures"
```

Expected: one commit containing failure and leakage hardening.

### Task 4: Guarded Live Validation Command

**Files:**
- Create: `src/skill2workflow/lark_task_live_validation.py`
- Create: `scripts/lark_task_live_validation.py`
- Create: `tests/test_lark_task_live_validation.py`

**Interfaces:**
- Consumes: Task 2/3 `lark_task` entrypoint, `ConnectorRuntime`, `ExternalConnector`, `StaticCredentialProvider`
- Produces: `run_lark_task_live_validation(repo_root, title, description, assignee_open_id, validation_run_id, confirmed, transport=None) -> Dict[str, object]` and `main(argv=None) -> int`

- [x] **Step 1: Write validation guard and compact-output tests**

Create `tests/test_lark_task_live_validation.py`:

```python
import json
import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.lark_task_live_validation import run_lark_task_live_validation


ROOT = Path(__file__).resolve().parents[1]


class LarkTaskLiveValidationTests(TestCase):
    def test_live_validation_requires_confirmation_switch_token_and_identity(self):
        cases = [
            ({}, False, "run_validation", "ou_test", "live validation requires --confirm-live-create"),
            ({"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"}, True, "run_validation", "ou_test", "LARK_BOT_ACCESS_TOKEN is required"),
            ({"LARK_BOT_ACCESS_TOKEN": "secret"}, True, "run_validation", "ou_test", "SKILL2WORKFLOW_LARK_TASK_LIVE=1 is required"),
            ({"SKILL2WORKFLOW_LARK_TASK_LIVE": "1", "LARK_BOT_ACCESS_TOKEN": "secret"}, True, "", "ou_test", "validation run id is required"),
            ({"SKILL2WORKFLOW_LARK_TASK_LIVE": "1", "LARK_BOT_ACCESS_TOKEN": "secret"}, True, "run_validation", "", "assignee open id is required"),
        ]

        for environment, confirmed, run_id, assignee, expected in cases:
            with self.subTest(expected=expected), patch.dict(os.environ, environment, clear=True):
                with self.assertRaisesRegex(ValueError, expected):
                    run_lark_task_live_validation(
                        ROOT,
                        title="Validation title",
                        description="Validation description",
                        assignee_open_id=assignee,
                        validation_run_id=run_id,
                        confirmed=confirmed,
                        transport=lambda request, timeout: None,
                    )

    def test_live_validation_returns_only_compact_metadata(self):
        transport = _FakeTransport()
        environment = {
            "SKILL2WORKFLOW_LARK_TASK_LIVE": "1",
            "LARK_BOT_ACCESS_TOKEN": "live-validation-secret",
        }
        with patch.dict(os.environ, environment, clear=True):
            result = run_lark_task_live_validation(
                ROOT,
                title="Validation title",
                description="Validation description",
                assignee_open_id="ou_validation",
                validation_run_id="run_validation",
                confirmed=True,
                transport=transport,
            )

        self.assertEqual(
            result,
            {
                "ok": True,
                "connector_id": "lark_task",
                "operation": "create_task",
                "mode": "live",
                "credential_status": "resolved",
                "idempotency_key_present": True,
                "provider_status": "completed",
                "lark_task_id_present": True,
                "assignee_present": True,
            },
        )
        encoded = json.dumps(result)
        for forbidden in (
            "live-validation-secret",
            "Validation title",
            "Validation description",
            "ou_validation",
            "task-guid-must-not-leak",
        ):
            self.assertNotIn(forbidden, encoded)


class _FakeResponse:
    status = 200

    def read(self):
        return json.dumps(
            {"code": 0, "msg": "success", "data": {"task": {"guid": "task-guid-must-not-leak"}}}
        ).encode("utf-8")

    def close(self):
        return None


class _FakeTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append((request, timeout))
        return _FakeResponse()
```

- [x] **Step 2: Run the new test and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_task_live_validation -v
```

Expected: FAIL because the validation module does not exist.

- [x] **Step 3: Implement the validation module**

Create `src/skill2workflow/lark_task_live_validation.py` with:

```python
"""Guarded one-shot validation for the scoped live Lark task connector."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict

from .connectors import ConnectorRuntime, ExternalConnector
from .credentials import StaticCredentialProvider
from .external_connectors import load_external_connector


LIVE_SWITCH = "SKILL2WORKFLOW_LARK_TASK_LIVE"
TOKEN_ENVIRONMENT = "LARK_BOT_ACCESS_TOKEN"


def run_lark_task_live_validation(
    repo_root: Path,
    title: str,
    description: str,
    assignee_open_id: str,
    validation_run_id: str,
    confirmed: bool,
    transport=None,
) -> Dict[str, object]:
    if not confirmed:
        raise ValueError("live validation requires --confirm-live-create")
    if os.environ.get(LIVE_SWITCH) != "1":
        raise ValueError("SKILL2WORKFLOW_LARK_TASK_LIVE=1 is required")
    token = os.environ.get(TOKEN_ENVIRONMENT, "")
    if not token:
        raise ValueError("LARK_BOT_ACCESS_TOKEN is required")
    if not validation_run_id:
        raise ValueError("validation run id is required")
    if not assignee_open_id:
        raise ValueError("assignee open id is required")

    connector = load_external_connector(Path(repo_root) / "examples" / "connectors" / "lark_task_connector.py")
    if transport is not None:
        original = connector

        def execute_with_transport(binding, credential_provider=None, context=None):
            return original.executor(
                binding,
                credential_provider=credential_provider,
                context=context,
                transport=transport,
            )

        connector = ExternalConnector(manifest=original.manifest, executor=execute_with_transport)

    runtime = ConnectorRuntime([connector])
    result = runtime.execute_connector(
        _validation_node(title, description, assignee_open_id),
        credential_provider=StaticCredentialProvider({"lark_bot_access_token": token}),
        context={
            "_execution": {
                "workflow_id": "workflow_lark_task_live_validation",
                "workflow_version": "0.1.0",
                "run_id": validation_run_id,
                "node_id": "create_lark_task",
            }
        },
    )
    audit = result.get("audit", {}) if isinstance(result.get("audit"), dict) else {}
    return {
        "ok": result.get("status") == "completed",
        "connector_id": str(result.get("connector", {}).get("id", "")),
        "operation": str(audit.get("operation", "")),
        "mode": str(audit.get("mode", "")),
        "credential_status": str(audit.get("credential_status", "")),
        "idempotency_key_present": bool(audit.get("idempotency_key_present")),
        "provider_status": str(audit.get("provider_status", "")),
        "lark_task_id_present": bool(audit.get("lark_task_id_present")),
        "assignee_present": bool(audit.get("assignee_present")),
    }


def _validation_node(title: str, description: str, assignee_open_id: str) -> Dict[str, object]:
    return {
        "id": "create_lark_task",
        "type": "tool_call",
        "connector": {
            "id": "lark_task",
            "kind": "lark_task",
            "operation": "create_task",
            "mode": "live",
            "request": {
                "body": {
                    "title": title,
                    "description": description,
                    "assignee_open_id": assignee_open_id,
                }
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="lark_task_live_validation")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--assignee-open-id", required=True)
    parser.add_argument("--validation-run-id", required=True)
    parser.add_argument("--confirm-live-create", action="store_true")
    args = parser.parse_args(argv)
    result = run_lark_task_live_validation(
        args.repo_root,
        title=args.title,
        description=args.description,
        assignee_open_id=args.assignee_open_id,
        validation_run_id=args.validation_run_id,
        confirmed=args.confirm_live_create,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1
```

Create `scripts/lark_task_live_validation.py` using the same source-checkout wrapper pattern as `scripts/lark_task_connector_smoke.py`, importing `main` from `skill2workflow.lark_task_live_validation`.

- [x] **Step 4: Run validation and focused connector tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_task_live_validation tests.test_lark_task_connector -v
```

Expected: all tests PASS with injected transport only.

- [x] **Step 5: Commit Task 4**

Run:

```bash
git add src/skill2workflow/lark_task_live_validation.py scripts/lark_task_live_validation.py tests/test_lark_task_live_validation.py
git commit -m "feat: add guarded lark live validation"
```

Expected: one commit containing the validation command and tests.

### Task 5: Public Connector Contract Documentation

**Files:**
- Modify: `docs/connectors.md`
- Modify: `docs/lark-live-connector-readiness.md`
- Modify: `tests/test_live_connector_readiness.py`

**Interfaces:**
- Consumes: implemented behavior from Tasks 1-4 and the approved design
- Produces: tested public documentation for activation, endpoint, native idempotency, durable-input interpretation, failure categories, and validation command

- [x] **Step 1: Extend the failing documentation contract**

Add assertions to `test_lark_live_connector_readiness_decision_is_documented` for these exact strings across the readiness and connector guides:

```python
        self.assertIn("https://open.feishu.cn/open-apis/task/v2/tasks?user_id_type=open_id", decision)
        self.assertIn("native `client_token`", decision)
        self.assertIn("SKILL2WORKFLOW_LARK_TASK_LIVE=1", decision)
        self.assertIn("run.context.input", decision)
        self.assertIn("must not copy raw task values into connector-produced state", decision)
        self.assertIn("python3 scripts/lark_task_live_validation.py", decision)

        self.assertIn("mode: live", connectors)
        self.assertIn("SKILL2WORKFLOW_LARK_TASK_LIVE=1", connectors)
        self.assertIn("provider_status", connectors)
        self.assertIn("LARK_BOT_ACCESS_TOKEN", connectors)
```

- [x] **Step 2: Run the docs contract and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_live_connector_readiness -v
```

Expected: FAIL because the docs still describe live mode as future work.

- [x] **Step 3: Update connector and readiness documentation**

Document these exact boundaries:

- fixed Task API v2 endpoint and `user_id_type=open_id`;
- `mode: live` plus exact environment switch;
- dry-run default and explicit loading;
- native `client_token` derived from runtime identity;
- `lark_bot_access_token` handle and `LARK_BOT_ACCESS_TOKEN` only for the guarded validation helper;
- required provider scope is either `task:task:write` or `task:task:writeonly`;
- documented provider limit is 10 create requests per second;
- 10-second timeout;
- compact `provider_status` categories from the design;
- no raw provider messages, task values, task guid, token, request, or response in connector-produced state;
- durable `run.context.input` remains unchanged and may contain user-supplied task input;
- fake transport in CI and guarded validation command outside CI;
- rollback by removing the environment switch.

Preserve the historical sentence `examples/connectors/lark_task_connector.py remains dry-run-only in Loop 38` because existing tests use it as Loop 38 evidence. Replace only current-state language saying the package remains dry-run-only with language saying dry-run remains the default and live is opt-in.

- [x] **Step 4: Run documentation and connector tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_live_connector_readiness tests.test_lark_task_connector tests.test_lark_task_live_validation -v
```

Expected: all tests PASS.

- [x] **Step 5: Commit Task 5**

Run:

```bash
git add docs/connectors.md docs/lark-live-connector-readiness.md tests/test_live_connector_readiness.py
git commit -m "docs: document scoped live lark connector"
```

Expected: one docs-contract commit.

### Task 6: Offline Verification And Approved Real Validation

**Files:**
- Create after successful call: `docs/lark-live-connector-validation.md`
- Create: `tests/test_lark_live_connector_validation_docs.py`

**Interfaces:**
- Consumes: guarded validation command from Task 4, Vault secret `LARK_BOT_ACCESS_TOKEN`, and the current Lark user's authenticated `open_id` from conversation metadata
- Produces: one retained Feishu validation task and one committed redacted evidence note

- [x] **Step 1: Run all offline verification before any live write**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py examples/connectors/lark_task_connector.py
python3 scripts/secret_hygiene.py examples/workflows
python3 scripts/lark_task_connector_smoke.py --work-dir /tmp/skill2workflow-lark-task-connector
python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot
git diff --check
```

Expected: all tests, compilation, hygiene, smokes, and diff checks PASS. Stop before live validation if any command fails.

- [x] **Step 2: Locate or request the protected Vault secret**

Run:

```bash
vibe vault find LARK_BOT_ACCESS_TOKEN
```

If no static secret exists, run exactly:

```bash
vibe vault request LARK_BOT_ACCESS_TOKEN --reason "Validate the explicitly approved Loop 39 Feishu create_task live path once" --spec-json '{"kind":"static","protection":"protected","description":"Short-lived Feishu bot access token for the approved Loop 39 validation","tags":["feishu","loop39","skill:lark-live-validation"],"policy":{"allowed_hosts":["open.feishu.cn"],"auth":{"type":"bearer"}}}'
```

Expected: the Vault either reports an existing static secret or asks the user to add/approve it in the browser. Never ask the user to paste the token into chat.

- [x] **Step 3: Prepare ephemeral approved task parameters**

In the execution shell, set these three variables from the already approved conversation values and authenticated current-message metadata:

```bash
test -n "$LARK_VALIDATION_TITLE"
test -n "$LARK_VALIDATION_DESCRIPTION"
test -n "$LARK_VALIDATION_ASSIGNEE_OPEN_ID"
```

Expected: all three checks exit `0`. Do not write their values to a repository file, report, audit note, or terminal output.

- [x] **Step 4: Execute the approved live write exactly once**

Run:

```bash
vibe vault run --env LARK_BOT_ACCESS_TOKEN -- env \
  SKILL2WORKFLOW_LARK_TASK_LIVE=1 \
  PYTHONPATH=src \
  python3 scripts/lark_task_live_validation.py \
  --confirm-live-create \
  --validation-run-id skill2workflow-loop39-live-validation-20260711 \
  --title "$LARK_VALIDATION_TITLE" \
  --description "$LARK_VALIDATION_DESCRIPTION" \
  --assignee-open-id "$LARK_VALIDATION_ASSIGNEE_OPEN_ID"
```

Expected compact output:

```json
{
  "ok": true,
  "connector_id": "lark_task",
  "operation": "create_task",
  "mode": "live",
  "credential_status": "resolved",
  "idempotency_key_present": true,
  "provider_status": "completed",
  "lark_task_id_present": true,
  "assignee_present": true
}
```

If protected Vault use requests approval, wait for the user to approve and rerun the same `vibe vault run` command once. If the provider response is not completed, stop and diagnose without changing the idempotency run id or task parameters.

- [x] **Step 5: Write the failing evidence-note contract test**

Create `tests/test_lark_live_connector_validation_docs.py`:

```python
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class LarkLiveConnectorValidationDocsTests(TestCase):
    def test_live_validation_evidence_is_compact_and_redacted(self):
        evidence = (ROOT / "docs" / "lark-live-connector-validation.md").read_text(encoding="utf-8")

        self.assertIn("# Lark/Feishu Live Connector Validation", evidence)
        self.assertIn("- connector_id: `lark_task`", evidence)
        self.assertIn("- operation: `create_task`", evidence)
        self.assertIn("- mode: `live`", evidence)
        self.assertIn("- credential_status: `resolved`", evidence)
        self.assertIn("- idempotency_key_present: `true`", evidence)
        self.assertIn("- provider_status: `completed`", evidence)
        self.assertIn("- lark_task_id_present: `true`", evidence)
        self.assertIn("- assignee_present: `true`", evidence)
        self.assertIn("Raw task values, user ids, credentials, request bodies, response bodies, and task ids are intentionally omitted.", evidence)
```

- [x] **Step 6: Run the evidence test and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_live_connector_validation_docs -v
```

Expected: FAIL because the evidence file does not exist.

- [x] **Step 7: Create the redacted evidence note from actual compact output**

Create `docs/lark-live-connector-validation.md` with:

- heading `# Lark/Feishu Live Connector Validation`;
- the actual UTC validation timestamp returned or recorded immediately after the call;
- the eight exact compact fields asserted by the test;
- the exact omission sentence asserted by the test;
- the offline verification commands used before the write;
- a statement that the task was assigned to the consenting current user and retained as visible evidence, without the user id or task content.

Do not include the task title, description, assignee id, task guid, token, request body, response body, provider message, or idempotency digest.

- [x] **Step 8: Run evidence test and secret checks**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_live_connector_validation_docs -v
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

Expected: test PASS, no secret findings, no whitespace errors.

- [x] **Step 9: Commit Task 6 evidence**

Run:

```bash
git add docs/lark-live-connector-validation.md tests/test_lark_live_connector_validation_docs.py
git commit -m "docs: record live lark connector validation"
```

Expected: one commit containing only redacted evidence and its contract test.

### Task 7: Loop 39 Roadmap Transition And Final Verification

**Files:**
- Modify: `ROADMAP.md`
- Modify: `README.md`
- Modify: `tests/test_production_roadmap.py`
- Modify: `tests/test_product_connector_pilot_roadmap.py`
- Modify: `tests/test_first_product_connector_candidate_docs.py`
- Modify: `tests/test_live_connector_readiness.py`
- Modify: `docs/superpowers/plans/2026-07-11-scoped-live-lark-task.md`

**Interfaces:**
- Consumes: all implementation, offline evidence, and real validation from Tasks 1-6
- Produces: completed Loop 39 history, active Loop 40 planning state, matching README summary, and a checked execution record

- [x] **Step 1: Update Roadmap contract tests to the completed state**

Update exact assertions so they require:

```text
Completed delivery loops: 1-39
Active loop: Loop 40, Controlled Live Connector Pilot
| Loop 39: Scoped Live Lark Task Connector | Complete |
| Loop 40: Controlled Live Connector Pilot | Next |
Delivery Loops 1-39 are complete
```

Keep Loops 41-43 as Candidate. Preserve the four maturity gates and keep current maturity as Local Evaluation.

Add assertions that Roadmap links `docs/lark-live-connector-validation.md`, keeps live behavior limited to the fixed `create_task` action, and distinguishes the one connector validation from the Loop 40 controlled business-workflow pilot.

- [x] **Step 2: Run Roadmap tests and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_production_roadmap tests.test_product_connector_pilot_roadmap tests.test_first_product_connector_candidate_docs tests.test_live_connector_readiness -v
```

Expected: FAIL because Roadmap and README still show Loop 39 active.

- [x] **Step 3: Transition Roadmap and README**

In `ROADMAP.md`:

- set completed loops to 1-39;
- set active loop to Loop 40;
- move Loop 39 into Delivery History with fake-transport, native-idempotency, redaction, rollback, and real-validation evidence;
- make Loop 40 `Next` and expand its active-loop section with goal, why-now evidence, scope, exclusions, acceptance evidence, and verification direction;
- retain Loops 41-43 as candidates;
- link the redacted validation note;
- state that the single connector validation is not the controlled real-team workflow pilot;
- keep current maturity at Local Evaluation until Loop 40 completes.

In `README.md`, change only the compact Roadmap summary to Loops 1-39 complete and Loop 40 active. Do not copy Loop 41-43 titles or acceptance criteria.

- [x] **Step 4: Run Roadmap and all focused Loop 39 tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_production_roadmap \
  tests.test_product_connector_pilot_roadmap \
  tests.test_first_product_connector_candidate_docs \
  tests.test_live_connector_readiness \
  tests.test_lark_live_connector_validation_docs \
  tests.test_lark_task_connector \
  tests.test_lark_task_live_validation \
  tests.test_executor -v
```

Expected: all focused tests PASS.

- [x] **Step 5: Commit the Roadmap transition**

Run:

```bash
git add ROADMAP.md README.md tests/test_production_roadmap.py tests/test_product_connector_pilot_roadmap.py tests/test_first_product_connector_candidate_docs.py tests/test_live_connector_readiness.py
git commit -m "docs: complete loop 39 live lark connector"
```

Expected: one Roadmap/README contract commit.

- [x] **Step 6: Run final full verification**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py examples/connectors/lark_task_connector.py
python3 scripts/secret_hygiene.py examples/workflows
python3 scripts/lark_task_connector_smoke.py --work-dir /tmp/skill2workflow-lark-task-connector
python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot
git diff --check
git status --short
```

Expected: all tests and checks PASS; only this plan is modified for checkbox completion.

- [x] **Step 7: Mark every completed plan step**

Change each successfully executed `- [ ]` checkbox in this file to `- [x]`. Do not mark a step whose expected command or live-write outcome was not achieved.

- [x] **Step 8: Commit the completed execution record**

Run:

```bash
git add docs/superpowers/plans/2026-07-11-scoped-live-lark-task.md
git commit -m "docs: complete scoped live lark task plan"
```

Expected: the final commit contains only the checked implementation plan.
