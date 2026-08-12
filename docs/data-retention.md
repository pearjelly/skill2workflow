# Data Retention And Disposal

Loop 47 adds an explicit, offline lifecycle path for sensitive run payloads in the self-hosted SQLite state. It does not edit the source directory. Instead, it takes a locked point-in-time snapshot, removes eligible data from a staged copy, verifies the complete state, and atomically publishes a new copy for operator cutover.

This is a data-minimization primitive, not a legal retention policy generator. The operator chooses the UTC cutoff after applying contractual, regulatory, incident-hold, and audit requirements.

## Fixed Policy Contract

The current machine-readable contract is [`schemas/retention-policy-0.3.0.schema.json`](../schemas/retention-policy-0.3.0.schema.json):

```json
{
  "schema_version": "skill2workflow-retention-policy-0.3.0",
  "retention": {
    "delete_before": "2026-01-01T00:00:00Z",
    "terminal_run_statuses": ["completed", "failed", "cancelled", "interrupted"],
    "terminal_dispatch_statuses": [
      "completed",
      "failed",
      "skipped",
      "uncertain"
    ]
  }
}
```

`delete_before` must be an aware ISO-8601 timestamp and is normalized to UTC. Eligibility is strictly earlier than the cutoff; equality is preserved. The status arrays are deliberately fixed and cannot be broadened by configuration. Policy `skill2workflow-retention-policy-0.1.0` remains accepted for compatibility and covers only `completed` and `failed` runs. Policy `0.2.0` adds `cancelled`; policy `0.3.0` adds operator-reviewed `interrupted` runs and their execution tickets.

The retained copy removes:

- `completed`, `failed`, `cancelled`, and `interrupted` runs whose SQLite `updated_at` is before the cutoff under policy `0.3.0`;
- every node event and durable audit event linked by `run_id` to those runs;
- every `run_cancellations` ledger row linked to those runs;
- every `run_executions` ledger row linked to those runs;
- `completed`, `failed`, `skipped`, and `uncertain` dispatch records scheduled before the cutoff.

It preserves:

- `created`, `running`, and `waiting` runs regardless of age; older policies also preserve `interrupted` runs;
- `claimed` dispatches regardless of age;
- terminal runs and dispatches at or after the cutoff;
- published/deprecated workflow records and their immutable artifacts;
- recurring schedule definitions and audit events not linked to an eligible run;
- external authentication and connector credentials, which are already outside state.

Invalid or unparseable stored timestamps are not eligible. This fails closed rather than guessing that a record is old enough to remove.

## Read-only Plan

Stop the service and every other writer, then inspect aggregate eligibility:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli state-retention-plan \
  /etc/skill2workflow/retention.json \
  --state-dir /var/lib/skill2workflow
```

The plan refuses legacy/future layouts and an active scheduler lease. It returns the normalized cutoff, a SHA-256 digest of the normalized policy, and aggregate counts: eligible runs, run events, cancellation and execution ledger rows, linked audit events, terminal dispatches, protected nonterminal runs, and protected claimed dispatches. Record that digest with the approval and verify that apply reports the same value. It never returns workflow, run, schedule, dispatch, customer, or payload values.

The lease check proves that the normal service is stopped. Operators must also quiesce ad hoc CLI writers; the locked snapshot taken during apply is the final point-in-time boundary.

## Create The Retained Copy

Choose a new output path outside the source directory:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli state-retention-apply \
  /etc/skill2workflow/retention.json \
  --state-dir /var/lib/skill2workflow \
  --output-dir /var/lib/skill2workflow-retained
```

The apply path is copy-on-write:

1. Revalidate the current layout and stopped-service boundary.
2. Create and verify a private temporary backup while locking all three databases.
3. Restore that snapshot into private staging.
4. Recompute eligibility against the exact snapshot.
5. Enable SQLite `secure_delete`, delete the fixed eligible rows, and run `VACUUM` on all three databases so removed payload bytes do not remain in the published database pages.
6. Verify table layouts, integrity, workflow artifact checksums, marker, and empty lease state through a second private backup.
7. Atomically rename the retained state into the requested output path.

Any failure before the final rename leaves the requested output absent and the source unchanged. Temporary full copies may have existed on the underlying filesystem; filesystem/SSD secure-erasure guarantees remain an infrastructure responsibility.

## Cutover, Rollback, And Actual Disposal

Before you cut over:

1. Compare apply counts with the approved plan and retention ticket.
2. Point a service configuration at the retained output while keeping it loopback-only.
3. Confirm `/readyz`, authenticated `/metrics`, and one approved non-destructive workflow trigger.
4. Move reverse-proxy traffic only after those checks pass.

The original source directory is the rollback copy because `state-retention-apply` never mutates it. Roll back by stopping the retained service and restarting the old configuration before any irreversible destruction. Writes accepted after cutover are not reconciled back automatically.

Publishing a retained copy alone does **not** complete a deletion obligation: the source directory and any operator-created backup still contain the removed data. After the rollback window and any required legal hold expire, securely destroy the old source, temporary snapshots, and external backups using the guarantees of the storage platform. If policy requires immediate erasure, do not keep a rollback copy or backup beyond that deadline.

## Evidence

Run the real-process drill:

```bash
python3 scripts/retention_smoke.py \
  --work-dir /tmp/skill2workflow-retention-loop47
```

The drill proves active-service refusal, source preservation, old terminal data removal, waiting/claimed preservation, byte-level absence of the old private payload in the retained SQLite files, retained-service readiness, and an authenticated post-cutover trigger. Its evidence contains only booleans and counts.

## Deferred Boundary

Loop 47 does not automate schedules, legal holds, tenant-specific policies, backup expiration, filesystem secure erase, remote object-store deletion, key destruction, workflow-version pruning, recurring-definition deletion, online compaction, or post-cutover reconciliation. Cancellation of actively executing work remains a separate runtime capability.
