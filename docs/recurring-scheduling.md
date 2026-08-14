# Durable Recurring Scheduling

Loop 43 adds persistent interval scheduling to the authenticated self-hosted service. The contract is `skill2workflow-schedule-0.2.0`, stored in SQLite and executed by the same published-workflow trigger boundary used by CLI and webhook runs. Workflow DSL remains the execution source of truth.

This is the supported single-team, single-state-directory scheduler. It is not a distributed queue and it is not exactly-once delivery.

## Schedule Contract

Create a JSON document such as:

```json
{
  "schema_version": "skill2workflow-schedule-0.2.0",
  "schedule": {
    "id": "schedule_hourly_report",
    "workflow_id": "workflow_hourly_report",
    "version": "0.1.0",
    "starts_at": "2026-08-11T00:00:00Z",
    "interval_seconds": 3600,
    "missed_run_policy": "latest",
    "enabled": true
  },
  "trigger": {
    "idempotency_key_prefix": "schedule_hourly_report",
    "input": {
      "report": "hourly"
    }
  }
}
```

`starts_at` must contain a timezone. `interval_seconds` accepts 1 through 31,536,000 seconds. `id` and `idempotency_key_prefix` use a constrained safe-character set. The published workflow version must already exist in the same SQLite state directory.

The runtime derives the trigger source as `recurring-schedule:<schedule.id>` and derives one idempotency key per scheduled occurrence. Callers cannot override the source. Trigger input is persisted in run context, so it must not contain secrets. The canonical UTF-8 JSON input object is capped at 1 MiB, matching CLI, webhook, and one-shot schedule triggers; oversized definitions are rejected before persistence.

The public JSON Schema is [`schemas/recurring-schedule-0.2.0.schema.json`](../schemas/recurring-schedule-0.2.0.schema.json).

## Missed-run Policy

Every schedule declares `missed_run_policy`:

- `latest` advances past all elapsed occurrences and claims only the latest due occurrence. The dispatch record reports how many older occurrences were coalesced.
- `skip` records the whole missed range as `skipped` when more than one occurrence is due. A single exactly-due occurrence still runs normally.

Disabling a schedule is durable. Re-enabling it preserves `next_run_at`, so the selected missed-run policy handles elapsed time explicitly rather than silently resetting the schedule.

## Claim And Recovery Semantics

Dispatch uses claim-before-execute inside a SQLite transaction. The scheduler first writes a unique `(schedule_id, scheduled_for)` dispatch record and advances `next_run_at`; only then does it invoke the workflow. Dispatch records are durable and inspectable with these terminal states:

| Status | Meaning |
| --- | --- |
| `completed` | The trigger returned a durable run and trigger id. |
| `failed` | Invocation raised an error; only the error type is retained. |
| `skipped` | The declared `skip` policy omitted a missed range. |
| `uncertain` | A previous owner lost its lease after claiming and before recording a terminal result. |

On restart, an expired `claimed` record becomes `uncertain`. It is not retried automatically because the external effect might already have happened. An operator must inspect the workflow or connector result before deciding on a new manual action.

Stale-claim recovery reads eligible dispatch rows through the SQLite cursor and
updates each claim as it is read. The long-running service takeover applies a
fixed 100-row batch boundary, renews the lease between full batches, and keeps
each write transaction bounded; a large dispatch ledger therefore cannot turn
restart recovery into one unbounded lease-held write or unbounded source read.
The `uncertain`
transition, no-automatic-retry rule, and return count are unchanged.

This design suppresses duplicate claims in one SQLite state directory, but it is not exactly-once. A crash can leave execution outcome uncertain, and a downstream system can still accept a duplicate if an operator retries. Use provider-native idempotency for effectful connectors and treat `schedule-dispatches` as the recovery ledger.

## SQLite Lease And Standby

All SQLite scheduling paths share one global SQLite lease. The active service renews it while dispatching. A second process using the same state directory may run as a standby, but its `GET /readyz` returns HTTP 503 until it owns the lease. After a graceful active shutdown, the standby acquires the released lease and becomes ready. After a crash, takeover waits for lease expiry and marks stale claims `uncertain` before dispatching new work.

Only the lease owner dispatches. The lease coordinates service processes that share one local SQLite filesystem; it is not a distributed lock for network filesystems or multiple independent databases. Do not run `schedule-run-due` concurrently with the service: the command respects the same lease and fails if another dispatcher owns it.

When manually draining a large backlog, use `schedule-run-due --max-items N`
with `N` from `1` through `100`. The invocation claims and processes at most
that many schedule records, returns a fixed `window` budget summary, and leaves
the remaining due records for a later invocation. Omitting the option retains
the historical complete-batch behavior.

During graceful service shutdown, the dispatcher closes its admission gate before
the process releases the lease. A dispatch that already passed that gate may
finish and record `completed`, `failed`, or `uncertain` evidence; no new
scheduled trigger begins after `draining` is published.

The long-running service scheduler applies the same fixed `1` through `100`
batch boundary on every polling pass. A larger due backlog remains eligible
for the next pass, so claim memory and side-effect admission stay bounded
without changing the CLI's complete-batch compatibility when `--max-items` is
omitted.

## Workflow Deadline Sweep

The active service scheduler also owns a bounded workflow-deadline sweep. About
once per second, it selects waiting runs with a durable
`policies.workflow_timeout_ms` deadline that has elapsed and updates them in the
same SQLite state boundary under `BEGIN IMMEDIATE`. The transition records a
fixed `run_failed` event with `error_code: "workflow_timeout"`, clears the
deadline window, and never resumes the human gate or invokes a successor. A
pending cooperative cancellation wins the race. Audit emission is reconciled
with the same retry-safe missing-event path used by operator actions.

Only the current scheduler lease owner performs the sweep; a standby takes it
over after lease acquisition. Each pass is capped at 256 candidates. The
standalone JSON/SQLite executor still checks deadlines at its own safe points,
but does not run a background sweeper.

## Operator Commands

Add and inspect a recurring schedule using SQLite:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli schedule-add /tmp/hourly.json \
  --state-dir /var/lib/skill2workflow --storage sqlite

PYTHONPATH=src python3 -m skill2workflow.cli schedules \
  --state-dir /var/lib/skill2workflow --storage sqlite

PYTHONPATH=src python3 -m skill2workflow.cli schedules \
  --state-dir /var/lib/skill2workflow --storage sqlite --limit 100

PYTHONPATH=src python3 -m skill2workflow.cli schedule-dispatches \
  --state-dir /var/lib/skill2workflow --storage sqlite \
  --schedule-id schedule_hourly_report

PYTHONPATH=src python3 -m skill2workflow.cli schedule-dispatches \
  --state-dir /var/lib/skill2workflow --storage sqlite \
  --schedule-id schedule_hourly_report --limit 100
```

The optional local `--limit` windows accept `1` through `1000`. Bounded
schedule output uses `skill2workflow-local-schedule-list-0.1.0` and omits
trigger inputs; bounded dispatch output uses
`skill2workflow-local-schedule-dispatch-list-0.1.0` and omits lease owner and
claim-expiry fields. Both retain newest records, include aggregate totals and
status counts, and leave the complete-list compatibility path unchanged when
the flag is omitted. Their schemas are
[`local-schedule-list-0.1.0.schema.json`](../schemas/local-schedule-list-0.1.0.schema.json)
and [`local-schedule-dispatch-list-0.1.0.schema.json`](../schemas/local-schedule-dispatch-list-0.1.0.schema.json).

For SQLite recurring schedules, the bounded inventory reads a transactional
`recurring_schedule_summaries` projection containing only scheduling metadata.
It does not parse complete definitions or trigger input for every historical
schedule. The projection is created and backfilled when an older scheduler
database is opened; complete `list`/`get` and dispatch execution paths retain
their existing full-definition behavior. The authenticated service inventory
route and the local bounded CLI both use this projection.

Pause and resume future dispatch:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli schedule-disable schedule_hourly_report \
  --state-dir /var/lib/skill2workflow --storage sqlite

PYTHONPATH=src python3 -m skill2workflow.cli schedule-enable schedule_hourly_report \
  --state-dir /var/lib/skill2workflow --storage sqlite
```

For deterministic operator testing without the long-running service:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli schedule-run-due \
  --state-dir /var/lib/skill2workflow --storage sqlite \
  --now 2026-08-11T00:00:00Z
```

The legacy `skill2workflow-schedule-0.1.0` format remains a local one-shot JSON schedule for evaluation and compatibility. The long-running service dispatches only the durable `0.2.0` SQLite contract.

## Repeatable Evidence

Run the real-process evidence smoke:

```bash
python3 scripts/recurring_scheduler_smoke.py \
  --work-dir /tmp/skill2workflow-recurring-scheduler-loop43
```

The smoke starts and stops real authenticated service processes and proves recurring dispatch, restart recovery, `latest` coalescing, single-owner readiness, standby takeover, stale-claim `uncertain` recovery, and graceful exit. Its output is compact and contains no credentials, workflow inputs, run ids, trigger ids, or lease-owner ids.

## Deferred Boundaries

Loop 43 does not add cron expressions, calendars, time-zone daylight-saving rules, distributed queues, network-filesystem locking, multi-tenant scheduler isolation, automatic retry of uncertain effects, dispatch retention, or exactly-once execution. Backup/restore, schema migration, bounded observability, and offline terminal-record retention are documented separately; automatic retention scheduling and broader fault-drill evidence remain Production Baseline work.
