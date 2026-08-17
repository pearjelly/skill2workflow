# Changelog

This file records notable user-visible changes. Work remains under
`Unreleased` until maintainers explicitly approve a package version and
release; Roadmap loop completion alone does not publish a new version.

## [Unreleased]

### Added

- Added optional service-wide `runtime.http_allowed_origins` governance for
  the built-in HTTP connector. Exact origins are validated at service startup
  and enforced before credential resolution or network access for direct and
  recurring execution; omission remains backward compatible.

- Normalized unexpected exceptions from explicitly loaded external connector
  fixtures to the fixed `external connector execution failed` message before
  they can enter durable run state.

- Normalized built-in HTTP transport and request-body serialization failures
  to fixed value-free messages, preventing URLs, provider-transport details,
  proxy text, socket errors, and mapped-value representations from entering
  durable connector failure results.

- Added a fixed no-redirect boundary to the built-in HTTP connector. `3xx`
  responses now fail before any follow-up request, preventing credential
  headers from being replayed to another target; non-redirect behavior is
  unchanged.

- Added a direct-egress boundary to the built-in HTTP connector. Ambient
  `http_proxy`, `https_proxy`, and `ALL_PROXY` settings are ignored so
  resolved credentials cannot be routed through an unreviewed process proxy.

- Added bounded HTTP request metadata: 16,384-byte URLs, 32-byte ASCII
  methods, and 64-entry/65,536-byte headers. Invalid metadata now fails with
  the connector's normalized error contract before network access.

- Added optional exact-origin HTTP egress governance through
  `connector.request.allowed_origins`, enforced before credential resolution
  and network access; omission remains backward compatible.

- Added opt-in HTTP `response_mode: "metadata"` to discard raw response headers
  and bodies after bounded reading while preserving status and size metadata;
  `full` remains the backward-compatible default.

- Added bounded HTTP connector query-parameter input mapping through
  `/query/<name>` targets, with scalar-only values and no template or expression
  evaluation.

- Added `connectors --connector-fixture` so operators can inspect a reviewed
  external connector manifest before running it, without creating state or
  executing connector code.

- Hardened explicit external connector fixture loading with a 2 MiB UTF-8
  source bound, regular-file/no-follow checks, device/inode identity checks,
  replacement detection, and in-memory compilation.

- Added an explicit local `--connector-fixture` flag for `run`, `resume`, and
  `bundle-run`, allowing reviewed external connector fixtures to participate in
  one CLI process without changing the default registry or service boundary.

- Added secret-free `operator_commands` argv arrays to the installed quickstart
  result, plus the fixed `quickstart-result-0.1.0` schema, so wrappers can
  inspect, approve, doctor, and start the generated workspace without manual
  path reconstruction.

- Added a standard installed-console `skill2workflow --version` identity
  check, with wheel qualification proving it matches distribution metadata.

- Added optional `bundle-run --summary` output for a value-free successful-run
  contract containing status counters and Bundle provenance without workflow,
  input, node-result, connector, or credential payloads.

- Extended the isolated wheel package smoke to execute the installed
  `bundle-run --summary` command against SQLite and verify its fixed schema,
  waiting status, consent flag, and Bundle fingerprint.

- Added optional `bundle-run --format json` output for a stable, value-free
  side-effect-consent refusal report that automation can classify without
  parsing human-readable stderr.

- Added exact verified Bundle provenance to successful runs through the
  value-free `context.bundle_run.bundle_sha256` digest, computed from the same
  bounded archive read used for execution.

- Added compact `context.bundle_run` evidence to successful Bundle runs,
  recording verification and side-effect-consent booleans without retaining
  credentials, provider payloads, or extra Bundle values.

- Added an explicit `bundle-run --allow-side-effects` consent guard: a
  connector-bearing Bundle cannot create state, resolve credentials, or call a
  network connector until the operator opts in.

- Added `bundle-preflight` for value-free, side-effect-free admission checks on
  verified bundles and optional trigger input; `bundle-run --input` reuses the
  same check before creating state or resolving credentials.

- Added `bundle-run`: verify a portable bundle before delegating to the normal
  local executor, with no publication, alias mutation, or second execution
  authority.

- Added value-free `bundle-diff` review for two verified Workflow DSL bundles,
  reusing the published-version structural diff semantics without exposing
  workflow values or executing either artifact.

- Added explicit local `bundle-publish` handoff: a bundle is fully verified
  in memory before entering the normal immutable Workflow publication path.
  Publishing does not execute workflows, resolve credentials, or call
  connectors.

- Added deterministic local Workflow DSL bundles through `bundle-create` and
  `bundle-verify`. The fixed `skill2workflow-workflow-bundle-0.1.0` ZIP
  contains only a digest-bound manifest and validated `workflow.json`; creation
  and verification enforce secret hygiene, regular-file/path safety, bounded
  archive/member sizes, and no-extraction/no-execution verification. Bundles
  are a sharing format, not a credential container or second execution
  authority. See `docs/workflow-bundles.md`.

- Added local `preflight` and authenticated `service-workflow-preflight`
  commands for checking trigger input contracts and HTTP request mappings before
  execution. The fixed `skill2workflow-workflow-preflight-0.1.0` report is
  bounded, side-effect free, and value free: it never calls connectors,
  resolves credentials, writes state, or echoes trigger values. See
  `docs/workflow-preflight.md`.

- Added `explain` and authenticated `service-workflow-explain` execution-plan
  views for Workflow DSL artifacts. The fixed
  `skill2workflow-workflow-explanation-0.1.0` contract is bounded to 64 KiB,
  reports topology, human gates, connector metadata, input shape, retries, and
  timeouts, and excludes connector request values, instructions, credentials,
  and trigger inputs. The plan is strictly read-only and side-effect free;
  see `docs/workflow-explanation.md`.

- Bounded SQLite trigger-ledger `response_json` values to 64 KiB UTF-8 JSON
  objects. Completed-row writes validate before advancing the pending claim;
  oversized, malformed, empty, or non-object replay rows fail closed as
  unresolved idempotency outcomes without changing trigger keys, fingerprints,
  replay fields, or the public response schema. See
  `docs/sqlite-trigger-ledger-boundary.md`.

- Bounded SQLite workflow registry `record_json` values to 2 MiB UTF-8 JSON
  objects across publication, direct/complete reads, alias resolution,
  snapshots, diagnostics, deprecation, promotion, and JSON-to-SQLite import.
  Replacement and alias-update batches validate before mutation; registry
  fields, aliases, checksums, artifacts, and compatibility paths remain
  unchanged. See `docs/sqlite-workflow-record-boundary.md`.

- Bounded local control-plane audit events to 1 MiB UTF-8 JSON-object
  documents across JSONL and SQLite writes, bounded reads, and JSON-to-SQLite
  import. Batch appends validate before emitting any member; event fields,
  filters, and audit-chain semantics remain compatible. See
  `docs/audit-event-boundary.md`.

- Bounded complete SQLite run-state documents to 8 MiB on durable writes and
  full-state reads, including interrupted recovery, cancellation, deadline
  expiry, and startup summary repair. The SQLite service state shape and
  compact operator projections remain compatible; see
  `docs/sqlite-run-state-boundary.md`.

- Bounded the normalized result envelope returned by explicitly loaded
  external connectors to 1 MiB and required a strict standard-JSON
  round-trip before the result enters durable run state. Existing built-in
  HTTP payload limits and connector contracts remain unchanged; see
  `docs/external-connector-result-boundary.md`.

- Bounded immutable Workflow artifact publication and reads to 2 MiB with a
  shared regular-file/no-follow descriptor contract, device/inode identity,
  max-plus-one reads, and growth/replacement checks across control-plane
  execution, SQLite cleanup, and verified backup paths. Workflow DSL shape,
  checksums, and backup/SQLite contracts remain unchanged.

- Bounded the local JSON control-plane `workflows/index.json` to 8 MiB with
  regular-file, no-follow, descriptor identity, and growth/replacement-race
  checks across save, load, and JSON-to-SQLite import. Registry shape and
  SQLite service storage remain unchanged.

- Bounded local JSON run-state serialization and reads to 8 MiB with
  regular-file, no-follow, descriptor identity, and growth/replacement-race
  checks across save, load, listing, and interrupted-run recovery. SQLite
  service storage and the JSON state shape remain unchanged.

- Bounded local `SKILL.md` parse/compile inputs to 2 MiB with regular-file,
  no-follow, descriptor identity, and growth/replacement-race checks while
  preserving the existing parser and source-line mapping contract.

- Bounded local JSON credential-file reads to 2 MiB with regular-file,
  no-follow, descriptor identity, and growth/replacement-race checks. The
  existing local credential shape and service directory-provider contract are
  unchanged.

- Hardened runtime service configuration loading with a fixed 64 KiB bound,
  regular-file and no-symlink checks, descriptor identity binding, and
  growth/replacement-race rejection for `service` and `service-doctor`.

- Added a shared 8 MiB UTF-8 boundary for generic JSON files supplied to the
  local CLI. Reads check the size before opening and after a bounded read to
  catch growth races; invalid operator inputs now return a stable non-zero
  exit without a traceback. Trigger, one-shot schedule, and service-body
  limits remain stricter where their existing contracts require them.

- Bounded local one-shot schedule document reads to a fixed 2 MiB UTF-8
  envelope across save, lookup, listing, compact inventory, and due discovery.
  Oversized or growth-raced documents fail closed before normalization; the
  existing trigger-input and recurring SQLite contracts are unchanged.

- Bounded one-shot schedule discovery now lazily enumerates local schedule
  files. `schedule-run-due --max-items` retains only the requested number of
  earliest `(run_at, schedule.id)` definitions, and `schedules --limit` no
  longer materializes the complete directory path list; complete-list and
  complete due-run compatibility paths are unchanged.

- Bounded remote backup retention-plan directory scanning. The local and
  authenticated remote preflight stops after the first over-budget backup set,
  preserving the fixed `inventory_truncated` contract while preventing an
  arbitrarily large backup parent from causing an unbounded retention scan.

- Added protected remote backup retention planning through
  `POST /api/v1/backup-retention-plan` and the installed
  `service-backup-retention-plan` CLI. The fixed redacted
  `skill2workflow-remote-backup-retention-plan-0.1.0` contract reuses the
  normalized local policy, blocks incomplete inventories, reports aggregate
  eligible/preserved counts and bytes, and never deletes or exposes backup
  names, paths, manifests, or workflow values.

- Added cursor-paged protected remote backup inventory through
  `GET /api/v1/backup-inventory-pages` and the installed
  `service-backup-inventory-page` CLI. The separate redacted 100-item/64 KiB
  contract walks older evidence with an opaque continuation cursor while
  preserving the exact recent-window inventory route.
- Added protected remote backup inventory through
  `GET /api/v1/backup-inventory` and the installed
  `service-backup-inventory` CLI. The optional owner-only backup parent is
  created by service bootstrap; the 100-item/64 KiB response reports only
  redacted integrity, age, layout, and size metadata and never exposes backup
  names, paths, workflow values, or credentials.
- Added a separate cursor-paged recurring-schedule dispatch diagnostics
  surface at `GET /api/v1/recurring-schedule-dispatch-pages` (and its targeted
  schedule route), plus the installed `service-recurring-dispatch-page` CLI.
  The new redacted 100-item/64 KiB contract walks older evidence with an
  opaque SQLite ordering cursor while preserving the exact recent-tail route.
- Added protected remote recurring-schedule patches through
  `PATCH /api/v1/recurring-schedules/{schedule_id}` and the installed
  `service-recurring-schedule-patch` CLI. Operators can update only safe
  workflow/timing fields while the service preserves trigger input and durable
  dispatch progress; stale `next_run_at` intent returns a fixed `409`.
- Added optional compare-and-swap protection to the existing remote recurring
  schedule enable/disable actions. Legacy empty-body callers remain supported;
  protected CLI callers can bind the transition to the last observed
  `next_run_at` and receive a fixed `409` on stale intent.
- Added protected remote recurring-schedule retirement through
  `DELETE /api/v1/recurring-schedules/{schedule_id}` and the installed
  `service-recurring-schedule-delete` CLI. Deletion requires explicit
  confirmation, a disabled schedule, and a `next_run_at` compare-and-swap;
  it retains dispatch history and makes ambiguous retries safe with a durable
  tombstone.
- Added protected remote recurring-schedule updates through
  `PUT /api/v1/recurring-schedules/{schedule_id}` and the installed
  `service-recurring-schedule-update` CLI. The request carries the last
  observed `next_run_at` compare-and-swap token, preserves durable dispatch
  progress, rejects stale edits with a fixed `409`, and never returns trigger
  input.
- Added protected remote recurring-schedule creation through
  `POST /api/v1/recurring-schedules` and the installed
  `service-recurring-schedule-add` CLI. Identical retries are no-ops, changed
  definitions return a fixed conflict, SQLite creation serializes with
  dispatcher claims, and the response never returns trigger input.
- Added the authenticated, read-only `GET /api/v1/audit-events` route and
  `service-audit-events` CLI. The fixed redacted SQLite projection supports
  exact filters and opaque sequence cursors under a 100-item/64 KiB bound,
  and never returns workflow DSL, trigger context, connector metadata,
  credentials, or raw provider errors.
- Added a bounded Production Baseline evidence bundle that runs the approved
  release, state-safety, service, and observability checks with isolated child
  workspaces and a secret-free summary contract. Release preflight can opt in
  with `--production-baseline`.
- Added a bounded real-process service soak and cutover drill. It repeats
  authenticated triggers across SQLite restarts, verifies idempotency replay
  and conflict handling, checks audit integrity/consistency, and runs in the
  operational CI gate without external providers.
- Added a dependency-free fixed-epoch reproducibility proof for release wheels.
  The release path builds twice, requires byte and manifest equality, writes
  value-free `reproducible-build.json` evidence, and repeats the proof in the
  release preflight and CI artifact gate.
- Added a dependency-free SPDX 2.3 release artifact SBOM for qualified wheels.
  Package smoke writes a value-free member inventory bound to the wheel archive
  SHA-256, and a dedicated CI artifact gate verifies the qualification and
  repository secret hygiene.
- Added a dedicated CI recovery and state-safety gate that runs isolated
  backup/restore, migration, retention, cancellation, interrupted-recovery,
  scheduling, and service-Doctor drills on Python 3.14, with matching local
  reproduction commands for contributors and release operators.
- Bounded the source reads for `audit-consistency`: global inspection counts
  durable runs and loads only the newest 256 summaries, while `--run-id` reads
  one run directly; the fixed report contract and diagnostic-only semantics are
  unchanged.
- Added bounded compact local schedule inspection through `schedules --limit`
  and `schedule-dispatches --limit`. The 1-1000 windows omit trigger inputs,
  lease owners, and claim-expiry details while preserving complete-list
  compatibility when the flags are omitted.
- Added bounded local published-workflow inventory through `workflows --limit`.
  The 1-100 redacted window reuses the workflow-inventory contract and omits
  workflow content while preserving complete-list compatibility.
- Bounded workflow artifact diagnostics now retain only the fixed issue window
  while preserving full issue counts and truncation status.
- SQLite workflow artifact diagnostics now stream registry rows and check
  filesystem artifacts by exact reference, avoiding a full registry/path-set
  materialization on long-running production instances.
- SQLite audit-chain verification and legacy-chain rebuilds now stream ordered
  event rows after count-only reads, avoiding full audit-history materialization.
- SQLite backup preflight, creation, and restore validation now stream ordered
  workflow artifact references, avoiding full registry-row materialization.
- Stale recurring-dispatch claim recovery now streams eligible SQLite rows in
  the existing recovery transaction, avoiding full dispatch-ledger
  materialization while preserving `uncertain` and no-automatic-retry semantics.
- Interrupted-run takeover now streams foreign active-execution rows in the
  existing SQLite recovery transaction, avoiding full execution-ledger
  materialization while preserving fencing and no-replay semantics.
- SQLite workflow alias promotion now reads the target directly and streams
  only the selected workflow's registry rows, avoiding unrelated-version
  materialization while preserving CAS and audit atomicity.
- Interrupted-run audit reconciliation now streams interrupted states and
  checks one `(run_id,event_type)` projection at a time, avoiding complete
  run-table and audit-history materialization during startup recovery.
- Live readiness now checks SQLite workflow-registry readability with a count
  query instead of loading every published record; complete list APIs remain
  compatible.
- Stable-alias trigger resolution now performs a direct exact-version lookup
  and scans only the selected workflow's registry rows, avoiding global
  registry materialization while preserving alias and replay semantics.
- Long-running service scheduler passes now claim at most 100 recurring
  dispatches, keeping backlog processing batch-bounded while preserving the
  existing lease and claim-before-execute semantics.
- Long-running service takeover now marks stale recurring claims uncertain in
  fixed 100-row transactions and renews the lease between full batches,
  preserving no-automatic-retry semantics while bounding recovery writes.
- Long-running service interrupted-run takeover now fences foreign executions
  in fixed 100-row transactions and renews the lease between full batches,
  preserving no-replay and audit-reconciliation semantics.
- Added an optional `schedule-run-due --max-items` side-effect batch budget;
  bounded invocations process at most 100 schedule records and leave the rest
  eligible for a later run.
- Added bounded read-only backup expiration planning through
  `backup-retention-plan`. An explicit cutoff and minimum-valid-backup floor
  produce candidates only from a complete inventory; truncation, invalid sets,
  and minimum retention fail closed, and the command never deletes or rewrites.
- Added bounded read-only local backup inventory through `backup-list`, with
  fixed integrity status, creation time, layout, file count, and byte totals;
  it never deletes, uploads, or exposes backup paths or contents.
- Added bounded local run discovery through `runs --limit` and
  `control-runs --limit`. JSON and SQLite retain only the newest 1-1000
  summaries in durable timestamp order while the omitted flag preserves the complete
  list path.
- Added `control-snapshot --max-items` for bounded offline operator exports.
  JSON and SQLite snapshots retain newest collection windows up to 1,000 while
  preserving aggregate totals; live snapshots keep their fixed 100-item bound.
- Added bounded local audit inspection through `audit --limit`. Filters are
  applied in JSON/SQLite storage before retaining the newest matching events,
  with a fixed 1-1000 range and chronological output.
- Added atomic first-use SQLite state-layout marker publication. Concurrent
  starters now observe either no marker or a complete owner-only marker, never
  a partially-written JSON document.
- Added a fixed 1 MiB payload boundary to the built-in HTTP connector. Oversized
  serialized request bodies fail before network I/O; oversized or invalid-UTF-8
  success/error responses fail before partial payloads enter run state.
- Added bounded per-node active execution deadlines through node `timeout_ms`.
  Expiry records fixed `node_timeout` evidence, counts retry backoff inside the
  same node window, pauses while human gates wait, and never follows a
  successor after a safe-point timeout.
- Added protected cursor-paged run discovery at `GET /api/v1/runs` and the
  `service-run-page` CLI. Operators can filter by status/workflow and continue
  through history without loading unbounded run state; the existing `/runs`
  0.1.0 contract remains unchanged.
- Added a bounded global workflow deadline: `policies.workflow_timeout_ms`
  starts at run creation, continues while human gates wait, and records fixed
  `workflow_timeout` failure evidence at executor safe points. The deadline is
  capped at 30 days and does not forcefully abort an in-flight provider call.
- Added a lease-owned SQLite deadline sweeper that atomically expires waiting
  runs after their global deadline, preserves cancellation precedence, never
  runs a successor, and retries missing terminal audit evidence.
- Added bounded connector retry backoff: `retry.backoff_ms` and
  `policies.default_retry.backoff_ms` now provide a fixed, capped delay before
  connector retries, with timeout/cancellation safe points and run-state,
  control-plane audit, and local visual evidence. The default remains zero for
  compatibility.
- Added a dependency-free release artifact manifest for wheels, recording the
  archive and member SHA-256 hashes plus fixed package metadata without source
  paths or workflow values.
- Added an importable, read-only Grafana dashboard starter pack for the fixed service metrics, with a dependency-free JSON/privacy smoke check.
- Added a dependency-free Prometheus alert starter pack for the fixed service metrics, with a value-free repository smoke check.
- Added the installed `service-wait` command for bounded startup and cutover
  readiness polling using the existing unauthenticated probe contract; it
  prints only the final fixed probe payload and preserves stable exit codes.
- Added the label-free `skill2workflow_scheduler_dispatch_inflight` gauge to
  authenticated `/metrics`, exposing an already-admitted recurring dispatch
  during graceful drain without changing the support-bundle 0.1.0 contract.
- Added the authenticated, label-free `skill2workflow_service_inflight_requests`
  gauge to `/metrics`, aligned with the fixed request-admission budget while
  excluding probes and the scrape itself; the versioned support-bundle
  contract remains unchanged.
- Closed the scheduler shutdown window: once `draining` begins, no new
  recurring scheduled trigger is admitted, while an already admitted dispatch
  retains the existing completion/uncertain-outcome semantics.
- Added an atomic shutdown admission boundary: mutating routes now fail closed
  with a bounded retryable response after `draining`, while health, metrics,
  and read-only operator diagnostics remain available.
- Serialized service lifecycle transitions across shutdown callers and the
  serving thread, preventing a concurrent shutdown from overwriting `draining`
  with `ready` and preserving ordered lifecycle events.
- Hardened service lifecycle startup so a shutdown request received during
  scheduler initialization is preserved; the service no longer publishes
  `ready` or enters the request loop after draining begins.
- Hardened the authenticated `/metrics` read surface with the shared zero-body
  request contract: malformed, transfer-encoded, oversized, and non-empty
  scraper bodies are rejected before telemetry rendering.
- Corrected run-audit consistency projections for waiting and interrupted
  runs: lifecycle events are no longer counted twice, so healthy paused or
  recovered runs no longer raise false operator attention.
- Added cross-database operator-action reconciliation for resume and
  cancellation: when durable run state commits before control-plane audit
  evidence, a safe retry repairs only the missing bounded evidence instead of
  re-executing a workflow or gate decision. The same failure-window retry
  contract is documented for recurring schedule enable/disable actions.
- Added production-boundary CI gates for every supported Python matrix entry:
  security isolation, authenticated observability, and two-cycle SQLite service
  restart continuity now run on every push and pull request.
- Added deterministic service teardown: scheduler startup failures now close the
  listener, and scheduler cleanup failures cannot leave the port bound or stop
  the service from reaching the final `stopped` lifecycle state.
- Added lifecycle event-logger isolation: operational collector failures can no
  longer abort service startup, strand scheduler threads, raise from shutdown
  callbacks, or mask final cleanup; lifecycle logging remains best-effort.
- Added a fail-closed service exception boundary: unexpected handler failures
  return a fixed `503 service unavailable` response without exception details,
  while connection aborts and telemetry failures cannot cause a second write or
  leak a traceback through the service response.
- Added exact-length request-body reads: early EOF now returns the fixed
  `request body incomplete` error and cannot be parsed or trigger a workflow.
- Added the bounded `service-probe` deployment gate, with a fixed health and
  readiness contract, stable exit codes, no redirects or proxy use, and no
  server-body disclosure.
- Added a fixed five-second request-body socket deadline to the local webhook
  adapter and authenticated service. Half-open or stalled bodies now receive a
  bounded HTTP `408` response and release their handler slot without triggering
  a workflow or blocking graceful drain.
- Added authenticated remote operational readiness at
  `GET /api/v1/operational-readiness` and the protected
  `service-operational-readiness` CLI, combining fixed lifecycle,
  artifact-consistency, audit-integrity, and offline-backup statuses without
  lifecycle mutation or sensitive-value export.
- Added authenticated remote retention readiness at
  `POST /api/v1/retention-readiness` and the protected
  `service-retention-readiness` CLI, binding the normalized copy-on-write
  policy to a fixed preflight, blocking active leases with null counts, and
  returning aggregate eligibility only after a quiesced read-only inspection.
- Added local `service-token-rotate` for atomic owner-only ingress-token replacement without secret output or service restart.
- Added protected remote Workflow deprecation at
  `POST /api/v1/workflow-deprecations` and the installed
  `service-workflow-deprecate` client, with idempotent SQLite status/alias
  retirement, one audit event, immutable artifact preservation, and a fixed
  redacted response.
- Added authenticated remote Workflow inventory at `GET /api/v1/workflows`
  and the installed `service-workflows` client, with fixed redacted version
  metadata, lifecycle counts, 100-item/64 KiB bounds, and no-write semantics.
- Added atomic lifecycle/runtime audit batches and a bounded `audit-consistency`
  report for missing, duplicate, or unexpected projections between durable run
  state and the control-plane audit store.
- Added authenticated remote `GET /api/v1/audit-consistency` and the protected
  `service-audit-consistency` CLI, reusing the exact redacted report contract
  with a fixed response bound and zero-write/readiness-independent behavior.
- Added targeted remote audit inspection with a safe `/run_id` path and
  `service-audit-consistency --run-id`, avoiding global-window truncation while
  preserving the fixed report and error boundaries.
- Added an authenticated, read-only recurring-schedule inventory at
  `GET /api/v1/recurring-schedules` and the protected
  `service-recurring-schedules` CLI, with fixed bounds and trigger-input
  redaction.
- Added protected, idempotent recurring-schedule enable/disable actions at
  `POST /api/v1/recurring-schedules/{schedule_id}/enable|disable` and the
  `service-schedule-enable`/`service-schedule-disable` CLI commands, with
  dispatcher-safe SQLite serialization, fixed response schema, and bounded
  mutation audit evidence.
- Added bounded, authenticated recurring-schedule dispatch diagnostics at
  `GET /api/v1/recurring-schedule-dispatches` and the targeted schedule route,
  plus the protected `service-recurring-dispatches` CLI, with uncertain-state
  visibility and lease/input redaction.
- Added authenticated remote workflow artifact consistency diagnostics at
  `GET /api/v1/workflow-artifacts` and the protected
  `service-workflow-artifacts` CLI, reusing the fixed value-free report with
  bounded issue and response windows.
- Added authenticated remote backup readiness at `GET /api/v1/backup-readiness`
  and the protected `service-backup-readiness` CLI, reusing a fixed redacted
  report with a 16 KiB bound and active-scheduler-lease blocking semantics.
- Added authenticated remote SQLite audit-chain verification at
  `GET /api/v1/audit-integrity` and the protected `service-audit-integrity` CLI,
  reusing the fixed payload-free integrity result with a 16 KiB bound and no
  repair mutation.
- Added authenticated remote runtime identity at `GET /api/v1/runtime-info` and
  the protected `service-runtime-info` CLI, exposing fixed package,
  compatibility-line, state-layout, lifecycle, readiness, and lease metadata
  with a 16 KiB bound and no configuration disclosure.
- Added the protected `service-trigger` CLI for remote published-workflow
  triggering, requiring a stable idempotency key, reusing shared input/body
  bounds, and validating the compact response before output.
- Added protected `POST /api/v1/workflow-releases` and the
  `service-workflow-publish` CLI, reusing immutable SQLite publication with a
  1 MiB request bound and a fixed path-free checksum response.
- Added protected `POST /api/v1/workflow-promotions` and the
  `service-workflow-promote` CLI, reusing transactional SQLite alias promotion,
  an optional compare-and-swap guard, and a fixed path-free summary response.
- Added authenticated read-only `GET /api/v1/workflow-diffs/...` and the
  `service-workflow-diff` CLI, reusing the value-free structural diff contract
  with a bounded response and no scheduler or state mutation.
- Added a bounded `workflow-artifacts` registry/file consistency report and
  cleanup of newly-created SQLite publication artifacts after known failures.
- Added an authenticated self-hosted runtime service with loopback-safe defaults, health and readiness probes, graceful shutdown, and durable SQLite state.
- Added durable recurring scheduling with explicit missed-run policies, persisted dispatch records, lease takeover, and uncertain-recovery handling.
- Added verified offline backup and restore, explicit copy-on-write state upgrade, and operator-controlled data retention for supported SQLite layouts.
- Added bounded runtime observability through authenticated Prometheus metrics and allowlisted operational NDJSON.
- Added durable cooperative cancellation and interrupted-run recovery with execution tickets, stale-writer fencing, and no automatic replay of unknown external effects.
- Bounded interrupted-run audit reconciliation in the long-running SQLite service to fixed 100-row cursor pages with lease renewal between full pages; direct complete-batch recovery and no-replay semantics remain compatible.
- Run-detail projections now apply their fixed 50-event audit tail at the storage query boundary, avoiding full per-run audit-history loads without changing the redacted response contract.
- SQLite bounded run discovery, cursor paging, snapshots, and global audit consistency now read compact run-summary/event projections instead of parsing complete run state documents; explicit detail and compatibility reads remain unchanged.
- SQLite bounded recurring-schedule inventory now reads a compact schedule-summary projection instead of parsing complete definitions that may contain large trigger inputs; full schedule and dispatch compatibility paths remain unchanged.
- SQLite authenticated run-detail reads now use a compact node-overlay/summary projection and a bounded event tail instead of parsing complete run state documents; JSON and explicit full-state compatibility paths remain unchanged.
- Added a secure service bootstrap and an installed controlled quickstart that reaches a durable human approval gate without a source checkout.
- Added a read-only `service-doctor` command with fixed secret-free diagnostics for configuration, authentication, credential directories, SQLite state, and loopback binding.
- Added descriptor-bound connector credential reads with private-directory and file permissions, no-follow identity checks, a 64 KiB limit, and execution-time atomic rotation.
- Added authenticated live Operator snapshots with a machine-readable schema, consistent collection windows, fixed byte bounds, a safe no-redirect CLI client, zero-write polling, and owner-only atomic output.
- Added a manually reviewed Linux systemd unit generator with non-overwriting output, state-only write access, fixed hardening directives, restart backoff, and SIGTERM-only shutdown.
- Added a Linux CI gate that runs `systemd-analyze verify` against a generated unit without installing or starting a service.
- Added an authenticated human-gate decision endpoint with an exact boolean body, durable success/failure branching, and waiting-only conflict semantics.
- Added protected `service-resume` and `service-cancel` CLI clients that read Bearer tokens from owner-only files and reject unsafe origins, redirects, and unbounded responses.
- Added authenticated redacted run detail at `GET /runs/{run_id}` and the protected `service-show` CLI with a fixed 50-event window and no raw workflow, input, connector, credential, or error payloads.
- Added authenticated redacted run discovery at `GET /runs` and the protected `service-runs` CLI with fixed status counts, a 100-item window, and no payload or credential export.
- Added an authenticated redacted support bundle at `GET /api/v1/support-bundle` and the protected `service-support-bundle` CLI with fixed aggregate observability, a nested run list, and owner-only atomic output.
- Added durable SQLite trigger idempotency: identical keyed retries replay the compact result without a second run, mismatched requests return fixed conflicts, and unresolved outcomes fail closed without storing input values.
- Enforced the existing bounded `policies.default_timeout_ms` runtime boundary at executor safe points, with persisted deadlines, human-gate pause semantics, and fixed timeout failure evidence.
- Added explicit `tool_call.on_fallback` transitions after exhausted connector retries, preserving failed-attempt evidence and promoting fixed fallback audit events.
- Added SQLite `sha256-chain-v1` audit integrity links, compact `audit-verify` verification, legacy-column upgrade, backup rejection for invalid current chains, and retained-copy re-chaining.
- Added a shared 1 MiB canonical UTF-8 trigger-input limit across CLI, webhook, one-shot schedule, and recurring schedule entry paths, with fixed oversize errors and no Workflow DSL compatibility change.
- Added optional bounded declarative `input_schema` contracts for published workflows, with publication validation and pre-idempotency trigger rejection for missing, mistyped, out-of-range, and undeclared input values.
- Added a fixed process-local service admission budget of 16 active business handlers, with a fixed retryable `429` response and probe availability under overload.
- Added stable workflow version promotion aliases with a `promote` CLI command, exact-version precedence, deprecation cleanup, and alias-scoped SQLite idempotency replay across later promotions.
- Added runtime published-artifact integrity verification: reads, promotions, triggers, and executions now compare each artifact with its control-plane checksum and fail closed before side effects when state is missing, malformed, or modified.
- Added reviewable published workflow releases with a bounded `workflow-diff` contract and an optional compare-and-swap precondition for alias promotion.
- Made SQLite workflow alias promotion atomic: the compare-and-swap check, alias mutation, and `workflow_promoted` audit row now commit together, preventing concurrent stale operators from overwriting a newer target.
- Made SQLite workflow publication and deprecation atomic: immutable registry changes and their audit rows commit together, concurrent versions are additive, and same-version matching publication retries are idempotent.
- Added the scoped domestic Feishu task connector and finalized redacted evidence from its controlled paid Pilot.

### Changed

- Advanced the documented maturity to Self-hosted Beta while retaining the single-tenant, one-team deployment boundary.
- Qualified the distributed wheel through an isolated build and install, production CLI coverage, metadata inspection, license verification, and private-artifact exclusion.
- Expanded the supported interpreter evidence to Python 3.9 through 3.14 while keeping runtime code dependency-light.
- Updated the pinned GitHub Actions toolchain to the green Dependabot revisions for checkout 7.0.1 and setup-python 7.0.0.

### Security

- Required authenticated business routes, file-backed ingress secrets, runtime credential-handle resolution, and external TLS termination for network exposure.
- Added a fixed redacted published-artifact integrity failure boundary; the checksum guard detects local artifact tampering but is not a signature or remote-attestation mechanism.
- Added repository security, support, moderation, pull-request, and CI supply-chain policies; GitHub Actions now use fixed reviewed commits, read-only permissions, bounded jobs, and non-persistent checkout credentials.
- Added repository-wide pre-commit hygiene scanning that rejects private paths, runtime state, key material, misplaced binary media, and symbolic links without reading rejected artifacts or echoing suspected secret values.
- Hardened explicit JSON hygiene scans to reject symbolic links, non-regular or unavailable files, invalid UTF-8, invalid JSON, and inputs above 2 MiB with fixed redacted findings instead of tracebacks.
- Hardened the local webhook adapter with the same bounded request-body and strict `Content-Length` contract as the authenticated service boundary.
- Hardened authenticated run-action bodies so malformed, oversized, transfer-encoded, or ambiguous requests return fixed JSON errors instead of terminating the handler.
- Restricted the unauthenticated local webhook adapter to loopback hosts so a local test command cannot be accidentally exposed on a public interface.
- Bound state-layout marker validation to one owner-only regular-file descriptor, rejected path-replacement races, and capped marker input at 16 KiB before decoding.
- Generated systemd units carry no secret values or `Environment=` entries and require a private regular service configuration plus a non-symlink executable.
- Bound ingress-token reads to one owner-only no-follow regular-file descriptor, capped token input at 16 KiB, and made service startup reject unsafe state or credential directory permissions.
- Required directory-backed connector credentials to use `0700` directories and `0600` regular files; symbolic links, replacement races, invalid UTF-8, empty values, and oversized inputs now fail closed without value disclosure.
- Restored the byte-for-byte official Apache License 2.0 text and made wheel qualification reject any modified or truncated license copy.
- Added maintainer-led governance and CODEOWNERS review routing for legal, security, release, schema, and runtime boundaries.

### Compatibility

- Workflow DSL `0.1.0` remains the execution truth source and stays readable by the current runtime.
- Existing unversioned SQLite state requires an explicit verified state upgrade into a new directory before current production commands use it.
- The runtime does not provide exactly-once execution, automatic provider reconciliation, hosted multi-tenancy, built-in TLS, or forceful interruption of an already-sent external request.
- The package remains version `0.1.0` until a separate release change approves and prepares the next version.

## [0.1.0] - 2026-07-03

- Published the first open-source bootstrap release with Skill parsing, Workflow DSL compilation and validation, durable local execution, human-gate pause/resume, connector execution, auditability, LiteGraph visualization, and the initial contributor and compatibility contracts. See the [v0.1.0 release notes](docs/releases/v0.1.0.md).

[Unreleased]: https://github.com/pearjelly/skill2workflow/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pearjelly/skill2workflow/releases/tag/v0.1.0
