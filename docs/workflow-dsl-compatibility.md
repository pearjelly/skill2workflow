# Workflow DSL Compatibility

This document defines the compatibility policy for Workflow DSL `0.1.0`.

The DSL is the execution truth source for `skill2workflow`. Visual graphs, editor state, run overlays, and generated artifacts must be converted back into Workflow DSL before execution or publication.

## Versioning

Current schema version:

```text
0.1.0
```

The schema file lives at:

```text
schemas/workflow.schema.json
```

The schema id is:

```text
https://skill2workflow.dev/schemas/workflow-0.1.0.json
```

## Compatibility Commitments For 0.1.x

Within the `0.1.x` release line:

- `schema_version: "0.1.0"` remains readable.
- Existing top-level fields keep their current meaning.
- Existing node ids, edge endpoints, and transition fields keep their semantics.
- Published workflow artifacts remain immutable after publication.
- Structured validation errors keep the `code`, `message`, `path`, and `severity` keys.
- New metadata may be added through additional properties.
- New node types may be added when schema and validator tests document their contract.
- Readers should ignore unknown additional properties unless they explicitly validate that field.

## Breaking Changes

A change is breaking if it:

- Renames or removes an existing top-level DSL field
- Changes the meaning of node ids, edge endpoints, or transition targets
- Makes previously valid `0.1.0` fixtures invalid without a migration path
- Changes structured validation error keys
- Makes published workflow artifacts mutable
- Makes LiteGraph JSON authoritative for execution

Breaking changes require:

- A new schema version
- A migration note
- Updated examples
- Validator tests that cover old and new behavior

## Visual Write-Back

Visual write-back is allowlisted. The editor may update:

- Node title
- Node description
- Human approval prompt
- Tool-call instruction
- Retry max attempts
- Built-in HTTP connector request method, URL, headers, body, and timeout

The editor must not change:

- Workflow node ids
- Edge topology
- Transition targets
- Source metadata
- Guard semantics
- Policy semantics
- Connector id or kind

## Connector Runtime Boundary

Workflow DSL `0.1.0` can carry built-in HTTP connector request metadata on `tool_call` nodes. The current local runtime supports method, URL, headers, body, and per-request timeout metadata as documented in `docs/connectors.md`.

`retry.max_attempts` and `policies.default_retry` remain policy metadata in the current local executor. They are preserved by readers and editable through the visual layer, but they do not imply automatic retry execution until that behavior is implemented with tests and compatibility notes.

Workflow DSL examples and fixtures must not store secrets. Credential storage, token injection, secret redaction, IAM, connector marketplaces, and product-specific SaaS connectors are outside the `0.1.x` built-in connector boundary.

## Consumer Guidance

Consumers should:

- Branch on structured validation error `code` and `path`, not message text.
- Treat undocumented fields as experimental.
- Validate Workflow DSL before execution.
- Treat generated LiteGraph JSON as an editor/view format.
- Prefer example workflows under `examples/workflows/` as compatibility fixtures.

## Contributor Guidance

When changing DSL behavior:

- Add or update schema definitions.
- Add structured validator tests before changing behavior.
- Update `docs/workflow-dsl-contract.md`.
- Update example workflows when they represent the supported contract.
- Describe compatibility impact in the PR body.
