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
- Built-in HTTP connector request method, URL, headers, body, body-only input mapping, and timeout

The editor must not change:

- Workflow node ids
- Edge topology
- Transition targets
- Source metadata
- Guard semantics
- Policy semantics
- Connector id or kind

## Connector Runtime Boundary

Workflow DSL `0.1.0` can carry built-in HTTP connector request metadata on `tool_call` nodes. The current local runtime supports method, URL, headers, body, per-request timeout metadata, optional body-only `input_mapping` metadata, and optional credential handle metadata as documented in `docs/connectors.md`.

`retry.max_attempts` and `policies.default_retry` are policy metadata honored by the current local executor for connector nodes. They are preserved by readers, editable through the visual layer, and documented in `docs/runtime-policy.md`.

Workflow DSL examples and fixtures must not store secrets. They may reference credential handles under connector metadata, but resolved credential values must stay in a local provider boundary outside Workflow DSL, LiteGraph fixtures, trigger input, run state, and audit events. Hosted credential storage, secret redaction, IAM, connector marketplaces, and product-specific SaaS connectors are outside the `0.1.x` built-in connector boundary.

HTTP `connector.request.input_mapping` is a constrained runtime-copy mapping contract. It reads only `/input/...` paths from durable run context and writes only `/body/...` paths into the outbound HTTP request body copy. Header mapping, URL interpolation, expression syntax, credential mapping, and product-specific connector packages are outside the current compatibility boundary.

Connector manifests use the minimum contract documented in `docs/connectors.md`. Workflow DSL `connector.id` and `connector.kind` identify the connector a runtime should use, but Workflow DSL remains authoritative over node identity, transitions, guards, policies, and request metadata. The current local runtime exposes built-in manifests and does not dynamically load external connector packages.

Committed Workflow DSL and LiteGraph example fixtures are checked by `python3 scripts/secret_hygiene.py examples/workflows` for obvious secret-like values. See `docs/credential-boundary.md` for allowed placeholder patterns and the local credential-provider boundary.

## Connector Package Compatibility

Workflow DSL `0.1.0` compatibility is separate from connector package conventions. Workflow DSL stores connector bindings such as `connector.id`, `connector.kind`, request metadata, credential handles, retry policy, and body-only input mapping. A connector package supplies executable code and a connector manifest version outside the Workflow DSL schema.

Current connector package conventions use:

- Workflow DSL schema version: `0.1.0`
- Connector manifest version: `skill2workflow-connector-0.1.0`
- Connector execution contract version: `skill2workflow-connector-execution-0.1.0`
- Explicit local loader: `load_external_connector(path)`

Changing the connector manifest version or execution contract version is not automatically a Workflow DSL breaking change. It becomes a Workflow DSL compatibility issue only if existing `schema_version: "0.1.0"` workflow artifacts can no longer bind to connector ids/kinds, preserve request metadata, validate, publish, or execute through an explicit runtime configuration.

Connector package conventions remain local-first: explicit file loading and registration are supported for examples and smoke tests, while automatic discovery, package installation, connector marketplaces, OAuth, hosted callbacks, queues, and product-specific connector packages remain outside the current compatibility boundary.

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
