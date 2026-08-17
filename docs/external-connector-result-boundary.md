# External Connector Result Boundary

Loop 173 introduced the bounded JSON handoff between an explicitly loaded
external connector and the durable executor. Loop 203 closes the remaining
metadata projection gap at that same boundary.

## Contract

After the connector returns its normalized result, the runtime serializes the
result as compact UTF-8 JSON with `allow_nan=false`. The complete normalized
envelope must be at most **1 MiB** (`1,048,576` bytes). This envelope includes
the connector status and reference, `output`, optional error text, and compact
credential, input-mapping, and audit summaries.

Results that are not JSON-serializable, contain non-finite numbers, exceed the
bound, or cannot be round-tripped through standard JSON fail as a fixed
`ConnectorExecutionError` before the result is attached to durable run state.
The accepted result is reconstructed from that JSON representation, so custom
Python objects cannot cross into run state or SQLite.

If an external executor raises an ordinary Python exception instead of the
declared `ConnectorExecutionError`, the runtime converts it to the fixed
`external connector execution failed` error before the executor sees it. The
underlying provider, URL, socket, traceback, and exception text therefore do
not enter connector results or durable state. The direct runtime result keeps
the existing explicit `ConnectorExecutionError` and returned-error contract
for callers that need immediate diagnostics, but the executor applies a
second durable boundary: any failed result from a non-built-in connector is
stored and emitted in retry/audit events only as the fixed
`external connector failed` message. Loop 203 adds a second projection for
successful and failed external results before they are persisted: `output` and
`audit` retain only the fixed status/presence vocabulary and bounded identifier
lists used by the approved fixtures; `input_mapping` retains only its status
and input-key names; and `credentials` retains only its status and bounded
handle names. Unknown fields, invalid enum values, nested objects, and strings
outside the fixed vocabulary are dropped. The direct runtime result remains
unchanged for callers that need immediate diagnostics.

The limit is enforced for explicitly loaded external connectors only. The
built-in HTTP connector keeps its existing 1 MiB request/response payload
contract; its response shape remains unchanged. External connector packages
still own their provider-specific outbound I/O timeouts and payload controls,
but they cannot bypass this final runtime persistence boundary.

## Safety boundary

This contract bounds the result and exception handoff to the local executor,
makes external failure text value-free, and projects persisted metadata to a
fixed value-free vocabulary. It does not sandbox imported Python code,
interrupt an outbound provider call, rewrite user-supplied trigger context,
add remote package installation, or claim exactly-once external effects.
Connector authors should still keep direct results compact and avoid placing
resolved secrets in `output`; the durable executor boundary is the final
protection for persisted run state and audit events.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest tests.test_connectors -v
```
