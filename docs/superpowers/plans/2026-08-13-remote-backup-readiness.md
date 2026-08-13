# Loop 82 Plan: Remote Backup Readiness

## Goal

Make the existing offline SQLite backup procedure easier to operate from a
remote control boundary without adding remote backup transport or mutation.

## Contract

- Add authenticated `GET /api/v1/backup-readiness` with no request body.
- Reuse the existing read-only backup validation and expose a fixed
  `skill2workflow-backup-readiness-0.1.0` report.
- Report active scheduler lease, state layout, database/artifact counts, and
  fixed blocking reasons only.
- Bound responses to 16 KiB and keep the endpoint readiness-independent.
- Add protected client/CLI, fixed telemetry, schema, docs, package evidence,
  and support-bundle redaction.

## Evidence

Service tests prove Bearer auth, active-lease blocking, and fixed output.
Client tests prove exact path, token header, schema validation, and response
limits. CLI, telemetry, schema, package, documentation, and full-suite tests
complete the operator contract.

## Explicit non-goals

No remote backup creation, upload, encryption, retention, restore, service
shutdown, scheduler mutation, or exactly-once backup claim is added.
