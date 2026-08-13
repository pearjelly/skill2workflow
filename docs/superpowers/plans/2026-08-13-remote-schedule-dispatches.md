# Loop 80 Plan: Remote Recurring-Schedule Dispatch Diagnostics

## Goal

Give a self-hosted operator a safe remote view of recent recurring-schedule
dispatch outcomes, including `uncertain` evidence, without exposing scheduler
leases or trigger input.

## Contract

- Add authenticated read-only global and schedule-targeted GET routes.
- Keep the exact response at schema version
  `skill2workflow-recurring-schedule-dispatch-list-0.1.0`.
- Bound storage queries and responses to 100 records and 64 KiB.
- Return fixed status counts and chronological dispatch metadata only.
- Sanitize error types and omit owner, lease, input, and raw record fields.
- Add a protected client/CLI operation with safe schedule-ID validation.
- Preserve low-cardinality telemetry and support-bundle redaction.

## Evidence

The SQLite store test proves bounded global and schedule-filtered queries. The
dashboard test proves the projection does not call an unbounded listing path
and excludes private dispatch fields. Service tests prove Bearer auth, fixed
errors, global/targeted routes, and redaction. Client tests prove exact paths,
auth headers, schema validation, schedule filtering, and the 64 KiB bound. CLI,
telemetry, schema, package, documentation, and full-suite tests complete the
installed operator contract.

## Explicit non-goals

No schedule enable/disable, dispatch claim, retry, replay, provider
reconciliation, RBAC, hosted TLS, or exactly-once execution claim is added.
