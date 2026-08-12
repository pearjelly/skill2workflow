# State Upgrade And Migration

Loop 45 adds an explicit upgrade boundary for the self-hosted SQLite runtime. Fresh state carries the owner-only `state-layout.json` marker defined by `skill2workflow-state-layout-marker-0.1.0`; the current layout is `skill2workflow-sqlite-layout-0.1.0`. Its `service_initialized` lifecycle flag distinguishes a first initialization that may safely create missing components from a previously complete service state where any missing database is treated as corruption. State created before this marker is treated as `skill2workflow-sqlite-layout-legacy-unversioned` when the released `v0.1.0` control and run databases, any later scheduler database, and referenced workflow artifacts pass structural and integrity validation.

The supported upgrade is offline and copy-on-write. It never edits the source state directory in place.

## Preflight

Before preflight, stop the service and every mutating CLI process, then inspect the source:

```bash
skill2workflow state-upgrade-plan \
  --state-dir /var/lib/skill2workflow-old
```

From a source checkout, prefix commands with `PYTHONPATH=src python3 -m skill2workflow.cli`.

Preflight is read-only. It validates the layout marker through a descriptor
bound to the same owner-only regular file identity observed by `lstat`, refuses
symbolic-link or replacement races, and limits the marker to 16 KiB before
UTF-8/JSON decoding. It also checks required SQLite `integrity_check` results,
exact required columns, immutable workflow references and checksums, and the
absence of an active scheduler lease when that database exists. It reports
`upgrade_required` for a valid unversioned legacy state and `current` for the
supported marked layout. Missing control/run state, overexposed-marker,
corrupt, oversized, replaced, or future layout state fails closed.

## Upgrade

Choose two paths that must not already exist and that are outside the source directory:

```bash
skill2workflow state-upgrade \
  --state-dir /var/lib/skill2workflow-old \
  --backup-dir /var/backups/skill2workflow/pre-upgrade-2026-08-11 \
  --output-dir /var/lib/skill2workflow-new
```

The command first creates and verifies an owner-only pre-upgrade backup. For released `v0.1.0` SQLite state that predates durable recurring scheduling, the backup records `scheduler_database_synthesized: true` and adds an empty scheduler database to the snapshot without changing the source. It then restores that snapshot into a private staging directory, writes the current marker, creates a second temporary verification backup of the upgraded copy, and publishes the new state directory with one filesystem rename only after every check passes. A failure leaves the requested output absent, preserves the source byte-for-byte, and retains any successfully created pre-upgrade backup.

The initial migration only converts the known legacy-unversioned form to the current explicit layout identity. It does not rewrite Workflow DSL, run context, audit records, recurring definitions, dispatch records, or immutable workflow artifacts.

## Cutover

1. Keep the old service stopped.
2. Point a copied service configuration at the new absolute `runtime.state_dir`.
3. Mount the authentication token and connector credentials separately; they are not in the backup.
4. Start one new service process.
5. Require `/readyz` to return `200`, then inspect workflow, run, audit, schedule, and dispatch counts.
6. Perform one approved authenticated canary trigger before returning normal traffic.

Do not run old and new binaries concurrently against either directory. Do not copy SQLite files between the two directories after cutover.

## Rollback

Rollback is a directory and binary switch, not a reverse migration:

1. Stop the new service.
2. Preserve the failed new directory for investigation.
3. Start the old binary against the untouched old state directory, or restore the verified pre-upgrade backup and use the old binary.
4. Confirm readiness and perform the same canary checks before returning traffic.

Writes accepted after cutover exist only in the new state. Rolling back to the old directory loses those post-cutover writes unless an operator reconciles them separately. For that reason, keep the validation window short and control ingress during cutover.

The current binary intentionally refuses legacy state and any future layout it does not understand. A future layout requires a separately shipped, forward-only migration step and corresponding evidence; operators must never edit `state-layout.json` to bypass compatibility checks.

## Evidence

Run the real-process drill:

```bash
python3 scripts/state_upgrade_smoke.py \
  --work-dir /tmp/skill2workflow-state-upgrade-loop45
```

The drill starts from the released two-database legacy shape and proves scheduler synthesis, legacy preflight, verified pre-upgrade backup, source immutability, copy-on-write publication, upgraded-service readiness, an authenticated post-upgrade trigger, future layout rejection, and graceful shutdown. Its report contains booleans and counts only.

## Deferred Boundaries

Loop 45 does not provide online schema migration, in-place upgrades, automatic service orchestration, downgrade conversion, post-cutover data reconciliation, cross-filesystem atomic rename, multi-node coordination, arbitrary historical layout support, or application-version package management. Bounded telemetry is documented in [`observability.md`](observability.md), and offline terminal-data disposal in [`data-retention.md`](data-retention.md); broader fault injection and sustained operating evidence remain separate Production Baseline work.
