# External Connector Result Boundary

Loop 173 closes the handoff between an explicitly loaded external connector and
the durable executor.

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

The limit is enforced for explicitly loaded external connectors only. The
built-in HTTP connector keeps its existing 1 MiB request/response payload
contract; its response shape remains unchanged. External connector packages
still own their provider-specific outbound I/O timeouts and payload controls,
but they cannot bypass this final runtime persistence boundary.

## Safety boundary

This contract bounds the result handed to the local executor. It does not
sandbox imported Python code, interrupt an outbound provider call, redact
business values returned by a connector, add remote package installation, or
claim exactly-once external effects. Connector authors must continue to return
compact, value-safe audit and credential summaries and must keep resolved
secrets out of `output`.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest tests.test_connectors -v
```
