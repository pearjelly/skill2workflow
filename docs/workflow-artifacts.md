# Workflow Artifact Consistency

Loop 74 adds a bounded, read-only check for the file and registry halves of
published workflow versions. It is useful after a crash, an interrupted
publication, a manual state copy, or a failed backup preflight.

The diagnostic uses the same 2 MiB artifact envelope enforced by publication,
execution, and verified backup paths. The descriptor-bound read contract is
documented in [`published-artifact-read-boundary.md`](published-artifact-read-boundary.md).

Run it against the self-hosted state directory:

```bash
skill2workflow workflow-artifacts \
  --state-dir /var/lib/skill2workflow \
  --storage sqlite
```

The command prints the `skill2workflow-workflow-artifact-report-0.1.0`
contract from [`schemas/workflow-artifact-report-0.1.0.schema.json`](../schemas/workflow-artifact-report-0.1.0.schema.json).
It reports counts and at most 256 value-free issue records. It never prints
workflow titles, instructions, connector requests, input values, checksums, or
credential material.

Issue kinds are:

- `missing`: a registry record points at an absent artifact;
- `unsafe_reference`: the registry path is not a relative `workflows/*.json`
  path;
- `unsafe_artifact`: an artifact or one of its path components is a symlink or
  not a regular file;
- `invalid_json`: the artifact cannot be decoded as JSON;
- `oversized`: the artifact exceeds the 2 MiB diagnostic read bound;
- `checksum_mismatch`: the artifact does not match its registry checksum; and
- `orphaned`: a JSON artifact exists under `workflows/` without a registry
  record.

Publication creates the artifact with exclusive installation. For SQLite, if a
new artifact is followed by a known failure in registry or audit persistence, cleanup runs
under the same database write lock and removes it only while its registry key
is absent and its content still matches the attempted checksum. A concurrent
publisher rechecks the artifact while holding that lock, so cleanup cannot
leave a new registry row pointing at a removed file.

The report is diagnostic. It counts the complete issue set but retains only the
fixed issue window, so issue memory does not grow with the number of failures.
On the production SQLite path, registry rows are streamed and filesystem
artifacts are checked one at a time against the registry; the diagnostic does
not materialize the complete registry or artifact path set. JSON remains the
dependency-light evaluation path and keeps its existing compatibility behavior.
It does not delete historical artifacts, repair a registry, rewrite a checksum,
or make JSON storage multi-process safe. Stop the service, preserve the private
state, and follow the backup/restore or migration procedure before manually
repairing any `attention` result.

## Evidence

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_workflow_artifact_report_is_bounded_and_finds_registry_and_orphan_gaps \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_workflow_artifact_report_streams_registry_without_loading_index \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_publication_rolls_back_registry_when_audit_append_fails \
  tests.test_cli.CliTests.test_workflow_artifacts_command_reports_bounded_consistency_without_values \
  -v
```
