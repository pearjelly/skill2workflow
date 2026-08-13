# SQLite Audit Integrity

Loop 65 makes the self-hosted SQLite audit trail verifiable without exposing
event payloads. Each new control-plane audit row stores a SHA-256 chain link:
the canonical event JSON, its SQLite sequence, and the previous digest. The
denormalized query columns (`event_type`, workflow identity, run id, and
timestamp) are checked against that JSON during verification, so a changed
index column cannot silently mislead an operator. The Workflow DSL, run
behavior, and JSON/JSONL evaluation path are unchanged.

## Verify

Stop the service before inspecting or copying state, then run:

```bash
skill2workflow audit-verify \
  --state-dir /var/lib/skill2workflow \
  --storage sqlite
```

From a source checkout, prefix the command with `PYTHONPATH=src python3 -m`.
The command prints only the fixed `skill2workflow-audit-integrity-0.1.0`
result contract:

```json
{
  "schema_version": "skill2workflow-audit-integrity-0.1.0",
  "status": "valid",
  "algorithm": "sha256-chain-v1",
  "event_count": 42,
  "head_digest": "<64 lowercase hex characters>",
  "first_invalid_sequence": 0,
  "reason": ""
}
```

Exit status `0` means the current chain is valid. Exit status `1` means the
chain is invalid or the selected storage is the legacy JSON path. An invalid
result reports only a fixed reason and the first affected sequence; it never
echoes the event, workflow input, connector response, credential, or raw error.
`legacy_unsealed` is expected only before an older current-layout SQLite
database is opened by this version; opening it adds the integrity columns and
seals its existing valid JSON rows in sequence.

The machine-readable contract is
[`schemas/audit-integrity-0.1.0.schema.json`](../schemas/audit-integrity-0.1.0.schema.json).

## Backup And Retention

`backup` and `backup-verify` reject a current-layout SQLite control database
whose chain is invalid. A legacy audit table remains readable for an explicit
upgrade boundary, but it is reported as `legacy_unsealed` until the control
plane opens it. Verified backup/restore preserves the chain. Copy-on-write
retention deliberately rebuilds the chain after deleting eligible audit rows,
so the retained copy remains independently verifiable while the source is
untouched.

The chain is an integrity and ordering signal, not a cryptographic signature:
it detects accidental edits, truncation, row replacement, and ordinary
tampering, but it does not prove who controlled the database or replace
operator-managed authenticated backup and access controls.

## Bounded Local Inspection

Use the optional `audit --limit` flag when inspecting a long-running state
directory:

```bash
skill2workflow audit \
  --state-dir /var/lib/skill2workflow \
  --storage sqlite \
  --run-id run_0123456789ab \
  --limit 100
```

The limit accepts integers from `1` through `1000` and returns the newest
matching events in their original chronological order. Storage applies the
workflow/version/run/event-type filters before the tail bound, so the command
does not load unrelated SQLite audit rows or emit a partial event. Omitting
`--limit` preserves the historical complete-list behavior; use the bounded
form for routine operator inspection and incident triage. This is an output
and memory boundary, not retention or deletion policy.

SQLite chain verification itself also streams the ordered audit rows after a
count-only query, so `audit-verify`, backup validation, and remote audit
diagnostics do not materialize the complete history in memory. Opening a legacy
audit table rebuilds its integrity columns through the same cursor path.

## Boundary

This loop covers one local audit database and bounded, secret-free inspection
when the tail form is selected. It excludes remote audit streaming, signed
attestations, external key management, immutable storage, JSON/JSONL
exactly-once guarantees, and hosted compliance retention policy.

Verification evidence:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_audit_integrity \
  tests.test_retention \
  tests.test_backup \
  -v
```
