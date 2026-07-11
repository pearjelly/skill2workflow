# Production Roadmap Reorganization Design

**Date:** 2026-07-11

**Status:** Approved for roadmap planning

## Purpose

Reorganize the public roadmap so it serves two jobs without mixing their levels of detail:

1. explain the capability and delivery evidence already present in the repository; and
2. define a credible path from local evaluation to a production-oriented, self-hosted, single-tenant runtime.

This work changes roadmap documentation and its contract tests only. It does not implement Loops 39-43 or change Workflow DSL, runtime, connector, storage, or CLI behavior.

## Product Direction

The near-term product direction is a self-hosted, single-tenant workflow runtime for one team. The project remains local-first and dependency-light while adding the minimum controls needed for a durable production path.

Workflow DSL remains the execution source of truth. LiteGraph and future UI layers remain editors and views. The roadmap must not imply a multi-tenant SaaS control plane, distributed scheduling, marketplace, or broad live connector platform.

## Roadmap Planning Model

Use a rolling planning window with production-readiness gates:

- The active loop has implementation-ready scope, exclusions, acceptance evidence, and verification commands.
- The next four candidate loops state their objective, dependencies, exit evidence, and explicit boundaries.
- Work beyond the rolling window is grouped by production capability theme and is not assigned loop numbers until evidence justifies selection.
- Release versions describe packaged compatibility and maturity. Loop numbers remain delivery units and are not release promises.

This model preserves the repository's small closed-loop delivery practice without pretending that distant implementation details are settled.

## Roadmap Information Architecture

`ROADMAP.md` will use the following order:

1. **Product Direction** — product goal, Workflow DSL authority, and the self-hosted single-tenant production focus.
2. **Status At A Glance** — release, compatibility line, completed loops, active loop, current maturity, and next decision.
3. **Production Readiness Path** — maturity gates from local evaluation through production baseline.
4. **Active Loop** — the full Loop 39 implementation boundary.
5. **Rolling Loop Queue** — candidate Loops 40-43, with detail decreasing as planning distance increases.
6. **Capability Baseline** — a compact five-layer table describing current capability.
7. **Delivery History** — one-line evidence summaries for Loops 1-38.
8. **Release Direction** — compatibility and maturity intent without assigning every loop to a release.
9. **Deferred Work** — capabilities explicitly outside the current product boundary.
10. **Roadmap Rules** — selection, evidence, compatibility, and maintenance rules.

The active roadmap should be readable before the historical record. Repeated capability lists, repeated Loop 39 prose, and speculative version-by-version feature inventories should be removed.

## Production Readiness Path

### Local Evaluation

**Status:** Achieved.

The repository can compile, validate, publish, trigger, execute, pause, resume, audit, and visualize workflows locally. It includes JSON and SQLite state, controlled connector boundaries, local pilot scenarios, and an out-of-core Lark task connector in dry-run mode.

### Controlled Live Pilot

**Target loops:** 39-40.

This gate requires one explicitly enabled live connector action plus controlled pilot evidence. It does not imply general live SaaS readiness.

### Self-hosted Beta

**Target loops:** 41-43.

This gate requires a long-running service boundary, authenticated ingress, a production credential boundary, durable recurring scheduling, restart recovery, and concurrency-safe dispatch for one self-hosted instance.

SQLite is the minimum production persistence baseline for this gate. JSON and JSONL remain supported for examples, local development, and dependency-light evaluation.

### Production Baseline

**Status:** Directional; not assigned loop numbers.

Candidate evidence includes backup and restore, upgrade and migration policy, cancellation and retention behavior, logs or metrics export, fault drills, contract stability, and sustained real-team operating evidence. These capabilities become numbered loops only after Self-hosted Beta evidence is reviewed.

## Rolling Loop Queue

### Loop 39: Scoped Live Lark Task Connector

Implement only the readiness-approved Lark/Feishu `create_task` live path behind explicit opt-in. Keep dry-run as the default. Exit evidence covers fake transport, credential isolation, persistent idempotency and duplicate prevention, normalized failures, audit redaction, rollback, and dry-run regression.

### Loop 40: Controlled Live Connector Pilot

Exercise Loop 39 through a controlled real-team pilot. Produce a reproducible runbook, redacted run and audit evidence, failure and rollback exercises, and an explicit decision to continue, harden, or defer broader live integration work.

The repository must not commit live credentials or raw live payload evidence.

### Loop 41: Self-hosted Runtime Service Boundary

Define one long-running self-hosted service entry point with configuration validation, health and readiness checks, graceful shutdown, and state continuity after process restart. Keep the scope single-instance and single-tenant.

### Loop 42: Authenticated Ingress And Production Credentials

Reject unauthenticated requests by default on the production service path. Add a minimal single-team authentication boundary, production credential-handle resolution, compact security audit evidence, and a documented external TLS termination boundary.

This loop does not introduce multi-tenant RBAC, an OAuth platform, or a hosted secret manager.

### Loop 43: Durable Recurring Scheduling And Safe Dispatch

Add persistent recurring schedules with restart recovery, a defined missed-run policy, durable dispatch records, and lease or locking semantics appropriate to one SQLite-backed service instance.

The contract should state delivery semantics precisely. Duplicate suppression relies on persisted dispatch state and workflow or connector idempotency; the roadmap must not claim exactly-once execution.

## README Boundary

`README.md` will contain only a compact roadmap summary:

- current maturity;
- completed loop range;
- active Loop 39 priority;
- the self-hosted single-tenant production direction; and
- a link to `ROADMAP.md` for full status and planning detail.

It will not duplicate the capability baseline, complete delivery history, candidate-loop acceptance criteria, or deferred-work catalog.

## Documentation Contracts And Verification

Existing roadmap contract tests rely on key Loop 35-39 wording. The reorganization will preserve those behavioral assertions or update the tests in the same change when headings and phrasing intentionally move.

Add focused documentation assertions for:

- the self-hosted single-tenant production direction;
- all four production-readiness gates;
- candidate Loops 40-43 and their status;
- SQLite as the production persistence baseline while JSON remains available for evaluation;
- the single-instance boundary and the absence of exactly-once claims; and
- consistency between the README roadmap summary and `ROADMAP.md`.

Verification will include:

```bash
PYTHONPATH=src python3 -m unittest tests.test_live_connector_readiness tests.test_product_connector_pilot_roadmap tests.test_first_product_connector_candidate_docs -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

## Maintenance Rules

- Update `ROADMAP.md` whenever a loop is selected, completed, or explicitly deferred.
- Select only one active loop.
- Review evidence from the active loop before promoting the next candidate.
- Keep implementation detail in the matching plan or capability guide.
- Keep the next four loops inside the rolling window; keep more distant work thematic and unnumbered.
- Require tests first for parser, compiler, validator, executor, connector, storage, or CLI behavior changes.
- Preserve Workflow DSL compatibility unless a separately approved contract change defines migration behavior.

## Explicit Non-goals

- Implementing any runtime capability from Loops 39-43
- Committing credentials or live customer data
- Multi-tenant SaaS architecture
- Distributed scheduling or worker coordination
- Full RBAC or IAM
- Connector marketplace, automatic installation, or broad connector catalogs
- OAuth and token-refresh platform work
- A promise that candidate loop numbers or release timing cannot change after evidence review
