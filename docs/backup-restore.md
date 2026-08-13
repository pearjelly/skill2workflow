# Verified Backup And Restore

Loop 44 adds an operator-controlled, verified backup and restore path for the self-hosted SQLite runtime. A backup uses the manifest contract `skill2workflow-state-backup-0.1.0`, records either the current `skill2workflow-sqlite-layout-0.1.0` identity or the recognized `skill2workflow-sqlite-layout-legacy-unversioned` source identity, and contains the three production databases plus every immutable workflow artifact referenced by the control database. Current-layout backups also contain the owner-only `state-layout.json` marker.

This is an offline application-consistent snapshot. It is not a hot-backup, replication, retention, or disaster-recovery service.

## Before Taking A Backup

Stop the service gracefully and wait for the process to exit. Do not rely on traffic removal alone: the scheduler heartbeat remains a writer while the process is alive.

```bash
kill -TERM <skill2workflow-service-pid>
wait <skill2workflow-service-pid>
```

The backup command rejects an unexpired scheduler lease. It then holds write locks on `scheduler.sqlite3`, `control.sqlite3`, and `runs.sqlite3` while copying them. These locks exclude accidental concurrent CLI writes during the snapshot, but the supported operational contract remains offline: stop the service and do not run mutating CLI commands until backup completion.

## Create And Verify

The destination must not already exist and must be outside the runtime state directory:

```bash
skill2workflow backup \
  --state-dir /var/lib/skill2workflow \
  --output-dir /var/backups/skill2workflow/2026-08-11
```

Always verify a backup before copying it to long-term storage:

```bash
skill2workflow backup-verify \
  --backup-dir /var/backups/skill2workflow/2026-08-11
```

From a source checkout, prefix each command with `PYTHONPATH=src python3 -m skill2workflow.cli`.

Creation is staged in a sibling temporary directory and renamed only after validation succeeds. Failure removes the staging directory and never publishes a partial backup.

## Backup Contents

The backup contains only:

- `control.sqlite3`: published version registry and compact audit events;
- `runs.sqlite3`: durable run state, run events, and the additive cancellation request ledger when present;
- `scheduler.sqlite3`: recurring definitions and dispatch records;
- the exact `workflows/**/*.json` artifacts referenced by `control.sqlite3`;
- `manifest.json` using [`schemas/state-backup-manifest-0.1.0.schema.json`](../schemas/state-backup-manifest-0.1.0.schema.json).

Each declared file has a byte length and lowercase SHA-256 digest. Verification rejects unknown fields, an unsupported or mismatched state layout marker, duplicate or unsafe paths, undeclared files, missing files, size or digest mismatches, invalid workflow JSON, workflow/control checksum disagreement, missing or incompatible core table columns, a malformed optional `run_cancellations` table, an invalid current SQLite audit chain, and any SQLite `integrity_check` result other than `ok`.

Scheduler lease rows are cleared in the snapshot. Durable dispatch claims are preserved; after restore, the scheduler applies its normal stale-claim `uncertain` recovery semantics. A recognized legacy `v0.1.0` source without `scheduler.sqlite3` is still backed up safely: the manifest sets `scheduler_database_synthesized: true` and the snapshot contains a new empty scheduler database while the source remains untouched.

Service configuration, Bearer token files, mounted credential directories, unrelated state-directory files, local JSON schedules, and legacy JSON/JSONL state are not copied. In particular, credentials are not included. Back up and restore external secrets through the operator's secret manager, then rotate them according to policy.

## Restore

Verify first, then restore into a path that must not already exist:

```bash
skill2workflow backup-verify \
  --backup-dir /var/backups/skill2workflow/2026-08-11

skill2workflow restore \
  --backup-dir /var/backups/skill2workflow/2026-08-11 \
  --state-dir /var/lib/skill2workflow-restored
```

Restore revalidates the complete backup before creating a staging directory. It copies only manifest-declared files, reruns database integrity and workflow-reference checks, and atomically renames the staging directory into place. A failed restore leaves the requested destination absent.

When present, the additive `run_executions` ledger is preserved and its exact
column layout is validated. This keeps `active`, `released`, and `interrupted`
execution tickets intact across restore and rejects malformed crash-recovery state.

Point the service configuration at the restored absolute `runtime.state_dir`, mount fresh authentication and connector credential files, start one service process, and require `GET /readyz` to return HTTP 200 before returning traffic. Keep the original state directory untouched until restored workflow, run, audit, schedule, and dispatch counts are reviewed.

If the restored manifest reports `skill2workflow-sqlite-layout-legacy-unversioned`, the current service will refuse it. Follow [`upgrade-migration.md`](upgrade-migration.md) to create a verified current-layout copy; do not hand-edit the marker.

## Security And Retention

Backup directories are owner-only (`0700`) and all files are owner-only (`0600`). Verification refuses a backup that became readable by group or others.

Although credentials are excluded, run context, workflow definitions, audit metadata, and connector results can contain confidential business data. Store backups outside the application host, encrypt them with an operator-managed mechanism, control access separately from the runtime account, define retention and deletion policy, and test recovery regularly. The runtime does not encrypt, upload, rotate, or delete backup sets.

Do not edit `manifest.json` or any backed-up file. SHA-256 detects accidental or untrusted modification but is not an authenticity signature; protect the whole backup with access controls and authenticated encryption.

## Recovery Drill Evidence

Run the real-process drill:

```bash
python3 scripts/backup_restore_smoke.py \
  --work-dir /tmp/skill2workflow-backup-restore-loop44
```

`backup_restore_smoke.py` proves active-lease rejection, pre-restore verification, point-in-time behavior, restored service readiness, an authenticated post-restore trigger, tamper rejection, credential exclusion, and graceful shutdown. Its output contains booleans and counts only; it excludes paths, run ids, trigger ids, credentials, and workflow inputs.

## Deferred Boundaries

Loop 44 does not provide online hot backup, incremental backup, compression, remote upload, encryption, signing, retention automation, scheduled backup jobs, point-in-time WAL recovery, network-filesystem coordination, or multi-node replication. State compatibility is documented in [`upgrade-migration.md`](upgrade-migration.md), bounded telemetry in [`observability.md`](observability.md), and offline terminal-data disposal in [`data-retention.md`](data-retention.md); backup-expiration automation, broader fault drills, and sustained operating evidence remain Production Baseline work.
