# Remote Backup Inventory

Loop 160 adds a protected, read-only view of the configured offline backup
parent. It closes the operator gap between “the service is currently able to
take a backup” and “the most recent backup sets are still valid and within the
expected size window.”

The service bootstrap creates an owner-only `backups/` directory and records
its absolute path as the optional `runtime.backup_parent_dir` setting. Existing
hand-written `service-0.2.0` configurations remain valid without that field;
the route returns a generic `503` until an operator configures a private
directory.

## Route and CLI

```text
GET /api/v1/backup-inventory?max_items=100
Authorization: Bearer <single-team-token>
```

Use the protected client:

```bash
skill2workflow service-backup-inventory \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --max-items 100
```

`max_items` is optional and is bounded to `1` through `100`. The request must
have an empty body. The route is authenticated, readiness-independent, and
read-only, so it remains useful while a service is draining or operating as a
standby.

## Fixed redacted contract

Responses use
`skill2workflow-remote-backup-inventory-0.1.0`, defined by
[`schemas/remote-backup-inventory-0.1.0.schema.json`](../schemas/remote-backup-inventory-0.1.0.schema.json).
Each returned entry contains only:

- `status`: `valid` or `invalid` after manifest, checksum, SQLite, and artifact
  verification;
- UTC creation time and state-layout identity;
- workflow-artifact count, file count, and total bytes.

The response never exports backup names and deliberately omits backup directory names, absolute paths,
manifest contents, workflow values, credentials, and database rows. The
`total` and `window.truncated` fields make an over-limit inventory visible
instead of presenting an incomplete list as complete. A local
`backup-list` remains the authority for mapping a reviewed entry to a specific
directory before `backup-verify` or `restore`.

The response is capped at 64 KiB. Authentication, malformed query/body,
missing or unsafe configuration, and filesystem/verification failures use
fixed `401`, `400`, or `503` responses without returning underlying error text.

## Configuration boundary

The optional setting is an absolute private directory:

```json
{
  "runtime": {
    "state_dir": "/var/lib/skill2workflow",
    "storage": "sqlite",
    "backup_parent_dir": "/var/backups/skill2workflow"
  }
}
```

The directory and each backup set must be owner-only and free of symlinks. The
service never creates, deletes, uploads, restores, or mutates a backup through
this route. The generated systemd unit grants the configured parent read-only
access while keeping the SQLite state directory as the only writable path.

## Verification

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_backup \
  tests.test_service.RuntimeServiceTests.test_backup_inventory_is_authenticated_redacted_and_bounded \
  tests.test_service_client.ServiceClientTests.test_backup_inventory_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_backup_inventory_command_prints_inventory \
  -v
```

This is an operator diagnostic, not a backup scheduler, retention executor,
remote upload, encryption/signing system, restore action, disaster-recovery
guarantee, or provider-side exactly-once claim.
