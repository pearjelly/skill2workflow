# Connector Runtime

`skill2workflow` currently ships a minimal local connector runtime. It is designed to make connector-bound workflow nodes testable and auditable without adding external services, SDK dependencies, secret storage, or a connector marketplace. Built-in HTTP payloads are bounded to protect the self-hosted process from untrusted response sizes and oversized serialized request bodies.
Loop 33 adds one explicitly loaded local external connector fixture to prove the extension boundary. Loop 36 adds the first product-shaped connector package fixture, a Lark/Feishu task `create_task` dry-run connector. Loop 37 proves that connector inside a sales renewal risk pilot workflow. Loop 38 readiness review approved only a scoped live `create_task` follow-up, documented in `docs/lark-live-connector-readiness.md`. Loop 39 implements that one opt-in live action while preserving explicit loading and the dry-run default; it does not add automatic discovery, OAuth, token refresh, or marketplace behavior.

Workflow DSL remains the execution truth source. Connector bindings live on workflow nodes, and the local executor records connector lifecycle events in run state and control-plane audit logs.

## Built-In Connectors

### Manual

The `manual` connector is the default connector for `human_gate` nodes.

Manual gates are not executed as outbound calls. They pause the run until a user resumes the gate with approval or rejection. The executor records `human_gate_waiting` and `human_gate_resumed` events, and published runs promote those events into the control-plane audit trail.

### HTTP

The `http` connector is the default connector for `tool_call` nodes.

When a `tool_call` node includes `connector.request`, the local executor sends a minimal HTTP request using the Python standard library:

```json
{
  "connector": {
    "id": "http",
    "kind": "http",
    "request": {
      "method": "POST",
      "url": "http://127.0.0.1:8080/example",
      "headers": {
        "Content-Type": "application/json"
      },
      "body": {
        "source": "skill2workflow"
      },
      "timeout_ms": 3000
    }
  }
}
```

Supported request metadata:

| Field | Behavior |
| --- | --- |
| `method` | Optional HTTP method. Defaults to `GET` and is uppercased before execution. |
| `url` | Required `http://` or `https://` URL. Other schemes fail before a network call. |
| `allowed_origins` | Optional exact-origin egress allowlist. Entries are `http://` or `https://` origins without userinfo, query, or fragment; omission preserves legacy unrestricted destination behavior. |
| `headers` | Optional object. Keys and values are stringified. |
| `body` | Optional JSON-serializable value. When present, it is encoded as UTF-8 JSON and must be at most 1 MiB. |
| `response_mode` | Optional response retention mode: `full` (default) keeps the legacy headers/body projection; `metadata` discards raw response headers and body after bounded reading. |
| `input_mapping` | Optional bounded mapping from durable trigger input into request body fields or query parameters. |
| `timeout_ms` | Optional positive millisecond timeout. Missing or invalid values default to 5000 ms. |

The built-in connector never follows HTTP redirects. Any `3xx` response is
rejected before a second request with the fixed error
`http connector redirects are disabled`. This prevents credential headers from
being replayed to a redirect target. Normal non-redirect `2xx`, `4xx`, and
`5xx` responses keep their existing result contract. Workflows that need a
provider-specific redirect policy must use an explicitly reviewed connector
boundary rather than enabling automatic follow-up requests here.

The connector also ignores ambient `http_proxy`, `https_proxy`, and
`ALL_PROXY` environment settings. Requests go directly to the configured URL;
there is no implicit proxy route that can receive resolved credentials. A
workflow that requires a proxy must use a separately reviewed connector with an
explicit, documented proxy boundary.

The self-hosted service can add a second, service-wide upper bound through
repeated `service-init --http-allowed-origin` options, which write
`runtime.http_allowed_origins` in `service.json`. It accepts up to 32 exact
origins and is shared by direct service triggers and recurring-schedule
dispatches. When configured, a request must match both the service list and
the workflow list; the service check runs before credential resolution or
network access. This setting is omitted by default for compatibility and is
not applied to explicitly loaded external connectors, whose provider-specific
egress must be reviewed separately.

This is exact-origin governance, not a wildcard matcher, DNS-rebinding
defense, IP-range policy, network firewall, or multi-tenant isolation. Operators
should combine it with the documented external TLS and host-network boundary.

### HTTP Request Metadata Boundary

Request metadata is bounded independently of the 1 MiB body boundary:

- URL: at most `16,384` UTF-8 bytes, with a valid `http`/`https` host and
  numeric port when present; embedded userinfo, NUL, and CR/LF are rejected.
- Method: an ASCII HTTP token of at most `32` bytes.
- Headers: at most `64` entries and `65,536` UTF-8 bytes in combined names and
  values; empty names and NUL/CR/LF characters are rejected.

Malformed or oversized metadata raises a fixed `ConnectorExecutionError`
before network access. Static URL, method, and header failures are rejected
before credential handles are resolved, and request-construction exceptions
are normalized instead of escaping as raw `urllib`/`http.client` exceptions.

### HTTP Payload Boundary

The built-in HTTP connector applies one fixed `1,048,576`-byte (`1 MiB`) bound
to both directions. A serialized request body that exceeds the bound fails
before the network opener is called. A successful or error response is read at most one
byte beyond the bound so an oversized body is rejected before it is returned
or persisted in run state. Response bodies must be valid UTF-8; invalid bytes
produce the fixed connector error `http connector response body must be valid
UTF-8`. Oversized bodies produce the fixed request/response errors and never
return a partial payload. This is a memory and state-size boundary, not a
content-redaction or provider-side cancellation guarantee.

Set `response_mode` to `metadata` when a workflow only needs completion status
and must not retain provider response values in run state:

```json
{
  "connector": {
    "id": "http",
    "kind": "http",
    "request": {
      "url": "http://127.0.0.1:8080/example",
      "response_mode": "metadata"
    }
  }
}
```

Metadata mode still reads the response through the fixed 1 MiB UTF-8 boundary,
then returns only `status_code`, `header_count`, `body_bytes`, and
`body_discarded: true`. It applies to successful and HTTP error responses and
does not alter the request or retry contract. The default `full` mode remains
backward compatible.

External connector packages own their provider-specific I/O limits, but their
normalized result still crosses the runtime's fixed 1 MiB persistence
boundary. Non-JSON or oversized external results fail before they are attached
to durable run state. An ordinary exception raised by a fixture is normalized
to `external connector execution failed`; connector-authored
`ConnectorExecutionError` messages remain part of the explicit fixture
contract and must be compact and value-free. See
[`external-connector-result-boundary.md`](external-connector-result-boundary.md).

If `body` is present and no case-insensitive `Content-Type` header is supplied, the connector adds `Content-Type: application/json`.

### HTTP Input Mapping

The built-in HTTP connector can copy non-secret values from durable run context into request body fields or query parameters at execution time:

```json
{
  "connector": {
    "id": "http",
    "kind": "http",
    "request": {
      "method": "POST",
      "url": "http://127.0.0.1:8080/example",
      "body": {
        "source": "skill2workflow"
      },
      "input_mapping": [
        {
          "from": "/input/customer_id",
          "to": "/body/customer_id",
          "required": true
        },
        {
          "from": "/input/page",
          "to": "/query/page",
          "required": false
        }
      ]
    }
  }
}
```

Supported mapping fields:

| Field | Behavior |
| --- | --- |
| `from` | Required JSON pointer under `/input/...`, resolved against `run_state.context.input`. |
| `to` | Required target under `/body/...` or `/query/<name>`. Body targets are applied to a runtime copy of `connector.request.body`; query targets replace an existing parameter with the same name and are percent-encoded. |
| `required` | Optional boolean. Defaults to `true`; when `false`, missing input leaves the static request unchanged. |

Input mapping never mutates the published Workflow DSL artifact. It applies only to the outbound request copy immediately before HTTP execution. Mapped values are not written to audit events; connector audit metadata may include compact mapping status and input keys only.

Current input mapping limits:

- only HTTP connector request body fields and flat query parameter targets are supported
- query targets accept only scalar string, number, or boolean input values
- no header, URL interpolation, path, credential, environment, or file mapping
- no arbitrary string templates, expression language, or script evaluation
- trigger input must remain non-secret business metadata

## Connector Extension Contract

Loop 31 defines the manifest and execution boundary future connector packages must follow. It does not add a dynamic plugin loader or product-specific connector package. The built-in `manual` and `http` connectors are the reference implementations for this contract.

Connector manifests use this minimum shape:

```json
{
  "manifest_version": "skill2workflow-connector-0.1.0",
  "id": "http",
  "name": "HTTP Connector",
  "kind": "http",
  "status": "active",
  "node_types": ["tool_call"],
  "description": "Built-in connector for minimal HTTP requests from tool-call nodes.",
  "config_schema": {
    "type": "object",
    "properties": {
      "request": {"type": "object"}
    }
  },
  "execution_contract": {
    "contract_version": "skill2workflow-connector-execution-0.1.0",
    "mode": "built_in",
    "entrypoint": "skill2workflow.connectors:execute_connector",
    "receives": ["node.connector", "run_context", "credential_provider"],
    "returns": ["status", "connector", "output", "error", "input_mapping"]
  },
  "credential_contract": {
    "supports_handles": true,
    "targets": ["header"],
    "resolved_value_policy": "never_in_workflow_run_state_or_audit"
  },
  "audit_contract": {
    "value_policy": "compact_no_payload_values",
    "events": ["connector_started", "connector_completed", "connector_failed"]
  }
}
```

Manifest fields:

| Field | Behavior |
| --- | --- |
| `manifest_version` | Required. Current value is `skill2workflow-connector-0.1.0`. |
| `id` | Required stable connector id used by Workflow DSL `connector.id`. |
| `kind` | Required connector kind. Built-ins use `manual` and `http`. |
| `status` | Required registry status such as `active`. |
| `node_types` | Required non-empty list of supported Workflow DSL node types. |
| `config_schema` | Required object describing connector configuration metadata. It is descriptive in this local runtime; Workflow DSL validation remains authoritative. |
| `execution_contract` | Required object describing how the runtime calls the connector and what normalized result shape it returns. |
| `credential_contract` | Required object describing handle support and resolved-value policy. |
| `audit_contract` | Required object describing compact audit event behavior. |

Execution handoff:

- The Workflow DSL node remains the execution source of truth.
- Connector code receives the node connector binding, optional durable run context, and an optional credential provider.
- Connector code must return a normalized result with `status`, `connector`, `output`, and optional `error` fields.
- Connector code must not mutate the published Workflow DSL artifact.
- Connector code must not write resolved credentials, raw authorization headers, raw webhook bodies, or mapped business payload values into audit events.

Future external connectors should use `execution_contract.mode: "external"` and provide their own package entrypoint. The current runtime supports one narrow prototype path: tests or smoke helpers may explicitly load a local connector fixture file and register it with `ConnectorRuntime`. This is not a dynamic package loader, connector installer, marketplace, OAuth flow, hosted callback system, queue, or production scheduler.

For local evaluation, the same explicit fixture boundary is available from the
installed CLI. The flag loads reviewed Python code only for the current process;
it never changes the default connector registry or persists plugin code into
Workflow DSL or service state:

```bash
skill2workflow run /tmp/workflow.json \
  --connector-fixture examples/connectors/local_echo_connector.py \
  --state-dir /tmp/skill2workflow-state

skill2workflow resume <run_id> \
  --connector-fixture examples/connectors/local_echo_connector.py \
  --state-dir /tmp/skill2workflow-state

skill2workflow bundle-run /tmp/workflow.s2w \
  --connector-fixture examples/connectors/local_echo_connector.py \
  --allow-side-effects \
  --state-dir /tmp/skill2workflow-bundle-state

skill2workflow connectors \
  --connector-fixture examples/connectors/local_echo_connector.py
```

This is intentionally a local, operator-supplied code-loading path. It is not
available through the long-running service, remote trigger API, automatic
discovery, or package installation. The loader accepts only a regular,
non-symbolic-link file, reads at most 2 MiB of UTF-8 source through a
no-follow descriptor bound to the file's device and inode, and detects a file
replacement or growth before compiling it in memory. This bounds the loader's
file handoff; it is not a Python sandbox. Only load connector files that have
been reviewed as executable code. The existing credential, input, result-size,
and audit-redaction boundaries still apply. See
[`external-connector-loading-boundary.md`](external-connector-loading-boundary.md)
for the exact contract.

The `connectors` inspection command prints the built-in manifests plus the
explicit fixture manifest without creating state or executing connector code.
Without `--connector-fixture`, it preserves the existing built-in or persisted
control-plane listing behavior.

Explicit local fixture loading:

```python
from pathlib import Path

from skill2workflow.connectors import ConnectorRuntime
from skill2workflow.external_connectors import load_external_connector

external_connector = load_external_connector(Path("examples/connectors/local_echo_connector.py"))
runtime = ConnectorRuntime([external_connector])
```

Pass the runtime into the local control plane or snapshot builder when a published run needs that fixture:

```python
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.dashboard import build_control_snapshot

control = LocalControlPlane(state_dir, connector_runtime=runtime)
snapshot = build_control_snapshot(state_dir, connector_runtime=runtime)
```

The default connector registry remains only `manual` and `http` unless an external fixture is explicitly registered.

Run the prototype smoke from a source checkout:

```bash
python3 scripts/external_connector_smoke.py --work-dir /tmp/skill2workflow-external-connector
```

The smoke loads `examples/connectors/local_echo_connector.py`, publishes a local workflow, triggers it with non-secret input, resolves a local credential handle at execution time, and writes workflow, run, audit, connector, trigger, and control-plane snapshot artifacts under the work directory.

The Python helper `validate_connector_manifest(manifest)` checks the minimum manifest shape without importing or executing connector code. Use it for contract tests when connector registry metadata changes.

External connector executors must return the same compact result shape as built-ins. The complete normalized result envelope is bounded to 1 MiB and must round-trip through standard JSON before it enters durable state. They may include `credentials` and `input_mapping` summaries, but those summaries must contain handles, statuses, and input key names only. Resolved credential values and raw mapped business values must not be returned.

Published-run audit events promote compact connector metadata for inspection. For external fixtures this includes fields such as `credential_status`, `credential_handles`, `input_mapping_status`, and `input_mapping_keys`, not payload values.

## Connector Package Layout

Loop 34 treats a connector package as a local source fixture that can be copied, reviewed, tested, and explicitly loaded. A package is not installed automatically and does not register itself with the default connector registry.

Reference layout:

```text
examples/connectors/
  local_echo_connector.py  # MANIFEST plus execute(...) reference implementation
  lark_task_connector.py   # Product-shaped dry-run connector package fixture
```

Required package surface:

| Item | Requirement |
| --- | --- |
| `MANIFEST` | Module-level dict that passes `validate_connector_manifest(MANIFEST)`. |
| `MANIFEST.execution_contract.mode` | Must be `external` for out-of-core connector fixtures. |
| `MANIFEST.execution_contract.entrypoint` | Human-readable module path to the executor, such as `examples/connectors/local_echo_connector.py:execute`. |
| `execute(binding, credential_provider=None, context=None)` | Module-level callable used by the explicit loader. |
| Result shape | Dict with `status`, `connector`, `output`, and optional `error`, `input_mapping`, and `credentials` summaries. |
| Credential behavior | Resolve handles at execution time, but return only handle names and compact status. |
| Audit behavior | Return compact metadata only; never return raw payload values, raw authorization headers, or resolved secrets. |

Explicit package loading remains the only supported package path:

```python
from pathlib import Path

from skill2workflow.connectors import ConnectorRuntime
from skill2workflow.external_connectors import load_external_connector

external_connector = load_external_connector(Path("examples/connectors/local_echo_connector.py"))
runtime = ConnectorRuntime([external_connector])
```

Connector package smoke contract:

- The package can be loaded from a fresh checkout by file path.
- `ConnectorRuntime().list_connectors()` still returns only `manual` and `http`.
- `ConnectorRuntime([external_connector]).list_connectors()` includes the external connector id.
- A published workflow can execute the external connector through the existing control plane.
- Smoke artifacts include workflow, run, audit, connector, trigger, and control-plane snapshot JSON.
- Resolved credential values and raw mapped business values do not appear in run state, audit events, or smoke result summaries.

Package conventions intentionally exclude automatic connector discovery, package installation, marketplace indexing, OAuth, hosted callbacks, queues, production schedulers, and product-specific SaaS connector behavior.

## Lark/Feishu Task Connector: Dry-Run Default And Scoped Live Mode

`examples/connectors/lark_task_connector.py` is the first product-shaped connector package fixture. It stays outside the built-in connector registry and must be explicitly loaded with `load_external_connector(...)`.

Supported scope:

- connector id and kind: `lark_task`
- operation: `create_task`
- default mode: `dry_run`
- opt-in mode: live
- node type: `tool_call`
- credential handle: `lark_bot_access_token`
- input mapping: body-only values from `/input/title`, `/input/description`, `/input/assignee_open_id`, and `/input/due_at`

The connector validates the request shape, resolves the local credential handle, and returns only compact metadata:

- operation and mode
- credential status and handle names
- input mapping status and input key names
- booleans indicating whether title, description, assignee, and due date were present

Dry-run remains the default when `mode` is missing or is `dry_run`. It validates and summarizes the request without a provider call. Raw mapped task values and resolved credential values must not appear in connector output or audit metadata.

The live connector readiness decision is documented in `docs/lark-live-connector-readiness.md`. The package now supports only the approved opt-in `create_task` action. Live network activity requires both an explicitly loaded binding with `mode: live` and the exact environment switch `SKILL2WORKFLOW_LARK_TASK_LIVE=1`; removing the switch immediately rolls the connector back to no live calls. No other truthy environment values enable it.

The connector posts only to the fixed Feishu domestic Task API v2 endpoint:

```text
https://open.feishu.cn/open-apis/task/v2/tasks?user_id_type=open_id
```

It uses a fixed 10-second timeout. The required provider scope is either `task:task:write` or `task:task:writeonly`, and the documented limit is 10 create requests per second. The connector derives the native Feishu `client_token` from runtime-owned workflow id, workflow version, run id, and node id. Retries may still invoke transport; reusing the stable token with unchanged request parameters lets Feishu perform provider-side deduplication. The connector does not locally block retry transport calls.

Normal execution resolves the `lark_bot_access_token` handle through the configured credential provider. `LARK_BOT_ACCESS_TOKEN` is reserved for the guarded validation helper and is not a Workflow DSL or connector-binding field. The helper must be run outside CI with explicit confirmation:

```bash
vibe vault run --env LARK_BOT_ACCESS_TOKEN -- env SKILL2WORKFLOW_LARK_TASK_LIVE=1 python3 scripts/lark_task_live_validation.py \
  --confirm-live-create \
  --validation-run-id '<stable-run-id>' \
  --assignee-open-id '<open_id>' \
  --title '<task-title>' \
  --description '<task-description>'
```

Use Avibe Vault as shown, or an equivalent secret manager that injects `LARK_BOT_ACCESS_TOKEN` only into the child process. Never paste the token into the command or shell history.

CI injects a fake transport and never accesses the live network. Recognized Feishu provider codes take precedence over generic HTTP status classification. Normalized `provider_status` values are exactly: `live_disabled`, `validation_failed`, `credential_failed`, `authorization_failed`, `permission_denied`, `rate_limited`, `resource_not_found`, `idempotency_conflict`, `provider_unavailable`, `timeout`, `malformed_response`, and `completed`.

Connector-produced output, audit, events, snapshots, and summaries contain presence flags and compact statuses only. They never contain raw provider messages, task values, the task guid, resolved token, `client_token`, raw request, or raw response. Durable user-supplied task input remains unchanged under `run.context.input`; it is not connector-produced state.

Run the dry-run smoke from a source checkout:

```bash
python3 scripts/lark_task_connector_smoke.py --work-dir /tmp/skill2workflow-lark-task-connector
```

The smoke explicitly loads `examples/connectors/lark_task_connector.py`, publishes a generated workflow, triggers it with non-secret task input, resolves `lark_bot_access_token` through a temporary local credential provider, and writes workflow, run, audit, connector, trigger, and control-plane snapshot artifacts under the work directory.

Run the sales renewal risk pilot smoke from a source checkout:

```bash
python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot
```

The pilot uses the same explicitly loaded package inside a workflow that starts through the local webhook trigger boundary, waits at a manual gate, resumes with approval, and then invokes the connector. It proves business handoff and operator evidence, not live Lark/Feishu task creation.

For the one approved controlled real-team pilot, follow `docs/controlled-live-pilot.md`. The dry-run remains the default; that runbook permits only the fixed Feishu domestic `create_task` action behind the existing explicit live guards.

HTTP connector bindings may also reference local credential handles:

```json
{
  "connector": {
    "id": "http",
    "kind": "http",
    "request": {
      "url": "http://127.0.0.1:8080/example"
    },
    "credentials": [
      {
        "target": "header",
        "name": "Authorization",
        "handle": "demo_api_token",
        "prefix": "Bearer "
      }
    ]
  }
}
```

Supported credential metadata:

| Field | Behavior |
| --- | --- |
| `target` | Required. Only `header` is supported in the current built-in HTTP connector. |
| `name` | Required HTTP header name. |
| `handle` | Required credential handle resolved by the local credential provider. |
| `prefix` | Optional string prepended to the resolved value. |

Provide values at runtime with a local credential file:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli run /tmp/skill2workflow-workflow.json \
  --state-dir /tmp/skill2workflow-state \
  --credential-file /tmp/skill2workflow-credentials.json
```

The credential file has this shape:

```json
{
  "credentials": {
    "demo_api_token": "local-secret-value"
  }
}
```

The resolved value is used only for the outbound request. Connector results, run context, and audit events do not include the resolved credential value by default. The local JSON file is bounded to 2 MiB and rejects symlink, replacement, and growth races before parsing; see [`credential-file-boundary.md`](credential-file-boundary.md).

## Result Semantics

Successful HTTP responses produce a completed connector result:

```json
{
  "status": "completed",
  "connector": {
    "id": "http",
    "kind": "http"
  },
  "output": {
    "status_code": 200,
    "headers": {},
    "body": "{\"ok\": true}"
  }
}
```

HTTP 4xx and 5xx responses produce a failed connector result instead of raising:

```json
{
  "status": "failed",
  "connector": {
    "id": "http",
    "kind": "http"
  },
  "output": {
    "status_code": 503,
    "headers": {},
    "body": "{\"error\": \"unavailable\"}"
  },
  "error": "HTTP 503"
}
```

Invalid request metadata, unsupported URL schemes, JSON body serialization
failures, connection failures, and timeouts raise `ConnectorExecutionError`.
The executor catches those errors, records a failed connector node result,
emits `connector_failed` and `node_failed`, and follows the node's `on_failure`
transition unless the node declares an explicit `on_fallback` path. Request
body serialization failures use the fixed message
`http connector request.body must be JSON serializable`; network failures use
`http connector request failed`; and timeouts use `http connector timed out`.
Underlying URL, provider-transport, proxy, socket, and exception text is never
copied into the connector failure message or durable run state. An explicitly
retained full HTTP response body remains governed by the existing response
retention mode.

## Retry And Timeout Boundary

`connector.request.timeout_ms` is the per-request timeout for the built-in HTTP connector. It is not a whole-node deadline and does not include queueing, human approval, or downstream workflow execution time. The separate top-level `policies.default_timeout_ms` budget bounds active workflow execution segments; see [`runtime-policy.md`](runtime-policy.md).

`retry.max_attempts`, `retry.backoff_ms`, and their `policies.default_retry.*`
counterparts are Workflow DSL policy fields. The local executor honors them for
connector nodes. `max_attempts` means retries after the first attempt; `1`
allows two total connector attempts. `backoff_ms` is a fixed delay before each
retry, defaults to `0`, and is bounded to 60,000 milliseconds. The executor
records the effective delay in the node result and retry event; a configured
delay is still subject to the active `default_timeout_ms` execution budget.

Retry and recovery events are recorded in run state and published-run audit logs:

- `node_retrying`
- `node_recovered`
- `node_failed`
- `node_fallback`

See `docs/runtime-policy.md` for current policy semantics and limits.

## Credential Boundary

Workflow DSL fixtures must not store secrets.

The built-in HTTP connector accepts static request metadata and optional credential handles so local examples and tests can run from a fresh checkout. Hosted secret stores, credential encryption, IAM, connector marketplaces, and product-specific SaaS connector packages are intentionally outside this MVP boundary.

Contributors should keep examples local and non-sensitive, such as `http://127.0.0.1` fixtures or placeholder URLs that are never executed in tests. If an example needs to show credential-shaped metadata, use credential handles or documented placeholders such as `<redacted>`, `REDACTED`, `placeholder`, `example-token`, or `token-placeholder`.

Run the committed-fixture guardrail before opening connector example PRs:

```bash
python3 scripts/secret_hygiene.py examples/workflows
```

See `docs/credential-boundary.md` for allowed placeholder patterns, scanner behavior, and the local credential-provider boundary.
