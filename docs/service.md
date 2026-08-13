# Self-hosted Runtime Service

The `service` command is the long-running, single-tenant runtime boundary delivered by Loop 41. It serves health, readiness, authenticated aggregate metrics, a bounded live Operator snapshot, a redacted per-run detail view, published-workflow triggers, authenticated human-gate decisions, and durable cooperative run cancellation. Workflow DSL remains the execution source of truth. Loop 49 adds execution ownership and fail-closed interrupted-run recovery; see [`interrupted-recovery.md`](interrupted-recovery.md).

The HTTP control plane and recurring dispatcher share the scheduler lease owner.
Graceful drain waits for in-flight HTTP handlers before releasing that lease. After
an ungraceful process loss, a replacement becomes ready only after lease expiry and
marks foreign active execution tickets `interrupted`; it never automatically
replays an external request with an unknown outcome.

This boundary is intentionally loopback-only and uses SQLite. Loop 42 adds mandatory single-team Bearer authentication and execution-time directory credentials. Loop 43 adds durable recurring dispatch and an active/standby lease for processes sharing one state directory. Loop 46 adds low-cardinality metrics and allowlisted operational NDJSON. Loop 48 adds authenticated, idempotent, cooperative cancellation. Loop 57 adds the authenticated human-gate decision route documented in [`human-approval.md`](human-approval.md). Loop 59 adds the bounded redacted run detail route documented in [`run-detail.md`](run-detail.md). The complete security and external TLS termination contract is documented in [`security-boundary.md`](security-boundary.md), scheduler semantics in [`recurring-scheduling.md`](recurring-scheduling.md), telemetry semantics in [`observability.md`](observability.md), and cancellation semantics in [`cancellation.md`](cancellation.md).

## Configuration

The service accepts one versioned JSON configuration file. Use an absolute state path so restarts resolve the same durable state independently of the process working directory.

For a new installation, [`service-bootstrap.md`](service-bootstrap.md) provides
the non-overwriting `service-init` command that generates this configuration,
an owner-only ingress token, the connector credential directory, and the state
directory together.

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
| `GET /runs/{run_id}` | Requires Bearer authentication and returns one redacted, read-only run detail projection with at most 50 allowlisted events and a 64 KiB response cap. |
| `POST /webhooks/<workflow_id>/<version>` | Requires Bearer authentication, then uses the existing trigger contract to start a published workflow. |
| `POST /runs/{run_id}/resume` | Requires Bearer authentication and exactly `{"approved": true|false}`, then resumes one waiting human gate through the existing control-plane executor. |
| `POST /runs/{run_id}/cancel` | Requires Bearer authentication and an empty JSON object, then durably requests idempotent cooperative cancellation. |

The webhook request and response contract remains documented in [`triggers.md`](triggers.md). Health does not imply readiness: during shutdown, readiness is withdrawn before the HTTP server closes.

The live snapshot remains available before readiness when authentication and
control state are readable. Its CLI client, response bounds, zero-write polling
contract, and real-process drill are documented in
[`live-control-snapshot.md`](live-control-snapshot.md).

The per-run detail remains available before readiness when authentication and
SQLite state are readable. Its fixed schema, redaction boundary, response cap,
and protected `service-show` client are documented in [`run-detail.md`](run-detail.md).

## Shutdown And Restart Continuity

`SIGINT` and `SIGTERM` begin graceful shutdown. The service stops accepting new work, lets already accepted concurrent handlers return, closes the listening socket, and exits normally. Operators should use `/readyz` for traffic removal and `/healthz` only for process liveness.

Concurrent request handling allows a cancellation request to be persisted while another handler is blocked in a connector. Cancellation remains cooperative and does not interrupt an external request already in flight; see [`cancellation.md`](cancellation.md) before operating side-effecting connectors.

SQLite is mandatory on this service path. Published workflow records, run state, audit events, recurring definitions, and dispatch records therefore remain available when a new process starts with the same `runtime.state_dir`. A renewable SQLite lease provides active/standby coordination for local processes sharing that directory. It is not a distributed lock and does not provide exactly-once delivery.

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
