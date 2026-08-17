# SQLite Trigger Ledger Response Boundary

Loop 177 closes the remaining durable trigger-ledger document gap after the
SQLite run-state, audit-event, and workflow-registry boundaries. The
`trigger_idempotency.response_json` column now stores one bounded replay
response instead of accepting an arbitrarily large completed-row document.

## Contract

Every completed SQLite trigger-idempotency response is serialized as a compact
JSON object and checked against a fixed **64 KiB** (`65,536` byte) UTF-8 limit
before the pending claim is marked completed. Trigger input, connector
payloads, and business values are never copied into this response by the
existing trigger-response contract.

Claim reads validate a stored response's UTF-8 byte size and JSON-object shape
before returning it to the control plane. Oversized, malformed, non-object, or
invalid UTF-8 values fail closed as an unresolved idempotency outcome; the
workflow is not executed again. A completed row with an empty response is also
rejected. Pending and unresolved rows retain their compact empty response.

Response serialization happens before the SQLite update, so an oversized or
non-JSON response leaves the claim pending and does not partially advance the
ledger. Existing idempotency keys, fingerprints, replay results, conflict
semantics, and the public trigger response schema remain unchanged.

## Safety boundary

The bound protects one durable SQLite replay document and its decode-time
allocation. It is not a total database-size limit, a trigger-input limit, a
connector payload limit, a retention policy, or a guarantee of exactly-once
external effects. An unknown or corrupt completed outcome remains fenced and
requires a new idempotency key.

Focused evidence:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_storage \
  tests.test_control_plane \
  tests.test_sqlite_trigger_ledger_boundary_docs \
  -v
```
