# Self-hosted Runtime Service

Loop 87 adds protected remote Workflow promotion through
[`remote-workflow-promotion.md`](remote-workflow-promotion.md); it reuses the
SQLite compare-and-swap alias transaction and returns only a fixed summary.
Loop 88 adds the read-only remote Workflow diff documented in
[`remote-workflow-diff.md`](remote-workflow-diff.md).
Loop 90 adds the protected remote Workflow deprecation action documented in
[`remote-workflow-deprecation.md`](remote-workflow-deprecation.md).
Loop 91 adds the bounded remote Workflow inventory documented in
[`remote-workflow-inventory.md`](remote-workflow-inventory.md).
Loop 178 adds the read-only Workflow explanation documented in
[`workflow-explanation.md`](workflow-explanation.md).
Loop 179 adds the side-effect-free trigger preflight documented in
[`workflow-preflight.md`](workflow-preflight.md).
Loop 180 adds the local-only Workflow DSL bundle format documented in
[`workflow-bundles.md`](workflow-bundles.md); it does not add a service upload
route or change the authenticated runtime boundary.
Loop 92 adds the policy-bound remote retention preflight documented in
[`remote-retention-readiness.md`](remote-retention-readiness.md).
The installed `service-retention-readiness` client wraps the exact policy
envelope and fixed response contract.
Loop 93 adds the aggregate [`remote-operational-readiness.md`](remote-operational-readiness.md)
report and its installed `service-operational-readiness` client.
Loop 95 adds the unauthenticated, read-only [`service-probe.md`](service-probe.md)
client for deployment cutovers; it composes the existing `/healthz` and
`/readyz` endpoints without adding a route or exposing response bodies.
Loop 96 makes all authenticated service request bodies exact-length reads, so
early EOF cannot be parsed as a complete request.
Loop 97 adds a fail-closed exception boundary around request dispatch: an
unexpected handler failure returns only `503 {"error":"service unavailable"}`
and never exposes the exception text.
Loop 98 isolates lifecycle event logging from service control flow: a failing
operational collector cannot abort startup, leave scheduler threads running,
raise from a shutdown signal, or mask final cleanup.
Loop 99 makes service teardown structural: scheduler-start failures close the
listener and transition to `stopped`, while scheduler-stop failures cannot
leave the bound listener open or prevent the final lifecycle state.
Loop 101 makes remote operator retries cross-database safe: resume and
cancellation can repair missing control-plane audit evidence after a durable
run-state commit without replaying execution; recurring schedule actions keep
their idempotent `changed: false` recovery path.
Loop 103 makes the authenticated `/metrics` route a uniform zero-body read
surface by applying shared request-body and transfer-encoding validation before
telemetry rendering.
Loop 104 preserves a shutdown request that arrives during scheduler startup;
the service now drains directly instead of publishing `ready` or entering the
HTTP request loop after termination has begun.
Loop 105 makes the lifecycle transition itself atomic across the serving thread
and shutdown callers, preserving both the state decision and ordered lifecycle
events when shutdown races the `ready` publication.
Loop 106 adds an atomic shutdown admission boundary: mutating routes receive a
bounded `503` with `Retry-After` after `draining` is published, while health,
readiness, metrics, and read-only operator diagnostics remain available for
investigation.
Loop 107 closes the matching scheduler boundary: once `draining` is published,
the recurring dispatcher admits no new scheduled trigger, while one dispatch
already admitted may finish under the existing uncertain-outcome contract.
Loop 108 exposes the live, label-free `skill2workflow_service_inflight_requests`
gauge through `/metrics`, making the fixed request-admission pressure and
graceful-drain progress visible without changing the support-bundle 0.1.0
contract.
Loop 109 adds the matching label-free
`skill2workflow_scheduler_dispatch_inflight` gauge, so an already-admitted
background recurring dispatch is visible while graceful drain waits for it.
Loop 110 adds the installed `service-wait` client command, which polls the
existing public probes with bounded timeout and interval values for safe
startup/cutover automation; it adds no route or authentication bypass.

Loop 151 adds the bounded [`service-soak-smoke.py`](../scripts/service_soak_smoke.py)
cutover drill. It repeats real-process startup, authenticated triggers,
idempotency replay/conflict checks, graceful shutdown, and SQLite/audit
continuity without changing the service protocol or claiming hosted capacity.

Loop 154 adds the authenticated, idempotent recurring-schedule create route and
the installed `service-recurring-schedule-add` client documented in
[`remote-schedule-create.md`](remote-schedule-create.md). It accepts one exact
schedule wrapper, protects identical retries and changed-definition conflicts,
and returns only the fixed redacted response.
Loop 155 adds the protected `PUT /api/v1/recurring-schedules/{schedule_id}`
route and installed `service-recurring-schedule-update` client documented in
[`remote-schedule-update.md`](remote-schedule-update.md). It requires the
operator's last observed `next_run_at` as a compare-and-swap precondition and
preserves all durable dispatch progress while replacing author-controlled
definition fields.
Loop 156 adds the protected `DELETE /api/v1/recurring-schedules/{schedule_id}`
route and installed `service-recurring-schedule-delete` client documented in
[`remote-schedule-delete.md`](remote-schedule-delete.md). It requires explicit
confirmation, a disabled schedule, and no active claim while retaining
historical dispatch evidence and making retries safe with a tombstone.
Loop 157 hardens the existing enable/disable actions documented in
[`remote-schedule-actions.md`](remote-schedule-actions.md): the legacy empty
body remains compatible, while an optional `expected_next_run_at` is compared
inside the dispatcher transaction to reject stale operator intent.
Loop 158 adds the protected `PATCH /api/v1/recurring-schedules/{schedule_id}`
route and installed `service-recurring-schedule-patch` client documented in
[`remote-schedule-patch.md`](remote-schedule-patch.md). It merges only safe
schedule fields, preserves the redacted trigger and durable progress, and
uses the same `next_run_at` compare-and-swap boundary.
Loop 159 adds a separate cursor-paged recurring dispatch diagnostics route and
the installed `service-recurring-dispatch-page` client documented in
[`remote-schedule-dispatch-pages.md`](remote-schedule-dispatch-pages.md);
the original fixed recent-tail dispatch contract remains unchanged.
Loop 160 adds the authenticated, read-only backup inventory route and the
installed `service-backup-inventory` client documented in
[`remote-backup-inventory.md`](remote-backup-inventory.md). Bootstrap records
optional owner-only `runtime.backup_parent_dir`; deployments may also set the
exact-origin `runtime.http_allowed_origins` service boundary through repeated
`service-init --http-allowed-origin` options; the route returns only
bounded integrity, age, layout, and size metadata and remains available for
diagnostics while the service is draining or on standby.
Loop 161 adds the cursor-paged backup inventory route and installed
`service-backup-inventory-page` client documented in
[`remote-backup-inventory-pages.md`](remote-backup-inventory-pages.md). The
separate redacted page contract walks older backup evidence with an opaque
continuation cursor while preserving the exact Loop 160 recent-window route.
Loop 162 adds the authenticated, read-only backup retention plan route and
installed `service-backup-retention-plan` client documented in
[`remote-backup-retention-plan.md`](remote-backup-retention-plan.md). It reuses
the local policy and complete-inventory check while returning only aggregate
counts and byte totals; truncated inventories are blocked and no backup is
mutated. Loop 163 stops that preflight after the first over-budget directory,
so a remote request cannot traverse an arbitrarily large backup parent before
returning the already-determined block. The existing inventory and page routes
retain their complete-count and paging semantics.
Loop 164 applies the same source-boundary discipline to bounded local
one-shot schedule discovery: `schedule-run-due --max-items` retains only the
earliest normalized records, while the complete due-run and complete-list
compatibility paths remain unchanged.

Loop 165 adds a fixed 2 MiB UTF-8 envelope to every local one-shot schedule
document read (including compact inventory and due discovery), with a second
bounded-read check for files that grow after `stat`. Oversized documents fail
closed before JSON normalization; recurring SQLite schedule documents and the
1 MiB trigger-input contract remain unchanged.

Loop 166 adds the shared local CLI JSON input boundary documented in
[`cli-input-boundary.md`](cli-input-boundary.md). Generic JSON operands are
limited to 8 MiB of UTF-8 bytes, growth-raced reads fail closed, and uncaught
operator-input failures return a stable non-zero exit without a traceback.
This does not change the service's HTTP body limits or its authenticated
single-tenant boundary.

Loop 167 hardens the startup configuration read described in
[`service-config-boundary.md`](service-config-boundary.md). The runtime and
Doctor accept at most 64 KiB, reject symlinks and non-regular files, bind the
read to one device/inode, and fail closed on growth or replacement races. The
generated workspace continues to publish its configuration as owner-only
`0600`; hand-made configurations remain subject to the separate Doctor
permission checks.

The `service` command is the long-running, single-tenant runtime boundary delivered by Loop 41. It serves health, readiness, authenticated aggregate metrics, a bounded live Operator snapshot, a redacted recurring-schedule inventory, redacted run discovery and detail views, a redacted support bundle, published-workflow triggers, protected Workflow DSL publication, authenticated human-gate decisions, and durable cooperative run cancellation. SQLite service triggers enforce durable idempotency before execution; see [`triggers.md`](triggers.md). Workflow DSL remains the execution source of truth. Loop 49 adds execution ownership and fail-closed interrupted-run recovery; see [`interrupted-recovery.md`](interrupted-recovery.md). Loop 68 adds fixed concurrent business-request admission so slow or retried requests cannot consume an unbounded amount of active service work. Loop 69 adds explicit stable workflow version aliases; service triggers resolve them through the same control-plane boundary.

The HTTP control plane and recurring dispatcher share the scheduler lease owner.
Graceful drain withdraws both mutating HTTP admission and new recurring-dispatch
admission, then waits for in-flight HTTP handlers before releasing that lease. A
dispatch already admitted before draining may finish under the existing
uncertain-outcome contract. After
an ungraceful process loss, a replacement becomes ready only after lease expiry and
marks foreign active execution tickets `interrupted`; it never automatically
replays an external request with an unknown outcome.

The same lease owner runs the bounded `workflow_timeout_ms` deadline sweep. It
atomically expires waiting runs about once per second, gives pending
cooperative cancellation precedence, and reconciles the fixed `run_failed`
audit evidence without executing a successor.

Loop 118 adds per-node `timeout_ms` safe-point enforcement to the shared
executor. A connector node's active work and retry backoff stay within its
declared bound; human-gate waiting is paused, and a `node_timeout` failure is
persisted without following a successor. This does not forcefully abort a
provider request already in flight.

Loop 119 adds a fixed 1 MiB payload boundary to the built-in HTTP connector.
Serialized request bodies fail before network I/O when oversized, and success
or error response bodies are bounded before they can enter run state. Invalid
UTF-8 responses use a fixed connector failure. External connector fixtures
retain their own explicit I/O contract.

Loop 120 publishes a fresh SQLite `state-layout.json` through a fully-written,
fsynced temporary file and a non-overwriting link. Concurrent starters sharing
one empty state directory therefore cannot parse a partial marker; this does
not add distributed locking or replication.

This boundary is intentionally loopback-only and uses SQLite. Loop 42 adds mandatory single-team Bearer authentication and execution-time directory credentials. Loop 43 adds durable recurring dispatch and an active/standby lease for processes sharing one state directory. Loop 46 adds low-cardinality metrics and allowlisted operational NDJSON. Loop 48 adds authenticated, idempotent, cooperative cancellation. Loop 57 adds the authenticated human-gate decision route documented in [`human-approval.md`](human-approval.md). Loop 59 adds the bounded redacted run detail route documented in [`run-detail.md`](run-detail.md). Loop 60 adds bounded redacted run discovery documented in [`run-list.md`](run-list.md). Loop 61 adds the bounded redacted support bundle documented in [`support-bundle.md`](support-bundle.md). Loop 78 adds the read-only recurring schedule inventory documented in [`remote-schedule-inventory.md`](remote-schedule-inventory.md). Loop 79 adds protected, idempotent recurring schedule state actions documented in [`remote-schedule-actions.md`](remote-schedule-actions.md). Loop 80 adds bounded, redacted recurring dispatch diagnostics documented in [`remote-schedule-dispatches.md`](remote-schedule-dispatches.md). Loop 81 adds remote workflow artifact consistency diagnostics documented in [`remote-workflow-artifacts.md`](remote-workflow-artifacts.md). Loop 82 adds remote backup readiness documented in [`remote-backup-readiness.md`](remote-backup-readiness.md). Loop 83 adds remote audit-chain verification documented in [`remote-audit-integrity.md`](remote-audit-integrity.md). Loop 84 adds remote runtime identity documented in [`remote-runtime-info.md`](remote-runtime-info.md). Loop 86 adds protected remote Workflow publication documented in [`remote-workflow-release.md`](remote-workflow-release.md). Loop 89 adds local ingress-token rotation documented in [`service-token-rotation.md`](service-token-rotation.md). Loop 90 adds protected remote Workflow deprecation documented in [`remote-workflow-deprecation.md`](remote-workflow-deprecation.md). Loop 91 adds bounded remote Workflow inventory documented in [`remote-workflow-inventory.md`](remote-workflow-inventory.md). Loop 92 adds authenticated, policy-bound retention readiness documented in [`remote-retention-readiness.md`](remote-retention-readiness.md). The complete security and external TLS termination contract is documented in [`security-boundary.md`](security-boundary.md), scheduler semantics in [`recurring-scheduling.md`](recurring-scheduling.md), telemetry semantics in [`observability.md`](observability.md), and cancellation semantics in [`cancellation.md`](cancellation.md).

## Configuration

The service accepts one versioned JSON configuration file. Use an absolute state path so restarts resolve the same durable state independently of the process working directory.

For a new installation, [`service-bootstrap.md`](service-bootstrap.md) provides
the non-overwriting `service-init` command that generates this configuration,
an owner-only ingress token, the connector credential directory, and the state
directory together.

Use [`service-token-rotation.md`](service-token-rotation.md) and the local
`service-token-rotate` command to atomically replace the ingress credential
without restarting the service. The command never prints the token and is not
exposed as a remote API.

For one manually reviewed Linux systemd supervisor definition, use
[`systemd-service.md`](systemd-service.md) only after the generated workspace
passes the Doctor. The runtime does not start, install, or enable a supervisor
itself.

The manual configuration shape is:

The machine-readable shape is published at [`schemas/service-config-0.2.0.schema.json`](../schemas/service-config-0.2.0.schema.json); runtime validation additionally enforces absolute paths and usable security providers.

```json
{
  "schema_version": "skill2workflow-service-0.2.0",
  "service": {
    "host": "127.0.0.1",
    "port": 8080
  },
  "runtime": {
    "state_dir": "/var/lib/skill2workflow",
    "storage": "sqlite",
    "backup_parent_dir": "/var/backups/skill2workflow",
    "http_allowed_origins": [
      "https://api.example.com",
      "https://lark.example.com"
    ]
  },
  "auth": {
    "provider": "bearer_token_file",
    "token_file": "/run/secrets/skill2workflow-ingress-token"
  },
  "credentials": {
    "provider": "directory",
    "directory": "/run/secrets/skill2workflow-connectors"
  }
}
```

Validation is fail-closed: unknown fields, a wrong schema version, missing security providers, relative paths, JSON storage, an invalid port, a non-loopback bind address, or malformed service-level HTTP origins prevent startup. The token file and credential directory must be usable before readiness. Port `0` is accepted for test harnesses that need an operating-system-assigned port. Service-level HTTP origins are exact origins, not wildcard patterns; requests must also satisfy any workflow-level allowlist.

After installing the package, start the service with:

```bash
skill2workflow service --config /etc/skill2workflow/service.json
```

Before startup or cutover, run the read-only [operational readiness
Doctor](service-doctor.md):

```bash
skill2workflow service-doctor --config /etc/skill2workflow/service.json
```

It checks the fixed configuration, authentication, credential-directory,
state, and loopback-bind boundaries without starting the service or modifying
the workspace. A passing Doctor is a preflight signal; `GET /readyz` remains
the authoritative live signal after the process owns its scheduler lease.

For a live deployment gate, use the fixed, unauthenticated service probe:

```bash
skill2workflow service-probe --service-url https://service.example
```

Require exit code `0` (`status: "ready"`) before routing application traffic.
See [`service-probe.md`](service-probe.md) for the contract and the distinct
`not_ready` versus `unavailable` exit states.

For a bounded restart or rollout wait, use the same contract without writing a
custom polling loop:

```bash
skill2workflow service-wait \
  --service-url https://service.example \
  --timeout-seconds 60 \
  --poll-interval-seconds 1
```

From a source checkout, the equivalent command is:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli service \
  --config /etc/skill2workflow/service.json
```

## HTTP Boundary

| Request | Behavior |
| --- | --- |
| `GET /healthz` | Confirms that the process HTTP boundary is alive. |
| `GET /readyz` | Returns `200` only while the service accepts work, its providers and SQLite control state are usable, and this process owns the scheduler lease. |
| `GET /metrics` | Requires Bearer authentication and exports aggregate Prometheus text metrics, including while the process is not ready. |
| `GET /api/v1/control-snapshot` | Requires Bearer authentication and returns a read-only, 100-item-per-collection, 1 MiB Operator snapshot without appending persisted audit state. |
| `GET /api/v1/workflow-artifacts` | Requires Bearer authentication and returns the fixed value-free workflow artifact consistency report with at most 64 remote issue records and a 64 KiB response cap. It does not repair registry or filesystem state. |
| `GET /api/v1/backup-readiness` | Requires Bearer authentication and returns the fixed offline-backup preflight with layout, artifact-count, and active-lease metadata within 16 KiB; it does not create or upload a backup. |
| `GET /api/v1/backup-inventory` | Requires Bearer authentication and an empty body. Returns at most 100 redacted configured-backup integrity/age/layout/size entries within 64 KiB; it never exposes backup names or paths and does not mutate backups. See [`remote-backup-inventory.md`](remote-backup-inventory.md). |
| `GET /api/v1/backup-inventory-pages` | Requires Bearer authentication and an empty body. Returns one newest-first, at-most-100 redacted backup page within 64 KiB; `window.next_cursor` continues toward older entries without exposing names or paths. Malformed cursors return fixed `400`; missing or unsafe backup configuration returns fixed `503`. See [`remote-backup-inventory-pages.md`](remote-backup-inventory-pages.md). |
| `POST /api/v1/backup-retention-plan` | Requires Bearer authentication and exactly `{"policy": <backup retention policy>}`. Returns the fixed redacted aggregate plan within 16 KiB; incomplete inventories return `blocked` with null summary values, while ready plans report eligible/preserved counts and bytes. It never deletes or exposes backup names, paths, manifests, or workflow values. See [`remote-backup-retention-plan.md`](remote-backup-retention-plan.md). |
| `POST /api/v1/retention-readiness` | Requires Bearer authentication and exactly `{"policy": <retention policy>}`. Returns the fixed retention preflight within 16 KiB; an active lease blocks the plan and counts remain null, while a quiesced current-layout read returns aggregate eligibility only. It never applies retention or mutates state. See [`remote-retention-readiness.md`](remote-retention-readiness.md). |
| `GET /api/v1/operational-readiness` | Requires Bearer authentication and no body. Returns the fixed aggregate service/artifact/audit/backup readiness report within 16 KiB; it does not mutate lifecycle or state and does not claim an atomic cross-database snapshot. See [`remote-operational-readiness.md`](remote-operational-readiness.md). |
| `GET /api/v1/audit-integrity` | Requires Bearer authentication and returns the fixed payload-free SQLite audit-chain verification result within 16 KiB; it does not repair or rewrite audit state. |
| `GET /api/v1/runtime-info` | Requires Bearer authentication and returns fixed package, compatibility-line, state-layout, lifecycle, readiness, and lease metadata within 16 KiB; it does not expose paths or configuration values. |
| `GET /api/v1/workflows` | Requires Bearer authentication and no body. Returns at most 100 redacted published-version records, fixed lifecycle counts, aliases, and checksums within 64 KiB without acquiring the scheduler lease or mutating state; the installed `service-workflows` client wraps this route. See [`remote-workflow-inventory.md`](remote-workflow-inventory.md). |
| `GET /api/v1/workflow-explanations/{workflow_id}/{version}` | Requires Bearer authentication and no body. Returns the fixed, side-effect-free `skill2workflow-workflow-explanation-0.1.0` execution plan for one published version within 64 KiB; it excludes connector values, credentials, instructions, and trigger inputs and does not mutate state. The installed `service-workflow-explain` client wraps this route. See [`workflow-explanation.md`](workflow-explanation.md). |
| `POST /api/v1/workflow-preflights/{workflow_id}/{version}` | Requires Bearer authentication and either an empty body or exactly `{"input": <object>}`. Returns the fixed `skill2workflow-workflow-preflight-0.1.0` admission report within 64 KiB; it validates input and request mappings without calling connectors, resolving credentials, writing state, or returning values. The installed `service-workflow-preflight` client wraps this route. See [`workflow-preflight.md`](workflow-preflight.md). |
| `POST /api/v1/workflow-release-preflights` | Requires readiness and Bearer authentication with exactly `{"workflow": <object>}` within the 1 MiB request bound. Validates one unpublished DSL document and returns a bounded value-free structural/empty-trigger report; it does not store an artifact, append audit state, resolve credentials, or invoke connectors. The installed `service-workflow-release-preflight` and verified-set `authoring-service-release-preflight` clients wrap this route. See [`remote-workflow-release.md`](remote-workflow-release.md). |
| `POST /api/v1/workflow-releases` | Requires readiness, the active scheduler lease, Bearer authentication, and exactly `{"workflow": <object>}`. Publishes one immutable Workflow DSL version within a 1 MiB request bound and returns a redacted fixed record; the installed `service-workflow-publish` and verified-set `authoring-service-publish` clients wrap this route. It does not promote aliases or trigger runs. See [`remote-workflow-release.md`](remote-workflow-release.md). |
| `POST /api/v1/workflow-promotions` | Requires readiness, the active scheduler lease, Bearer authentication, and the exact promotion envelope. Atomically moves one alias with an optional expected-current-version CAS guard and returns a redacted fixed summary; the installed `service-workflow-promote` client wraps this route. It does not publish or trigger runs. See [`remote-workflow-promotion.md`](remote-workflow-promotion.md). |
| `POST /api/v1/workflow-deprecations` | Requires readiness, the active scheduler lease, Bearer authentication, and either the legacy `{"workflow_id": <string>, "version": <string>}` body or the protected form with `expected_checksum` and sorted `expected_aliases`. The CAS form atomically checks the observed metadata before marking one published version deprecated, removing its stable aliases, appending one audit event, and returning the fixed redacted deprecation summary; the installed `service-workflow-deprecate` client wraps this route. A stale CAS returns `409` without mutation. It does not delete artifacts, publish, promote, or trigger runs. See [`remote-workflow-deprecation.md`](remote-workflow-deprecation.md). |
| `GET /api/v1/workflow-diffs/{workflow_id}/{from_version}/{to_version}` | Requires Bearer authentication and no body. Returns the existing bounded, value-free structural diff for two exact published versions without acquiring the scheduler lease or mutating state; the installed `service-workflow-diff` client wraps this route. See [`remote-workflow-diff.md`](remote-workflow-diff.md). |
| `GET /api/v1/recurring-schedules` | Requires Bearer authentication and returns a read-only, 100-item, 64 KiB redacted recurring-schedule inventory without acquiring the scheduler lease or changing schedule state. |
| `POST /api/v1/recurring-schedules` | Requires readiness, the active scheduler lease, Bearer authentication, and exactly `{"schedule": <recurring schedule definition>}`. Creates or replays one durable recurring schedule under the fixed redacted create contract; a changed existing definition returns `409`, and trigger input is never returned. See [`remote-schedule-create.md`](remote-schedule-create.md). |
| `PUT /api/v1/recurring-schedules/{schedule_id}` | Requires readiness, Bearer authentication, a complete definition with explicit `schedule.enabled`, and the last observed `expected_next_run_at`. Performs a SQLite compare-and-swap that preserves durable progress; stale updates return `409` under the fixed redacted update contract. See [`remote-schedule-update.md`](remote-schedule-update.md). |
| `PATCH /api/v1/recurring-schedules/{schedule_id}` | Requires readiness, Bearer authentication, only safe non-trigger schedule fields, and the last observed `expected_next_run_at`. Merges the patch while preserving trigger input and durable progress; stale patches return `409` under the fixed redacted patch contract. See [`remote-schedule-patch.md`](remote-schedule-patch.md). |
| `POST /api/v1/recurring-schedules/{schedule_id}/enable` or `/disable` | Requires Bearer authentication and either the legacy empty JSON object or one `expected_next_run_at` CAS field. Applies one idempotent schedule state change only while ready, serializes with dispatcher claims, and returns the fixed action contract documented in [`remote-schedule-actions.md`](remote-schedule-actions.md). |
| `GET /api/v1/recurring-schedule-dispatches` or `/api/v1/recurring-schedules/{schedule_id}/dispatches` | Requires Bearer authentication and no body. Returns at most 100 chronological, redacted dispatch records and fixed status counts within 64 KiB, without claiming scheduler ownership or mutating dispatch state. See [`remote-schedule-dispatches.md`](remote-schedule-dispatches.md). |
| `GET /api/v1/recurring-schedule-dispatch-pages` or `/api/v1/recurring-schedules/{schedule_id}/dispatch-pages` | Requires Bearer authentication and no body. Returns a cursor-paged, redacted dispatch projection under a separate 100-item/64 KiB contract; the opaque cursor walks toward older records without changing the fixed recent-tail route. See [`remote-schedule-dispatch-pages.md`](remote-schedule-dispatch-pages.md). |
| `GET /api/v1/audit-consistency` or `GET /api/v1/audit-consistency/{run_id}` | Requires Bearer authentication and returns the bounded, value-free run/audit consistency report with a 64 KiB response cap and no persisted-state mutation. The targeted form bypasses the global 256-run window for one safe run identifier. |
| `GET /api/v1/audit-events` | Requires Bearer authentication and no body. Returns the fixed `skill2workflow-audit-event-list-0.1.0` redacted SQLite audit projection with exact filters, an opaque sequence cursor, a 100-item/64 KiB bound, no raw payload or error disclosure, and no state mutation. The installed `service-audit-events` client wraps this route. See [`remote-audit-events.md`](remote-audit-events.md). |
| `GET /runs/{run_id}` | Requires Bearer authentication and returns one redacted, read-only run detail projection with at most 50 allowlisted events and a 64 KiB response cap. |
| `GET /runs` | Requires Bearer authentication and returns at most 100 redacted run summaries for operator discovery, with fixed status counts and a 64 KiB response cap. |
| `GET /api/v1/runs` | Requires Bearer authentication and no body. Returns filtered, cursor-paged redacted run summaries under `skill2workflow-run-list-0.2.0`, with status/workflow filters, a 100-item/64 KiB bound, no scheduler lease acquisition, and no state mutation. The installed `service-run-page` client wraps this route. See [`run-list.md`](run-list.md). |
| `GET /api/v1/support-bundle` | Requires Bearer authentication and returns fixed lifecycle, aggregate observability, and nested redacted run-list data with a 128 KiB response cap. |
| `POST /webhooks/<workflow_id>/<version>` | Requires Bearer authentication, then uses the existing trigger contract to start a published workflow. SQLite requests with a non-empty idempotency key claim and replay durably; key conflicts return `409`. The installed `service-trigger` client wraps this route with a required retry key and fixed response validation; see [`remote-trigger.md`](remote-trigger.md). |
| `POST /runs/{run_id}/resume` | Requires Bearer authentication and exactly `{"approved": true|false}`, then resumes one waiting human gate through the existing control-plane executor. If state commits before audit evidence, retrying the same decision repairs only missing evidence; a fully reconciled non-waiting run still returns `409`. |
| `POST /runs/{run_id}/cancel` | Requires Bearer authentication and an empty JSON object, then durably requests idempotent cooperative cancellation. If state commits before audit evidence, retrying the same action repairs only missing evidence. |

All non-probe routes share a fixed `MAX_CONCURRENT_BUSINESS_REQUESTS` budget of
16 active handlers. When the budget is exhausted, the service fails fast with
HTTP `429`, the fixed body `{"error":"service concurrency limit reached"}`,
and `Retry-After: 1`; it does not create a run, append business audit state, or
wait for a slot. `/healthz` and `/readyz` remain available so an external
proxy can observe liveness and remove a draining instance. The budget is
process-local and protects one single-tenant service; it is not a distributed
queue or a guarantee of exactly-once execution.

Request bodies are read to the exact advertised `Content-Length` with a fixed
five-second socket deadline (`REQUEST_SOCKET_TIMEOUT_SECONDS`). The authenticated
`GET /metrics` route is a zero-body read surface and rejects a non-zero or
invalid `Content-Length`, or any `Transfer-Encoding`, before rendering
telemetry. A client that
advertises a body but stalls before delivering it receives HTTP `408` with
`{"error":"request timed out"}`; a client that closes early receives HTTP `400`
with `{"error":"request body incomplete"}`. Neither path can reach a workflow
trigger, and the handler releases its admission slot and closes the
connection. This bounds slow, half-open, and truncated body reads during
overload and graceful drain. It is a per-request read deadline, not a total
workflow or connector execution timeout.

The webhook request and response contract remains documented in [`triggers.md`](triggers.md). Health does not imply readiness: during shutdown, readiness is withdrawn before the HTTP server closes. The readiness probe checks SQLite workflow-registry readability with a count query and does not materialize the complete published-version registry; the complete local workflow-list API remains available for explicit inspection. Stable-alias trigger resolution uses a direct exact-version lookup and a selected-workflow cursor, so unrelated published versions are not loaded on the request path.

Unexpected exceptions from a business handler are converted to the fixed
`503` `service unavailable` response. Connection-abort errors close the socket
without attempting a second write. Request telemetry and operational event
logging are best-effort both after the response path and across lifecycle
transitions; they cannot replace or corrupt the fixed response contract or
prevent orderly startup and shutdown.

The live snapshot remains available before readiness when authentication and
control state are readable. Its CLI client, response bounds, zero-write polling
contract, and real-process drill are documented in
[`live-control-snapshot.md`](live-control-snapshot.md).

The per-run detail remains available before readiness when authentication and
SQLite state are readable. Its fixed schema, redaction boundary, response cap,
and protected `service-show` client are documented in [`run-detail.md`](run-detail.md).

The run/audit consistency diagnostic is also available before readiness when
authentication and SQLite state are readable. It reuses the local report
contract, performs no writes or provider calls, and is documented in
[`remote-audit-consistency.md`](remote-audit-consistency.md).

## Shutdown And Restart Continuity

`SIGINT` and `SIGTERM` begin graceful shutdown. The service stops accepting new work, lets already accepted concurrent handlers return, closes the listening socket, and exits normally. A shutdown request that arrives during scheduler startup is preserved; the service does not publish `ready`, invoke the ready callback, or enter the HTTP request loop after draining has begun. Lifecycle state transitions are serialized across signal and embedding callers, so the ready/draining decision cannot be overwritten and lifecycle events remain ordered. Once `draining` is published, mutating routes are rejected before authentication, body parsing, or control-plane side effects with the fixed `503` `service is draining` response and `Retry-After: 1`; health, readiness, metrics, and read-only operator diagnostics remain available for investigation. Startup or scheduler-cleanup failures also close the listener and force the observable lifecycle state to `stopped` before the original exception is reported. Operators should use `/readyz` for traffic removal and `/healthz` only for process liveness. A handler that already acquired an admission slot releases it on every response or socket failure path.

Concurrent request handling allows a cancellation request to be persisted while another handler is blocked in a connector. Cancellation remains cooperative and does not interrupt an external request already in flight; see [`cancellation.md`](cancellation.md) before operating side-effecting connectors.

SQLite is mandatory on this service path. Published workflow records, run state, audit events, recurring definitions, and dispatch records therefore remain available when a new process starts with the same `runtime.state_dir`. A renewable SQLite lease provides active/standby coordination for local processes sharing that directory. It is not a distributed lock and does not provide exactly-once delivery.

Loop 70 verifies each published artifact against its control-plane checksum
before a service trigger or run can proceed. Missing or mismatched artifacts
fail closed before idempotency claims, run creation, or audit emission; see
[`published-artifact-integrity.md`](published-artifact-integrity.md).

Run the real-process evidence smoke with:

```bash
python3 scripts/service_boundary_smoke.py \
  --work-dir /tmp/skill2workflow-service-boundary
```

The smoke starts the service twice against one SQLite state directory, checks health and readiness, triggers one run per cycle, sends `SIGTERM`, and writes `service-boundary-smoke.json`. The report contains only booleans and counts; it excludes request values, run identifiers, and credentials.

For scrape configuration, the fixed metric vocabulary, operational log schema, and the real-process telemetry drill, follow [`observability.md`](observability.md).

For repeated local cutovers and durable trigger replay evidence, follow
[`service-soak.md`](service-soak.md).

For offline sensitive run-data minimization, stop every writer and follow [`data-retention.md`](data-retention.md). Retention publishes a new verified state directory; validate its service readiness before cutover, and explicitly manage destruction of the old source and backups.

For offline state protection and a tested restored-service startup path, follow [`backup-restore.md`](backup-restore.md). Stop the service before backup; authentication and connector credential files are intentionally outside that backup contract.

The service accepts only the current explicit SQLite state layout. Startup validates all three database layouts and integrity, workflow artifact references, and the marker before recording `service_initialized`; an already initialized state with a missing database fails closed. Before pointing a newer binary at existing state, follow [`upgrade-migration.md`](upgrade-migration.md): stop the old service, run read-only preflight, create the required verified backup and copy-on-write upgraded directory, then cut over only after the new service is ready. Legacy and future layouts fail closed.

## Current Security Boundary

- Bind addresses are limited to `127.0.0.1`, `::1`, or `localhost`.
- Business routes require a file-backed Bearer token by default; probes remain minimal and anonymous.
- Connector handles resolve from a mounted directory at execution time.
- TLS terminates at an external reverse proxy that forwards only to loopback.
- Put no live credential or business payload in the service configuration or smoke evidence.
- Run one active service process for one team and one state directory. A local standby may share that state and remains unready until it acquires the scheduler lease; distributed workers and multi-tenancy remain out of scope.
