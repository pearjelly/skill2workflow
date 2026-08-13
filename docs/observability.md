# Runtime Observability

Loop 46 adds a dependency-free, machine-consumable observability boundary to the self-hosted service. Loop 108 adds live HTTP in-flight-request pressure, Loop 109 adds recurring scheduler-dispatch pressure, and Loop 112 adds an importable Grafana dashboard to that boundary. It exposes authenticated Prometheus text metrics and emits structured operational lifecycle/request events as NDJSON. Both surfaces are deliberately aggregate and low-cardinality: they do not export workflow IDs, versions, run IDs, schedule IDs, request paths, bodies, credentials, remote addresses, or connector payloads.

Workflow audit events remain the durable business evidence. Operational metrics and logs answer a narrower question: whether the service is healthy enough for an operator to detect and investigate runtime problems.

## Authenticated Metrics

`GET /metrics` uses the same file-backed Bearer authenticator as workflow trigger routes:

```text
GET /metrics
Authorization: Bearer <single-team-token>
```

The request is a zero-body read: a non-zero `Content-Length`, duplicate or
invalid length, or `Transfer-Encoding` header is rejected with the shared
bounded `400`/`413` request contract before telemetry is rendered. This keeps
scraper failures from leaving unread bytes at the service boundary.

An absent, malformed, or invalid token returns `401` and `WWW-Authenticate: Bearer`. An unavailable token provider returns `503`. Metrics authentication attempts do not create persisted workflow audit events, avoiding scrape-driven audit growth. The in-memory HTTP counter still records the fixed route and response class.

Unlike workflow triggers, authenticated metrics remain available while `/readyz` reports `503`. This lets an operator diagnose a starting, draining, or standby process. The exported `skill2workflow_service_ready` and `skill2workflow_scheduler_lease_owned` gauges show that state directly. A SQLite read failure returns a compact `503 metrics unavailable` response without storage details.

During graceful shutdown, new mutating routes are rejected before their
authentication or request bodies are processed, but `/metrics` remains a
read-only diagnostic surface. Its `service_state` gauge therefore continues to
expose the transition through `draining` until the listener stops.

The live `skill2workflow_service_inflight_requests` gauge reports admitted
non-metrics handlers that have not completed. It is process-local, has no
labels, and is sampled from the same handler boundary as the fixed 16-request
admission budget. Health/readiness probes are not budgeted and are not counted;
the `/metrics` scrape is excluded so a scrape reports existing workload rather
than counting itself. The value is intentionally omitted from the versioned
support bundle 0.1.0, whose aggregate snapshot contract remains stable and
whose durable run evidence is safer for incident handoff.

The `skill2workflow_scheduler_dispatch_inflight` gauge reports recurring
dispatcher calls that passed the shutdown admission gate and have not returned.
It is process-local, has no labels, and is `0` when the scheduler is polling
without owning the lease. During drain, a value of `1` means an already-admitted
dispatch may still be finishing; it does not mean a second dispatch can start.
This gauge is also omitted from support-bundle 0.1.0.

The response content type is:

```text
text/plain; version=0.0.4; charset=utf-8
```

## Metric Contract

| Metric | Type | Labels | Source and meaning |
| --- | --- | --- | --- |
| `skill2workflow_service_ready` | gauge | none | `1` only when normal readiness passes |
| `skill2workflow_scheduler_lease_owned` | gauge | none | `1` when this process currently owns the local scheduler lease |
| `skill2workflow_service_uptime_seconds` | gauge | none | Monotonic process uptime; resets at restart |
| `skill2workflow_service_inflight_requests` | gauge | none | Admitted non-metrics handlers currently in flight; process-local and resets at restart |
| `skill2workflow_scheduler_dispatch_inflight` | gauge | none | Admitted recurring scheduler dispatch calls currently in flight; process-local and resets at restart |
| `skill2workflow_service_state` | gauge | fixed `status` | One-hot lifecycle state: `starting`, `ready`, `draining`, `stopped`, or `unknown` |
| `skill2workflow_workflows` | gauge | fixed `status` | SQLite workflow-version counts: `published`, `deprecated`, or `other` |
| `skill2workflow_runs` | gauge | fixed `status` | SQLite run counts: `created`, `running`, `waiting`, `completed`, `failed`, `cancelled`, `interrupted`, or `other` |
| `skill2workflow_audit_events` | gauge | none | Total persisted audit events |
| `skill2workflow_recurring_schedules` | gauge | none | Total persisted recurring schedules |
| `skill2workflow_schedule_dispatches` | gauge | fixed `status` | Dispatch counts: `claimed`, `completed`, `failed`, `skipped`, `uncertain`, or `other` |
| `skill2workflow_http_requests_total` | counter | fixed `route`, fixed `status_class` | Requests observed by this process; resets at restart |

The only HTTP route labels are `health`, `readiness`, `metrics`, `control_snapshot`, `workflow_artifact_report`, `backup_readiness`, `retention_readiness`, `operational_readiness`, `audit_integrity`, `runtime_info`, `workflow_inventory`, `recurring_schedule_list`, `recurring_schedule_action`, `recurring_schedule_dispatch_list`, `audit_consistency`, `support_bundle`, `run_list`, `run_detail`, `workflow_trigger`, `workflow_release`, `workflow_promotion`, `workflow_deprecation`, `workflow_diff`, `run_resume`, `run_cancel`, and `unknown`. The only response-class labels are `2xx`, `4xx`, and `5xx`. Unknown persisted statuses roll into `other`; user-controlled values never become label values. This fixed matrix intentionally favors safe alerting and bounded time-series count over per-workflow diagnosis.

Prometheus or another compatible scraper should connect through the same externally terminated TLS and private operator boundary documented in [`security-boundary.md`](security-boundary.md). Store the Bearer token in the scraper's secret facility and do not put it in repository configuration, command history, or scrape labels.

## Operational NDJSON

The `skill2workflow service` CLI writes one JSON object per line to standard output using schema `skill2workflow-operational-event-0.1.0`. Library callers remain quiet unless they explicitly provide an `OperationalEventLogger`.

Lifecycle events contain only:

- schema version, UTC timestamp, event type, fixed service name;
- lifecycle status: `starting`, `ready`, `draining`, or `stopped`.

Request-completion events contain only:

- schema version, UTC timestamp, event type, fixed service name;
- normalized method: `GET`, `POST`, `PUT`, `DELETE`, or `OTHER`;
- normalized route from the fixed route list;
- numeric status, response class, and rounded non-negative duration in milliseconds.

The application logger never receives raw URLs, query strings, headers, bodies, workflow/run identifiers, credential values, or exception messages. Forward standard output with an operator-managed log collector. Configure the reverse proxy separately so its access logs also exclude Authorization headers and request bodies.

Operational event delivery is best-effort. A closed pipe, unavailable
collector, or custom logger exception is swallowed at the service boundary so
logging cannot prevent startup, strand scheduler threads, raise from a signal
handler, or mask shutdown cleanup. Durable workflow audit events remain the
source of business evidence; an operational log gap must be investigated as an
observability incident rather than treated as a workflow-state failure.

Lifecycle cleanup does not depend on successful event delivery: the listener
and scheduler teardown path remain authoritative even when the collector is
unavailable.

## Verification

Run the real-process observability drill:

```bash
python3 scripts/observability_smoke.py \
  --work-dir /tmp/skill2workflow-observability-loop108
```

The drill starts the CLI service, proves unauthenticated denial, performs authenticated scrapes and a workflow trigger, verifies aggregate SQLite state and the fixed label vocabulary, terminates the process, and validates starting/ready/draining/stopped NDJSON events. Its evidence file contains booleans and counts only.

## Deferred Boundary

The in-flight gauge is a live pressure signal, not a queue, admission lease, or
execution outcome. It may fall to zero while a connector's external outcome is
still uncertain after a handler returns; use durable dispatch/run/audit evidence
for recovery decisions.

Loop 46 does not add tracing, per-node latency, exemplars, histograms, log rotation, remote metric storage, OpenTelemetry, or multi-process metric aggregation. Loop 111 adds only the operator-managed, dependency-free alert starter pack in [`prometheus-alerts.md`](prometheus-alerts.md), and Loop 112 adds the corresponding read-only Grafana dashboard in [`grafana-dashboard.md`](grafana-dashboard.md); neither adds an alert manager, notification routing, or automatic remediation. In-memory HTTP counters, in-flight requests, and uptime reset on restart. Durable workflow diagnosis continues to use the existing audit and run-state surfaces.
