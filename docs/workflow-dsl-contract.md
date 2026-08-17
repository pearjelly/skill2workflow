# Workflow DSL Contract

This document describes the public contract for Workflow DSL `0.1.0`.

The Workflow DSL is the execution truth source for `skill2workflow`. Visual graphs, generated LiteGraph JSON, and future UI editors must round-trip through this DSL before execution or publication.

See `docs/workflow-dsl-compatibility.md` for the release-line compatibility policy and `docs/stability.md` for stable versus experimental surfaces.

## Schema

The versioned JSON Schema lives at:

```text
schemas/workflow.schema.json
```

The schema id is:

```text
https://skill2workflow.dev/schemas/workflow-0.1.0.json
```

The schema documents the stable top-level shape:

- `schema_version`
- `workflow`
- `entry`
- `nodes`
- `edges`
- `input_schema` (optional)
- `state_schema`
- `guards`
- `checkpoints`
- `policies`

It also documents the initial node and edge shapes. Connector retry policy
supports `max_attempts` plus an optional fixed `backoff_ms` from `0` to
`60000`. The `policies` object also supports a bounded
`workflow_timeout_ms` wall-clock deadline from `0` to `2592000000`
milliseconds; zero disables it and human-gate waiting consumes the budget.
Nodes may also declare `timeout_ms` from `0` to `86400000` milliseconds for a
bounded active-execution window; zero or omission disables it, and
human-gate waiting pauses it. Expiry records fixed `node_timeout` evidence at
a safe point and does not follow a successor.
The current schema intentionally allows additional properties so the compiler,
executor, visual editor, and connector runtime can add metadata without
breaking old readers.

## Declarative Trigger Input Contracts

Published workflows may declare an optional `input_schema` to make their
business-facing trigger payload explicit:

```json
{
  "input_schema": {
    "type": "object",
    "properties": {
      "customer_id": {"type": "string", "minLength": 1},
      "priority": {"type": "string", "enum": ["high", "normal"]}
    },
    "required": ["customer_id"],
    "additionalProperties": false
  }
}
```

This is a deliberately narrow JSON-Schema-like subset, not a claim of full
JSON Schema support. The root must be an object. Nested schemas support
`object`, `array`, `string`, `integer`, `number`, `boolean`, and `null`, with
`properties`, `required`, `additionalProperties`, `items`, `minLength`,
`maxLength`, `minimum`, `maximum`, and `enum` where applicable. Unsupported
keywords are rejected at workflow validation/publication time. The schema is
bounded to 64 KiB, eight nesting levels, 128 object properties, and 128 enum
items.

Trigger input is checked after the shared canonical 1 MiB envelope limit but
before a SQLite idempotency claim, run-state creation, audit emission, or any
external connector call. A rejected request returns a fixed validation error
with a JSON path and never echoes the rejected value. Workflows without
`input_schema` retain the historical open-object input behavior.

## Connector Binding

Connector-capable nodes declare a `connector` object directly on the node:

```json
{
  "id": "call_api",
  "type": "tool_call",
  "title": "Call API",
  "connector": {
    "id": "http",
    "kind": "http",
    "request": {
      "method": "POST",
      "url": "http://127.0.0.1:8080/example",
      "body": {"example": true},
      "input_mapping": [
        {
          "from": "/input/customer_id",
          "to": "/body/customer_id",
          "required": true
        }
      ]
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

Built-in bindings:

- `manual`: default binding for compiled `human_gate` nodes. Human gates still pause and resume through run state.
- `http`: default binding for compiled `tool_call` nodes. When `connector.request` is present, the local executor performs the HTTP request and records connector events.

HTTP connector credentials may reference local handles under `connector.credentials`. Only handles belong in Workflow DSL; resolved secret values are supplied at runtime through the local credential provider and are not written to run state or audit events by the built-in runtime.

The built-in HTTP connector may declare `connector.request.allowed_origins` as
an exact list such as [`https://api.example.com/`]. When present, the
request's normalized scheme/host/port origin must match one entry before
credentials are resolved or network access begins. Entries do not support
wildcards, paths beyond an optional `/`, query strings, fragments, or userinfo;
omitting the field preserves the legacy unrestricted destination behavior.

HTTP connector request metadata may declare bounded `input_mapping` and a
`response_mode` of `full` (default) or `metadata`. The built-in runtime reads
`/input/...` paths from durable run context and writes either `/body/...` fields
into a runtime copy of `connector.request.body` or scalar values into
`/query/<name>` URL parameters. In metadata mode, raw response headers and body
are discarded after bounded reading; only status, header count, byte count, and
a discard marker remain in the node result. These controls do not mutate the
published Workflow DSL artifact. Mapping audit metadata exposes status and
input keys only, not mapped values.

Validation requires `tool_call` nodes to declare `connector.id`. Missing bindings produce `connector_binding_missing`.

Published runs promote connector runtime events into control-plane audit events, including `connector_started`, `connector_completed`, `connector_failed`, and explicit `node_fallback` routes.

## Failure Transitions

All executable nodes declare `on_success`; nodes that can fail normally declare
`on_failure`. A `tool_call` may additionally declare `on_fallback`:

```json
{
  "id": "call_primary",
  "type": "tool_call",
  "on_success": "end",
  "on_failure": "failure",
  "on_fallback": "manual_recovery"
}
```

`on_fallback` is an explicit, edge-backed alternative path used only after the
connector has exhausted its declared retries. The failed node result and its
`node_failed` evidence remain durable; the executor records a `node_fallback`
event and continues at the declared target. It does not invoke another
provider automatically or erase the failed attempt. Only `tool_call` nodes may
declare this field; malformed or missing targets fail validation.

## Validation

The CLI keeps the existing human-readable mode:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli validate workflow.json
```

For tools and UI integrations, use JSON output:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli validate workflow.json --format json
```

JSON output shape:

```json
{
  "valid": false,
  "schema_version": "0.1.0",
  "errors": [
    {
      "code": "edge_target_missing",
      "message": "edge_1.to references missing node missing",
      "path": ["edges", 0, "to"],
      "severity": "error"
    }
  ]
}
```

The Python API exposes both modes:

- `validate_workflow(workflow)` returns a list of human-readable messages.
- `validate_workflow_structured(workflow)` returns machine-readable error objects.

## Error Object

Each structured validation error has:

- `code`: stable machine-readable error code
- `message`: human-readable explanation
- `path`: JSON path as a list of object keys and array indexes
- `severity`: currently always `error`

Consumers should branch on `code` and `path`, not on the message text.

## Golden Fixtures

Example workflows under `examples/workflows/` are compatibility fixtures. The current primary fixture is:

```text
examples/workflows/approval-flow.workflow.json
```

Contract tests verify that fixture stays valid under the structured validator.

## Compatibility Policy

The detailed policy lives in `docs/workflow-dsl-compatibility.md`.

For `0.1.x`:

- `schema_version` remains `0.1.0` until a breaking DSL shape change is required.
- Existing top-level fields must remain readable.
- Existing node ids, edge endpoints, transition fields, and workflow lifecycle fields keep their semantics.
- New metadata may be added through additional properties.
- New node types should update both `schemas/workflow.schema.json` and validator tests.
- Breaking changes require a new schema file and a migration path.

## Contributor Rules

- Keep Workflow DSL as the execution truth source.
- Add validator tests before changing DSL semantics.
- Add or update schema definitions when adding node or edge fields that contributors need to rely on.
- Preserve `validate_workflow()` compatibility unless there is a deliberate major-version change.
- Prefer structured errors for UI, editor, and control-plane integrations.
