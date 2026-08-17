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
- Published Workflow artifact publication and reads use a fixed 2 MiB UTF-8
  envelope with regular-file/no-follow descriptor identity and growth-race
  checks across control-plane execution, SQLite cleanup, and verified backup
  paths, documented in [`published-artifact-read-boundary.md`](published-artifact-read-boundary.md)
- Explicit external connector results use a fixed 1 MiB normalized JSON
  envelope and strict JSON round-trip before entering durable run state,
  and unexpected fixture exceptions use the fixed `external connector
  execution failed` message; documented in
  [`external-connector-result-boundary.md`](external-connector-result-boundary.md)
- The built-in HTTP connector rejects every `3xx` redirect before a follow-up
  request, so resolved credential headers cannot be replayed to a redirect
  target; normal non-redirect response handling remains compatible, as
  documented in [`connectors.md`](connectors.md)
- The built-in HTTP connector ignores ambient proxy environment variables and
  opens configured URLs directly; proxy-based egress requires an explicit
  reviewed connector, as documented in [`connectors.md`](connectors.md)
- Built-in HTTP request metadata uses fixed 16,384-byte URL, 32-byte method,
  and 64-entry/65,536-byte header bounds; malformed metadata fails closed
  before network access, as documented in [`connectors.md`](connectors.md)
- `connector.request.allowed_origins` is an additive exact-origin egress
  allowlist; omission preserves legacy behavior, while configured entries are
  enforced before credential resolution and network access
- The optional self-hosted `runtime.http_allowed_origins` configuration is a
  service-wide exact-origin upper bound for built-in HTTP execution and
  recurring schedules; requests must satisfy both service and workflow lists,
  and omission preserves legacy behavior, as documented in
  [`service-config-boundary.md`](service-config-boundary.md)
- Built-in HTTP transport failures use fixed value-free messages (`http
  connector request failed`, `http connector timed out`, and the fixed JSON
  body serialization message); underlying URL, provider-transport, proxy,
  socket, and exception text is not persisted in connector failure results;
  intentionally retained full response bodies remain governed by
  `response_mode`
- SQLite run-state documents use the same fixed 8 MiB UTF-8 persistence bound
  as the JSON backend across save, load, recovery, cancellation, deadline
  expiry, and startup summary repair, documented in
  [`sqlite-run-state-boundary.md`](sqlite-run-state-boundary.md)
- Local audit events use a fixed 1 MiB UTF-8 JSON-object envelope across JSONL
  and SQLite writes, bounded JSONL line reads, SQLite payload decoding, and
  JSON-to-SQLite import; batch appends validate before writing any member,
  documented in [`audit-event-boundary.md`](audit-event-boundary.md)
- SQLite workflow registry records use a fixed 2 MiB UTF-8 JSON-object envelope
  across publication, complete/direct reads, alias resolution, snapshots,
  diagnostics, deprecation, promotion, and JSON-to-SQLite import; replacement
  and alias-update batches validate before mutation, documented in
  [`sqlite-workflow-record-boundary.md`](sqlite-workflow-record-boundary.md)
- SQLite trigger-ledger responses use a fixed 64 KiB UTF-8 JSON-object envelope
  across completed-row writes and replay reads; rejected writes leave the
  pending claim unchanged, and corrupt completed rows fail closed as
  unresolved outcomes, documented in
  [`sqlite-trigger-ledger-boundary.md`](sqlite-trigger-ledger-boundary.md)
- Workflow bundle manifest `skill2workflow-workflow-bundle-0.1.0` uses a
  deterministic two-member ZIP (`manifest.json` and `workflow.json`) with a
  digest-bound validated DSL artifact, fixed 8 MiB archive/2 MiB member/4 MiB
  total bounds, and secret-hygiene checks. Bundle verification is read-only
  and never extracts or executes the workflow, documented in
  [`workflow-bundles.md`](workflow-bundles.md)
- Installed quickstart result `skill2workflow-quickstart-result-0.1.0` includes
  value-free workspace metadata and fixed `operator_commands` argv arrays for
  inspection, approval, Doctor, and service startup, documented in
  [`quickstart.md`](quickstart.md)
- Release manifest schema `skill2workflow-release-artifact-manifest-0.1.0`, including archive/member SHA-256 hashes, fixed package metadata, and rejection of private/state wheel content, documented in [`release-artifact-manifest.md`](release-artifact-manifest.md)
- Release SBOM schema `skill2workflow-release-sbom-0.1.0`, using SPDX JSON 2.3 with one checksum entry per qualified wheel member and a package-to-file relationship set, documented in [`release-artifact-sbom.md`](release-artifact-sbom.md)
- Reproducible release evidence schema `skill2workflow-reproducible-build-0.1.0`, recording two byte-identical fixed-epoch wheel builds for one checkout and toolchain, documented in [`reproducible-builds.md`](reproducible-builds.md)
- Service soak evidence schema `skill2workflow-service-soak-evidence-0.1.0`, recording bounded repeated cutovers, idempotency replay/conflict checks, and SQLite/audit continuity without changing runtime contracts, documented in [`service-soak.md`](service-soak.md)
- Production Baseline evidence schema `skill2workflow-production-baseline-evidence-0.1.0`, recording the fixed local release/state-safety/service/observability check set without command output or sensitive values, documented in [`production-baseline-evidence.md`](production-baseline-evidence.md)
- Control-plane workflow version aliases and the `promote`/trigger resolution contract documented in `docs/triggers.md`
- Reviewable published workflow diffs and the optional compare-and-swap promotion precondition documented in [`workflow-releases.md`](workflow-releases.md)
- SQLite promotion transactionally couples the compare-and-swap check, alias mutation, and promotion audit append; JSON remains local-evaluation storage without cross-process coordination
- SQLite promotion reads the target directly and streams only the selected workflow's registry rows; alias CAS, uniqueness, audit atomicity, and JSON compatibility remain unchanged
- SQLite publication and deprecation transactionally couple single-record registry changes with their audit rows, preserving immutable-version and retry semantics
- `workflow-artifacts` report contract `skill2workflow-workflow-artifact-report-0.1.0`, including bounded registry/file consistency issues and known-failure SQLite publication cleanup
- `audit-consistency` report contract `skill2workflow-run-audit-report-0.1.0`, including bounded missing/duplicate/unexpected run-audit projections; one control-plane lifecycle/runtime emission is transactional in SQLite, while the two-database boundary remains diagnostic-only
- Global `audit-consistency` inspection counts durable runs and reads at most the newest 256 summaries; targeted inspection reads one run directly, preserving the fixed report contract without an unbounded run-state load
- `audit-consistency` treats waiting human gates and recovered interrupted runs as clean when their single durable lifecycle projection is present; the status field is not counted as a second event
- Authenticated `GET /api/v1/audit-consistency` and `service-audit-consistency` reuse the exact run-audit report contract with a 64 KiB response bound, zero-write semantics, and readiness-independent availability when auth and SQLite state are readable
- Targeted `GET /api/v1/audit-consistency/{run_id}` and `service-audit-consistency --run-id` reuse the same report contract and safe `run_` identifier grammar to inspect one run beyond the global report window
- Authenticated `GET /api/v1/audit-events` and `service-audit-events` reuse the fixed `skill2workflow-audit-event-list-0.1.0` redacted SQLite projection with exact filters, opaque sequence cursors, a 100-item/64 KiB bound, and no raw payload, credential, connector metadata, or error disclosure, documented in [`remote-audit-events.md`](remote-audit-events.md)
- Authenticated `GET /api/v1/recurring-schedules` and `service-recurring-schedules` reuse the fixed `skill2workflow-recurring-schedule-list-0.1.0` redacted inventory contract with a 64 KiB response bound and no schedule mutation
- Protected `PATCH /api/v1/recurring-schedules/{schedule_id}` and `service-recurring-schedule-patch` reuse the fixed `skill2workflow-recurring-schedule-patch-0.1.0` redacted response contract with a 1 MiB request/16 KiB response bound, a `next_run_at` compare-and-swap, safe-field-only merging, trigger-input preservation, and no progress reset, documented in [`remote-schedule-patch.md`](remote-schedule-patch.md)
- Authenticated recurring-schedule dispatch reads and `service-recurring-dispatches` reuse the fixed `skill2workflow-recurring-schedule-dispatch-list-0.1.0` redacted diagnostics contract with 100-item/64 KiB bounds and no scheduler mutation
- Cursor-paged recurring-schedule dispatch reads and `service-recurring-dispatch-page` use the separate `skill2workflow-recurring-schedule-dispatch-page-0.1.0` redacted contract with an opaque `(scheduled_for, dispatch_id)` cursor, 100-item/64 KiB bounds, and no scheduler mutation; the fixed recent-tail contract remains unchanged, documented in [`remote-schedule-dispatch-pages.md`](remote-schedule-dispatch-pages.md)
- Authenticated `GET /api/v1/workflow-artifacts` and `service-workflow-artifacts` reuse the fixed `skill2workflow-workflow-artifact-report-0.1.0` value-free consistency contract with a 64-issue/64 KiB remote bound and no repair mutation
- Authenticated `GET /api/v1/backup-readiness` and `service-backup-readiness` reuse the fixed `skill2workflow-backup-readiness-0.1.0` value-free preflight contract with a 16 KiB remote bound, active-lease blocking semantics, and no backup mutation
- Authenticated `GET /api/v1/backup-inventory` and `service-backup-inventory` reuse the fixed `skill2workflow-remote-backup-inventory-0.1.0` redacted contract with a 100-item/64 KiB bound, optional owner-only `runtime.backup_parent_dir` configuration, and no backup mutation, documented in [`remote-backup-inventory.md`](remote-backup-inventory.md)
- Authenticated `GET /api/v1/backup-inventory-pages` and `service-backup-inventory-page` reuse the fixed `skill2workflow-remote-backup-inventory-page-0.1.0` redacted cursor-page contract with an opaque continuation cursor, 100-item/64 KiB bounds, and no backup mutation, documented in [`remote-backup-inventory-pages.md`](remote-backup-inventory-pages.md)
- Authenticated `POST /api/v1/backup-retention-plan` and `service-backup-retention-plan` reuse the fixed `skill2workflow-remote-backup-retention-plan-0.1.0` redacted policy-bound aggregate contract with a 64 KiB request/16 KiB response bound, complete-inventory truncation blocking, a fixed `limit + 1` retention scan guard, and no backup mutation, documented in [`remote-backup-retention-plan.md`](remote-backup-retention-plan.md)
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
- Protected `GET /api/v1/workflow-explanations/{workflow_id}/{version}` and `service-workflow-explain` reuse the fixed `skill2workflow-workflow-explanation-0.1.0` side-effect-free plan contract with a 64 KiB response bound and no connector, credential, instruction, or trigger-input values documented in [`workflow-explanation.md`](workflow-explanation.md)
- Protected `POST /api/v1/workflow-preflights/{workflow_id}/{version}` and `service-workflow-preflight` reuse the fixed `skill2workflow-workflow-preflight-0.1.0` value-free admission contract with 1 MiB request/64 KiB response bounds, no connector calls or credential resolution, and stable input/mapping issue codes documented in [`workflow-preflight.md`](workflow-preflight.md)
- Protected `POST /api/v1/workflow-deprecations` and `service-workflow-deprecate` reuse the fixed `skill2workflow-workflow-deprecation-0.1.0` redacted registry-retirement contract with a 1 MiB request bound, idempotent SQLite status/alias mutation, one audit event, and no artifact deletion documented in [`remote-workflow-deprecation.md`](remote-workflow-deprecation.md)
- Protected `GET /api/v1/workflows` and `service-workflows` reuse the fixed `skill2workflow-workflow-inventory-0.1.0` redacted version-inventory contract with a 100-item/64 KiB bound, no scheduler lease acquisition, and no state mutation documented in [`remote-workflow-inventory.md`](remote-workflow-inventory.md)
- Authenticated `POST /api/v1/recurring-schedules/{schedule_id}/enable|disable` and protected `service-schedule-enable`/`service-schedule-disable` reuse the fixed `skill2workflow-recurring-schedule-action-0.1.0` contract, preserve the legacy empty-body form, optionally enforce an atomic `next_run_at` compare-and-swap token, and retain idempotent state transitions plus bounded audit evidence documented in [`remote-schedule-actions.md`](remote-schedule-actions.md)
- Authenticated `PUT /api/v1/recurring-schedules/{schedule_id}` and protected `service-recurring-schedule-update` reuse the fixed `skill2workflow-recurring-schedule-update-0.1.0` contract, require an observed `next_run_at` compare-and-swap token, preserve durable dispatch progress, and return a fixed `409` on stale updates as documented in [`remote-schedule-update.md`](remote-schedule-update.md)
- Authenticated `DELETE /api/v1/recurring-schedules/{schedule_id}` and protected `service-recurring-schedule-delete` require explicit confirmation, a `next_run_at` compare-and-swap token, a disabled schedule, and no active claim; the fixed `skill2workflow-recurring-schedule-delete-0.1.0` contract retains dispatch history and makes retries safe with a tombstone as documented in [`remote-schedule-delete.md`](remote-schedule-delete.md)
- Resume, cancellation, and recurring schedule action retries reconcile a
  committed SQLite state mutation with missing control-plane audit evidence
  without replaying workflow execution or a human decision; this is a retry
  recovery contract, not a distributed transaction or provider compensation
- JSON storage as the dependency-light default
- Local JSON run-state documents use the fixed 8 MiB regular-file/no-follow,
  device/inode-bound read and write contract documented in
  [`json-run-state-boundary.md`](json-run-state-boundary.md); the JSON state
  shape and SQLite service requirement remain unchanged
- The local JSON control-plane index uses the fixed 8 MiB regular-file/
  no-follow, device/inode-bound read and write contract documented in
  [`json-control-index-boundary.md`](json-control-index-boundary.md); registry
  shape and the JSON-to-SQLite import path remain compatible
- SQLite storage as an opt-in local persistence mode
- Built-in connector runtime boundaries documented in `docs/connectors.md`
- Built-in HTTP connector request/response payloads are bounded to 1 MiB with fixed overflow and invalid-UTF-8 failures, as documented in `docs/connectors.md`
- Built-in HTTP `response_mode` accepts `full` or `metadata`; metadata mode retains only status and bounded size facts after reading, while `full` preserves the legacy headers/body projection
- Fresh SQLite state-layout markers are atomically published without replacing a concurrent marker; startup remains single-directory and non-distributed
- Credential placeholder and fixture hygiene boundary documented in `docs/credential-boundary.md`
- Local credential handle boundary documented in `docs/credential-boundary.md`
- Local CLI JSON credential maps use the fixed 2 MiB regular-file/no-follow,
  device/inode-bound read contract documented in `docs/credential-file-boundary.md`;
  the existing `{"credentials": {...}}` shape remains compatible
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
- Run-detail projection reads at most the fixed 50-event audit tail at the storage boundary; response shape, total run-state event count, and redaction semantics remain unchanged
- Authenticated `GET /runs`, redacted run-list schema `skill2workflow-run-list-0.1.0`, and protected `service-runs` CLI documented in `docs/run-list.md`
- Authenticated `GET /api/v1/runs`, filtered cursor-paged run-list schema `skill2workflow-run-list-0.2.0`, and protected `service-run-page` CLI documented in `docs/run-list.md`; the 0.1.0 `/runs` tail contract remains unchanged
- Authenticated `GET /api/v1/support-bundle`, redacted support-bundle schema `skill2workflow-support-bundle-0.1.0`, and protected `service-support-bundle` CLI documented in `docs/support-bundle.md`
- SQLite trigger idempotency for keyed service/control-plane requests, including durable replay, fixed `409` conflicts, and unresolved-outcome fail-closed behavior documented in `docs/triggers.md`
- Bounded active execution timeout semantics for `policies.default_timeout_ms`, including fixed `execution_timeout` evidence and human-gate pause behavior documented in `docs/runtime-policy.md`
- Bounded per-node active execution timeout semantics for node `timeout_ms`, including fixed `node_timeout` evidence, retry/backoff coverage, and human-gate pause behavior documented in `docs/runtime-policy.md`
- Bounded global workflow deadline semantics for `policies.workflow_timeout_ms`, including fixed `workflow_timeout` evidence and human-gate wall-clock coverage documented in `docs/runtime-policy.md`
- Lease-owned SQLite deadline sweep semantics for waiting runs, including bounded atomic expiry, cancellation precedence, audit reconciliation, and no-successor execution documented in `docs/recurring-scheduling.md`
- Connector retry policy semantics for `max_attempts` and bounded fixed `backoff_ms`, including control-plane audit and local visual evidence documented in `docs/runtime-policy.md` and `docs/connectors.md`
- Optional `tool_call.on_fallback` transition semantics, edge validation, LiteGraph slot projection, and fixed `node_fallback` evidence documented in `docs/workflow-dsl-contract.md`
- SQLite audit integrity result contract `skill2workflow-audit-integrity-0.1.0` and the payload-free `audit-verify` CLI; this does not claim signatures or JSON/JSONL chain guarantees
- Local `audit --limit` accepts a bounded 1-1000 tail after storage-level filters and preserves chronological output; omitting it retains the complete-list compatibility path
- Offline `control-snapshot --max-items` accepts a bounded 1-1000 window for JSON and SQLite state, preserves aggregate totals, and leaves live snapshots at their fixed 100-item bound
- Local `runs --limit` and `control-runs --limit` accept a bounded 1-1000 newest-summary window for JSON and SQLite state; omitting the flag retains the complete-list compatibility path
- SQLite bounded run discovery, cursor pages, offline snapshot windows, global audit consistency, and authenticated run detail read compact summary/event projections instead of parsing complete run state documents; complete local state reads remain unchanged
- SQLite bounded recurring-schedule inventory reads compact schedule metadata instead of parsing complete definitions or trigger inputs; explicit schedule retrieval and dispatch paths remain unchanged
- SQLite service readiness checks registry readability with a count query rather than materializing every published workflow; explicit workflow inventory/list APIs retain their complete-list compatibility behavior
- SQLite stable-alias trigger resolution uses a direct version lookup plus a selected-workflow cursor rather than loading the global registry; exact-version precedence, ambiguity rejection, and replay pinning remain unchanged
- Authenticated Prometheus text metric names, fixed label vocabularies, live HTTP/scheduler pressure gauges, and operational event schema `skill2workflow-operational-event-0.1.0` documented in `docs/observability.md`
- The operator-managed `examples/observability/prometheus-alerts.yml` starter pack and its fixed-metric safety checks are documented in `docs/prometheus-alerts.md`; it adds no runtime route, dependency, or automatic remediation
- The operator-managed `examples/observability/grafana-dashboard.json` read-only dashboard and its fixed-metric safety checks are documented in `docs/grafana-dashboard.md`; it adds no runtime route, dependency, or mutation
- Authenticated `GET /metrics` zero-body request validation: malformed,
  transfer-encoded, oversized, and non-empty scraper bodies use the shared
  bounded request error contract before telemetry rendering
- Control snapshot `skill2workflow-control-snapshot-0.1.0`, `schemas/control-snapshot-0.1.0.schema.json`, authenticated `GET /api/v1/control-snapshot`, and live `window` semantics documented in `docs/live-control-snapshot.md`
- Retention policies `skill2workflow-retention-policy-0.1.0`, `skill2workflow-retention-policy-0.2.0`, and `skill2workflow-retention-policy-0.3.0`, aggregate plan/apply summaries, and protected state semantics documented in `docs/data-retention.md`
- Additive SQLite `run_executions` ownership tickets, terminal `interrupted` run state, and no-replay recovery semantics documented in `docs/interrupted-recovery.md`
- Long-running SQLite service interrupted-run takeover fences foreign active executions in fixed 100-row transactions and renews the lease between full batches; fencing, audit reconciliation, returned recovered states, and no-replay semantics remain unchanged
- Interrupted-run audit reconciliation streams interrupted states and checks one `(run_id,event_type)` projection at a time; the long-running service repairs fixed 100-row cursor pages and renews the lease between full pages, while startup recovery no longer enumerates the complete run table or audit history
- File-backed single-team Bearer and execution-time directory credential contracts documented in `docs/security-boundary.md`
- Durable recurring schedule input contract `skill2workflow-schedule-0.2.0` and its published JSON Schema
- Recurring dispatch states, missed-run policies, and single-SQLite lease semantics documented in `docs/recurring-scheduling.md`
- Long-running SQLite service takeover recovery marks stale recurring-dispatch claims `uncertain` in fixed 100-row transactions and renews the lease between full batches; direct dispatcher and CLI complete-batch compatibility, no-automatic-retry behavior, and recovery counts remain unchanged
- State backup manifest `skill2workflow-state-backup-0.1.0`, current `skill2workflow-sqlite-layout-0.1.0`, and verified offline restore contract documented in `docs/backup-restore.md`
- Local `backup-list` contract `skill2workflow-state-backup-list-0.1.0` provides a read-only 1-1000 newest-set inventory with fixed integrity, size, and layout metadata; it does not delete or upload backups
- Local `backup-retention-plan` contracts `skill2workflow-backup-retention-policy-0.1.0` and `skill2workflow-backup-retention-plan-0.1.0` provide a read-only, complete-inventory-only expiration plan with an explicit cutoff and minimum-valid-backup floor; truncation blocks candidates and no backup is mutated
- Local one-shot schedule documents use a fixed 2 MiB UTF-8 envelope across save, lookup, listing, compact inventory, and due discovery; a document that grows beyond the bound is rejected before normalization, while the recurring SQLite schedule contract is unchanged
- SQLite backup preflight, creation, and restored-state artifact validation stream ordered workflow registry references instead of materializing the complete registry row set; manifest and artifact contracts remain unchanged
- Local `schedules --limit` and `schedule-dispatches --limit` contracts `skill2workflow-local-schedule-list-0.1.0` and `skill2workflow-local-schedule-dispatch-list-0.1.0` provide 1-1000 compact newest windows, omit trigger inputs and lease ownership, and preserve the complete-list path when the flag is omitted
- Local `workflows --limit` reuses `skill2workflow-workflow-inventory-0.1.0` for a read-only 1-100 newest published-version window with workflow-content redaction; the complete-list path remains unchanged when the flag is omitted
- Local `workflow-artifacts` retains a fixed 1-256 value-free issue window while preserving complete issue counts and truncation status; it never repairs or deletes artifacts
- SQLite `workflow-artifacts` streams registry rows and checks filesystem artifacts by exact reference instead of materializing the full registry/path set; JSON keeps its dependency-light compatibility path
- SQLite audit-chain verification counts events and streams the ordered rows; legacy-chain rebuilds use the same cursor path without changing the fixed result contract
- Local `schedule-run-due --max-items` accepts a 1-100 side-effect batch budget and leaves unclaimed due schedules for later invocations; omission preserves complete-batch compatibility
- Bounded one-shot due discovery lazily enumerates schedule files, retains at most the requested full-definition window, and selects earliest normalized `(run_at, schedule.id)` records; compact `schedules --limit` likewise avoids materializing the full path list
- The long-running SQLite service scheduler uses a fixed 100-dispatch batch per polling pass, leaving remaining due schedules for later passes without changing lease, claim, or uncertain-outcome semantics
- State layout marker `skill2workflow-state-layout-marker-0.1.0`, fail-closed compatibility preflight, and legacy-to-current copy-on-write migration documented in `docs/upgrade-migration.md`
- Bounded body/query HTTP connector input mapping and response retention mode documented in `docs/connectors.md`
- Minimum connector manifest contract documented in `docs/connectors.md`
- explicit local connector fixture loading for examples, using `load_external_connector(path)` plus `ConnectorRuntime([external_connector])`; the loader accepts only a regular non-symlink file, reads at most 2 MiB of UTF-8 source through a device/inode-bound no-follow descriptor, and detects replacement or growth before compiling
- Connector package layout expectations documented in `docs/connectors.md`

## Experimental

These surfaces may change while the project learns from real workflows:

- Parser heuristics for arbitrary `SKILL.md` formats
- Local `SKILL.md` parse/compile inputs use the fixed 2 MiB regular-file,
  no-follow, device/inode-bound read contract documented in
  `docs/skill-input-boundary.md`
- Skill IR shape
- Compiler defaults for new node types
- LiteGraph node layout and web editor UI
- Visual write-back allowlist beyond the documented fields
- Connector manifest fields beyond the documented minimum contract
- Dynamic connector loading, automatic connector discovery and product-specific connector packages
- Connector package installation, marketplace indexing, OAuth, hosted callbacks, and distributed queues
- HTTP connector request metadata beyond documented method, URL, headers, body, timeout, response mode, credential handles, and bounded body/query input mapping
- Credential providers beyond the documented local static file and mounted directory boundaries
- Exponential retry strategies, provider-specific retry classification, and automatic retry of uncertain external effects beyond the documented connector-node retry and fixed backoff boundary
- Hosted secret storage, OAuth, multi-tenant RBAC, and IAM
- Advanced input mapping beyond the bounded body/query contract, templating, and connector request interpolation
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
