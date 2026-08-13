# Run Audit Consistency

Loop 75 adds a bounded diagnostic for the split between durable run state and
the control-plane audit database. A run is persisted in `runs.sqlite3`, while
its operator evidence is persisted in `control.sqlite3`; a process can stop
between those transactions. The diagnostic compares the event projection
expected from each run state with the audit events actually present.

Run it against the private service state directory:

```bash
skill2workflow audit-consistency \
  --state-dir /var/lib/skill2workflow \
  --storage sqlite
```

To inspect one run:

```bash
skill2workflow audit-consistency \
  --state-dir /var/lib/skill2workflow \
  --storage sqlite \
  --run-id run_...
```

The command prints the `skill2workflow-run-audit-report-0.1.0` contract from
[`schemas/run-audit-report-0.1.0.schema.json`](../schemas/run-audit-report-0.1.0.schema.json).
It is bounded to 256 runs and 64 event-type counters per run. It reports only
run identifiers, workflow identity, status, and event counts; it never prints
workflow instructions, trigger input, connector output, credentials, or raw
errors. When more than 256 runs exist, the top-level status is `attention` and
`summary.truncated` is true; use `--run-id` to inspect a specific run.

`missing` means the durable run state implies an audit projection that is not
present. `duplicate` means an expected event type appears more often than the
projection permits. `unexpected` means the audit contains an event type that
cannot be derived from the current run state. An `attention` result is an
operator signal, not permission to replay the workflow or a connector.

The current `waiting` and `interrupted` states are each represented by their
durable lifecycle event (`human_gate_waiting` or `run_interrupted`); the report
does not count the status field a second time. A waiting run and a recovered
interrupted run therefore report `clean` when their single terminal projection
is present. This diagnostic remains read-only and does not infer provider
outcomes.

Loop 75 also emits each run lifecycle/runtime audit batch in one control-store
transaction. SQLite therefore cannot commit `run_started` while losing the
terminal event because a later append failed. The cross-database boundary
still exists: the diagnostic must be run after restart or before incident
closure when a process may have stopped after run-state persistence. It never
repairs, deletes, or rewrites audit history.

## Evidence

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_published_run_audit_batch_is_all_or_nothing \
  tests.test_control_plane.ControlPlaneTests.test_run_audit_consistency_report_detects_missing_and_duplicate_events \
  tests.test_control_plane.ControlPlaneTests.test_run_audit_consistency_report_is_clean_for_waiting_and_resumed_run \
  tests.test_cli.CliTests.test_audit_consistency_command_reports_run_evidence_without_values \
  -v
```
