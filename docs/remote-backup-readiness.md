# Remote Backup Readiness

Loop 82 adds a read-only preflight for the existing offline SQLite backup
procedure. It lets an operator confirm the state layout, referenced artifact
count, and scheduler lease condition before stopping the service for a backup.
It does not create, upload, or retain a backup remotely.

## Route and CLI

```text
GET /api/v1/backup-readiness
Authorization: Bearer <single-team-token>
```

The request must not include a body. The route is authenticated, bounded, and
read-only. It is available while the service is starting, ready, draining, or
standby when the SQLite state can be inspected; it never acquires the
scheduler lease and never changes scheduler state.

Use the protected client:

```bash
skill2workflow service-backup-readiness \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

## Fixed contract

Responses use
`skill2workflow-backup-readiness-0.1.0`, defined by
[`schemas/backup-readiness-0.1.0.schema.json`](../schemas/backup-readiness-0.1.0.schema.json).
The report contains only:

- current/legacy SQLite layout identity and the fixed database count;
- the number of referenced immutable workflow artifacts;
- whether a scheduler lease is active;
- whether the scheduler database was synthesized for recognized legacy state;
- `backup_allowed` and a fixed blocking reason list.

`status: "blocked"` with `blocking_reasons: ["active_scheduler_lease"]`
means the service must be stopped before running the existing local
`backup` command. `status: "ready"` means this preflight found no active
lease; it is not a claim that a later backup cannot fail if the state changes.
The local backup command remains authoritative and rechecks all databases and
artifact checksums while taking its locks.

The remote response is capped at 16 KiB. Authentication, body, and state
failures use fixed `401`, `400`, and `503` responses. The stable support-bundle
0.1.0 projection intentionally omits this route's counter.

## Safe operating sequence

1. Fetch the report and record the schema version and status.
2. If blocked, drain and stop the service through the host supervisor.
3. Run the documented local [`backup`](backup-restore.md) command and verify
   its manifest before moving the copy off-host.

The endpoint does not expose paths, database contents, workflow values,
credentials, lease owner identities, or backup bytes.

## Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_backup_readiness_is_authenticated_and_reports_active_lease \
  tests.test_service_client.ServiceClientTests.test_backup_readiness_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_backup_readiness_command_prints_report \
  -v
```
