# Loop 74: Workflow Artifact Consistency

## Goal

Make the split between immutable workflow files and the control registry
observable and safe after publication failures. SQLite publication must not
leave a known-failure orphan, and operators need a bounded report for crashes
that occur between filesystem and database operations.

## Scope

- Keep Workflow DSL `0.1.0`, registry records, and artifact paths unchanged.
- Add a value-free `workflow-artifacts` CLI report for JSON and SQLite state.
- Detect missing, unsafe, invalid, oversized, mismatched, and orphaned files.
- Bound diagnostic artifact reads to 2 MiB and issue output to 256 records.
- On a failed newly-created SQLite publication, clean up only an unregistered
  artifact whose content still matches the attempted checksum.
- Recheck the artifact inside the SQLite write transaction before inserting a
  registry record, preventing cleanup from racing a waiting publisher.

## Test-first contract

Tests prove clean JSON and SQLite reports, bounded redacted issue output,
missing/checksum/orphan detection, audit-failure cleanup, and retry success.
The CLI and installed package help expose the report command.

## Boundary

This is local diagnostic and known-failure cleanup for one self-hosted,
single-tenant control plane. It is not automatic repair, artifact garbage
collection, a distributed filesystem transaction, a signature, a remote
artifact store, or a JSON multi-process guarantee.
