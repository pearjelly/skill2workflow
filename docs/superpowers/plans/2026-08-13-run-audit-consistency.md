# Plan: Run Audit Consistency and Atomic Emission

## Goal

Close the production evidence gap between durable run state and the separate
control-plane audit store without changing Workflow DSL authority or replaying
provider side effects.

## Scope

- add one logical audit-batch primitive to JSON and SQLite control stores;
- emit run lifecycle/runtime audit in one transaction per control-plane action;
- compare bounded expected event counts with observed audit counts;
- publish a value-free CLI/schema/operator guide;
- keep the remaining cross-database crash window explicit and diagnostic-only.

## Verification

- injected audit-batch failure leaves no partial run audit rows;
- missing and duplicate audit projections are reported without payload values;
- waiting → resume remains clean;
- CLI and schema contracts are covered;
- full unittest, package, service-boundary, secret-hygiene, compile, and diff
  checks pass before commit.
