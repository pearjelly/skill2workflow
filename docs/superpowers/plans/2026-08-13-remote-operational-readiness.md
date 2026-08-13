# Loop 93 Plan: Remote Operational Readiness

## Goal

Give self-hosted operators one protected, value-free report for the existing
service, artifact, audit, and backup readiness checks without adding a new
mutation or pretending the independent SQLite reads are atomic.

## Contract

- Add authenticated `GET /api/v1/operational-readiness` with no request body.
- Aggregate fixed lifecycle, artifact, audit-chain, and offline-backup statuses.
- Keep active-lease backup blocking as an expected maintenance note while a
  running service remains otherwise ready.
- Bound the response to 16 KiB and preserve readiness-independent reads.
- Add protected client/CLI, fixed telemetry, schema, docs, package evidence,
  and support-bundle redaction.

## Explicit non-goals

No lifecycle mutation, service drain, backup/restore, retention apply, repair,
atomic cross-database snapshot, raw logs, credentials, paths, RBAC, or hosted
monitoring is added.
