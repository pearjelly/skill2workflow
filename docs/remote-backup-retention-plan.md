# Remote Backup Retention Plan

Loop 162 adds an authenticated, read-only plan for reviewing backup
expiration remotely. It reuses the local backup-retention policy and complete
inventory check, but exports only aggregate counts and byte totals. Backup
names, paths, per-set reasons, manifest contents, and credentials never cross
the service boundary.

## Route and CLI

```text
POST /api/v1/backup-retention-plan
Authorization: Bearer <single-team-token>
Content-Type: application/json

{"policy": { ...backup-retention-policy-0.1.0... }}
```

Use the protected client:

```bash
skill2workflow service-backup-retention-plan \
  /etc/skill2workflow/backup-retention.json \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

## Fixed contract

Responses use `skill2workflow-remote-backup-retention-plan-0.1.0`, defined by
[`schemas/remote-backup-retention-plan-0.1.0.schema.json`](../schemas/remote-backup-retention-plan-0.1.0.schema.json).
The policy is normalized by the same implementation used by local
`backup-retention-plan`; its SHA-256 digest, cutoff, and minimum-valid-backup
floor are returned so an approval record can bind to the exact policy.

The plan is `ready` only when the bounded inventory is complete. If more than
1,000 direct child directories exist, it is `blocked` with
`inventory_truncated` and all summary values are `null`; the service never
guesses which older sets were omitted. A ready response reports valid and
invalid counts, eligible and preserved counts, and their byte totals. The
response is capped at 16 KiB and the request at 64 KiB.

## Safe operating sequence

1. Fetch the report and record its policy digest with the retention approval.
2. If blocked, use shell access to inspect or increase the bounded inventory;
   do not treat a partial report as an expiration plan.
3. For an approved ready report, stop the service and run the local
   [`backup-retention-plan`](backup-restore.md#verified-backup-and-restore)
   command again before any manual deletion. Compare its digest and counts.
4. Delete only the explicitly approved local names through the operator's
   established storage controls; this endpoint never performs deletion.

The report is a diagnostic and approval aid. A concurrent backup can appear
after the report, so the local complete-inventory plan remains authoritative at
the point of any manual action.

## Verification

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_backup.StateBackupTests.test_remote_backup_retention_plan_is_aggregate_and_redacted \
  tests.test_service.RuntimeServiceTests.test_backup_retention_plan_is_authenticated_aggregate_and_redacted \
  tests.test_service_client.ServiceClientTests.test_backup_retention_plan_posts_authenticated_policy_and_validates_contract \
  tests.test_cli.CliTests.test_service_backup_retention_plan_command_prints_plan \
  -v
```

The contract is read-only, single-tenant, and filesystem-local. It does not
delete, rename, upload, restore, encrypt, sign, schedule, replicate, or
automatically expire backups.
