# Stability Boundaries

`skill2workflow` is at Self-hosted Beta maturity. Some surfaces are stable for
the `0.1.x` compatibility line, while Production Baseline work and the internals
listed below remain experimental. This document separates those contracts from
implementation details that may still change.

## Stable For 0.1.x

These surfaces should remain compatible during the `0.1.x` line:

- Workflow DSL `0.1.0` top-level shape
- `schemas/workflow.schema.json`
- Structured validation error keys: `code`, `message`, `path`, `severity`
- CLI command names documented in `README.md` and `HARNESS.md`
- Example workflow fixture validity under `examples/workflows/`
- Published workflow artifact immutability
- Published artifact checksum verification before read, promotion, trigger, or execution, documented in [`published-artifact-integrity.md`](published-artifact-integrity.md)
- Control-plane workflow version aliases and the `promote`/trigger resolution contract documented in `docs/triggers.md`
- Reviewable published workflow diffs and the optional compare-and-swap promotion precondition documented in [`workflow-releases.md`](workflow-releases.md)
- SQLite promotion transactionally couples the compare-and-swap check, alias mutation, and promotion audit append; JSON remains local-evaluation storage without cross-process coordination
- SQLite publication and deprecation transactionally couple single-record registry changes with their audit rows, preserving immutable-version and retry semantics
- `workflow-artifacts` report contract `skill2workflow-workflow-artifact-report-0.1.0`, including bounded registry/file consistency issues and known-failure SQLite publication cleanup
- `audit-consistency` report contract `skill2workflow-run-audit-report-0.1.0`, including bounded missing/duplicate/unexpected run-audit projections; one control-plane lifecycle/runtime emission is transactional in SQLite, while the two-database boundary remains diagnostic-only
- `audit-consistency` treats waiting human gates and recovered interrupted runs as clean when their single durable lifecycle projection is present; the status field is not counted as a second event
- Authenticated `GET /api/v1/audit-consistency` and `service-audit-consistency` reuse the exact run-audit report contract with a 64 KiB response bound, zero-write semantics, and readiness-independent availability when auth and SQLite state are readable
- Targeted `GET /api/v1/audit-consistency/{run_id}` and `service-audit-consistency --run-id` reuse the same report contract and safe `run_` identifier grammar to inspect one run beyond the global report window
- Authenticated `GET /api/v1/recurring-schedules` and `service-recurring-schedules` reuse the fixed `skill2workflow-recurring-schedule-list-0.1.0` redacted inventory contract with a 64 KiB response bound and no schedule mutation
- Authenticated recurring-schedule dispatch reads and `service-recurring-dispatches` reuse the fixed `skill2workflow-recurring-schedule-dispatch-list-0.1.0` redacted diagnostics contract with 100-item/64 KiB bounds and no scheduler mutation
- Authenticated `GET /api/v1/workflow-artifacts` and `service-workflow-artifacts` reuse the fixed `skill2workflow-workflow-artifact-report-0.1.0` value-free consistency contract with a 64-issue/64 KiB remote bound and no repair mutation
- Authenticated `GET /api/v1/backup-readiness` and `service-backup-readiness` reuse the fixed `skill2workflow-backup-readiness-0.1.0` value-free preflight contract with a 16 KiB remote bound, active-lease blocking semantics, and no backup mutation
- Authenticated `POST /api/v1/retention-readiness` and `service-retention-readiness` reuse the fixed `skill2workflow-retention-readiness-0.1.0` policy-bound preflight contract with a 64 KiB request/16 KiB response bound, active-lease null-count blocking semantics, and no retention mutation documented in [`remote-retention-readiness.md`](remote-retention-readiness.md)
- Authenticated `GET /api/v1/operational-readiness` and `service-operational-readiness` reuse the fixed `skill2workflow-operational-readiness-0.1.0` aggregate value-free report with a 16 KiB response bound, no lifecycle mutation, and explicit best-effort cross-database semantics documented in [`remote-operational-readiness.md`](remote-operational-readiness.md)
- The installed `service-probe` command reuses the existing unauthenticated `/healthz` and `/readyz` endpoints through the fixed `skill2workflow-service-probe-0.1.0` contract, with no redirects or proxies, a five-second request timeout, an 8 KiB response bound, and stable exit codes documented in [`service-probe.md`](service-probe.md)
- The installed `service-wait` command reuses that same fixed probe contract with a 300-second timeout and 10-second poll-interval ceiling; it adds no service route or schema
- Authenticated `GET /api/v1/audit-integrity` and `service-audit-integrity` reuse the fixed `skill2workflow-audit-integrity-0.1.0` payload-free verification contract with a 16 KiB remote bound, readiness-independent availability, and no repair mutation
- Authenticated `GET /api/v1/runtime-info` and `service-runtime-info` reuse the fixed `skill2workflow-runtime-info-0.1.0` identity/compatibility contract with a 16 KiB remote bound, no path disclosure, and no upgrade mutation
- Protected `service-trigger` reuses the authenticated webhook trigger contract with a required idempotency key, shared 1 MiB input/body bounds, safe URL-component validation, and exact compact response validation documented in [`remote-trigger.md`](remote-trigger.md)
- Protected `POST /api/v1/workflow-releases` and `service-workflow-publish` reuse the fixed `skill2workflow-workflow-release-0.1.0` redacted publication contract with a 1 MiB request bound, immutable SQLite publication semantics, and no artifact-path disclosure documented in [`remote-workflow-release.md`](remote-workflow-release.md)
- Protected `POST /api/v1/workflow-promotions` and `service-workflow-promote` reuse the fixed `skill2workflow-workflow-promotion-0.1.0` redacted CAS promotion contract with a 1 MiB request bound, transactional SQLite alias mutation, and no artifact-path disclosure documented in [`remote-workflow-promotion.md`](remote-workflow-promotion.md)
- Protected `GET /api/v1/workflow-diffs/{workflow_id}/{from_version}/{to_version}` and `service-workflow-diff` reuse the fixed `skill2workflow-workflow-diff-0.1.0` value-free structural review contract with a 64 KiB response bound and no state mutation documented in [`remote-workflow-diff.md`](remote-workflow-diff.md)
- Protected `POST /api/v1/workflow-deprecations` and `service-workflow-deprecate` reuse the fixed `skill2workflow-workflow-deprecation-0.1.0` redacted registry-retirement contract with a 1 MiB request bound, idempotent SQLite status/alias mutation, one audit event, and no artifact deletion documented in [`remote-workflow-deprecation.md`](remote-workflow-deprecation.md)
- Protected `GET /api/v1/workflows` and `service-workflows` reuse the fixed `skill2workflow-workflow-inventory-0.1.0` redacted version-inventory contract with a 100-item/64 KiB bound, no scheduler lease acquisition, and no state mutation documented in [`remote-workflow-inventory.md`](remote-workflow-inventory.md)
- Authenticated `POST /api/v1/recurring-schedules/{schedule_id}/enable|disable` and protected `service-schedule-enable`/`service-schedule-disable` reuse the fixed `skill2workflow-recurring-schedule-action-0.1.0` contract, exact empty-body boundary, idempotent state transitions, and bounded audit evidence documented in [`remote-schedule-actions.md`](remote-schedule-actions.md)
- Resume, cancellation, and recurring schedule action retries reconcile a
  committed SQLite state mutation with missing control-plane audit evidence
  without replaying workflow execution or a human decision; this is a retry
  recovery contract, not a distributed transaction or provider compensation
- JSON storage as the dependency-light default
- SQLite storage as an opt-in local persistence mode
- Built-in connector runtime boundaries documented in `docs/connectors.md`
- Credential placeholder and fixture hygiene boundary documented in `docs/credential-boundary.md`
- Local credential handle boundary documented in `docs/credential-boundary.md`
- Local trigger command and envelope documented in `docs/triggers.md`
- Local trigger run-context shape documented in `docs/triggers.md`
- Shared 1 MiB canonical UTF-8 JSON-object trigger-input limit and fixed oversize failure boundary documented in `docs/triggers.md`
- Optional bounded declarative `input_schema` trigger contracts, publication validation, and pre-idempotency runtime rejection documented in `docs/workflow-dsl-contract.md` and `docs/triggers.md`
- Fixed process-local business-request admission of 16 active handlers, `429`/`Retry-After` rejection, and probe availability documented in `docs/service.md`
- Exact `Content-Length` request-body reads with a fixed five-second socket deadline, stable `408` `request timed out` and `400` `request body incomplete` errors, and no partial-trigger execution for the service and loopback webhook adapter, without changing connector execution deadlines
- The authenticated service converts unexpected request-dispatch exceptions into the fixed `503` `service unavailable` response, suppresses exception details and second writes after connection aborts, and treats telemetry/event logging as best-effort across both request and lifecycle paths
- Service startup and teardown always close the listener and publish `stopped` after scheduler cleanup attempts, while preserving the original scheduler failure for the caller
- A shutdown request observed during scheduler startup is preserved: the service never publishes `ready`, invokes the ready callback, or enters the request loop after draining begins
- Lifecycle state transitions are serialized across shutdown callers and the serving thread, preserving the ready/draining decision and ordered lifecycle events
- Mutating service routes are atomically rejected after `draining` is published with the fixed `503`/`Retry-After: 1` contract, while probes, metrics, and read-only diagnostics remain available
- Local webhook route and response shape documented in `docs/triggers.md`
- Self-hosted service configuration `skill2workflow-service-0.2.0` and its published JSON Schema
- Local `service-token-rotate` and `skill2workflow-service-token-rotation-result-0.1.0` preserve owner-only atomic ingress-token replacement without returning the secret
- Loopback service health/readiness paths and authenticated workflow-trigger boundary documented in `docs/service.md`
- Authenticated `POST /runs/{run_id}/cancel`, CLI `cancel-run`, terminal `cancelled`, and cooperative safe-point semantics documented in `docs/cancellation.md`
- Authenticated `POST /runs/{run_id}/resume`, exact boolean decision body, waiting-only conflict behavior, and durable human-gate branch semantics documented in `docs/human-approval.md`
- Protected `service-resume` and `service-cancel` CLI commands, token-file authentication, fixed origin validation, and bounded response handling documented in `docs/human-approval.md`
- Authenticated `GET /runs/{run_id}`, redacted run-detail schema `skill2workflow-run-detail-0.1.0`, and protected `service-show` CLI documented in `docs/run-detail.md`
- Authenticated `GET /runs`, redacted run-list schema `skill2workflow-run-list-0.1.0`, and protected `service-runs` CLI documented in `docs/run-list.md`
- Authenticated `GET /api/v1/support-bundle`, redacted support-bundle schema `skill2workflow-support-bundle-0.1.0`, and protected `service-support-bundle` CLI documented in `docs/support-bundle.md`
- SQLite trigger idempotency for keyed service/control-plane requests, including durable replay, fixed `409` conflicts, and unresolved-outcome fail-closed behavior documented in `docs/triggers.md`
- Bounded active execution timeout semantics for `policies.default_timeout_ms`, including fixed `execution_timeout` evidence and human-gate pause behavior documented in `docs/runtime-policy.md`
- Optional `tool_call.on_fallback` transition semantics, edge validation, LiteGraph slot projection, and fixed `node_fallback` evidence documented in `docs/workflow-dsl-contract.md`
- SQLite audit integrity result contract `skill2workflow-audit-integrity-0.1.0` and the payload-free `audit-verify` CLI; this does not claim signatures or JSON/JSONL chain guarantees
- Authenticated Prometheus text metric names, fixed label vocabularies, live HTTP/scheduler pressure gauges, and operational event schema `skill2workflow-operational-event-0.1.0` documented in `docs/observability.md`
- The operator-managed `examples/observability/prometheus-alerts.yml` starter pack and its fixed-metric safety checks are documented in `docs/prometheus-alerts.md`; it adds no runtime route, dependency, or automatic remediation
- The operator-managed `examples/observability/grafana-dashboard.json` read-only dashboard and its fixed-metric safety checks are documented in `docs/grafana-dashboard.md`; it adds no runtime route, dependency, or mutation
- Authenticated `GET /metrics` zero-body request validation: malformed,
  transfer-encoded, oversized, and non-empty scraper bodies use the shared
  bounded request error contract before telemetry rendering
- Control snapshot `skill2workflow-control-snapshot-0.1.0`, `schemas/control-snapshot-0.1.0.schema.json`, authenticated `GET /api/v1/control-snapshot`, and live `window` semantics documented in `docs/live-control-snapshot.md`
- Retention policies `skill2workflow-retention-policy-0.1.0`, `skill2workflow-retention-policy-0.2.0`, and `skill2workflow-retention-policy-0.3.0`, aggregate plan/apply summaries, and protected state semantics documented in `docs/data-retention.md`
- Additive SQLite `run_executions` ownership tickets, terminal `interrupted` run state, and no-replay recovery semantics documented in `docs/interrupted-recovery.md`
- File-backed single-team Bearer and execution-time directory credential contracts documented in `docs/security-boundary.md`
- Durable recurring schedule input contract `skill2workflow-schedule-0.2.0` and its published JSON Schema
- Recurring dispatch states, missed-run policies, and single-SQLite lease semantics documented in `docs/recurring-scheduling.md`
- State backup manifest `skill2workflow-state-backup-0.1.0`, current `skill2workflow-sqlite-layout-0.1.0`, and verified offline restore contract documented in `docs/backup-restore.md`
- State layout marker `skill2workflow-state-layout-marker-0.1.0`, fail-closed compatibility preflight, and legacy-to-current copy-on-write migration documented in `docs/upgrade-migration.md`
- Body-only HTTP connector input mapping documented in `docs/connectors.md`
- Minimum connector manifest contract documented in `docs/connectors.md`
- explicit local connector fixture loading for examples, using `load_external_connector(path)` plus `ConnectorRuntime([external_connector])`
- Connector package layout expectations documented in `docs/connectors.md`

## Experimental

These surfaces may change while the project learns from real workflows:

- Parser heuristics for arbitrary `SKILL.md` formats
- Skill IR shape
- Compiler defaults for new node types
- LiteGraph node layout and web editor UI
- Visual write-back allowlist beyond the documented fields
- Connector manifest fields beyond the documented minimum contract
- Dynamic connector loading, automatic connector discovery and product-specific connector packages
- Connector package installation, marketplace indexing, OAuth, hosted callbacks, and distributed queues
- HTTP connector request metadata beyond documented method, URL, headers, body, timeout, credential handles, and body-only input mapping
- Credential providers beyond the documented local static file and mounted directory boundaries
- Advanced retry behavior beyond documented connector-node retry and fallback execution
- Hosted secret storage, OAuth, multi-tenant RBAC, and IAM
- Advanced input mapping beyond the body-only contract, templating, and connector request interpolation
- Hosted webhook ingress, callback verification, distributed queues, cron/calendar scheduling, and multi-database schedulers
- Product-specific connector packages and connector marketplaces
- SQLite table internals beyond the published state-layout identity and supported migration path
- Executor event taxonomy beyond documented audit examples
- Future remote mutation APIs, browser credential sessions, and live UI polling beyond the fixed read-only snapshot boundary
- Observability backends, tracing, histograms, and per-node telemetry beyond the fixed Loop 46 export contract, Loop 111 alert starter pack, and Loop 112 Grafana dashboard
- Forceful connector abort, provider compensation, bulk cancellation, cancellation deadlines, automatic workflow replay or provider reconciliation, distributed ownership, and exactly-once execution beyond the fixed Loop 48 cancellation, Loop 49 interruption, and Loop 101 operator-retry contracts
- Legal-policy automation, backup expiration, media erasure, and online retention beyond the fixed copy-on-write contract

## Extension Rules

When extending stable surfaces:

- Preserve old readers where possible.
- Add structured validation coverage.
- Update schema and docs in the same PR.
- Keep examples runnable from a fresh checkout.
- Keep Workflow DSL authoritative over visual graph state.

When changing experimental surfaces:

- Keep the change scoped to one closed loop.
- Document migration notes if examples or contributor workflows are affected.
- Prefer additive changes over rewrites.

## Dependency Policy

Runtime code currently uses the Python standard library. New runtime dependencies should be added only when they directly support a spec-backed capability and the PR explains why standard-library code is insufficient.

Development-only tools may be introduced later, but the fresh-checkout path should remain simple.
