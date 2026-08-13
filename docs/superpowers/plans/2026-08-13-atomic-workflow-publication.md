# Loop 73: Atomic Workflow Registry Mutations

## Goal

Make the SQLite control-plane publication lifecycle safe under concurrent
operators. Publishing immutable versions must not use stale full-index writes,
and registry state must not commit without the corresponding audit evidence.

## Scope

- Keep the existing `publish`, `deprecate`, and exact Workflow DSL `0.1.0`
  contracts.
- Create each published artifact with exclusive immutable installation so a
  concurrent writer cannot replace its bytes.
- Insert one SQLite workflow registry record and its `workflow_published`
  audit row in one `BEGIN IMMEDIATE` transaction.
- Make matching same-version publication retries idempotent and reject a
  checksum mismatch with the existing immutable-version error.
- Update one deprecation record and append `workflow_deprecated` in one
  transaction, preserving aliases and statuses on audit failure.
- Keep JSON as the dependency-light local evaluation backend without claiming
  cross-process coordination.

## Test-first contract

The control-plane tests start independent SQLite operators concurrently and
prove that distinct versions both remain published, same-version matching
publishes produce one audit row, and different content for one version fails
closed. A publication/deprecation interleaving preserves both mutations, and
injected audit failures roll back registry changes so a retry remains safe.

## Implementation

`LocalControlPlane` uses an exclusive temporary artifact link before delegating
SQLite registry work. `SqliteControlStore.publish_workflow_record` reads the
target row inside a write transaction, inserts only the missing record, and
appends its audit chain row before commit. `deprecate_workflow_record` updates
only the selected `record_json` and denormalized status fields, then appends its
audit row in the same transaction. Existing full-index JSON writes remain only
on the local evaluation path.

## Evidence

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_concurrent_publication_preserves_each_version_and_audit \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_concurrent_same_version_publication_is_idempotent \
  tests.test_control_plane.ControlPlaneTests.test_concurrent_different_content_same_version_fails_closed \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_publication_rolls_back_registry_when_audit_append_fails \
  -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Boundary

This is one local SQLite registry transaction for one self-hosted,
single-tenant control plane. It is not a distributed lock, JSON multi-process
coordinator, remote artifact store, signature, approval policy, canary or
rollback system, or exactly-once provider guarantee.
