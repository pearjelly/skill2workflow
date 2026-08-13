# Loop 63: Bounded Active Execution Timeout

**Status:** Complete.

**Goal:** Make the existing `policies.default_timeout_ms` field enforce a
bounded execution safety boundary instead of remaining inert metadata.

## Contract

- `policies.default_timeout_ms` accepts an integer from `0` through `86400000`
  milliseconds. `0` disables the boundary.
- The budget applies to one active execution segment and is checked before
  each node and after a connector returns.
- The active deadline is persisted with the run state. A malformed persisted
  deadline fails closed as `execution_timeout`.
- A timeout ends the run as `failed`, records fixed `error_code:
  "execution_timeout"`, and does not retry or expose connector output that
  returned after the deadline.
- Human-gate waiting clears the active deadline. Resuming the gate starts a
  fresh active segment, so operator review time does not consume execution
  budget.
- An outbound connector call is never forcefully interrupted; its result is
  evaluated at the next safe point.

## Exclusions

This loop does not add global wall-clock workflow deadlines, human-gate expiry,
delayed retry backoff, background workers, forceful provider cancellation, or
exactly-once side-effect guarantees. JSON and SQLite use the same executor
semantics, while SQLite remains the production persistence baseline.

## Evidence

The public policy is documented in [`docs/runtime-policy.md`](../../runtime-policy.md),
the DSL compatibility note, and the versioned workflow schema. Compiler tests
reject invalid bounds; executor tests cover safe-point timeout, persisted fixed
failure evidence, and paused human-gate timing. Full-suite and package checks
 remain release gates.
