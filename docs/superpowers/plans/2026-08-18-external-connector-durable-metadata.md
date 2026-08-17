# External Connector Durable Metadata Boundary

## Goal

Close the remaining persistence gap after the external connector failure
boundary: an explicitly loaded connector may return a JSON result containing
provider or business strings in `output`, `audit`, input-mapping summaries, or
credential summaries. The immediate `ConnectorRuntime` result remains useful
to the caller, but the executor must persist only a fixed, value-free summary.

## Scope

- apply the projection only when the connector id is not one of the built-in
  connectors;
- preserve the direct runtime result contract for local callers;
- retain the approved Lark/Feishu pilot fields and the local echo key-name
  lists;
- allow only fixed status enums, boolean presence/attempt flags, and bounded
  identifier lists at the durable boundary;
- drop unknown fields and invalid values rather than inventing redacted text;
- cover both in-memory and reloaded JSON/SQLite run state and connector events.

## Exclusions

This does not sandbox imported Python, inspect arbitrary provider payloads,
rewrite user-supplied trigger context, cancel provider I/O, or provide
exactly-once external effects. Built-in HTTP response compatibility remains
unchanged. A connector's immediate result may still contain diagnostics; the
durable boundary is the trust boundary for persisted state and audit events.

## Verification

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_connectors.ConnectorTests.test_external_connector_direct_metadata_keeps_immediate_contract \
  tests.test_executor.ExecutorTests.test_external_connector_metadata_is_projected_before_durable_persistence -v
```
