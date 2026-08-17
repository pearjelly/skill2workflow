# Published Workflow Artifact Read Boundary

Loop 172 closes the remaining unbounded read in the immutable Workflow DSL
artifact path. Published artifacts use a fixed **2,097,152-byte (2 MiB)** UTF-8
envelope. Publication serialization rejects a larger artifact before
installation, and every artifact read uses the same bound.

The shared reader is used by:

- control-plane inspection, promotion, triggering, and execution;
- immutable-artifact rechecks and SQLite publication cleanup; and
- SQLite backup preflight, backup creation, verification, and restore checks.

Each read checks that the path is a regular non-symlink file, opens it with
`O_NOFOLLOW` where available, binds the descriptor to the original device/inode,
reads at most one byte beyond the limit, and rechecks identity and size
after reading. Symlink, replacement, growth, oversized, invalid-UTF-8, and
invalid-JSON inputs fail closed before workflow values reach validation or
execution.

The control-plane error remains the existing redacted
`published workflow artifact unavailable: <workflow_id>@<version>` contract.
Backup and storage paths retain their existing value-free failure behavior.
Workflow DSL shape, canonical checksum computation, immutable version
semantics, SQLite transactions, and backup manifest schema remain unchanged.

This boundary does not split large workflows, encrypt artifacts, make JSON
storage multi-process safe, cap unrelated connector/configuration documents,
or change the complete-list compatibility paths.

## Evidence

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_artifact_io \
  tests.test_control_plane.ControlPlaneTests.test_published_artifact_read_rejects_oversized_file_before_json_decode \
  tests.test_control_plane.ControlPlaneTests.test_publication_rejects_oversized_artifact_before_installation \
  tests.test_backup.StateBackupTests.test_backup_preflight_rejects_oversized_workflow_artifact_before_json_decode \
  -v
```
