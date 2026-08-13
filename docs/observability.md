# Runtime Observability

Loop 46 adds a dependency-free, machine-consumable observability boundary to the self-hosted service. It exposes authenticated Prometheus text metrics and emits structured operational lifecycle/request events as NDJSON. Both surfaces are deliberately aggregate and low-cardinality: they do not export workflow IDs, versions, run IDs, schedule IDs, request paths, bodies, credentials, remote addresses, or connector payloads.

Workflow audit events remain the durable business evidence. Operational metrics and logs answer a narrower question: whether the service is healthy enough for an operator to detect and investigate runtime problems.

## Authenticated Metrics

`GET /metrics` uses the same file-backed Bearer authenticator as workflow trigger routes:

```text
GET /metrics
Authorization: Bearer <single-team-token>
```

An absent, malformed, or invalid token returns `401` and `WWW-Authenticate: Bearer`. An unavailable token provider returns `503`. Metrics authentication attempts do not create persisted workflow audit events, avoiding scrape-driven audit growth. The in-memory HTTP counter still records the fixed route and response class.

Unlike workflow triggers, authenticated metrics remain available while `/readyz` reports `503`. This lets an operator diagnose a starting, draining, or standby process. The exported `skill2workflow_service_ready` and `skill2workflow_scheduler_lease_owned` gauges show that state directly. A SQLite read failure returns a compact `503 metrics unavailable` response without storage details.

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
| `skill2workflow_service_state` | gauge | fixed `status` | One-hot lifecycle state: `starting`, `ready`, `draining`, `stopped`, or `unknown` |
| `skill2workflow_workflows` | gauge | fixed `status` | SQLite workflow-version counts: `published`, `deprecated`, or `other` |
| `skill2workflow_runs` | gauge | fixed `status` | SQLite run counts: `created`, `running`, `waiting`, `completed`, `failed`, `cancelled`, `interrupted`, or `other` |
| `skill2workflow_audit_events` | gauge | none | Total persisted audit events |
| `skill2workflow_recurring_schedules` | gauge | none | Total persisted recurring schedules |
| `skill2workflow_schedule_dispatches` | gauge | fixed `status` | Dispatch counts: `claimed`, `completed`, `failed`, `skipped`, `uncertain`, or `other` |
| `skill2workflow_http_requests_total` | counter | fixed `route`, fixed `status_class` | Requests observed by this process; resets at restart |

The only HTTP route labels are `health`, `readiness`, `metrics`, `control_snapshot`, `workflow_artifact_report`, `backup_readiness`, `audit_integrity`, `runtime_info`, `recurring_schedule_list`, `recurring_schedule_action`, `recurring_schedule_dispatch_list`, `audit_consistency`, `support_bundle`, `run_list`, `run_detail`, `workflow_trigger`, `run_resume`, `run_cancel`, and `unknown`. The only response-class labels are `2xx`, `4xx`, and `5xx`. Unknown persisted statuses roll into `other`; user-controlled values never become label values. This fixed matrix intentionally favors safe alerting and bounded time-series count over per-workflow diagnosis.

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

## Verification

Run the real-process observability drill:

```bash
python3 scripts/observability_smoke.py \
  --work-dir /tmp/skill2workflow-observability-loop46
```

The drill starts the CLI service, proves unauthenticated denial, performs authenticated scrapes and a workflow trigger, verifies aggregate SQLite state and the fixed label vocabulary, terminates the process, and validates starting/ready/draining/stopped NDJSON events. Its evidence file contains booleans and counts only.

## Deferred Boundary

Loop 46 does not add tracing, per-node latency, exemplars, histograms, alert rules, dashboards, log rotation, remote metric storage, OpenTelemetry, or multi-process metric aggregation. In-memory HTTP counters and uptime reset on restart. Durable workflow diagnosis continues to use the existing audit and run-state surfaces.
