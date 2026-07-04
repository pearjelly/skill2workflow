# Connector Runtime

`skill2workflow` currently ships a minimal local connector runtime. It is designed to make connector-bound workflow nodes testable and auditable without adding external services, SDK dependencies, secret storage, or a connector marketplace.

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
| `headers` | Optional object. Keys and values are stringified. |
| `body` | Optional JSON-serializable value. When present, it is encoded as UTF-8 JSON. |
| `timeout_ms` | Optional positive millisecond timeout. Missing or invalid values default to 5000 ms. |

If `body` is present and no case-insensitive `Content-Type` header is supplied, the connector adds `Content-Type: application/json`.

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

Invalid request metadata, unsupported URL schemes, JSON body serialization failures, connection failures, and timeouts raise `ConnectorExecutionError`. The executor catches those errors, records a failed connector node result, emits `connector_failed` and `node_failed`, and follows the node's `on_failure` transition.

## Retry And Timeout Boundary

`connector.request.timeout_ms` is the per-request timeout for the built-in HTTP connector. It is not a whole-node deadline and does not include queueing, human approval, or downstream workflow execution time.

`retry.max_attempts` and `policies.default_retry.max_attempts` are Workflow DSL policy fields. The local executor honors them for connector nodes. `max_attempts` means retries after the first attempt; `1` allows two total connector attempts.

Retry and recovery events are recorded in run state and published-run audit logs:

- `node_retrying`
- `node_recovered`
- `node_failed`

See `docs/runtime-policy.md` for current policy semantics and limits.

## Credential Boundary

Workflow DSL fixtures must not store secrets.

The built-in HTTP connector accepts static request metadata so local examples and tests can run from a fresh checkout. Enterprise credential management, token injection, secret redaction, IAM, connector marketplaces, and product-specific SaaS connector packages are intentionally outside this MVP boundary.

Until a credential layer exists, contributors should keep examples local and non-sensitive, such as `http://127.0.0.1` fixtures or placeholder URLs that are never executed in tests. If an example needs to show credential-shaped metadata, use documented placeholders such as `<redacted>`, `REDACTED`, `placeholder`, `example-token`, or `token-placeholder`.

Run the committed-fixture guardrail before opening connector example PRs:

```bash
python3 scripts/secret_hygiene.py examples/workflows
```

See `docs/credential-boundary.md` for allowed placeholder patterns, scanner behavior, and future credential provider boundaries.
