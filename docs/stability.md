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
- JSON storage as the dependency-light default
- SQLite storage as an opt-in local persistence mode
- Built-in connector runtime boundaries documented in `docs/connectors.md`
- Credential placeholder and fixture hygiene boundary documented in `docs/credential-boundary.md`
- Local credential handle boundary documented in `docs/credential-boundary.md`
- Local trigger command and envelope documented in `docs/triggers.md`
- Local trigger run-context shape documented in `docs/triggers.md`
- Shared 1 MiB canonical UTF-8 JSON-object trigger-input limit and fixed oversize failure boundary documented in `docs/triggers.md`
- Optional bounded declarative `input_schema` trigger contracts, publication validation, and pre-idempotency runtime rejection documented in `docs/workflow-dsl-contract.md` and `docs/triggers.md`
- Local webhook route and response shape documented in `docs/triggers.md`
- Self-hosted service configuration `skill2workflow-service-0.2.0` and its published JSON Schema
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
- Authenticated Prometheus text metric names, fixed label vocabularies, and operational event schema `skill2workflow-operational-event-0.1.0` documented in `docs/observability.md`
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
- Observability backends, alert rules, dashboards, tracing, histograms, and per-node telemetry beyond the fixed Loop 46 export contract
- Forceful connector abort, provider compensation, bulk cancellation, cancellation deadlines, automatic replay/reconciliation, distributed ownership, and exactly-once execution beyond the fixed Loop 48 cancellation and Loop 49 interruption contracts
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
