# Runtime service API reference

This reference consolidates the remote CLI and authenticated HTTP contracts.
For deployment and lifecycle setup, start with [the service guide](service.md).
Each resource section retains its request, response, error and operator rules.
Workflow DSL remains the execution authority; HTTP and CLI operations use the
same validated control-plane contracts.

## Resources

- [Remote Audit Consistency](#remote-audit-consistency)
- [Remote Audit Event Tail](#remote-audit-events)
- [Remote Audit Integrity](#remote-audit-integrity)
- [Cursor-Paged Remote Backup Inventory](#remote-backup-inventory-pages)
- [Remote Backup Inventory](#remote-backup-inventory)
- [Remote Backup Readiness](#remote-backup-readiness)
- [Remote Backup Retention Plan](#remote-backup-retention-plan)
- [Remote Operational Readiness](#remote-operational-readiness)
- [Remote Retention Readiness](#remote-retention-readiness)
- [Remote Runtime Info](#remote-runtime-info)
- [Remote recurring-schedule actions](#remote-schedule-actions)
- [Remote recurring-schedule creation](#remote-schedule-create)
- [Remote recurring-schedule deletion](#remote-schedule-delete)
- [Cursor-Paged Remote Recurring-Schedule Dispatch Diagnostics](#remote-schedule-dispatch-pages)
- [Remote Uncertain-Dispatch Reviews](#remote-schedule-dispatch-reviews)
- [Remote Recurring-Schedule Dispatch Diagnostics](#remote-schedule-dispatches)
- [Remote Recurring Schedule Inventory](#remote-schedule-inventory)
- [Remote Recurring-Schedule Patch](#remote-schedule-patch)
- [Remote recurring-schedule updates](#remote-schedule-update)
- [Remote Workflow Trigger](#remote-trigger)
- [Remote Workflow Artifact Consistency](#remote-workflow-artifacts)
- [Remote Workflow Deprecation](#remote-workflow-deprecation)
- [Remote Workflow Diff](#remote-workflow-diff)
- [Remote Workflow Inventory](#remote-workflow-inventory)
- [Remote Workflow Promotion](#remote-workflow-promotion)
- [Remote Workflow Publication](#remote-workflow-release)

<a id="remote-audit-consistency"></a>
<a id="remote-audit-consistency--remote-audit-consistency"></a>
## Remote Audit Consistency

The self-hosted service exposes the local run/audit consistency diagnostic to
authenticated operators without requiring shell access to the state directory.
It is a read-only incident diagnostic: it never resumes, retries, repairs, or
deletes a run or an audit event.

<a id="remote-audit-consistency--http-contract"></a>
### HTTP Contract

```http
GET /api/v1/audit-consistency
Authorization: Bearer <token>
```

The global 256-run window is selected from the newest durable run summaries
after a count-only scan; the service never materializes the complete run
history for this diagnostic. When that window is truncated, target one run
without shell access using the fixed path form:

```http
GET /api/v1/audit-consistency/run_<opaque-id>
Authorization: Bearer <token>
```

The target identifier must use the same `run_`-prefixed safe identifier grammar
as the run-detail endpoint. A targeted report has one run and is never marked
truncated because of the global window. An unknown target returns the fixed
`503` unavailable response rather than exposing state or filesystem details.

The request must have an empty body. The endpoint returns the existing
`skill2workflow-run-audit-report-0.1.0` contract from
[`run-audit-consistency.md`](run-audit-consistency.md), with a 64 KiB encoded
response bound. Authentication failures use the same fixed `401`/`503`
boundary as the other protected read routes. An invalid body returns `400` and
the fixed message `audit consistency request must not include a body`.

The endpoint is available before readiness when the authentication provider and
SQLite state are readable. It does not append an ingress audit event, acquire
the scheduler lease, or expose workflow instructions, trigger input, connector
output, credentials, or raw errors. If the projection cannot be read or would
exceed its bound, it returns `503` with `{"error":"audit consistency unavailable"}`.

<a id="remote-audit-consistency--installed-client"></a>
### Installed Client

The installed CLI reads the Bearer token from an owner-only file and validates
the exact response shape before printing it:

```bash
skill2workflow service-audit-consistency \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-audit-consistency \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --run-id run_...
```

The client rejects ambiguous origins, remote plain HTTP, redirects, malformed
headers, oversized responses, and extra or missing report fields. Use the
local `audit-consistency` command when the operator is already on the service
host; use this endpoint for a remote, TLS-terminated self-hosted deployment.

<a id="remote-audit-consistency--evidence"></a>
### Evidence

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_audit_consistency_is_authenticated_bounded_and_read_only \
  tests.test_service.RuntimeServiceTests.test_audit_consistency_is_available_before_readiness \
  tests.test_service.RuntimeServiceTests.test_audit_consistency_rejects_oversized_projection_without_disclosure \
  tests.test_service.RuntimeServiceTests.test_audit_consistency_can_target_one_run_beyond_the_global_window \
  tests.test_service_client.ServiceClientTests.test_audit_consistency_uses_authenticated_get_and_validates_contract \
  tests.test_service_client.ServiceClientTests.test_audit_consistency_can_target_one_safe_run_id \
  tests.test_service_client.ServiceClientTests.test_audit_consistency_rejects_unsafe_target_before_network_access \
  tests.test_cli.CliTests.test_service_audit_consistency_command_prints_report \
  tests.test_cli.CliTests.test_service_audit_consistency_command_accepts_one_run_id \
  -v
```
<!-- end: remote-audit-consistency -->

<a id="remote-audit-events"></a>
<a id="remote-audit-events--remote-audit-event-tail"></a>
## Remote Audit Event Tail

The self-hosted service exposes a bounded, redacted audit tail for remote
incident diagnosis. It is read-only: it never resumes, retries, repairs, or
deletes a run, audit row, workflow, credential, or connector result.

<a id="remote-audit-events--http-contract"></a>
### HTTP contract

```http
GET /api/v1/audit-events?max_items=100&workflow_id=<id>&workflow_version=<version>&run_id=run_<id>&event_type=<type>
Authorization: Bearer <token>
```

The request must have an empty body. `max_items` is 1 through 100. The optional
filters are exact matches and may occur only once. The response uses
[`schemas/audit-event-list-0.1.0.schema.json`](../schemas/audit-event-list-0.1.0.schema.json)
and is capped at 64 KiB. Events are returned in sequence order within each
page. When `window.truncated` is true, pass the opaque `window.next_cursor`
back as `cursor` to read the preceding page. The total is the count for the
selected filter (not a count of raw payload bytes).

Every event is projected through a fixed allowlist: sequence, type, safe
workflow/run identifiers, timestamp, node/connector status, retry counters,
approval state, and an error-presence flag. Workflow DSL, trigger context,
connector metadata/output, credential values, raw provider errors, and arbitrary
payload keys never cross this boundary. Authentication failures use the same
fixed `401`/`503` boundary as the other protected read routes. Invalid query
fields or a non-empty body return `400`; an unreadable SQLite projection
returns `503` with the fixed `audit event page unavailable` message.

The route is available before readiness when authentication and SQLite state are
readable. It does not acquire the scheduler lease, call providers, or append
ingress audit evidence. JSON storage is intentionally rejected for this remote
service surface because cursor paging requires the bounded SQLite index.

<a id="remote-audit-events--installed-client"></a>
### Installed client

The installed CLI reads the Bearer token from an owner-only file, validates the
origin, response headers, byte bound, exact schema, and redaction shape, then
prints the projection:

```bash
skill2workflow service-audit-events \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --max-items 100

skill2workflow service-audit-events \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --run-id run_... \
  --event-type connector_failed \
  --cursor <next_cursor>
```

Use the local `audit --limit` command when shell access is available; use this
endpoint for a TLS-terminated self-hosted deployment where the operator needs
bounded, value-free diagnostics without copying the state directory.

<a id="remote-audit-events--evidence"></a>
### Evidence

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_storage.StorageTests.test_sqlite_audit_page_filters_and_continues_with_sequence_cursor \
  tests.test_dashboard.DashboardTests.test_audit_event_page_is_cursor_paged_and_redacted \
  tests.test_service.RuntimeServiceTests.test_audit_event_page_is_authenticated_filtered_cursor_paged_and_redacted \
  tests.test_service_client.ServiceClientTests.test_audit_event_page_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_audit_events_command_prints_filtered_page \
  -v
```
<!-- end: remote-audit-events -->

<a id="remote-audit-integrity"></a>
<a id="remote-audit-integrity--remote-audit-integrity"></a>
## Remote Audit Integrity

Loop 83 exposes the existing SQLite SHA-256 audit-chain verification result
through the authenticated service boundary. It lets an operator detect a
truncated, reordered, or tampered control-plane audit chain without shell
access or event-payload export.

<a id="remote-audit-integrity--route-and-cli"></a>
### Route and CLI

```text
GET /api/v1/audit-integrity
Authorization: Bearer <single-team-token>
```

The request must not include a body. The route is read-only and remains
available while the service is starting, ready, draining, or standby when the
SQLite control database is readable.

Use the protected client:

```bash
skill2workflow service-audit-integrity \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

<a id="remote-audit-integrity--fixed-contract"></a>
### Fixed contract

The response reuses
`skill2workflow-audit-integrity-0.1.0`, defined by
[`schemas/audit-integrity-0.1.0.schema.json`](../schemas/audit-integrity-0.1.0.schema.json).
It contains only the status, algorithm, event count, chain head digest, first
affected sequence, and a fixed reason. It never includes an audit event,
workflow identifier, run identifier, input, connector response, credential, or
raw exception.

`status: "valid"` confirms the locally stored chain is internally consistent.
`status: "invalid"` is still a successful diagnostic response and requires
operator investigation; the route does not repair or rewrite the chain.
`status: "legacy_unsealed"` is the expected result for a legacy JSON audit
path or before an older SQLite audit table is opened by a version that seals
it. The existing local `audit-verify` command remains authoritative for the
host-side stop-and-recovery procedure.

The response is capped at 16 KiB. Authentication, body, and state failures
use fixed `401`, `400`, and `503` responses. The older support-bundle 0.1.0
projection intentionally omits this route's counter.

<a id="remote-audit-integrity--safe-operating-sequence"></a>
### Safe operating sequence

1. Fetch the report and record the schema version, status, reason, and event
   count.
2. If the status is `invalid`, stop mutating service state and follow the local
   [`audit-integrity.md`](audit-integrity.md) recovery and backup procedure.
3. Preserve the original state directory and any verified backup before an
   operator-managed restore or migration decision.

The endpoint does not sign evidence, establish operator identity, repair the
database, or replace authenticated backups and access controls.

<a id="remote-audit-integrity--verification"></a>
### Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_audit_integrity_is_authenticated_payload_free_and_read_only \
  tests.test_service_client.ServiceClientTests.test_audit_integrity_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_audit_integrity_command_prints_report \
  -v
```
<!-- end: remote-audit-integrity -->

<a id="remote-backup-inventory-pages"></a>
<a id="remote-backup-inventory-pages--cursor-paged-remote-backup-inventory"></a>
## Cursor-Paged Remote Backup Inventory

Loop 161 adds a separate page surface for the protected remote backup
inventory. The Loop 160 `service-backup-inventory` command remains the fixed
recent-window compatibility view; this page surface lets an operator inspect
older backup sets without changing that contract.

<a id="remote-backup-inventory-pages--route-and-cli"></a>
### Route and CLI

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

<a id="remote-backup-inventory-pages--fixed-redacted-contract"></a>
### Fixed redacted contract

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

<a id="remote-backup-inventory-pages--verification"></a>
### Verification

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_backup.StateBackupTests.test_remote_backup_inventory_page_redacts_names_and_pages \
  tests.test_service.RuntimeServiceTests.test_backup_inventory_page_is_authenticated_redacted_and_cursor_paged \
  tests.test_service_client.ServiceClientTests.test_backup_inventory_page_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_backup_inventory_page_command_prints_page \
  -v
```
<!-- end: remote-backup-inventory-pages -->

<a id="remote-backup-inventory"></a>
<a id="remote-backup-inventory--remote-backup-inventory"></a>
## Remote Backup Inventory

Loop 160 adds a protected, read-only view of the configured offline backup
parent. It closes the operator gap between “the service is currently able to
take a backup” and “the most recent backup sets are still valid and within the
expected size window.”

The service bootstrap creates an owner-only `backups/` directory and records
its absolute path as the optional `runtime.backup_parent_dir` setting. Existing
hand-written `service-0.2.0` configurations remain valid without that field;
the route returns a generic `503` until an operator configures a private
directory.

<a id="remote-backup-inventory--route-and-cli"></a>
### Route and CLI

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

<a id="remote-backup-inventory--fixed-redacted-contract"></a>
### Fixed redacted contract

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

<a id="remote-backup-inventory--configuration-boundary"></a>
### Configuration boundary

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

<a id="remote-backup-inventory--verification"></a>
### Verification

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
<!-- end: remote-backup-inventory -->

<a id="remote-backup-readiness"></a>
<a id="remote-backup-readiness--remote-backup-readiness"></a>
## Remote Backup Readiness

Loop 82 adds a read-only preflight for the existing offline SQLite backup
procedure. It lets an operator confirm the state layout, referenced artifact
count, and scheduler lease condition before stopping the service for a backup.
It does not create, upload, or retain a backup remotely.

<a id="remote-backup-readiness--route-and-cli"></a>
### Route and CLI

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

<a id="remote-backup-readiness--fixed-contract"></a>
### Fixed contract

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

<a id="remote-backup-readiness--safe-operating-sequence"></a>
### Safe operating sequence

1. Fetch the report and record the schema version and status.
2. If blocked, drain and stop the service through the host supervisor.
3. Run the documented local [`backup`](backup-restore.md) command and verify
   its manifest before moving the copy off-host.

The endpoint does not expose paths, database contents, workflow values,
credentials, lease owner identities, or backup bytes.

<a id="remote-backup-readiness--verification"></a>
### Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_backup_readiness_is_authenticated_and_reports_active_lease \
  tests.test_service_client.ServiceClientTests.test_backup_readiness_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_backup_readiness_command_prints_report \
  -v
```
<!-- end: remote-backup-readiness -->

<a id="remote-backup-retention-plan"></a>
<a id="remote-backup-retention-plan--remote-backup-retention-plan"></a>
## Remote Backup Retention Plan

Loop 162 adds an authenticated, read-only plan for reviewing backup
expiration remotely. Loop 163 bounds the directory scan used by that plan: it
stops after the first over-budget set instead of walking an arbitrarily large
backup parent. The route reuses the local backup-retention policy and complete
inventory check, but exports only aggregate counts and byte totals. Backup
names, paths, per-set reasons, manifest contents, and credentials never cross
the service boundary.

<a id="remote-backup-retention-plan--route-and-cli"></a>
### Route and CLI

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

<a id="remote-backup-retention-plan--fixed-contract"></a>
### Fixed contract

Responses use `skill2workflow-remote-backup-retention-plan-0.1.0`, defined by
[`schemas/remote-backup-retention-plan-0.1.0.schema.json`](../schemas/remote-backup-retention-plan-0.1.0.schema.json).
The policy is normalized by the same implementation used by local
`backup-retention-plan`; its SHA-256 digest, cutoff, and minimum-valid-backup
floor are returned so an approval record can bind to the exact policy.

The plan is `ready` only when the bounded inventory is complete. If more than
1,000 direct child directories exist, it is `blocked` with
`inventory_truncated` and all summary values are `null`; the service stops
after observing the first 1,001 sets and never guesses which older sets were
omitted. A ready response reports valid and invalid counts, eligible and
preserved counts, and their byte totals. The response is capped at 16 KiB and
the request at 64 KiB.

<a id="remote-backup-retention-plan--safe-operating-sequence"></a>
### Safe operating sequence

1. Fetch the report and record its policy digest with the retention approval.
2. If blocked, use shell access to inspect or increase the bounded inventory;
   do not treat the lower-bound scan or partial report as an expiration plan.
3. For an approved ready report, stop the service and run the local
   [`backup-retention-plan`](backup-restore.md#verified-backup-and-restore)
   command again before any manual deletion. Compare its digest and counts.
4. Delete only the explicitly approved local names through the operator's
   established storage controls; this endpoint never performs deletion.

The report is a diagnostic and approval aid. A concurrent backup can appear
after the report, so the local complete-inventory plan remains authoritative at
the point of any manual action.

<a id="remote-backup-retention-plan--verification"></a>
### Verification

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
<!-- end: remote-backup-retention-plan -->

<a id="remote-operational-readiness"></a>
<a id="remote-operational-readiness--remote-operational-readiness"></a>
## Remote Operational Readiness

Loop 93 adds one authenticated, read-only report for operators and deployment
automation. It combines the existing service lifecycle, published-artifact
consistency, SQLite audit integrity, and offline-backup preflight checks into a
small fixed contract. It does not replace any individual check and does not
claim an atomic snapshot across SQLite databases.

<a id="remote-operational-readiness--route-and-cli"></a>
### Route and CLI

```text
GET /api/v1/operational-readiness
Authorization: Bearer <single-team-token>
```

The request must not include a body. Use the protected client:

```bash
skill2workflow service-operational-readiness \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

<a id="remote-operational-readiness--fixed-contract"></a>
### Fixed contract

Responses use `skill2workflow-operational-readiness-0.1.0`, defined by
[`schemas/operational-readiness-0.1.0.schema.json`](../schemas/operational-readiness-0.1.0.schema.json).
The report contains only:

- service lifecycle, readiness, SQLite layout, and lease ownership;
- an aggregate workflow-artifact check with an issue count, never issue values;
- the audit-chain status, never a digest or event payload;
- offline-backup status and active-lease state;
- fixed blocking reasons and the note that offline backup requires a stopped
  service when its lease is active.

`status: "ready"` means the service is ready, the current layout is in use,
the artifact report is clean, and the SQLite audit chain is valid. An active
lease makes offline backup `blocked` but is an expected note while the service
is running; it does not make the overall report fail. `status: "attention"`
means one of the execution-safety checks needs operator action. The report is
best-effort across independent read-only checks, so the individual check
statuses are authoritative for diagnosis.

The response is capped at 16 KiB. Authentication, body, and state failures use
fixed `401`, `400`, and `503` responses. The stable support-bundle 0.1.0
projection intentionally omits this route's telemetry counter.

<a id="remote-operational-readiness--safe-operating-sequence"></a>
### Safe operating sequence

1. Fetch the report with the protected CLI and record the schema/status.
2. Stop or drain the service only when the report or the relevant check calls
   require maintenance; this endpoint never changes lifecycle state.
3. For a failed check, follow its authoritative guide: artifact consistency,
   audit integrity, backup readiness, or retention readiness.

The endpoint exposes no paths, workflow DSL, run identifiers, audit payloads,
credentials, lease-owner identities, or provider data.

<a id="remote-operational-readiness--verification"></a>
### Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_operational_readiness_is_authenticated_aggregate_and_redacted \
  tests.test_service_client.ServiceClientTests.test_operational_readiness_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_operational_readiness_command_prints_report \
  -v
```
<!-- end: remote-operational-readiness -->

<a id="remote-retention-readiness"></a>
<a id="remote-retention-readiness--remote-retention-readiness"></a>
## Remote Retention Readiness

Loop 92 adds a read-only, policy-bound preflight for the existing local
copy-on-write retention procedure. It lets an operator validate a normalized
retention policy and see whether the service is quiesced before stopping it.
It never deletes, copies, vacuums, uploads, or changes runtime state.

<a id="remote-retention-readiness--route-and-cli"></a>
### Route and CLI

```text
POST /api/v1/retention-readiness
Authorization: Bearer <single-team-token>
Content-Type: application/json

{"policy": { ...retention-policy-0.3.0... }}
```

Use the protected client:

```bash
skill2workflow service-retention-readiness \
  /etc/skill2workflow/retention.json \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

<a id="remote-retention-readiness--fixed-contract"></a>
### Fixed contract

Responses use `skill2workflow-retention-readiness-0.1.0`, defined by
[`schemas/retention-readiness-0.1.0.schema.json`](../schemas/retention-readiness-0.1.0.schema.json).
The policy is normalized by the same implementation used by local
`state-retention-plan`; its SHA-256 digest and normalized UTC cutoff are
returned so an approval record can bind to the exact policy.

When the scheduler lease is active, the response is `blocked` and all
eligibility counts are `null`. Reading multiple SQLite databases while the
service is writing cannot safely claim to be one retention plan. After the
service is quiesced, the response is `ready` and returns only aggregate counts
for eligible and preserved records. The local `state-retention-plan` remains
authoritative and rechecks the stopped-service boundary immediately before
apply.

Authentication, malformed policy/body, oversized body, and state failures use
fixed `401`, `400`, `413`, and `503` responses. The response is capped at 16 KiB;
the request is capped at 64 KiB by the protected client. The stable support
bundle 0.1.0 projection intentionally omits this route's telemetry counter.

<a id="remote-retention-readiness--safe-operating-sequence"></a>
### Safe operating sequence

1. Fetch the report and record its policy digest and status with the retention
   approval.
2. If blocked, drain and stop the service through the host supervisor.
3. Run the local [`state-retention-plan`](data-retention.md#read-only-plan),
   compare its digest and counts, then use the documented copy-on-write apply.

The endpoint exposes no paths, workflow values, run payloads, credentials,
lease-owner identities, or deleted data.

<a id="remote-retention-readiness--verification"></a>
### Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_retention.StateRetentionTests.test_remote_readiness_returns_counts_only_when_state_is_quiesced \
  tests.test_service.RuntimeServiceTests.test_retention_readiness_is_authenticated_bounded_and_blocks_live_service \
  tests.test_service_client.ServiceClientTests.test_retention_readiness_posts_policy_and_validates_fixed_contract \
  tests.test_cli.CliTests.test_service_retention_readiness_command_loads_policy_and_prints_report \
  -v
```
<!-- end: remote-retention-readiness -->

<a id="remote-runtime-info"></a>
<a id="remote-runtime-info--remote-runtime-info"></a>
## Remote Runtime Info

Loop 84 adds a protected, read-only identity report for upgrade and incident
triage. It lets an operator confirm which package and service contract are
running, which Workflow DSL compatibility line they expose, which SQLite state
layout they opened, and whether the current process is ready and owns the
scheduler lease.

<a id="remote-runtime-info--route-and-cli"></a>
### Route and CLI

```text
GET /api/v1/runtime-info
Authorization: Bearer <single-team-token>
```

The request must not include a body. The route is readiness-independent: a
starting, draining, or standby process can still report its identity when the
state directory is readable.

Use the protected client:

```bash
skill2workflow service-runtime-info \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

<a id="remote-runtime-info--fixed-contract"></a>
### Fixed contract

Responses use `skill2workflow-runtime-info-0.1.0`, defined by
[`schemas/runtime-info-0.1.0.schema.json`](../schemas/runtime-info-0.1.0.schema.json).
The report contains only:

- package, service-config, Workflow DSL, and compatibility-line versions;
- SQLite storage and state-layout identities; and
- fixed lifecycle, readiness, and scheduler-lease booleans.

It never includes hostnames, ports, filesystem paths, token metadata,
credentials, workflow identifiers, run identifiers, or request values. The
response is capped at 16 KiB. Authentication, body, and state failures use
fixed `401`, `400`, and `503` responses.

`service_ready` is the live `/readyz` result at collection time and can be
false while `service_status` is `starting`, `draining`, or `ready` without a
current scheduler lease. The report is a point-in-time diagnostic, not a
compatibility proof for an arbitrary future binary or a replacement for the
Doctor and migration preflights.

<a id="remote-runtime-info--safe-upgrade-sequence"></a>
### Safe upgrade sequence

1. Fetch and record `package_version`, `service_schema_version`,
   `workflow_dsl_schema_version`, and `state_layout_version` from the old
   process.
2. Stop the old service and run the documented Doctor and migration preflight
   before pointing a new binary at the state directory.
3. Fetch the report from the new process and require `/readyz` to return 200
   before returning traffic.

<a id="remote-runtime-info--verification"></a>
### Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_runtime_info_is_authenticated_bounded_and_reports_compatibility \
  tests.test_service_client.ServiceClientTests.test_runtime_info_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_runtime_info_command_prints_report \
  -v
```
<!-- end: remote-runtime-info -->

<a id="remote-schedule-actions"></a>
<a id="remote-schedule-actions--remote-recurring-schedule-actions"></a>
## Remote recurring-schedule actions

Loop 79 adds a small, protected operator write surface for the durable
recurring scheduler. It complements the read-only inventory in
[`remote-schedule-inventory.md`](api-reference.md#remote-schedule-inventory): an operator can
pause a faulty schedule or resume it after remediation without opening the
service host shell.

<a id="remote-schedule-actions--contract"></a>
### Contract

Both endpoints require the service Bearer token. The legacy empty JSON object
(`{}`) body remains supported:

```text
POST /api/v1/recurring-schedules/{schedule_id}/disable
POST /api/v1/recurring-schedules/{schedule_id}/enable
```

For stale-inventory protection, an operator may instead send exactly one
`expected_next_run_at` field:

```json
{"expected_next_run_at": "2026-08-11T01:00:00+00:00"}
```

The value is compared with the persisted schedule inside the same
`BEGIN IMMEDIATE` transaction used by dispatcher claims. A mismatch returns
HTTP `409` with `recurring schedule action precondition failed`; malformed or
null values return `400`. Omitting the field retains the original idempotent
action behavior for compatibility. A successful action still returns the
same fixed response schema and never exposes trigger input.

`schedule_id` is limited to 128 letters, numbers, `_`, `-`, and `.`. The
service must be ready before a mutation is accepted. The response is the
fixed [`recurring-schedule-action-0.1.0`](../schemas/recurring-schedule-action-0.1.0.schema.json)
contract:

```json
{
  "schema_version": "skill2workflow-recurring-schedule-action-0.1.0",
  "schedule_id": "schedule_hourly_report",
  "enabled": false,
  "status": "disabled",
  "changed": true
}
```

The write is idempotent. Repeating the same action returns `200` with
`changed: false`; it does not create another state transition. Unknown IDs
return a fixed `404`, malformed bodies return `400`, and authentication or
service failures do not disclose scheduler state.

The transition uses the recurring store's existing `BEGIN IMMEDIATE` SQLite
transaction, so it serializes with due-dispatch claims. The authenticated
ingress and successful mutation are recorded as bounded control-plane audit
events (`recurring_schedule_action` and `recurring_schedule_updated`). The
control and scheduler databases remain separate; the mutation transaction is
the source of truth for scheduler state, while the control audit records the
operator evidence after that state transaction succeeds.

If the scheduler commit succeeds but the control-audit append fails, the action
can return `503` after the requested enabled state is already durable. Retry the
same enable/disable endpoint after recovery. Because the transition is
idempotent, the retry returns `200` with `changed: false` and completes the
missing operator evidence; it never manufactures a second state transition.

<a id="remote-schedule-actions--cli"></a>
### CLI

```bash
PYTHONPATH=src python3 -m skill2workflow.cli service-recurring-schedules \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /path/to/ingress.token

PYTHONPATH=src python3 -m skill2workflow.cli service-schedule-disable \
  schedule_hourly_report \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /path/to/ingress.token

PYTHONPATH=src python3 -m skill2workflow.cli service-schedule-enable \
  schedule_hourly_report \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /path/to/ingress.token

PYTHONPATH=src python3 -m skill2workflow.cli service-schedule-disable \
  schedule_hourly_report \
  --expected-next-run-at 2026-08-11T01:00:00+00:00 \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /path/to/ingress.token
```

The client validates the HTTPS-or-loopback origin, owner-only token file,
no-redirect policy, response headers, response size, schedule identifier, and
the complete response schema before printing it.

<a id="remote-schedule-actions--observability-and-compatibility"></a>
### Observability and compatibility

The complete `/metrics` route matrix includes the low-cardinality
`recurring_schedule_action` route. The fixed support-bundle 0.1.0 contract
continues to omit newer schedule route labels, so existing incident tooling
does not need a schema migration. Schedule action requests never expose
trigger input, workflow DSL, credentials, or raw SQLite content.

Focused verification:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules \
  tests.test_control_plane \
  tests.test_service_client \
  tests.test_service \
  tests.test_cli \
  tests.test_telemetry -v
```
<!-- end: remote-schedule-actions -->

<a id="remote-schedule-create"></a>
<a id="remote-schedule-create--remote-recurring-schedule-creation"></a>
## Remote recurring-schedule creation

Loop 154 adds one protected operator write path for creating a durable
recurring schedule without opening the service host shell. It complements the
remote inventory and enable/disable actions while keeping SQLite scheduling
semantics unchanged.

<a id="remote-schedule-create--contract"></a>
### Contract

The endpoint requires the service Bearer token, readiness, the active scheduler
lease, and an exact wrapper body:

```text
POST /api/v1/recurring-schedules
```

```json
{
  "schedule": {
    "schema_version": "skill2workflow-schedule-0.2.0",
    "schedule": {
      "id": "schedule_hourly_report",
      "workflow_id": "workflow_hourly_report",
      "version": "0.1.0",
      "starts_at": "2026-08-11T00:00:00Z",
      "interval_seconds": 3600,
      "missed_run_policy": "latest",
      "enabled": true
    },
    "trigger": {
      "idempotency_key_prefix": "schedule_hourly_report",
      "input": {"report": "hourly"}
    }
  }
}
```

The response is the fixed redacted
[`recurring-schedule-create-0.1.0`](../schemas/recurring-schedule-create-0.1.0.schema.json)
contract. It returns scheduling metadata and a `created` flag, but never
returns trigger input, the source, or the idempotency-key prefix:

```json
{
  "schema_version": "skill2workflow-recurring-schedule-create-0.1.0",
  "schedule_id": "schedule_hourly_report",
  "workflow_id": "workflow_hourly_report",
  "workflow_version": "0.1.0",
  "status": "active",
  "enabled": true,
  "starts_at": "2026-08-11T00:00:00+00:00",
  "next_run_at": "2026-08-11T00:00:00+00:00",
  "interval_seconds": 3600,
  "missed_run_policy": "latest",
  "created": true
}
```

The request is bounded by the shared 1 MiB body/input limits and the response
is capped at 16 KiB. Invalid JSON or a wrong wrapper returns `400`; a changed definition
for an existing `schedule_id` returns fixed `409`; authentication,
readiness, or storage failures do not disclose scheduler state.

Creation is retry-safe. An identical definition returns `200` with
`created: false`. A changed retry never resets `next_run_at` or other durable
dispatch progress. The store uses `BEGIN IMMEDIATE`, serializing creation with
dispatcher claims. The control-plane audit records bounded authentication and
creation/replay events; trigger values remain in the scheduler database only.

If the scheduler transaction commits but the separate control-audit append
fails, the request can return `503`. Retrying the identical definition repairs
the missing operator evidence without creating a second schedule or resetting
progress.

<a id="remote-schedule-create--cli"></a>
### CLI

```bash
PYTHONPATH=src python3 -m skill2workflow.cli service-recurring-schedule-add \
  /path/to/recurring-schedule.json \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /path/to/ingress.token
```

The installed client validates the origin, owner-only token file, redirect
policy, request/response bounds, and the complete fixed response schema before
printing it.

<a id="remote-schedule-create--boundary"></a>
### Boundary

This loop creates recurring SQLite schedules only. It does not update or
delete an existing definition, create one-shot JSON schedules, publish a
workflow, or claim exactly-once delivery. Use the existing enable/disable
action to pause or resume a created schedule and the dispatch diagnostics to
inspect uncertain outcomes.

Focused verification:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules \
  tests.test_service_client \
  tests.test_service \
  tests.test_cli \
  tests.test_telemetry -v
```
<!-- end: remote-schedule-create -->

<a id="remote-schedule-delete"></a>
<a id="remote-schedule-delete--remote-recurring-schedule-deletion"></a>
## Remote recurring-schedule deletion

Loop 156 adds a protected way to retire one recurring schedule through the
authenticated service boundary. Retirement is deliberately narrower than a
database purge: the schedule definition and compact inventory row are removed,
historical dispatch records remain available for diagnosis, and a tombstone
makes retries safe.

<a id="remote-schedule-delete--contract"></a>
### Contract

The endpoint requires service readiness, the active scheduler lease, a Bearer
token, and an exact confirmation body:

```text
DELETE /api/v1/recurring-schedules/{schedule_id}
```

```json
{
  "expected_next_run_at": "2026-08-11T01:00:00+00:00",
  "confirm": true
}
```

`expected_next_run_at` is the last value observed by the operator. The store
compares it inside the same `BEGIN IMMEDIATE` transaction used by dispatcher
claims. The schedule must already be disabled and there must be no active claim
(`claimed` dispatch) for it. Stale, active, or enabled schedules return fixed `409`
responses; unknown IDs return fixed `404` responses.

The successful response is the fixed redacted
[`recurring-schedule-delete-0.1.0`](../schemas/recurring-schedule-delete-0.1.0.schema.json)
contract:

```json
{
  "schema_version": "skill2workflow-recurring-schedule-delete-0.1.0",
  "schedule_id": "schedule_hourly_report",
  "deleted": true
}
```

An identical retry after the definition has been retired returns `200` with
`deleted: false`. The tombstone prevents the schedule ID from being reused, so
a delayed retry can never remove a different schedule. Dispatch history is
not deleted, and no trigger input, workflow content, credential, or provider
response is returned.

If the scheduler transaction succeeds but the separate control-plane audit
append fails, the request may return `503`. Retrying the same request observes
the tombstone, appends the missing value-free evidence, and returns the fixed
no-op response.

<a id="remote-schedule-delete--cli"></a>
### CLI

```bash
skill2workflow service-recurring-schedule-delete \
  schedule_hourly_report \
  --expected-next-run-at 2026-08-11T01:00:00+00:00 \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The installed client validates the HTTPS-or-loopback origin, owner-only token
file, redirect policy, request/response bounds, safe schedule identifier, and
the complete fixed response schema before printing it.

<a id="remote-schedule-delete--boundary-and-verification"></a>
### Boundary and verification

This is a single-tenant schedule retirement boundary. It does not delete
dispatch evidence, cancel an in-flight provider call, reclaim tombstones,
delete one-shot schedules, publish workflows, or claim exactly-once provider
effects.

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules \
  tests.test_service_client \
  tests.test_service \
  tests.test_cli \
  tests.test_telemetry -v
```
<!-- end: remote-schedule-delete -->

<a id="remote-schedule-dispatch-pages"></a>
<a id="remote-schedule-dispatch-pages--cursor-paged-remote-recurring-schedule-dispatch-diagnostics"></a>
## Cursor-Paged Remote Recurring-Schedule Dispatch Diagnostics

Loop 159 adds a versioned, read-only page surface for recurring dispatch
evidence. The original `service-recurring-dispatches` command remains a fixed
recent-tail compatibility view; this page surface lets an operator inspect
older records without loading the complete dispatch history into memory.

<a id="remote-schedule-dispatch-pages--routes-and-cli"></a>
### Routes and CLI

```text
GET /api/v1/recurring-schedule-dispatch-pages?max_items=100&cursor=<opaque>
GET /api/v1/recurring-schedules/{schedule_id}/dispatch-pages?max_items=100&cursor=<opaque>
```

The request is Bearer-authenticated, has no body, and is available while the
service is starting or draining. The installed client is:

```bash
skill2workflow service-recurring-dispatch-page \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --schedule-id schedule_hourly_report \
  --max-items 50 \
  --cursor <next_cursor-from-the-previous-page>
```

Omit `--schedule-id` and `--cursor` for the first global page. The cursor is
opaque and must be passed back unchanged; it contains only the last returned
dispatch ordering key and is URL-safe. Pages are returned in chronological
order within each newest-to-oldest page, while `next_cursor` walks toward
older records. Concurrently appended records do not invalidate an existing
cursor.

<a id="remote-schedule-dispatch-pages--fixed-contract-and-safety"></a>
### Fixed contract and safety

Responses use
`skill2workflow-recurring-schedule-dispatch-page-0.1.0`, defined by
[`schemas/recurring-schedule-dispatch-page-0.1.0.schema.json`](../schemas/recurring-schedule-dispatch-page-0.1.0.schema.json).
Each response contains the same redacted dispatch fields as the compatibility
tail, aggregate status counts, and a fixed `max_items`/`has_more`/`next_cursor`
window. `max_items` is bounded from 1 through 100 and the response is capped
at 64 KiB.

The service uses a SQLite ordering key `(scheduled_for, dispatch_id)` and a
bounded `LIMIT max_items + 1` query. It never exports trigger input,
connector payloads, credential handles, scheduler owner identities, lease
expiry timestamps, or raw persisted records. Invalid cursors, duplicate query
fields, unsupported query fields, body-bearing requests, and oversized
responses fail closed with fixed `400`/`503` behavior. The route is read-only:
it does not acquire the scheduler lease, claim or replay dispatches, append
audit state, or reconcile uncertain outcomes.

The page route is deliberately separate from the 0.1.0 compatibility tail,
so existing clients keep their exact response shape. It does not add bulk
retry, automatic provider reconciliation, RBAC, hosted TLS, or exactly-once
provider execution.

<a id="remote-schedule-dispatch-pages--verification"></a>
### Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_recurring_dispatch_page_is_cursor_paged_and_redacted \
  tests.test_service.RuntimeServiceTests.test_recurring_schedule_dispatch_list_is_authenticated_bounded_and_redacted \
  tests.test_service_client.ServiceClientTests.test_recurring_dispatch_page_uses_cursor_and_validates_contract \
  tests.test_cli.CliTests.test_service_recurring_dispatch_page_command_supports_cursor \
  -v
```
<!-- end: remote-schedule-dispatch-pages -->

<a id="remote-schedule-dispatch-reviews"></a>
<a id="remote-schedule-dispatch-reviews--remote-uncertain-dispatch-reviews"></a>
## Remote Uncertain-Dispatch Reviews

The scheduler intentionally leaves a recovered dispatch in `uncertain`: a
process may have lost its lease after the provider accepted the effect. Loop
205 adds a narrow operator evidence action for that state without pretending
to reconcile the provider.

<a id="remote-schedule-dispatch-reviews--routes-and-cli"></a>
### Routes and CLI

```text
POST /api/v1/recurring-schedule-dispatches/{dispatch_id}/review
GET  /api/v1/recurring-schedule-dispatches/{dispatch_id}/review
```

Both routes use the service Bearer token. `POST` requires a JSON body with
exactly the two fields below:

```json
{
  "expected_completed_at": "2026-08-11T00:01:00+00:00",
  "outcome": "effect_not_observed"
}
```

The outcome must be one of:

- `effect_confirmed`: the operator observed the provider-side effect;
- `effect_not_observed`: the operator observed no provider-side effect;
- `no_conclusion`: inspection did not establish either result.

The timestamp is copied from the dispatch list/page projection and is a
compare-and-swap token. A review is idempotent when the same outcome and token
are submitted again. A different outcome, a stale token, a non-uncertain
dispatch, or an invalid identifier returns a fixed conflict/error response.

The installed commands are:

```bash
skill2workflow service-recurring-dispatch-review \
  dispatch_0123456789abcdef \
  --expected-completed-at 2026-08-11T00:01:00+00:00 \
  --outcome effect_not_observed \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-recurring-dispatch-review-get \
  dispatch_0123456789abcdef \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

<a id="remote-schedule-dispatch-reviews--contract-and-safety-boundary"></a>
### Contract and safety boundary

Responses use
[`recurring-schedule-dispatch-review-0.1.0.schema.json`](../schemas/recurring-schedule-dispatch-review-0.1.0.schema.json).
They expose only dispatch/schedule identifiers, scheduling timestamps, the
fixed uncertain status, the supplied outcome, the review timestamp, and an
idempotency `changed` flag. Raw trigger input, connector payloads, credentials,
lease owner, lease expiry, and provider response data never enter the
projection.

The review is stored inside the existing SQLite `record_json` row, so backup,
restore, and audit-chain reads retain it without a schema migration. While the
dispatch record is retained, its status remains `uncertain`. The review does not complete, retry, cancel, or replay work. A
`recurring_schedule_dispatch_reviewed` audit event records the bounded
identifiers, fixed outcome, and whether the write changed durable state.
Operators must use provider-native idempotency and make any subsequent manual
action separately.

<a id="remote-schedule-dispatch-reviews--verification"></a>
### Verification

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_uncertain_dispatch_review_is_cas_idempotent_and_preserves_status \
  tests.test_service.RuntimeServiceTests.test_uncertain_dispatch_review_is_authenticated_cas_and_durable \
  tests.test_service_client.ServiceClientTests.test_recurring_dispatch_review_posts_cas_payload_and_fetches_projection \
  -v
```
<!-- end: remote-schedule-dispatch-reviews -->

<a id="remote-schedule-dispatches"></a>
<a id="remote-schedule-dispatches--remote-recurring-schedule-dispatch-diagnostics"></a>
## Remote Recurring-Schedule Dispatch Diagnostics

Loop 80 adds a bounded, authenticated read surface for diagnosing durable
recurring-schedule dispatches without shell access to the service host. It is
an operator evidence projection, not a scheduler control plane.

<a id="remote-schedule-dispatches--routes"></a>
### Routes

The loopback service accepts Bearer-authenticated `GET` requests to:

```text
GET /api/v1/recurring-schedule-dispatches
GET /api/v1/recurring-schedules/{schedule_id}/dispatches
```

The second route uses the same safe identifier grammar as schedule actions:
ASCII letters, digits, `_`, `-`, and `.`, with a maximum of 128 characters.
Requests must have no body. The route is available while the service is
starting or draining because it is read-only; it does not require scheduler
lease ownership.

The installed client exposes the same operation through:

```bash
skill2workflow service-recurring-dispatches \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /path/to/ingress.token

skill2workflow service-recurring-dispatches \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /path/to/ingress.token \
  --schedule-id schedule_hourly_report
```

<a id="remote-schedule-dispatches--fixed-response-and-redaction"></a>
### Fixed response and redaction

Successful responses use
`skill2workflow-recurring-schedule-dispatch-list-0.1.0`, defined by
[`schemas/recurring-schedule-dispatch-list-0.1.0.schema.json`](../schemas/recurring-schedule-dispatch-list-0.1.0.schema.json).
The projection contains fixed status counts, a chronological bounded window,
and compact dispatch metadata: dispatch ID, schedule ID, scheduled time,
status, coalesced occurrence count, run/trigger IDs, a sanitized error type,
and completion time.

It never returns trigger input, connector payloads, credential handles,
scheduler owner IDs, lease expiry timestamps, or raw persisted records. Error
types are limited to short identifier-like values; other values become an
empty string. The global and targeted reports are limited to 100 records and
64 KiB. The targeted response repeats the requested schedule ID and every
returned record must belong to it.

`uncertain` means the scheduler cannot prove whether the external effect was
observed before ownership was lost. Operators should inspect the linked run or
provider idempotency evidence before deciding whether to retry; this endpoint
does not replay or reconcile that effect.

Unauthenticated requests return a fixed `401`; provider authentication
failures return `503`; body-bearing requests and unavailable state use fixed
errors. Read requests do not append audit rows, but route counters remain
visible in the low-cardinality metrics export.

<a id="remote-schedule-dispatches--verification"></a>
### Verification

The focused evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_recurring_dispatch_list_is_bounded_and_excludes_lease_or_input_values \
  tests.test_service.RuntimeServiceTests.test_recurring_schedule_dispatch_list_is_authenticated_bounded_and_redacted \
  tests.test_service_client.ServiceClientTests.test_recurring_dispatch_list_uses_authenticated_global_and_targeted_paths \
  tests.test_cli.CliTests.test_service_recurring_dispatches_command_supports_schedule_filter \
  -v
```

This capability does not provide schedule mutation, lease ownership, bulk
retry, automatic reconciliation, RBAC, hosted TLS, or exactly-once provider
execution.
<!-- end: remote-schedule-dispatches -->

<a id="remote-schedule-inventory"></a>
<a id="remote-schedule-inventory--remote-recurring-schedule-inventory"></a>
## Remote Recurring Schedule Inventory

The self-hosted service exposes the durable recurring schedules needed for
remote operator diagnosis. The inventory itself remains read-only: it never
enables, disables, claims, dispatches, or rewrites a schedule. Protected state
changes are documented separately in [`remote-schedule-actions.md`](api-reference.md#remote-schedule-actions).

<a id="remote-schedule-inventory--http-contract"></a>
### HTTP Contract

```http
GET /api/v1/recurring-schedules
Authorization: Bearer <service-ingress-token>
```

The response follows
[`schemas/recurring-schedule-list-0.1.0.schema.json`](../schemas/recurring-schedule-list-0.1.0.schema.json)
and is versioned as `skill2workflow-recurring-schedule-list-0.1.0`. It contains
at most the latest 100 recurring definitions, fixed active/disabled counts,
workflow references, interval and missed-run policy, next scheduled time, and
compact last-run metadata. The response omits trigger input values, idempotency prefixes, scheduler
owner IDs, credentials, and provider payloads never cross the boundary.

The endpoint is available while the service is starting, draining, or standby
when authenticated SQLite state is readable. It does not acquire or inspect
the scheduler lease and returns `Cache-Control: no-store`. Responses are
bounded to 64 KiB. Missing authentication returns `401`; a non-empty request
body returns `400`; and a storage or response-bound failure returns the fixed
`{"error":"recurring schedule list unavailable"}` response.

<a id="remote-schedule-inventory--protected-cli-client"></a>
### Protected CLI client

```bash
skill2workflow service-recurring-schedules \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The CLI keeps the token out of argv, disables proxies and redirects, validates
the response headers and schema, and prints only the fixed redacted contract.
Use the protected `service-schedule-enable` and `service-schedule-disable`
commands for deliberate remote changes, or the local `schedule-enable`,
`schedule-disable`, and `schedule-dispatches` commands on the service host.

<a id="remote-schedule-inventory--evidence"></a>
### Evidence

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_recurring_schedule_list_is_bounded_and_excludes_trigger_input \
  tests.test_service.RuntimeServiceTests.test_recurring_schedule_list_is_authenticated_redacted_and_available_before_readiness \
  tests.test_service_client.ServiceClientTests.test_recurring_schedule_list_uses_authenticated_get_and_validates_contract \
  tests.test_service_client.ServiceClientTests.test_recurring_schedule_list_rejects_oversized_response \
  tests.test_cli.CliTests.test_service_recurring_schedules_command_prints_redacted_inventory \
  -v
```
<!-- end: remote-schedule-inventory -->

<a id="remote-schedule-patch"></a>
<a id="remote-schedule-patch--remote-recurring-schedule-patch"></a>
## Remote Recurring-Schedule Patch

The authenticated `PATCH /api/v1/recurring-schedules/{schedule_id}` endpoint
updates only non-sensitive schedule fields while preserving the stored trigger
input and durable dispatch progress. This is the safe remote alternative when
the inventory endpoint intentionally redacts trigger metadata.

The request body must contain exactly `schedule` and
`expected_next_run_at`:

```json
{
  "schedule": {
    "workflow_id": "workflow_service_v2",
    "version": "2.0.0",
    "interval_seconds": 120,
    "missed_run_policy": "latest",
    "enabled": true
  },
  "expected_next_run_at": "2026-08-11T00:01:00+00:00"
}
```

The safe fields are `workflow_id`, `version`, `starts_at`,
`interval_seconds`, `missed_run_policy`, and `enabled`; `schedule` may contain
only these fields. It must not contain an `id`, `status`, progress fields, or a
`trigger` object. Omitted fields remain unchanged. The path identifier is
authoritative. The server merges the patch inside the same `BEGIN IMMEDIATE`
transaction as the `expected_next_run_at` compare-and-swap check, so a stale
inventory is rejected with `409` and the response
`{ "error": "recurring schedule patch precondition failed" }`.

The response is the fixed redacted contract
`skill2workflow-recurring-schedule-patch-0.1.0`, described by
[`schemas/recurring-schedule-patch-0.1.0.schema.json`](../schemas/recurring-schedule-patch-0.1.0.schema.json).
It never includes trigger input, idempotency prefixes, or audit payloads.

The installed CLI accepts a JSON object containing only the safe patch fields:

```bash
skill2workflow service-recurring-schedule-patch schedule_service_report patch.json \
  --expected-next-run-at 2026-08-11T00:01:00+00:00 \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The operation requires the normal authenticated, ready SQLite service. It
does not change the existing full `PUT` update contract, and it does not claim
exactly-once provider execution.
<!-- end: remote-schedule-patch -->

<a id="remote-schedule-update"></a>
<a id="remote-schedule-update--remote-recurring-schedule-updates"></a>
## Remote recurring-schedule updates

Loop 155 adds a protected way to change one durable recurring schedule without
opening the service host shell or resetting dispatch progress. The operation is
designed to preserve durable dispatch progress and complements remote creation
and enable/disable actions.

<a id="remote-schedule-update--contract"></a>
### Contract

The endpoint requires the service Bearer token, readiness, and one exact
compare-and-swap body:

```text
PUT /api/v1/recurring-schedules/{schedule_id}
```

```json
{
  "schedule": {
    "schema_version": "skill2workflow-schedule-0.2.0",
    "schedule": {
      "id": "schedule_hourly_report",
      "workflow_id": "workflow_hourly_report",
      "version": "1.1.0",
      "starts_at": "2026-08-11T00:00:00Z",
      "interval_seconds": 3600,
      "missed_run_policy": "latest",
      "enabled": true
    },
    "trigger": {
      "idempotency_key_prefix": "schedule_hourly_report",
      "input": {"report": "hourly-v2"}
    }
  },
  "expected_next_run_at": "2026-08-11T01:00:00+00:00"
}
```

`expected_next_run_at` must equal the last value observed by the operator. The
SQLite store compares it inside the same `BEGIN IMMEDIATE` transaction used by
dispatcher claims. A stale value returns:

```json
{"error": "recurring schedule update precondition failed"}
```

with HTTP `409`. The update never accepts persisted progress fields from the
request. `next_run_at`, `last_scheduled_for`, `last_run_id`, and
`last_trigger_id` are copied from the durable row, so a successful update
cannot move scheduling backwards or erase dispatch evidence. The request must
include `schedule.enabled` explicitly to avoid accidentally re-enabling a
disabled schedule.

The response is the fixed redacted
[`recurring-schedule-update-0.1.0`](../schemas/recurring-schedule-update-0.1.0.schema.json)
contract. It returns scheduling metadata and `changed`, but never trigger
input, the derived source, or the idempotency-key prefix. Identical retries
return `200` with `changed: false`.

The request is bounded by the shared 1 MiB body/input limit and the response is
capped at 16 KiB. Unknown IDs return a fixed `404`; malformed bodies and
invalid definitions return fixed `400` errors. Authenticated ingress and
value-free definition-update evidence are written to the control-plane audit.

<a id="remote-schedule-update--cli"></a>
### CLI

```bash
skill2workflow service-recurring-schedule-update \
  schedule_hourly_report /path/to/recurring-schedule-v2.json \
  --expected-next-run-at 2026-08-11T01:00:00+00:00 \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The installed client validates the HTTPS-or-loopback origin, owner-only token
file, redirect policy, request/response bounds, schedule identifier, and the
complete response schema before printing it.

<a id="remote-schedule-update--boundary-and-verification"></a>
### Boundary and verification

This is a single-tenant recurring-definition update. It does not delete
schedules, change one-shot schedules, publish workflows, expose trigger
values, or claim exactly-once provider delivery. Use the existing inventory to
obtain `next_run_at`, then retry with that value if a concurrent dispatch causes
a `409`.

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules \
  tests.test_service_client \
  tests.test_service \
  tests.test_cli \
  tests.test_telemetry -v
```
<!-- end: remote-schedule-update -->

<a id="remote-trigger"></a>
<a id="remote-trigger--remote-workflow-trigger"></a>
## Remote Workflow Trigger

Loop 85 turns the existing authenticated webhook boundary into a usable
installed-CLI path. `service-trigger` starts one published workflow through the
self-hosted service without requiring callers to hand-build URLs or response
parsers.

<a id="remote-trigger--command"></a>
### Command

```bash
skill2workflow service-trigger workflow_approval_flow \
  --version production \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --idempotency-key partner-event-001 \
  --source partner-system \
  --input /path/to/non-secret-input.json
```

`--idempotency-key` is required. The client reads the Bearer token from the
owner-only token file, refuses ambiguous origins and redirects, and never
prints the token or request input. `--input` must contain one JSON object; an
omitted file means `{}`. Trigger inputs are durable run context, not a secret
store, so credentials and confidential payloads must stay outside the input
file.

<a id="remote-trigger--request-and-response-boundary"></a>
### Request and response boundary

The client calls the existing protected route:

```text
POST /webhooks/<workflow_id>/<version-or-alias>
Authorization: Bearer <single-team-token>
```

The canonical request envelope contains only `source`, `idempotency_key`, and
`input`. The shared canonical UTF-8 JSON-object input limit remains 1 MiB, and
the complete remote request is capped at the service's 1 MiB body boundary.
Workflow IDs and versions are validated as one safe path component before URL
quoting; aliases such as `production` are allowed.

The client validates the compact existing trigger response exactly:

```json
{
  "trigger_id": "trigger_opaque",
  "workflow_id": "workflow_approval_flow",
  "workflow_version": "0.1.0",
  "run_id": "run_opaque",
  "run_status": "waiting",
  "source": "partner-system",
  "idempotency_key": "partner-event-001",
  "input_keys": ["customer_id"]
}
```

The returned version is the resolved immutable version, even when the request
used an alias. The response contains keys rather than input values.

<a id="remote-trigger--retry-and-failure-semantics"></a>
### Retry and failure semantics

For SQLite service state, retrying the same workflow, requested version,
source, idempotency key, and canonical input replays the compact response
without starting a second run. Reusing the key with a different request, or
retrying an unresolved external outcome, returns `409`; the client surfaces a
fixed `trigger idempotency conflict` error. Authentication, malformed input,
oversized bodies, unavailable service, and missing workflows retain the
existing `401`, `400`, `413`, `503`, and `404` boundaries.

<a id="remote-trigger--verification"></a>
### Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service_client.ServiceClientTests.test_service_trigger_posts_bounded_idempotent_envelope \
  tests.test_service_client.ServiceClientTests.test_service_trigger_requires_idempotency_and_rejects_unsafe_path_before_network \
  tests.test_service_client.ServiceClientTests.test_service_trigger_rejects_oversized_complete_body_before_network \
  tests.test_cli.CliTests.test_service_trigger_command_loads_input_and_requires_retry_key \
  -v
```

The service boundary smoke also exercises the authenticated webhook with a
real service process and SQLite restart continuity.
<!-- end: remote-trigger -->

<a id="remote-workflow-artifacts"></a>
<a id="remote-workflow-artifacts--remote-workflow-artifact-consistency"></a>
## Remote Workflow Artifact Consistency

Loop 81 exposes the existing value-free `workflow-artifacts` consistency
diagnostic through the authenticated self-hosted service. This lets an
operator verify a deployment after a crash, manual state copy, backup restore,
or package cutover without shell access to the service host.

<a id="remote-workflow-artifacts--route-and-cli"></a>
### Route and CLI

```text
GET /api/v1/workflow-artifacts
Authorization: Bearer <single-team-token>
```

The request must not include a body. The route is read-only and remains
available while the service is starting, draining, or on standby when SQLite
state is readable. It does not acquire the scheduler lease, mutate registry
records, delete artifacts, or append audit events.

The installed client validates the existing
`skill2workflow-workflow-artifact-report-0.1.0` contract:

```bash
skill2workflow service-workflow-artifacts \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

<a id="remote-workflow-artifacts--fixed-report-and-bounds"></a>
### Fixed report and bounds

The report is the same schema used by the local `workflow-artifacts` command.
It contains aggregate registry/filesystem counts and at most 64 issue records
over the remote boundary, within a 64 KiB UTF-8 response bound. `summary.issue_count`
and `summary.truncated` retain the full-state count and indicate when the
returned issue window is incomplete.

Issue kinds are `missing`, `unsafe_reference`, `unsafe_artifact`, `invalid_json`,
`oversized`, `checksum_mismatch`, and `orphaned`. Each issue contains only its
kind, bounded artifact reference, and optional workflow/version identifiers.
Workflow titles, instructions, connector requests, checksums, trigger input,
credentials, and raw exception text are never returned.

An empty report has `status: "clean"`; any issue has `status: "attention"`.
The service returns fixed `401`, `400`, and `503` errors for authentication,
body, and state/response failures. Responses are `Cache-Control: no-store`.

<a id="remote-workflow-artifacts--operator-sequence"></a>
### Operator sequence

1. Fetch the report remotely and record the schema version, status, and counts.
2. If status is `attention`, use the bounded issue references to identify the
   affected state copy without attempting automatic repair.
3. Preserve the private state and follow [`backup-restore.md`](backup-restore.md)
   or [`upgrade-migration.md`](upgrade-migration.md) before manual repair.

The route does not repair or delete artifacts, rewrite registry checksums,
publish workflows, or claim a cross-database transaction boundary.

<a id="remote-workflow-artifacts--verification"></a>
### Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_remote_workflow_artifact_report_is_bounded_and_reuses_fixed_contract \
  tests.test_service.RuntimeServiceTests.test_workflow_artifact_report_is_authenticated_bounded_and_value_free \
  tests.test_service_client.ServiceClientTests.test_workflow_artifact_report_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_workflow_artifacts_command_prints_report \
  -v
```
<!-- end: remote-workflow-artifacts -->

<a id="remote-workflow-deprecation"></a>
<a id="remote-workflow-deprecation--remote-workflow-deprecation"></a>
## Remote Workflow Deprecation

Loop 90 adds a narrow authenticated lifecycle action for operators that need to
retire one published Workflow DSL version through the installed service
boundary. It is deliberately smaller than publication and promotion: the
service changes only the registry status and stable-alias metadata already
owned by the SQLite control plane. Protected callers can include the observed
checksum and alias set as a compare-and-swap (CAS) guard so stale inventory
cannot retire a version that changed while it was being reviewed.

<a id="remote-workflow-deprecation--command"></a>
### Command

```bash
skill2workflow service-workflow-deprecate workflow_approval_flow \
  --version 0.1.0 \
  --expected-checksum <64-lowercase-hex-digest> \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

Repeat `--expected-alias <alias>` for every alias observed in the inventory.
Use the CAS flags together; omitting both preserves the legacy operator
command. The live control-plane UI always uses the protected form and only
offers deprecation after all aliases have been removed.

The token file is read locally and is never printed. The command validates both
path components before making a request. The service remains loopback-bound by
default; an external TLS/authentication boundary is required for deployment
behind a proxy (see [`security-boundary.md`](security-boundary.md)).

<a id="remote-workflow-deprecation--fixed-http-contract"></a>
### Fixed HTTP contract

The legacy client sends exactly one bounded JSON object to
`POST /api/v1/workflow-deprecations`:

```json
{
  "workflow_id": "workflow_approval_flow",
  "version": "0.1.0"
}
```

Protected callers send the following exact form instead. `expected_aliases`
is sorted, unique, and may be empty:

```json
{
  "workflow_id": "workflow_approval_flow",
  "version": "0.1.0",
  "expected_checksum": "<64 lowercase hex characters>",
  "expected_aliases": []
}
```

The route requires a ready service, the active scheduler lease, and a valid
Bearer token. The request is limited to the shared 1 MiB JSON body bound. A
successful response is exactly:

```json
{
  "schema_version": "skill2workflow-workflow-deprecation-0.1.0",
  "workflow_id": "workflow_approval_flow",
  "version": "0.1.0",
  "status": "deprecated",
  "checksum": "<64 lowercase hex characters>"
}
```

The response is capped at 16 KiB and contains no artifact path, Workflow DSL,
alias list, timestamp, credential, or request value. A missing version returns
`404`; malformed input returns the fixed `400` error; a CAS mismatch returns
`409` and leaves the registry unchanged. The installed client maps the
conflict to its fixed redacted `409` error shape.

<a id="remote-workflow-deprecation--semantics-and-safety-boundary"></a>
### Semantics and safety boundary

Deprecation is an atomic SQLite registry mutation. It marks the selected
published version `deprecated`, removes any stable aliases from that version,
and appends one `workflow_deprecated` audit event. When CAS fields are supplied,
the checksum and complete alias set are checked inside the same transaction
before any mutation. Repeating the same request is idempotent: it returns the
same redacted record without appending a duplicate deprecation event. The
immutable published artifact remains on disk so the existing
artifact-consistency and backup checks can still account for it.

This action does not publish a new version, promote an alias, delete an
artifact, trigger a run, cancel a run, or export Workflow content. Operators
must explicitly publish and promote a replacement before directing new traffic
to it. Existing in-flight executions are not rewritten by deprecation.

<a id="remote-workflow-deprecation--verification"></a>
### Verification

The release qualification checks that the installed command is present. The
service integration drill covers denied and malformed requests, authenticated
deprecation, alias removal, redacted responses, idempotent replay, and exactly
one audit event. The complete suite is run with:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src \
  python3 -m unittest discover -s tests -q
```
<!-- end: remote-workflow-deprecation -->

<a id="remote-workflow-diff"></a>
<a id="remote-workflow-diff--remote-workflow-diff"></a>
## Remote Workflow Diff

Loop 88 adds a read-only remote review surface for the release path. The
protected `service-workflow-diff` command compares two exact published
Workflow DSL versions through the service, reusing the existing structural
diff contract. It returns identifiers, checksums, aliases, and changed
sections only; workflow values never cross the service boundary.

<a id="remote-workflow-diff--command"></a>
### Command

```bash
skill2workflow service-workflow-diff workflow_approval_flow \
  --from-version 0.1.0 \
  --to-version 0.2.0 \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The client reads the Bearer token from an owner-only file, rejects redirects
and ambiguous origins, validates the safe workflow references, and enforces a
64 KiB response bound. The route is read-only and does not require readiness or
the scheduler lease.

<a id="remote-workflow-diff--request-boundary"></a>
### Request boundary

```text
GET /api/v1/workflow-diffs/<workflow_id>/<from_version>/<to_version>
Authorization: Bearer <single-team-token>
```

The request has no body. Path components are URL-quoted by the client and use
the same safe reference validation as remote trigger and promotion commands.
Missing versions return `404`; malformed bodies or paths return `400`/`404`;
unavailable or unverifiable artifacts return `503`.

<a id="remote-workflow-diff--fixed-response"></a>
### Fixed response

The response is exactly the existing
`skill2workflow-workflow-diff-0.1.0` contract documented in
[`workflow-releases.md`](workflow-releases.md) and
[`schemas/workflow-diff-0.1.0.schema.json`](../schemas/workflow-diff-0.1.0.schema.json).
It contains no titles, descriptions, connector requests, input values,
credentials, artifact paths, or arbitrary field values.

This route does not promote aliases, publish versions, trigger runs, approve a
release, or provide semantic business-risk analysis. Operators still choose
the target and use `service-workflow-promote` with an expected-current-version
guard when moving the alias.

<a id="remote-workflow-diff--verification"></a>
### Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_diff_is_authenticated_value_free_and_read_only \
  tests.test_service_client.ServiceClientTests.test_service_workflow_diff_uses_fixed_redacted_contract \
  tests.test_cli.CliTests.test_service_workflow_diff_command_uses_version_options \
  -v
```
<!-- end: remote-workflow-diff -->

<a id="remote-workflow-inventory"></a>
<a id="remote-workflow-inventory--remote-workflow-inventory"></a>
## Remote Workflow Inventory

Loop 91 adds a bounded, authenticated read surface for the published Workflow
registry. Remote publication, diff, promotion, and deprecation are useful only
if an operator can first discover which versions exist; this endpoint supplies
that missing inventory without exporting Workflow content or filesystem data.

<a id="remote-workflow-inventory--command"></a>
### Command

```bash
skill2workflow service-workflows \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The token is read from the owner-only file and is never printed. The command
uses the same redirect, proxy, origin, response-size, and Bearer-token
boundaries as the other installed service clients.

<a id="remote-workflow-inventory--fixed-http-contract"></a>
### Fixed HTTP contract

The client sends an authenticated body-less `GET /api/v1/workflows`. The route
is available while the service is starting, draining, or standby, provided
authentication and SQLite state are readable. It does not acquire the scheduler
lease and does not append audit state.

The response is capped at 64 KiB and contains at most 100 versions:

```json
{
  "schema_version": "skill2workflow-workflow-inventory-0.1.0",
  "summary": {
    "total": 2,
    "status_counts": {"published": 1, "deprecated": 1, "other": 0}
  },
  "versions": [
    {
      "workflow_id": "workflow_approval_flow",
      "version": "0.2.0",
      "status": "published",
      "aliases": ["production"],
      "checksum": "<64 lowercase hex characters>"
    }
  ],
  "window": {"max_items": 100, "total": 2, "returned": 1, "truncated": true}
}
```

Only stable identifiers, lifecycle status, bounded aliases, and checksums cross
the boundary. The response never includes the Workflow name or DSL, artifact
path, `published_at`/`deprecated_at`, audit events, credentials, trigger input,
or provider data. The client validates the exact schema, status counts, window
arithmetic, and lowercase SHA-256 checksums before printing anything.

<a id="remote-workflow-inventory--operator-sequence-and-safety-boundary"></a>
### Operator sequence and safety boundary

Use `service-workflows` to select known versions, `service-workflow-diff` to
review a structural change, `service-workflow-promote` with an expected-current
version to move an alias, and `service-workflow-deprecate` to retire a version.
Inventory is read-only: it does not publish, promote, deprecate, trigger,
repair, delete artifacts, or perform semantic business-risk analysis.

Invalid body, transfer encoding, malformed state, authentication failure, and
oversized responses fail with fixed generic errors. No user-controlled value is
turned into a telemetry label or error detail.

<a id="remote-workflow-inventory--verification"></a>
### Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_inventory_is_authenticated_bounded_and_read_only \
  tests.test_service_client.ServiceClientTests.test_service_workflow_inventory_uses_fixed_redacted_contract \
  tests.test_cli.CliTests.test_service_workflows_command_prints_inventory \
  -v
```
<!-- end: remote-workflow-inventory -->

<a id="remote-workflow-promotion"></a>
<a id="remote-workflow-promotion--remote-workflow-promotion"></a>
## Remote Workflow Promotion

Loop 87 closes the controlled CI/CD path after remote publication. The
protected `service-workflow-promote` command moves one immutable published
version to a stable alias through the service, using the existing SQLite
compare-and-swap transaction. It does not publish, trigger, or mutate the
Workflow DSL artifact.

<a id="remote-workflow-promotion--command"></a>
### Command

```bash
skill2workflow service-workflow-promote workflow_approval_flow \
  --version 0.2.0 \
  --alias production \
  --expected-current-version 0.1.0 \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

`--expected-current-version` is optional for a first promotion, but is
recommended whenever an operator is moving an existing alias. If another
operator moves the alias first, the request fails with `409` and makes no
alias or audit change.

<a id="remote-workflow-promotion--request-boundary"></a>
### Request boundary

```text
POST /api/v1/workflow-promotions
Authorization: Bearer <single-team-token>
```

The JSON body is exactly:

```json
{
  "workflow_id": "workflow_approval_flow",
  "version": "0.2.0",
  "alias": "production",
  "expected_current_version": "0.1.0"
}
```

The service requires readiness and the active scheduler lease. Workflow and
alias identifiers use the same safe grammar as the local `promote` command;
the complete request is capped at 1 MiB. The token is read from an owner-only
file and is never included in the request body or output.

<a id="remote-workflow-promotion--fixed-response"></a>
### Fixed response

Successful promotion returns exactly:

```json
{
  "schema_version": "skill2workflow-workflow-promotion-0.1.0",
  "workflow_id": "workflow_approval_flow",
  "version": "0.2.0",
  "alias": "production",
  "status": "promoted",
  "checksum": "sha256-hex"
}
```

The response contains no filesystem path, workflow content, credentials, or
request values beyond the selected identifiers. Missing target versions return
`404`; a stale expected version returns `409`; malformed requests return
`400`; an unavailable service or state store returns `503`.

SQLite couples the compare-and-swap check, alias metadata update, and
`workflow_promoted` audit row in one transaction. A repeated promotion to the
same alias target is safe and returns the same fixed summary. This route does
not publish or deprecate versions, trigger runs, upload artifacts, perform
rollbacks, or claim exactly-once provider effects.

<a id="remote-workflow-promotion--verification"></a>
### Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_promotion_is_authenticated_cas_and_redacted \
  tests.test_service_client.ServiceClientTests.test_service_workflow_promote_uses_fixed_contract \
  tests.test_cli.CliTests.test_service_workflow_promote_command_uses_cas_options \
  -v
```
<!-- end: remote-workflow-promotion -->

<a id="remote-workflow-release"></a>
<a id="remote-workflow-release--remote-workflow-publication"></a>
## Remote Workflow Publication

Loop 86 adds one controlled CI/CD entry point for a self-hosted service. The
protected `service-workflow-publish` command sends one Workflow DSL document to
the service, which reuses the existing immutable SQLite publication transaction
and returns a redacted record. Version promotion remains a separate operator
decision and is not performed by this command.

<a id="remote-workflow-release--command"></a>
### Command

```bash
skill2workflow service-workflow-publish \
  /path/to/workflow.workflow.json \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The client reads the Bearer token from an owner-only file, refuses ambiguous
origins and redirects, and never prints the submitted Workflow DSL or service
artifact path. The service requires readiness and the active SQLite scheduler
lease before accepting the mutation.

<a id="remote-workflow-release--request-boundary"></a>
### Request boundary

```text
POST /api/v1/workflow-releases
Authorization: Bearer <single-team-token>
```

The JSON body is exactly `{"workflow": <Workflow DSL object>}`. The complete
request is capped at 1 MiB, and the existing Workflow DSL validator remains the
source of truth for schema and graph validity. Invalid requests are rejected
before publication. Do not put credentials, access tokens, or confidential
business payloads in a workflow artifact; credential handles remain references
to the separate local provider boundary.

<a id="remote-workflow-release--release-preflight"></a>
### Release preflight

```bash
skill2workflow service-workflow-release-preflight \
  /path/to/workflow.workflow.json \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

```text
POST /api/v1/workflow-release-preflights
Authorization: Bearer <single-team-token>
```

The body is the same exact `{"workflow": <Workflow DSL object>}` envelope and
uses the same 1 MiB request bound. It is a side-effect-free check for an
*unpublished* document: the service validates the DSL, inspects the empty
trigger shape, and returns only bounded structural counts and issue paths.
It does not create an artifact or registry record, append an audit event,
resolve credentials, or invoke a connector. `empty_trigger_ready: false` means
the workflow needs trigger input; it is not a publication failure.

Successful preflight returns exactly these top-level fields:

```json
{
  "schema_version": "skill2workflow-workflow-release-preflight-0.1.0",
  "workflow": {"id": "workflow_approval_flow", "version": "0.1.0"},
  "document_valid": true,
  "empty_trigger_ready": false,
  "summary": {},
  "issues": [],
  "safety": {
    "side_effect_free": true,
    "connector_calls": false,
    "credentials_resolved": false,
    "raw_values_included": false
  }
}
```

Malformed envelopes or invalid DSL return `400`; an oversized body returns
`413`; unavailable service/state returns `503`. The installed live console uses
this route as a required staged-file check before exposing its separate publish
confirmation, and the CLI prints the same value-free report without publishing
the document.

<a id="remote-workflow-release--publication-target-review"></a>
### Publication-target review

Before an operator asks the service to publish, it can also inspect the exact
immutable target at the instant of the read:

```bash
skill2workflow service-workflow-release-target-review \
  /path/to/workflow.workflow.json \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

```text
POST /api/v1/workflow-release-target-reviews
Authorization: Bearer <single-team-token>
```

The exact request envelope and 1 MiB bound are the same as release preflight.
The fixed `skill2workflow-workflow-release-target-review-0.1.0` response
contains only the workflow id/version, SHA-256 recognition digests, the existing
target state, and the existing value-free preflight projection. It never returns
the candidate DSL or published DSL, credentials, paths, or business values.

`target.state` is one of:

- `new`: no matching `workflow_id@version` was present at the read;
- `idempotent`: the matching immutable record has the exact candidate digest;
- `conflict`: a matching record exists with a different digest.

`publication_ready` is true for `new` and `idempotent`; an
`empty_trigger_ready: false` candidate can still be published when its trigger
contract requires input. The review is read-only and writes neither a registry
record nor an audit event. It is an advisory point-in-time result, not a lock,
reservation, authorization, or compare-and-swap precondition: another publisher
can win the target after the response. The subsequent immutable publish route
remains the authoritative atomic conflict decision.

<a id="remote-workflow-release--fixed-response"></a>
### Fixed response

Successful publication returns exactly:

```json
{
  "schema_version": "skill2workflow-workflow-release-0.1.0",
  "workflow_id": "workflow_approval_flow",
  "version": "0.1.0",
  "status": "published",
  "checksum": "sha256-hex"
}
```

The response contains no filesystem path, workflow content, credentials, or
request values. Publishing the same immutable version with identical content
is safe to retry and returns the same compact record. Publishing different
content under an existing version returns `409`; malformed DSL and envelope
errors return `400`; an oversized body returns `413`; unavailable service/state
returns `503`.

The server reuses the existing publication transaction: SQLite couples the
immutable artifact, registry record, and `workflow_published` audit row. This
route does not promote an alias, trigger a run, deprecate a version, or upload
an artifact elsewhere.

<a id="remote-workflow-release--verification"></a>
### Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_publication_is_authenticated_immutable_and_redacted \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_release_preflight_validates_unpublished_document_without_writing \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_release_target_review_is_authenticated_read_only_and_race_advisory \
  tests.test_service_client.ServiceClientTests.test_service_workflow_publish_uses_fixed_contract \
  tests.test_service_client.ServiceClientTests.test_service_workflow_release_preflight_uses_fixed_value_free_contract \
  tests.test_service_client.ServiceClientTests.test_service_workflow_release_target_review_uses_fixed_value_free_contract \
  tests.test_cli.CliTests.test_service_workflow_release_preflight_command_loads_unpublished_workflow \
  tests.test_cli.CliTests.test_service_workflow_release_target_review_command_loads_candidate \
  tests.test_cli.CliTests.test_service_workflow_publish_command_loads_workflow \
  -v
```
<a id="remote-workflow-release--verified-authoring-set-handoff"></a>
### Verified Authoring-Set Handoff

For a local authoring directory created by `authoring-export`, prefer
`authoring-service-release-preflight <authoring-dir>` and
`authoring-service-release-target-review <authoring-dir>` and
`authoring-service-publish <authoring-dir>` over reopening its `workflow.json`.
They load only the descriptor-bound bytes that pass complete authoring
verification before using the existing authenticated service routes. Preflight,
target review, and publication remain separate explicit actions; neither starts
a run.
<!-- end: remote-workflow-release -->
