# Workflow DSL Compatibility

Preflight now applies the existing trigger input canonical-copy and 1 MiB UTF-8
bound before schema/mapping analysis. Over-limit or nonfinite input cannot
produce a ready report; authenticated malformed preflights receive fixed 400
refusals and clients reject invalid input before I/O. Workflow/report schemas,
runtime admission, exports and existing transport/report limits are unchanged.
See [preflight input limits](workflow-preflight.md#local-draft-check).

The editor now coordinates asynchronous JSON/example/Skill imports so obsolete
results cannot overwrite newer drafts or edits. Current JSON read/parse errors
use fixed recovery text and retain active-graph validation; document replacement
clears previously staged Skill text. This affects local UI ownership only, not
source formats, DSL, exports, validation semantics, publication or execution.
See [draft import ownership](authoring.md#keep-the-current-draft-during-imports).

An explicit standalone Skill `workflow_version` declaration selects the existing
`workflow.version` field for newly compiled drafts. No declaration retains
`0.1.0`; ordinary metadata is not deployment intent. This bounded source grammar
does not narrow manually authored DSL versions or alter published workflows,
version-pinned runs, schemas, aliases or execution policy. See
[versioned Skill iteration](skill-workflow-versions.md).

Skill compile failures now have opt-in, source-free diagnostic evidence and
fixed CLI/editor recovery wording. The library frontmatter `ValueError` string,
default API refusal and successful compile response stay compatible. Accepted
Skill forms, Workflow DSL, published artifacts and execution authority do not
change. See [compile recovery](skill-input-boundary.md#recover-from-a-compile-refusal).

New Skill compilation isolates top-level identity from nested metadata and
decodes the documented frontmatter string subset. Duplicate keys and unsupported
YAML now fail with a fixed refusal instead of producing ambiguous identity or
text. Parsed IR optional metadata becomes a scoped map; it is not emitted as
Workflow DSL or runtime permission. Existing flat valid Skills and source lines
remain compatible, while formerly misparsed identity/text may change on explicit
recompilation. Review that diff before publication; no stored workflow, alias,
run, DSL schema or execution behavior is rewritten. See
[frontmatter compatibility](skill-input-boundary.md#frontmatter-identity-and-text).

The UI static file server admits only the fixed packaged public resources for
GET/HEAD; arbitrary neighboring files and directory listings are not a supported
UI interface. Load custom workflows/snapshots with the existing file picker.
This tightened delivery boundary does not change the Workflow DSL, graph
write-back, local authoring helpers or authenticated service routes. See
[installed UI](installed-ui.md#fixed-static-asset-boundary).

Explicit Skill step declarations (`<!-- skill2workflow: human_gate -->`) affect
newly compiled drafts. They emit the existing `human_gate` node contract and
add no Workflow DSL fields. Unmarked Skill inference and published artifacts
retain their existing behavior. Invalid reserved declarations are rejected
before an output workflow is written; review the newly compiled draft before
publication.

This document defines the compatibility policy for Workflow DSL `0.1.0`.

The editor's workflow-input review is read-only and its fixed local draft
preflight returns the existing `skill2workflow-workflow-preflight-0.1.0` report.
Ephemeral test input is not embedded into Workflow DSL, LiteGraph, downloads or
runtime state. No schema dialect, execution authority, service trigger semantics
or write-back permission is added. Static hosting retains honest helper-
unavailable feedback. See [draft input review](authoring.md#check-draft-input-in-the-editor).

Quickstart accepts optional `--input` and validates finite, bounded business
data against the compiled contract before initialization. Missing required
input and non-manual connectors before its first human gate now fail before
workspace or token creation. Explicit input uses existing SQLite trigger
admission; omitted valid empty input retains legacy first-run context. The
quickstart result schema, Workflow DSL, general executor and other direct-run
semantics are unchanged. See [input-aware quickstart](quickstart.md#provide-business-input).

Quickstart now requires the existing bounded input/mapping preflight to be
ready before bootstrap, including required mapping sources not enforced by an
input schema. Optional `--dry-run` / Python `dry_run=True` returns the existing
workflow-preflight report without creating a workspace or run. Normal quickstart
result and preflight schemas remain unchanged. This stricter onboarding boundary
does not change general trigger or executor semantics; provider/credential health
and query scalar conversion remain execution-time checks. See
[readiness preview](quickstart.md#preview-before-creating-a-workspace).

Explicit [Skill trigger input declarations](skill-input-contracts.md) emit the
existing top-level `input_schema` on newly compiled drafts. Skills without the
declaration and published artifacts keep their prior behavior. Trigger admission
is unchanged; no schema dialect, default injection, coercion, raw-executor context
validation, implicit approval or new write-back field is added.

Service takeover readiness and recurring dispatch now wait for completed
recovery/reconciliation, rather than lease acquisition alone. This strengthens
the existing recovery contract without changing DSL, state layout, or replay
policy.

Explicit Skill `http` declarations emit the existing HTTP binding on newly
compiled drafts. They default `response_mode` to `metadata`; an explicit `full`
retains the existing opt-in response projection. Published DSL, unmarked Skill
inference, request execution, and legacy retention defaults are unchanged.

Skill `http_assert` declarations affect newly compiled drafts and emit the
existing tool-call/connector contract. They do not reinterpret published DSL
or infer endpoints from prose. Compile review includes these executable checks
in `verification_node_count`; its existing fields and version are unchanged.

The DSL is the execution truth source for `skill2workflow`. Visual graphs, editor state, run overlays, and generated artifacts must be converted back into Workflow DSL before execution or publication.

The read-only HTTP assertion inspector presents stored connector configuration
and source-DSL destinations without changing them. It adds no DSL fields,
execution behavior, credential resolution, or write-back permissions.

Parser support for explicit numbered `Workflow` and `Steps` sections changes
only newly compiled drafts that lack a Checklist section. Checklist precedence
and list formats are unchanged, but examples in supported fences no longer become steps or
guidance in newly compiled drafts, including recognized indented and simple
list/blockquote fences. Conservative matching can exclude later steps when a
fence does not have a matching close. Published Workflow DSL
artifacts are not recompiled or reinterpreted. The DSL schema and execution
semantics are unchanged. Authors should review newly recognized nodes before
publication, especially inferred tool calls and human gates. Multiple populated
fallback process sections now fail compilation instead of producing a generic
review step. See the [Skill input contract](skill-input-boundary.md#explicit-process-sections).

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

`http_assert` is an additional explicit built-in connector for tool-call
nodes. Its bounded JSON response assertions execute on supporting runtimes;
older runtimes reject its unknown connector ID. Existing `http` and inferred
`verification` node behavior is preserved. See [HTTP JSON assertions](http-json-assertions.md).

Within the `0.1.x` release line:

- `schema_version: "0.1.0"` remains readable.
- Existing top-level fields keep their current meaning.
- Existing node ids, edge endpoints, and transition fields keep their semantics.
- Published workflow artifacts remain immutable after publication.
- Published artifact reads verify the registry checksum before promotion or
  execution; missing, unavailable, malformed, or mismatched artifacts fail
  closed with a fixed redacted error.
- The `workflow-artifacts` control-plane report remains additive and follows
  the bounded `skill2workflow-workflow-artifact-report-0.1.0` schema; it does
  not expose Workflow DSL values or mutate published artifacts.
- Structured validation errors keep the `code`, `message`, `path`, and `severity` keys.
- New metadata may be added through additional properties.
- New node types may be added when schema and validator tests document their contract.
- Readers should ignore unknown additional properties unless they explicitly validate that field.
- Optional `input_schema` contracts are additive. Readers that do not enforce
  them may retain the historical open-object behavior, while current
  publishers and trigger boundaries validate the documented bounded subset.
- The local Workflow Bundle manifest `skill2workflow-workflow-bundle-0.1.0`
  is an additive distribution wrapper around one unchanged `0.1.0` DSL
  artifact. Bundle verification checks the digest and revalidates the DSL;
  bundles do not change execution semantics or publication immutability.

Workflow version aliases are control-plane registry metadata, not Workflow DSL
fields. They may point a trigger or schedule at one published immutable
artifact, but promotion never mutates the artifact or changes the DSL schema;
an exact version remains a valid and deterministic target.

The `workflow-diff` output and `--expected-current-version` promotion guard are
additive control-plane interfaces. They do not change Workflow DSL `0.1.0` or
the meaning of an existing published version.

When SQLite is the control-plane backend, the promotion guard, alias metadata
update, and promotion audit append commit in one transaction. This hardening
does not change the artifact contract or add fields to Workflow DSL.

The built-in HTTP connector rejects all `3xx` redirects before issuing a
follow-up request. This is an additive runtime safety boundary that prevents
credential-header replay; existing non-redirect response and error contracts
remain unchanged.

The built-in HTTP connector also ignores ambient proxy environment variables
and opens the configured URL directly. This keeps proxy routing out of the
implicit Workflow DSL execution contract; an explicit reviewed connector is
required for proxy-based egress.

Built-in HTTP request metadata has additive fixed bounds: URL length is capped
at 16,384 UTF-8 bytes, methods at 32 ASCII token bytes, and headers at 64
entries/65,536 UTF-8 bytes. Invalid URL, method, or header metadata fails
before network access with the existing connector failure boundary; existing
valid request behavior remains compatible.

`connector.request.allowed_origins` is an additive exact-origin egress
allowlist. Workflows that omit it retain legacy destination behavior; when
present, the runtime requires the normalized request origin to match one of
the declared entries before credential resolution or network access.

The self-hosted service configuration may additionally define
`runtime.http_allowed_origins` as a service-wide exact-origin upper bound.
This is outside Workflow DSL `0.1.0`, is optional for compatibility, and is
enforced for built-in HTTP execution (including recurring schedules) before
credential resolution or network access. A request must satisfy both lists
when both are present; external connector fixtures remain responsible for
their own provider-specific egress policy.

External connector failure text is also bounded at the executor persistence
boundary: direct connector callers retain the existing immediate result
contract, while failed non-built-in connector results use the fixed
`external connector failed` message in durable run state and retry/audit
events. This is additive runtime protection and does not change Workflow DSL
`0.1.0` fields.

The same durable boundary projects non-built-in connector `output`, `audit`,
input-mapping, and credential summaries to fixed status/presence fields and
bounded identifier lists. Unknown fields and invalid strings are dropped
before persistence; the immediate connector result remains unchanged. This is
also additive runtime protection and does not change Workflow DSL `0.1.0`
fields. Connector manifests may add a bounded, value-free
`audit_contract.durable_metadata` vocabulary for finite string enums, booleans,
and identifier lists; malformed declarations fail before explicit fixture
registration and do not alter the Workflow DSL contract.

Built-in HTTP transport failures use fixed, value-free connector messages:
`http connector request failed` for non-timeout network failures and
`http connector timed out` for timeouts. Request-body serialization failures
use `http connector request.body must be JSON serializable`; underlying URL,
provider-transport, proxy, socket, and exception text is not part of the
durable failure contract. Intentionally retained full response bodies remain
governed by `response_mode`.

SQLite publication and deprecation likewise mutate one registry record and its
audit row atomically. Concurrent publication of distinct immutable versions is
additive; a same-version checksum mismatch remains an immutable-version error.

Known SQLite publication failures may remove only a newly-created artifact
while its registry key is absent and its content still matches the attempted
checksum. The report and cleanup do not provide a filesystem transaction or
JSON cross-process coordination guarantee.

The runtime integrity guard is additive control-plane behavior. It does not
change the Workflow DSL schema or canonical checksum algorithm used at
publication. Existing records without a checksum are not executed
unverified; operators must use the documented state-upgrade and backup/restore
paths or publish a new immutable version.

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
- Node active timeout (`timeout_ms`, bounded to `0..86400000` milliseconds)
- Retry max attempts
- Fixed connector retry backoff in the bounded `0..60000` millisecond range
- Built-in HTTP connector request method, URL, exact-origin allowlist, headers, body, bounded body/query input mapping, response retention mode, and timeout

The editor must not change:

- Workflow node ids
- Edge topology
- Transition targets
- Source metadata
- Guard semantics
- Policy semantics
- Connector id or kind

## Connector Runtime Boundary

Workflow DSL `0.1.0` can carry built-in HTTP connector request metadata on
`tool_call` nodes. The current local runtime supports method, URL, headers,
body, per-request timeout metadata, optional bounded body/query `input_mapping`,
optional `response_mode` (`full` or `metadata`), and optional credential handle
metadata as documented in `docs/connectors.md`. Built-in HTTP request and
UTF-8 response bodies are bounded to 1 MiB at execution time; metadata mode
prevents the response projection from retaining raw headers or body, while the
default full mode preserves the legacy result shape.

`retry.max_attempts`, optional fixed `retry.backoff_ms`, and their
`policies.default_retry` counterparts are policy metadata honored by the
current local executor for connector nodes. `backoff_ms` is bounded to
`0..60000` milliseconds and defaults to zero. `policies.default_timeout_ms` is
a bounded active-execution segment budget: zero disables it, human-gate
waiting pauses it, and an expiry fails closed with
`error_code: "execution_timeout"`. A `tool_call` may declare an optional
`on_fallback`
transition; after connector retries are exhausted, the executor records the
failed node and routes to that explicit edge without automatically invoking
another provider. `policies.workflow_timeout_ms` is a separate bounded global
wall-clock deadline: zero disables it, human-gate waiting consumes it, and an
expiry fails closed with `error_code: "workflow_timeout"`. These fields are
preserved by readers, editable through the visual layer where supported, and
documented in `docs/runtime-policy.md`.

Nodes may additionally carry `timeout_ms`, an additive active-execution window
for that node. Zero or omission disables it; human-gate waiting is paused, and
expiry records fixed `error_code: "node_timeout"` evidence without following a
successor. This field is preserved by older readers that ignore unknown
metadata, while current validators reject values outside `0..86400000`.

Workflow DSL examples and fixtures must not store secrets. They may reference credential handles under connector metadata, but resolved credential values must stay in a local provider boundary outside Workflow DSL, LiteGraph fixtures, trigger input, run state, and audit events. Hosted credential storage, secret redaction, IAM, connector marketplaces, and product-specific SaaS connectors are outside the `0.1.x` built-in connector boundary.

The self-hosted SQLite service additionally sweeps elapsed waiting global
deadlines from the active scheduler lease; standalone executors remain
safe-point only. See `docs/recurring-scheduling.md` for the bounded expiry and
audit-reconciliation boundary.

HTTP `connector.request.input_mapping` is a constrained runtime-copy mapping
contract. It reads only `/input/...` paths from durable run context and writes
either `/body/...` paths into the outbound HTTP request body copy or scalar
values into flat `/query/<name>` URL parameters. `connector.request.response_mode`
is an additive `full`/`metadata` retention choice; metadata mode omits raw
response headers and body from the node result after bounded reading. Header
mapping, URL interpolation, expression syntax, credential mapping, and
product-specific connector packages are outside the current compatibility
boundary.

`input_schema` is a constrained trigger-input contract, not full JSON Schema.
Its root is an object; supported nested types and keywords are documented in
`docs/workflow-dsl-contract.md`. The contract is bounded and rejected at
publication when malformed. Invalid trigger values are rejected before
idempotency claims or execution. Removing or changing an existing contract in
a new immutable workflow version is permitted; changing the meaning of an
already-published version is not.

Connector manifests use the minimum contract documented in `docs/connectors.md`. Workflow DSL `connector.id` and `connector.kind` identify the connector a runtime should use, but Workflow DSL remains authoritative over node identity, transitions, guards, policies, and request metadata. The default runtime and long-running service expose only built-in manifests; local `run`, `resume`, and `bundle-run` may load one operator-supplied fixture through the explicit `--connector-fixture` flag for that process only.

Committed Workflow DSL and LiteGraph example fixtures are checked by `python3 scripts/secret_hygiene.py examples/workflows` for obvious secret-like values. See `docs/credential-boundary.md` for allowed placeholder patterns and the local credential-provider boundary.

## Connector Package Compatibility

Workflow DSL `0.1.0` compatibility is separate from connector package
conventions. Workflow DSL stores connector bindings such as `connector.id`,
`connector.kind`, request metadata, response retention mode, credential handles,
retry policy, and bounded body/query input mapping. A connector package supplies
executable code and a connector manifest version outside the Workflow DSL
schema.

Current connector package conventions use:

- Workflow DSL schema version: `0.1.0`
- Connector manifest version: `skill2workflow-connector-0.1.0`
- Connector execution contract version: `skill2workflow-connector-execution-0.1.0`
- Explicit local loader: `load_external_connector(path)`

The explicit loader's source-file safety boundary is documented in
[`external-connector-loading-boundary.md`](external-connector-loading-boundary.md):
regular non-symlink input, a 2 MiB UTF-8 source limit, no-follow descriptor
loading, device/inode identity checks, and replacement/growth detection. This
does not sandbox executable Python or make fixture loading available to the
service or remote trigger paths.

Changing the connector manifest version or execution contract version is not automatically a Workflow DSL breaking change. It becomes a Workflow DSL compatibility issue only if existing `schema_version: "0.1.0"` workflow artifacts can no longer bind to connector ids/kinds, preserve request metadata, validate, publish, or execute through an explicit runtime configuration.

Connector package conventions remain local-first: explicit file loading and registration are supported for examples and smoke tests, while automatic discovery, package installation, connector marketplaces, OAuth, hosted callbacks, queues, and product-specific connector packages remain outside the current compatibility boundary.

## Consumer Guidance

Browser graph exports explicitly include actual node titles even when LiteGraph
would normally omit a registered default. Pending form edits synchronize before
graph serialization. CLI write-back still requires non-empty titles and rejects
changed identities/topology; no fallback or field-deletion protocol is added.
See [browser graph export](authoring.md#browser-graph-export).

The HTTP browser inspector preserves omitted request properties on an unedited
save. Its explicit reset values (`GET`, `{}`, `null`, and timeout `0`) use the
existing DSL contract. Clearing a declared form control does not request field
deletion; CLI partial-graph write-back behavior and allowlists are unchanged.
See [HTTP inspector editing](authoring.md#http-inspector-editing).

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
