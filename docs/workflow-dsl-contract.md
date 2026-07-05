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
- `state_schema`
- `guards`
- `checkpoints`
- `policies`

It also documents the initial node and edge shapes. The current schema intentionally allows additional properties so the compiler, executor, visual editor, and connector runtime can add metadata without breaking old readers.

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
      "body": {"example": true}
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

Validation requires `tool_call` nodes to declare `connector.id`. Missing bindings produce `connector_binding_missing`.

Published runs promote connector runtime events into control-plane audit events, including `connector_started`, `connector_completed`, and `connector_failed`.

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
