# Interrupted Run Recovery

Loop 49 makes service-process loss explicit instead of leaving a run permanently
`running`. When a replacement service acquires the persisted scheduler lease, it
marks active executions owned by the lost process as `interrupted`. This status
means **unknown external outcome**: a connector request may have reached its
provider even though skill2workflow did not persist a terminal response.

The runtime deliberately performs no automatic retry, successor transition, or
compensation for an interrupted run. Those actions require provider evidence and
an operator decision.

## Execution ownership and fencing

Every service-owned run attempt has a row in the additive SQLite
`run_executions` ledger:

- `owner_id` is the process-unique owner of the scheduler lease;
- `execution_id` is a unique execution ticket for one initial run or resume;
- `active`, `released`, and `interrupted` are the only ticket states;
- claim, run-state persistence, and ticket release occur in the same SQLite
  transaction.

The HTTP control plane and recurring dispatcher share one owner identity. A run
holds an active execution ticket only while it is executing. Entering `waiting`,
`completed`, `failed`, or `cancelled` releases the ticket. Resuming a waiting run
claims a new ticket.

Takeover changes every foreign active ticket and its run state in one transaction.
The ticket then provides fencing: a delayed write from the old process is rejected
and cannot replace `interrupted` with a stale success or failure snapshot. Owner
identities and ticket values are not copied into run JSON, audit events, metrics,
or the control snapshot.

Foreign active-execution rows are read through the SQLite cursor inside that same
transaction and converted one at a time. Recovery therefore avoids materializing
the full execution ledger before fencing runs; the returned recovered-state list
and takeover semantics remain compatible.

The executor rechecks the ticket before every node and connector attempt and
persists `connector_started` before transport. If takeover occurs between two
nodes, the old owner cannot start the successor. A tiny check-to-send interval
still exists before an external request, which is why machine fencing and
exactly-once delivery remain outside this contract.

Ownerless JSON/SQLite CLI runs are outside the service ownership protocol and are
not reclassified. A `waiting` run has no active execution and is also preserved.

## Takeover and graceful shutdown

The service uses the recurring scheduler lease as its single active-owner boundary.
Recovery runs only after a process successfully acquires that lease. A standby
that is still returning `503` readiness cannot recover or mutate the active
process's runs.

During graceful drain, the HTTP listener waits for in-flight request threads before
the scheduler lease is released. This lets the current connector result reach its
normal durable state and prevents a standby from misclassifying healthy work.
After `SIGKILL`, machine loss, or an unrecoverable process exit, the old lease
expires; the standby acquires it, recovers stale schedule claims, and then marks
foreign active executions `interrupted`.

This is crash detection, not exactly-once execution. There is an unavoidable
interval between sending an external request and durably saving its response.

## Operator workflow

Inspect affected runs and compact audit evidence:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli control-runs \
  --state-dir /srv/skill2workflow/state --storage sqlite

PYTHONPATH=src python3 -m skill2workflow.cli control-run <run_id> \
  --state-dir /srv/skill2workflow/state --storage sqlite

PYTHONPATH=src python3 -m skill2workflow.cli audit \
  --state-dir /srv/skill2workflow/state --storage sqlite \
  --run-id <run_id> --event-type run_interrupted
```

For each interrupted run:

1. inspect the last node and connector attempt;
2. query the provider using its idempotency key or provider-side operation record;
3. determine whether the side effect committed, failed, or remains unknown;
4. create a separately reviewed follow-up or compensation workflow when needed;
5. do not edit the authoritative run into a guessed success state.

`cancel-run` rejects an already interrupted run. Cancellation cannot retract an
external request whose outcome is unknown.

Prometheus exposes only the fixed aggregate series
`skill2workflow_runs{status="interrupted"}`. The operator snapshot creates a
critical `interrupted_run` attention item. The control audit event contains only
workflow/run identity, type, and timestamp; it contains no owner, ticket, payload,
credential, or provider response.

## Backup and retention

Verified backup/restore preserves and validates the optional `run_executions`
table. Its exact columns are checked so malformed ownership state fails closed.

After investigation and the applicable retention period, use policy
`skill2workflow-retention-policy-0.3.0`. It adds `interrupted` to the exact terminal
run set and removes the linked execution ticket, events, audit rows, and run from
the copy-on-write retained state. Policies `0.1.0` and `0.2.0` remain accepted for
compatibility and intentionally do not delete interrupted runs.

## Fault drill

Run the real-process drill:

```bash
python3 scripts/interrupted_recovery_smoke.py \
  --work-dir /tmp/skill2workflow-interrupted-recovery
```

The drill lets a local provider commit one side effect, sends `SIGKILL` to the
service before its response is persisted, starts a standby, waits for lease
takeover, and proves: one provider attempt, zero successor attempts, one
`run_interrupted` event and audit record, a fenced execution ticket, preserved
waiting work, and the fixed aggregate metric.

## Explicit boundary

Loop 49 does not provide provider reconciliation adapters, automatic replay,
automatic compensation, distributed worker leasing, machine fencing, connector
idempotency, or exactly-once execution. It turns an ambiguous crash into durable,
observable operator work without silently repeating a possibly committed side
effect.
