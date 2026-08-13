# Loop 72: Atomic Workflow Alias Promotion

## Goal

Make the reviewed release guard a real production concurrency boundary for the
SQLite-backed self-hosted control plane. Two operators that both observed the
same current alias target must not both commit a promotion, and a successful
alias move must not become durable without its promotion audit evidence.

## Scope

- Keep the existing `promote` CLI and `--expected-current-version` contract.
- Move the SQLite compare-and-swap check and alias metadata update into one
  `BEGIN IMMEDIATE` transaction.
- Append the `workflow_promoted` audit row in that same transaction so rollback
  covers both registry and audit state.
- Preserve JSON as the dependency-light local evaluation backend without
  claiming cross-process transaction coordination.
- Preserve Workflow DSL `0.1.0` and immutable published artifacts.

## Test-first contract

The control-plane regression starts two independent SQLite operators at the
same expected version. Exactly one promotion succeeds; the other receives the
fixed `workflow alias precondition failed` error. The test also verifies that
the winning alias is unique, there are exactly two promotion audits including
the bootstrap promotion, and `audit-verify` remains valid.

## Implementation

`LocalControlPlane.promote_workflow` retains artifact checksum verification,
then delegates SQLite alias mutation to `SqliteControlStore`. The store takes a
write transaction, rereads the registry inside the transaction, checks the
expected published alias target, updates only affected `record_json` rows, and
appends the audit chain row before commit. A precondition failure raises before
any registry or audit mutation.

## Evidence

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_promotion_cas_is_atomic_across_concurrent_operators \
  -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke-loop72
python3 scripts/service_boundary_smoke.py --work-dir /tmp/skill2workflow-service-boundary-loop72
```

## Boundary

This is a local SQLite transaction for one self-hosted, single-tenant control
plane. It is not a distributed lock, JSON multi-process coordinator, approval
policy, canary rollout, automatic rollback, release signature, or exactly-once
provider guarantee.
