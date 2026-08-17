# SQLite Workflow Registry Record Boundary

Loop 176 closes the remaining control-plane registry gap after the JSON index,
published artifact, SQLite run-state, and audit-event boundaries. The SQLite
`workflow_versions.record_json` column now stores one bounded UTF-8 JSON object
instead of accepting an arbitrarily large registry document.

## Contract

Every SQLite workflow registry record is serialized and checked against a fixed
**2 MiB** (`2,097,152` byte) UTF-8 limit before insertion or update. The limit
matches the immutable published Workflow artifact ceiling, so valid published
metadata cannot exceed the artifact boundary merely because it is stored in
the registry.

Complete registry loads, direct version reads, alias resolution, streaming
diagnostics, snapshots, startup import, publication, deprecation, and alias
promotion all use the same encode/decode helpers. Reads check the byte size
before JSON decoding and reject oversized, malformed, non-object, or invalid
UTF-8 values with a stable `ValueError`.

`save_index` serializes every replacement record before deleting any existing
rows. A bad record therefore cannot leave a partially replaced SQLite registry;
alias updates likewise serialize all changed records before the update batch.
Record fields, version lookup, alias semantics, artifact checksums, and the
complete-list compatibility API remain unchanged.

## Safety boundary

The bound protects one durable SQLite registry document and its decode-time
memory allocation. It is not a total database-size limit, a retention policy,
an artifact signature, a secret-redaction mechanism, or a guarantee of exactly
once publication. Workflow inputs, connector responses, credentials, and
provider payloads remain outside registry metadata.

Focused evidence:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_storage \
  tests.test_sqlite_workflow_record_boundary_docs \
  -v
```
