# Audit Event Boundary

Loop 175 closes the remaining local audit persistence gap after the run-state
boundaries. Both supported control-plane stores now treat one audit event as a
bounded UTF-8 document instead of allowing a JSONL line or SQLite
`payload_json` value to grow without limit.

## Contract

Every audit append serializes a JSON object and enforces a fixed **1 MiB**
(`1,048,576` byte) UTF-8 limit before the write transaction or JSONL append
starts. A batch validates every event before writing any member, so an
oversized event cannot leave a partial logical emission behind.

JSONL reads use a bounded line window and SQLite reads check the stored UTF-8
size before JSON decoding. Oversized, malformed, or non-object payloads fail
closed with a `ValueError`; the SQLite audit-integrity verifier reports the
existing payload-invalid result contract without returning the payload.

The bound applies to local audit persistence and import. It does not change
the event fields, filter semantics, chronological output, audit hash-chain
algorithm, remote redacted event projection, or the existing complete-list
compatibility path.

## Safety boundary

Audit events remain compact operational metadata. Workflow inputs, connector
responses, credentials, and provider payloads must stay outside audit events;
this size ceiling is a memory and durable-storage guard, not a redaction
substitute, retention policy, signature, or exactly-once guarantee.

Focused evidence:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_storage \
  tests.test_audit_integrity \
  tests.test_audit_event_boundary_docs \
  -v
```
