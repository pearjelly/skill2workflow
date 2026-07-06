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
| `input_mapping` | Optional body-only mapping from durable trigger input into request body fields. |
| `timeout_ms` | Optional positive millisecond timeout. Missing or invalid values default to 5000 ms. |

If `body` is present and no case-insensitive `Content-Type` header is supplied, the connector adds `Content-Type: application/json`.

### HTTP Input Mapping

The built-in HTTP connector can copy non-secret values from durable run context into request body fields at execution time:

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
| `to` | Required JSON pointer under `/body/...`, applied to a runtime copy of `connector.request.body`. |
| `required` | Optional boolean. Defaults to `true`; when `false`, missing input leaves the static body unchanged. |

Input mapping never mutates the published Workflow DSL artifact. It applies only to the outbound request copy immediately before HTTP execution. Mapped values are not written to audit events; connector audit metadata may include compact mapping status and input keys only.

Current input mapping limits:

- only HTTP connector request body targets are supported
- no header, URL, path, query string, credential, environment, or file mapping
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

Future external connectors should use `execution_contract.mode: "external"` and provide their own package entrypoint, but this repository does not load external connector packages yet. Until a loader exists, external connector manifests are documentation and compatibility artifacts only.

The Python helper `validate_connector_manifest(manifest)` checks the minimum manifest shape without importing or executing connector code. Use it for contract tests when connector registry metadata changes.

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

The resolved value is used only for the outbound request. Connector results, run context, and audit events do not include the resolved credential value by default.

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

The built-in HTTP connector accepts static request metadata and optional credential handles so local examples and tests can run from a fresh checkout. Hosted secret stores, credential encryption, IAM, connector marketplaces, and product-specific SaaS connector packages are intentionally outside this MVP boundary.

Contributors should keep examples local and non-sensitive, such as `http://127.0.0.1` fixtures or placeholder URLs that are never executed in tests. If an example needs to show credential-shaped metadata, use credential handles or documented placeholders such as `<redacted>`, `REDACTED`, `placeholder`, `example-token`, or `token-placeholder`.

Run the committed-fixture guardrail before opening connector example PRs:

```bash
python3 scripts/secret_hygiene.py examples/workflows
```

See `docs/credential-boundary.md` for allowed placeholder patterns, scanner behavior, and the local credential-provider boundary.
