# Cursor-Paged Remote Backup Inventory

Loop 161 adds a separate page surface for the protected remote backup
inventory. The Loop 160 `service-backup-inventory` command remains the fixed
recent-window compatibility view; this page surface lets an operator inspect
older backup sets without changing that contract.

## Route and CLI

```text
GET /api/v1/backup-inventory-pages?max_items=100&cursor=<opaque>
Authorization: Bearer <single-team-token>
```

Use the installed client:

```bash
skill2workflow service-backup-inventory-page \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --max-items 50 \
  --cursor <next_cursor-from-the-previous-page>
```

Omit `--cursor` for the first page. Pass `window.next_cursor` back unchanged
for the next page. Entries are returned newest first and the cursor moves
toward older entries. The total count remains the complete direct-child backup
count, while `window.has_more` indicates whether the current cursor has more
entries.

## Fixed redacted contract

Responses use
`skill2workflow-remote-backup-inventory-page-0.1.0`, defined by
[`schemas/remote-backup-inventory-page-0.1.0.schema.json`](../schemas/remote-backup-inventory-page-0.1.0.schema.json).
Each entry contains only verification status, creation time, state layout,
workflow-artifact count, file count, and total bytes. Backup names, paths,
manifest contents, workflow values, credentials, and database rows are never
exported.

The cursor is URL-safe and contains only a normalized ordering value and a
digest of the private directory name. It is an opaque continuation token for
the client; it is not an authorization credential. A malformed or modified
cursor fails with a fixed `400` response. `max_items` is bounded from 1
through 100 and the response is capped at 64 KiB.

The route is authenticated, read-only, and available while the service is
starting or draining. It does not acquire the scheduler lease, create, delete,
upload, restore, encrypt, sign, or expire backups. Missing or unsafe backup
configuration and filesystem/verification failures use a fixed `503` without
returning underlying error text.

The separate page route preserves the exact Loop 160 compatibility response.
It does not add remote backup transport, retention execution, disaster-
recovery guarantees, RBAC, multi-tenant isolation, or exactly-once provider
semantics.

## Verification

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_backup.StateBackupTests.test_remote_backup_inventory_page_redacts_names_and_pages \
  tests.test_service.RuntimeServiceTests.test_backup_inventory_page_is_authenticated_redacted_and_cursor_paged \
  tests.test_service_client.ServiceClientTests.test_backup_inventory_page_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_backup_inventory_page_command_prints_page \
  -v
```
