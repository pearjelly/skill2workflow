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

The `service` command is the long-running, single-tenant runtime boundary delivered by Loop 41. It serves health, readiness, authenticated aggregate metrics, a bounded live Operator snapshot, a redacted recurring-schedule inventory, redacted run discovery and detail views, a redacted support bundle, published-workflow triggers, protected Workflow DSL publication, authenticated human-gate decisions, and durable cooperative run cancellation. SQLite service triggers enforce durable idempotency before execution; see [`triggers.md`](triggers.md). Workflow DSL remains the execution source of truth. Loop 49 adds execution ownership and fail-closed interrupted-run recovery; see [`interrupted-recovery.md`](interrupted-recovery.md). Loop 68 adds fixed concurrent business-request admission so slow or retried requests cannot consume an unbounded amount of active service work. Loop 69 adds explicit stable workflow version aliases; service triggers resolve them through the same control-plane boundary.

The HTTP control plane and recurring dispatcher share the scheduler lease owner.
Graceful drain waits for in-flight HTTP handlers before releasing that lease. After
an ungraceful process loss, a replacement becomes ready only after lease expiry and
marks foreign active execution tickets `interrupted`; it never automatically
replays an external request with an unknown outcome.

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
    "storage": "sqlite"
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

Validation is fail-closed: unknown fields, a wrong schema version, missing security providers, relative paths, JSON storage, an invalid port, or a non-loopback bind address prevent startup. The token file and credential directory must be usable before readiness. Port `0` is accepted for test harnesses that need an operating-system-assigned port.

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
| `POST /api/v1/retention-readiness` | Requires Bearer authentication and exactly `{"policy": <retention policy>}`. Returns the fixed retention preflight within 16 KiB; an active lease blocks the plan and counts remain null, while a quiesced current-layout read returns aggregate eligibility only. It never applies retention or mutates state. See [`remote-retention-readiness.md`](remote-retention-readiness.md). |
| `GET /api/v1/operational-readiness` | Requires Bearer authentication and no body. Returns the fixed aggregate service/artifact/audit/backup readiness report within 16 KiB; it does not mutate lifecycle or state and does not claim an atomic cross-database snapshot. See [`remote-operational-readiness.md`](remote-operational-readiness.md). |
| `GET /api/v1/audit-integrity` | Requires Bearer authentication and returns the fixed payload-free SQLite audit-chain verification result within 16 KiB; it does not repair or rewrite audit state. |
| `GET /api/v1/runtime-info` | Requires Bearer authentication and returns fixed package, compatibility-line, state-layout, lifecycle, readiness, and lease metadata within 16 KiB; it does not expose paths or configuration values. |
| `GET /api/v1/workflows` | Requires Bearer authentication and no body. Returns at most 100 redacted published-version records, fixed lifecycle counts, aliases, and checksums within 64 KiB without acquiring the scheduler lease or mutating state; the installed `service-workflows` client wraps this route. See [`remote-workflow-inventory.md`](remote-workflow-inventory.md). |
| `POST /api/v1/workflow-releases` | Requires readiness, the active scheduler lease, Bearer authentication, and exactly `{"workflow": <object>}`. Publishes one immutable Workflow DSL version within a 1 MiB request bound and returns a redacted fixed record; the installed `service-workflow-publish` client wraps this route. It does not promote aliases or trigger runs. See [`remote-workflow-release.md`](remote-workflow-release.md). |
| `POST /api/v1/workflow-promotions` | Requires readiness, the active scheduler lease, Bearer authentication, and the exact promotion envelope. Atomically moves one alias with an optional expected-current-version CAS guard and returns a redacted fixed summary; the installed `service-workflow-promote` client wraps this route. It does not publish or trigger runs. See [`remote-workflow-promotion.md`](remote-workflow-promotion.md). |
| `POST /api/v1/workflow-deprecations` | Requires readiness, the active scheduler lease, Bearer authentication, and exactly `{"workflow_id": <string>, "version": <string>}`. Atomically marks one published version deprecated, removes its stable aliases, appends one audit event, and returns the fixed redacted deprecation summary; the installed `service-workflow-deprecate` client wraps this route. It does not delete artifacts, publish, promote, or trigger runs. See [`remote-workflow-deprecation.md`](remote-workflow-deprecation.md). |
| `GET /api/v1/workflow-diffs/{workflow_id}/{from_version}/{to_version}` | Requires Bearer authentication and no body. Returns the existing bounded, value-free structural diff for two exact published versions without acquiring the scheduler lease or mutating state; the installed `service-workflow-diff` client wraps this route. See [`remote-workflow-diff.md`](remote-workflow-diff.md). |
| `GET /api/v1/recurring-schedules` | Requires Bearer authentication and returns a read-only, 100-item, 64 KiB redacted recurring-schedule inventory without acquiring the scheduler lease or changing schedule state. |
| `POST /api/v1/recurring-schedules/{schedule_id}/enable` or `/disable` | Requires Bearer authentication and an exact empty JSON object. Applies one idempotent schedule state change only while ready, serializes with dispatcher claims, and returns the fixed action contract documented in [`remote-schedule-actions.md`](remote-schedule-actions.md). |
| `GET /api/v1/recurring-schedule-dispatches` or `/api/v1/recurring-schedules/{schedule_id}/dispatches` | Requires Bearer authentication and no body. Returns at most 100 chronological, redacted dispatch records and fixed status counts within 64 KiB, without claiming scheduler ownership or mutating dispatch state. See [`remote-schedule-dispatches.md`](remote-schedule-dispatches.md). |
| `GET /api/v1/audit-consistency` or `GET /api/v1/audit-consistency/{run_id}` | Requires Bearer authentication and returns the bounded, value-free run/audit consistency report with a 64 KiB response cap and no persisted-state mutation. The targeted form bypasses the global 256-run window for one safe run identifier. |
| `GET /runs/{run_id}` | Requires Bearer authentication and returns one redacted, read-only run detail projection with at most 50 allowlisted events and a 64 KiB response cap. |
| `GET /runs` | Requires Bearer authentication and returns at most 100 redacted run summaries for operator discovery, with fixed status counts and a 64 KiB response cap. |
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

The webhook request and response contract remains documented in [`triggers.md`](triggers.md). Health does not imply readiness: during shutdown, readiness is withdrawn before the HTTP server closes.

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

`SIGINT` and `SIGTERM` begin graceful shutdown. The service stops accepting new work, lets already accepted concurrent handlers return, closes the listening socket, and exits normally. A shutdown request that arrives during scheduler startup is preserved; the service does not publish `ready`, invoke the ready callback, or enter the HTTP request loop after draining has begun. Lifecycle state transitions are serialized across signal and embedding callers, so the ready/draining decision cannot be overwritten and lifecycle events remain ordered. Startup or scheduler-cleanup failures also close the listener and force the observable lifecycle state to `stopped` before the original exception is reported. Operators should use `/readyz` for traffic removal and `/healthz` only for process liveness. A handler that already acquired an admission slot releases it on every response or socket failure path.

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
