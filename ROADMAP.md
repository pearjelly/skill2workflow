# Roadmap

This roadmap turns the approved `skill2workflow` design into small, verifiable delivery loops. Each loop should leave behind a runnable command, tests, documentation, and an inspectable artifact.

## Product Direction

The near-term target is a self-hosted, single-tenant workflow runtime for one team. The project remains local-first and dependency-light while adding the minimum controls needed for a durable production path.

Workflow DSL remains the authoritative execution source of truth. LiteGraph and future UI layers are editors and views, not runtime authorities. The approved foundation remains in `docs/superpowers/specs/2026-07-01-skill2workflow-design.md`, and the production roadmap design is recorded in `docs/superpowers/specs/2026-07-11-production-roadmap-design.md`.

## Status At A Glance

- Published release: `v0.1.0`
- Workflow DSL compatibility line: `0.1.x` artifacts using `schema_version: "0.1.0"`
- Completed delivery loops: 1-233
- Current maturity: Self-hosted Beta
- Active loop: None; Loop 233 is complete with strict local Skill decoding
- Next maturity gate: Production Baseline
- Next decision: select the next Production Baseline loop after reviewing the source-fidelity authoring evidence

## Production Readiness Path

### Local Evaluation

**Status:** Achieved.

The repository can compile, validate, publish, trigger, execute, pause, resume, audit, and visualize workflows locally. It includes JSON and SQLite state, controlled connector boundaries, local pilot scenarios, and an out-of-core Lark task connector in dry-run mode.

### Controlled Live Pilot

**Target loops:** 40.

**Status:** Achieved.

Loop 40 completed a paid assisted, single-team Pilot with five approved real
tasks across five `Asia/Shanghai` calendar days, two opaque private cases, one
human rejection, the fixed safety exercises, and seven passing verification
commands. The committed evidence is redacted and scoped to the fixed
`create_task` action; it does not claim general live SaaS readiness.

This gate requires the completed scoped live connector action plus controlled pilot evidence. It does not imply general live SaaS readiness.

### Self-hosted Beta

**Target loops:** 41-43.

**Status:** Achieved.

This gate requires a long-running service boundary, authenticated ingress, a production credential boundary, durable recurring scheduling, restart recovery, and concurrency-safe dispatch for one self-hosted instance.

SQLite is the minimum production persistence baseline for Self-hosted Beta. JSON and JSONL remain supported for examples, local development, and evaluation.

### Production Baseline

**Status:** Directional; Loops 44-233 complete, further loop numbers unassigned.

Loop 91 adds bounded remote Workflow inventory after the remote-deprecation
evidence. Loop 92 adds policy-bound remote retention readiness after the
inventory evidence. Loop 93 adds aggregate remote operational readiness after
the retention evidence. Loop 94 adds bounded request-body reads after the
operational-readiness evidence. Loop 95 adds an installed service probe after
the transport-boundary evidence. Loop 96 adds exact-length body reads after
the service-probe evidence. Loop 97 adds a fail-closed service exception
boundary after the exact-length body-read evidence. Loop 98 isolates lifecycle
event logging after review of the exception-boundary drill. Loop 99 hardens
service teardown after review of the lifecycle-observer drill. Loop 100 makes
the security, observability, and restart-continuity drills mandatory in CI.
The follow-on production hardening continues through Loop 193; the detailed
entries below record the operator-action recovery, audit-projection, metrics,
startup-shutdown, atomic lifecycle-state, shutdown-admission, and scheduler
dispatch boundaries, live HTTP request-pressure telemetry, and scheduler
dispatch-pressure telemetry, bounded readiness waiting, a fixed alert starter
pack, a read-only Grafana dashboard starter pack, a value-free release
artifact provenance manifest, bounded connector retry backoff, a bounded global workflow deadline plus its lease-owned waiting-run sweep, filtered cursor-paged run discovery, per-node active execution deadlines, a bounded built-in HTTP connector payload boundary, atomic first-use SQLite state initialization, bounded local audit inspection, bounded offline control snapshots, bounded local run discovery, bounded local backup inventory, bounded backup retention planning, bounded local schedule inspection, bounded local workflow inventory, bounded workflow artifact diagnostics, bounded due-run batches, bounded run-audit inspection, streaming SQLite audit integrity, streaming backup artifact registry reads, streaming stale-claim recovery, and streaming interrupted-run takeover, and streaming workflow promotion, streaming interrupted-run reconciliation, bounded readiness registry checks, bounded stable-alias resolution, bounded service dispatch batches, bounded stale-claim recovery writes, bounded interrupted-run takeover writes, bounded interrupted-run audit reconciliation, bounded run-detail audit reads, and compact SQLite run-summary projections.

Loop 101 closes the cross-database operator-action recovery gap. Resume and
cancellation retries reconcile a durable run-state commit with missing
control-plane audit evidence without replaying workflow execution or a human
decision; recurring schedule actions retain the same idempotent retry contract.
The loop preserves the existing service routes and response schemas while
making the failure window explicit and testable.

Loop 102 fixes two run-audit consistency false positives: a waiting human gate
and a recovered interrupted run are each represented by one durable lifecycle
event, so the status field is not projected a second time. The report contract,
read-only behavior, and execution authority remain unchanged.

Loop 103 closes a service protocol mismatch: the authenticated `/metrics`
read surface now rejects non-empty or unsupported request bodies before
rendering telemetry. This keeps scraper traffic on the documented zero-body
contract and prevents unread request bytes from crossing the service boundary.

Loop 148 makes the existing recovery and state-safety evidence mandatory in a
dedicated CI job. Backup/restore, state upgrade, retention, cancellation,
interrupted recovery, one-shot and recurring scheduling, and the service
Doctor now run as isolated Python 3.14 gates on every push and pull request.

Candidate evidence includes backup and restore, upgrade and migration policy, cancellation and retention behavior, logs or metrics export, fault drills, contract stability, and sustained real-team operating evidence. Backup/restore became Loop 44, state upgrade/migration became Loop 45, observability export became Loop 46, data retention/disposal became Loop 47, durable cooperative cancellation became Loop 48, interrupted-run crash recovery became Loop 49, release-artifact qualification became Loop 50, secure service bootstrap became Loop 51, the installed controlled quickstart became Loop 52, the operational readiness Doctor became Loop 53, descriptor-bound connector credentials became Loop 54, the authenticated live Operator snapshot became Loop 55, a manually reviewed Linux systemd unit became Loop 56, an authenticated human-gate decision endpoint became Loop 57, protected remote operator action clients became Loop 58, authenticated redacted run detail became Loop 59, authenticated redacted run discovery became Loop 60, authenticated redacted support bundle became Loop 61, durable trigger idempotency became Loop 62, bounded active execution timeout became Loop 63, declarative fallback transitions became Loop 64, SQLite audit integrity became Loop 65, bounded trigger inputs became Loop 66, declarative trigger input contracts became Loop 67, bounded service request admission became Loop 68, stable workflow version promotion aliases became Loop 69, published artifact integrity verification became Loop 70, and reviewable workflow releases became Loop 71 after review of the preceding evidence; atomic workflow alias promotion became Loop 72 after review of the release-review drill; atomic workflow registry mutations became Loop 73 after review of the promotion transaction drill; workflow artifact consistency diagnostics became Loop 74 after review of the registry mutation drill; atomic run-audit emission and consistency diagnostics became Loop 75 after review of the artifact consistency drill; authenticated remote run-audit consistency became Loop 76 after review of the remote diagnostic drill; targeted remote run-audit inspection became Loop 77 after review of the global-window operator gap; remote recurring-schedule inventory became Loop 78 after review of the remote operator scheduling gap; protected remote recurring-schedule actions became Loop 79 after review of the inventory drill; remote recurring-schedule dispatch diagnostics became Loop 80 after review of the schedule action drill; remote workflow artifact consistency diagnostics became Loop 81 after review of the remote dispatch evidence; remote backup readiness diagnostics became Loop 82 after review of the remote artifact consistency evidence; remote audit-chain verification became Loop 83 after review of the backup-readiness evidence; remote runtime identity diagnostics became Loop 84 after review of the remote audit-integrity evidence; protected remote workflow triggering became Loop 85 after review of the remote runtime-info evidence; protected remote Workflow publication became Loop 86 after review of the remote-trigger evidence; protected remote Workflow promotion became Loop 87 after review of the remote-publication evidence; protected remote Workflow diff became Loop 88 after review of the remote-promotion evidence; protected local ingress-token rotation became Loop 89 after review of the remote-diff evidence; protected remote Workflow deprecation became Loop 90 after review of the token-rotation evidence; bounded remote Workflow inventory became Loop 91 after review of the remote-deprecation evidence; policy-bound remote retention readiness became Loop 92 after review of the remote-inventory evidence; aggregate remote operational readiness became Loop 93 after review of the retention evidence; bounded request-body reads became Loop 94 after review of the operational-readiness evidence; and the deployment service probe became Loop 95 after review of the transport-boundary evidence; exact-length request-body reads became Loop 96 after review of the service-probe evidence; the fail-closed service exception boundary became Loop 97 after review of the body-read evidence. The bounded global workflow deadline became Loop 115 after review of the retry-backoff evidence. Remaining capabilities become numbered loops only after preceding evidence is reviewed.

Verified offline backup/restore, copy-on-write state migration, bounded telemetry export, copy-on-write retention/disposal, durable cooperative cancellation, fail-closed interrupted-run recovery, isolated wheel qualification, secure first-use initialization, an installed first-value workflow journey, read-only startup diagnostics, descriptor-bound connector credentials, a bounded live Operator read surface, a manually reviewed least-privilege Linux systemd unit, an authenticated human-gate decision endpoint, protected remote operator action clients, bounded redacted run detail, bounded redacted run discovery, a bounded redacted support bundle, durable SQLite trigger idempotency, bounded active execution timeout, declarative connector fallback transitions, tamper-evident SQLite audit verification, bounded trigger input validation, declarative trigger input contracts, bounded service request admission, stable workflow version promotion aliases, published artifact integrity verification, and reviewable workflow releases, plus atomic workflow alias promotion, atomic workflow registry mutations, workflow artifact consistency diagnostics, atomic run-audit emission and consistency diagnostics, targeted remote run-audit inspection, remote recurring-schedule inventory, protected remote recurring-schedule actions, bounded remote recurring-schedule dispatch diagnostics, remote workflow artifact consistency diagnostics, remote backup readiness diagnostics, remote audit-chain verification, remote runtime identity diagnostics, protected remote workflow triggering, protected remote Workflow publication, protected remote Workflow promotion, protected remote Workflow diff, protected local ingress-token rotation, protected remote Workflow deprecation, bounded remote Workflow inventory, policy-bound remote retention readiness, aggregate remote operational readiness, bounded request-body reads, the fixed deployment service probe, exact-length request-body reads, lifecycle event-logger isolation, deterministic service teardown, production-boundary CI gates for security, observability, and restart continuity, the uniform zero-body metrics boundary, startup-shutdown race protection, atomic lifecycle state transitions, atomic shutdown admission, and atomic scheduler dispatch admission, live in-flight request pressure metrics, a fixed Prometheus alert starter pack, a read-only Grafana dashboard starter pack, and a value-free release artifact provenance manifest, bounded connector retry backoff, a bounded global workflow deadline, filtered cursor-paged run discovery, per-node active execution deadlines, a bounded built-in HTTP connector payload boundary, atomic first-use SQLite state initialization, bounded local audit inspection, bounded offline control snapshots, bounded local run discovery, bounded local backup inventory, bounded backup retention planning, bounded local schedule inspection, bounded local workflow inventory, bounded interrupted-run audit reconciliation, bounded run-detail audit reads, and compact SQLite run-summary projections, compact SQLite recurring-schedule projections, compact SQLite run-detail projections, and recovery and state-safety CI gates, an SPDX release artifact SBOM, reproducible fixed-epoch wheel builds, bounded service soak/cutover evidence, and a bounded Production Baseline evidence bundle, are achieved by Loops 44-152. Production Baseline remains directional until the remaining candidate evidence is selected, delivered, and reviewed; these controls do not advance project maturity by themselves.

Loop 190 adds a bounded, descriptor-bound explicit external connector fixture
loader without making dynamic code loading available to the service or remote
trigger paths. Loop 191 adds a read-only CLI manifest inspection path for an
explicit fixture without creating state or executing connector code. Loop 192
adds bounded scalar query-parameter mapping for the built-in HTTP connector
without enabling templates, expressions, or dynamic header mapping. Loop 193
adds an opt-in metadata-only response projection that discards raw HTTP
response headers and bodies after bounded reading.

Loop 194 adds a fixed no-redirect boundary to the built-in HTTP connector after
reproducing credential-header replay across two local HTTP servers.

Loop 195 adds a direct-egress boundary after reproducing ambient proxy routing
of a credentialed HTTP request through a local proxy server.

Loop 196 adds bounded and normalized HTTP URL, method, and header metadata
after reproducing raw `urllib` exceptions and unbounded request envelopes.

Loop 197 adds optional exact-origin egress governance for built-in HTTP
requests, enforced before credential resolution and network access.

Loop 198 adds fixed, value-free built-in HTTP transport and request-body
serialization failures so provider-transport, URL, proxy, socket, and
mapped-value exception text cannot enter durable connector failure results.

Loop 199 adds a fixed boundary for ordinary exceptions raised by explicitly
loaded external connector fixtures before they can escape into the executor or
durable run state.

The lease-owned workflow deadline sweep became Loop 116 after review of the
global-deadline evidence. Filtered cursor-paged run discovery became Loop 117
after review of the service's bounded run-list tail. Per-node active execution
deadlines became Loop 118 after review of the global deadline and retry-backoff
boundaries. The built-in HTTP connector payload boundary became Loop 119 after
review of unbounded request/response I/O. Atomic first-use SQLite state
initialization became Loop 120 after the concurrent marker-read failure drill.
Bounded local audit inspection became Loop 121 after the long-running audit
tail memory drill.
Bounded offline control snapshots became Loop 122 after the unbounded local
snapshot export drill.
Bounded local run discovery became Loop 123 after the unbounded local run list
inspection drill. Bounded local backup inventory became Loop 124 after the
multi-backup integrity inspection drill. Bounded backup retention planning
became Loop 125 after the manual backup expiration gap review.
Bounded local schedule inspection became Loop 126 after the unbounded local
schedule and dispatch inspection drill. Bounded local workflow inventory became
Loop 127 after the unbounded published-version inspection drill. Bounded
artifact diagnostic retention became Loop 128 after the full issue-collection
memory drill. Bounded due-run batches became Loop 129 after the unbounded
manual scheduler drain drill. Bounded run-audit inspection became Loop 130 after the global report's 256-run window still materialized every historical run before truncation. Streaming SQLite audit integrity became Loop 132 after the verifier and legacy-chain upgrade path still materialized the complete ordered event history. Streaming backup artifact registry reads became Loop 133 after backup preflight and restore validation still materialized every workflow reference before processing artifacts. Streaming stale-claim recovery became Loop 134 after scheduler restart recovery still materialized every eligible dispatch row before updating uncertain claims. Streaming interrupted-run takeover became Loop 135 after process-loss recovery still materialized every foreign active-execution row before fencing abandoned runs. Streaming workflow promotion became Loop 136 after SQLite alias moves still materialized unrelated workflow versions before updating the selected alias. Streaming interrupted-run reconciliation became Loop 137 after startup audit repair still enumerated the complete run table and audit history after takeover. Bounded readiness registry checks became Loop 138 after every live readiness probe still materialized the complete SQLite workflow registry. Bounded stable-alias resolution became Loop 139 after each alias trigger still loaded unrelated workflow versions before selecting its target. Bounded service dispatch batches became Loop 140 after the long-running scheduler still claimed all due recurring schedules in one polling pass. Bounded stale-claim recovery writes became Loop 141 after lease takeover still updated every expired claim in one transaction even after source reads became streaming. Bounded interrupted-run takeover writes became Loop 142 after process-loss recovery still fenced every foreign execution in one transaction even after source reads became streaming. Bounded interrupted-run audit reconciliation becomes Loop 143 after the service still scanned and repaired every missing interruption projection without a cursor batch or lease-renewal boundary. Bounded run-detail audit reads become Loop 144 after the fixed 50-event response still loaded a complete per-run audit history before truncation. Compact SQLite run-summary projections become Loop 145 after bounded operator reads still parsed complete run state documents containing workflow, input, and node-result data.
These are verified as bounded local controls, not maturity-gate advances;
Production Baseline remains directional.

## Active Loop

No delivery loop is currently active. The detailed entries below are retained
as historical evidence for completed Production Baseline loops; the current
completion point and next-selection rule are authoritative in “Status At A
Glance” and “Rolling Loop Queue”.

### Loop 56: Linux systemd Supervision

**Status:** Complete.

**Prior basis:** The secure bootstrap can create a ready workspace and the Doctor can diagnose it, but operators still had to hand-author a supervisor definition. That left restart semantics, least-privilege filesystem access, signal handling, and the service command line vulnerable to deployment-specific drift.

**Outcome:** `systemd-unit` validates one secure service configuration and writes one non-overwriting Linux `.service` file. It fixes the service account, command, restart/backoff, SIGTERM-only shutdown, `0700` process umask, systemd sandboxing, and a least-privilege split: only SQLite state is writable while configuration, ingress-token, and connector paths are explicitly read-only.

**Evidence:** [`docs/systemd-service.md`](docs/systemd-service.md) defines the manual account, generation, target-host verification, enabling, shutdown, and boundary contracts. Unit and CLI tests cover path and account injection, private input, output permissions, no-overwrite, fixed sandbox directives, no environment or secret output, and port stability. `scripts/systemd_service_smoke.py` proves the real CLI generator and Doctor path without requiring systemd on the development machine.

**Safety boundary:** This is one manually enabled Linux systemd unit, not account provisioning, automatic `systemctl` execution, Launchd, Windows services, containers, Kubernetes, remote monitoring, log shipping, hosted TLS, or forceful provider-request abort. Each target host must run `systemd-analyze verify` and explicitly review/enable the output before treating it as a deployment unit.

The repeatable evidence command is:

```bash
python3 scripts/systemd_service_smoke.py --work-dir /tmp/skill2workflow-systemd-service-loop56
```

Loop 56 closes the single-host supervisor-definition gap without altering host state or expanding the network boundary. Current maturity remains Self-hosted Beta until the remaining Production Baseline evidence is explicitly completed and reviewed.

### Loop 57: Authenticated Human-Gate Decisions

**Status:** Complete.

**Prior basis:** The service could trigger, inspect, and cooperatively cancel durable runs, but an operator still needed local CLI access to approve or reject a waiting human gate. That made the self-hosted service boundary incomplete for a controlled remote review handoff.

**Outcome:** `POST /runs/{run_id}/resume` accepts one exact `{"approved": true|false}` body behind the existing Bearer boundary. It reuses the control-plane executor, follows the declared success/failure branch, persists compact ingress and `run_resumed` evidence, and returns a fixed conflict for repeated or non-waiting decisions.

**Evidence:** [`docs/human-approval.md`](docs/human-approval.md) defines the stable endpoint, exact body, error contract, external TLS boundary, and operator verification. Service, control-plane, telemetry, documentation, and full-suite tests cover authentication, strict input, durable branch behavior, bounded bodies, route labels, and audit redaction.

**Safety boundary:** This is one single-tenant Bearer-authenticated decision route. It excludes hosted RBAC, multi-user identity, arbitrary reason text, bulk decisions, hosted callbacks, remote audit storage, and exactly-once provider effects.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_authenticated_resume_endpoint_requires_exact_decision_and_reuses_audit_path \
  -v
```

Loop 57 closes the remote human-gate handoff gap without expanding the workflow DSL or network bind boundary. Current maturity remains Self-hosted Beta until the remaining Production Baseline evidence is explicitly completed and reviewed.

### Loop 58: Protected Remote Operator Action Clients

**Status:** Complete.

**Prior basis:** Loop 57 exposed safe authenticated service actions, but operators still needed to hand-write `curl` requests or build their own token-bearing client. That created avoidable command-line secret and redirect/proxy hazards during routine approval and cancellation work.

**Outcome:** The installed CLI now provides `service-resume` and `service-cancel`. Both read a protected Bearer token file, validate an HTTPS or loopback origin and safe run identifier, disable proxies and redirects, enforce a bounded `application/json`/`no-store` response, and print only the compact action result.

**Evidence:** [`docs/human-approval.md`](docs/human-approval.md) documents the operator commands and boundary. Client, CLI, live-snapshot compatibility, documentation, and installed-wheel help tests cover exact requests, fixed errors, redirect/size rejection, and token-file handling.

**Safety boundary:** This is a convenience client for the existing single-tenant service routes. It adds no retries, browser token storage, RBAC, approval identity, bulk actions, or provider-side exactly-once guarantee.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest tests.test_service_client tests.test_cli.CliTests.test_service_action_commands_keep_remote_operator_contract_compact -v
```

Loop 58 closes the operator ergonomics gap without changing the service protocol or workflow execution authority. Current maturity remains Self-hosted Beta until the remaining Production Baseline evidence is explicitly completed and reviewed.

### Loop 59: Authenticated Redacted Run Detail

**Status:** Complete.

**Prior basis:** Loop 58 made remote approval and cancellation safe from an installed CLI, but an operator still had to fetch a broad snapshot and locally search it before deciding which run to act on. The broad snapshot also mixed registry, audit, connector, and run collections, which was unnecessary for a single-run handoff.

**Outcome:** `GET /runs/{run_id}` serves one authenticated, read-only `skill2workflow-run-detail-0.1.0` projection. It includes fixed run status fields, compact node overlays, and at most the latest 50 allowlisted events. The installed `service-show` client validates the origin, protected token file, response headers, byte bound, and schema before printing the projection.

**Evidence:** [`docs/run-detail.md`](docs/run-detail.md) defines the schema, redaction and availability boundaries. Dashboard, service, client, CLI, telemetry, schema, documentation, and full-suite tests prove that workflow DSL, trigger input, node-result payloads, connector responses, credential values, and raw errors do not cross the boundary.

**Safety boundary:** This is a single-tenant diagnostic read surface. It does not expose full run state, append audit events, mutate execution, add pagination cursors, accept arbitrary filters, or provide hosted RBAC, browser sessions, or remote audit storage.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_run_detail_is_bounded_and_redacts_context_results_and_errors \
  tests.test_service.RuntimeServiceTests.test_run_detail_is_authenticated_redacted_bounded_and_read_only \
  tests.test_service_client.ServiceClientTests.test_run_detail_uses_authenticated_get_and_validates_redacted_contract \
  -v
```

Loop 59 closes the single-run operator diagnosis gap while preserving the existing execution authority and single-tenant network boundary. Current maturity remains Self-hosted Beta until the remaining Production Baseline evidence is explicitly completed and reviewed.

### Loop 60: Authenticated Redacted Run Discovery

**Status:** Complete.

**Prior basis:** Loop 59 let an operator inspect a known run safely, but the operator still had to obtain a `run_id` from the broad control snapshot or another system. That made the remote list → inspect → decide handoff incomplete and encouraged unnecessary export of registry and audit collections.

**Outcome:** `GET /runs` serves one authenticated, read-only `skill2workflow-run-list-0.1.0` projection with fixed status counts and at most 100 compact run summaries. The installed `service-runs` client validates the origin, protected token file, response headers, byte bound, and schema before printing the projection.

**Evidence:** [`docs/run-list.md`](docs/run-list.md) defines the fixed fields, window semantics, redaction boundary, and operator sequence. Dashboard, service, client, CLI, telemetry, schema, documentation, wheel, and full-suite tests prove that run discovery does not expose workflow DSL, trigger input, node-result payloads, connector responses, credentials, or raw errors, and does not append audit events or acquire the scheduler lease.

**Safety boundary:** This is a single-tenant discovery read surface. It excludes arbitrary filters, pagination cursors, full state export, mutation, browser sessions, RBAC, remote audit storage, and any provider-side execution guarantee.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_run_list_is_bounded_and_redacted \
  tests.test_service.RuntimeServiceTests.test_run_list_is_authenticated_bounded_and_read_only \
  tests.test_service_client.ServiceClientTests.test_run_list_uses_authenticated_get_and_validates_contract \
  -v
```

Loop 60 completes the remote operator discovery handoff without changing workflow execution authority or the single-tenant network boundary. Current maturity remains Self-hosted Beta until the remaining Production Baseline evidence is explicitly completed and reviewed.

### Loop 61: Authenticated Redacted Support Bundle

**Status:** Complete.

**Prior basis:** Loop 60 completed run discovery, but incident triage still required an operator to manually combine readiness, metrics, run-list, and service details. That increased support friction and encouraged sharing broader snapshots or raw state directories.

**Outcome:** `GET /api/v1/support-bundle` serves one authenticated, read-only `skill2workflow-support-bundle-0.1.0` projection. It combines fixed lifecycle state, structured aggregate observability, and the nested redacted run-list contract under a 128 KiB response bound. The installed `service-support-bundle` client validates the origin, protected token file, headers, byte bound, and schema before atomically writing a 0600 file.

**Evidence:** [`docs/support-bundle.md`](docs/support-bundle.md) defines the incident handoff, exclusions, and operator command. Dashboard, telemetry, service, client, CLI, schema, documentation, wheel, and full-suite tests prove that the bundle excludes paths, workflow DSL, trigger input, node-result payloads, connector responses, credentials, raw errors, audit payloads, and request headers, while not appending audit state or acquiring the scheduler lease.

**Safety boundary:** This is a single-tenant diagnostic artifact. It excludes remote upload, tracing, raw logs, full state export, browser sessions, RBAC, hosted support, and automatic disclosure or retention decisions.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_support_bundle_is_authenticated_redacted_bounded_and_read_only \
  tests.test_service_client.ServiceClientTests.test_support_bundle_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_support_bundle_writes_private_output \
  -v
```

Loop 61 closes the incident-handoff gap without changing workflow execution authority or the single-tenant network boundary. Current maturity remains Self-hosted Beta until the remaining Production Baseline evidence is explicitly completed and reviewed.

### Loop 62: Durable SQLite Trigger Idempotency

**Status:** Complete.

**Prior basis:** The service already authenticated webhook requests and recurring dispatches, but `idempotency_key` was only metadata. A client retry could therefore start a second workflow run and repeat an external connector effect.

**Outcome:** SQLite control-plane triggers now atomically claim a safe non-empty key before execution. An identical completed retry returns the original compact response without a new run or duplicate run-lifecycle audit event; a different request using the key returns a fixed conflict; and a concurrent or interrupted claim remains unresolved and fail-closed. The ledger stores only scope, a SHA-256 request fingerprint, compact response metadata, status, and timestamps. Authenticated HTTP ingress continues to record its normal authentication event for each accepted request.

**Evidence:** [`docs/triggers.md`](docs/triggers.md) defines the key grammar, fingerprint boundary, replay contract, fixed `409` errors, and JSON/local compatibility boundary. Trigger normalization, SQLite storage, control-plane, authenticated service, recurring-dispatch, backup/restore, and full-suite tests prove duplicate suppression, mismatch rejection, concurrency safety, unknown-outcome fencing, no input-value persistence, and replay safety after restore.

**Safety boundary:** This is durable idempotency for one self-hosted SQLite control plane. It excludes exactly-once provider effects, automatic retries after unknown outcomes, key expiration or garbage collection, distributed coordination, cross-tenant identity, and JSON/local evaluation enforcement.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_trigger_idempotency_replays_without_new_run_or_audit \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_trigger_idempotency_conflicts_on_changed_request \
  tests.test_service.RuntimeServiceTests.test_authenticated_webhook_idempotency_replays_conflicts_and_does_not_duplicate_runs \
  tests.test_backup.StateBackupTests.test_backup_round_trip_preserves_trigger_idempotency_replay_safety \
  -v
```

Loop 62 closes the duplicate-trigger risk without changing Workflow DSL authority or claiming exactly-once provider execution. Current maturity remains Self-hosted Beta until the remaining Production Baseline evidence is explicitly completed and reviewed.

### Loop 63: Bounded Active Execution Timeout

**Status:** Complete.

**Prior basis:** The DSL already emitted `policies.default_timeout_ms`, but the executor treated it as inert metadata. A connector or long node sequence could therefore run without a bounded active execution segment, and the runtime-policy guide incorrectly listed idempotency as entirely unavailable after Loop 62.

**Outcome:** The compiler now validates a `0`-to-24-hour timeout bound. JSON and SQLite executors persist an active deadline, check it before each node and after connector returns, and fail closed with fixed `error_code: "execution_timeout"` evidence. Human-gate waiting clears the deadline and resume starts a fresh segment; outbound calls are never forcefully interrupted.

**Evidence:** [`docs/runtime-policy.md`](docs/runtime-policy.md) and the DSL compatibility guide define the semantics and exclusions. Compiler, executor, control-plane, schema, documentation, and full-suite tests cover bound validation, safe-point timeout, persisted failure evidence, human-gate pause semantics, and redaction-compatible terminal audit metadata.

**Safety boundary:** This is an active execution segment budget, not a global workflow deadline. It excludes human-gate expiry, delayed retry backoff, background workers, forceful provider cancellation, and exactly-once side-effect claims.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_executor.ExecutorTests.test_default_timeout_fails_closed_at_a_safe_point_and_persists_fixed_error \
  tests.test_executor.ExecutorTests.test_default_timeout_pauses_while_waiting_for_human_gate \
  tests.test_compiler.CompilerTests.test_default_timeout_policy_has_a_bounded_contract \
  tests.test_runtime_policy_docs -v
```

Loop 63 closes the inert-timeout gap without changing Workflow DSL version `0.1.0` or the single-tenant service boundary. Current maturity remains Self-hosted Beta until the remaining Production Baseline evidence is explicitly completed and reviewed.

### Loop 64: Declarative Fallback Transitions

**Status:** Complete.

**Prior basis:** Connector retries previously had only two outcomes: success or
the node's ordinary `on_failure` path. A workflow author could not declare a
safe alternate branch that preserved the failed attempt and routed to manual
recovery or a compensating step.

**Outcome:** `tool_call` nodes may now declare an optional `on_fallback`
transition. The compiler requires a valid target and edge, the executor routes
there only after connector retries are exhausted, and the failed node remains
durable with `node_failed` plus fixed `node_fallback` evidence. LiteGraph
projects the transition as a third output slot, while Workflow DSL remains the
topology authority.

**Evidence:** [`docs/workflow-dsl-contract.md`](docs/workflow-dsl-contract.md)
and [`docs/runtime-policy.md`](docs/runtime-policy.md) define the semantics and
exclusions. Compiler, executor, control-plane, schema, visualizer, and full
suite tests cover validation, failed-attempt preservation, audit promotion, and
fallback graph projection.

**Safety boundary:** This is an explicitly authored route, not provider
failover or an automatically generated retry. It excludes compensation,
backoff, queues, expression evaluation, and exactly-once side-effect claims.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_executor.ExecutorTests.test_connector_failure_routes_to_declared_fallback_without_retrying_side_effect \
  tests.test_compiler.CompilerTests.test_declared_fallback_transition_requires_a_matching_edge \
  tests.test_control_plane.ControlPlaneTests.test_published_fallback_promotes_fixed_route_evidence_to_audit \
  tests.test_visualizer.VisualizerTests.test_workflow_to_litegraph_preserves_fallback_transition_slot \
  -v
```

Loop 64 adds a compatible, explicit recovery branch without changing Workflow DSL version `0.1.0` or the single-tenant service boundary. Current maturity remains Self-hosted Beta until the remaining Production Baseline evidence is explicitly completed and reviewed.

### Loop 65: SQLite Audit Integrity

**Status:** Complete.

**Prior basis:** SQLite audit events were durable and queryable, but operators
had no fixed way to detect payload edits, row replacement, or broken ordering
after a backup, restore, or retention cutover. A count or SQLite integrity
check alone does not establish that the business evidence is internally
consistent.

**Outcome:** New SQLite audit rows carry a `sha256-chain-v1` previous-digest
link and digest over canonical event JSON. `audit-verify` prints a fixed,
payload-free result and exits nonzero for invalid or legacy-unsealed storage.
Opening the known legacy audit table adds and backfills the integrity columns;
malformed rows fail closed. Backup validation rejects an invalid current chain,
and copy-on-write retention rebuilds the retained chain after intentional row
deletion.

**Evidence:** [`docs/audit-integrity.md`](docs/audit-integrity.md) and
[`schemas/audit-integrity-0.1.0.schema.json`](schemas/audit-integrity-0.1.0.schema.json)
define the result contract, operator boundary, and exclusions. Storage,
backup, retention, CLI, documentation, and full-suite tests cover valid chains,
tampering, legacy upgrade, backup/restore preservation, and compact failure
evidence.

**Safety boundary:** This is one local SQLite integrity signal, not a digital
signature or an authenticity claim. It excludes remote audit streaming,
external key management, immutable storage, JSON/JSONL chain guarantees, and
hosted compliance retention policy.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_audit_integrity \
  tests.test_retention \
  tests.test_backup \
  -v
```

Loop 65 strengthens evidence trust without changing Workflow DSL version
`0.1.0` or the single-tenant service boundary. Current maturity remains
Self-hosted Beta until the remaining Production Baseline evidence is explicitly
completed and reviewed.

### Loop 66: Bounded Trigger Inputs

**Status:** Complete.

**Prior basis:** Trigger input is intentionally durable run context, but the
CLI and schedule normalizers previously accepted arbitrarily large JSON
objects. Webhook transport had a body limit, yet the four trigger entry paths
did not share one payload contract. That left SQLite context growth and
idempotency fingerprint work dependent on caller behavior.

**Outcome:** CLI, webhook, one-shot schedule, and recurring schedule inputs
share a fixed 1 MiB canonical UTF-8 JSON-object limit before persistence or
fingerprinting. Oversized values fail with fixed, non-secret errors; accepted
inputs retain the existing durable context and audit-key-only behavior. The
Workflow DSL `0.1.0` contract and provider connector boundary are unchanged.

**Evidence:** [`docs/triggers.md`](docs/triggers.md) and
[`docs/recurring-scheduling.md`](docs/recurring-scheduling.md) document the
limit and its non-confidentiality boundary. Trigger, schedule, recurring
schedule, webhook, documentation, and full-suite tests cover acceptance,
oversize rejection, and compatibility across all entry paths.

**Safety boundary:** This bounds one trigger input object; it does not encrypt,
redact, classify, or impose field-level business schemas. It excludes request
quotas, rate limiting, streaming uploads, JSON/JSONL historical-state rewrite,
and exactly-once provider effects.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_triggers \
  tests.test_schedules \
  tests.test_recurring_schedules \
  tests.test_webhooks \
  -v
```

Loop 66 strengthens the persistence boundary without changing Workflow DSL
version `0.1.0` or the single-tenant service boundary. Current maturity remains
Self-hosted Beta until the remaining Production Baseline evidence is explicitly
completed and reviewed.

### Loop 67: Declarative Trigger Input Contracts

**Status:** Complete.

**Prior basis:** Loop 66 bounded the size of trigger objects, but every
published workflow still accepted any JSON object. Operators could not declare
which business fields were required, which types were safe, or whether unknown
fields should be rejected before a run was claimed.

**Outcome:** Workflow DSL `0.1.0` now supports an optional, bounded
JSON-Schema-like `input_schema`. The root is an object; nested objects, arrays,
strings, numbers, booleans, nulls, ranges, enums, required properties, and
additional-property policy are validated by a dependency-free contract module.
Malformed contracts fail publication. Invalid trigger values fail before
SQLite idempotency claims, run-state creation, audit emission, or connector
execution, with fixed errors that expose only a JSON path and reason.

**Evidence:** [`docs/workflow-dsl-contract.md`](docs/workflow-dsl-contract.md),
[`docs/workflow-dsl-compatibility.md`](docs/workflow-dsl-compatibility.md), and
[`docs/triggers.md`](docs/triggers.md) define the supported subset, bounds,
compatibility behavior, and pre-execution boundary. Contract, runtime,
publication, SQLite idempotency, documentation, and full-suite tests cover
valid, malformed, missing, mistyped, unknown, and legacy inputs.

**Safety boundary:** This is a bounded local contract, not full JSON Schema,
field-level secrecy, coercion, redaction, encryption, rate limiting, hosted
validation, or exactly-once provider execution. Workflows without
`input_schema` retain the historical open-object behavior.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest tests.test_input_schema tests.test_webhooks -v
```

Loop 67 makes business-input intent executable without changing the Workflow
DSL version or the single-tenant service boundary. Current maturity remains
Self-hosted Beta until the remaining Production Baseline evidence is explicitly
completed and reviewed.

### Loop 68: Bounded Service Request Admission

**Status:** Complete.

**Prior basis:** The self-hosted service used `ThreadingHTTPServer`, so every
incoming non-probe request could enter authentication, projection, trigger,
or connector execution without a process-local active-work budget. A slow
connector or retry storm could therefore consume unbounded handler capacity
before the external proxy had a chance to shed traffic.

**Outcome:** All non-probe routes now acquire one of 16 fixed process-local
business-request slots without waiting. When no slot is available, the service
returns HTTP `429`, a fixed error body, and `Retry-After: 1`. Health and
readiness probes bypass the budget, and every admitted slot is released on
normal response and socket-failure paths. Rejection occurs before auth,
trigger normalization, SQLite idempotency claims, run creation, or business
audit writes.

**Evidence:** [`docs/service.md`](docs/service.md) defines the fixed budget,
response contract, probe behavior, and graceful-drain boundary. Service tests
exhaust the budget, verify a fixed `429`, verify probe availability, and cover
the existing full service suite; telemetry still records the bounded status.

**Safety boundary:** This is one process-local admission budget for one
single-tenant service. It is not a distributed queue, client identity quota,
rate limiter, back-pressure protocol, or exactly-once execution guarantee.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_business_routes_fail_fast_when_admission_budget_is_exhausted_but_probes_remain_available \
  tests.test_service_docs \
  -v
```

Loop 68 makes overload behavior explicit without changing the service schema,
Workflow DSL version, or single-tenant network boundary. Current maturity
remains Self-hosted Beta until the remaining Production Baseline evidence is
explicitly completed and reviewed.

### Loop 69: Stable Workflow Version Promotion Aliases

**Status:** Complete.

**Prior basis:** Published versions were immutable and safely triggerable, but
every schedule, webhook integration, and operator command had to name an exact
version. Releasing a replacement therefore required a coordinated configuration
edit, and an alias-based retry could not yet define safe behavior across a
promotion.

**Outcome:** The control plane now stores optional bounded aliases on existing
workflow registry records and exposes `promote <workflow_id> --version <version>
--alias <alias>`. Promotion moves an alias only between published versions and
records compact `workflow_promoted` evidence. Trigger, webhook, and schedule
paths resolve aliases before validation and return the resolved immutable
version; exact versions take precedence and deprecation clears aliases.

**Evidence:** [`docs/triggers.md`](docs/triggers.md) defines the alias grammar,
CLI contract, persistence behavior, and operator boundaries. Control-plane,
trigger, SQLite, CLI, and documentation tests cover alias movement, exact
precedence, deprecation cleanup, JSON/SQLite compatibility, new-version
execution, and replay of the original result after a later promotion.

**Safety boundary:** This is explicit single-tenant control-plane metadata. It
does not add health-based rollout, traffic splitting, automatic rollback,
hosted release orchestration, or exactly-once provider effects.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_workflow_alias_promotion_resolves_triggers_and_pins_replays \
  tests.test_cli.CliTests.test_promote_command_assigns_alias_and_trigger_resolves_it \
  tests.test_trigger_docs \
  -v
```

Loop 69 makes version rollout practical without mutating Workflow DSL
artifacts or expanding the single-tenant service boundary. Current maturity
remains Self-hosted Beta until the remaining Production Baseline evidence is
explicitly completed and reviewed.

### Loop 70: Published Artifact Integrity Verification

**Status:** Complete.

**Prior basis:** Publication stored a canonical checksum in the control-plane
registry and backup verification checked it, but ordinary artifact reads did
not recheck that value. A local file replacement could therefore be consumed
by inspection, execution, trigger validation, or alias promotion before an
operator noticed the mismatch.

**Outcome:** `get_workflow()` now verifies every published JSON artifact against
the registry checksum and returns fixed redacted failures for missing,
unreadable, malformed, checksum-less, or modified artifacts. Version
promotion verifies the target before alias metadata changes. Trigger, webhook,
schedule, and exact-version execution paths reuse the same guard, so a failed
check happens before input validation, idempotency claims, run creation, audit
emission, or alias mutation.

**Evidence:** [`docs/published-artifact-integrity.md`](docs/published-artifact-integrity.md)
defines the failure and operator-response contract. Control-plane tests cover
tampered reads, runs, keyed SQLite triggers, and promotion side-effect
suppression; the existing backup/restore and JSON/SQLite compatibility suite
remains green.

**Safety boundary:** This is a local checksum guard, not a digital signature,
remote attestation, automatic repair mechanism, or protection against an
operator who can rewrite both the artifact and its control database.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_tampered_published_artifact_is_rejected_before_execution \
  tests.test_control_plane.ControlPlaneTests.test_tampered_published_artifact_cannot_be_promoted \
  -v
```

Loop 70 closes the published-artifact read gap without changing Workflow DSL
`0.1.0`, artifact layout, or the single-tenant service boundary. Current
maturity remains Self-hosted Beta until remaining Production Baseline evidence
is explicitly completed and reviewed.

### Loop 71: Reviewable Workflow Releases

**Status:** Complete.

**Prior basis:** Immutable versions and stable aliases made releases safe to
  execute, but operators could review only coarse node/edge counts and a stale
  promotion command could overwrite an alias moved by another operator.

**Outcome:** `workflow-diff` compares two exact published versions after
  integrity verification and emits the version records, changed sections, and
  bounded node/edge identifiers without workflow values. `promote` accepts an
  optional `--expected-current-version` compare-and-swap precondition; a stale,
  missing, or ambiguous alias target fails before registry or audit mutation.

**Evidence:** [`docs/workflow-releases.md`](docs/workflow-releases.md) and
  [`schemas/workflow-diff-0.1.0.schema.json`](schemas/workflow-diff-0.1.0.schema.json)
  define the machine-readable review contract. Control-plane and CLI tests
  cover structural redaction, checksum-guarded reads, successful CAS
  promotion, stale-precondition rejection, and alias preservation.

**Safety boundary:** This is a local operator review aid and optimistic
  concurrency guard. It is not semantic risk analysis, an approval policy,
  canary/rollback controller, signature, or multi-tenant release service.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_workflow_diff_is_structural_and_does_not_expose_node_values \
  tests.test_control_plane.ControlPlaneTests.test_promotion_expected_version_precondition_is_compare_and_swap \
  tests.test_cli.CliTests.test_workflow_diff_and_expected_promotion_version_are_safe_cli_contracts \
  -v
```

Loop 71 closes the release-review race without changing Workflow DSL `0.1.0`
or the single-tenant service boundary. Current maturity remains Self-hosted
Beta until remaining Production Baseline evidence is explicitly completed and
reviewed.

### Loop 72: Atomic Workflow Alias Promotion

**Status:** Complete.

**Prior basis:** Loop 71 added an exact expected-version check, but SQLite
  promotion still read the registry and wrote the full index in separate
  operations. Two concurrent operators could both pass the check and let the
  stale writer replace the newer alias target.

**Outcome:** SQLite-backed `promote` now performs the compare-and-swap check,
  alias mutation, and `workflow_promoted` audit append inside one
  `BEGIN IMMEDIATE` transaction. Exactly one of two concurrent promotions that
  observed the same expected target can commit; the losing operation returns
  the existing fixed precondition error without changing the registry or audit
  chain.

**Evidence:** The implementation plan at
[`docs/superpowers/plans/2026-08-13-atomic-workflow-alias-promotion.md`](docs/superpowers/plans/2026-08-13-atomic-workflow-alias-promotion.md)
and [`docs/workflow-releases.md`](docs/workflow-releases.md) define
  the SQLite transaction boundary and keeps JSON explicitly in local-evaluation
  scope. Control-plane tests run two concurrent SQLite operators, assert one
  success and one stale-precondition failure, verify the single winning alias,
  and verify the audit chain remains valid.

**Safety boundary:** This is one local SQLite transaction for one
  single-tenant control plane. It does not add distributed locks, JSON
  cross-process coordination, release approvals, canaries, rollback, or
  exactly-once provider effects.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_promotion_cas_is_atomic_across_concurrent_operators \
  -v
```

Loop 72 closes the SQLite stale-writer gap without changing Workflow DSL
`0.1.0` or the single-tenant service boundary. Current maturity remains
Self-hosted Beta until remaining Production Baseline evidence is explicitly
completed and reviewed.

### Loop 73: Atomic Workflow Registry Mutations

**Status:** Complete.

**Prior basis:** SQLite alias promotion was transactional, but publication and
  deprecation still used full-index replacement and separate audit writes. A
  concurrent publication could erase another new version, duplicate a
  same-version audit, or leave registry and audit state at different commit
  points.

**Outcome:** SQLite publication inserts one immutable version record and its
  `workflow_published` audit row in one `BEGIN IMMEDIATE` transaction.
  Same-version matching retries are idempotent, different content fails closed,
  and deprecation updates only its one record while committing its audit row in
  the same transaction. Artifact creation uses an exclusive immutable link so
  concurrent writers cannot replace the published bytes.

**Evidence:** The implementation plan at
[`docs/superpowers/plans/2026-08-13-atomic-workflow-publication.md`](docs/superpowers/plans/2026-08-13-atomic-workflow-publication.md)
and [`docs/workflow-releases.md`](docs/workflow-releases.md) define the
transaction and retry boundaries. Control-plane tests cover concurrent
different-version publication, same-version idempotency, immutable-content
conflict, publication/deprecation interleaving, and rollback when audit append
fails.

**Safety boundary:** This is one local SQLite registry transaction for one
single-tenant control plane. It does not add distributed coordination, JSON
cross-process guarantees, signatures, approvals, canaries, or exactly-once
provider effects.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_concurrent_publication_preserves_each_version_and_audit \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_concurrent_same_version_publication_is_idempotent \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_publication_rolls_back_registry_when_audit_append_fails \
  -v
```

Loop 73 closes the SQLite registry lost-update gap without changing Workflow
DSL `0.1.0` or the single-tenant service boundary. Current maturity remains
Self-hosted Beta until remaining Production Baseline evidence is explicitly
completed and reviewed.

### Loop 74: Workflow Artifact Consistency

**Status:** Complete.

**Prior basis:** Loop 73 made SQLite registry and audit mutations atomic, but
the filesystem artifact still lived outside the database transaction. A failed
publication could leave an unregistered file, and a crash could leave an
operator without a bounded way to distinguish missing, modified, unsafe, or
orphaned artifacts.

**Outcome:** `workflow-artifacts` reports bounded, value-free registry/file
consistency for JSON and SQLite state. It detects missing, unsafe, invalid,
oversized, checksum-mismatched, and orphaned files. SQLite publication
rechecks the artifact inside its write transaction and removes a newly-created
matching file after a known failure only while its registry key remains absent.

**Evidence:** [`docs/workflow-artifacts.md`](docs/workflow-artifacts.md) and
[`docs/superpowers/plans/2026-08-13-workflow-artifact-consistency.md`](docs/superpowers/plans/2026-08-13-workflow-artifact-consistency.md)
define the report schema, 2 MiB read bound, 256-issue output bound, cleanup
guard, and manual repair boundary. Control-plane, CLI, schema, package, and
documentation tests cover clean state, redacted issue reporting, orphan and
checksum detection, audit-failure cleanup, and retry success.

**Safety boundary:** This is local diagnosis and known-failure cleanup for one
self-hosted single-tenant control plane. It does not repair a registry,
garbage-collect historical artifacts, create a distributed filesystem
transaction, sign artifacts, or add JSON cross-process coordination.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_workflow_artifact_report_is_bounded_and_finds_registry_and_orphan_gaps \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_publication_rolls_back_registry_when_audit_append_fails \
  tests.test_cli.CliTests.test_workflow_artifacts_command_reports_bounded_consistency_without_values \
  -v
```

### Loop 75: Run Audit Consistency

**Status:** Complete.

**Prior basis:** Durable run state and control-plane audit evidence live in
separate SQLite databases. A process stop after run-state persistence could
leave a partial lifecycle trail, and the prior multi-call emission could make
one failed append visible while later events were absent.

**Outcome:** Lifecycle and runtime audit for one control-plane action now emits
as one JSON append or one SQLite transaction. `audit-consistency` compares
bounded expected event counts derived from durable run state with observed
control audit counts and reports missing, duplicate, or unexpected event types
without workflow or business values.

**Evidence:** [`docs/run-audit-consistency.md`](docs/run-audit-consistency.md)
and [`schemas/run-audit-report-0.1.0.schema.json`](schemas/run-audit-report-0.1.0.schema.json)
define the report, 256-run/64-type bounds, and explicit cross-database
diagnostic boundary. Control-plane, CLI, schema, documentation, package, and
full-suite tests cover all-or-nothing audit emission, missing/duplicate
diagnostics, waiting/resume continuity, and redaction.

**Safety boundary:** This closes partial audit emission within one control
store transaction. It does not make the two SQLite databases atomic, repair or
rewrite audit history, replay connectors, add signatures, or claim exactly-once
provider effects.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_published_run_audit_batch_is_all_or_nothing \
  tests.test_control_plane.ControlPlaneTests.test_run_audit_consistency_report_detects_missing_and_duplicate_events \
  tests.test_control_plane.ControlPlaneTests.test_run_audit_consistency_report_is_clean_for_waiting_and_resumed_run \
  tests.test_cli.CliTests.test_audit_consistency_command_reports_run_evidence_without_values \
  -v
```

Loop 75 closes the partial control-audit emission gap while keeping the
cross-database recovery boundary explicit. Current maturity remains
Self-hosted Beta until the remaining Production Baseline evidence is selected
and reviewed.

### Loop 76: Remote Run Audit Consistency

**Status:** Complete.

**Prior basis:** Loop 75 made the diagnostic available locally, but remote
self-hosted operators still had to obtain shell access to the service state
directory or assemble evidence through several separate endpoints.

**Outcome:** The authenticated service now exposes
`GET /api/v1/audit-consistency` and the installed
`service-audit-consistency` client. Both reuse the exact bounded
`skill2workflow-run-audit-report-0.1.0` contract. The route is read-only,
available before readiness when auth and SQLite state are readable, and does
not append audit state, acquire the scheduler lease, or call connectors.

**Evidence:** [`docs/remote-audit-consistency.md`](docs/remote-audit-consistency.md)
defines the request, fixed error, authentication, 64 KiB bound, and client
origin/redirect/schema checks. Service, client, CLI, telemetry, package, docs,
and full-suite tests prove authenticated access, zero-write behavior, redaction,
oversize rejection, and exact response validation.

**Safety boundary:** This is a remote read path only. It does not repair audit
history, make the two SQLite databases atomic, provide remote replication, or
claim exactly-once provider effects.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_audit_consistency_is_authenticated_bounded_and_read_only \
  tests.test_service.RuntimeServiceTests.test_audit_consistency_is_available_before_readiness \
  tests.test_service.RuntimeServiceTests.test_audit_consistency_rejects_oversized_projection_without_disclosure \
  tests.test_service_client.ServiceClientTests.test_audit_consistency_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_audit_consistency_command_prints_report \
  -v
```

### Loop 77: Targeted Remote Run Audit Inspection

**Status:** Complete.

**Prior basis:** The Loop 76 remote report was bounded to 256 runs. That is
safe for response size, but an operator could not inspect a known older run
without shell access when the global report was truncated.

**Outcome:** The authenticated audit route now accepts a fixed
`/api/v1/audit-consistency/{run_id}` form. The installed
`service-audit-consistency --run-id` command validates the same safe run
identifier grammar and exact `skill2workflow-run-audit-report-0.1.0` response.
Targeted reports contain one run and remain bounded, redacted, zero-write, and
available before readiness when auth and SQLite state are readable.

**Evidence:** [`docs/remote-audit-consistency.md`](docs/remote-audit-consistency.md)
defines both route forms, target validation, fixed errors, and operator usage.
Service, client, CLI, documentation, full-suite, and wheel tests prove exact
path construction, safe rejection before network access, targeted report
selection, and compatibility with the unscoped endpoint.

**Safety boundary:** This does not expose arbitrary paths, bypass authentication,
expand the report schema, repair audit history, or claim exactly-once provider
effects.

The repeatable targeted evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_audit_consistency_can_target_one_run_beyond_the_global_window \
  tests.test_service_client.ServiceClientTests.test_audit_consistency_can_target_one_safe_run_id \
  tests.test_service_client.ServiceClientTests.test_audit_consistency_rejects_unsafe_target_before_network_access \
  tests.test_cli.CliTests.test_service_audit_consistency_command_accepts_one_run_id \
  -v
```

Loop 77 closes the global-window operator gap while keeping the remote audit
surface read-only and value-free. Current maturity remains Self-hosted Beta
until the remaining Production Baseline evidence is explicitly completed and
reviewed.

### Loop 78: Remote Recurring-Schedule Inventory

**Status:** Complete.

**Prior basis:** Durable recurring schedules were available to the local
service and CLI, but a remote operator could not inspect next-run timing,
enabled state, missed-run policy, or compact last-run metadata without shell
access to the service host.

**Outcome:** The authenticated service now exposes
`GET /api/v1/recurring-schedules`, and the installed
`service-recurring-schedules` client validates the fixed
`skill2workflow-recurring-schedule-list-0.1.0` contract. The report is bounded
to 100 definitions and 64 KiB, excludes trigger input and scheduler-owner
identities, remains available before readiness, and performs no schedule or
lease mutation.

**Evidence:** [`docs/remote-schedule-inventory.md`](docs/remote-schedule-inventory.md)
defines the route, schema, redaction, fixed errors, and operator sequence.
Dashboard, service, client, CLI, telemetry, schema, package, documentation,
and full-suite tests prove exact path/auth handling, response bounds, schedule
state visibility, and compatibility with the existing support-bundle contract.

**Safety boundary:** This does not enable or disable schedules, claim or
dispatch occurrences, expose trigger input or credentials, add filtering or
pagination, or claim exactly-once provider effects.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_recurring_schedule_list_is_bounded_and_excludes_trigger_input \
  tests.test_service.RuntimeServiceTests.test_recurring_schedule_list_is_authenticated_redacted_and_available_before_readiness \
  tests.test_service_client.ServiceClientTests.test_recurring_schedule_list_uses_authenticated_get_and_validates_contract \
  tests.test_service_client.ServiceClientTests.test_recurring_schedule_list_rejects_oversized_response \
  tests.test_cli.CliTests.test_service_recurring_schedules_command_prints_redacted_inventory \
  -v
```

Loop 78 closes the remote scheduling visibility gap while keeping scheduling
authority local and read-only. Loop 79 adds a narrowly scoped remote control
surface for pausing and resuming schedules, with dispatcher-safe serialization,
idempotent responses, and bounded audit evidence. Current maturity remains
Self-hosted Beta until the remaining Production Baseline evidence is explicitly
completed and reviewed.

### Loop 79: Protected Remote Recurring-Schedule Actions

**Status:** Complete.

**Prior basis:** Loop 78 let remote operators see durable schedule state, but a
faulty recurring schedule still required shell access to pause or resume.

**Outcome:** The authenticated service now exposes exact empty-body `POST`
actions at `/api/v1/recurring-schedules/{schedule_id}/enable` and `/disable`.
The installed `service-schedule-enable` and `service-schedule-disable` clients
validate the fixed `skill2workflow-recurring-schedule-action-0.1.0` contract.
Actions require readiness, use the existing `BEGIN IMMEDIATE` scheduler
transaction so they serialize with dispatcher claims, return `changed: false`
for safe retries, and append bounded ingress and mutation audit evidence.

**Evidence:** [`docs/remote-schedule-actions.md`](docs/remote-schedule-actions.md)
defines the route, body, identifier grammar, fixed errors, redaction, and
cross-database audit boundary. Store, control-plane, service, client, CLI,
telemetry, schema, package, documentation, and full-suite tests cover auth,
body rejection, unknown IDs, idempotence, audit evidence, and support-bundle
compatibility.

**Safety boundary:** This does not claim exactly-once provider effects, expose
trigger input or credentials, take scheduler lease ownership, dispatch a run,
provide RBAC, or provide atomic transactions across the control and scheduler
SQLite databases.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_set_enabled_with_result_is_idempotent_and_serialized \
  tests.test_control_plane.ControlPlaneTests.test_recurring_schedule_change_audit_is_bounded_and_allowlisted \
  tests.test_service.RuntimeServiceTests.test_recurring_schedule_action_is_authenticated_idempotent_and_audited \
  tests.test_service_client.ServiceClientTests.test_recurring_schedule_state_posts_authenticated_empty_object_and_validates_contract \
  tests.test_cli.CliTests.test_service_schedule_state_command_prints_action \
  -v
```

### Loop 80: Remote Recurring-Schedule Dispatch Diagnostics

**Status:** Complete.

**Prior basis:** Loop 79 gave remote operators safe schedule state actions, but
dispatch failures and `uncertain` recovery evidence still required shell access
to the service host.

**Outcome:** The authenticated service now exposes global and schedule-targeted
read routes for a fixed, redacted dispatch projection. The installed
`service-recurring-dispatches` client validates the
`skill2workflow-recurring-schedule-dispatch-list-0.1.0` schema, with a 100-item
SQLite query bound and 64 KiB response bound. Scheduler owner, lease, trigger
input, and raw record values remain private.

**Evidence:** [`docs/remote-schedule-dispatches.md`](docs/remote-schedule-dispatches.md)
defines the routes, fixed errors, redaction, and `uncertain` semantics. Store,
dashboard, service, client, CLI, telemetry, schema, package, documentation,
and full-suite tests cover bounded global/targeted reads, authentication,
response validation, and support-bundle compatibility.

**Safety boundary:** This does not claim replay, provider reconciliation,
exactly-once execution, schedule mutation, lease ownership, RBAC, or bulk
export.

The repeatable evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_recurring_dispatch_list_is_bounded_and_excludes_lease_or_input_values \
  tests.test_service.RuntimeServiceTests.test_recurring_schedule_dispatch_list_is_authenticated_bounded_and_redacted \
  tests.test_service_client.ServiceClientTests.test_recurring_dispatch_list_uses_authenticated_global_and_targeted_paths \
  tests.test_cli.CliTests.test_service_recurring_dispatches_command_supports_schedule_filter \
  -v
```

### Loop 81: Remote Workflow Artifact Consistency

**Status:** Complete.

**Prior basis:** Loop 80 let remote operators inspect dispatch outcomes, but
published workflow files could still be missing, orphaned, invalid, or
checksum-mismatched without shell access to the service host.

**Outcome:** The authenticated service now exposes `GET
/api/v1/workflow-artifacts`, and the installed `service-workflow-artifacts`
client reuses the fixed `skill2workflow-workflow-artifact-report-0.1.0`
value-free contract. The remote projection returns at most 64 issue records and
64 KiB, preserves full aggregate counts, and never repairs state.

**Evidence:** [`docs/remote-workflow-artifacts.md`](docs/remote-workflow-artifacts.md)
defines the route, schema, redaction, fixed errors, and operator sequence.
Dashboard, service, client, CLI, telemetry, package, documentation, and
full-suite tests cover authentication, issue-window bounds, content redaction,
response validation, and support-bundle compatibility.

**Safety boundary:** This does not publish, delete, repair, rewrite checksums,
upload artifacts, add RBAC, or claim cross-database atomicity.

The repeatable evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_remote_workflow_artifact_report_is_bounded_and_reuses_fixed_contract \
  tests.test_service.RuntimeServiceTests.test_workflow_artifact_report_is_authenticated_bounded_and_value_free \
  tests.test_service_client.ServiceClientTests.test_workflow_artifact_report_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_workflow_artifacts_command_prints_report \
  -v
```

### Loop 82: Remote Backup Readiness

**Status:** Complete.

**Prior basis:** Loop 81 let remote operators inspect workflow artifact
consistency, but the existing offline SQLite backup still required a host-side
stop decision without a remote view of the state layout or active scheduler
lease.

**Outcome:** The authenticated service now exposes `GET
/api/v1/backup-readiness`, and the installed `service-backup-readiness` client
returns the fixed `skill2workflow-backup-readiness-0.1.0` report. The report is
read-only, bounded to 16 KiB, readiness-independent, and exposes only layout,
artifact-count, scheduler-lease, and fixed blocking-reason fields.

**Evidence:** [`docs/remote-backup-readiness.md`](docs/remote-backup-readiness.md)
defines the route, schema, redaction, fixed errors, and safe stop-then-backup
sequence. Backup, service, client, CLI, telemetry, package, schema,
documentation, and full-suite tests cover authentication, active-lease
blocking, response validation, and support-bundle compatibility.

**Safety boundary:** This does not create, upload, encrypt, restore, or retain
backups remotely; stop the service; mutate scheduler state; expose paths or
lease identities; or claim a later backup cannot fail after the preflight.

The repeatable evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_backup_readiness_is_authenticated_and_reports_active_lease \
  tests.test_service_client.ServiceClientTests.test_backup_readiness_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_backup_readiness_command_prints_report \
  -v
```

### Loop 83: Remote Audit Integrity

**Status:** Complete.

**Prior basis:** Loop 82 let remote operators confirm the state boundary and
scheduler lease before a host-side backup, but audit-chain tampering still
required shell access to run the local `audit-verify` command.

**Outcome:** The authenticated service now exposes `GET
/api/v1/audit-integrity`, and the installed `service-audit-integrity` client
reuses the fixed `skill2workflow-audit-integrity-0.1.0` payload-free result.
Valid, invalid, and legacy-unsealed states are reported within a 16 KiB bound;
event payloads and identifiers never cross the service boundary.

**Evidence:** [`docs/remote-audit-integrity.md`](docs/remote-audit-integrity.md)
defines the route, schema reuse, fixed errors, redaction, and safe incident
sequence. Service, client, CLI, telemetry, package, documentation, and
full-suite tests cover authentication, body rejection, invalid-state redaction,
response validation, and support-bundle compatibility.

**Safety boundary:** This does not repair or rewrite audit rows, export event
payloads, sign the chain, manage keys, create backups, restore state, or claim
operator identity or hosted compliance.

The repeatable evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_audit_integrity_is_authenticated_payload_free_and_read_only \
  tests.test_service_client.ServiceClientTests.test_audit_integrity_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_audit_integrity_command_prints_report \
  -v
```

### Loop 84: Remote Runtime Info

**Status:** Complete.

**Prior basis:** Loop 83 let remote operators verify the audit chain without
shell access, but upgrade and rollback triage still lacked a safe way to
identify the running package, service contract, Workflow DSL line, and state
layout from the service boundary.

**Outcome:** The authenticated service now exposes `GET
/api/v1/runtime-info`, and the installed `service-runtime-info` client returns
the fixed `skill2workflow-runtime-info-0.1.0` report. It includes package and
compatibility metadata plus fixed lifecycle, readiness, storage-layout, and
scheduler-lease fields while omitting paths, configuration, and business
values.

**Evidence:** [`docs/remote-runtime-info.md`](docs/remote-runtime-info.md)
defines the route, schema, redaction, fixed errors, and safe upgrade sequence.
Service, client, CLI, telemetry, package, schema, documentation, and full-suite
tests cover authentication, body rejection, readiness-independent collection,
response validation, and support-bundle compatibility.

**Safety boundary:** This does not upgrade, migrate, roll back, shut down, or
reconfigure the service; expose host inventory or paths; or claim that a future
binary is compatible solely from this point-in-time report.

The repeatable evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_runtime_info_is_authenticated_bounded_and_reports_compatibility \
  tests.test_service_client.ServiceClientTests.test_runtime_info_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_runtime_info_command_prints_report \
  -v
```

### Loop 85: Protected Remote Workflow Triggering

**Status:** Complete.

**Prior basis:** Loop 84 made the remote service identity observable, but an
installed operator still had to hand-build a webhook URL and JSON request to
start a published workflow. That made retry safety, input bounds, and response
handling easy to implement inconsistently across integrations.

**Outcome:** The installed `service-trigger` client now wraps the existing
authenticated webhook boundary. It requires a stable idempotency key, accepts
one bounded non-secret JSON input object, safely quotes workflow path
components, and validates the compact trigger response before printing it.
Aliases such as `production` remain supported and the server's resolved
immutable version is returned.

**Evidence:** [`docs/remote-trigger.md`](docs/remote-trigger.md) defines the
request, retry, error, and input boundaries. Client and CLI tests cover the
Bearer header, exact path/body, required retry key, unsafe-path rejection, and
fixed response. The existing real-process service boundary continues to prove
the authenticated webhook, SQLite idempotency, and restart continuity.

**Safety boundary:** This adds no new execution authority or provider
semantics. It does not accept secrets, bypass published-workflow checks, retry
unresolved external effects, expose raw input values, or claim exactly-once
execution.

The repeatable evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service_client.ServiceClientTests.test_service_trigger_posts_bounded_idempotent_envelope \
  tests.test_service_client.ServiceClientTests.test_service_trigger_requires_idempotency_and_rejects_unsafe_path_before_network \
  tests.test_service_client.ServiceClientTests.test_service_trigger_rejects_oversized_complete_body_before_network \
  tests.test_cli.CliTests.test_service_trigger_command_loads_input_and_requires_retry_key \
  -v
```

### Loop 86: Protected Remote Workflow Publication

**Status:** Complete.

**Prior basis:** Loop 85 made starting an already-published workflow safe from
an installed client, but CI/CD operators still had to copy a Workflow DSL file
onto the service host and invoke the local publisher. That left publication
automation outside the authenticated service boundary.

**Outcome:** The installed `service-workflow-publish` client now submits one
bounded Workflow DSL document through `POST /api/v1/workflow-releases`. The
service requires readiness and the active SQLite scheduler lease, reuses the
immutable publication transaction, and returns only a fixed redacted record
with the workflow id, version, status, and checksum. Replays of identical
content are safe; changed content under an existing version is rejected.

**Evidence:** [`docs/remote-workflow-release.md`](docs/remote-workflow-release.md)
defines the exact envelope, 1 MiB request bound, fixed response, error classes,
and non-goals. Service, client, CLI, telemetry, package, documentation, and
real-process tests cover authentication, immutable replay/conflict behavior,
response validation, and artifact-path redaction.

**Safety boundary:** This loop does not promote aliases, trigger runs,
deprecate versions, upload artifacts elsewhere, accept credentials, or claim
remote release orchestration, signatures, or exactly-once provider effects.

The repeatable evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_publication_is_authenticated_immutable_and_redacted \
  tests.test_service_client.ServiceClientTests.test_service_workflow_publish_uses_fixed_contract \
  tests.test_cli.CliTests.test_service_workflow_publish_command_loads_workflow \
  -v
```

### Loop 87: Protected Remote Workflow Promotion

**Status:** Complete.

**Prior basis:** Loop 86 allowed an installed CI/CD client to publish an
immutable version, but making that version reachable through a stable alias
still required shell access to the service host. That left the remote release
path incomplete and made stale operator actions harder to guard consistently.

**Outcome:** The installed `service-workflow-promote` client now moves one
published version through `POST /api/v1/workflow-promotions`. The service
requires readiness and the active SQLite scheduler lease, reuses the existing
transactional alias mutation, supports an optional expected-current-version
CAS guard, and returns only a fixed redacted summary. Repeating a no-op
promotion is idempotent and does not append duplicate promotion evidence.

**Evidence:** [`docs/remote-workflow-promotion.md`](docs/remote-workflow-promotion.md)
defines the exact envelope, safe identifier grammar, 1 MiB request bound, fixed
response, error classes, and non-goals. Service, client, CLI, telemetry,
package, documentation, control-plane, and real-process tests cover
authentication, stale CAS rejection, alias uniqueness, idempotent replay,
response validation, and artifact-path redaction.

**Safety boundary:** This loop does not publish, deprecate, trigger, roll back,
upload artifacts, issue credentials, perform hosted release orchestration, or
claim signatures or exactly-once provider effects.

The repeatable evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_promotion_is_authenticated_cas_and_redacted \
  tests.test_service_client.ServiceClientTests.test_service_workflow_promote_uses_fixed_contract \
  tests.test_cli.CliTests.test_service_workflow_promote_command_uses_cas_options \
  -v
```

### Loop 88: Protected Remote Workflow Diff

**Status:** Complete.

**Prior basis:** Loop 87 completed remote publication and CAS promotion, but a
remote operator still could not review the structural change before choosing
the promotion target. That pushed CI/CD review back onto service-host shell
access and weakened the publish → review → promote path.

**Outcome:** The installed `service-workflow-diff` client now fetches two exact
published versions through `GET /api/v1/workflow-diffs/{workflow_id}/{from_version}/{to_version}`.
The service reuses the existing value-free structural diff, requires Bearer
authentication, validates an empty body, and returns a bounded fixed schema
without acquiring the scheduler lease or mutating state.

**Evidence:** [`docs/remote-workflow-diff.md`](docs/remote-workflow-diff.md)
defines the route, 64 KiB response bound, redaction rules, and operator
sequence. Service, client, CLI, telemetry, package, documentation, and
real-process tests cover authentication, body rejection, safe URL quoting,
schema validation, missing-version errors, value/path redaction, and zero-write
behavior.

**Safety boundary:** This loop does not publish, promote, trigger, approve,
deprecate, repair, or semantically assess business risk. Operators still use
the CAS-protected promotion command after reviewing the diff.

The repeatable evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_diff_is_authenticated_value_free_and_read_only \
  tests.test_service_client.ServiceClientTests.test_service_workflow_diff_uses_fixed_redacted_contract \
  tests.test_cli.CliTests.test_service_workflow_diff_command_uses_version_options \
  -v
```

### Loop 89: Protected Local Ingress-Token Rotation

**Status:** Complete.

**Prior basis:** The service already reread its owner-only Bearer token on each
request, but operators had to replace the file by hand. That made rotation
easy to perform non-atomically and left no packaged, redacted verification
path for a running service.

**Outcome:** The installed `service-token-rotate` command validates the existing
file, generates a new token locally, rechecks file identity, and atomically
replaces the owner-only file. The service accepts the new token immediately
and rejects the old one without a restart. The fixed result contains only the
schema version, status, and token-file path.

**Evidence:** [`docs/service-token-rotation.md`](docs/service-token-rotation.md)
defines the local-only contract, failure boundary, and consumer handoff. Unit,
service, CLI, package, documentation, and wheel tests cover redaction, weak or
unsafe files, atomic replacement, identity races, old/new authentication, and
installed command behavior.

**Safety boundary:** This loop does not expose rotation remotely, return the
credential, manage multiple active tokens, provide OAuth/RBAC, or coordinate
external secret stores and service-manager reloads.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service_bootstrap.ServiceBootstrapTests.test_rotate_replaces_valid_token_atomically_without_returning_secret \
  tests.test_service_bootstrap.ServiceBootstrapTests.test_rotate_rejects_unsafe_or_invalid_inputs_without_mutating_old_token \
  tests.test_service.RuntimeServiceTests.test_business_routes_require_rotatable_bearer_auth_and_write_compact_audit \
  -v
```

### Loop 90: Protected Remote Workflow Deprecation

**Status:** Complete.

**Prior basis:** Remote publication, promotion, and structural diff review were
available, but an installed operator still had to use shell access to retire a
published version. That left the remote lifecycle incomplete and encouraged
unsafe direct registry edits.

**Outcome:** The authenticated `POST /api/v1/workflow-deprecations` route and
installed `service-workflow-deprecate` client retire one published version
through the existing control-plane transaction. Deprecation removes stable
aliases, preserves the immutable artifact, appends one audit event, and returns
only a fixed checksum summary. Replays are idempotent and do not duplicate the
audit event.

**Evidence:** [`docs/remote-workflow-deprecation.md`](docs/remote-workflow-deprecation.md)
defines the exact bounded request/response, readiness and lease requirements,
redaction, error boundary, and no-delete semantics. Client, CLI, telemetry,
documentation, package, and real-process service tests cover denied and
malformed requests, alias removal, idempotent replay, immutable artifact
preservation, and one deprecation audit event.

**Safety boundary:** This loop does not delete artifacts, publish or promote a
replacement, trigger or cancel runs, export Workflow content, provide RBAC, or
claim exactly-once external effects. Existing in-flight executions continue
under their durable run state.

The repeatable evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_deprecation_is_authenticated_idempotent_and_redacted \
  tests.test_service_client.ServiceClientTests.test_service_workflow_deprecate_uses_fixed_redacted_contract \
  tests.test_cli.CliTests.test_service_workflow_deprecate_command_uses_version_options \
  -v
```

### Loop 91: Bounded Remote Workflow Inventory

**Status:** Complete.

**Prior basis:** Remote publication, diff, promotion, and deprecation were
available, but a remote operator still needed to know a version identifier from
outside the service before beginning that lifecycle sequence. The existing
control snapshot was broader than this boundary and could include unrelated
operator data.

**Outcome:** The authenticated `GET /api/v1/workflows` route and installed
`service-workflows` client expose at most 100 redacted version records with
fixed lifecycle counts, aliases, and checksums. SQLite reads use a bounded
query; JSON fallback remains bounded at the projection boundary. The endpoint
is read-only, readiness-independent, does not acquire the scheduler lease, and
does not append audit state.

**Evidence:** [`docs/remote-workflow-inventory.md`](docs/remote-workflow-inventory.md)
defines the exact schema, 64 KiB response cap, no-body contract, redaction, and
operator sequence. Client, CLI, telemetry, schema, documentation, package, and
real-process tests cover authentication, body rejection, window arithmetic,
status counts, checksum validation, alias projection, and zero-write behavior.

**Safety boundary:** This loop does not export Workflow DSL, names, artifact
paths, timestamps, audit payloads, credentials, or provider data. It does not
publish, promote, deprecate, trigger, repair, delete, or semantically assess a
workflow.

The repeatable evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_inventory_is_authenticated_bounded_and_read_only \
  tests.test_service_client.ServiceClientTests.test_service_workflow_inventory_uses_fixed_redacted_contract \
  tests.test_cli.CliTests.test_service_workflows_command_prints_inventory \
  -v
```

### Loop 92: Policy-bound Remote Retention Readiness

**Status:** Complete.

**Prior basis:** The local copy-on-write retention flow already protected the
source state and required a stopped service, but remote operators had no safe
way to bind an approved policy to a preflight or distinguish an active service
from a quiesced plan without shell access.

**Outcome:** The authenticated `POST /api/v1/retention-readiness` route and
installed `service-retention-readiness` client reuse the exact local policy
normalization. An active scheduler lease returns `blocked` with null counts;
only a current-layout, quiesced read-only inspection returns aggregate
eligibility and preserved-work counts. The route never applies retention,
copies databases, acquires the lease, or appends audit state.

**Evidence:** [`docs/remote-retention-readiness.md`](docs/remote-retention-readiness.md)
defines the fixed policy-bound schema, digest, 64 KiB request/16 KiB response
bounds, authentication/body/error contract, redaction boundary, and safe
operator sequence. Retention, service, client, CLI, telemetry, schema,
documentation, package, and full-suite tests cover both quiesced counts and
active-lease blocking.

**Safety boundary:** This loop does not delete, copy, vacuum, upload, restore,
shutdown, infer legal holds, expose paths or payloads, or claim that a plan
remains valid after state changes. The local plan/apply commands remain the
authoritative stopped-state operation.

The repeatable evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_retention.StateRetentionTests.test_remote_readiness_returns_counts_only_when_state_is_quiesced \
  tests.test_service.RuntimeServiceTests.test_retention_readiness_is_authenticated_bounded_and_blocks_live_service \
  tests.test_service_client.ServiceClientTests.test_retention_readiness_posts_policy_and_validates_fixed_contract \
  tests.test_cli.CliTests.test_service_retention_readiness_command_loads_policy_and_prints_report \
  -v
```

### Loop 93: Remote Operational Readiness

**Status:** Complete.

**Prior basis:** Operators had to call lifecycle, workflow-artifact, audit,
and backup diagnostics separately and manually interpret their relationship.
That encouraged bespoke scripts and broader state exports during deployment or
incident handoff.

**Outcome:** The authenticated `GET /api/v1/operational-readiness` route and
installed `service-operational-readiness` client combine fixed lifecycle,
current-layout, artifact-consistency, audit-chain, and offline-backup statuses
into one bounded value-free report. It explicitly treats an active lease as an
expected offline-backup maintenance note while the running service remains
otherwise ready, and it does not claim an atomic cross-database snapshot.

**Evidence:** [`docs/remote-operational-readiness.md`](docs/remote-operational-readiness.md)
defines the exact schema, redaction, best-effort semantics, 16 KiB bound,
authentication/body/error contract, and operator sequence. Service, client,
CLI, telemetry, schema, documentation, package, and full-suite tests cover
ready, attention, body rejection, and response-bound behavior.

**Safety boundary:** This loop does not drain or stop the service, create or
restore backups, apply retention, repair artifacts or audit state, export raw
logs, expose credentials or paths, or provide hosted monitoring/RBAC.

The repeatable evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_operational_readiness_is_authenticated_aggregate_and_redacted \
  tests.test_service_client.ServiceClientTests.test_operational_readiness_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_operational_readiness_command_prints_report \
  -v
```

### Loop 94: Bounded Request-Body Reads

**Status:** Complete.

**Prior basis:** The service already bounded body size and concurrent handler
count, but a client could advertise a body and then stop sending bytes. The
blocking `read()` held an HTTP handler, consumed admission capacity, and could
delay graceful drain indefinitely.

**Outcome:** The authenticated service and loopback webhook adapter set a fixed
five-second socket deadline for request-body reads. A stalled body receives a
bounded HTTP `408` response with the fixed `request timed out` error, releases
its admission slot, and cannot trigger a workflow from partial input.

**Evidence:** [`docs/service.md`](docs/service.md) and
[`docs/triggers.md`](docs/triggers.md) define the deadline, error, size, and
execution boundaries. Service tests exercise an incomplete authenticated body
against the real threaded server and prove the handler exits without a leaked
thread; the full suite and package/security checks cover the existing routes.

**Safety boundary:** This loop bounds transport reads only. It does not change
the connector execution timeout, workflow deadline, retry policy, request body
limit, proxy/TLS boundary, or provider-side cancellation semantics.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_incomplete_request_body_times_out_with_bounded_error \
  -v
```

### Loop 95: Deployment Service Probe

**Status:** Complete.

**Prior basis:** The service already exposed stable `/healthz` and `/readyz`
endpoints, but deployment automation still had to hand-roll two HTTP calls,
redirect handling, response parsing, and the distinction between a live but
not-ready process and an unavailable process.

**Outcome:** The installed `service-probe` command composes those existing
read-only endpoints into the fixed `skill2workflow-service-probe-0.1.0`
contract. It disables redirects and proxies, uses a five-second timeout and an
8 KiB response bound, never prints server bodies, and maps `ready`, `not_ready`,
and `unavailable` to stable exit codes `0`, `1`, and `2`.

**Evidence:** [`docs/service-probe.md`](docs/service-probe.md) defines the
schema, security boundary, cutover sequence, and verification commands.
Client, CLI, redirect, unsafe-origin, and not-ready tests cover the fixed
contract; the package smoke includes the installed command.

**Safety boundary:** This loop adds no HTTP route, authentication bypass for
business traffic, lifecycle mutation, proxy/TLS management, monitoring
backend, or deployment orchestration. Health and readiness remain the only
unauthenticated requests and must stay behind the existing external network
policy.

The repeatable evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service_client.ServiceClientTests.test_service_probe_returns_fixed_ready_contract_without_credentials \
  tests.test_service_client.ServiceClientTests.test_service_probe_distinguishes_not_ready_from_unavailable \
  tests.test_cli.CliTests.test_service_probe_command_prints_contract_and_maps_ready_exit_code \
  -v
```

### Loop 96: Exact-Length Request-Body Reads

**Status:** Complete.

**Prior basis:** Loop 94 bounded slow request bodies with a socket deadline,
but a client could still advertise a longer `Content-Length`, send a shorter
body, and close the connection. A short read must not be parsed as a complete
request at either the webhook adapter or authenticated service boundary.

**Outcome:** The shared body reader now loops until the exact advertised byte
count arrives. Early EOF returns the fixed HTTP `400` error
`{"error":"request body incomplete"}`; socket stalls retain the fixed HTTP
`408` `request timed out` contract. Neither path reaches workflow parsing,
trigger claims, or connector execution.

**Evidence:** [`docs/service.md`](docs/service.md) and
[`docs/triggers.md`](docs/triggers.md) define exact-length semantics and the
two fixed failure classes. Unit tests cover early EOF directly, and real
threaded webhook/service tests prove bounded responses and no partial trigger.

**Safety boundary:** This loop changes only request-body completeness checks.
It does not expand body limits, add transfer encoding, change workflow or
connector timeouts, or claim protection against external side effects after a
complete request has been accepted.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_webhooks.WebhookTests.test_read_request_body_rejects_early_eof_without_returning_partial_bytes \
  tests.test_service.RuntimeServiceTests.test_early_eof_rejects_partial_body_with_bounded_error \
  -v
```

### Loop 97: Fail-Closed Service Exception Boundary

**Status:** Complete.

**Prior basis:** Individual service handlers translated many expected storage
and validation failures, but an unexpected business-handler exception could
escape the request thread. That left clients without a stable response and
could expose exception details through the default HTTP traceback logger.

**Outcome:** The request dispatcher now converts unexpected handler failures to
the fixed `503 {"error":"service unavailable"}` response. Connection-abort
errors close without a second write, and telemetry/operational event logging
are best-effort after the response path. No exception text, request value, or
credential is serialized.

**Evidence:** [`docs/service.md`](docs/service.md) and
[`docs/security-boundary.md`](docs/security-boundary.md) define the fixed
error and disclosure boundary. A real threaded service test forces an
unexpected business failure and verifies the redacted 503 response; the
existing body, security, and full-suite tests cover regression behavior.

**Safety boundary:** This loop does not retry failed handlers, alter workflow
state, change connector semantics, or claim that a 503 means an external side
effect did not occur. It only makes the HTTP error boundary deterministic and
non-disclosing.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_unexpected_request_failure_returns_fixed_503_without_error_details \
  -v
```

### Loop 98: Lifecycle Event-Logger Isolation

**Status:** Complete.

**Prior basis:** Loop 97 made request telemetry and operational event logging
best-effort after the response path, but lifecycle logging still ran directly
inside service construction, startup, signal-driven drain, and final cleanup.
A closed collector or custom logger exception could therefore abort startup,
strand scheduler threads, raise from a signal callback, or mask shutdown.

**Outcome:** Lifecycle event delivery now catches ordinary logger failures at
the service boundary. The service still transitions through `starting`,
`ready`, `draining`, and `stopped`, and scheduler/listener cleanup remains
deterministic even when every lifecycle log write fails.

**Evidence:** [`docs/observability.md`](docs/observability.md) defines the
best-effort operational-log contract. A threaded lifecycle test forces the
logger to fail for all four states and verifies successful construction,
startup, drain, scheduler cleanup, and final stopped state; the full suite
covers request logging and signal/lifecycle regressions.

**Safety boundary:** This loop does not persist operational logs, retry or
buffer collector writes, alter durable workflow audit state, or claim that a
missing operational event proves a workflow did not run. It isolates only the
optional observer from service control flow.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_lifecycle_logger_failure_cannot_break_startup_or_shutdown \
  -v
```

### Loop 99: Deterministic Service Teardown

**Status:** Complete.

**Prior basis:** Loop 98 isolated lifecycle event logging, but `serve()` still
started the scheduler outside its cleanup boundary and assumed scheduler stop
could not fail. A startup recovery error could leave the listener bound, while
a release error could prevent the service from publishing `stopped`.

**Outcome:** Listener closure and scheduler cleanup now run through nested
`finally` blocks. Scheduler-start failures close the listener before the
original exception is surfaced; cleanup failures still leave the service in
`stopped` and preserve the failure for the caller.

**Evidence:** [`docs/service.md`](docs/service.md) defines the startup and
teardown contract. Thread-free regression tests inject failures into scheduler
start and stop, verify the port can be rebound, and assert the final status;
the existing callback-failure and real-process shutdown tests cover normal
continuity.

**Safety boundary:** This loop does not retry scheduler startup, hide storage
errors, forcefully terminate worker threads, or claim that a failed cleanup
released an external provider lease. It guarantees only local listener/state
cleanup ordering and preserves the original exception.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_scheduler_start_failure_closes_listener_and_marks_stopped \
  tests.test_service.RuntimeServiceTests.test_scheduler_stop_failure_still_closes_listener_and_marks_stopped \
  -v
```

### Loop 100: Production-Boundary CI Gates

**Status:** Complete.

**Prior basis:** The repository already shipped security, observability, and
service restart-continuity smokes, but CI stopped after unit tests, packaging,
and secret scans. A pull request could therefore pass the test suite while
breaking a real process boundary that contributors and release operators rely
on.

**Outcome:** Every supported Python matrix entry now runs the three production
boundary drills: default-deny authentication/credential rotation, real
observability export, and two-cycle SQLite service restart continuity. The same
commands are documented for local reproduction and release preflight.

**Evidence:** `.github/workflows/ci.yml` contains the three required commands;
`tests.test_ci` locks the CI contract. The existing scripts emit fixed,
secret-free evidence and were run successfully against this commit alongside
the full suite and isolated wheel smoke.

**Safety boundary:** This loop does not claim hosted CI is a deployment gate,
replace target-host systemd verification, upload telemetry, or prove external
provider availability. It makes only the existing local production-boundary
evidence mandatory on pull requests and pushes.

The repeatable evidence commands are:

```bash
python3 scripts/security_boundary_smoke.py --work-dir /tmp/skill2workflow-security-ci
python3 scripts/observability_smoke.py --work-dir /tmp/skill2workflow-observability-ci
python3 scripts/service_boundary_smoke.py --work-dir /tmp/skill2workflow-service-boundary-ci
```

### Loop 101: Cross-Database Operator-Action Recovery

**Status:** Complete.

**Prior basis:** Remote resume, cancellation, and recurring schedule actions
commit durable state in one SQLite database and append bounded operator
evidence in another. A process failure in between could return `503` after the
state mutation, leaving an operator unsure whether retrying was safe.

**Outcome:** Resume and cancellation retries now recognize committed run-state
events and append only missing control-plane audit evidence. A retry never
replays a workflow or human-gate decision, while an already reconciled decision
keeps the existing `409` non-waiting contract. Schedule actions retain their
idempotent `changed: false` reconciliation path, and all three boundaries now
document the failure window and recovery procedure.

**Evidence:** Fault-injection tests force the control-audit append to fail after
run-state commit, then prove a same-action retry restores a clean audit
consistency report with exactly one decision projection. Existing schedule
action tests continue to prove one state transition and bounded audit output.

**Safety boundary:** This loop does not add distributed transactions, automatic
HTTP retries, provider compensation, RBAC, or exactly-once external effects.
Operators still inspect provider outcomes and use the fixed audit-consistency
diagnostic when a process may have stopped during an action.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_resume_retry_reconciles_audit_after_run_state_commit \
  tests.test_cancellation.CancellationTests.test_control_plane_retries_cancellation_to_reconcile_audit_after_state_commit \
  tests.test_service.RuntimeServiceTests.test_recurring_schedule_action_is_authenticated_idempotent_and_audited \
  -v
```

### Loop 102: Run-Audit Lifecycle Projection Accuracy

**Status:** Complete.

**Prior basis:** The consistency projection counted a `waiting` or
`interrupted` status in addition to the lifecycle event already persisted in
the run event stream. Healthy paused and recovered runs therefore appeared to
have missing audit evidence.

**Outcome:** Waiting and interrupted lifecycle events are now projected exactly
once. The fixed report schema and read-only semantics remain compatible, while
operator attention is reserved for genuine missing, duplicate, or unexpected
evidence.

**Evidence:** Dedicated control-plane tests cover clean waiting and interrupted
runs alongside existing missing/duplicate detection. The full suite and the
remote report contract continue to validate the unchanged schema.

**Safety boundary:** This loop changes only diagnostic counting. It does not
rewrite audit history, repair state, replay workflows, infer provider outcomes,
or alter human-gate/cancellation/interruption behavior.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_run_audit_consistency_report_is_clean_for_waiting_run \
  tests.test_control_plane.ControlPlaneTests.test_run_audit_consistency_report_is_clean_for_interrupted_run \
  tests.test_control_plane.ControlPlaneTests.test_run_audit_consistency_report_detects_missing_and_duplicate_events \
  -v
```

### Loop 103: Uniform Metrics Request Boundary

**Status:** Complete.

**Prior basis:** The service guide described protected read routes as
zero-body surfaces, but `/metrics` did not validate `Content-Length` or
`Transfer-Encoding` before rendering telemetry. A malformed scraper request
could therefore take a different protocol path from the other bounded read
routes.

**Outcome:** Authenticated `GET /metrics` now reuses the exact request-body
validation contract. Non-empty, malformed, duplicate, oversized, or
transfer-encoded bodies are rejected with the existing bounded `400`/`413`
errors before metrics rendering; valid scrapes and the unauthenticated
response remain unchanged.

**Evidence:** A threaded service regression test proves a body is rejected
without rendering or mutating telemetry state. The observability and service
guides document the zero-body scraper contract, and the full suite plus
production-boundary smokes verify compatibility and redaction.

**Safety boundary:** This loop only hardens the local HTTP request boundary.
It does not add metric labels, retries, proxy behavior, tracing, or remote
telemetry storage.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_metrics_rejects_request_body_before_rendering \
  tests.test_service.RuntimeServiceTests.test_metrics_route_requires_auth_and_exports_only_aggregate_text \
  -v
```

### Loop 104: Startup-Shutdown Race Protection

**Status:** Complete.

**Prior basis:** `SIGINT`/`SIGTERM` can arrive while the scheduler is being
started. The service recorded `draining`, but the normal startup path then
unconditionally published `ready`, invoked the ready callback, and entered the
HTTP loop. That could make a terminating instance appear healthy to a
supervisor or briefly accept traffic after the shutdown request.

**Outcome:** Scheduler startup now checks the lifecycle state before publishing
`ready`. If draining has begun, the service skips the ready callback and HTTP
loop and proceeds through the normal listener/scheduler cleanup path, leaving a
deterministic `stopped` state.

**Evidence:** A regression test injects a shutdown request during scheduler
startup and proves no request loop or ready callback is entered. Existing
startup-failure, lifecycle-logger, service-boundary, and full-suite tests
continue to cover cleanup and restart behavior.

**Safety boundary:** This loop changes only lifecycle sequencing. It does not
forcefully abort connector calls, alter readiness schemas, or add a new
supervisor or signal type.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_shutdown_requested_during_scheduler_start_does_not_restore_ready \
  tests.test_service.RuntimeServiceTests.test_scheduler_start_failure_closes_listener_and_marks_stopped \
  -v
```

### Loop 105: Atomic Lifecycle State Transitions

**Status:** Complete.

**Prior basis:** Loop 104 protected the startup check, but a shutdown request
could still race between that check and publication of `ready`. That left a
narrow path where a draining service could overwrite its state, invoke the
ready callback, and enter the request loop.

**Outcome:** Lifecycle transitions are serialized across the serving thread,
signal handlers, and embedding callers. The `ready`/`draining` decision is
atomic, and lifecycle events remain ordered through the final `stopped` state.

**Evidence:** A deterministic concurrent regression test injects shutdown
during the transition and proves there is no ready callback or request-loop
entry, with the lifecycle sequence `starting → draining → stopped`. Focused,
full-suite, and production-boundary service checks cover the compatibility
contract and cleanup behavior.

**Safety boundary:** This loop only closes the in-process lifecycle race. It
does not forcefully abort connector calls, change readiness schemas, or add a
new supervisor or signal type.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_ready_transition_is_atomic_against_shutdown_request \
  tests.test_service.RuntimeServiceTests.test_shutdown_requested_during_scheduler_start_does_not_restore_ready \
  -v
```

### Loop 106: Atomic Shutdown Admission

**Status:** Complete.

**Prior basis:** Loop 105 made the lifecycle state transition atomic, but a
request arriving after `draining` could still acquire the business-request
semaphore and enter a mutating route before that route's readiness check. That
left shutdown behavior dependent on route-specific timing and could consume a
request body or emit authentication/audit work during drain.

**Outcome:** Lifecycle state and request admission now share one short critical
section. Mutating routes are rejected with a fixed retryable `503` before
authentication, body parsing, or control-plane effects once draining begins;
health, readiness, metrics, and read-only operator diagnostics remain usable.

**Evidence:** A deterministic admission-race regression proves a shutdown
request wins the lifecycle decision, and a threaded webhook test proves the
draining response occurs before authentication, body consumption, or workflow
execution. Existing concurrency-budget and graceful-drain tests preserve the
probe and read-only compatibility boundary.

**Safety boundary:** This loop only controls new in-process HTTP admission. It
does not cancel handlers already admitted, abort outbound connector calls, or
change the scheduler lease, readiness schema, or external TLS boundary.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_request_admission_is_atomic_against_shutdown_request \
  tests.test_service.RuntimeServiceTests.test_draining_rejects_new_mutating_request_before_auth_or_body_side_effects \
  tests.test_service.RuntimeServiceTests.test_business_routes_fail_fast_when_admission_budget_is_exhausted_but_probes_remain_available \
  -v
```

### Loop 107: Atomic Scheduler Dispatch Admission

**Status:** Complete.

**Prior basis:** Loop 106 stopped new HTTP mutations during graceful shutdown,
but the scheduler's recurring-dispatch thread had no matching admission gate.
A timing window could therefore start another scheduled trigger after
`draining` was published and before scheduler cleanup released the lease.

**Outcome:** Scheduler dispatch admission is serialized by a dedicated gate.
Shutdown closes that gate without waiting in a signal handler; one dispatch
already admitted may finish, while later recurring triggers cannot start.

**Evidence:** A deterministic gate-race regression proves a shutdown request
wins over a not-yet-started dispatch, and existing recurring-dispatch,
standby-takeover, failure-release, and service-boundary tests preserve the
lease and uncertain-outcome contracts.

**Safety boundary:** This loop only controls new in-process recurring
dispatches. It does not cancel an active connector, rewrite a claimed
dispatch, alter the scheduler lease schema, or claim exactly-once execution.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_shutdown_closes_scheduler_dispatch_gate_atomically \
  tests.test_service.RuntimeServiceTests.test_service_dispatches_recurring_schedule_and_persists_record \
  tests.test_service.RuntimeServiceTests.test_unexpected_scheduler_failure_releases_lease_for_standby \
  -v
```

### Loop 108: Live In-Flight Request Pressure Metrics

**Status:** Complete.

**Prior basis:** The service already enforced a fixed 16-handler admission
budget and closed new work during graceful drain, but operators could only see
cumulative request counters. There was no safe live signal showing whether
admitted work was still occupying the budget or whether drain progress had
reached zero.

**Outcome:** Authenticated `/metrics` now exports the label-free
`skill2workflow_service_inflight_requests` gauge. It is updated at the same
request-admission boundary as the semaphore, excludes health/readiness probes
and the scrape itself, and is explicitly kept out of support-bundle 0.1.0 so
that the older incident-handoff schema remains stable.

**Evidence:** Telemetry unit coverage proves the gauge is live, route-free,
non-negative, and scrape-excluding. A threaded service regression holds one
authenticated webhook in flight, observes the gauge at `1`, releases it, and
observes `0`; the existing full metrics/authentication and observability smoke
checks remain green.

**Safety boundary:** This is a process-local pressure gauge, not a queue depth,
distributed capacity signal, cancellation mechanism, or external-outcome
claim. Durable run, dispatch, and audit evidence remains authoritative for
recovery decisions.

The focused evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_telemetry.RuntimeTelemetryTests.test_inflight_request_gauge_is_live_route_free_and_excludes_scrape \
  tests.test_service.RuntimeServiceTests.test_metrics_exposes_admitted_inflight_request_pressure \
  -v
```

### Loop 109: Live Scheduler Dispatch Pressure Metrics

**Status:** Complete.

**Prior basis:** Loop 107 atomically stopped new recurring dispatch admission,
and Loop 108 exposed live HTTP handler pressure. Background scheduler work is
outside the HTTP semaphore, so a draining service could still be waiting on an
already-admitted `dispatch_due` call while `/metrics` reported no in-flight
HTTP work.

**Outcome:** Authenticated `/metrics` now exports the label-free
`skill2workflow_scheduler_dispatch_inflight` gauge. The scheduler increments it
only after the dispatch gate and lease checks pass, and decrements it in a
`finally` path after the dispatch call returns. Existing scheduler instances
without telemetry remain supported, and support-bundle 0.1.0 stays unchanged.

**Evidence:** Telemetry coverage proves the gauge is live and route-free. A
threaded scheduler regression holds an admitted dispatch, observes the gauge at
`1`, releases the call, and observes `0`; the shutdown gate regression remains
green. The real observability smoke checks both live gauges and the existing
fixed-label/secret-free evidence.

**Safety boundary:** This is a process-local visibility signal, not a second
lease, queue, cancellation mechanism, or exactly-once claim. It does not admit
new work and does not rewrite a claimed dispatch.

The focused evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_telemetry.RuntimeTelemetryTests.test_scheduler_dispatch_gauge_is_live_and_route_free \
  tests.test_service.RuntimeServiceTests.test_scheduler_dispatch_pressure_gauge_tracks_admitted_dispatch \
  tests.test_service.RuntimeServiceTests.test_shutdown_closes_scheduler_dispatch_gate_atomically \
  -v
```

### Loop 110: Bounded Service Readiness Waiting

**Status:** Complete.

**Prior basis:** Loop 95 gave supervisors a one-shot deployment probe, but
startup and cutover scripts still had to implement their own polling loops.
Those ad hoc loops could spin too quickly, wait forever, hide the final safe
probe state, or disagree on exit semantics.

**Outcome:** The installed `service-wait` command polls the existing public
`/healthz` and `/readyz` contract with an immediate attempt, a timeout capped at
300 seconds, and a poll interval capped at 10 seconds. It prints only the last
fixed probe payload and preserves the existing `ready`/`not_ready`/`unavailable`
exit codes. No service route, credential, schema, or lifecycle behavior changes.

**Evidence:** Client tests cover ready-after-retry, deadline return, and timing
validation; CLI tests cover option forwarding and stable exit mapping. The
installed package smoke includes `service-wait --help`, while existing probe,
security, service-boundary, and full-suite checks remain green.

**Safety boundary:** This is a bounded client-side wait, not a service-side
readiness override, retry of business requests, or proxy/TLS bypass. Invalid
origins still fail before network access, and every probe retains the existing
five-second request timeout and 8 KiB response bound.

The focused evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service_client.ServiceClientTests.test_service_wait_polls_until_ready_with_bounded_sleep \
  tests.test_service_client.ServiceClientTests.test_service_wait_returns_last_not_ready_probe_at_deadline \
  tests.test_cli.CliTests.test_service_wait_command_prints_ready_contract_and_options \
  -v
```

### Loop 111: Prometheus Alert Starter Pack

**Status:** Complete.

**Prior basis:** Loop 46 established a fixed, low-cardinality Prometheus
surface, and Loops 108-109 added live HTTP and scheduler pressure gauges.
Operators still had to translate those stable signals into alert rules by
hand, which made first deployment and incident response needlessly dependent
on local Prometheus knowledge.

**Outcome:** The repository now ships an operator-managed
`examples/observability/prometheus-alerts.yml` starter pack covering readiness,
scheduler lease loss, uncertain recurring dispatches, request-admission
saturation, and server-class responses. The rules use only fixed metric names
and labels, include bounded `for` windows, and add no runtime route,
dependency, notification receiver, or automatic remediation.

**Evidence:** `observability_rules_smoke.py` checks the fixed group, alert set,
metric vocabulary, bounded rule/annotation shape, and absence of credential or
workflow-value markers. Unit tests invoke that smoke and assert the committed
rule contract; CI runs the smoke on every supported Python version.

**Safety boundary:** Alerts are operator signals, not execution controls. An
uncertain dispatch alert never authorizes blind replay, and saturation or
readiness alerts never mutate service lifecycle or workflow state. Prometheus
`promtool` remains the deployment-time parser/evaluator for the target version.

The focused evidence command is:

```bash
python3 scripts/observability_rules_smoke.py
PYTHONPATH=src python3 -m unittest tests.test_observability_rules -v
```

### Loop 112: Grafana Dashboard Starter Pack

**Status:** Complete.

**Prior basis:** Loop 111 made the fixed service metrics actionable with
operator-managed alert rules, but first deployment still required operators to
assemble a Grafana view by hand. That slowed health review and made the
readiness, lease, pressure, and uncertain-dispatch signals harder to inspect
consistently.

**Outcome:** The repository now ships an importable
`examples/observability/grafana-dashboard.json` starter dashboard with eight
read-only panels over the fixed service metrics. It uses one operator-selected
Prometheus datasource, fixed metric and label vocabulary, and no tenant,
workflow, run, request, credential, or host values.

**Evidence:** `observability_dashboard_smoke.py` validates JSON shape, the
Prometheus datasource input, panel IDs and types, the fixed metric vocabulary,
allowed labels, and the absence of sensitive-value markers. Unit tests invoke
that smoke and assert the import/read-only documentation contract; CI runs it
on every supported Python version.

**Safety boundary:** The dashboard is a read-only visualization artifact. It
does not add a runtime route, dependency, alert manager, notification policy,
automatic remediation, or workflow/service mutation. Grafana remains an
operator-managed deployment surface, and the target Grafana version must be
used to validate import compatibility.

The focused evidence command is:

```bash
python3 scripts/observability_dashboard_smoke.py
PYTHONPATH=src python3 -m unittest tests.test_observability_dashboard -v
```

### Loop 113: Release Artifact Provenance Manifest

**Status:** Complete.

**Prior basis:** Loop 50 proved that a wheel could be built, installed, and
qualified outside the source checkout, while Loop 112 made runtime health
signals easy to inspect. A release user still had to trust a maintainer's
description of the downloaded wheel or write a custom inventory script before
checking its exact bytes and member set.

**Outcome:** The repository now generates
`release-artifact-manifest.json` for each qualified wheel. The manifest records
the archive basename, byte length, SHA-256, fixed package metadata, and a
sorted SHA-256/size entry for every wheel member. The writer is atomic and
public-readable, and it rejects traversal, duplicate, symlink, private/state,
unexpected-root, identity, and dependency-contract violations.

**Evidence:** `scripts/release_manifest.py` is a standard-library generator;
`scripts/package_smoke.py` invokes it against the real built wheel and reports
the artifact digest and member count. Unit tests cover deterministic hashes,
atomic publication, traversal/duplicate/dependency rejection, and package-smoke
integration. Release documentation describes how users can verify the archive
without installing it.

**Safety boundary:** This is integrity/provenance evidence only. It is not a
digital signature, trusted-key attestation, SBOM, reproducible-build claim,
package upload, or release publication. The manifest does not include absolute
paths, source contents, credentials, workflow values, or environment data.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest tests.test_release_manifest -v
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-loop113
```

### Loop 114: Bounded Connector Retry Backoff

**Status:** Complete.

**Prior basis:** Connector retries were durable and auditable, but repeated
failures could immediately re-enter the provider call in a tight loop. That
made rate limits and transient outages harder to absorb and left the runtime
policy explicitly incomplete for production use.

**Outcome:** Connector retry policies now accept an additive `backoff_ms` on
the node or `policies.default_retry`. The effective fixed delay is bounded to
60,000 milliseconds, defaults to zero for compatibility, and is checked at a
safe point against the active `default_timeout_ms` budget. Run results,
`node_retrying` events, control-plane audit projection, local LiteGraph
overlays, and the authoring inspector expose the effective delay while the
stable remote run-detail shape remains unchanged.

**Evidence:** Compiler and JSON Schema validation cover the bounded policy;
executor tests inject a sleeper to prove delay, fallback resolution, clamping,
and recovery; control-plane, dashboard, service-client, visualizer, and web
authoring paths preserve the fixed redacted contracts.

**Safety boundary:** This is a fixed local delay, not exponential scheduling,
provider-specific retry classification, background workers, queueing,
automatic retry of uncertain effects, or exactly-once execution. The default
remains zero and external provider idempotency boundaries are unchanged.

The focused evidence commands are:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_executor tests.test_control_plane tests.test_dsl_contract \
  tests.test_visualizer tests.test_dashboard tests.test_service_client -v
```

### Loop 115: Bounded Global Workflow Deadline

**Status:** Complete.

**Prior basis:** The runtime bounded active execution segments, but a run
could remain in a human gate indefinitely because review time was intentionally
paused. Production workflows needed a separate, durable wall-clock boundary
that could converge after a missed or late operator decision without changing
the active-segment semantics.

**Outcome:** `policies.workflow_timeout_ms` is an additive, bounded policy from
0 to 30 days. The deadline starts when a run is created, remains active while a
human gate waits, and is checked before each node, after connector returns, and
after retry backoff. Expiry records fixed `workflow_timeout` evidence, keeps the
operator decision durable if resume arrives late, and prevents successor
execution. Existing `default_timeout_ms` behavior and stable remote read
contracts remain unchanged.

**Evidence:** Compiler and JSON Schema validation cover the bound. Executor and
control-plane tests cover human-gate expiry on resume, post-connector expiry,
persistence, fixed terminal audit evidence, and successor suppression. Runtime
policy, DSL contract, compatibility, stability, README, changelog, and roadmap
documentation define the boundary.

**Safety boundary:** This is a local safe-point deadline, not a background
expiry worker, node-level deadline, forceful provider abort, provider
reconciliation mechanism, or exactly-once guarantee. A connector already in
flight is observed only after it returns, and a run that is never resumed is
not asynchronously rewritten.

The focused evidence commands are:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_executor tests.test_compiler tests.test_dsl_contract \
  tests.test_runtime_policy_docs tests.test_production_roadmap -v
```

### Loop 116: Lease-Owned Workflow Deadline Sweep

**Status:** Complete.

**Prior basis:** The global deadline failed closed at executor safe points, but
a human gate with no operator activity could remain `waiting` indefinitely in a
long-running service. That left terminal retention, audit reconciliation, and
operator visibility dependent on a future resume request.

**Outcome:** The active SQLite scheduler lease now runs a bounded sweep about
once per second. Waiting runs with an elapsed `workflow_timeout_ms` deadline are
updated atomically under `BEGIN IMMEDIATE`, receive fixed
`error_code: "workflow_timeout"` evidence, and never resume or execute a
successor. Pending cooperative cancellation wins the race. The control plane
reconciles missing terminal audit evidence on every pass, so a cross-database
append failure can be repaired after takeover without replaying workflow work.

**Evidence:** JSON and SQLite stores cover bounded expiry and idempotence;
control-plane tests cover terminal audit reconciliation and audit-consistency
cleanliness; scheduler tests cover lease recovery and a real running scheduler
expiring a waiting run. Service, runtime-policy, recurring-scheduling, README,
stability, changelog, and roadmap documentation define the boundary.

**Safety boundary:** This is one lease-owned local SQLite sweeper, capped at
256 candidates per pass. It does not provide distributed scheduling, forceful
provider cancellation, automatic retry of uncertain effects,
or exactly-once execution. Standalone executors remain safe-point only.

The focused evidence commands are:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_executor tests.test_control_plane tests.test_service \
  tests.test_runtime_policy_docs tests.test_production_roadmap -v
```

### Loop 117: Filtered Cursor-Paged Run Discovery

**Status:** Complete.

**Prior basis:** The authenticated `/runs` view was intentionally a bounded
latest-run tail, which was sufficient for a small local operator handoff but
could not find an older failed or waiting run without direct SQLite access.
Operators needed a historical, filterable view that remained safe to expose
over the service boundary.

**Outcome:** The additive authenticated `GET /api/v1/runs` route and installed
`service-run-page` client provide status and workflow filters plus an opaque
cursor for stable continuation. Each page is redacted, limited to 100 items,
and capped at 64 KiB. The existing `/runs` and `service-runs` 0.1.0 tail
contract remains unchanged, and the page route performs no scheduler lease
acquisition or state mutation.

**Evidence:** SQLite storage, dashboard projection, service handler, protected
client, CLI, schema, telemetry, package qualification, documentation, and
real-process service tests cover filtering, cursor continuation, redaction,
authentication, response bounds, and compatibility with the legacy tail.

**Safety boundary:** This is a bounded local discovery window, not an
unbounded export, full-text search, arbitrary SQL surface, hosted multi-tenant
query service, or payload/credential inspection API. Cursors are opaque and
must be treated as short-lived continuation tokens; they do not provide a
snapshot isolation guarantee across concurrent writes.

The focused evidence commands are:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_storage tests.test_dashboard tests.test_service \
  tests.test_service_client tests.test_cli tests.test_run_detail_docs -v
```

### Loop 118: Per-Node Active Execution Deadlines

**Status:** Complete.

**Prior basis:** The runtime had a workflow-wide active execution budget and a
global wall-clock deadline, but a single slow connector or retry sequence could
consume the entire active segment without a node-specific limit. Operators
could not distinguish that case from a broader workflow timeout.

**Outcome:** Any node may declare `timeout_ms` from `0` to 24 hours. The
deadline starts when the node becomes current, is persisted with the run, and
is checked before node work, after connector returns, and after retry backoff.
Expiry records fixed `error_code: "node_timeout"` evidence, preserves the
failed node result, and suppresses successor execution. Human-gate waiting
clears the node window so review time is not charged.

**Evidence:** Workflow JSON Schema and compiler validation cover the bound;
executor tests cover connector-return expiry, persistence, successor
suppression, and human-gate pause behavior; LiteGraph round-trip tests cover
the allowlisted authoring field. Runtime-policy, compatibility, stability,
README, changelog, service, and roadmap documentation define the safe-point
boundary.

**Safety boundary:** This is a local safe-point budget, not forceful thread or
socket cancellation, provider reconciliation, distributed scheduling, or an
exactly-once guarantee. A provider request already in flight is observed only
after it returns, and standalone executors remain safe-point only.

The focused evidence commands are:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_executor tests.test_compiler tests.test_visualizer \
  tests.test_dsl_contract tests.test_runtime_policy_docs \
  tests.test_production_roadmap -v
```

### Loop 119: Bounded Built-in HTTP Connector Payloads

**Status:** Complete.

**Prior basis:** The built-in HTTP connector serialized arbitrary request JSON
and read arbitrary success or error response bodies. A malformed or untrusted
endpoint could therefore amplify memory use and persist an unexpectedly large
connector output in a durable run state.

**Outcome:** Built-in HTTP request bodies and UTF-8 success/error response
bodies are capped at 1 MiB. Request overflow fails before `urlopen`; response
overflow is detected after reading only one bounded sentinel byte and before a
connector result is returned. Invalid UTF-8 uses a fixed connector failure, and
no partial response is returned. Explicit external connector fixtures keep
their own I/O contract.

**Evidence:** Connector unit tests cover request overflow, success-response
overflow, response closing, invalid UTF-8 normalization, and existing success,
failure, timeout, credential, and body-mapping behavior. Connector docs,
compatibility/stability contracts, README, changelog, service guide, and this
roadmap record the 1 MiB boundary and its non-forceful semantics.

**Safety boundary:** This bounds built-in HTTP memory and persisted payload
size; it is not response redaction, provider-side cancellation, a limit on
explicit external connector code, or an exactly-once guarantee.

The focused evidence commands are:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_connectors tests.test_connector_package_docs -v
```

### Loop 120: Atomic First-Use SQLite State Initialization

**Status:** Complete.

**Prior basis:** Concurrent first use of one self-hosted SQLite state directory
could expose a partially-written `state-layout.json` to a second process. The
second initializer could fail with a malformed-marker error before it reached
its coordination boundary, leaving startup behavior timing-dependent.

**Outcome:** Fresh state markers are written to an owner-only temporary file,
fsynced, and published with a non-overwriting hard link. A concurrent
initializer either observes no marker yet or the complete current marker; it
never reads an in-progress JSON document and never replaces an existing marker.
Temporary files are cleaned up on success and failure.

**Evidence:** State-migration tests cover concurrent fresh SQLite initialization
and complete marker validation. Existing concurrent publication tests now run
through the same first-use path without marker corruption. The implementation
preserves legacy/future-layout rejection, owner-only permissions, descriptor
identity checks, and explicit copy-on-write migration semantics.

**Safety boundary:** This closes first-use marker publication for one local
state directory. It is not distributed locking, database replication, online
migration, or a multi-tenant state boundary.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_state_migration.StateMigrationTests.test_concurrent_fresh_sqlite_initialization_never_reads_partial_marker \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_concurrent_same_version_publication_is_idempotent \
  tests.test_control_plane.ControlPlaneTests.test_concurrent_different_content_same_version_fails_closed -v
```

### Loop 121: Bounded Local Audit Inspection

**Status:** Complete.

**Prior basis:** The local `audit` command and control-plane API could read the
entire JSONL or SQLite audit history before applying caller-side filters. On a
long-running self-hosted instance, routine incident inspection could therefore
consume memory proportional to the full audit log and print an unbounded
payload.

**Outcome:** `audit --limit N` accepts a fixed `1` through `1000` tail bound.
Workflow, version, run, and event-type filters are pushed into JSON/SQLite
storage before the bound. The newest matching events are returned in original
chronological order; no partial event is emitted. Omitting the flag preserves
the complete-list compatibility path.

**Evidence:** Storage tests cover JSON and SQLite filter-before-tail behavior,
chronological ordering, and invalid limits. CLI tests cover bounded output and
fixed validation errors. The operator guide, runtime-policy guide, stability
contract, README, changelog, and this roadmap document the 1-1000 boundary and
its non-retention semantics.

**Safety boundary:** This is an inspection/output and memory bound. It does not
delete audit rows, alter retention policy, seal JSON/JSONL storage, export a
remote audit stream, or change the unbounded compatibility behavior when the
flag is omitted.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_storage.StorageTests.test_audit_tail_limit_filters_before_bounding_for_json_and_sqlite \
  tests.test_cli.CliTests.test_audit_command_supports_bounded_tail_after_filters \
  tests.test_cli.CliTests.test_audit_command_rejects_unbounded_limit_without_traceback -v
```

### Loop 122: Bounded Offline Control Snapshots

**Status:** Complete.

**Prior basis:** The live control snapshot already exposed a fixed 100-item
window, but the offline `control-snapshot` command had no CLI window option and
could load complete JSON/SQLite history before trimming its output. Routine
operator exports could therefore grow with the lifetime of the state directory.

**Outcome:** Offline `control-snapshot --max-items N` accepts a fixed `1` through
`1000` bound and publishes the existing `window` accounting. JSON and SQLite
storage retain newest workflow, run, and audit windows while preserving
aggregate totals; live service snapshots keep their fixed 100-item contract.
The option is rejected for `--service-url`, and omitting it preserves the
complete offline export path.

**Evidence:** Dashboard tests prove JSON and SQLite bounded windows avoid
unbounded run/audit list paths, preserve totals, and report truncation. CLI
tests cover offline output, fixed range validation, and live-option rejection.
The operator guide, stability contract, README, changelog, and this roadmap
record the 1-1000 boundary and complete-export compatibility.

**Safety boundary:** This bounds inspection output and retained window data; it
does not delete state, change retention, alter the live service response, or
claim that a bounded export is a complete disaster-recovery backup.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_json_bounded_snapshot_does_not_call_unbounded_list_paths \
  tests.test_dashboard.DashboardTests.test_sqlite_bounded_snapshot_does_not_call_unbounded_list_paths \
  tests.test_cli.CliTests.test_control_snapshot_command_accepts_bounded_offline_window \
  tests.test_cli.CliTests.test_control_snapshot_command_rejects_max_items_for_live_service -v
```

### Loop 123: Bounded Local Run Discovery

**Status:** Complete.

**Prior basis:** Remote operators already had a bounded cursor-paged run route,
but local `runs` and `control-runs` loaded every run before printing compact
summaries. JSON snapshot tails also used filename order rather than the newest
durable state timestamp.

**Outcome:** Local `runs --limit N` and `control-runs --limit N` accept a fixed
`1` through `1000` bound and preserve the existing compact array output. SQLite
uses durable update time and run ID ordering; JSON retains only the newest
timestamped states with a filesystem fallback for legacy records without event
timestamps. Omitting the flag preserves the complete-list compatibility path.

**Evidence:** Storage tests prove JSON/SQLite bounded reads retain the newest
chronological states and reject invalid limits. CLI tests cover both storage
backends, both local commands, fixed validation, and compatibility. The run
discovery guide, stability contract, README, changelog, and this roadmap record
the 1-1000 boundary and no-mutation semantics.

**Safety boundary:** This bounds local inspection and retained read memory; it
does not delete runs, alter retention, change remote service contracts, or add
cursor state to the local CLI.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_storage.StorageTests.test_run_windows_are_bounded_and_ordered_by_latest_state_timestamp \
  tests.test_cli.CliTests.test_local_run_commands_support_bounded_windows_for_json_and_sqlite \
  tests.test_cli.CliTests.test_local_run_commands_reject_invalid_limit_without_traceback -v
```

### Loop 124: Bounded Local Backup Inventory

**Status:** Complete.

**Prior basis:** Operators could create and verify one backup set at a time,
but had no safe bounded view of a backup parent containing many point-in-time
sets. A naive inventory could load every manifest, expose host paths, or
silently treat an invalid set as usable.

**Outcome:** `backup-list` accepts a fixed `1` through `1000` limit (default
`100`), scans only direct owner-only child directories, retains the newest
manifest creation times with a filesystem fallback for malformed entries, and
verifies only the returned sets. Its fixed value-free projection reports
integrity status, creation time, layout identity, file count, workflow-artifact
count, and total bytes without paths, contents, credentials, or manifest error
details.

**Evidence:** Backup and CLI tests cover newest-set ordering, invalid-set
reporting, fixed limit validation, owner-only boundaries, and the JSON contract.
The operator guide, stability contract, README, changelog, package smoke, and
[`schemas/state-backup-list-0.1.0.schema.json`](schemas/state-backup-list-0.1.0.schema.json)
record the same 1-1000 boundary and no-mutation semantics.

**Safety boundary:** This is a local read-only inventory. It does not delete,
upload, rewrite, expire, encrypt, restore, or replicate backups, and it does
not turn the backup directory into a complete disaster-recovery service.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_backup.StateBackupTests.test_backup_list_is_bounded_and_reports_integrity_without_paths \
  tests.test_backup.StateBackupTests.test_backup_list_reports_invalid_selected_sets_and_rejects_bad_limits \
  tests.test_cli.CliTests.test_backup_list_command_reports_bounded_verified_inventory -v
```

### Loop 125: Bounded Backup Retention Planning

**Status:** Complete.

**Prior basis:** Operators could inspect backup sets, but expiration remained
an ad hoc manual decision. That made it easy to delete too many copies, remove
the only valid recovery point, or act on an incomplete inventory.

**Outcome:** `backup-retention-plan` accepts the fixed
`skill2workflow-backup-retention-policy-0.1.0` policy with an explicit
`expire_before` cutoff and `minimum_keep` valid-backup floor. It emits a
`ready` plan only for a complete bounded inventory, marks strictly older valid
sets outside the floor as candidates, preserves invalid sets and newer sets,
and returns a policy digest, fixed counts, byte totals, names, and reasons.

**Evidence:** Backup and CLI tests cover candidate ordering, minimum retention,
invalid-set preservation, policy validation, inventory truncation blocking, and
zero filesystem mutation. The operator guide, stability contract, README,
changelog, package smoke, and the versioned policy/plan schemas record the
same fail-closed semantics.

**Safety boundary:** This is a read-only plan. It does not delete, rename,
upload, rewrite, encrypt, restore, or schedule backup expiration; an operator
must separately review the plan and use storage-platform controls for any
irreversible destruction.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_backup.StateBackupTests.test_backup_retention_plan_preserves_minimum_and_invalid_sets \
  tests.test_backup.StateBackupTests.test_backup_retention_plan_blocks_truncated_inventory_and_rejects_policy_shape \
  tests.test_cli.CliTests.test_backup_retention_plan_command_is_read_only_and_bounded -v
```

### Loop 126: Bounded Local Schedule Inspection

**Status:** Complete.

**Prior basis:** Local `schedules` and `schedule-dispatches` inspection loaded
complete collections into operator output. That left long-running self-hosted
instances with an unbounded read surface even though remote recurring-schedule
diagnostics already had fixed windows.

**Outcome:** The optional `--limit` flag accepts `1` through `1000` and returns
the newest compact schedule or dispatch summaries with aggregate totals and
status counts. Schedule summaries omit trigger inputs; dispatch summaries omit
lease-owner and claim-expiry identities. Omitting the flag preserves the
complete-list compatibility path.

**Evidence:** Storage, runner, CLI, schema, documentation, changelog, and
package-smoke tests cover newest-window ordering, fixed limits, redaction,
invalid input, JSON/SQLite parity, and compatibility without the flag.

**Safety boundary:** This is read-only local inspection. It does not mutate
schedules, acquire leases, dispatch work, or alter remote recurring-schedule
contracts.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_schedules tests.test_recurring_schedules \
  tests.test_cli.CliTests.test_schedule_list_command_supports_bounded_compact_window -v
```

### Loop 127: Bounded Local Workflow Inventory

**Status:** Complete.

**Prior basis:** The local `workflows` command returned the complete workflow
registry, even though the authenticated remote inventory already had a fixed
redacted contract. Long-running self-hosted installations therefore had no
bounded local operator view for release discovery.

**Outcome:** `workflows --limit` reuses
`skill2workflow-workflow-inventory-0.1.0`, retaining the newest 1–100 published
versions with aggregate lifecycle counts and truncation metadata. The compact
projection contains only ids, versions, statuses, aliases, and checksums; it
does not expose workflow content, trigger inputs, connector requests, or
credentials. Omitting the flag preserves the complete-list compatibility path.

**Evidence:** CLI, dashboard-projection, schema, documentation, changelog,
package, and full-suite tests cover JSON/SQLite publication, newest ordering,
redaction, invalid limits, and unchanged complete-list behavior.

**Safety boundary:** This is a read-only local inventory. It does not acquire
the scheduler lease, inspect artifact contents, mutate the registry, promote
aliases, trigger runs, or change the remote service contract.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_workflow_inventory_is_bounded_redacted_and_storage_compatible \
  tests.test_cli.CliTests.test_workflows_command_supports_bounded_redacted_inventory_window \
  tests.test_cli.CliTests.test_workflows_command_rejects_invalid_bounded_inventory_limit \
  tests.test_workflow_releases_docs.WorkflowReleaseDocumentationTests.test_review_contract_and_cas_boundary_are_published -v
```

### Loop 128: Bounded Workflow Artifact Diagnostics

**Status:** Complete.

**Prior basis:** `workflow-artifacts` already capped its returned issue array,
but the control-plane scan first retained every issue and only then truncated
the report. A damaged or orphan-heavy state directory could therefore consume
memory proportional to all detected failures during routine diagnostics.

**Outcome:** Artifact inspection now counts every issue while retaining only a
fixed 1–256 deterministic issue window. Local and remote projections share the
same bounded collector; `issue_count`, per-kind counts, status, and truncation
remain complete, while issue records stay value-free and bounded.

**Evidence:** Control-plane and dashboard tests cover custom windows, complete
counts, deterministic ordering, redaction, and the existing 256-record remote
contract. The artifact guide, stability contract, changelog, and full-suite
tests record the no-repair/no-delete boundary.

**Safety boundary:** This is a read-only diagnostic retention bound. It does
not repair registry entries, rewrite checksums, delete artifacts, or change
publication and backup behavior.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_workflow_artifact_report_retains_only_requested_issue_window \
  tests.test_dashboard.DashboardTests.test_remote_workflow_artifact_report_is_bounded_and_reuses_fixed_contract \
  tests.test_workflow_releases_docs.WorkflowReleaseDocumentationTests.test_artifact_diagnostic_window_is_documented -v
```

### Loop 129: Bounded Due-Run Batches

**Status:** Complete.

**Prior basis:** `schedule-run-due` processed every due one-shot and recurring
schedule in one invocation. A large backlog or operator retry could therefore
create an unbounded batch of workflow side effects and hold the scheduler lease
for an uncontrolled interval.

**Outcome:** The optional `--max-items` flag accepts `1` through `100` and
applies one deterministic budget across one-shot and recurring schedule
records. Recurring claims are limited inside the SQLite transaction; unclaimed
due records remain eligible for a later invocation. Bounded output adds a
compact `window` budget summary; omitted flags preserve the historical result
shape and complete-batch behavior.

**Evidence:** Runner, recurring dispatcher, CLI, documentation, stability,
package, and full-suite tests cover one-shot preservation, SQLite claim limits,
fixed validation, deterministic ordering, and compatibility without the flag.

**Safety boundary:** This is an operator-side batch budget, not a retry policy,
queue, cancellation mechanism, or exactly-once provider guarantee. It does not
change trigger idempotency, scheduler lease ownership, or missed-run policy.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_schedules.ScheduleTests.test_runner_can_bound_one_shot_due_batch_without_consuming_remaining_schedules \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_recurring_dispatch_budget_claims_only_requested_batch \
  tests.test_cli.CliTests.test_schedule_run_due_command_supports_bounded_batch_budget -v
```

### Loop 130: Bounded Run-Audit Inspection

**Status:** Complete.

**Prior basis:** `audit-consistency` already capped its report at 256 runs, but
the control-plane path first loaded every durable run state and then truncated
the in-memory summaries. Long-running instances could therefore pay an
unbounded diagnostic read cost despite the fixed redacted report contract.

**Outcome:** Global inspection now counts durable run rows/files and reads only
the newest 256 summaries. Targeted `--run-id` inspection reads one run
directly. The report schema, redaction, missing/duplicate/unexpected event
semantics, and diagnostic-only boundary remain unchanged.

**Evidence:** Storage, executor, control-plane, documentation, and full-suite
tests prove count-only global reads, bounded summary selection, direct targeted
reads, and compatibility with existing JSON/SQLite reports and remote routes.

**Safety boundary:** This is a source-read bound for diagnostics. It does not
repair audit history, alter retention, replay workflows, or change the remote
service response contract.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_storage.StorageTests.test_run_count_does_not_load_all_states \
  tests.test_control_plane.ControlPlaneTests.test_run_audit_consistency_global_report_uses_bounded_run_window \
  tests.test_control_plane.ControlPlaneTests.test_run_audit_consistency_target_reads_one_run_without_listing_all_runs \
  -v
```

### Loop 131: Streaming Workflow Artifact Diagnostics

**Status:** Complete.

**Prior basis:** Loop 128 bounded retained issue records, but the production
SQLite diagnostic still loaded the complete workflow registry and materialized
the complete filesystem artifact set before reporting orphaned files.

**Outcome:** SQLite artifact inspection now streams registry rows in stable
order, counts references in the database, and checks each filesystem artifact
by exact registry reference. Issue retention, complete counts, deterministic
redaction, and the JSON evaluation path remain compatible.

**Evidence:** Control-plane, service, documentation, package, and full-suite
tests prove clean and damaged SQLite reports, registry streaming, orphan
detection, and the unchanged remote report contract.

**Safety boundary:** This is a read-only diagnostic memory bound. It does not
repair or delete artifacts, mutate registry rows, change checksums, or make
JSON storage multi-process safe.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_workflow_artifact_report_is_bounded_and_finds_registry_and_orphan_gaps \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_workflow_artifact_report_streams_registry_without_loading_index \
  tests.test_service.RuntimeServiceTests.test_workflow_artifact_report_is_authenticated_bounded_and_value_free \
  -v
```

### Loop 132: Streaming SQLite Audit Integrity

**Status:** Complete.

**Prior basis:** Loop 65 made the SQLite audit chain independently verifiable,
but verification and legacy-column rebuilds still used `fetchall()` for the
complete ordered event history. Long-running instances could therefore turn a
read-only integrity check, backup validation, or remote diagnostic into an
unbounded memory operation.

**Outcome:** Current-chain verification performs one count-only query and then
streams rows through the existing digest, denormalized-column, and payload
checks. Legacy-chain integrity columns are rebuilt through the same cursor
path. The fixed result contract and invalid-chain semantics are unchanged.

**Evidence:** Audit-integrity tests cover valid and tampered chains, verified
backup/restore, legacy upgrade, and a no-`fetchall` streaming proxy. The
existing backup, remote audit-integrity, CLI, package, and full-suite paths
reuse the same implementation.

**Safety boundary:** This bounds verifier source memory only. It does not make
the audit log immutable, cryptographically signed, remotely replicated, or
JSON/JSONL chain-aware.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_audit_integrity.AuditIntegrityTests.test_audit_chain_verification_and_rebuild_stream_event_rows \
  tests.test_audit_integrity.AuditIntegrityTests.test_sqlite_audit_chain_is_valid_and_detects_payload_tampering \
  tests.test_service.RuntimeServiceTests.test_audit_integrity_is_authenticated_payload_free_and_read_only \
  -v
```

### Loop 133: Streaming Backup Artifact Registry Reads

**Status:** Complete.

**Prior basis:** Verified backup preflight, creation, and restored-state
validation used `_workflow_artifact_records()` and materialized every
`workflow_versions` artifact row before processing the referenced files. A
long-running registry could therefore add avoidable memory pressure to the
offline recovery boundary.

**Outcome:** Backup paths now iterate artifact references in stable SQL order,
deduplicate adjacent versions with a constant-size cursor state, validate and
copy each referenced artifact as it is read, and compare restored references
against the manifest without a second full registry set. The manifest,
checksum, restore, and JSON evaluation contracts remain unchanged.

**Evidence:** Backup tests cover round trips, tamper rejection, legacy/current
state handling, a no-`fetchall` artifact-registry proxy, and the real-process
backup/restore drill. Documentation, stability, package, and full-suite tests
retain the public contract.

**Safety boundary:** This bounds SQLite registry source reads only. It does not
add hot backup, incremental snapshots, remote replication, encryption,
signatures, or backup deletion automation.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_backup.StateBackupTests.test_workflow_artifact_registry_streams_without_fetchall \
  tests.test_backup.StateBackupTests.test_round_trip_preserves_control_runs_schedules_and_workflow_artifacts \
  tests.test_backup.StateBackupTests.test_tampering_is_rejected_before_restore_creates_destination \
  -v
```

### Loop 134: Streaming Stale-Claim Recovery

**Status:** Complete.

**Prior basis:** Recurring scheduler restart recovery selected every expired
`claimed` dispatch row with `fetchall()` before updating it to `uncertain`.
Long-running dispatch ledgers could therefore add avoidable memory pressure to
the lease-takeover path even though each row was processed independently.

**Outcome:** Recovery now iterates eligible dispatch rows through the SQLite
cursor inside the existing transaction, updates each row as it is read, and
returns the same recovered count. The `uncertain` transition, no-automatic-
retry rule, audit behavior, and scheduler lease boundary remain unchanged.

**Evidence:** Recurring-schedule tests cover the no-`fetchall` cursor boundary
and existing stale-claim recovery semantics. Documentation, stability,
package, and full-suite tests retain the public contract.

**Safety boundary:** This bounds stale-claim recovery source reads only. It does
not add automatic replay, provider reconciliation, distributed scheduling, or
exactly-once execution.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_stale_claim_rows_stream_without_fetchall \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_stale_claim_becomes_uncertain_and_is_not_automatically_retried \
  -v
```

### Loop 135: Streaming Interrupted-Run Takeover

**Status:** Complete.

**Prior basis:** Process-loss recovery selected every foreign active execution
and its full run-state JSON with `fetchall()` before fencing abandoned tickets.
A long-running service could therefore add avoidable memory pressure to the
lease-takeover path before any recovery mutation began.

**Outcome:** Takeover now iterates foreign active-execution rows through the
SQLite cursor inside the existing transaction, fences and rewrites each run as
it is read, and preserves the recovered-state return list. The fencing,
unknown-outcome, audit-reconciliation, and no-replay contracts remain
unchanged.

**Evidence:** Storage tests cover the no-`fetchall` execution-ledger cursor and
interrupted-recovery tests retain takeover, fencing, crash, and real-process
drill coverage. Documentation, stability, package, and full-suite tests retain
the public contract.

**Safety boundary:** This bounds the takeover source read only. It does not add
automatic replay, provider reconciliation, distributed ownership, or
exactly-once execution.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_storage.StorageTests.test_interrupted_execution_rows_stream_without_fetchall \
  tests.test_interrupted_recovery.InterruptedRunRecoveryTests.test_takeover_marks_foreign_active_run_interrupted_and_fences_old_writer \
  -v
```

### Loop 136: Streaming Workflow Alias Promotion

**Status:** Complete.

**Prior basis:** SQLite alias promotion loaded every workflow registry record
into an in-memory index before checking the target, evaluating the CAS guard,
and rewriting aliases. A large multi-workflow registry could therefore make a
single release move pay for unrelated versions.

**Outcome:** Promotion now reads the target record directly and streams only
the selected workflow's records while removing the alias. The transaction,
compare-and-swap guard, alias uniqueness, audit append, and JSON compatibility
remain unchanged.

**Evidence:** Control-plane tests cover CAS, no-op retry, concurrent operators,
artifact-integrity failure, alias-scoped replay, and a regression that rejects
the global SQLite registry load. Storage tests cover the no-`fetchall` selected-
workflow cursor. Documentation, package, and full-suite tests retain the
public contract.

**Safety boundary:** This bounds promotion source reads only. It does not add
canary rollout, health-based rollback, policy evaluation, distributed release
coordination, or multi-tenant isolation.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_promotion_does_not_load_the_global_registry \
  tests.test_storage.StorageTests.test_workflow_records_for_id_stream_without_fetchall \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_promotion_cas_is_atomic_across_concurrent_operators \
  -v
```

### Loop 137: Streaming Interrupted-Run Reconciliation

**Status:** Complete.

**Prior basis:** After takeover, control-plane recovery loaded every
`run_interrupted` audit payload and every run state to find missing audit
evidence. A long-running service with a large historical backlog could
therefore reintroduce unbounded startup memory even after the execution-ledger
source read was streamed.

**Outcome:** Recovery now streams durable `interrupted` run states and checks
one `(run_id,event_type)` audit projection at a time before appending the
missing compact event. The takeover count, audit repair semantics, unknown-
outcome boundary, and no-replay behavior remain unchanged.

**Evidence:** Storage tests cover the no-`fetchall` interrupted-state cursor;
recovery tests reject full run/audit enumeration while retaining takeover,
mid-recovery repair, fencing, and real-process crash evidence. Documentation,
stability, package, and full-suite tests retain the public contract.

**Safety boundary:** This bounds post-takeover reconciliation reads only. It
does not add automatic replay, provider reconciliation, distributed ownership,
or exactly-once execution.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_storage.StorageTests.test_interrupted_run_states_stream_without_fetchall \
  tests.test_interrupted_recovery.InterruptedRunRecoveryTests.test_recovery_reconciliation_does_not_enumerate_full_runs_or_audit \
  tests.test_interrupted_recovery.InterruptedRunRecoveryTests.test_takeover_repairs_missing_control_audit_after_mid_recovery_crash \
  -v
```

### Loop 138: Bounded Readiness Registry Checks

**Status:** Complete.

**Prior basis:** The live `/readyz` path called the complete workflow-list API
on every probe. As published-version history grew, routine traffic-removal
checks could repeatedly materialize the entire SQLite registry even though
readiness only needed to know whether the registry was readable.

**Outcome:** Readiness now uses a count-only registry check for SQLite and
retains the complete-list compatibility path for explicit operator inventory.
The probe still fails closed on storage errors, while no workflow payloads are
returned or copied during readiness.

**Evidence:** Control-plane and service tests reject the old full-list path and
prove the count query is used; full-suite, package, service-boundary, and
secret-hygiene checks retain the public service contract.

**Safety boundary:** This bounds readiness inspection only. It does not change
workflow publication, inventory, artifact validation, scheduler ownership, or
the complete `list_workflows()` API.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_registry_readiness_check_does_not_load_records \
  tests.test_service.RuntimeServiceTests.test_readiness_checks_sqlite_registry_without_materializing_records \
  -v
```

### Loop 139: Bounded Stable-Alias Resolution

**Status:** Complete.

**Prior basis:** Trigger requests using a stable alias called the generic
workflow resolver, which loaded the complete SQLite registry before selecting
one published version. Alias traffic therefore copied unrelated workflow
history into every request process even though the target workflow was known.

**Outcome:** SQLite resolution now checks the exact `workflow_id@version` key
directly, then streams only records for the requested workflow when resolving
an alias. Exact-version precedence, ambiguity rejection, and idempotency
replay pinning remain unchanged.

**Evidence:** A control-plane regression rejects global index loading during
alias resolution; alias-trigger replay and exact-version precedence tests
remain green, with selected-workflow cursor coverage retained in storage.

**Safety boundary:** This bounds version resolution reads only. It does not
change publication, promotion, deprecation, artifact validation, or the
complete workflow inventory/list APIs.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane.ControlPlaneTests.test_sqlite_alias_resolution_does_not_load_global_registry \
  tests.test_control_plane.ControlPlaneTests.test_workflow_alias_promotion_resolves_triggers_and_pins_replays \
  tests.test_control_plane.ControlPlaneTests.test_exact_version_takes_precedence_over_same_named_alias \
  -v
```

### Loop 140: Bounded Service Dispatch Batches

**Status:** Complete.

**Prior basis:** The CLI already had `schedule-run-due --max-items 100`, but
the long-running service scheduler called `dispatch_due` without a budget.
A large due backlog could therefore be claimed and retained in one polling
pass while the lease-held claim transaction and subsequent side-effect batch
grew with history.

**Outcome:** Every service scheduler polling pass now passes a fixed 100-item
budget to recurring dispatch. Remaining due schedules remain eligible for the
next pass; lease ownership, claim-before-execute ordering, uncertain recovery,
and complete-batch CLI compatibility remain unchanged.

**Evidence:** Service regression coverage asserts the fixed batch argument and
the existing recurring dispatch persistence/budget tests remain green. Full
suite, package, service-boundary, backup, observability, interrupted-recovery,
and secret-hygiene smoke evidence retain the public contract.

**Safety boundary:** This bounds long-running service polling only. It does
not add automatic retries, alter the CLI omission behavior, or claim
exactly-once provider execution.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_scheduler_dispatch_uses_fixed_batch_budget \
  tests.test_service.RuntimeServiceTests.test_service_dispatches_recurring_schedule_and_persists_record \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_recurring_dispatch_budget_claims_only_requested_batch \
  -v
```

### Loop 141: Bounded Stale-Claim Recovery Writes

**Status:** Complete.

**Prior basis:** Loop 134 changed stale-claim recovery to stream eligible
dispatch rows, but a service takeover still updated every expired claim inside
one lease-held write transaction. A large crash backlog could therefore keep
the scheduler lease and SQLite write transaction busy for an unbounded amount
of time.

**Outcome:** Long-running service takeover now recovers stale claims in fixed
100-row transactions and renews the lease between full batches. Remaining
claims are processed before interrupted-run reconciliation and dispatch resume;
the `uncertain` state, no-automatic-retry rule, and complete-batch direct
dispatcher/CLI compatibility remain unchanged.

**Evidence:** Recurring-schedule coverage proves a caller can recover claims
in bounded batches while preserving all `uncertain` records. Service coverage
proves takeover passes the fixed budget and renews between full batches. Full
suite, service-boundary, backup, observability, interrupted-recovery, and
secret-hygiene smoke evidence retain the public contract.

**Safety boundary:** This bounds service takeover write transactions only. It
does not retry uncertain provider effects, alter claim-before-execute ordering,
or introduce distributed scheduling or exactly-once execution.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_scheduler_lease_recovery_runs_workflow_deadline_sweep \
  tests.test_service.RuntimeServiceTests.test_scheduler_lease_recovery_renews_between_full_stale_claim_batches \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_stale_claim_recovery_accepts_a_bounded_batch \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_stale_claim_becomes_uncertain_and_is_not_automatically_retried \
  -v
```

### Loop 142: Bounded Interrupted-Run Takeover Writes

**Status:** Complete.

**Prior basis:** Loop 135 changed process-loss takeover to stream foreign
active-execution rows, but the service still fenced every abandoned execution
inside one lease-held SQLite write transaction. A large crash backlog could
therefore delay lease renewal and keep recovery unavailable for an unbounded
interval.

**Outcome:** Long-running service takeover now fences foreign executions in
fixed 100-row transactions and renews the scheduler lease between full batches.
After all batches finish, the existing streamed interrupted-run audit
reconciliation repairs missing control evidence before normal deadline sweeps
and recurring dispatch resume. Direct executor/control-plane complete-batch
compatibility and no-replay semantics remain unchanged.

**Evidence:** Interrupted-recovery coverage seeds multiple foreign active
executions and proves bounded batches fence each run without replay. Service
coverage proves the fixed budget and lease renewal between full batches. Full
suite, service-boundary, backup, observability, interrupted-recovery, and
secret-hygiene smoke evidence retain the public contract.

**Safety boundary:** This bounds service takeover write transactions only. It
does not retry unknown provider effects, weaken execution-ticket fencing, alter
audit repair, or introduce distributed scheduling or exactly-once execution.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_interrupted_recovery.InterruptedRunRecoveryTests.test_interrupted_takeover_accepts_a_bounded_write_batch \
  tests.test_interrupted_recovery.InterruptedRunRecoveryTests.test_scheduler_runs_recovery_only_after_it_acquires_the_lease \
  tests.test_service.RuntimeServiceTests.test_scheduler_lease_recovery_renews_between_full_interrupted_batches \
  tests.test_interrupted_recovery.InterruptedRunRecoveryTests.test_takeover_repairs_missing_control_audit_after_mid_recovery_crash \
  -v
```

### Loop 143: Bounded Interrupted-Run Audit Reconciliation

**Status:** Complete.

**Prior basis:** Loop 137 changed interrupted-run audit repair to stream run
states and check one audit projection at a time, but the service still scanned
and repaired the entire interrupted backlog after takeover without a cursor
batch or lease-renewal boundary. A large crash backlog could therefore delay
deadline sweeps and recurring dispatch even though takeover writes were already
bounded.

**Outcome:** The control plane now exposes a cursor-bounded reconciliation
primitive that scans at most 100 interrupted states and appends missing
`run_interrupted` evidence as one bounded audit batch. The service renews its
scheduler lease between full cursor pages. Direct complete-batch recovery keeps
its existing return value and no-replay semantics; the cursor is internal and
is not a new remote operator filter.

**Evidence:** Interrupted-recovery coverage proves cursor continuation,
bounded scanning, idempotent audit repair, and complete-batch compatibility.
Service coverage proves the fixed 100-item argument and lease renewal between
full audit pages. Full suite, service-boundary, backup, observability,
interrupted-recovery, and secret-hygiene smoke evidence retain the public
contract.

**Safety boundary:** This bounds startup audit-repair work only. It does not
retry unknown provider effects, change audit payloads, weaken execution-ticket
fencing, or introduce distributed scheduling or exactly-once execution.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_interrupted_recovery.InterruptedRunRecoveryTests.test_interrupted_audit_reconciliation_accepts_a_bounded_cursor_batch \
  tests.test_service.RuntimeServiceTests.test_scheduler_lease_recovery_renews_between_full_interrupted_audit_batches \
  tests.test_interrupted_recovery.InterruptedRunRecoveryTests.test_takeover_repairs_missing_control_audit_after_mid_recovery_crash \
  -v
```

### Loop 144: Bounded Run-Detail Audit Reads

**Status:** Complete.

**Prior basis:** Loop 59 fixed the authenticated run-detail response at a
50-event redacted window, but the dashboard helper still loaded every matching
control-plane audit event for the selected run before truncating the projection.
A retry-heavy run could therefore make an ordinary operator detail request
scale with its complete audit history despite the fixed response contract.

**Outcome:** Run-detail projection now passes its fixed 50-event budget through
to both JSON and SQLite audit stores. The storage layer retains the newest
matching tail before overlay and response projection; run-state event totals,
redaction, response schema, and complete local audit-list compatibility remain
unchanged.

**Evidence:** Dashboard regression coverage rejects an unbounded audit-store
call and proves the fixed detail window remains unchanged. Service and client
run-detail contract tests, full suite, package, service-boundary, backup,
observability, interrupted-recovery, and secret-hygiene smoke evidence retain
the public contract.

**Safety boundary:** This bounds one diagnostic read only. It does not alter
run execution, retention, audit-chain integrity, event persistence, or the
operator's complete local `audit` compatibility path.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_run_detail_reads_only_the_bounded_audit_tail \
  tests.test_dashboard.DashboardTests.test_run_detail_is_bounded_and_redacts_context_results_and_errors \
  tests.test_service.RuntimeServiceTests.test_run_detail_is_authenticated_redacted_bounded_and_read_only \
  tests.test_service_client.ServiceClientTests.test_run_detail_uses_authenticated_get_and_validates_redacted_contract \
  -v
```

### Loop 145: Compact SQLite Run-Summary Projections

**Status:** Complete.

**Prior basis:** Bounded run discovery, cursor paging, offline snapshots, and
global audit consistency already limited the number of returned rows, but the
SQLite queries still selected each complete `state_json` document. A single
run can contain workflow DSL, trigger context, node results, and long event
history, so a fixed row window did not provide a fixed source-read boundary.

**Outcome:** SQLite now maintains a transactional `run_summaries` projection
with only run identity, status, current node, event count, node-result count,
and update ordering. Bounded list, snapshot, cursor-page, and targeted/global
audit-consistency reads select compact summary columns; audit consistency uses
grouped `run_events` counts instead of loading complete run state. Explicit
`get_run`/run-detail and complete-list compatibility paths remain unchanged.

**Evidence:** Storage regression corrupts the full state document after the
summary is persisted and proves bounded list, snapshot, and page reads still
return the fixed redacted summary. Audit-consistency regression proves the
global report remains clean without parsing that document. Backup validation
accepts the optional summary table for older state copies, and retention removes
summary rows with their terminal runs.

**Safety boundary:** The projection is derived transactionally from the same
run save that persists full state and event rows. It does not change workflow
execution, event persistence, audit-chain semantics, full detail reads, JSON
compatibility, or the retention source-preservation boundary.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_storage.StorageTests.test_sqlite_bounded_run_reads_use_compact_summary_projection \
  tests.test_control_plane.ControlPlaneTests.test_run_audit_global_projection_does_not_load_full_sqlite_run_state \
  tests.test_control_plane.ControlPlaneTests.test_run_audit_consistency_report_detects_missing_and_duplicate_events \
  tests.test_dashboard.DashboardTests.test_run_list_is_bounded_and_redacted \
  tests.test_dashboard.DashboardTests.test_run_page_is_filtered_redacted_and_cursor_paged \
  -v
```

### Loop 146: Compact SQLite Recurring-Schedule Projections

**Status:** Complete.

**Prior basis:** The bounded recurring-schedule inventory already limited the
returned window, but SQLite still selected and parsed every complete
`definition_json` document. A schedule definition can carry a trigger input up
to the canonical 1 MiB boundary, so a fixed item window did not provide a fixed
source-read boundary.

**Outcome:** SQLite now maintains a transactional
`recurring_schedule_summaries` projection containing only scheduling metadata.
Bounded recurring-schedule inventory reads summary columns and status counts
without parsing trigger input; complete `list`/`get` and dispatch execution
paths remain unchanged.

**Evidence:** The storage and dashboard regressions corrupt a persisted full
definition after the summary is written and prove both local and authenticated
service inventory still return the fixed redacted metadata. Existing dispatch,
enable/disable, backup, restore, and restart tests prove the projection is
maintained across state transitions and older scheduler databases are
backfilled on open.

**Safety boundary:** The projection is derived in the same SQLite transaction
as definition writes and is optional for backup-schema compatibility. It does
not change trigger inputs, lease ownership, missed-run policy, dispatch
claims, or full schedule retrieval.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_sqlite_compact_schedule_inventory_uses_summary_projection \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_sqlite_store_streams_bounded_schedule_inventory \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_set_enabled_with_result_is_idempotent_and_serialized \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_latest_policy_coalesces_missed_occurrences_into_one_durable_dispatch \
  -v
```

### Loop 147: Compact SQLite Run-Detail Projections

**Status:** Complete.

**Prior basis:** Loop 144 bounded the run-detail audit tail and Loop 145
bounded run discovery, but authenticated `GET /runs/{run_id}` still loaded the
complete SQLite `state_json` document. A run can contain a large trigger
context, workflow DSL, connector output, node results, and a long event
history, so a fixed 50-event response did not provide a fixed source-read
boundary.

**Outcome:** SQLite now maintains a value-free run-detail projection alongside
the existing run summary. Authenticated detail reads select compact node
overlays and counts plus at most the requested `run_events` tail; they do not
parse the complete state document. JSON storage, `get_run`, and other explicit
full-state compatibility paths remain unchanged.

**Evidence:** Dashboard regression corrupts a persisted SQLite `state_json`
document after the compact projection is written and proves the fixed redacted
detail contract still returns status, counts, node overlays, and the bounded
event tail. Existing service, backup, migration, and redaction tests cover
schema compatibility, state initialization, authenticated availability, and
no private-value disclosure.

**Safety boundary:** The projection is derived transactionally during the same
run save as full state and event rows. It contains only allowlisted overlay
metadata and a boolean error flag; it does not change execution, event
persistence, audit integrity, retention, or the complete local state API.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_sqlite_run_detail_uses_compact_projection_without_state_json \
  tests.test_dashboard.DashboardTests.test_run_detail_is_bounded_and_redacts_context_results_and_errors \
  tests.test_dashboard.DashboardTests.test_run_detail_reads_only_the_bounded_audit_tail \
  tests.test_service.RuntimeServiceTests.test_run_detail_is_authenticated_redacted_bounded_and_read_only \
  -v
```

Loop 147 closes the authenticated per-run source-read gap without changing the
single-tenant service boundary or the public `skill2workflow-run-detail-0.1.0`
schema. Production Baseline remains directional until the remaining candidate
evidence is explicitly completed and reviewed.

### Loop 148: Recovery And State-Safety CI Gates

**Status:** Complete.

**Prior basis:** The repository already had deterministic smoke programs for
backup/restore, state migration, retention, cancellation, interrupted-run
recovery, scheduling, and service Doctor checks. They were documented for
contributors and release operators, but a pull request could pass the unit
suite and the existing security/observability/service gates while regressing
one of these state-safety boundaries.

**Outcome:** A dedicated `operational-gates` GitHub Actions job now runs all
eight recovery and state-safety drills on Python 3.14 with fresh isolated work
directories. The existing two-version unit/package/security/observability
matrix remains unchanged, and the same sequence is documented for local and
release reproduction.

**Evidence:** `tests.test_ci` locks the job name and complete smoke command
set. The eight scripts emit deterministic, secret-free evidence and were run
successfully against this commit alongside the full test suite. Contributor
and release guides identify the exact commands and their boundaries.

**Safety boundary:** This gate is local deterministic evidence only. It does
not access live providers or credentials, install a service manager, claim
hosted disaster recovery, guarantee exactly-once delivery, or replace target
host verification.

The focused evidence command is:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ci -v
python3 scripts/backup_restore_smoke.py --work-dir /tmp/skill2workflow-backup-loop148
python3 scripts/state_upgrade_smoke.py --work-dir /tmp/skill2workflow-state-upgrade-loop148
python3 scripts/retention_smoke.py --work-dir /tmp/skill2workflow-retention-loop148
python3 scripts/cancellation_smoke.py --work-dir /tmp/skill2workflow-cancellation-loop148
python3 scripts/interrupted_recovery_smoke.py --work-dir /tmp/skill2workflow-interrupted-loop148
python3 scripts/schedule_smoke.py --work-dir /tmp/skill2workflow-schedule-loop148
python3 scripts/recurring_scheduler_smoke.py --work-dir /tmp/skill2workflow-recurring-loop148
python3 scripts/service_doctor_smoke.py --work-dir /tmp/skill2workflow-doctor-loop148
```

Loop 148 makes state-safety evidence a required contribution gate without
changing Workflow DSL, storage schemas, runtime semantics, or the maturity
claim. Production Baseline remains directional until the remaining candidate
evidence is explicitly completed and reviewed.

### Loop 149: Release Artifact SPDX SBOM

**Status:** Complete.

**Prior basis:** Loop 113 made the qualified wheel independently inspectable
through a value-free archive/member manifest, but release operators still had
to translate that evidence into an inventory format understood by supply-chain
and compliance tooling. The release qualification also explicitly deferred an
SBOM.

**Outcome:** `scripts/release_sbom.py` now derives an SPDX JSON 2.3 document
from the same qualified wheel manifest. It records the fixed package metadata,
one SHA-256 checksum for every accepted wheel member, `CONTAINS`
relationships, and the archive digest binding. The package smoke writes the
public `release-artifact-sbom.json`, and a dedicated Python 3.14 CI
`artifact-gates` job repeats the isolated wheel qualification and repository
secret-hygiene scan.

**Evidence:** `tests.test_release_sbom` verifies SPDX shape, archive/member
hash correspondence, relationship coverage, atomic public writing, and
manifest safety inheritance. Package-smoke and CI contract tests lock the
artifact output and gate. The focused command is:

```bash
PYTHONPATH=src python3 -m unittest tests.test_release_sbom tests.test_package_smoke tests.test_ci -v
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-loop149
```

**Safety boundary:** The SBOM is public inventory and checksum evidence only.
It contains no source paths, contents, credentials, or workflow values and is
not a signature, key attestation, reproducible-build proof, registry upload,
hosted vulnerability scan, or maturity-gate claim. Workflow DSL, runtime,
storage, and connector behavior remain unchanged.

### Loop 150: Reproducible Release Artifact Builds

**Status:** Complete.

**Prior basis:** Loop 149 made the qualified wheel's inventory and SPDX
representation reviewable, but the release path still had no executable proof
that identical fixed inputs produced identical archive bytes. Reproducible
build claims remained explicitly deferred.

**Outcome:** `scripts/reproducible_build.py` creates a fresh build environment,
builds the current checkout twice with a fixed `SOURCE_DATE_EPOCH` and stable
locale/hash/timezone inputs, and requires both wheel bytes and release
manifests to match. It writes the public
`reproducible-build.json` evidence contract. Default release preflight and the
Python 3.14 `artifact-gates` CI job now execute the proof.

**Evidence:** `tests.test_reproducible_build` covers deterministic comparison,
atomic public evidence, and fail-closed epoch validation. The focused command
and the real double-build smoke are:

```bash
PYTHONPATH=src python3 -m unittest tests.test_reproducible_build tests.test_release_preflight tests.test_ci -v
python3 scripts/reproducible_build.py --work-dir /tmp/skill2workflow-reproducible-loop150
```

**Safety boundary:** The proof is scoped to one checkout, packaging toolchain,
Python environment, and fixed build inputs. It is not a signature, source
commit attestation, independent-builder comparison, all-platform guarantee,
registry upload, or maturity-gate claim. Workflow DSL, runtime, storage, and
connector behavior remain unchanged.

### Loop 151: Bounded Service Soak And Cutover Evidence

**Status:** Complete.

**Prior basis:** The service boundary smoke proved two graceful restarts with
one trigger per cycle, but it did not exercise repeated cutovers, durable
idempotency replay/conflict behavior, or post-restart audit diagnostics. That
left sustained operating evidence dependent on ad hoc operator testing.

**Outcome:** `scripts/service_soak_smoke.py` runs a bounded three-cycle real
process drill against one SQLite state directory. Each cycle checks health and
readiness, submits six authenticated start-to-end triggers, replays one exact
request, rejects one changed-input conflict, performs graceful `SIGTERM`, and
verifies that all persisted runs remain completed. A final cutover checks live
audit integrity and audit consistency through the authenticated service. The
operational CI gate runs the same command on Python 3.14.

**Evidence:** `tests.test_service_soak_smoke` locks option bounds, fixture
shape, public evidence permissions, and safe work-directory handling. The real
smoke command is:

```bash
PYTHONPATH=src python3 -m unittest tests.test_service_soak_smoke tests.test_ci -v
python3 scripts/service_soak_smoke.py --work-dir /tmp/skill2workflow-service-soak-loop151 --cycles 3 --triggers-per-cycle 6
```

**Safety boundary:** This is a bounded local operating drill, not a load test,
capacity target, zero-downtime guarantee, exactly-once provider claim, hosted
availability commitment, or external-side-effect reconciliation. It does not
change Workflow DSL, service routes, storage schemas, connector behavior, or
the single-tenant loopback/TLS boundary.

### Loop 152: Production Baseline Evidence Bundle

**Status:** Complete.

**Prior basis:** Loops 148-151 made the recovery, release-artifact, and
production-boundary checks individually reproducible, but a release reviewer
still had to assemble 19 commands manually and inspect separate outputs. That
made the Production Baseline evidence difficult to repeat consistently and
made accidental disclosure from a copied smoke log more likely.

**Outcome:** `scripts/production_baseline_smoke.py` runs the fixed 19-check
local suite with one owner-only work directory, a 180-second per-check limit,
and a ten-minute suite limit. Child artifacts are removed after each check.
The final `production-baseline-evidence.json` contains only fixed check names,
statuses, exit codes, and timeout flags. Release preflight accepts the explicit
`--production-baseline` switch, and release-related CI enables it.

**Evidence:** `tests.test_production_baseline_smoke` locks the fixed suite,
safe work-directory marker, child cleanup, redacted summary, failure/timeout
classification, and result normalization. The real bundle passed all 19
checks, including the full 928-test suite, package/reproducibility proofs,
state-safety drills, service boundary checks, and the three-cycle service
soak.

**Safety boundary:** This is an aggregation and release-review aid only. It
does not change Workflow DSL, runtime, storage, connector behavior, or
production maturity. It does not claim independent-builder reproducibility,
hosted availability, disaster recovery, exactly-once provider effects, or
automatic promotion of the Production Baseline gate.

### Loop 153: Authenticated Redacted Audit Event Tail

**Status:** Complete.

**Prior basis:** Remote operators could inspect one run, a bounded run/audit
consistency report, or an aggregate support bundle, but a long-running service
still required shell access to inspect the chronological audit tail. Copying
raw audit history would risk exposing trigger context, connector metadata,
credentials, and provider error text.

**Outcome:** The authenticated `GET /api/v1/audit-events` route and installed
`service-audit-events` client expose the fixed
`skill2workflow-audit-event-list-0.1.0` projection. SQLite performs exact
filtering and sequence-cursor pagination with a 100-item/64 KiB bound. The
allowlist includes only compact lifecycle, node/connector status, retry, and
approval evidence plus an error-presence flag; raw payloads and error strings
are never returned. The route is read-only, zero-body, readiness-independent,
and telemetry uses the fixed `audit_event_list` label.

**Evidence:** Storage, dashboard, service, client, CLI, telemetry, schema, and
documentation tests cover filtering, cursor continuation, authentication,
response validation, redaction, read-only behavior, and package help. The
focused command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_storage.StorageTests.test_sqlite_audit_page_filters_and_continues_with_sequence_cursor \
  tests.test_dashboard.DashboardTests.test_audit_event_page_is_cursor_paged_and_redacted \
  tests.test_service.RuntimeServiceTests.test_audit_event_page_is_authenticated_filtered_cursor_paged_and_redacted \
  tests.test_service_client.ServiceClientTests.test_audit_event_page_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_audit_events_command_prints_filtered_page -v
```

**Safety boundary:** This is a bounded incident-diagnostics projection for a
single-tenant SQLite service. It does not provide audit export, tamper repair,
full-text search, provider reconciliation, multi-tenant authorization, or a
claim of complete historical observability beyond the paged rows.

### Loop 154: Protected Remote Recurring-Schedule Creation

**Status:** Complete.

**Prior basis:** Remote operators could inventory and enable or disable durable
recurring schedules, but creating one still required shell access. A remote
creation path must not expose trigger input, reset an existing schedule's
progress on retry, or turn a malformed request into an unbounded state write.

**Outcome:** The authenticated `POST /api/v1/recurring-schedules` route and
installed `service-recurring-schedule-add` client accept the exact
`{"schedule": {...}}` wrapper and create one normalized SQLite recurring
schedule. Identical retries are idempotent no-ops with `created: false`; a
changed definition for an existing `schedule_id` returns a fixed conflict and
cannot overwrite `next_run_at` or dispatch state. The response is the fixed
`skill2workflow-recurring-schedule-create-0.1.0` redacted projection and never
returns trigger input, source, or idempotency-prefix values.

**Evidence:** `RecurringScheduleStore.add_with_result` uses one
`BEGIN IMMEDIATE` transaction to serialize create/replay decisions and update
the compact schedule summary. Service readiness, ingress authentication,
lease admission, fixed request/response bounds, audit events, client
validation, CLI help, schema, and documentation tests cover the boundary. The
focused command is:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_add_with_result_replays_identical_definition_without_resetting_state \
  tests.test_service.RuntimeServiceTests.test_recurring_schedule_create_is_authenticated_idempotent_redacted_and_audited \
  tests.test_service_client.ServiceClientTests.test_recurring_schedule_create_uses_authenticated_post_and_redacted_contract \
  tests.test_cli.CliTests.test_service_recurring_schedule_add_command_prints_create_result -v
```

**Safety boundary:** This is a protected single-tenant recurring-schedule
creation boundary. It does not add schedule update/delete, one-shot trigger
execution, workflow publication, provider exactly-once guarantees, hosted
multi-tenant authorization, or a claim that trigger payloads are safe to
return.

### Loop 155: Protected Remote Recurring-Schedule Updates

**Status:** Complete.

**Prior basis:** Loop 154 made remote recurring-schedule creation safe and
retryable, but an operator still needed shell access to change a workflow
version, interval, missed-run policy, or trigger definition. A replacement
must not accept client-supplied progress fields or silently overwrite a
concurrent dispatcher claim.

**Outcome:** `PUT /api/v1/recurring-schedules/{schedule_id}` and the installed
`service-recurring-schedule-update` client accept one complete author-owned
definition plus the last observed `expected_next_run_at`. The SQLite store
performs a compare-and-swap inside `BEGIN IMMEDIATE`, copies all durable
progress fields from the persisted row, and returns a fixed redacted response.
Identical retries are no-ops; stale progress returns a fixed `409`.

**Evidence:** [`docs/remote-schedule-update.md`](docs/remote-schedule-update.md)
defines the request, response, CAS, redaction, and retry contracts. Storage,
service, client, CLI, telemetry, schema, documentation, package, and full
suite tests cover authentication, readiness, bounded bodies, path identity,
progress preservation, stale-write rejection, audit evidence, and secret
hygiene.

**Safety boundary:** This is a protected single-tenant definition update. It
does not delete schedules, reset dispatch progress, expose trigger input,
publish workflows, or claim exactly-once provider effects.

### Loop 156: Protected Remote Recurring-Schedule Retirement

**Status:** Complete.

**Prior basis:** Loop 155 made remote definition changes safe, but an obsolete
schedule still required shell access and an operator could not retire it
without risking a concurrent claim or losing the dispatch evidence needed for
incident review.

**Outcome:** `DELETE /api/v1/recurring-schedules/{schedule_id}` and the
installed `service-recurring-schedule-delete` client require explicit
confirmation plus the last observed `expected_next_run_at`. The SQLite store
performs the compare-and-swap inside `BEGIN IMMEDIATE`, rejects enabled
schedules and active claims, deletes only the definition and compact summary,
retains dispatch history, and records a tombstone so an ambiguous retry is a
durable no-op and the ID cannot be reused.

**Evidence:** [`docs/remote-schedule-delete.md`](docs/remote-schedule-delete.md)
defines the request, response, disabled-only, history-retention, tombstone,
redaction, and retry contracts. Storage, service, client, CLI, telemetry,
schema, documentation, package, and full-suite tests cover authentication,
readiness, bounded bodies, CAS conflicts, active-claim rejection, audit
repair, replay, and secret hygiene.

**Safety boundary:** This is a protected single-tenant schedule retirement.
It does not delete dispatch evidence, cancel an in-flight provider call,
reclaim tombstones, delete one-shot schedules, publish workflows, or claim
exactly-once provider effects.

### Loop 157: CAS-Protected Remote Recurring-Schedule State Actions

**Status:** Complete.

**Prior basis:** Loop 79 made remote enable/disable actions authenticated and
idempotent, while Loops 155-156 added compare-and-swap protection to complete
definition edits and retirement. The state actions still accepted only an
empty body, so an operator acting from an old inventory could overwrite a
concurrent scheduler transition without an explicit stale-write check.

**Outcome:** The existing `POST /api/v1/recurring-schedules/{schedule_id}/enable`
and `/disable` routes retain their empty-object compatibility contract and now
also accept exactly one `expected_next_run_at` field. When present, the token
is compared inside the same `BEGIN IMMEDIATE` transaction as dispatcher claims;
stale intent returns a fixed `409`. The installed state-action clients expose
the token through `--expected-next-run-at`, while successful response and audit
schemas remain unchanged.

**Evidence:** [`docs/remote-schedule-actions.md`](docs/remote-schedule-actions.md)
defines both request forms, compatibility, stale-write behavior, and the CLI.
Storage, service, client, CLI, documentation, and full-suite tests cover
legacy empty-body callers, current-token success, stale-token conflict, null
token rejection, redaction, and serialized scheduler behavior.

**Safety boundary:** This is a protected single-tenant state transition. It
does not add bulk actions, RBAC, schedule recreation, trigger-input export,
provider cancellation, distributed locking, or exactly-once execution.

### Loop 158: Safe Remote Recurring-Schedule Patches

**Status:** Complete.

**Prior basis:** Loop 155 made full recurring-schedule definition updates
available remotely, but its complete `PUT` body requires the original trigger
input. The inventory intentionally redacts that input, so an operator could
not safely change a workflow version or interval from remote inventory alone.

**Outcome:** The authenticated `PATCH
/api/v1/recurring-schedules/{schedule_id}` route and installed
`service-recurring-schedule-patch` client accept only safe author-controlled
schedule fields (`workflow_id`, `version`, `starts_at`, `interval_seconds`,
`missed_run_policy`, and `enabled`). The service merges those fields inside the
same `BEGIN IMMEDIATE` transaction as the observed `next_run_at` CAS check,
preserves the stored trigger and all durable dispatch progress, and returns a
fixed redacted response contract.

**Evidence:** [`docs/remote-schedule-patch.md`](docs/remote-schedule-patch.md)
defines the exact request, response, rejection, redaction, and CLI contracts.
Storage, service, client, CLI, audit, telemetry, schema, documentation,
package, and full-suite tests cover authentication, stale-write conflicts,
trigger preservation, unsupported-field rejection, replay, and bounded
responses.

**Safety boundary:** This is a protected single-tenant schedule-definition
patch. It does not export trigger input, reset progress, add bulk mutation,
RBAC, distributed locking, provider cancellation, or exactly-once execution.

### Loop 159: Cursor-Paged Remote Recurring-Schedule Dispatch Diagnostics

**Status:** Complete.

**Prior basis:** Loop 80 provided a fixed recent-tail dispatch projection, but
its 100-record bound meant an operator could not inspect older failure or
uncertain evidence remotely once the dispatch table grew.

**Outcome:** The separate authenticated `GET
/api/v1/recurring-schedule-dispatch-pages` and targeted `dispatch-pages` route,
plus the installed `service-recurring-dispatch-page` client, expose a bounded
cursor page with a fixed redacted response contract. SQLite orders by
`(scheduled_for, dispatch_id)`, reads at most `max_items + 1`, and returns an
opaque cursor that walks toward older records. The original 0.1.0 recent-tail
route remains unchanged for compatibility.

**Evidence:** [`docs/remote-schedule-dispatch-pages.md`](docs/remote-schedule-dispatch-pages.md)
defines the separate schema, cursor, query, redaction, and failure contracts.
Storage, dashboard, service, client, CLI, telemetry, packaging, schema,
documentation, and full-suite tests cover global and targeted pages,
authentication, cursor continuation, bounds, and private-value exclusion.

**Safety boundary:** This is a read-only single-tenant diagnostic projection.
It does not claim scheduler ownership, export trigger input, replay or retry a
dispatch, reconcile uncertain provider effects, add bulk mutation, RBAC,
distributed locking, or exactly-once execution.

### Loop 160: Protected Redacted Remote Backup Inventory

**Status:** Complete.

**Prior basis:** The offline backup command, local inventory, retention plan,
and remote backup-readiness preflight were all available, but a running service
could not show a remote operator whether configured backup sets remained
valid, how old they were, or how much storage they consumed. Requiring shell
access for that read-only check slowed incident review and encouraged copying
private backup names into remote tooling.

**Outcome:** Service bootstrap now creates an owner-only `backups/` directory
and records the optional `runtime.backup_parent_dir` setting. The authenticated
`GET /api/v1/backup-inventory` route and installed
`service-backup-inventory` client return at most 100 entries and 64 KiB of
redacted integrity, creation-time, layout, artifact-count, file-count, and
size metadata. Existing hand-written service configurations remain valid
without the optional setting; the route fails closed until a private parent is
configured. The generated systemd unit grants that parent read-only access.

**Evidence:** [`docs/remote-backup-inventory.md`](docs/remote-backup-inventory.md)
defines the route, query, configuration, redaction, and failure contracts.
Backup, service, client, CLI, telemetry, schema, bootstrap, systemd, package,
documentation, and full-suite tests cover authentication, bounds, malformed
queries, integrity projection, name/path exclusion, optional compatibility,
and read-only behavior.

**Safety boundary:** This is a diagnostic projection only. It does not create,
delete, upload, restore, encrypt, sign, schedule, or expire backups; expose
backup names or paths; or claim disaster-recovery, multi-tenant, or
exactly-once provider guarantees.

### Loop 161: Cursor-Paged Protected Remote Backup Inventory

**Status:** Complete.

**Prior basis:** Loop 160 provided a fixed 100-entry redacted remote backup
inventory, but an operator could not inspect older backup sets after the recent
window filled.

**Outcome:** The separate authenticated `GET
/api/v1/backup-inventory-pages` route and installed
`service-backup-inventory-page` client expose bounded newest-first pages with a
URL-safe opaque cursor that walks toward older entries. The exact Loop 160
recent-window route remains unchanged for compatibility. Page responses retain
the complete total count while exporting only verification status, creation
time, layout, artifact count, file count, and size metadata.

**Evidence:** [`docs/remote-backup-inventory-pages.md`](docs/remote-backup-inventory-pages.md)
defines the fixed page schema, cursor/query bounds, redaction, authentication,
and failure contracts. Backup, service, client, CLI, telemetry, schema,
packaging, documentation, and full-suite tests cover continuation, malformed
cursors, response limits, and private-value exclusion.

**Safety boundary:** This is a read-only single-tenant diagnostic projection.
It does not create, delete, upload, restore, encrypt, sign, schedule, or expire
backups; expose names or paths; or claim disaster-recovery, multi-tenant, or
exactly-once provider guarantees.

### Loop 162: Protected Remote Backup Retention Planning

**Status:** Complete.

**Prior basis:** Loop 161 let remote operators inspect every configured backup
set through cursor-paged redacted inventory, but it still required shell access
to determine whether a fixed expiration policy was complete and how many bytes
were eligible beyond the minimum-valid-backup floor.

**Outcome:** The authenticated `POST /api/v1/backup-retention-plan` route and
installed `service-backup-retention-plan` client reuse the local normalized
backup-retention policy and bounded complete-inventory check. The response is
the fixed `skill2workflow-remote-backup-retention-plan-0.1.0` aggregate: it
reports policy binding, completeness, counts, and eligible/preserved byte
totals, while never exporting backup names, paths, per-set reasons, manifests,
workflow values, or credentials. Incomplete inventories fail closed as
`blocked` with null summary values; the route never mutates backups.

**Evidence:** [`docs/remote-backup-retention-plan.md`](docs/remote-backup-retention-plan.md)
defines the exact policy envelope, redaction, fixed errors, request/response
bounds, and operator sequence. Backup, service, client, CLI, telemetry,
schema, documentation, package, and full-suite tests cover authentication,
normalization, aggregate output, truncation blocking, response limits,
private-value exclusion, and read-only behavior.

**Safety boundary:** This is a read-only single-tenant review aid. It does not
delete, rename, upload, restore, encrypt, sign, schedule, replicate, or
automatically expire backups; the local complete-inventory plan remains the
authoritative pre-action check.

### Loop 163: Bounded Remote Backup Retention Scanning

**Status:** Complete.

**Prior basis:** Loop 162 failed closed when more than 1,000 backup sets were
present, but the retention preflight still enumerated the entire direct-child
directory before it could report that block. A very large or hostile backup
 parent could therefore consume unbounded filesystem traversal for a result
 that was already known to be unusable.

**Outcome:** The local and authenticated remote retention-plan paths now stop
after the first over-budget directory. The existing `inventory_truncated`
 response, aggregate fields, redaction boundary, and no-delete semantics are
 unchanged; the bounded inventory's total is treated as a lower bound only
 when the internal scan guard trips. Ordinary `backup-list` and cursor-paged
 inventory callers retain their complete-count and paging behavior.

**Evidence:** Backup regression coverage creates an over-budget parent and
 proves the retention inventory stops at `limit + 1`; existing local, remote,
 service, client, CLI, schema, package, and full-suite tests retain the public
 contract and redaction guarantees.

**Safety boundary:** This bounds retention-plan directory enumeration only. It
 does not change backup creation, verification, restore, remote inventory
 paging, expiration, deletion, upload, replication, or disaster-recovery
 guarantees.

### Loop 164: Lazy Bounded One-Shot Schedule Discovery

**Status:** Complete.

**Prior basis:** Loop 129 bounded the number of one-shot and recurring side
 effects per manual drain, and Loop 126 added a compact local schedule
 inventory. The one-shot implementation still sorted the complete schedule
 directory before applying a batch limit, so a large local directory could
 materialize every path even when the operator requested one record.

**Outcome:** Bounded one-shot due selection now enumerates schedule files
 lazily, retains at most the requested number of full definitions, and returns
 the earliest normalized `(run_at, schedule.id)` records. The compact
 `schedules --limit` projection also avoids materializing the complete path
 list. Complete `schedules`, unbounded due-run behavior, and all recurring
 SQLite dispatch semantics remain unchanged.

**Evidence:** Schedule regression coverage rejects path sorting during bounded
 due discovery and compact inventory, proves timestamp/id ordering, and keeps
 the existing due-run budget and value-free projection contracts. Full suite,
 package, production-baseline, and secret-hygiene evidence retain the public
 CLI and documentation boundaries.

**Safety boundary:** This bounds local schedule-discovery memory only. It does
 not change workflow execution, trigger input limits, recurring schedule
 leases, dispatch claims, distributed scheduling, or complete-list
 compatibility paths.

### Loop 165: Bounded One-Shot Schedule Document Reads

**Status:** Complete.

**Prior basis:** Loop 164 made one-shot schedule directory discovery lazy and
bounded the number of retained definitions, but every discovered JSON file was
still read with an unbounded `read_text` call. A corrupted or hostile local
schedule could therefore force excessive parser memory before the existing
1 MiB trigger-input validation ran.

**Outcome:** One-shot schedule save, lookup, complete listing, compact bounded
inventory, and due-run discovery now share a fixed 2 MiB UTF-8 document bound.
The reader rejects a file that is already oversized and re-checks the bounded
read window so a file growing between `stat` and `open` cannot bypass the
parser boundary. Existing schedule normalization, trigger-input limits,
complete-list behavior, and recurring SQLite scheduling remain unchanged.

**Evidence:** Schedule regression coverage writes an oversized otherwise-valid
document and proves every one-shot read surface fails closed before
normalization. The focused schedule suite, full suite, package, production
baseline, and secret-hygiene gates retain the public CLI and documentation
contracts.

**Safety boundary:** This bounds local one-shot JSON parsing only. It does not
change trigger input semantics, recurring schedule storage, workflow
execution, provider effects, directory enumeration, or distributed
scheduling.

### Loop 166: Bounded CLI JSON Document Inputs

**Status:** Complete.

**Prior basis:** The runtime's service bodies, trigger inputs, credentials,
and one-shot schedules had explicit read limits, but generic JSON files passed
to the local CLI still used an unbounded `read_text` call. A malformed or
hostile workflow, policy, LiteGraph, or run-state file could therefore consume
unbounded memory before schema validation or the command's normal error path.

**Outcome:** The shared CLI JSON loader now accepts at most 8 MiB of UTF-8
bytes, checks the size before opening, reads at most one byte beyond the limit,
and rechecks the window to catch file growth between those operations. The
public `main` boundary converts uncaught operator-input `OSError`, decoding,
and JSON/value failures into exit status `1` without a traceback. Existing
domain-specific trigger, schedule, and service-body limits remain stricter.

**Evidence:** CLI regression coverage proves an oversized workflow is rejected
before validation, emits a fixed size error, and does not print a traceback.
The focused CLI and documentation suites preserve all existing command and
Workflow DSL compatibility contracts. The exact boundary is documented in
[`docs/cli-input-boundary.md`](docs/cli-input-boundary.md).

**Safety boundary:** This bounds generic local CLI JSON parsing only. It does
not change Workflow DSL semantics, persistent state formats, service request
framing, credential handling, or introduce remote upload, multi-tenancy, or
arbitrary-size workflow execution.

### Loop 167: Descriptor-Bound Service Configuration Reads

**Status:** Complete.

**Prior basis:** The systemd unit generator already required a bounded,
private service configuration, but the actual `service` and `service-doctor`
startup path still used an unbounded `read_text` call. A replaced, symlinked,
or unexpectedly large configuration could therefore bypass the runtime's
startup safety boundary.

**Outcome:** Runtime configuration loading now accepts at most 64 KiB,
rejects symlinks and non-regular files, checks size before opening, binds the
descriptor to the inspected device/inode, reads at most one byte beyond the
bound, and rechecks the path after reading. Existing versioned parsing and
hand-made configuration compatibility remain unchanged; generated workspace
permissions and the operational Doctor remain separate controls.

**Evidence:** Service configuration regression coverage proves pre-open size
rejection, post-stat growth rejection, symlink rejection, path-replacement
fencing, and successful loading of the existing schema. The contract is
documented in [`docs/service-config-boundary.md`](docs/service-config-boundary.md).

**Safety boundary:** This bounds the local startup configuration read only. It
does not change service HTTP bodies, credential values, Workflow DSL
compatibility, remote configuration, encryption, or multi-tenant behavior.

### Loop 168: Bounded Local Credential-File Reads

**Status:** Complete.

**Prior basis:** The local CLI still loaded the JSON `--credential-file` with
`Path.read_text`, even though execution-time service credentials and generic
CLI JSON inputs already had bounded descriptor-based reads. A large, linked, or
replaced local credential map could therefore bypass the local secret-input
boundary before connector execution.

**Outcome:** `load_credential_file` accepts at most 2 MiB, rejects symlinks and
non-regular files, checks the size before opening, binds the descriptor to one
device/inode, reads at most one byte beyond the bound, and rechecks the path
after reading. The existing `{"credentials": {...}}` shape remains compatible;
malformed, deeply nested, and non-UTF-8 documents fail closed without exposing
parser details.

**Evidence:** Credential regression coverage proves pre-open size rejection,
symlink rejection, path-replacement fencing, read-growth rejection, stable
shape compatibility, and value-free failures. The contract is documented in
[`docs/credential-file-boundary.md`](docs/credential-file-boundary.md).

**Safety boundary:** This bounds the local CLI credential map only. It does not
change the self-hosted service directory provider, permission-bit policy,
encryption, secret-manager integration, remote configuration, or multi-tenant
behavior.

### Loop 169: Bounded SKILL.md Authoring Inputs

**Status:** Complete.

**Prior basis:** The local JSON and credential-file inputs had bounded reads,
but the first `parse`/`compile` step still used unbounded `Path.read_text()` for
user-provided `SKILL.md` files. A large, linked, or replaced authoring source
could therefore bypass the input boundary before Skill IR construction.

**Outcome:** `parse_skill_file` accepts at most 2 MiB, rejects symlinks and
non-regular files, checks size before opening, binds the descriptor to one
device/inode, reads at most one byte beyond the bound, and rechecks the path
after reading. Existing frontmatter, checklist extraction, and source-line
mapping remain compatible for valid inputs.

**Evidence:** Parser regression coverage proves pre-open size rejection,
symlink rejection, path-replacement fencing, read-growth rejection, and the
existing parser contract. The boundary is documented in
[`docs/skill-input-boundary.md`](docs/skill-input-boundary.md).

**Safety boundary:** This bounds the local authoring source only. It does not
change Workflow DSL semantics, trigger-input limits, remote upload, arbitrary
Markdown conversion, encryption, or multi-tenant behavior.

### Loop 170: Bounded Local JSON Run-State Reads

**Status:** Complete.

**Prior basis:** The SQLite service path already uses compact run projections,
but the dependency-light JSON backend still loaded every run document through
unbounded `Path.read_text()`. A large, linked, or replaced local state file
could therefore consume unbounded memory during load, listing, or interrupted
run recovery.

**Outcome:** JSON run-state serialization is capped at 8 MiB. Save, load,
complete listing, bounded listing, and interrupted-run iteration now use the
fixed local file boundary: regular non-symlink files, no-follow descriptors,
device/inode binding, a one-byte-over-bound read window, and a post-read path
identity/size check. SQLite storage and the existing JSON state shape remain
compatible.

**Evidence:** Storage regression coverage proves oversized-write rejection,
pre-open oversized-read rejection, symlink rejection, path-replacement
fencing, and read-growth rejection. The contract is documented in
[`docs/json-run-state-boundary.md`](docs/json-run-state-boundary.md).

**Safety boundary:** This protects local JSON run-state files only. It does not
change SQLite projections, encryption, multi-process locking, service storage
requirements, remote state, or the JSON/SQLite run-state shape.

### Loop 171: Bounded Local JSON Control Index Reads

**Status:** Complete.

**Prior basis:** The dependency-light JSON run-state backend now had a fixed
file boundary, but the control-plane `workflows/index.json` registry still
used unbounded `Path.read_text()` during local operations and during the
one-time JSON-to-SQLite import. A large, linked, or replaced registry could
therefore consume unbounded memory before control-plane validation.

**Outcome:** JSON control-index serialization is capped at 8 MiB. Save, load,
and JSON-to-SQLite import use the same fixed local file boundary as run state:
regular non-symlink files, no-follow descriptors, device/inode binding, a
one-byte-over-bound read window, and post-read path identity/size checks.
Registry records and SQLite projections remain compatible.

**Evidence:** Storage regression coverage proves oversized-write rejection,
pre-open oversized-read rejection, symlink rejection, path-replacement
fencing, and read-growth rejection. The contract is documented in
[`docs/json-control-index-boundary.md`](docs/json-control-index-boundary.md).

**Safety boundary:** This protects the local JSON control index only. It does
not change workflow artifact payload limits, audit-line retention, SQLite
registry semantics, encryption, multi-process locking, or multi-tenant
behavior.

### Loop 172: Bounded Published Workflow Artifact Reads

**Status:** Complete.

**Prior basis:** Published Workflow artifacts already had a 2 MiB diagnostic
bound and registry checksum verification, but execution, immutable-artifact
rechecks, SQLite cleanup, and verified backup paths could still call
`Path.read_text()` before applying either guard. A large or path-raced artifact
could therefore consume unbounded memory before the existing integrity failure.

**Outcome:** Publication serialization and every control-plane, SQLite
publication-cleanup, and verified-backup artifact read now share a 2 MiB
UTF-8 boundary. The common reader requires a regular non-symlink file, uses
`O_NOFOLLOW` where available, binds the descriptor to one device/inode, reads
at most one byte beyond the bound, and rechecks path identity and size after
reading. Oversized publication is rejected before installation.

**Evidence:** Focused artifact-I/O, control-plane, and backup tests prove
pre-open size rejection, publication rejection, symlink/path-replacement
fencing, read-growth rejection, and backup-preflight rejection. The contract
is documented in
[`docs/published-artifact-read-boundary.md`](docs/published-artifact-read-boundary.md).

**Safety boundary:** Workflow DSL shape, canonical checksum computation,
immutable version semantics, SQLite transactions, and backup manifest shape
remain unchanged. This does not split large workflows, cap unrelated
configuration or audit documents, encrypt artifacts, or make JSON storage
multi-process safe.

### Loop 173: Bounded External Connector Result Envelopes

**Status:** Complete.

**Prior basis:** Built-in HTTP connectors already bounded request and response
payloads, but explicitly loaded external connector fixtures could return an
arbitrarily large or non-JSON `output`/metadata object. The executor would
attach that object to durable run state before the storage backend had a chance
to reject it.

**Outcome:** The external connector handoff now serializes the complete
normalized result as strict compact UTF-8 JSON and enforces a fixed 1 MiB
envelope before the result crosses into durable state. The accepted result is
round-tripped through standard JSON, rejecting custom Python objects and
non-finite numbers. Existing connector IDs, normalized fields, built-in HTTP
payloads, and dry-run behavior remain compatible.

**Evidence:** Connector regression tests prove normal external execution,
oversized result rejection, non-JSON rejection, and unchanged built-in HTTP
payload behavior. The contract is documented in
[`docs/external-connector-result-boundary.md`](docs/external-connector-result-boundary.md).

**Safety boundary:** This bounds the normalized external result handoff only.
It does not sandbox imported Python, bound provider-specific outbound I/O,
interrupt a provider request, redact business values, add package
installation, or claim exactly-once external effects.

### Loop 174: Bounded SQLite Run-State Documents

**Status:** Complete.

**Prior basis:** The dependency-light JSON run-state backend already enforced
an 8 MiB document boundary, while the recommended SQLite service backend could
write and decode an arbitrarily large complete `state_json` document. That
left workflow definitions, trigger context, accumulated events, and connector
results without one predictable production persistence ceiling.

**Outcome:** SQLite run-state inserts and updates now serialize the complete
document within a fixed 8 MiB UTF-8 bound. Full-state load, complete listing,
cancellation, deadline expiry, interrupted-run recovery, and startup summary
repair validate that bound before JSON decoding. Existing compact summary and
cursor-page projections remain read-only and avoid loading the full document
when they do not need it.

**Evidence:** Storage regression tests prove oversized write rejection and
oversized read rejection. The fixed contract is documented in
[`docs/sqlite-run-state-boundary.md`](docs/sqlite-run-state-boundary.md), and
the stability guide records the SQLite/JSON compatibility boundary.

**Safety boundary:** This caps the complete SQLite run-state document only. It
does not split or encrypt state, cap individual event rows separately, change
the Workflow DSL, or claim rollback or exactly-once provider effects.

### Loop 175: Bounded Audit Event Documents

**Status:** Complete.

**Prior basis:** Complete SQLite run-state documents were bounded, but the
control-plane audit stores still accepted arbitrarily large JSONL lines and
SQLite `payload_json` values. A malformed or oversized audit document could
therefore allocate memory during import, inspection, or integrity verification
even though routine remote projections were bounded.

**Outcome:** JSON and SQLite audit appends now serialize JSON objects within a
fixed 1 MiB UTF-8 envelope, and a batch validates every event before writing
any member. JSONL line reads use a bounded window; SQLite payload reads check
the byte bound before decoding. Existing event fields, filters, chronological
output, hash-chain result, and complete-list compatibility remain unchanged.

**Evidence:** Storage regression tests prove oversized write rejection,
atomic batch validation, and fail-closed JSONL/SQLite reads. The fixed
contract is documented in
[`docs/audit-event-boundary.md`](docs/audit-event-boundary.md), with stability
and README links kept aligned.

**Safety boundary:** This bounds local audit documents only. It does not
redact business values, change the audit schema or hash algorithm, provide
retention, add signatures, or claim exactly-once external effects.

### Loop 176: Bounded SQLite Workflow Registry Records

**Status:** Complete.

**Prior basis:** SQLite run state, audit events, JSON control indexes, and
published artifacts had fixed persistence boundaries, but the recommended
SQLite control-plane registry still decoded `workflow_versions.record_json`
without a per-record limit. A malformed or oversized row could bypass the
other local document ceilings during registry reads, alias operations, or
startup import.

**Outcome:** SQLite workflow registry records now serialize as JSON objects
within a fixed 2 MiB UTF-8 envelope. Complete and direct reads, alias
resolution, streaming diagnostics, snapshots, publication, deprecation, alias
promotion, and JSON-to-SQLite import use the same bounded encode/decode helpers.
`save_index` validates every replacement record before deleting existing rows,
and alias updates validate every changed record before the update batch.

**Evidence:** Storage regression tests prove oversized write rejection,
atomic replacement validation, and fail-closed oversized/malformed/non-object
reads. The fixed contract is documented in
[`docs/sqlite-workflow-record-boundary.md`](docs/sqlite-workflow-record-boundary.md),
with stability, README, and changelog links kept aligned.

**Safety boundary:** This caps one SQLite registry document only. It does not
cap total database size, change the Workflow DSL or artifact checksum
contract, redact metadata, add signatures, or claim exactly-once publication.

### Loop 177: Bounded SQLite Trigger-Ledger Responses

**Status:** Complete.

**Prior basis:** SQLite run state, audit events, workflow registry records, and
published artifacts had fixed persistence boundaries, but completed trigger
idempotency rows still decoded `trigger_idempotency.response_json` without a
per-response limit. A malformed or oversized replay row could bypass the other
local document ceilings and destabilize idempotency recovery.

**Outcome:** Completed SQLite trigger-ledger responses now serialize as compact
JSON objects within a fixed 64 KiB UTF-8 envelope. Claim reads validate the
stored response before returning it, and corrupt, oversized, empty, or
non-object completed rows fail closed as unresolved outcomes. Response writes
validate before the pending claim advances, so rejected documents leave the
ledger pending. Existing trigger keys, fingerprints, replay fields, and public
response schemas remain unchanged.

**Evidence:** Storage and control-plane regression tests prove oversized write
rejection before mutation, fail-closed oversized/malformed replay reads, and
stable unresolved idempotency errors. The fixed contract is documented in
[`docs/sqlite-trigger-ledger-boundary.md`](docs/sqlite-trigger-ledger-boundary.md),
with stability, README, and changelog links kept aligned.

**Safety boundary:** This caps one SQLite trigger-ledger response only. It does
not cap trigger inputs, connector payloads, total database size, retention, or
external side effects, and it does not claim exactly-once execution.

### Loop 178: Bounded Workflow Execution Explanations

**Status:** Complete.

**Prior basis:** Operators could validate, diff, publish, and trigger a
workflow, but there was no fixed pre-execution view of the graph's human gates,
connector side effects, input shape, retry policy, and timeout policy. Remote
operators therefore had to inspect full artifacts or rely on release metadata
before approving a real trigger.

**Outcome:** The local `explain` command and authenticated remote
`service-workflow-explain` client expose the fixed
`skill2workflow-workflow-explanation-0.1.0` contract. It reports only bounded
topology and policy metadata: node/edge counts, transitions, human gates,
connector id/kind/method and counts, input-property shape, retries, and
timeouts. It excludes titles, descriptions, instructions, connector URLs,
headers, bodies, mapping values, conditions, credentials, and trigger inputs.
The result is explicitly side-effect free and never invokes a connector.

**Evidence:** [`docs/workflow-explanation.md`](docs/workflow-explanation.md)
defines the local and remote contracts, fixed redaction, 64 KiB/1,000-node/
2,000-edge/128-property bounds, and operator sequence. Builder, CLI, client,
service, telemetry, schema, package-smoke, and full-suite tests cover
determinism, authentication, empty-body enforcement, redaction, bounded
responses, and read-only behavior.

**Safety boundary:** This is a review aid, not a second execution authority.
Workflow DSL remains authoritative. The plan does not validate provider
availability, resolve credentials, predict external outcomes, or claim
exactly-once effects.

### Loop 179: Side-Effect-Free Trigger Preflight

**Status:** Complete.

**Prior basis:** Loop 178 made the workflow topology and policy reviewable,
but an operator still learned whether a trigger input satisfied its schema or
HTTP request mappings only after starting a real run. That made a missing
required mapping an avoidable production failure and gave local and remote
operators no common admission contract.

**Outcome:** The local `preflight` command and authenticated remote
`service-workflow-preflight` client now validate a supplied object (or an
explicit empty-object draft) against the input contract and every built-in
HTTP request mapping. The fixed
`skill2workflow-workflow-preflight-0.1.0` report returns only counts, stable
issue codes, safe paths, connector/credential-handle counts, and per-node
mapping status. It never invokes a connector, resolves a credential, writes
state, or copies trigger values.

**Evidence:** [`docs/workflow-preflight.md`](docs/workflow-preflight.md) and
[`schemas/workflow-preflight-0.1.0.schema.json`](schemas/workflow-preflight-0.1.0.schema.json)
define the local/remote request and response contracts. Builder, CLI, service,
client, telemetry, package-smoke, documentation, and full-suite tests cover
determinism, missing mappings, input-schema errors, authentication, bounds,
redaction, and the no-side-effect boundary.

**Safety boundary:** Preflight is an admission hint, not a dry-run or a second
execution authority. It does not contact providers, inspect credential stores,
invoke external connector hooks, or predict network/provider success. Workflow
DSL and the normal trigger path remain authoritative.

### Loop 180: Portable Workflow DSL Bundles

**Status:** Complete.

**Prior basis:** Loop 179 made a real trigger safe to inspect before admission,
but sharing a validated workflow still required copying a loose JSON file and
repeating the same manual integrity and secret-hygiene checks in every
checkout. That made the open-source distribution path less reproducible than
the runtime itself.

**Outcome:** `bundle-create` writes a deterministic two-member ZIP containing
only `workflow.json` and a digest-bound `manifest.json`. `bundle-verify` reads
the archive through a regular-file/no-follow bound, rejects unsafe or oversized
members, checks the manifest digest and connector summary, revalidates the
Workflow DSL, and reruns secret hygiene without extracting or executing the
workflow. Existing output is protected from accidental overwrite unless
`--force` is explicit, and replacement is atomic.

**Evidence:** [`docs/workflow-bundles.md`](docs/workflow-bundles.md) defines the
`skill2workflow-workflow-bundle-0.1.0` manifest, fixed 8 MiB archive/2 MiB
member/4 MiB total bounds, reproducibility rules, redacted verification
report, and explicit non-goals. Bundle unit tests, CLI tests, documentation
contracts, package help checks, full-suite validation, and secret hygiene prove
the sharing boundary.

**Safety boundary:** This is a local distribution and review format. It does
not upload or install bundles, sign publishers, package source Skills or
connector code, carry credentials or runtime state, alter Workflow DSL
execution authority, or provide hosted marketplace behavior.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m unittest tests.test_bundles tests.test_bundle_docs -v
PYTHONPATH=src python3 -m skill2workflow.cli bundle-create \
  examples/workflows/approval-flow.workflow.json \
  --output /tmp/skill2workflow-approval.s2w
PYTHONPATH=src python3 -m skill2workflow.cli bundle-verify \
  /tmp/skill2workflow-approval.s2w
```

Loop 180 closes the reproducible local sharing gap while preserving the
Workflow DSL, published artifact, credential, and service contracts.

### Loop 181: Verified Local Workflow Bundle Publication

**Status:** Complete.

**Prior basis:** Loop 180 made one Workflow DSL artifact deterministic and
safe to verify, but operators still had to manually extract or copy the
workflow before publishing it into a local control plane. That duplicated the
trust decision and made the share-to-run path unnecessarily fragile.

**Outcome:** `bundle-publish` reads a bundle through the same regular-file and
size boundary, verifies the exact two-member archive, manifest digest, DSL, and
secret hygiene in memory, then hands the validated document to the existing
immutable `LocalControlPlane.publish_workflow` path. It never extracts files,
executes a workflow, resolves credentials, calls a connector, or overwrites a
different artifact for the same workflow/version.

**Evidence:** [`docs/workflow-bundles.md`](docs/workflow-bundles.md) defines the
explicit publish handoff and idempotent/conflict behavior. Bundle loader,
CLI/control-plane, documentation, package-smoke, and full-suite tests cover
valid publication, malformed/tampered rejection, SQLite storage, redaction,
and installed-wheel availability.

**Safety boundary:** This is an explicit local publication command. It does
not add remote bundle upload, marketplace discovery, hosted signing,
credential packaging, workflow execution, or migration of published service
state. Workflow DSL and the normal publication path remain authoritative.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-publish \
  /tmp/approval-flow.s2w \
  --state-dir /tmp/skill2workflow-control \
  --storage sqlite
```

### Loop 182: Value-Free Workflow Bundle Diff Review

**Status:** Complete.

**Prior basis:** Loop 181 made a verified bundle publishable locally, but
reviewers still had to publish both versions before using the existing
structural diff. That weakened the share → review → publish path and encouraged
manual inspection of workflow values.

**Outcome:** `bundle-diff` verifies both bundles, requires the same workflow
identity, and reuses the shared structural diff helper used by published
version review. The fixed `skill2workflow-workflow-bundle-diff-0.1.0` report
contains only version/status/digest metadata, changed sections, and node/edge
IDs. It is read-only and never extracts, publishes, executes, resolves
credentials, or calls connectors.

**Evidence:** [`docs/workflow-bundles.md`](docs/workflow-bundles.md) and
[`schemas/workflow-bundle-diff-0.1.0.schema.json`](schemas/workflow-bundle-diff-0.1.0.schema.json)
define the contract. Shared-helper coverage, bundle/CLI tests, mismatch and
redaction regressions, installed command help, package smoke, full-suite
validation, and release preflight prove the boundary.

**Safety boundary:** This is a local review aid, not a semantic business-risk
analyzer, approval controller, signature, remote upload path, or promotion
mechanism. Operators still choose whether to publish and promote a version.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-diff \
  /tmp/approval-flow-old.s2w \
  /tmp/approval-flow-new.s2w
```

### Loop 183: Verified Local Workflow Bundle Execution

**Status:** Complete.

**Prior basis:** Loop 182 allowed operators to review two bundles before
publication, but evaluating a received bundle still required manual extraction
or publication. That added friction and made it harder to test a workflow in a
controlled local run without changing the control-plane registry.

**Outcome:** `bundle-run` verifies the complete bundle in memory before
delegating to the existing `LocalExecutor`, JSON/SQLite run storage, retry and
timeout policy, and credential-file provider. It creates no published version,
does not move aliases, and introduces no second execution authority. Invalid
bundles fail before the run-state directory is initialized.

**Evidence:** [`docs/workflow-bundles.md`](docs/workflow-bundles.md) defines the
explicit execution boundary. CLI tests cover completed runs, SQLite state,
invalid-bundle pre-state rejection, credential/normal-executor delegation,
installed command help, package smoke, full-suite validation, and release
preflight.

**Safety boundary:** This is an explicit local execution command and can carry
the same deliberate connector side effects as `run`; it is not a sandbox,
provider reconciliation layer, published release, alias promotion, remote
upload, or exactly-once guarantee. Operators remain responsible for choosing
credentials and state directories.

The repeatable evidence command is:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-run \
  /tmp/approval-flow.s2w \
  --state-dir /tmp/skill2workflow-bundle-run \
  --storage sqlite
```

### Loop 184: Verified Workflow Bundle Input Preflight

**Status:** Complete.

**Prior basis:** Loop 183 made a received bundle executable without
publication, but workflows with trigger input still required operators to
extract the artifact or risk discovering a missing input mapping only after
execution began.

**Outcome:** `bundle-preflight` verifies a bundle in memory and reuses the
side-effect-free trigger preflight contract for optional input schema and
connector mappings. `bundle-run --input` runs that same admission check before
creating run state or resolving credentials, then passes the bounded input to
the existing executor context. A blocked report is value-free and exits
non-zero; no connector, credential, or state side effect occurs.

**Evidence:** [`docs/workflow-bundles.md`](docs/workflow-bundles.md) defines the
portable input boundary. CLI tests cover ready and blocked preflight, value
redaction, blocked-input pre-state rejection, contextual bundle execution,
installed command help, package smoke, full-suite validation, and release
preflight.

**Safety boundary:** This is an admission hint and local execution convenience,
not a second trigger/idempotency authority, provider reconciliation layer,
sandbox, or secret store. Input values still enter local run state when an
operator explicitly runs with `--input`; operators must not place credentials
or secrets in trigger input.

The repeatable evidence commands are:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-preflight \
  /tmp/approval-flow.s2w \
  --input /tmp/approval-flow-input.json \
  --format text
PYTHONPATH=src python3 -m skill2workflow.cli bundle-run \
  /tmp/approval-flow.s2w \
  --input /tmp/approval-flow-input.json \
  --state-dir /tmp/skill2workflow-bundle-run \
  --storage sqlite
```

### Loop 185: Explicit Workflow Bundle Side-Effect Consent

**Status:** Complete.

**Prior basis:** Loop 184 made Bundle input admission safe, but a connector-
bearing Bundle could still proceed from a ready preflight directly into local
execution without a distinct operator acknowledgement of external side
effects.

**Outcome:** `bundle-run` now always evaluates the verified Bundle through the
existing preflight contract and refuses connector-bearing workflows unless the
operator passes `--allow-side-effects`. The refusal occurs before run-state
creation, credential resolution, or connector transport. Approval workflows
without connector nodes remain runnable without the switch; explicit consent
preserves the existing executor and connector semantics.

**Evidence:** CLI tests cover the pre-state consent guard, an explicitly
authorized local HTTP connector run, value-free input admission, installed
command help, package smoke, full-suite validation, and release preflight.

**Safety boundary:** The switch is a per-invocation local acknowledgement, not
an approval policy, sandbox, provider reconciliation mechanism, or exactly-once
guarantee. It does not make connector effects reversible and does not authorize
credentials by itself; operators still choose the Bundle, input, credential
file, and state directory.

The repeatable guarded command is:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-run \
  /tmp/connector-flow.s2w \
  --input /tmp/connector-flow-input.json \
  --allow-side-effects \
  --state-dir /tmp/skill2workflow-bundle-run \
  --storage sqlite
```

### Loop 186: Compact Workflow Bundle Run Evidence

**Status:** Complete.

**Prior basis:** Loop 185 made side-effect consent explicit, but a successful
local Bundle run did not retain a compact indication of Bundle verification or
the consent decision for later operator diagnosis.

**Outcome:** Successful `bundle-run` executions now persist
`context.bundle_run` with only `bundle_verified` and
`side_effects_authorized` booleans. Input remains under `context.input` only
when explicitly supplied. The metadata is written through the existing
LocalExecutor state path and contains no Bundle values, credentials, or
provider payloads.

**Evidence:** CLI tests cover approval-only and explicitly authorized
connector runs, state metadata, input handling, installed command help,
package smoke, full-suite validation, and release preflight.

**Safety boundary:** This is compact local run-state metadata, not a signed
approval record, immutable audit proof, or provider reconciliation mechanism.
It does not authorize side effects; the separate `--allow-side-effects` guard
remains mandatory for connector-bearing Bundles.

Repeatable command:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-run \
  /tmp/connector-flow.s2w \
  --input /tmp/connector-flow-input.json \
  --allow-side-effects \
  --state-dir /tmp/skill2workflow-bundle-run \
  --storage sqlite
```

### Loop 187: Exact Workflow Bundle Provenance Evidence

**Status:** Complete.

**Prior basis:** Loop 186 recorded verification and side-effect consent, but
the run state did not identify which exact Bundle archive supplied the
verified Workflow DSL.

**Outcome:** Successful `bundle-run` executions now also persist the lowercase
SHA-256 digest of the exact verified archive in
`context.bundle_run.bundle_sha256`. The digest is computed during the same
bounded, descriptor-checked read that supplies the executable workflow, so the
provenance field cannot drift through a second path read. No Bundle values,
paths, credentials, or provider payloads are retained.

**Evidence:** Bundle loader tests prove the workflow and value-free report are
derived from one read, CLI tests cover approval-only and explicitly authorized
connector runs, and the installed command, package smoke, full-suite, secret
hygiene, and release-preflight checks remain green.

**Safety boundary:** The digest is an artifact fingerprint, not a signature,
attestation, approval record, or provider reconciliation mechanism. The
separate `--allow-side-effects` guard remains mandatory for connector-bearing
Bundles.

Repeatable command:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-run \
  /tmp/connector-flow.s2w \
  --input /tmp/connector-flow-input.json \
  --allow-side-effects \
  --state-dir /tmp/skill2workflow-bundle-run \
  --storage sqlite
```

### Loop 188: Structured Workflow Bundle Admission Refusals

**Status:** Complete.

**Prior basis:** Loop 187 made successful Bundle runs traceable to an exact
archive, but a missing side-effect acknowledgement still surfaced only as
human-readable stderr, forcing automation to parse prose.

**Outcome:** `bundle-run --format json` now returns a fixed,
value-free `skill2workflow-workflow-bundle-run-0.1.0` refusal report when a
connector-bearing Bundle lacks `--allow-side-effects`. The report includes
workflow identity, the verified Bundle SHA-256, the stable
`side_effect_consent_required` reason, side-effecting node count, and false
safety flags for state creation, credential resolution, connector calls, and
raw values. The default invocation keeps the existing text error and exit
code.

**Evidence:** CLI tests cover the default text compatibility path and the
structured refusal, schema/documentation tests lock the report contract, and
the installed command, package smoke, full-suite, secret-hygiene, and release
preflight checks remain green.

**Safety boundary:** The JSON report is an admission refusal, not a permit,
approval record, or execution result. It creates no state, resolves no
credentials, and calls no connector. Connector-bearing Bundles still require
the explicit `--allow-side-effects` flag.

Repeatable command:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-run \
  /tmp/connector-flow.s2w \
  --format json \
  --state-dir /tmp/skill2workflow-bundle-run
```

### Loop 189: Safe Workflow Bundle Run Summaries

**Status:** Complete.

**Prior basis:** Loop 188 made consent refusals machine-readable, but a
successful `bundle-run` still printed the complete local state by default,
which is unsuitable for automation or an operator handoff that should not
carry input and provider payloads.

**Outcome:** `bundle-run --summary` now emits the fixed,
value-free `skill2workflow-workflow-bundle-summary-0.1.0` contract. It keeps
run identity, status counters, and the three Bundle provenance fields while
omitting Workflow DSL, trigger context, node-result payloads, connector
responses, and credentials. The complete state remains available through the
existing default output for local debugging.

**Evidence:** CLI tests cover summary shape, completed status, provenance,
redaction, and default-output compatibility; schema/documentation tests lock
the contract; the isolated wheel smoke invokes the installed `bundle-run
--summary` command against SQLite and checks its schema, status, and Bundle
fingerprint; full-suite, secret-hygiene, and release-preflight checks remain
green.

**Safety boundary:** `--summary` is a redacted presentation mode, not a
retention or authorization boundary. The executor still persists its normal
state locally, and connector-bearing Bundles still require
`--allow-side-effects`.

Repeatable command:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli bundle-run \
  /tmp/approval-flow.s2w \
  --summary \
  --state-dir /tmp/skill2workflow-bundle-run
```

### Loop 190: Bounded External Connector Fixture Loading

**Status:** Complete.

**Prior basis:** The explicit local `--connector-fixture` path made reviewed
external connector code usable from `run`, `resume`, and `bundle-run`, but the
loader still delegated to a second path-based import with no source-size or
replacement boundary.

**Outcome:** `load_external_connector(path)` now accepts only one regular,
non-symbolic-link file, reads at most 2 MiB of UTF-8 source through an
`O_NOFOLLOW` descriptor where available, binds the read to the original
device/inode, detects replacement or growth, and compiles the bounded source
in memory. The default registry and long-running service remain closed to
dynamic connector loading.

**Evidence:** Focused loader tests cover regular execution, symbolic-link and
non-regular rejection, source-size and UTF-8 bounds, and syntax-error
normalization. Existing CLI fixture tests, external-connector smoke, package
smoke, full-suite, secret-hygiene, and Production Baseline evidence remain
green. The contract is documented in
[`docs/external-connector-loading-boundary.md`](docs/external-connector-loading-boundary.md).

**Safety boundary:** This bounds the local file handoff; it is not a Python
sandbox. The fixture executes with the invoking process privileges and must be
reviewed by the operator. It is unavailable to the service, remote trigger
API, automatic discovery, and package installation paths.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_external_connectors -v
```

### Loop 191: Explicit Connector Fixture Manifest Inspection

**Status:** Complete.

**Prior basis:** Loop 190 made the local fixture handoff bounded, but an
operator still had to execute a workflow or use Python directly to see the
manifest that would be registered.

**Outcome:** `connectors --connector-fixture PATH` now loads one reviewed local
fixture through the same bounded loader and prints the built-in plus external
manifests without creating state, resolving credentials, or executing a
connector. The default command keeps its existing built-in or persisted
control-plane listing behavior.

**Evidence:** CLI tests assert manifest identity and contract metadata, while
connector documentation tests, installed command help, external connector
smoke, full-suite, secret-hygiene, and release-preflight checks remain green.

**Safety boundary:** This is a read-only inspection path, not a connector
execution or installation permit. The fixture is still executable Python and
must be reviewed; service, remote trigger, automatic discovery, and package
installation paths remain closed to dynamic loading.

Repeatable command:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli connectors \
  --connector-fixture examples/connectors/local_echo_connector.py
```

### Loop 192: Bounded HTTP Query-Parameter Input Mapping

**Status:** Complete.

**Prior basis:** Loop 179 made HTTP input presence reviewable before execution,
and the existing runtime could copy input only into JSON request bodies. Common
list, filter, and pagination APIs still required a hand-written connector or
unsafe URL templating.

**Outcome:** `connector.request.input_mapping` now accepts `/query/<name>`
targets in addition to existing `/body/...` targets. Query values are limited
to strings, finite numbers, and booleans, are percent-encoded, replace an
existing parameter with the same name, and are assembled only in a runtime URL
copy. Published DSL, run state, and audit metadata remain value-free with
respect to mapped values; body mappings and all existing contracts are
unchanged.

**Evidence:** Compiler and schema tests cover the additive target contract and
invalid nested targets. HTTP connector tests cover mixed body/query execution,
existing-query replacement, scalar conversion, non-scalar rejection before
network access, binding immutability, full-suite checks, package smoke,
secret-hygiene, and release-preflight evidence.

**Safety boundary:** This is flat query-parameter mapping only. Header mapping,
URL interpolation, path templates, expressions, credential/environment/file
mapping, and provider-specific request languages remain outside the boundary.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_connectors.ConnectorTests.test_http_connector_maps_scalar_context_input_into_query_without_mutating_binding -v
```

### Loop 193: Metadata-Only HTTP Response Retention

**Status:** Complete.

**Prior basis:** The built-in HTTP connector bounded response size, but its
backward-compatible result always retained decoded response headers and body in
the node result. Enterprise workflows that only need delivery status had no
declarative way to avoid durable provider-response values.

**Outcome:** `connector.request.response_mode` now accepts `full` (the default)
or `metadata`. Metadata mode reads and validates the same fixed 1 MiB UTF-8
boundary, then retains only `status_code`, `header_count`, `body_bytes`, and
`body_discarded: true` for both successful and HTTP error responses. It does
not alter request, retry, credential, or audit contracts.

**Evidence:** Runtime tests cover successful and failed metadata projections,
raw-body absence, invalid-mode rejection before network access, compiler
validation, schema contract, full-suite, package, secret-hygiene, and
production-baseline evidence.

**Safety boundary:** This is response retention control, not provider-side
redaction, encryption, forceful cancellation, or a guarantee that a provider
never received the request. The default `full` result shape remains compatible.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_connectors.ConnectorTests.test_http_connector_metadata_response_discards_body_and_headers -v
```

### Loop 194: Fixed HTTP No-Redirect Credential Boundary

**Status:** Complete.

**Prior basis:** The built-in HTTP connector resolved credential handles into
request headers, but Python's default opener followed `3xx` responses and
replayed those headers to the redirect target. A two-server local drill
confirmed that this could move an `Authorization` value across host/port
boundaries.

**Outcome:** The connector now uses a dedicated opener that rejects every
redirect before issuing a follow-up request, returning the fixed error
`http connector redirects are disabled`. Existing non-redirect `2xx`, `4xx`,
and `5xx` result contracts remain unchanged.

**Evidence:** A real dual-server regression proves the target receives no
request and no credential header. Existing HTTP success/error, credential,
payload-boundary, metadata, full-suite, package, secret-hygiene, and
Production Baseline checks remain green. The behavior is documented in
[`docs/connectors.md`](docs/connectors.md), the compatibility contract, and
the stability boundaries.

**Safety boundary:** This is a fixed no-redirect rule, not an SSRF defense,
provider-side cancellation guarantee, or allowlist. Provider-specific
follow-up behavior requires a separately reviewed connector boundary.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_connectors.ConnectorTests.test_http_connector_rejects_redirect_before_replaying_credentials -v
```

### Loop 195: Fixed HTTP Direct-Egress Boundary

**Status:** Complete.

**Prior basis:** Loop 194 stopped redirect replay, but Python's default opener
still honored ambient `http_proxy`, `https_proxy`, and `ALL_PROXY` environment
settings. A local reproduction showed a credentialed workflow request being
received by a proxy server instead of its configured target.

**Outcome:** The built-in HTTP connector now installs an empty `ProxyHandler`
alongside its no-redirect handler. It opens the configured URL directly and
does not inherit proxy routing from the process environment. Existing direct
HTTP success/error behavior remains unchanged.

**Evidence:** A real target-plus-proxy regression sets all common proxy
environment variables and proves the target receives the request with its
credential header while the proxy receives none. Redirect, credential,
payload-boundary, metadata, full-suite, package, secret-hygiene, and
Production Baseline checks remain green. The direct-egress contract is
documented in [`docs/connectors.md`](docs/connectors.md), compatibility, and
stability boundaries.

**Safety boundary:** This is direct egress, not an SSRF defense, DNS-rebinding
defense, network firewall, or proxy implementation. Workflows that require a
proxy need a separately reviewed connector with an explicit route.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_connectors.ConnectorTests.test_http_connector_ignores_ambient_proxy_for_credentialed_request -v
```

### Loop 196: Bounded HTTP Request Metadata

**Status:** Complete.

**Prior basis:** The built-in HTTP connector bounded request and response
bodies, but URL length, method syntax, and header count/size were unbounded.
Malformed header values or ports could also escape as raw `ValueError` or
`InvalidURL` exceptions instead of the connector's normalized failure result.

**Outcome:** HTTP request metadata now has fixed URL, method, and header bounds
and rejects CR/LF/NUL injection, malformed ports, userinfo, and invalid token
syntax before network access. Request construction exceptions are normalized
to `ConnectorExecutionError`; static metadata validation occurs before
credential resolution.

**Evidence:** Focused tests cover malformed header, URL, and method inputs,
oversized URL/header envelopes, and the no-network guarantee. Existing direct
HTTP success/error, credential, redirect, proxy, payload, metadata, full-suite,
package, secret-hygiene, and Production Baseline checks remain green. The
contract is documented in [`docs/connectors.md`](docs/connectors.md),
compatibility, and stability boundaries.

**Safety boundary:** These are request-envelope and exception-normalization
limits, not an SSRF defense, DNS-rebinding defense, or provider-side request
cancellation guarantee.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_connectors.ConnectorTests.test_http_connector_normalizes_invalid_request_metadata_before_network_call \
  tests.test_connectors.ConnectorTests.test_http_connector_rejects_oversized_request_metadata_before_network_call -v
```

### Loop 197: Declarative HTTP Origin Governance

**Status:** Complete.

**Prior basis:** Direct egress and bounded request metadata made the transport
safer, but a published workflow still had no declarative way to review or
restrict which HTTP origin it could call. The runtime could not distinguish an
intended provider endpoint from an accidental destination.

**Outcome:** `connector.request.allowed_origins` now accepts up to 32 exact
`http`/`https` origins. The runtime canonicalizes scheme/host/port and rejects
non-matching destinations before resolving credential handles or opening a
socket. Omission preserves the legacy unrestricted destination behavior, while
the compiler, versioned schema, LiteGraph write-back, and docs expose the
allowlist for reviewed workflows.

**Evidence:** Runtime tests prove matching local origins succeed, mismatches
make no request and do not resolve a missing credential, malformed entries and
oversized lists fail closed, compiler/schema tests cover the additive contract,
and visual write-back preserves the allowlist. Full-suite, package,
secret-hygiene, and Production Baseline checks remain green.

**Safety boundary:** This is exact-origin governance, not a wildcard matcher,
SSRF defense, DNS-rebinding defense, IP-range policy, or network firewall.
Workflows that omit the field retain compatibility; production operators
should declare explicit origins for externally connected workflows.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_connectors.ConnectorTests.test_http_connector_enforces_exact_origin_allowlist_before_credentials -v
```

### Loop 198: Fixed HTTP Transport Error Redaction

**Status:** Complete.

**Prior basis:** Loop 197 governed which exact HTTP origins a reviewed
workflow could reach, but transport and request-body serialization exceptions
still surfaced their underlying text through `ConnectorExecutionError`. That
text can contain a provider URL, proxy/socket detail, or a representation of a
mapped value before the executor persists the failed node result.

**Outcome:** Built-in HTTP request-body serialization failures now use a fixed
value-free message. Timeout failures use `http connector timed out`, while
other `URLError` and raw socket/SSL failures use `http connector request
failed`. The existing HTTP status-result contract, retry behavior, and network
execution semantics are unchanged.

**Evidence:** Focused tests inject timeout, `URLError`, and raw `OSError`
failures containing a private marker and prove the fixed messages contain no
underlying detail. Existing timeout, HTTP status, credential, redirect, proxy,
origin-governance, full-suite, package, secret-hygiene, and Production
Baseline checks remain green. The contract is documented in
[`docs/connectors.md`](docs/connectors.md), compatibility, and stability
boundaries.

**Safety boundary:** This is connector failure-message redaction. It does not
redact intentionally retained full HTTP response bodies, add provider error
classification, cancel an already accepted remote request, or replace the
external TLS/firewall boundary.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_connectors.ConnectorTests.test_http_connector_normalizes_transport_failures_without_leaking_details -v
```

### Loop 199: External Connector Exception Boundary

**Status:** Complete.

**Prior basis:** The external connector result envelope was bounded and
round-tripped through JSON, but an explicitly loaded fixture that raised an
ordinary Python exception could bypass that result boundary. The exception
could escape the executor with provider, URL, socket, or traceback text and
leave no normalized connector failure result.

**Outcome:** `_execute_external_connector` now preserves the explicit
`ConnectorExecutionError` contract while converting every other ordinary
fixture exception into the fixed `external connector execution failed` error.
The executor therefore records the normal failed-node, retry, and audit path;
the underlying exception remains available only through Python exception
chaining inside the process and is not serialized.

**Evidence:** Direct runtime tests inject a private-marker `RuntimeError` and
assert the fixed error. A SQLite executor regression proves the failed node
and reloaded run contain only the fixed message and no marker. Existing
external result bounds, explicit credential behavior, built-in HTTP, full
suite, package, secret-hygiene, and Production Baseline checks remain green.
The contract is documented in [`docs/external-connector-result-boundary.md`](docs/external-connector-result-boundary.md), connector guidance, and stability boundaries.

**Safety boundary:** This normalizes unexpected fixture exceptions; it does
not sandbox imported Python, rewrite connector-authored `ConnectorExecutionError`
messages, cancel provider I/O, redact connector output values, or claim
exactly-once external effects.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_connectors.ConnectorTests.test_external_connector_normalizes_unexpected_executor_failures \
  tests.test_executor.ExecutorTests.test_unexpected_external_connector_failure_persists_fixed_value_free_error -v
```

### Loop 200: Service-Level HTTP Origin Upper Bound

**Status:** Complete.

**Prior basis:** Loop 197 let each reviewed workflow declare an exact HTTP
origin allowlist, but a service-wide deployment policy was still absent. A
single workflow that omitted its optional list could therefore reach any
destination permitted by the process network boundary, including when it was
started by a recurring schedule.

**Outcome:** The versioned self-hosted service configuration now accepts the
optional `runtime.http_allowed_origins` list. It is canonicalized and bounded
at startup to 32 unique exact `http`/`https` origins. The same immutable policy
is injected into the direct service control plane and the lease-owned
recurring scheduler; built-in HTTP requests must satisfy it before credential
resolution or network access, and still must satisfy any workflow-level list.
Omission preserves the existing service behavior and Workflow DSL `0.1.0`
compatibility. The policy is intentionally limited to the built-in HTTP
connector; explicitly loaded external fixtures retain their own reviewed
egress responsibility.

**Evidence:** Connector tests prove canonicalization, malformed/duplicate
rejection, matching execution, service-policy mismatch suppression before a
missing credential or network call, and intersection with the workflow list.
Service configuration tests prove startup validation and propagation to both
the HTTP control plane and recurring dispatcher. The versioned service schema,
bootstrap/service/operator guides, compatibility notes, and stability
contract document the additive field and its exact-origin safety boundary.

**Safety boundary:** This is service-level exact-origin governance, not a
wildcard matcher, SSRF or DNS-rebinding defense, IP-range firewall, proxy
policy, external-connector sandbox, or multi-tenant isolation.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_connectors.ConnectorTests.test_connector_runtime_enforces_service_origin_upper_bound_before_credentials \
  tests.test_service.ServiceConfigTests.test_load_service_config_accepts_exact_http_origin_upper_bound \
  tests.test_service.RuntimeServiceTests.test_service_http_origin_policy_is_shared_by_http_and_scheduler_execution -v
```

### Loop 201: Discoverable Service HTTP Origin Bootstrap

**Status:** Complete.

**Prior basis:** Loop 200 added a service-wide exact-origin upper bound, but a
fresh installation still required an operator to hand-edit the generated
`service.json`. That made the safe deployment path easy to miss and created a
configuration-copy risk at the first-run boundary.

**Outcome:** `service-init` now accepts repeatable
`--http-allowed-origin ORIGIN` options. Initialization validates and
canonicalizes the same bounded, duplicate-free exact-origin set used by the
runtime, writes the canonical list into the versioned service configuration,
and rejects invalid policy input before creating any workspace directories.
Existing invocations that omit the option remain byte-compatible in behavior;
the service policy itself remains optional and absent by default.

**Evidence:** Bootstrap unit tests prove canonical JSON output, invalid-origin
pre-creation failure, and repeated CLI options. The installed bootstrap and
service configuration guides now show the safe first-run command and retain
the manual-edit fallback. Full service, package, secret-hygiene, and release
preflight checks remain the acceptance gates.

**Safety boundary:** This is operator ergonomics for the existing exact-origin
service policy, not a wildcard matcher, SSRF/DNS-rebinding defense, network
firewall, secret transport, or external-connector sandbox.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service_bootstrap.ServiceBootstrapTests.test_initialize_writes_canonical_http_origin_policy \
  tests.test_service_bootstrap.ServiceBootstrapTests.test_service_init_cli_accepts_repeated_http_allowed_origin_options -v
```

### Loop 202: Durable External Connector Failure Boundary

**Status:** Complete.

**Prior basis:** Loop 199 normalized ordinary exceptions raised by external
fixtures, but a connector that deliberately raised `ConnectorExecutionError`
or returned a failed result could still place provider, URL, or response text
in run state, retry events, and control-plane audit evidence. The direct
connector API also needed to retain its existing immediate diagnostics.

**Outcome:** The executor now recognizes non-built-in connector references at
the durable boundary and replaces any failed error text with the fixed
`external connector failed` message before writing node results or emitting
connector-failure, retry, recovery, fallback, and audit projections. Direct
`ConnectorRuntime` callers retain the existing explicit exception and returned
error contract; built-in HTTP failure messages remain unchanged. The boundary
does not redact business output values or claim to sandbox connector code.

**Evidence:** Direct runtime tests prove returned external errors remain
available to immediate callers. SQLite executor tests cover returned failures,
explicit `ConnectorExecutionError`, retries, node results, and all relevant
event projections; private provider markers are absent from both in-memory and
reloaded state. External connector smoke, full suite, package, secret-hygiene,
and Production Baseline gates remain green.

**Safety boundary:** This is durable error-text redaction, not imported-Python
sandboxing, provider cancellation, output-value redaction, compensation, or
exactly-once external execution.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_connectors.ConnectorTests.test_external_connector_direct_failed_result_keeps_immediate_contract \
  tests.test_executor.ExecutorTests.test_external_connector_error_text_is_sanitized_before_durable_persistence \
  tests.test_executor.ExecutorTests.test_explicit_external_connector_error_text_is_sanitized_before_persistence -v
```

### Loop 203: Durable External Connector Metadata Boundary

**Status:** Complete.

**Prior basis:** Loop 202 fixed durable failure text, but an external fixture
could still return arbitrary provider or business strings in `output`, `audit`,
input-mapping summaries, or credential summaries. The 1 MiB envelope bounded
size and JSON shape, but not the value vocabulary persisted in local JSON or
SQLite state.

**Outcome:** The executor now projects non-built-in connector metadata before
writing node results or connector events. It retains only the fixed status and
presence vocabulary plus bounded identifier lists used by the approved
fixtures; unknown fields, invalid enum values, nested objects, and invalid
strings are dropped. Direct `ConnectorRuntime` results remain unchanged, and
built-in HTTP output compatibility is preserved.

**Evidence:** Direct runtime tests prove immediate metadata remains available.
SQLite executor tests prove malicious output/audit/input-mapping/credential
fields are absent from in-memory and reloaded state while approved metadata
and connector-event projections remain intact. The focused plan is
[`docs/superpowers/plans/2026-08-18-external-connector-durable-metadata.md`](docs/superpowers/plans/2026-08-18-external-connector-durable-metadata.md).

**Safety boundary:** This is a durable metadata projection, not imported-Python
sandboxing, provider cancellation, trigger-context rewriting, or exactly-once
external execution.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_connectors.ConnectorTests.test_external_connector_direct_metadata_keeps_immediate_contract \
  tests.test_executor.ExecutorTests.test_external_connector_metadata_is_projected_before_durable_persistence -v
```

### Loop 204: Manifest-Declared External Connector Metadata Policy

**Status:** Complete.

**Prior basis:** Loop 203 protected durable state with a fixed executor
vocabulary, but an open-source connector author had no safe way to retain a
connector-specific finite status, presence flag, or key-name list. The only
alternatives were to silently lose useful diagnostics or widen the executor
with provider-specific code.

**Outcome:** External manifests may optionally declare
`audit_contract.durable_metadata` with bounded `string_enums`, `booleans`, and
`lists` sections. Registration rejects unknown sections, invalid identifiers,
duplicate names, and oversized declarations. The executor merges only the
validated policy with the existing fixed vocabulary; input-mapping and
credential summaries remain fixed, unknown values are dropped, and direct
runtime results remain unchanged.

**Evidence:** Connector tests cover policy normalization and fail-closed
validation. Executor tests cover custom enum/boolean/list retention and
private-value exclusion across JSON and SQLite reloads. The focused plan is
[`docs/superpowers/plans/2026-08-18-external-connector-durable-metadata-policy.md`](docs/superpowers/plans/2026-08-18-external-connector-durable-metadata-policy.md).

**Safety boundary:** This is a reviewed metadata vocabulary, not arbitrary
durable-field injection, imported-Python sandboxing, provider cancellation,
credential storage, trigger-context rewriting, or exactly-once execution.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_connectors.ConnectorTests.test_manifest_declared_metadata_policy_is_bounded_and_exposed \
  tests.test_connectors.ConnectorTests.test_manifest_declared_metadata_policy_rejects_unsafe_shape \
  tests.test_executor.ExecutorTests.test_manifest_declared_external_metadata_is_projected_without_raw_values -v
```

### Loop 205: Protected Uncertain-Dispatch Reviews

**Status:** Complete.

**Prior basis:** Loop 159 gave remote operators a bounded, redacted dispatch
diagnostic surface, while Loop 43 deliberately kept recovered effects in the
`uncertain` state and refused automatic replay. Operators could inspect the
evidence, but there was no durable way to record the conclusion they reached
or to distinguish a reviewed incident from an unattended one.

**Outcome:** The SQLite dispatch ledger now accepts one explicit operator
review for an `uncertain` record, guarded by the observed `completed_at` value.
The fixed outcomes are `effect_confirmed`, `effect_not_observed`, and
`no_conclusion`. Repeating the same outcome is idempotent; a stale token or a
contradictory conclusion returns a conflict. The dispatch status remains
`uncertain`, and no review can retry, complete, cancel, or replay work. An
authenticated service route, installed local/remote CLI commands, fixed
redacted schema, bounded audit event, backup-compatible record, documentation,
and regression evidence make the human review durable without claiming
provider reconciliation or exactly-once execution.

**Evidence:** Recurring-store tests cover CAS, idempotency, contradictory
reviews, SQLite reload, and unchanged status. Service tests cover
authentication, redaction, remote persistence, replay, conflict, and audit
evidence; service-client and CLI/package checks cover the fixed contract and
installed commands. The focused design is
[`docs/remote-schedule-dispatch-reviews.md`](docs/remote-schedule-dispatch-reviews.md).

**Safety boundary:** This records operator evidence only. It does not infer
provider state, automatically retry uncertain effects, alter dispatch claims,
write trigger inputs, expose credentials, or introduce exactly-once execution.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_uncertain_dispatch_review_is_cas_idempotent_and_preserves_status \
  tests.test_service.RuntimeServiceTests.test_uncertain_dispatch_review_is_authenticated_cas_and_durable \
  tests.test_service_client.ServiceClientTests.test_recurring_dispatch_review_posts_cas_payload_and_fetches_projection -v
```

### Loop 206: Installed Static UI Launcher

**Status:** Complete.

**Prior basis:** The repository already shipped a LiteGraph editor and a
control-plane inspector, but wheel users had to return to a source checkout
and invoke a generic `http.server` command. That made the first-value path
less reproducible and left the packaged artifact without a qualified UI
surface.

**Outcome:** The installed `skill2workflow ui` command serves the editor,
control-plane inspector, and non-sensitive example assets from the wheel. It
binds only to loopback addresses, supports a bounded `--once` request for
smoke tests, and never reads runtime state, resolves credentials, or mutates
workflows. The wheel provenance manifest and SBOM now include the static
assets, and the package smoke starts the installed command with source imports
disabled before fetching `/web/index.html`.

**Evidence:** UI unit tests cover source discovery, loopback rejection, static
serving, and CLI forwarding. The isolated wheel smoke verifies the packaged
asset members, installed command help, and a real one-request server. Full
tests, secret hygiene, reproducible wheel, external connector, and Production
Baseline checks remain the release gates.

**Safety boundary:** This is a static local presentation surface. It does not
serve service state, provide authentication, add public ingress, or replace
the authenticated runtime API. Operators must keep it on loopback or place it
behind their own HTTPS boundary when widening access.

Repeatable command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui -v
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke-loop206
```

### Loop 207: Authenticated Live Control-Plane UI

**Status:** Complete.

**Prior basis:** Loop 206 made the editor and control-plane inspector
reproducible from an installed wheel, but the inspector still required an
operator to export a snapshot file before viewing a running service.

**Outcome:** The installed `skill2workflow ui` command now accepts an explicit
service origin and owner-only ingress token file. When both are configured, the
control-plane page's **Load Live Snapshot** action reaches a fixed same-origin
`/api/v1/control-snapshot` route. The UI process reads the token per request,
uses the existing bounded live snapshot client, and returns only a validated,
read-only `no-store` response. Static mode remains the default; incomplete
configuration, arbitrary paths, query parameters, redirects, invalid schemas,
and upstream failures fail closed without exposing token or provider details.

**Evidence:** UI tests cover server-side Authorization forwarding, token
non-disclosure, response headers, fixed-path behavior, loopback binding, and
complete CLI configuration. Control UI contract tests cover the live action.
The installed UI, package, reproducible-build, secret-hygiene, full-suite,
external-connector, and Production Baseline gates remain the release checks.

**Safety boundary:** This is one-team read-only presentation. It does not add
browser credential storage, arbitrary service proxying, CORS, RBAC, workflow or
run mutations, provider reconciliation, or hosted TLS. Operators must keep the
launcher on loopback or provide their own HTTPS boundary for wider access.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 208: Live Service Readiness Badge

**Status:** Complete.

**Prior basis:** Loop 207 made the installed control-plane page able to fetch
one bounded live snapshot, but a failed fetch did not distinguish static mode,
a standby or draining service, and an unavailable process.

**Outcome:** The UI process now exposes a second fixed same-origin route,
`/api/v1/service-probe`, that composes the existing unauthenticated `/healthz`
and `/readyz` contract through the bounded `service-probe` client. The scope
bar reports `ready`, `not ready`, `unavailable`, or `static mode`; the probe is
read-only, `no-store`, capped at the existing 8 KiB contract, and never proxies
arbitrary paths. Snapshot authentication and token handling remain unchanged.

**Evidence:** UI tests cover the installed proxy's fixed probe schema and
response headers. Control UI contract tests cover the readiness badge and
status mapping. The installed UI, package, reproducible-build, secret-hygiene,
full-suite, external-connector, and Production Baseline gates remain the
release checks.

**Safety boundary:** This is an operator diagnostic only. It does not add
browser credential storage, service mutations, CORS, RBAC, arbitrary proxying,
or hosted TLS. Operators must keep the launcher on loopback or provide their
own HTTPS boundary for wider access.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 209: Bounded Live Snapshot Refresh

**Status:** Complete.

**Prior basis:** Loop 208 made readiness visible, but operators still had to
click **Load Live Snapshot** repeatedly to watch a running service. Unbounded
browser polling would add avoidable load and could hide stale data semantics.

**Outcome:** The installed control-plane UI now offers an explicit
**Auto-refresh** control. When live mode is configured, it refreshes the fixed
snapshot route every 10 seconds, skips requests while the document is hidden,
coalesces overlapping requests, and stops when the operator selects an example
or file snapshot. A transient refresh failure preserves the previous valid
snapshot and marks the view unavailable instead of clearing operator evidence.
Static mode remains poll-free and disables the control.

**Evidence:** Control UI contract tests cover the fixed interval, explicit
toggle, visibility pause, and stale-data message. The full UI, package,
reproducible-build, secret-hygiene, external-connector, and Production
Baseline gates remain the release checks.

**Safety boundary:** This is a read-only browser refresh loop. It does not add
credentials to browser state, mutate service data, proxy arbitrary paths, or
claim a real-time streaming guarantee. The fixed interval and visibility guard
bound routine load; operators can disable it at any time.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_control_ui tests.test_ui -v
```

### Loop 210: Protected Live Support-Bundle Download

**Status:** Complete.

**Prior basis:** Loop 209 made live monitoring practical, but incident handoff
still required switching to the CLI and manually locating the protected
`service-support-bundle` output path.

**Outcome:** The configured live UI now exposes a **Download Support Bundle**
action backed by one fixed same-origin `/api/v1/support-bundle` route. The UI
process reuses the authenticated support-bundle client, validates the existing
redacted 128 KiB contract, emits a fixed attachment filename, and never uploads
or stores the artifact in browser application state. Static mode disables the
control; query parameters and arbitrary service paths are rejected.

**Evidence:** UI tests cover the fixed attachment response, bounded payload,
token non-disclosure, and live-only configuration. Control UI contract tests
cover the download action and route. The full UI, package, reproducible-build,
secret-hygiene, external-connector, and Production Baseline gates remain the
release checks.

**Safety boundary:** This is an explicit, read-only support handoff. It does
not add automatic upload, browser credential storage, mutations, CORS, RBAC,
arbitrary proxying, or hosted TLS. Operators remain responsible for reviewing
the redacted artifact before sharing it.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 211: Confirmation-Protected Live Human-Gate Action

**Status:** Complete.

**Prior basis:** Loop 210 made incident handoff available from the live
console, but an operator still had to leave the UI and invoke the installed
CLI to approve or reject a waiting human gate. That split the evidence view
from the controlled decision action and made the first-value journey harder
to operate.

**Outcome:** Selecting a `waiting` run in a configured live console now shows
explicit **Approve run** and **Reject run** controls. Each action requires a
browser confirmation and posts exactly one boolean decision through the fixed
same-origin `/api/v1/runs/{run_id}/resume` route. The UI process accepts only a
bounded JSON body and an ASCII `run_*` identifier, reuses the authenticated
service client and server-side token, validates the fixed response, and
refreshes the snapshot. Static, example, and file snapshots remain read-only.

**Evidence:** UI integration tests prove the fixed path, exact request body,
server-side Authorization forwarding, token non-disclosure, and response
contract. Control UI contract tests cover the waiting-run guard, explicit
confirmation, fixed POST path, and disabled/static boundary. Documentation
and the installed package contract describe the operator boundary; the full
UI, package, reproducible-build, secret-hygiene, external-connector, and
Production Baseline gates remain the release checks.

**Safety boundary:** This adds only the existing single-run human-gate resume
decision. It does not expose browser credentials, accept arbitrary paths or
run identifiers, publish workflows, cancel runs, retry effects, infer provider
state, add RBAC/CORS/hosted TLS, or claim exactly-once execution. The UI stays
loopback-only unless an operator supplies a private HTTPS boundary.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 212: Bounded Live Run-Detail Evidence

**Status:** Complete.

**Prior basis:** Loop 211 put the human-gate decision beside the live run
summary, but an operator still had to switch to the CLI to inspect the bounded
event tail before deciding. That weakened the evidence-to-decision path and
made a safe review harder to perform from the installed console.

**Outcome:** Selecting a live run now fetches the existing redacted
`skill2workflow-run-detail-0.1.0` projection through one fixed same-origin
`GET /api/v1/runs/{run_id}` route. The UI process reuses the authenticated
run-detail client and server-side token, enforces the existing 50-event/64 KiB
contract, validates the run identifier and event window in the browser, and
keeps the bounded summary visible if detail retrieval fails. No workflow
inputs, connector output, credentials, or raw errors enter the UI contract.

**Evidence:** UI integration tests prove the fixed route, bounded redacted
response, server-side Authorization forwarding, and token non-disclosure.
Control UI contract tests cover the run-detail fetch, schema/window validation,
loading/error status, and static boundary. Documentation and the installed
package contract link the detail evidence to the existing service schema; the
full UI, package, reproducible-build, secret-hygiene, external-connector, and
Production Baseline gates remain the release checks.

**Safety boundary:** This is a read-only evidence projection. It does not
proxy arbitrary paths, alter run state, append audit events, expose raw state,
store browser credentials, add pagination or RBAC, or infer provider state.
The separate Loop 211 decision route remains the only live UI mutation.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 213: Bounded Live Run Discovery

**Status:** Complete.

**Prior basis:** Loop 212 made a selected run safe to inspect, but the live
console still exposed only the newest 100-run snapshot window. Operators could
see truncation counts yet had to leave the UI and use the CLI to find an older
run before inspecting or deciding it.

**Outcome:** A truncated live Runs view now enables **Load Older Runs**. Each
explicit click reaches one fixed same-origin `/api/v1/run-page` proxy, which
uses the existing redacted `skill2workflow-run-list-0.2.0` client with a
100-item cursor page. The UI accepts only the returned opaque cursor,
deduplicates rows, caps retained live rows at 500, and keeps static/example/
file snapshots read-only. Existing run-detail and human-gate controls work on
newly discovered rows without widening their contracts.

**Evidence:** UI integration tests prove the fixed proxy path, upstream
`max_items=100` request, server-side Authorization forwarding, and token
non-disclosure. Control UI contract tests cover the explicit button, page
schema/window validation, cursor path, 500-row client bound, and static
boundary. Documentation and Roadmap evidence link the UI behavior to the
existing service run-page schema; the full UI, package, reproducible-build,
secret-hygiene, external-connector, and Production Baseline gates remain the
release checks.

**Safety boundary:** This is bounded, read-only run discovery. It does not
accept arbitrary status/workflow filters, proxy arbitrary paths, export full
state, store credentials, append audit events, or claim complete history after
the fixed 500-row client cap. The service remains the source of truth for
cursor ordering and redaction.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 214: Confirmation-Protected Live Cooperative Cancellation

**Status:** Complete.

**Prior basis:** Loop 213 completed the live list → inspect → decide read path,
but the installed console still required the operator to switch to the CLI to
request cancellation. The service already had durable cooperative cancellation;
this loop closes the live operator-control gap without adding a new execution
authority.

**Outcome:** A selected live run in `created`, `running`, or `waiting` status
now exposes **Cancel run** behind an explicit browser confirmation. The UI sends
exactly `{}` to the fixed same-origin `POST /api/v1/runs/{run_id}/cancel` route,
which forwards the existing authenticated service action with the token kept
server-side. Human-gate and cancellation actions disable each other while a
request is in flight, and a successful response refreshes the live snapshot.

**Evidence:** UI integration tests prove the fixed cancel route, exact empty
JSON body, server-side Authorization forwarding, and token non-disclosure.
Control UI contract tests cover the non-terminal guard, confirmation text,
mutual action disabling, response validation, and static/file boundary.
Documentation, package, reproducible-build, secret-hygiene, external-connector,
full-suite, and Production Baseline gates remain the release checks.

**Safety boundary:** This is a request for the existing cooperative cancellation
semantics. It does not forcefully abort an in-flight provider call, roll back an
external effect, accept arbitrary reason text or paths, rewrite terminal runs,
or reconcile provider state. Static, example, and file snapshots never expose
the mutation.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 215: Bounded Live Audit Discovery

**Status:** Complete.

**Prior basis:** Loop 214 completed the live list → inspect → decide → cancel
path, but the Audit view still exposed only the newest snapshot tail. Operators
could see that the redacted audit window was truncated yet had to leave the
installed console to inspect older evidence.

**Outcome:** A truncated live Audit view now enables **Load Older Audit**. Each
explicit click reaches one fixed same-origin `GET /api/v1/audit-page` proxy,
which reuses the existing redacted
`skill2workflow-audit-event-list-0.1.0` contract with a 100-event cursor page
and no filters. The browser validates the sequence-cursor response,
deduplicates events, and retains at most 500 live audit rows. Static, example,
and file snapshots remain read-only and never expose the control.

**Evidence:** UI integration tests prove the fixed proxy path, upstream
`max_items=100` request, server-side Authorization forwarding, and token
non-disclosure. Control UI contract tests cover the explicit button, page
schema/window validation, cursor handling, 500-row client bound, and static
boundary. Documentation and the installed package contract link the behavior
to the existing redacted audit-event schema; the full UI, package,
reproducible-build, secret-hygiene, external-connector, full-suite, and
Production Baseline gates remain the release checks.

**Safety boundary:** This is bounded, read-only audit discovery. It does not
accept browser-authored filters, proxy arbitrary paths, export raw state,
store credentials, append audit events, or claim complete history after the
fixed 500-row client cap. The service remains the source of truth for cursor
ordering and redaction.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 216: Bounded Live Recurring-Schedule Discovery

**Status:** Complete.

**Prior basis:** Loop 215 completed the live run and audit evidence path, but
the installed console still could not show whether recurring workflows were
enabled, when they would run next, or what their compact last-run outcome was.
Operators had to leave the console and use the protected CLI even though the
service already exposed a bounded redacted schedule inventory.

**Outcome:** A configured live console now exposes **Load Live Schedules** and
one fixed same-origin `GET /api/v1/recurring-schedules` proxy. The UI process
reuses the existing authenticated
`skill2workflow-recurring-schedule-list-0.1.0` contract, validates the exact
100-item response, and renders schedule status, enablement, next-run timing,
interval, missed-run policy, and compact last-run metadata. Static, example,
and file snapshots keep the control disabled.

**Evidence:** UI integration tests prove the fixed route, bounded redacted
response, server-side Authorization forwarding, `no-store`, and token
non-disclosure. Control UI contract tests cover the explicit live-only control,
schema/window validation, schedule table, and static boundary. The installed
UI guide, live-control guide, Changelog, and README link the view to the
existing service inventory contract; the full UI, package, reproducible-build,
secret-hygiene, external-connector, full-suite, and Production Baseline gates
remain the release checks.

**Safety boundary:** This is bounded, read-only schedule discovery. It does
not enable, disable, create, delete, claim, dispatch, or rewrite schedules; it
does not expose trigger inputs, scheduler lease identities, credentials,
provider payloads, arbitrary service paths, or a second execution authority.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 217: Live Production-Readiness Diagnostics

**Status:** Complete.

**Prior basis:** Loop 216 completed the live operator's schedule view, but the
installed console still reduced service health to a coarse ready/not-ready
badge. The service already exposed a bounded, value-free operational-readiness
report covering artifact consistency, audit integrity, and offline-backup
preflight, yet operators had to leave the console to inspect its blocking
reasons.

**Outcome:** A configured live console now exposes **Load Live Readiness** and
one fixed same-origin `GET /api/v1/operational-readiness` proxy. The UI process
reuses the existing authenticated
`skill2workflow-operational-readiness-0.1.0` contract, validates the exact
service/check/report shape, and renders service, workflow-artifact,
audit-integrity, offline-backup, and blocking-reason rows. Static, example, and
file snapshots keep the control disabled.

**Evidence:** UI integration tests prove the fixed route, server-side
Authorization forwarding, `no-store`, and token non-disclosure. Control UI
contract tests cover the live-only control, exact schema validation, readiness
table, and static boundary. The installed UI guide, live-control guide,
Changelog, README, and this Roadmap record the operator contract; the full UI,
package, reproducible-build, secret-hygiene, external-connector, full-suite,
and Production Baseline gates remain the release checks.

**Safety boundary:** This is bounded, read-only production-readiness
diagnostics. It does not repair artifacts, rewrite audit state, create backups,
stop the service, expose paths, workflow content, run identifiers, lease
identities, credentials, provider payloads, arbitrary service paths, or a
second execution authority.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 218: Live Published-Workflow Inventory

**Status:** Complete.

**Prior basis:** Loop 217 made production readiness actionable in the live
console, but the Registry tab still depended on the bounded control snapshot.
Operators could not reliably distinguish current published versions, aliases,
and immutable checksums when the snapshot window was truncated, even though the
service already exposed a dedicated redacted Workflow inventory contract.

**Outcome:** A configured live console now exposes **Load Live Workflows** and
one fixed same-origin `GET /api/v1/workflows` proxy. The UI process reuses the
existing authenticated `skill2workflow-workflow-inventory-0.1.0` contract,
validates the exact 100-item window and lowercase SHA-256 checksum shape, and
renders lifecycle status, aliases, and shortened checksum recognition values.
Static, example, and file snapshots keep the control disabled.

**Evidence:** UI integration tests prove the fixed route, server-side
Authorization forwarding, `no-store`, and token non-disclosure. Control UI
contract tests cover the live-only control, exact schema/window validation,
live registry table, and static boundary. The installed UI guide, live-control
guide, Changelog, README, and this Roadmap record the operator contract; the
full UI, package, reproducible-build, secret-hygiene, external-connector,
full-suite, and Production Baseline gates remain the release checks.

**Safety boundary:** This is bounded, read-only published-version discovery. It
does not publish, promote, deprecate, trigger, repair, delete, export Workflow
content or filesystem paths, expose credentials, trigger inputs, provider data,
or create a second execution authority.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 219: Live Workflow-Plan Review

**Status:** Complete.

**Prior basis:** Loop 218 made current published versions discoverable in the
live console, but an operator still had to leave the console to understand a
selected version's topology, human gates, connector side effects, retries, and
deadlines before approving a run or investigating a release.

**Outcome:** Selecting a live Registry version now enables **Review Workflow
Plan** through one fixed same-origin
`GET /api/v1/workflow-explanations/{workflow_id}/{version}` proxy. The UI
validates the existing `skill2workflow-workflow-explanation-0.1.0` contract,
including bounded nodes/edges and the side-effect-free safety flags, then
renders the redacted plan in the selection detail. Static, example, and file
snapshots keep the action disabled.

**Evidence:** UI integration tests prove exact two-component path parsing,
server-side Authorization forwarding, `no-store`, and the value-free response
boundary. Control UI contract tests cover the live-only action, exact schema
validation, and static boundary. The installed UI guide, live-control guide,
Changelog, README, and this Roadmap record the operator contract; the full UI,
package, reproducible-build, secret-hygiene, external-connector, full-suite,
and Production Baseline gates remain the release checks.

**Safety boundary:** This is bounded, read-only workflow explanation. It does
not execute, trigger, publish, promote, deprecate, repair, or mutate a
Workflow; it does not resolve credentials or invoke connectors, and it does
not expose Workflow values, instructions, artifact paths, trigger inputs, or
provider data.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 220: Live Empty-Trigger Preflight

**Status:** Complete.

**Prior basis:** Loop 219 let operators understand a selected live version's
execution plan, but the console still offered no safe way to check whether an
empty trigger would satisfy its declared input and connector mappings before a
real trigger was attempted.

**Outcome:** The selected-version review now offers **Check Empty Trigger**
through one fixed same-origin
`POST /api/v1/workflow-preflights/{workflow_id}/{version}` proxy. The UI sends
only `{}`, validates the existing
`skill2workflow-workflow-preflight-0.1.0` contract, and shows readiness,
missing-input/mapping blockers, connector counts, and issue codes. Static,
example, and file snapshots keep the action disabled.

**Evidence:** UI integration tests prove exact path parsing, exact empty-body
forwarding, server-side Authorization, `no-store`, and the value-free response
boundary. Control UI contract tests cover the live-only action and strict
schema checks. The installed UI guide, live-control guide, Changelog, README,
and this Roadmap record that no business input is accepted; the full UI,
package, reproducible-build, secret-hygiene, external-connector, full-suite,
and Production Baseline gates remain the release checks.

**Safety boundary:** This is bounded, read-only trigger admission inspection.
It does not accept or persist business input, create a run, resolve
credentials, invoke connectors, or mutate Workflow, schedule, audit, or
runtime state.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 221: Live Workflow Version Diff Review

**Status:** Complete.

**Prior basis:** Loop 220 let operators check a selected live version's empty
trigger shape and mapping readiness, but the console still offered no safe way
to compare the selected release with another version before deciding whether
to promote or trigger it.

**Outcome:** The selected-version review now offers **Compare Versions** for
another version of the same workflow through one fixed same-origin
`GET /api/v1/workflow-diffs/{workflow_id}/{from_version}/{to_version}` proxy.
The UI validates the exact `skill2workflow-workflow-diff-0.1.0` contract and
renders only changed structural sections plus bounded node/edge identifiers.
The server keeps the ingress token, caps the response at 64 KiB, and performs
no execution or mutation.

**Evidence:** UI integration tests prove exact three-component path parsing,
server-side Authorization forwarding, `no-store`, and the value-free diff
response boundary. Control UI contract tests cover same-workflow version
selection, the fixed route, and strict schema validation. The installed UI
guide, live-control guide, Changelog, README, and this Roadmap record the
operator contract; the full UI, package, reproducible-build, secret-hygiene,
external-connector, full-suite, and Production Baseline gates remain the
release checks.

**Safety boundary:** This is bounded, read-only release comparison. It does
not execute, trigger, publish, promote, deprecate, repair, or mutate a
Workflow; it does not resolve credentials or invoke connectors, and it does
not expose Workflow values, instructions, artifact paths, trigger inputs, or
provider data.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 222: Live Recurring-Dispatch Evidence

**Status:** Complete.

**Prior basis:** Loop 216 made recurring schedules visible in the live console,
but operators still had to leave the UI to inspect whether recent dispatches
completed, failed, were skipped, or became uncertain after a process/provider
boundary.

**Outcome:** Selecting a live schedule now offers **Load Dispatch Evidence**
through the fixed same-origin
`GET /api/v1/recurring-schedule-dispatch-pages/{schedule_id}` proxy. **Load
Older Dispatches** follows a fixed opaque cursor route. The browser validates
the exact `skill2workflow-recurring-schedule-dispatch-page-0.1.0` contract,
deduplicates dispatch ids, retains at most 500 records, and highlights
uncertain outcomes. The server keeps the ingress token, requests a fixed
100-item page, bounds the response at 64 KiB, and exposes no mutation route.

**Evidence:** UI integration tests prove exact schedule/cursor path parsing,
server-side Authorization forwarding, fixed upstream query construction,
`no-store`, and the redacted dispatch-page response boundary. Control UI
contract tests cover the live-only controls and strict schema validation. The
installed UI guide, live-control guide, Changelog, README, and this Roadmap
record that dispatch evidence cannot claim, replay, review, or mutate state;
the full UI, package, reproducible-build, secret-hygiene, external-connector,
full-suite, and Production Baseline gates remain the release checks.

**Safety boundary:** This is bounded, read-only dispatch inspection. It does
not claim a dispatch, replay a trigger, persist an uncertain review, mutate a
schedule, resolve credentials, invoke connectors, or expose trigger inputs,
lease identities, provider payloads, or raw errors.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 223: Live Uncertain-Dispatch Review

**Status:** Complete.

**Prior basis:** Loop 222 let operators see uncertain recurring dispatches in
the live console, but resolving the operational question still required
leaving the UI for the existing protected review client.

**Outcome:** An uncertain record now exposes **Record Review** with a browser
confirmation and a fixed outcome allowlist: `effect_confirmed`,
`effect_not_observed`, or `no_conclusion`. The UI sends only the selected
record's server-provided completion timestamp and dispatch id through the
fixed authenticated
`POST /api/v1/recurring-schedule-dispatch-reviews/{dispatch_id}` proxy. The
service reuses its existing compare-and-swap precondition and audit event;
stale or already-reviewed records fail closed. The dispatch remains
`uncertain`, and no replay or claim capability is added.

**Evidence:** UI integration tests prove exact dispatch-id path parsing,
allowlisted body construction, server-side Authorization forwarding,
`no-store`, and the redacted review response boundary. Control UI contract
tests cover confirmation controls and strict review-schema validation. The
installed UI guide, live-control guide, Changelog, README, and this Roadmap
record the non-replay safety boundary; the full UI, package,
reproducible-build, secret-hygiene, external-connector, full-suite, and
Production Baseline gates remain the release checks.

**Safety boundary:** This is an explicit operator conclusion, not a provider
reconciliation or execution command. It does not claim, replay, cancel, or
mutate a dispatch; it does not accept arbitrary reason text, credentials,
trigger inputs, lease identities, or provider payloads.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 224: Live Workflow Promotion

**Status:** Complete.

**Prior basis:** Loop 221 let operators compare published versions and Loop
220 let them check empty-trigger readiness, but the live console still forced
the final stable-alias change through a separate CLI workflow. That split made
the reviewed release path harder to follow and encouraged copying identifiers
between tools.

**Outcome:** Selecting a published live version now offers **Promote to
production** through the fixed same-origin
`POST /api/v1/workflow-promotions` proxy. The browser requires explicit
confirmation and sends only the workflow id, version, fixed `production` alias,
and the observed current alias target. The service reuses the existing
compare-and-swap promotion boundary; stale or ambiguous inventory fails closed
and the UI never accepts Workflow content, trigger input, credentials, or an
arbitrary alias.

**Evidence:** UI integration tests prove server-side Authorization forwarding,
the exact promotion body, `no-store`, and the redacted response contract.
Control UI contract tests cover the fixed route, confirmation action, and
strict schema validation. The installed UI guide, live-control guide,
Changelog, README, and this Roadmap record the operator boundary; the full UI,
package, reproducible-build, secret-hygiene, external-connector, full-suite,
and Production Baseline gates remain the release checks.

**Safety boundary:** This is a reviewed stable-alias mutation, not Workflow
publication or execution. It does not accept a Workflow document, trigger a
run, resolve credentials, invoke connectors, mutate arbitrary aliases, or
bypass the service's compare-and-swap precondition.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 225: CAS-Protected Live Workflow Deprecation

**Status:** Complete.

**Prior basis:** Loop 224 connected live production promotion to the console,
but the existing deprecation route still accepted a legacy request with no
inventory precondition. An operator acting on stale metadata could therefore
retire a version after another operator had changed its alias state.

**Outcome:** The local control plane, SQLite transaction, authenticated
service, installed client, and live UI now support an optional exact
checksum-plus-alias-set compare-and-swap guard. The legacy deprecation request
remains compatible, while protected callers fail with `409` before mutation
when the published artifact metadata or aliases differ. The live console adds
confirmation-protected **Deprecate version**, only enables it for published
versions with no active alias, keeps the ingress token server-side, refreshes
the redacted inventory after success, and leaves immutable artifacts intact.

**Evidence:** Control-plane JSON/SQLite tests cover current metadata acceptance
and stale checksum/alias rejection. Service and client tests cover the protected
request body and `409` conflict. UI integration and contract tests cover exact
server-side forwarding, response bounds, `no-store`, confirmation controls,
and strict redacted response validation. The remote-deprecation guide, service
contract, stability notes, README, Changelog, and this Roadmap document the
legacy compatibility and CAS safety boundary.

**Safety boundary:** This is a protected registry lifecycle mutation. It does
not delete artifacts, publish or promote a replacement, trigger or cancel a
run, rewrite in-flight executions, export Workflow content, resolve
credentials, or claim exactly-once external effects.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_control_plane tests.test_service tests.test_service_client \
  tests.test_ui tests.test_control_ui -v
```

### Loop 226: Confirmation-Protected Live Workflow Publication

**Status:** Complete.

**Prior basis:** The live console could inspect the redacted registry, review a
version's plan and empty trigger, compare releases, promote a reviewed version,
and deprecate an unaliased version. Publishing a newly reviewed Workflow DSL
artifact still required leaving the console for the installed CLI, breaking the
otherwise controlled lifecycle handoff.

**Outcome:** The installed live control-plane UI now exposes **Stage Workflow**
and **Publish Staged Workflow** only after a live snapshot is loaded. It reads
one local JSON document, checks the existing 1 MiB publication envelope and
safe workflow id/version before confirmation, retains it only in browser memory,
and forwards only the exact `{"workflow": <object>}` body through a fixed
same-origin route. The UI process continues to read the ingress token
server-side; the existing authenticated service validates the DSL and performs
its immutable SQLite publication transaction. The compact redacted response is
validated before the UI refreshes inventory and discards the staged document.

**Evidence:** UI integration covers exact envelope forwarding to the existing
publication route, server-side Bearer authentication, `no-store`, and strict
redacted response handling. Browser contract tests cover the staged-file bound,
confirmation flow, fixed endpoint, and no-promotion/no-execution message.
Installed UI, live-control snapshot, stability, README, Changelog, and this
Roadmap record the publication boundary.

**Safety boundary:** This adds one reviewed immutable-version publication path.
It does not make the browser a Workflow DSL authority, display the staged
document, create credentials, promote an alias, trigger execution, accept
arbitrary proxy paths, delete artifacts, provide RBAC, or claim exactly-once
external effects.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 227: Side-Effect-Free Live Workflow Release Preflight

**Status:** Complete.

**Prior basis:** Loop 226 gave the live console a bounded, confirmation-protected
immutable publication path, but full DSL validation occurred only after the
operator committed that publication. A structurally invalid staged artifact
therefore failed at the last control step, while an input-requiring artifact
could be mistakenly treated as unsuitable for publication.

**Outcome:** The installed live control-plane UI now requires **Check Staged
Workflow** before it enables publication. The fixed authenticated
`/api/v1/workflow-release-preflights` route receives the same bounded
`{"workflow": <object>}` envelope, validates the unpublished document using
the execution preflight's structural rules, and returns only a bounded,
value-free report. It neither creates an artifact nor records a workflow,
resolves credentials, or invokes a connector. Its `empty_trigger_ready` field
is informative: a document which requires trigger input remains valid to
publish after the explicit operator confirmation.

**Evidence:** Service and client tests prove authentication, malformed-body
rejection, exact fixed endpoint/envelope, no stored workflow or audit mutation,
and no raw title or input values in the result. UI-proxy tests prove that the
ingress token remains server-side and the redacted response is `no-store`.
Browser contract tests cover the staged-check control, strict schema validation,
and the publication gate. The protected
`service-workflow-release-preflight` CLI exposes the same endpoint for release
automation. Installed UI, live-control snapshot, stability, README, Changelog,
and this Roadmap record the boundary.

**Safety boundary:** This adds an authenticated validation preview only. It
does not store a draft, change the Workflow DSL authority, expose staged
content, resolve credentials, call connectors, promote an alias, trigger a
run, accept arbitrary proxy paths, provide RBAC, or claim exactly-once external
effects.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_service tests.test_service_client tests.test_ui tests.test_control_ui -v
```

### Loop 228: Confirmation-Protected Live Empty Trigger

**Status:** Complete.

**Prior basis:** The live console could review a published version and prove
that its empty trigger was ready, but the final no-input operational handoff
still required an installed CLI invocation. Any browser action must preserve
the normal trigger idempotency semantics without accepting business values or
silently starting an external effect.

**Outcome:** A selected published exact version now exposes **Start Empty
Trigger** only after its current empty preflight is ready. Following an explicit
confirmation, the browser submits only workflow id, exact version, and a
cryptographically generated opaque idempotency key to a fixed same-origin UI
route. The UI proxy fixes `source` to `live-ui` and input to `{}`, keeps the
ingress token server-side, and calls the existing protected webhook client. A
compact receipt is validated before rendering. If outcome delivery is uncertain,
the visible manual retry reuses the same in-memory idempotency key and unchanged
empty request; no automatic retry is attempted.

**Evidence:** UI-proxy tests prove fixed `/webhooks/{id}/{version}` forwarding,
server-side Bearer authentication, fixed `live-ui` source, exact empty input,
`no-store`, strict compact receipt validation, and early rejection of a body
that tries to add input. Browser contract tests cover the published-version and
ready-preflight gates, confirmation wording, receipt validation, and same-key
retry boundary. Installed UI, live-control snapshot, README, Changelog, and
this Roadmap record the scope.

**Safety boundary:** This runs only an exact published version with an empty
input after confirmation. It does not accept aliases, business payloads,
credentials, arbitrary sources or proxy paths, automatic retries, provider
reconciliation, RBAC, or exactly-once external-effect claims.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 229: Staged-Input Live Workflow Trigger

**Status:** Complete.

**Prior basis:** Loop 228 made a no-input, exactly versioned launch available
from the live console after an empty preflight, but real customer workflows
often require an explicit business input object. The console needed to support
that useful path without displaying values, treating credentials as input, or
weakening normal trigger idempotency.

**Outcome:** The workflow review now accepts one locally staged JSON object for
a selected published version. The browser retains it only in memory and limits
it to the shared 1 MiB/128-top-level-key preflight boundary. A fixed UI proxy
forwards the exact version and input to the existing authenticated preflight;
only its value-free report is rendered. After a ready result and explicit
confirmation, a second fixed proxy forwards the unchanged input to the existing
protected trigger client with source fixed to `live-ui` and a browser-generated
idempotency key. The compact receipt contains input keys, never values. Manual
uncertain-outcome retry reuses both the same staged object and key; no automatic
retry occurs.

**Evidence:** UI contract tests lock the staged-file controls, published-version
and ready-preflight gating, confirmation warning, strict receipt validation,
and same-key retry behavior. UI proxy tests prove exact field admission,
fixed-source forwarding, object input, and server-side ingress-token use;
existing remote-preflight and trigger clients validate bounds and value-free
responses. Documentation records that input is durable context and must not
contain credentials or sensitive business values.

**Safety boundary:** This adds one explicit exact-version trigger path. It does
not accept aliases, arbitrary source fields, browser credentials, arbitrary
proxy paths, automatic retry, provider reconciliation, RBAC, or any claim that
business input is secret-safe in durable run state.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 230: Live Trigger-To-Run Handoff

**Status:** Complete.

**Prior basis:** The live console could safely issue an exact-version trigger
and present its compact receipt, but an operator had to manually refresh and
search the run table before inspecting the resulting execution.

**Outcome:** Either accepted live trigger now records one validated compact
receipt for its selected workflow version. **Review Started Run** turns that
receipt into a local selection and requests the existing fixed bounded
redacted run-detail route. A background snapshot refresh keeps the handoff only
when the same session still selects the same exact version from its loaded
redacted inventory. It does not re-trigger, infer a provider outcome, or add a
new service route. Existing human-gate and cooperative-cancel controls remain
the only available run mutations.

**Evidence:** UI contract tests lock the receipt-bound handoff control and
detail call. Existing run-detail proxy tests retain the server-side-token,
fixed-path, no-body and bounded redacted-detail contracts. Documentation
records the operator sequence and explicitly excludes provider reconciliation.

**Safety boundary:** The handoff exists only for a receipt validated in the
same browser session and matching the currently selected exact workflow
version. It does not expose trigger input, accept a user-supplied run id,
change a run, bypass the existing human-gate/cancel controls, or claim the
provider outcome is reconciled.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_control_ui -v
```

### Loop 231: Local SKILL.md Editor Compilation

**Status:** Complete.

**Prior basis:** The editor could inspect existing Workflow DSL files and the
CLI could compile a `SKILL.md`, but a user working in the installed visual
authoring surface had to leave the editor and manage an intermediate file.

**Outcome:** The loopback `skill2workflow ui` process now accepts one bounded
in-memory `SKILL.md` document through a fixed local compile route, parses and
compiles it with the normal compiler, and returns one validated draft Workflow
DSL document to the editor. The browser then uses the normal graph and
allowlisted write-back path. No source file is written: generated node metadata
uses the fixed `SKILL.md` reference rather than a browser file path.

**Evidence:** Parser tests cover bounded in-memory text and preserve normal
file parsing. UI HTTP tests cover successful local compilation, a fixed source
reference, `no-store`, and rejection of extra client-selected fields. The
editor contract and authoring/install documentation lock the two-step upload
and compile interaction and distinguish it from generic static hosting.

**Safety boundary:** This is a loopback-only authoring aid. It accepts exactly
one 2 MiB Markdown string, does not persist input or output, read service
state, resolve credentials, receive an ingress token, publish, execute, or
proxy arbitrary compiler/runtime paths. It is not a secret-safe upload surface;
credentials and customer data remain forbidden in Skill files.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_parser tests.test_ui -v
```

### Loop 232: Offline Editor Asset Boundary

**Status:** Complete.

**Prior basis:** The installed editor and new local `SKILL.md` authoring path
were useful only where the browser could fetch the LiteGraph JavaScript and
stylesheet from a third-party CDN at runtime. That prevented dependable use in
air-gapped, restricted-egress, and offline self-hosted environments.

**Outcome:** The pinned LiteGraph 0.7.18 JavaScript and stylesheet now ship as
committed local assets. The editor loads only those relative paths; a vendor
record carries the upstream MIT license and exact SHA-256 digests. The installed
wheel and source static preview therefore require no runtime CDN or package
manager access.

**Evidence:** UI tests lock every local asset digest, the local relative paths,
the absence of the former CDN origin, and the vendor version record. The
installed UI and authoring guides document the offline behavior and review
process. The normal test suite, connector smoke, and secret-hygiene checks
remain green.

**Safety boundary:** Bundling a reviewed browser dependency does not make the
editor a hosted frontend or modify workflow/runtime authority. The vendor
directory is a fixed pinned asset set, not an automatic updater, package
installer, or general static asset proxy; changes require an explicit review of
the version, license, and hashes.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui -v
```

### Loop 233: Strict Local SKILL.md Source Decoding

**Status:** Complete.

**Prior basis:** The loopback compiler already rejected invalid text at its
boundary, but the browser staged source with `File.text()`. Browser replacement
decoding could change malformed UTF-8 bytes before the compiler ever saw them,
leaving the author with a draft that did not exactly represent the selected
file.

**Outcome:** The editor now reads selected Skill bytes through a fatal UTF-8
decoder before staging. A browser without that verification primitive or a file
with malformed bytes receives a visible staging failure; no replacement-decoded
text reaches the compiler. Valid text retains the existing 2 MiB bound,
in-memory-only route, fixed source reference, and no-persistence behavior.

**Evidence:** UI tests lock the fatal `TextDecoder` use, byte-buffer intake,
and absence of `File.text()` in the SKILL staging path. Existing parser and UI
HTTP tests continue to cover the service-side UTF-8 and bounded-body rejection
paths. Documentation records the source-fidelity promise and excludes this
authoring route from credential or runtime access.

**Safety boundary:** This validates only document encoding and does not make a
Skill document trustworthy or secret-safe. It does not upload files beyond the
loopback compiler request, reveal source bytes in errors, read local paths,
write an artifact, or authorize publication/execution.

Repeatable focused command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui tests.test_parser -v
```

## Rolling Loop Queue

This rolling queue is ordered. Loop 233 is complete and there is no active delivery loop; select the next Production Baseline item only after reviewing the release artifact and production-boundary CI evidence.


| Loop | Status | Goal | Exit artifact |
| --- | --- | --- | --- |
| Loop 39: Scoped Live Lark Task Connector | Complete | Explicit live `create_task` opt-in, fake-transport coverage, native provider idempotency, redaction and rollback boundaries, and one redacted real-validation evidence note |
| Loop 40: Controlled Live Connector Pilot | Complete | Paid assisted Pilot completed under the fixed live `create_task` boundary with five approved real tasks, five days, two cases, a rejection, safety exercises, and verification | Finalized redacted evidence at `docs/pilot-evidence/loop-40/`; maturity advances to Controlled Live Pilot |
| Loop 41: Self-hosted Runtime Service Boundary | Complete | Added one loopback-only long-running service entry point with versioned validated configuration and SQLite state | Health/readiness checks, graceful SIGTERM smoke, and two-process restart continuity evidence |
| Loop 42: Authenticated Ingress And Production Credentials | Complete | Require authentication by default for business routes and resolve mounted credential handles at execution time | Compact secret-free security audit evidence, rotation smoke, and a documented external TLS termination boundary |
| Loop 43: Durable Recurring Scheduling And Safe Dispatch | Complete | Persist recurring schedules with restart recovery and a defined missed-run policy | Durable dispatch records, explicit uncertain recovery, and one SQLite lease with standby takeover evidence |
| Loop 44: Verified Backup And Restore | Complete | Protect and recover the complete self-hosted SQLite state boundary without credentials | Owner-only SHA-256 manifest, integrity-checked atomic restore, and restored-service drill evidence |
| Loop 45: State Upgrade And Migration | Complete | Make state compatibility explicit and move legacy SQLite state without mutating the source | Read-only preflight, mandatory verified backup, atomic copy-on-write upgrade, rollback contract, and upgraded-service drill evidence |
| Loop 46: Runtime Observability Export | Complete | Expose bounded service telemetry without leaking business or credential values | Authenticated aggregate Prometheus text, fixed label vocabulary, safe NDJSON, and real-process drill evidence |
| Loop 47: Data Retention And Disposal | Complete | Remove expired sensitive runtime state without risking protected work or mutating the source | Fixed policy schema, aggregate plan, verified retained copy, byte-level disposal, and cutover drill evidence |
| Loop 48: Durable Cooperative Run Cancellation | Complete | Persist an operator stop decision independently from stale run snapshots and suppress future workflow progress | Authenticated route and CLI, safe-point/retry semantics, compact audit, backup/retention integration, and concurrent real-process evidence |
| Loop 49: Interrupted Run Recovery | Complete | Detect process-lost service executions without replaying an unknown external side effect | Execution tickets, lease-bound takeover, stale-writer fencing, graceful-drain exclusion, compact attention, and real `SIGKILL` evidence |
| Loop 50: Release Artifact Qualification | Complete | Prove the distributed wheel carries the production CLI and modules without source-checkout assistance | Wheel-only isolated install, scrubbed import environment, minimum command contract, Beta metadata, and release-preflight evidence |
| Loop 51: Secure Service Bootstrap | Complete | Turn an installed wheel into one ready secure service workspace without manual configuration assembly | Non-overwriting owner-only layout, generated ingress secret, compact output, installed CLI contract, and authenticated real-process drill |
| Loop 52: Installed Controlled Quickstart | Complete | Let an installed-wheel user reach a durable human-gated workflow without source examples or manual DSL assembly | Bundled Skill compilation, immutable SQLite publication, waiting/resume path, unchanged service startup, and authenticated installed-wheel journey |
| Loop 53: Operational Readiness Doctor | Complete | Diagnose whether one self-hosted service configuration can safely start without mutating its workspace | Fixed secret-free checks, shared startup guards, stable exit codes, permission and bind failure evidence, and a real CLI drill |
| Loop 54: Descriptor-bound Connector Credentials | Complete | Bind every execution-time connector credential read to one private regular file without losing atomic rotation | `0700`/`0600` enforcement, no-follow identity checks, 64 KiB bound, generic failures, and outbound suppression evidence |
| Loop 55: Authenticated Live Operator Snapshot | Complete | Expose the existing Operator artifact through a bounded authenticated service read without poll-driven state mutation | Fixed-window and byte bounds, safe token-file CLI, owner-only output, fixed telemetry, and real-process evidence |
| Loop 56: Linux systemd Supervision | Complete | Generate one least-privilege manually enabled Linux systemd unit for a secure self-hosted workspace | Non-overwrite CLI, fixed systemd sandbox, state-only write path, SIGTERM-only shutdown, target-host verification contract, and portable generator evidence |
| Loop 57: Authenticated Human-Gate Decisions | Complete | Provide one authenticated service decision route for a waiting human gate without bypassing the durable executor | Exact boolean body, waiting-only conflict, success/failure branch audit, fixed route telemetry, and real threaded-service evidence |
| Loop 58: Protected Remote Operator Action Clients | Complete | Make the existing service actions safe and ergonomic from an installed CLI | Token-file auth, origin/redirect/proxy/response bounds, exact request contracts, compact errors, and wheel help evidence |
| Loop 59: Authenticated Redacted Run Detail | Complete | Let an operator inspect one run safely before remote action | Fixed redacted schema, 50-event window, 64 KiB response bound, authenticated `service-show`, and leakage/read-only evidence |
| Loop 60: Authenticated Redacted Run Discovery | Complete | Let an operator discover candidate runs safely before inspection or remote action | Fixed redacted schema, 100-run window, 64 KiB response bound, authenticated `service-runs`, and leakage/read-only evidence |
| Loop 61: Authenticated Redacted Support Bundle | Complete | Give an operator one safe incident-handoff artifact without exporting raw state | Fixed support-bundle schema, structured aggregate observability, nested 100-run window, 128 KiB response bound, authenticated `service-support-bundle`, and 0600 output evidence |
| Loop 62: Durable SQLite Trigger Idempotency | Complete | Prevent retried service/control-plane triggers from starting duplicate runs | Atomic pre-execution claim, compact replay, fixed mismatch/unresolved conflicts, no input-value ledger, and backup/restore evidence |
| Loop 63: Bounded Active Execution Timeout | Complete | Enforce the existing workflow timeout policy at durable executor safe points | 24-hour bound validation, persisted active deadline, fixed timeout failure evidence, human-gate pause semantics, and full-suite coverage |
| Loop 64: Declarative Fallback Transitions | Complete | Preserve exhausted connector failures while routing to an explicit alternate workflow path | `on_fallback` target/edge validation, durable `node_fallback` evidence, control-plane promotion, and LiteGraph fallback slot |
| Loop 65: SQLite Audit Integrity | Complete | Make durable SQLite audit evidence independently verifiable across operation, backup/restore, and retention | `sha256-chain-v1` links, payload-free `audit-verify`, legacy-column upgrade, invalid-backup rejection, and retained-copy rechain |
| Loop 66: Bounded Trigger Inputs | Complete | Bound durable trigger context and idempotency fingerprint work consistently across all trigger entry paths | Shared 1 MiB canonical input limit, fixed oversize errors, and CLI/schedule/recurring/webhook contract tests |
| Loop 67: Declarative Trigger Input Contracts | Complete | Make published workflow business inputs explicit without breaking open-object legacy workflows | Bounded `input_schema`, publication/runtime validation, pre-idempotency rejection, fixed errors, and contract/SQLite compatibility tests |
| Loop 68: Bounded Service Request Admission | Complete | Prevent unbounded active HTTP business work while keeping liveness and readiness probes available | Fixed 16-slot process-local admission, fixed `429`/`Retry-After`, slot release, and service regression evidence |
| Loop 69: Stable Workflow Version Promotion Aliases | Complete | Let operators roll an immutable workflow release forward without editing every trigger target | Bounded alias metadata, `promote` CLI, exact-version precedence, deprecation cleanup, alias-scoped idempotency replay, and JSON/SQLite evidence |
| Loop 70: Published Artifact Integrity Verification | Complete | Refuse modified or unverifiable published artifacts before they can be inspected, promoted, triggered, or executed | Canonical registry checksum verification, fixed redacted failures, promotion side-effect suppression, and JSON/SQLite runtime tests |
| Loop 71: Reviewable Workflow Releases | Complete | Let operators inspect bounded version structure and prevent stale alias promotions | `workflow-diff` contract, structural redaction, compare-and-swap promotion precondition, and JSON/SQLite/CLI evidence |
| Loop 72: Atomic Workflow Alias Promotion | Complete | Prevent concurrent SQLite operators from overwriting a newer reviewed alias target | Transactional compare-and-swap, alias mutation, audit append, concurrent-operator test, and valid-chain evidence |
| Loop 73: Atomic Workflow Registry Mutations | Complete | Preserve concurrent immutable publication and deprecation changes with their audit evidence | Transactional single-record insert/update, exclusive artifact creation, idempotent matching publish, conflict and rollback tests |
| Loop 74: Workflow Artifact Consistency | Complete | Diagnose registry/file divergence and clean up only known-failure unregistered publication artifacts | Bounded `workflow-artifacts` report, orphan/mismatch detection, transactional artifact recheck, guarded cleanup, CLI/schema/package evidence |
| Loop 75: Run Audit Consistency | Complete | Preserve one control-plane run-audit emission and diagnose cross-database evidence gaps | Atomic audit batch, bounded `audit-consistency` report, missing/duplicate detection, CLI/schema/package evidence |
| Loop 76: Remote Run Audit Consistency | Complete | Let remote self-hosted operators inspect run/audit divergence without shell access or state mutation | Authenticated zero-write endpoint, exact bounded client contract, readiness-independent read path, telemetry/docs/package evidence |
| Loop 77: Targeted Remote Run Audit Inspection | Complete | Let operators inspect one known run beyond the global report window | Safe targeted route and CLI selection, exact report compatibility, and targeted operator evidence |
| Loop 78: Remote Recurring-Schedule Inventory | Complete | Let remote operators inspect durable schedule timing and state without shell access or mutation | Authenticated zero-write endpoint, fixed redacted schema, bounded client/CLI, telemetry/docs/package evidence |
| Loop 79: Protected Remote Recurring-Schedule Actions | Complete | Let remote operators pause or resume one durable schedule through a controlled authenticated action | Exact empty-body enable/disable routes, idempotent client/CLI, dispatcher-safe serialization, bounded audit evidence, telemetry/docs/package evidence |
| Loop 80: Remote Recurring-Schedule Dispatch Diagnostics | Complete | Let remote operators inspect bounded dispatch outcomes, including uncertain recovery, without shell access or trigger-input exposure | Authenticated global/targeted read routes, fixed redacted schema, bounded SQLite query/response, client/CLI, telemetry/docs/package evidence |
| Loop 81: Remote Workflow Artifact Consistency | Complete | Let remote operators verify published workflow files and registry consistency without shell access or content export | Authenticated zero-write report route, fixed value-free schema reuse, bounded issue/response windows, client/CLI, telemetry/docs/package evidence |
| Loop 82: Remote Backup Readiness | Complete | Let remote operators confirm SQLite layout and scheduler-lease conditions before a host-side offline backup | Authenticated zero-write readiness route, fixed redacted schema, 16 KiB response bound, client/CLI, telemetry/docs/package evidence |
| Loop 83: Remote Audit Integrity | Complete | Let remote operators verify the SQLite audit chain without shell access or event-payload export | Authenticated zero-write integrity route, fixed contract reuse, 16 KiB response bound, client/CLI, telemetry/docs/package evidence |
| Loop 84: Remote Runtime Info | Complete | Let remote operators identify package, compatibility line, state layout, lifecycle, and lease state during upgrade or rollback triage | Authenticated zero-write identity route, fixed schema, 16 KiB response bound, client/CLI, telemetry/docs/package evidence |
| Loop 85: Protected Remote Workflow Triggering | Complete | Let installed operators trigger one published workflow safely through the authenticated service without hand-built HTTP | Required idempotency key, shared input/body bounds, safe URL components, exact response validation, CLI/docs/package evidence |
| Loop 86: Protected Remote Workflow Publication | Complete | Let installed operators publish one immutable Workflow DSL version through the authenticated service without shell access | Exact bounded envelope, immutable SQLite publication, fixed redacted checksum response, client/CLI/docs/package/real-process evidence |
| Loop 87: Protected Remote Workflow Promotion | Complete | Let installed operators move one published version to a stable alias through the authenticated service without shell access | Exact bounded envelope, transactional alias CAS, idempotent no-op replay, fixed redacted summary, client/CLI/docs/package/real-process evidence |
| Loop 88: Protected Remote Workflow Diff | Complete | Let installed operators review two published versions through the authenticated service without shell access or state mutation | Exact bounded value-free diff, safe URL quoting, fixed response validation, client/CLI/docs/package/real-process evidence |
| Loop 89: Protected Local Ingress-Token Rotation | Complete | Let a self-hosted operator replace the service Bearer token without printing it or restarting the service | Atomic owner-only replacement, file-identity recheck, redacted CLI result, rotation tests, package/docs evidence |
| Loop 90: Protected Remote Workflow Deprecation | Complete | Let installed operators retire one published version through the authenticated service without deleting its immutable artifact | Exact redacted request/response, transactional status and alias removal, idempotent replay, one audit event, client/CLI/package/docs/real-process evidence |
| Loop 91: Bounded Remote Workflow Inventory | Complete | Let installed operators discover published versions before review and lifecycle actions without exporting workflow content | Exact redacted inventory, 100-item/64 KiB bounds, bounded SQLite query, zero-write service/CLI/package/docs/real-process evidence |
| Loop 92: Policy-bound Remote Retention Readiness | Complete | Let remote operators bind an approved retention policy to a safe stopped-state preflight without remote deletion or shell access | Exact policy digest, active-lease null-count blocking, quiesced aggregate counts, 64 KiB/16 KiB bounds, zero-write service/CLI/package/docs evidence |
| Loop 93: Remote Operational Readiness | Complete | Let operators consume one bounded value-free deployment/incident readiness report without bespoke endpoint stitching or lifecycle mutation | Exact aggregate service/artifact/audit/backup contract, best-effort semantics, 16 KiB bound, zero-write service/CLI/package/docs evidence |
| Loop 94: Bounded Request-Body Reads | Complete | Prevent half-open clients from holding a service handler or admission slot while an advertised body remains incomplete | Five-second body-read deadline, fixed HTTP 408 contract, real threaded-service evidence, loopback adapter parity, no workflow trigger from partial input |
| Loop 95: Deployment Service Probe | Complete | Give supervisors and cutover automation one fixed distinction between ready, not-ready, and unavailable service states without a new route | Fixed health/readiness schema, stable exit codes, no redirect/proxy use, bounded responses, no server-body disclosure, client/CLI/docs/package evidence |
| Loop 96: Exact-Length Request-Body Reads | Complete | Reject early EOF before any request body is parsed or executed | Exact `Content-Length` loop, fixed HTTP 400 incomplete-body contract, preserved 408 timeout contract, webhook/service real-process evidence, no partial trigger |
| Loop 97: Fail-Closed Service Exception Boundary | Complete | Keep unexpected service failures deterministic and non-disclosing | Fixed HTTP 503 contract, connection-abort no-second-write behavior, best-effort telemetry, forced unexpected-error threaded evidence |
| Loop 98: Lifecycle Event-Logger Isolation | Complete | Keep optional operational logging from destabilizing service lifecycle control flow | Best-effort lifecycle logging, four-state failing-logger threaded evidence, deterministic scheduler/listener cleanup, docs and full-suite coverage |
| Loop 99: Deterministic Service Teardown | Complete | Ensure startup and cleanup failures close the listener and publish a final stopped state | Nested cleanup boundary, scheduler start/stop fault injection, port-rebind evidence, preserved caller exceptions, real-process continuity |
| Loop 100: Production-Boundary CI Gates | Complete | Make existing security, observability, and restart-continuity evidence mandatory on every supported Python CI entry | CI commands, local reproduction docs, CI contract tests, and three passing real-process drills |
| Loop 101: Cross-Database Operator-Action Recovery | Complete | Reconcile durable run-state mutations with missing control-plane audit evidence without replaying execution or decisions | Safe retry semantics for resume/cancel, explicit schedule-action retry guidance, regression tests, and updated operator docs |
| Loop 102: Run-Audit Lifecycle Projection Accuracy | Complete | Prevent healthy waiting and interrupted runs from being reported as missing terminal audit evidence | Exact-once status projection, waiting/interrupted regression tests, and diagnostic documentation |
| Loop 103: Uniform Metrics Request Boundary | Complete | Keep authenticated scraper traffic on the documented zero-body service contract | Shared request-body validation, metrics regression evidence, and observability/service documentation |
| Loop 104: Startup-Shutdown Race Protection | Complete | Preserve an in-progress shutdown request during scheduler startup | Lifecycle-state guard, no-ready/no-request-loop regression test, and service boundary evidence |
| Loop 105: Atomic Lifecycle State Transitions | Complete | Preserve ready/draining decisions and ordered lifecycle events under concurrent shutdown | RLock-guarded transitions, race regression test, and service lifecycle evidence |
| Loop 106: Atomic Shutdown Admission | Complete | Reject new mutating requests after draining while preserving probes and read-only diagnostics | Lifecycle/admission critical section, pre-auth webhook rejection test, and service lifecycle evidence |
| Loop 107: Atomic Scheduler Dispatch Admission | Complete | Prevent new recurring triggers after draining while preserving in-flight uncertain-outcome semantics | Scheduler dispatch gate, shutdown race regression test, and recurring-schedule evidence |
| Loop 108: Live In-Flight Request Pressure Metrics | Complete | Expose safe live pressure at the fixed request-admission boundary without changing durable support evidence | Label-free authenticated gauge, threaded in-flight/drain regression, telemetry docs, and smoke coverage |
| Loop 109: Live Scheduler Dispatch Pressure Metrics | Complete | Expose already-admitted recurring dispatch pressure during graceful drain without changing dispatch semantics | Label-free authenticated gauge, threaded scheduler regression, observability smoke, and compatibility docs |
| Loop 110: Bounded Service Readiness Waiting | Complete | Give deployment scripts one safe bounded readiness wait without adding a route or auth surface | Installed `service-wait`, fixed probe reuse, timing/exit tests, and package smoke evidence |
| Loop 111: Prometheus Alert Starter Pack | Complete | Make the fixed service metrics actionable at first deployment without adding runtime alerting state | Operator-managed rules, fixed-vocabulary smoke, CI evidence, and alert safety docs |
| Loop 112: Grafana Dashboard Starter Pack | Complete | Give operators a consistent read-only visual view over the fixed service metrics without adding runtime state | Importable eight-panel dashboard, fixed-metric/privacy smoke, CI evidence, and dashboard safety docs |
| Loop 113: Release Artifact Provenance Manifest | Complete | Let users independently verify a qualified wheel's exact archive and member set without installing it | Atomic value-free manifest generator, package-smoke integration, hash/rejection tests, and release documentation |
| Loop 114: Bounded Connector Retry Backoff | Complete | Absorb transient connector failures without tight-loop retries while preserving the existing single-tenant, auditable execution boundary | Additive bounded `backoff_ms` DSL policy, safe-point timeout/cancellation checks, audit/local-overlay evidence, authoring support, and focused regression coverage |
| Loop 115: Bounded Global Workflow Deadline | Complete | Bound the wall-clock lifetime of one durable run, including human-gate waiting, without changing active timeout or stable remote contracts | Additive 30-day-bounded `workflow_timeout_ms`, persisted safe-point enforcement, fixed timeout evidence, late-resume suppression, compiler/schema/docs/tests |
| Loop 116: Lease-Owned Workflow Deadline Sweep | Complete | Converge expired waiting runs in the self-hosted SQLite service without resuming workflow work or losing terminal audit evidence | Lease-owned one-second sweep, atomic 256-candidate expiry, cancellation precedence, audit reconciliation, scheduler and real-running-service evidence |
| Loop 117: Filtered Cursor-Paged Run Discovery | Complete | Let operators find historical runs without unbounded state reads or direct SQLite access | Protected 0.2.0 route/CLI, status and workflow filters, opaque cursor, 100-item/64 KiB bounds, redaction and service evidence |
| Loop 118: Per-Node Active Execution Deadlines | Complete | Bound one node's active work and retry sequence without forceful provider cancellation | Bounded `timeout_ms`, fixed `node_timeout` evidence, successor suppression, human-gate pause, DSL/compiler/LiteGraph/runtime tests |
| Loop 119: Bounded Built-in HTTP Connector Payloads | Complete | Keep built-in HTTP request and response payloads from amplifying self-hosted memory or durable run state | Fixed 1 MiB request/response bound, pre-network request rejection, sentinel response read, fixed UTF-8 failure, connector regression evidence |
| Loop 120: Atomic First-Use SQLite State Initialization | Complete | Make concurrent process startup observe only a complete state-layout marker | Atomic temporary-file publication, non-overwriting marker semantics, owner-only cleanup, concurrent initialization regression evidence |
| Loop 121: Bounded Local Audit Inspection | Complete | Keep routine local audit inspection bounded on long-running instances without changing retention or compatibility | Storage-level filters, 1-1000 newest-match tail, chronological output, JSON/SQLite/CLI regression evidence |
| Loop 122: Bounded Offline Control Snapshots | Complete | Keep local operator snapshot exports bounded without changing live snapshot or complete-export compatibility | `control-snapshot --max-items`, JSON/SQLite bounded windows, aggregate totals, fixed live-option rejection, CLI/dashboard evidence |
| Loop 123: Bounded Local Run Discovery | Complete | Keep local run-summary inspection bounded without changing complete-list or remote compatibility | `runs --limit` / `control-runs --limit`, JSON/SQLite timestamp ordering, 1-1000 validation, CLI/storage evidence |
| Loop 124: Bounded Local Backup Inventory | Complete | Keep backup-parent inspection bounded and value-free without mutating or exposing backup sets | `backup-list`, newest-set selection, integrity summaries, 1-1000 validation, schema/docs/package evidence |
| Loop 125: Bounded Backup Retention Planning | Complete | Make local backup expiration reviewable without deleting recovery points or acting on an incomplete inventory | `backup-retention-plan`, explicit cutoff/minimum floor, truncation blocking, policy/plan schemas, CLI/docs/package evidence |
| Loop 126: Bounded Local Schedule Inspection | Complete | Keep local schedule and dispatch inspection bounded without exposing trigger inputs or lease identities | `schedules --limit`, `schedule-dispatches --limit`, compact newest windows, schemas/docs/package evidence |
| Loop 127: Bounded Local Workflow Inventory | Complete | Keep local published-version inspection bounded without exposing workflow content | `workflows --limit`, redacted workflow-inventory contract, newest window, CLI/docs/package evidence |
| Loop 128: Bounded Workflow Artifact Diagnostics | Complete | Keep artifact consistency issue retention bounded while preserving complete counts | Fixed 1-256 issue window, deterministic redaction, local/remote projection evidence |
| Loop 129: Bounded Due-Run Batches | Complete | Keep manual due-schedule side effects within an explicit per-invocation budget | `schedule-run-due --max-items`, SQLite claim cap, window summary, CLI/docs/package evidence |
| Loop 130: Bounded Run-Audit Inspection | Complete | Keep run-audit diagnostics bounded at the source-read boundary without changing the report contract | Count-only global scan, newest 256 summaries, direct targeted read, JSON/SQLite/control-plane/docs evidence |
| Loop 131: Streaming Workflow Artifact Diagnostics | Complete | Keep SQLite artifact diagnostics bounded at the source-read boundary without changing the report contract | Streamed registry rows, exact orphan reference checks, bounded issue window, JSON/SQLite/control-plane/docs evidence |
| Loop 132: Streaming SQLite Audit Integrity | Complete | Keep audit-chain verification bounded at the source-read boundary without changing the report contract | Count-only event total, cursor-streamed verification/rebuild, tamper/legacy/backup/remote evidence |
| Loop 133: Streaming Backup Artifact Registry Reads | Complete | Keep verified backup artifact handling bounded at the source-read boundary without changing the manifest contract | Cursor-streamed registry references, constant-size deduplication, no-`fetchall` test, backup/restore smoke and docs evidence |
| Loop 134: Streaming Stale-Claim Recovery | Complete | Keep recurring scheduler restart recovery bounded at the source-read boundary without changing uncertain-claim semantics | Cursor-streamed stale dispatch rows, no-`fetchall` test, recovery regression, scheduler smoke and docs evidence |
| Loop 135: Streaming Interrupted-Run Takeover | Complete | Keep process-loss recovery bounded at the source-read boundary without changing fencing or no-replay semantics | Cursor-streamed foreign execution rows, no-`fetchall` test, takeover/fencing regression, crash smoke and docs evidence |
| Loop 136: Streaming Workflow Alias Promotion | Complete | Keep SQLite release promotion bounded to the selected workflow without changing CAS or audit semantics | Direct target read, selected-workflow cursor, no-global-registry test, concurrent CAS evidence, package and docs evidence |
| Loop 137: Streaming Interrupted-Run Reconciliation | Complete | Keep post-takeover audit repair bounded at the source-read boundary without changing no-replay semantics | Cursor-streamed interrupted states, one-run audit existence query, no-full-enumeration test, crash smoke and docs evidence |
| Loop 138: Bounded Readiness Registry Checks | Complete | Keep live readiness probes bounded as published workflow history grows without changing complete-list compatibility | SQLite registry count check, no-materialization readiness tests, full-suite and service smoke evidence |
| Loop 139: Bounded Stable-Alias Resolution | Complete | Keep alias-trigger resolution bounded to the selected workflow without changing exact-version, ambiguity, or replay semantics | Direct version lookup, selected-workflow cursor, no-global-registry test, trigger replay regression and docs evidence |
| Loop 140: Bounded Service Dispatch Batches | Complete | Keep recurring service dispatch bounded per polling pass without changing lease or claim-before-execute semantics | Fixed 100-claim scheduler budget, dispatch regression, recurring-service smoke and docs evidence |
| Loop 141: Bounded Stale-Claim Recovery Writes | Complete | Keep service takeover write transactions bounded without changing uncertain or no-automatic-retry semantics | Fixed 100-claim recovery batches, lease-renewal regression, recurring recovery evidence and docs |
| Loop 142: Bounded Interrupted-Run Takeover Writes | Complete | Keep process-loss takeover write transactions bounded without changing fencing, audit repair, or no-replay semantics | Fixed 100-execution recovery batches, lease-renewal regression, bounded takeover evidence and docs |
| Loop 143: Bounded Interrupted-Run Audit Reconciliation | Complete | Keep startup audit repair bounded without changing audit evidence, fencing, or no-replay semantics | Fixed 100-state cursor pages, lease-renewal regression, bounded audit-repair evidence and docs |
| Loop 144: Bounded Run-Detail Audit Reads | Complete | Keep fixed run-detail diagnostics bounded at the storage boundary without changing redaction or response compatibility | Fixed 50-event audit-tail query, source-bound regression, service/client evidence and docs |
| Loop 145: Compact SQLite Run-Summary Projections | Complete | Keep bounded run discovery and audit diagnostics source-bounded without parsing complete run state documents | Transactional summary table, grouped event counts, corruption regression, backup/retention compatibility and docs |
| Loop 146: Compact SQLite Recurring-Schedule Projections | Complete | Keep bounded recurring-schedule inventory source-bounded without parsing complete definitions or trigger inputs | Transactional schedule-summary table, corruption regression, state-transition/backup compatibility and docs |
| Loop 147: Compact SQLite Run-Detail Projections | Complete | Keep authenticated per-run detail source-bounded without parsing complete state documents | Transactional value-free detail projection, corrupt-state regression, bounded event tail, backup compatibility and docs |
| Loop 148: Recovery And State-Safety CI Gates | Complete | Make deterministic recovery and state-safety evidence mandatory on every change | Dedicated Python 3.14 CI job, eight isolated smoke drills, CI contract test, contributor/release reproduction docs |
| Loop 149: Release Artifact SPDX SBOM | Complete | Make a qualified wheel's contents consumable by standard supply-chain tooling without adding runtime dependencies | SPDX 2.3 SBOM generator, package-smoke output, dedicated artifact CI gate, hash/safety tests, and release documentation |
| Loop 150: Reproducible Release Artifact Builds | Complete | Prove that fixed inputs produce identical qualified release wheels before publication | Two isolated fixed-epoch wheel builds, byte and manifest equality, public evidence, release-preflight and CI gates, tests, and documentation |
| Loop 151: Bounded Service Soak And Cutover Evidence | Complete | Prove repeated real-process cutovers preserve idempotent trigger behavior and SQLite/audit continuity | Three-cycle service soak, replay/conflict checks, graceful shutdown, authenticated audit diagnostics, operational CI gate, tests, and documentation |
| Loop 152: Production Baseline Evidence Bundle | Complete | Make the approved production-boundary evidence repeatable as one safe release-review artifact | Fixed 19-check bundle, isolated child workspaces, redacted summary schema, optional release-preflight flag, CI coverage, tests, and documentation |
| Loop 153: Authenticated Redacted Audit Event Tail | Complete | Give remote operators bounded chronological audit diagnostics without exporting sensitive payloads | Fixed redacted schema, exact filters, opaque sequence cursors, SQLite source bounds, authenticated CLI/route, leakage/read-only evidence, and documentation |
| Loop 154: Protected Remote Recurring-Schedule Creation | Complete | Let remote operators create or replay one durable recurring schedule without exposing trigger input or resetting progress | Exact wrapped POST and installed CLI, `BEGIN IMMEDIATE` replay/conflict protection, redacted response schema, authentication/readiness/lease/audit evidence, and documentation |
| Loop 155: Protected Remote Recurring-Schedule Updates | Complete | Let remote operators change one recurring definition without resetting durable dispatch progress or overwriting a concurrent claim | Exact wrapped PUT with `next_run_at` CAS, installed CLI, redacted response schema, stale-write conflict, audit evidence, and documentation |
| Loop 156: Protected Remote Recurring-Schedule Retirement | Complete | Let remote operators safely retire a disabled recurring schedule without losing dispatch evidence or deleting a reused ID | Exact confirmed DELETE with `next_run_at` CAS, disabled/no-claim guard, tombstone replay, retained dispatch history, redacted response schema, audit evidence, and documentation |
| Loop 157: CAS-Protected Remote Recurring-Schedule State Actions | Complete | Let remote enable/disable operations reject stale inventory intent without breaking legacy callers | Optional `next_run_at` CAS body, serialized state mutation, fixed `409`, installed CLI flag, compatibility tests, and documentation |
| Loop 158: Safe Remote Recurring-Schedule Patches | Complete | Let remote operators update non-sensitive schedule fields without re-supplying or exposing trigger input | Safe-field-only PATCH, `next_run_at` CAS, trigger/progress preservation, redacted response schema, installed CLI, audit/telemetry, tests, and documentation |
| Loop 159: Cursor-Paged Remote Recurring-Schedule Dispatch Diagnostics | Complete | Let remote operators inspect older dispatch evidence after the fixed recent tail is exhausted | Separate redacted page schema, opaque SQLite ordering cursor, global/targeted authenticated routes, installed CLI, source-bounded reads, compatibility preservation, tests, and documentation |
| Loop 160: Protected Redacted Remote Backup Inventory | Complete | Let remote operators inspect configured backup integrity, age, and size without shell access or private names | Optional owner-only backup parent, redacted 100-item/64 KiB route and CLI, bootstrap/systemd wiring, schema, authentication/bounds/redaction tests, and documentation |
| Loop 161: Cursor-Paged Protected Remote Backup Inventory | Complete | Let remote operators inspect older configured backup evidence beyond the fixed recent window | Separate redacted 100-item/64 KiB page route and CLI, URL-safe opaque continuation cursor, compatibility-preserving contract, authentication/bounds/redaction tests, and documentation |
| Loop 162: Protected Remote Backup Retention Planning | Complete | Let remote operators review a complete expiration policy and aggregate eligible bytes without exposing backup names | Authenticated 64 KiB policy request/16 KiB redacted aggregate plan, truncation blocking, client/CLI/schema/docs, and authentication/redaction/read-only tests |
| Loop 163: Bounded Remote Backup Retention Scanning | Complete | Keep over-budget retention preflights from traversing an unbounded backup parent before failing closed | Fixed `limit + 1` scan guard, lower-bound truncation semantics, regression coverage, and aligned backup/remote-retention documentation |
| Loop 164: Lazy Bounded One-Shot Schedule Discovery | Complete | Keep bounded local due batches and compact schedule inventories from materializing every schedule-directory path | Lazy file enumeration, deterministic `(run_at, schedule.id)` selection, bounded full-definition retention, compatibility tests, and aligned trigger documentation |
| Loop 165: Bounded One-Shot Schedule Document Reads | Complete | Keep local one-shot schedule parsing from allocating an unbounded JSON document | Fixed 2 MiB UTF-8 read window across save/read/list/compact/due paths, growth-race recheck, fail-closed regression coverage, and aligned scheduling documentation |
| Loop 166: Bounded CLI JSON Document Inputs | Complete | Keep generic local CLI JSON parsing from allocating an unbounded operator file | Fixed 8 MiB UTF-8 window, growth-race recheck, stable no-traceback input failures, compatibility regression coverage, and CLI boundary documentation |
| Loop 167: Descriptor-Bound Service Configuration Reads | Complete | Keep service startup from parsing an unbounded or path-raced configuration document | Fixed 64 KiB read window, regular-file/no-symlink check, device/inode binding, growth/replacement regression coverage, and service configuration documentation |
| Loop 168: Bounded Local Credential-File Reads | Complete | Keep local CLI credential maps from bypassing the secret-input boundary through unbounded or path-raced reads | Fixed 2 MiB read window, regular-file/no-symlink check, device/inode binding, growth/replacement regression coverage, and credential-file boundary documentation |
| Loop 169: Bounded SKILL.md Authoring Inputs | Complete | Keep parse/compile authoring sources from bypassing the input boundary through unbounded or path-raced reads | Fixed 2 MiB read window, regular-file/no-symlink check, device/inode binding, growth/replacement regression coverage, and SKILL.md input boundary documentation |
| Loop 170: Bounded Local JSON Run-State Reads | Complete | Keep dependency-light JSON run-state load and recovery from bypassing the local input boundary through unbounded or path-raced reads | Fixed 8 MiB read/write window, regular-file/no-symlink check, device/inode binding, growth/replacement regression coverage, and JSON run-state boundary documentation |
| Loop 171: Bounded Local JSON Control Index Reads | Complete | Keep the dependency-light JSON control registry and its SQLite import from bypassing the local input boundary through unbounded or path-raced reads | Fixed 8 MiB read/write window, regular-file/no-symlink check, device/inode binding, growth/replacement regression coverage, and JSON control-index boundary documentation |
| Loop 172: Bounded Published Workflow Artifact Reads | Complete | Keep immutable Workflow artifacts from bypassing the local input boundary before checksum verification or backup validation | Fixed 2 MiB publication/read window, shared descriptor-bound reader, pre-open/growth/path-race regression coverage, backup evidence, and published-artifact read-boundary documentation |
| Loop 173: Bounded External Connector Result Envelopes | Complete | Keep explicitly loaded external connector results from bypassing the durable executor boundary through oversized or non-JSON handoffs | Fixed 1 MiB strict-JSON normalized result envelope, rejection before durable state, connector regression coverage, and external-connector result-boundary documentation |
| Loop 174: Bounded SQLite Run-State Documents | Complete | Keep the recommended SQLite production backend from bypassing the complete run-state persistence boundary through oversized or malformed documents | Fixed 8 MiB UTF-8 state bound on writes and full-state decodes, recovery/cancellation/startup coverage, and SQLite run-state boundary documentation |
| Loop 175: Bounded Audit Event Documents | Complete | Keep local JSONL and SQLite control-plane audit persistence from bypassing a fixed per-event document boundary | Fixed 1 MiB UTF-8 JSON-object bound on writes and bounded reads, atomic batch validation, import/integrity coverage, and audit-event boundary documentation |
| Loop 176: Bounded SQLite Workflow Registry Records | Complete | Keep the recommended SQLite workflow registry from bypassing a fixed per-record document boundary | Fixed 2 MiB UTF-8 JSON-object bound on registry writes and reads, atomic replacement and alias-update validation, import/diagnostic coverage, and SQLite registry boundary documentation |
| Loop 177: Bounded SQLite Trigger-Ledger Responses | Complete | Keep completed trigger idempotency rows from bypassing a fixed replay-document boundary | Fixed 64 KiB UTF-8 JSON-object bound on replay writes and reads, atomic pending-claim preservation, fail-closed corruption handling, control-plane coverage, and SQLite trigger-ledger boundary documentation |
| Loop 178: Bounded Workflow Execution Explanations | Complete | Give local and remote operators a safe pre-execution review of topology, gates, connector side effects, input shape, retries, and timeouts without exposing values or executing work | Fixed side-effect-free explanation schema, local/remote CLI, authenticated read-only route, 64 KiB/1,000-node/2,000-edge bounds, redaction tests, and operator documentation |
| Loop 179: Side-Effect-Free Trigger Preflight | Complete | Let operators validate trigger input and HTTP request mappings before starting a real run without exposing values or invoking providers | Fixed value-free preflight schema, local/remote CLI, authenticated POST route, 1 MiB/64 KiB bounds, stable issue codes, redaction/read-only tests, package-smoke evidence, and operator documentation |
| Loop 180: Portable Workflow DSL Bundles | Complete | Share one validated Workflow DSL artifact as a deterministic, secret-checked local bundle without packaging state or credentials | Fixed two-member ZIP manifest, digest verification, 8 MiB/2 MiB/4 MiB bounds, path/read safety, local CLI, tests, docs, and package evidence |
| Loop 181: Verified Local Workflow Bundle Publication | Complete | Move a fully verified local bundle into the normal immutable publication path without extraction, execution, or credential access | In-memory verified loader, explicit local `bundle-publish`, JSON/SQLite publication coverage, conflict/idempotency evidence, installed CLI, tests, docs, and package evidence |
| Loop 182: Value-Free Workflow Bundle Diff Review | Complete | Compare two verified bundles before publication without exposing workflow values or requiring control-plane state | Shared structural diff helper, fixed bundle-diff schema, identity mismatch guard, redaction/read-only tests, installed CLI, docs, and package evidence |
| Loop 183: Verified Local Workflow Bundle Execution | Complete | Run a verified bundle through the existing local executor without publication or a second execution authority | `bundle-run`, JSON/SQLite execution evidence, invalid-pre-state guard, normal credential/retry/timeout delegation, installed CLI, docs, and package evidence |
| Loop 184: Verified Workflow Bundle Input Preflight | Complete | Check optional bundle trigger input and connector mappings without state or side effects, then reuse the admission result before bundle execution | `bundle-preflight`, value-free readiness report, blocked-input pre-state guard, `bundle-run --input`, installed CLI, docs, and package evidence |
| Loop 185: Explicit Workflow Bundle Side-Effect Consent | Complete | Require per-invocation operator consent before a connector-bearing Bundle can create state, resolve credentials, or call a connector | `--allow-side-effects` guard, pre-state rejection, authorized HTTP connector evidence, installed CLI, docs, and package evidence |
| Loop 186: Compact Workflow Bundle Run Evidence | Complete | Preserve only Bundle verification and side-effect-consent booleans in successful local run context for diagnosis without secrets or provider payloads | `context.bundle_run` metadata, state tests, installed CLI, docs, and package evidence |
| Loop 187: Exact Workflow Bundle Provenance Evidence | Complete | Preserve the exact verified Bundle archive fingerprint in successful local run context without retaining paths, values, credentials, or provider payloads | same-read verified loader, `context.bundle_run.bundle_sha256`, provenance tests, installed CLI, docs, and package evidence |
| Loop 188: Structured Workflow Bundle Admission Refusals | Complete | Expose machine-readable side-effect-consent refusals without changing the default text error or creating state | `bundle-run --format json`, fixed refusal schema, safety tests, installed CLI, docs, and package evidence |
| Loop 189: Safe Workflow Bundle Run Summaries | Complete | Expose successful Bundle runs as a value-free handoff without changing complete local output | `bundle-run --summary`, fixed summary schema, redaction tests, installed CLI, docs, and package evidence |
| Loop 190: Bounded External Connector Fixture Loading | Complete | Bound explicit local connector source loading without widening service or remote dynamic-code paths | 2 MiB UTF-8 source bound, regular-file/no-follow checks, device/inode identity and replacement detection, focused loader tests, docs, and baseline evidence |
| Loop 191: Explicit Connector Fixture Manifest Inspection | Complete | Let operators review an explicitly loaded connector manifest before execution without creating state or invoking a connector | `connectors --connector-fixture`, read-only CLI coverage, manifest contract assertions, docs, and package evidence |
| Loop 192: Bounded HTTP Query-Parameter Input Mapping | Complete | Map scalar trigger input into flat HTTP query parameters without templates, expressions, or header interpolation | Additive `/query/<name>` contract, percent-encoded runtime URL copy, scalar/rejection tests, docs, and package evidence |
| Loop 193: Metadata-Only HTTP Response Retention | Complete | Let workflows discard raw HTTP response values while preserving bounded delivery metadata | Additive `response_mode` contract, success/error projections, raw-value absence and invalid-mode tests, docs, and package evidence |
| Loop 194: Fixed HTTP No-Redirect Credential Boundary | Complete | Reject HTTP redirects before credential headers can be replayed to a second target | Dedicated no-redirect opener, real dual-server credential regression, unchanged non-redirect contract tests, docs, and package evidence |
| Loop 195: Fixed HTTP Direct-Egress Boundary | Complete | Prevent ambient process proxy settings from rerouting credentialed HTTP requests | Empty proxy handler, real target-plus-proxy regression, unchanged direct HTTP contract tests, docs, and package evidence |
| Loop 196: Bounded HTTP Request Metadata | Complete | Keep URL, method, and headers bounded and normalize malformed request failures before network access | Fixed URL/method/header bounds, injection and invalid-port rejection, raw-exception regression tests, docs, and package evidence |
| Loop 197: Declarative HTTP Origin Governance | Complete | Let reviewed workflows restrict built-in HTTP egress to exact origins before credential resolution | Additive `allowed_origins` schema/compiler/runtime contract, no-network mismatch tests, LiteGraph write-back, docs, and package evidence |
| Loop 198: Fixed HTTP Transport Error Redaction | Complete | Keep built-in HTTP transport and request-body failures value-free before durable connector persistence | Fixed timeout/network/serialization messages, injected leakage regressions, compatibility/docs updates, and package evidence |
| Loop 199: External Connector Exception Boundary | Complete | Keep unexpected explicitly loaded connector exceptions inside the normalized durable failure path | Fixed unexpected-exception message, direct and SQLite leakage regressions, result-boundary docs, and package evidence |
| Loop 200: Service-Level HTTP Origin Upper Bound | Complete | Govern built-in HTTP destinations at the self-hosted service boundary, including recurring execution, without changing Workflow DSL compatibility | Versioned exact-origin service policy, direct/scheduled propagation, pre-credential/network suppression, schema/docs, and regression evidence |
| Loop 201: Discoverable Service HTTP Origin Bootstrap | Complete | Make the service-level HTTP origin policy safe and discoverable during first-run initialization | Repeatable CLI options, canonical config output, pre-creation validation, operator docs, and bootstrap regression evidence |
| Loop 202: Durable External Connector Failure Boundary | Complete | Keep provider-authored external connector failure text out of durable run and audit projections without breaking immediate callers | Fixed durable failure message, returned/raised/retry coverage, SQLite reload evidence, docs, and production gates |
| Loop 203: Durable External Connector Metadata Boundary | Complete | Keep arbitrary external connector output, audit, input-mapping, and credential strings out of durable state without breaking immediate callers | Fixed value-free durable projection, direct-result compatibility, SQLite reload evidence, docs, and production gates |
| Loop 204: Manifest-Declared External Connector Metadata Policy | Complete | Let reviewed external connectors retain safe connector-specific finite metadata without widening durable state to arbitrary provider values | Strict manifest policy validation, JSON/SQLite custom-vocabulary projection evidence, docs, and production gates |
| Loop 205: Protected Uncertain-Dispatch Reviews | Complete | Let operators persist a bounded, compare-and-swap review of uncertain recurring effects without replaying or changing dispatch state | Fixed review schema, authenticated/local CLI and service routes, idempotent/conflict-safe SQLite evidence, redacted audit, package/docs/full-suite gates |
| Loop 206: Installed Static UI Launcher | Complete | Let wheel users launch the editor and control-plane inspector without a source checkout or ad hoc server command | Loopback-only `ui` CLI, packaged static/example assets, isolated wheel serving evidence, docs, and full gates |
| Loop 207: Authenticated Live Control-Plane UI | Complete | Let an explicitly configured installed UI inspect one running service without exposing the ingress token to the browser | Fixed same-origin snapshot proxy, server-side token reads, fail-closed path/schema/response boundary, UI/CLI tests, docs, and full gates |
| Loop 208: Live Service Readiness Badge | Complete | Let operators distinguish static mode, a ready service, a not-ready standby/draining service, and an unavailable process in the installed UI | Fixed service-probe proxy, bounded readiness schema, status badge, UI tests, docs, and full gates |
| Loop 209: Bounded Live Snapshot Refresh | Complete | Let operators explicitly monitor one configured live service without unbounded browser polling or losing the last valid snapshot on transient failures | Fixed 10-second timer, visibility pause, overlap guard, stale-data preservation, UI contract tests, docs, and full gates |
| Loop 210: Protected Live Support-Bundle Download | Complete | Let operators hand off one explicit redacted support artifact from the live console without exposing credentials or adding automatic upload | Fixed support-bundle proxy, 128 KiB response bound, attachment filename, UI/route tests, docs, and full gates |
| Loop 211: Confirmation-Protected Live Human-Gate Action | Complete | Let operators approve or reject one selected waiting run from the live console without exposing credentials or adding arbitrary mutation proxying | Fixed waiting-run guard, confirmation-protected POST, server-side token forwarding, response refresh, UI/route tests, docs, and full gates |
| Loop 212: Bounded Live Run-Detail Evidence | Complete | Let operators inspect the existing redacted event tail before a live human-gate decision without exposing credentials or raw state | Fixed run-detail proxy, 50-event/64 KiB bounds, schema/window validation, UI/route tests, docs, and full gates |
| Loop 213: Bounded Live Run Discovery | Complete | Let operators find older runs from the live console without arbitrary queries or unbounded browser state | Fixed cursor-page proxy, 100-item pages, 500-row client cap, schema/window validation, UI/route tests, docs, and full gates |
| Loop 214: Confirmation-Protected Live Cooperative Cancellation | Complete | Let operators request cooperative cancellation for one selected non-terminal live run without exposing credentials or adding arbitrary mutation proxying | Fixed cancel proxy, exact empty object, non-terminal guard, confirmation, UI/route tests, docs, and full gates |
| Loop 215: Bounded Live Audit Discovery | Complete | Let operators inspect older redacted audit events from the live console without arbitrary filters or unbounded browser state | Fixed audit-page proxy, 100-event pages, 500-row cap, cursor/schema validation, UI/route tests, docs, and full gates |
| Loop 216: Bounded Live Recurring-Schedule Discovery | Complete | Let operators inspect recurring schedule health and next-run timing from the live console without schedule mutation or trigger-input exposure | Fixed schedule inventory proxy, exact 100-item redacted contract, schedule table, UI/route tests, docs, and full gates |
| Loop 217: Live Production-Readiness Diagnostics | Complete | Let operators inspect actionable service, artifact, audit, backup, and blocking-reason checks from the live console without mutation or value exposure | Fixed operational-readiness proxy, exact schema validation, readiness table, UI/route tests, docs, and full gates |
| Loop 218: Live Published-Workflow Inventory | Complete | Let operators inspect current published versions, aliases, lifecycle status, and checksums from the live console without Workflow content exposure | Fixed workflow-inventory proxy, exact 100-item redacted contract, live registry table, UI/route tests, docs, and full gates |
| Loop 219: Live Workflow-Plan Review | Complete | Let operators review a selected live version's topology, gates, connector side effects, retries, and timeouts without executing it or exposing values | Fixed workflow-explanation proxy, exact bounded redacted contract, selection review action, UI/route tests, docs, and full gates |
| Loop 220: Live Empty-Trigger Preflight | Complete | Let operators check a selected version's empty-trigger input and mapping readiness without accepting business values or starting a run | Fixed preflight proxy, exact empty-body contract, value-free readiness review, UI/route tests, docs, and full gates |
| Loop 221: Live Workflow Version Diff Review | Complete | Let operators compare two versions of one live workflow without exposing values or mutating runtime state | Fixed three-component diff proxy, exact bounded redacted contract, same-workflow target selection, UI/route tests, docs, and full gates |
| Loop 222: Live Recurring-Dispatch Evidence | Complete | Let operators inspect cursor-paged recurring dispatch outcomes, including uncertain records, without claiming or replaying work | Fixed schedule/cursor proxy, exact bounded redacted contract, 500-row browser cap, UI/route tests, docs, and full gates |
| Loop 223: Live Uncertain-Dispatch Review | Complete | Let operators record one explicit conclusion for an uncertain dispatch without replaying or claiming work | Fixed confirmation-protected review proxy, outcome allowlist, CAS/audit reuse, UI/route tests, docs, and full gates |
| Loop 224: Live Workflow Promotion | Complete | Let operators promote one reviewed published version to the fixed production alias without leaving the live console | Fixed confirmation-protected promotion proxy, observed-alias CAS precondition, strict UI/route tests, docs, and full gates |
| Loop 225: CAS-Protected Live Workflow Deprecation | Complete | Let operators retire one reviewed published version without allowing stale inventory to override a concurrent alias or artifact change | Optional checksum-plus-alias CAS across local/SQLite/service/client paths, confirmation-protected UI action, strict UI/route tests, docs, and full gates |
| Loop 226: Confirmation-Protected Live Workflow Publication | Complete | Let operators publish one reviewed local Workflow DSL document from the live console without exposing ingress credentials or automatically activating it | Fixed bounded publication proxy, server-side token, confirmation, redacted response validation, inventory refresh, UI/route tests, docs, and full gates |
| Loop 227: Side-Effect-Free Live Workflow Release Preflight | Complete | Validate one staged Workflow DSL document before immutable publication without storing or executing it | Fixed authenticated preflight proxy, server-side token, strict bounded value-free response, staged-control gate, UI/service tests, docs, and full gates |
| Loop 228: Confirmation-Protected Live Empty Trigger | Complete | Let operators start one preflighted no-input published version from the live console without browser credentials or uncontrolled retries | Fixed source/empty-input proxy, confirmation, strict compact receipt, manual same-key retry, UI tests, docs, and full gates |
| Loop 229: Staged-Input Live Workflow Trigger | Complete | Let operators preflight and start a published exact version with one explicit non-secret JSON input from the live console | Fixed staged-input proxies, value-free preflight, confirmation, server-side token, same-key retry, UI/docs/tests, and full gates |
| Loop 230: Live Trigger-To-Run Handoff | Complete | Let operators move from one accepted exact-version trigger receipt into the bounded redacted run review without manually searching the run table | Receipt-bound local handoff, existing fixed run-detail route, UI/docs/tests, and full gates |
| Loop 231: Local SKILL.md Editor Compilation | Complete | Let authors compile one standard local SKILL.md directly into the installed visual editor without creating an intermediate file | Fixed loopback compile route, bounded in-memory parser/compiler handoff, no-write/source-path redaction, UI/docs/tests, and full gates |
| Loop 232: Offline Editor Asset Boundary | Complete | Make the installed visual authoring surface usable without CDN access or runtime internet egress | Pinned local LiteGraph assets, MIT notice, SHA-256 integrity test, offline docs, and full gates |
| Loop 233: Strict Local SKILL.md Source Decoding | Complete | Keep a selected local Skill's bytes from being silently replacement-decoded before compilation | Fatal UTF-8 byte decoder, explicit browser failure, UI/docs/tests, and full gates |

Loop 40 is complete. Any future Pilot must begin under a new authorization boundary and still produce reproducible controlled live-pilot evidence, explicit failure and rollback exercises, and a decision to continue, harden, or defer broader live integration work. The repository must not commit live credentials or raw live payload evidence.

The Loop 39 validation remains recorded at `docs/lark-live-connector-validation.md`. Live behavior remains limited to the fixed `create_task` action. The one scoped live connector validation is not the controlled real-team business-workflow pilot required for Loop 40. The earlier stopped Pilot is retained separately at `docs/controlled-pilot-deferral-review.md` and did not contribute to the completed evidence.

Loop 41 keeps the runtime scope single-instance and single-tenant. It does not introduce worker coordination or a multi-tenant service boundary.

Loop 42 requires authentication by default on the production service path, credential-handle resolution, compact security audit evidence, and external TLS termination. It does not introduce multi-tenant RBAC, an OAuth platform, or a hosted secret manager.

Loop 43 covers persistent recurring schedules, restart recovery, missed-run policy, durable dispatch records, and lease or locking semantics for one SQLite-backed service instance. Duplicate suppression relies on persisted dispatch state and workflow or connector idempotency; the roadmap must not claim exactly-once execution.

Loop 44 covers only verified offline backup and atomic new-directory restore for the current SQLite layout. It excludes credentials, hot backup, cross-version migration, retention automation, remote replication, and a complete disaster-recovery claim.

Loop 45 covers explicit layout identity and the one supported legacy-unversioned-to-current copy-on-write migration. It excludes online or in-place migration, automatic deployment orchestration, downgrade conversion, post-cutover write reconciliation, and arbitrary future schemas.

Loop 46 covers only the fixed authenticated aggregate metric and operational-event contracts. It excludes identifiers and request values, tracing, histograms, alerts, dashboards, remote telemetry storage, log rotation, and distributed aggregation.

Loop 47 covers only offline copy-on-write disposal of old terminal runs, their linked evidence, and terminal dispatches. It excludes automatic legal policy, secure destruction of source media or backups, workflow/schedule-definition pruning, active-run cancellation, online retention, and post-cutover reconciliation.

Loop 48 covers only durable cooperative cancellation for one run. It excludes forceful thread or provider abort, side-effect rollback, compensation, bulk cancellation, deadlines, arbitrary reason text, and exactly-once execution. Fail-closed interrupted-run detection is delivered separately by Loop 49.

Loop 49 covers service-process ownership loss and fencing for the single-tenant SQLite runtime. It excludes automatic replay, provider reconciliation adapters, compensation, distributed workers, machine-level fencing, and exactly-once execution.

Loop 50 covers isolated wheel qualification and public metadata alignment. It excludes package-registry upload, tags, GitHub Releases, artifact signing, SBOM generation, reproducible-build claims, and a new package version.

Loop 51 covers first-run creation of one local service workspace. It excludes external TLS automation, process supervision, system accounts, containers, firewall policy, hosted secret management, connector credential generation, and workflow publication.

Loop 52 covers a local installed-wheel demonstration workflow. It excludes external connectors, real business side effects, production workflow design, automatic approval, destructive reset, and hosted onboarding.

Loop 53 covers read-only pre-start diagnostics. It excludes repair, permission changes, migration, scheduler-lease acquisition, live dependency checks, external connector calls, supervisor integration, and replacement of the live readiness endpoint.

Loop 54 covers only directory-backed connector credential reads. It excludes encryption at rest, secret distribution, IAM, OAuth, hosted vaults, automatic rotation, certificate/key parsing, and changes to the local-evaluation JSON credential file.

Loop 55 covers only authenticated bounded reads of the current control snapshot. It excludes browser credential storage, CORS, live UI polling, remote mutations, pagination cursors, RBAC, hosted TLS, multi-tenant filtering, and remote audit storage.

Loop 56 covers only generation of one manually enabled Linux systemd unit. It excludes account provisioning, automatic unit installation or enabling, service-manager alternatives, containers, log shipping, TLS/proxy automation, hosted monitoring, secret rotation, distributed coordination, and forceful provider-request abort.

Loop 57 covers only one authenticated decision for one waiting human gate. It excludes hosted RBAC, multi-user identity, arbitrary reason text, bulk approval, callbacks, remote audit storage, provider reconciliation, and exactly-once execution.

Loop 58 covers only the CLI client for the existing resume and cancel routes. It excludes browser sessions, token issuance or rotation, retries, queued actions, RBAC, bulk operations, and changes to service-side authorization.

Loop 59 covers only one authenticated `GET /runs/{run_id}` projection and its protected CLI client. It excludes full run-state export, workflow/input/result payloads, raw errors, arbitrary filtering, pagination cursors, mutation, browser sessions, RBAC, and remote audit storage.

Loop 60 covers only one authenticated `GET /runs` projection and its protected CLI client. It excludes arbitrary filters, pagination cursors, full state export, mutation, browser sessions, RBAC, remote audit storage, and provider-side execution guarantees.

Loop 61 covers only one authenticated `GET /api/v1/support-bundle` projection and its protected CLI client. It excludes remote upload, tracing, raw logs, full state export, browser sessions, RBAC, hosted support, and automatic disclosure or retention decisions.

Loop 62 covers only durable idempotency for non-empty trigger keys in SQLite control-plane and authenticated service requests. It excludes exactly-once provider effects, automatic replay after unknown outcomes, key expiration, distributed coordination, cross-tenant identity, and JSON/local evaluation enforcement.

Loop 63 covers only the bounded active execution segment controlled by `policies.default_timeout_ms`. It excludes human-gate expiry, delayed retry backoff, background workers, forceful provider cancellation, and exactly-once execution; Loop 115 added the separate global wall-clock deadline and Loop 118 added the per-node active deadline.

Loop 64 covers only an explicit `tool_call.on_fallback` transition after connector retries are exhausted. It excludes provider failover, compensation, delayed backoff, hidden transition mutation, expression evaluation, and exactly-once execution.

Loop 65 covers only a local SQLite SHA-256 audit chain and fixed verification result. It excludes digital signatures, external keys, immutable storage, remote streaming, JSON/JSONL chain guarantees, and hosted compliance retention policy.

Loop 66 covers only a 1 MiB canonical UTF-8 JSON-object limit on trigger inputs. It excludes encryption, redaction, field-level schemas, rate limiting, streaming uploads, historical-state rewriting, and exactly-once execution.

Loop 67 covers only the documented bounded `input_schema` subset and its
pre-idempotency runtime validation. It excludes full JSON Schema, coercion,
secret classification, encryption, redaction, hosted validation, rate
limiting, historical-state rewriting, and exactly-once execution.

Loop 68 covers only a fixed process-local active-handler budget for non-probe
service routes. It excludes distributed coordination, per-client quotas,
token-bucket rate limiting, queue persistence, admission of scheduler work,
provider cancellation, and exactly-once execution.

Loop 69 covers only explicit aliases scoped to one workflow and one local
control plane. It excludes health-based canaries, traffic splitting, automatic
rollback, alias garbage collection, hosted release orchestration, multi-tenant
routing, and exactly-once provider effects.

Loop 70 covers only canonical checksum verification against the local
control-plane registry before artifact reads, promotion, trigger validation, or
execution. It excludes digital signatures, remote attestation, automatic
repair, remote replication, and protection from an operator who can rewrite
both the artifact and its registry record.

Loop 71 covers only bounded structural diff output and an optional exact
expected-current-version check for one local alias. It excludes semantic
business-risk analysis, approval policy, canary traffic, automatic rollback,
signatures, hosted release orchestration, and multi-tenant coordination.

Loop 72 covers only the SQLite transaction boundary for one local alias
promotion: the exact expected-version check, registry mutation, and promotion
audit append commit together. It excludes distributed locks, JSON
cross-process coordination, release approvals, canary traffic, automatic
rollback, signatures, and exactly-once provider effects.

Loop 73 covers only SQLite single-record publication and deprecation
transactions plus exclusive immutable artifact creation. It excludes
distributed coordination, JSON cross-process guarantees, hosted release
orchestration, signatures, approvals, canaries, rollback, and exactly-once
provider effects.

Loop 74 covers only bounded local registry/file diagnostics and guarded cleanup
of a newly-created unregistered SQLite publication artifact after a known
failure. It excludes automatic repair, historical artifact garbage collection,
distributed filesystem transactions, signatures, remote artifact stores, and
JSON cross-process guarantees.

Loop 75 covers only atomic emission of one control-plane run-audit batch and a
bounded comparison of durable run-state event counts with observed audit event
counts. It excludes cross-database atomicity, automatic repair, audit rewriting,
connector replay, digital signatures, remote replication, and exactly-once
provider effects.

Loop 76 covers only an authenticated remote read of the Loop 75 report and its
protected CLI client. It excludes remote writes, automatic repair, audit
rewriting, remote replication, RBAC, hosted support, and exactly-once provider
effects.

Loop 77 covers only safe targeting of one existing run within the Loop 76
diagnostic report. It excludes arbitrary path selection, bulk export, remote
writes, automatic repair, audit rewriting, and exactly-once provider effects.

Loop 78 covers only an authenticated, bounded read of recurring schedule
definitions. It excludes remote schedule mutation, dispatch claims, lease
control, trigger input, scheduler-owner identities, arbitrary filters,
pagination cursors, and exactly-once provider effects.

Loop 79 covers only protected enable/disable actions for one existing recurring
schedule. It excludes schedule creation/deletion, dispatch claims, lease
control, arbitrary filters, RBAC, cross-database atomicity, trigger input,
credentials, and exactly-once provider effects.

Loop 80 covers only bounded, authenticated read projections of persisted
recurring dispatch outcomes. It excludes schedule mutation, dispatch claims,
lease control, replay or reconciliation, trigger input, credentials, RBAC,
bulk export, and exactly-once provider effects.

Loop 81 covers only bounded, authenticated projections of local workflow
registry/file consistency. It excludes artifact repair or deletion, checksum
rewriting, publication, upload, RBAC, and cross-database atomicity.

Loop 82 covers only a bounded, authenticated preflight for the existing local
offline SQLite backup. It excludes remote backup creation or transport,
encryption, restore, retention, service shutdown, scheduler mutation, paths,
lease identities, credentials, and any guarantee that a later backup cannot
fail after the report is read.

Loop 83 covers only a bounded, authenticated projection of the existing local
SQLite audit-chain verification result. It excludes repair or rewrite, event
payload export, digital signatures, key management, backup transport, restore,
RBAC, hosted compliance, and operator identity claims.

Loop 84 covers only a bounded, authenticated point-in-time runtime identity and
compatibility projection. It excludes upgrade, migration, rollback, shutdown,
configuration disclosure, host inventory, dependency dumps, RBAC, and any
guarantee that a future binary is compatible with the reported state.

Loop 85 covers only a protected client for the existing published-workflow
webhook boundary. It excludes new execution authority, draft-workflow access,
secret input handling, external-effect retry, hosted ingress, OAuth/RBAC, and
exactly-once provider semantics.

Loop 86 covers only one authenticated publication route for a complete Workflow
DSL document. It excludes alias promotion, run triggering, deprecation,
artifact upload or download, release approvals, signatures, hosted CI/CD
orchestration, credentials in workflow content, and exactly-once provider
semantics.

Loop 87 covers only one authenticated promotion route for an existing published
version and one bounded alias. It excludes publication, deprecation, trigger
execution, rollback orchestration, alias health checks, canary traffic,
multi-tenant authorization, hosted CI/CD, signatures, and exactly-once provider
semantics.

Loop 88 covers only a bounded authenticated structural diff of two existing
published versions. It excludes workflow value export, semantic business-risk
analysis, approval policy, promotion mutation, publication, deprecation,
trigger execution, artifact repair, pagination, and exactly-once provider
semantics.

Loop 89 covers only local owner-controlled replacement of one file-backed
service ingress token. It excludes remote rotation, token return, multiple
active credentials, OAuth/RBAC, external secret-store coordination, and
service-manager reload orchestration.

Loop 90 covers only one authenticated deprecation route for one existing
published version. It removes stable aliases and marks registry status while
preserving the immutable artifact and one audit event. It excludes artifact
deletion, replacement publication or promotion, trigger execution, in-flight
run rewriting, Workflow content export, RBAC, and exactly-once provider
semantics.

Loop 91 covers only bounded authenticated metadata discovery for existing
published Workflow versions. It excludes Workflow DSL/name export, artifact
paths, timestamps, audit payloads, pagination cursors, publication, promotion,
deprecation, trigger execution, repair, deletion, RBAC, and semantic business
risk analysis.

Loop 92 covers only an authenticated, policy-bound read-only retention
preflight. It excludes remote copy-on-write apply, deletion, backup creation,
service shutdown, legal-hold inference, filesystem erasure, path/payload
export, RBAC, and any claim that a plan remains valid after state changes.

Loop 93 covers only an authenticated aggregate projection of existing service,
artifact, audit, and offline-backup checks. It excludes lifecycle mutation,
atomic cross-database snapshots, raw logs, paths, credentials, repair,
backup/restore, retention apply, hosted monitoring, RBAC, and deployment
compatibility guarantees beyond the individual checks.

Loop 94 covers only the transport read deadline for one advertised HTTP
request body. It excludes total request deadlines, connector execution
timeouts, forceful provider cancellation, proxy/TLS management, request
queuing, body-size expansion, and any guarantee about external side effects.

Loop 95 covers only a client-side composition of the existing health and
readiness probes. It excludes new HTTP routes, authenticated business traffic,
proxy/TLS management, monitoring backends, deployment orchestration, lifecycle
mutation, and any claim that a ready response guarantees external provider
availability.

Loop 96 covers only exact completion of one advertised HTTP request body. It
excludes body-size expansion, transfer-encoding support, total request
deadlines, connector execution timeouts, forceful provider cancellation,
proxy/TLS management, and any guarantee about external side effects after a
complete request is accepted.

Loop 97 covers only the HTTP dispatch error boundary. It excludes handler
retries, workflow-state compensation, connector cancellation, automatic
reconciliation, alert delivery, traceback retention, proxy/TLS management, and
any guarantee that a fixed 503 means an external provider call did not occur.

Loop 98 covers only isolation of optional lifecycle event logging. It excludes
durable log delivery, retry/buffering, collector health monitoring, alerting,
log rotation, remote aggregation, and any guarantee that a missing operational
event proves a workflow did not execute.

Loop 99 covers only local listener and scheduler cleanup ordering around service
startup/teardown exceptions. It excludes scheduler retries, worker force-kill,
remote lease reconciliation, external provider compensation, and any guarantee
that an external side effect was rolled back after local cleanup.

Selection rules:

- Merge or explicitly defer the current loop before starting the next one.
- Keep work local-first and dependency-light unless an approved capability requires otherwise.
- Prefer trust, recovery, and operator evidence over broader platform surface area.
- Do not expand live SaaS behavior beyond the Loop 38 decision without a new readiness review.
- Keep candidate loops tentative until evidence from the preceding loop is complete.

## Capability Baseline

The project is a runnable local-first harness across all five approved architecture layers:

| Area | Current capability |
| --- | --- |
| Ingestion and compilation | Parse structured `SKILL.md` files into Skill IR, compile Workflow DSL, validate against the schema, and report structured errors |
| Authoring | Render Workflow DSL as LiteGraph JSON, inspect run overlays, and write back allowlisted visual edits without making the graph authoritative |
| Runtime | Execute and resume durable runs with JSON or SQLite state, bounded active timeout policy, human gates, retry/recovery policy, run context, connector events, and verifiable SQLite audit evidence |
| Control plane | Transactionally publish/deprecate immutable workflow versions and promote stable SQLite aliases, publish/promote/deprecate/inventory bounded versions through the authenticated service, protect live deprecation with checksum-plus-alias compare-and-swap guards, inspect registry/file artifact consistency, trigger runs from CLI/webhook/schedules with SQLite idempotency, query audit evidence, export read-only operator snapshots, inspect redacted runs, write a redacted support bundle, rotate the local ingress token atomically, preflight retention policy and trigger inputs/mappings through authenticated service diagnostics, inspect bounded local and protected remote backup inventories (including cursor-paged older evidence) and retention plans, inspect bounded redacted local workflow inventory, and consume aggregate operational readiness through the authenticated service |
| Extensions and safety | Run built-in and explicitly loaded connectors behind manifest, bounded descriptor-bound fixture loading, credential-handle, input-mapping, audit-redaction, and secret-hygiene boundaries |

Important boundaries:

- Published workflow artifacts remain immutable JSON documents in both storage modes.
- Visual write-back is allowlisted; topology, node ids, transition targets, and connector identity remain DSL-controlled.
- JSON and JSONL remain the dependency-light defaults for examples, local development, and evaluation; SQLite is the minimum production persistence baseline.
- Connector package loading is explicit. Automatic discovery, installation, and marketplace behavior are deferred.
- `0.1.x` compatibility covers the documented Workflow DSL `0.1.0` contract; undocumented internals remain experimental.

## Delivery History

The detailed implementation plans under `docs/superpowers/plans/` are the historical evidence for these loops.

| Loop | Status | Delivered |
| --- | --- | --- |
| Loop 1: Parser | Complete | Frontmatter, hard gates, checklist normalization, source line mapping |
| Loop 2: Compiler / Validator | Complete | Ordered workflow generation, node and edge validation, terminal-node checks |
| Loop 3: Executor | Complete | Local JSON-backed run state, human gate pause/resume, run list and detail |
| Loop 4: LiteGraph | Complete | Static LiteGraph editor, node inspector, run-state coloring, graph validation |
| Loop 5: Control Plane | Complete | Immutable publish, workflow lifecycle index, published-version runs, audit JSONL, connector placeholders |
| Loop 6: Workflow DSL Contract | Complete | JSON Schema, structured validator output, golden workflow fixture coverage |
| Loop 7: Visual Write-Back | Complete | `write-back` CLI, `Save DSL`, source Workflow DSL embedding, topology-preserving write-back |
| Loop 8: Runtime Durability | Complete | Storage boundary, SQLite run state, SQLite workflow registry, SQLite audit events, JSON import path |
| Loop 9: Control Plane Hardening | Complete | `resume-published`, `control-runs`, `control-run`, audit filters, deprecated-version guard |
| Loop 10: Connector Runtime MVP | Complete | Active connector manifests, manual and HTTP bindings, HTTP execution, connector run events, connector audit events |
| Loop 11: Authoring Experience | Complete | Example gallery, richer LiteGraph parameter forms, safe action/retry/HTTP request write-back, authoring docs |
| Loop 12: Open Source Release Readiness | Complete | `CONTRIBUTING.md`, issue templates, release notes, DSL compatibility policy, stability boundaries |
| Loop 13: Local Control Plane UI | Complete | `control-snapshot`, example snapshot fixture, static control-plane inspector, docs |
| Loop 14: Release Tagging | Complete | Annotated `v0.1.0` tag, GitHub release, release notes published from verified `main` |
| Loop 15: Release Automation | Complete | Read-only release preflight script, version/tag/notes guards, CI dry-run, maintainer docs |
| Loop 16: Workflow Example Pack | Complete | Enterprise example skills, synchronized Workflow DSL and LiteGraph fixtures, example docs and gallery entries |
| Loop 17: Connector Runtime Hardening | Complete | Deterministic HTTP connector tests, timeout/error normalization, retry/timeout docs, credential boundary docs |
| Loop 18: Control Plane Operator UX | Complete | Snapshot operator insights, static Operator view, attention/recent/connector/version tables, docs |
| Loop 19: Demo And Contributor Onboarding | Complete | Resettable local demo helper, generated onboarding artifacts, README/HARNESS entry path, tests |
| Loop 20: Packaging And Installability | Complete | Package metadata guards, editable install smoke helper, installed console-script verification, contributor docs |
| Loop 21: Runtime Policy And Recovery | Complete | Connector retry policy execution, retry/recovery events, audit promotion, runtime policy docs |
| Loop 22: Credential Boundary And Secret Hygiene | Complete | Credential boundary docs, committed-fixture secret hygiene scanner, CI guardrail, contributor guidance |
| Loop 23: Trigger And Local Run API | Complete | Trigger envelope, local trigger command, run-start audit metadata, trigger docs |
| Loop 24: Workflow Inputs And Run Context | Complete | Trigger input persistence, durable run context, compact audit boundary, executor context tests |
| Loop 25: Credential Provider Interface | Complete | Local credential provider, connector handle metadata, credential-file CLI path, leakage tests |
| Loop 26: Local Webhook Adapter | Complete | Local webhook request contract, stdlib webhook server, trigger-boundary adapter, JSON/SQLite tests, docs |
| Loop 27: Run Overlay In Visual Editor | Complete | Read-only run overlay contract, LiteGraph node overlays, control snapshot `node_overlays`, static Nodes view, docs |
| Loop 28: Pilot Playbook And Example | Complete | Local customer-support pilot smoke, webhook-triggered scenario, credential handle proof, snapshot and LiteGraph overlay artifacts, pilot docs |
| Loop 29: Scheduled Trigger Boundary | Complete | Deterministic local schedule contract, schedule CLI, due-run helper, audit tests, schedule smoke, docs |
| Loop 30: Trigger Input Mapping | Complete | Body-only HTTP connector input mapping from durable trigger context, validator/schema coverage, CLI/webhook/schedule tests, docs |
| Loop 31: Connector Extension Contract | Complete | Minimum connector manifest contract, execution handoff boundary, credential/audit rules, registry contract tests, docs |
| Loop 32: Pilot Scenario Pack | Complete | Multi-scenario local pilot pack for customer support, sales renewal, and risk exception workflows, with mapped connector input evidence and artifacts |
| Loop 33: Connector Extension Prototype | Complete | Explicit local external connector fixture, narrow runtime registration, published workflow smoke, credential-handle isolation, and compact audit evidence |
| Loop 34: Connector Packaging Boundary | Complete | Repeatable local connector package layout, explicit-loading smoke contract, compatibility notes, and stability boundaries |
| Loop 35: First Product Connector Candidate | Complete | Lark/Feishu task connector selected, alternatives compared, package boundary and dry-run smoke plan documented |
| Loop 36: First Product Connector Package Smoke | Complete | Lark/Feishu task connector dry-run package fixture, explicit-loading smoke, credential-handle evidence, and compact connector metadata |
| Loop 37: Product Connector Pilot Scenario | Complete | Sales renewal risk workflow using the Lark/Feishu task dry-run connector after a manual gate, with webhook trigger, audit, snapshot, and LiteGraph overlay artifacts |
| Loop 38: Live Connector Readiness Review | Complete | Decision note approving only scoped live Lark/Feishu `create_task` follow-up, with credential, idempotency, failure, audit, test, and rollback boundaries |
| Loop 39: Scoped Live Lark Task Connector | Complete | Explicit live `create_task` opt-in, fake-transport coverage, native provider idempotency, redaction and rollback boundaries, and one redacted real-validation evidence note |
| Loop 40: Controlled Live Connector Pilot | Complete | Paid assisted five-day, five-run Pilot with two private cases, a human rejection, safety exercises, fixed verification, a `continue` decision, and finalized redacted evidence |
| Loop 41: Self-hosted Runtime Service Boundary | Complete | Versioned service configuration, loopback-only ingress, health/readiness probes, graceful signal shutdown, SQLite restart continuity, operator guide, and real-process smoke evidence |
| Loop 42: Authenticated Ingress And Production Credentials | Complete | File-backed bearer authentication, execution-time directory credentials, compact ingress audit, request-size guard, external TLS contract, and security smoke evidence |
| Loop 43: Durable Recurring Scheduling And Safe Dispatch | Complete | Persistent interval schedules, explicit missed-run policy, claim-before-execute dispatch ledger, restart recovery, SQLite lease exclusion, standby takeover, and real-process evidence |
| Loop 44: Verified Backup And Restore | Complete | Offline three-database locking, referenced workflow artifacts, owner-only manifest, SHA-256 and integrity verification, atomic new-directory restore, credential exclusion, and real-process recovery drill |
| Loop 45: State Upgrade And Migration | Complete | Owner-only layout marker, read-only legacy/current/future preflight, mandatory pre-upgrade backup, source-preserving atomic copy upgrade, rollback boundary, and real-process cutover drill |
| Loop 46: Runtime Observability Export | Complete | Authenticated Prometheus aggregate metrics, fixed status/route labels, process-local HTTP counters, strict operational NDJSON, and real-process leakage evidence |
| Loop 47: Data Retention And Disposal | Complete | Versioned fixed retention policy, aggregate stopped-state plan, protected waiting/claimed state, secure-delete vacuumed copy, atomic publication, and real-process cutover evidence |
| Loop 48: Durable Cooperative Run Cancellation | Complete | Independent SQLite cancellation ledger, authenticated route and CLI, immediate waiting stop, running/retry safe points, stale-save protection, backup/retention integration, and real-process concurrency evidence |
| Loop 49: Interrupted Run Recovery | Complete | Lease-owned execution tickets, transactional interruption, stale-writer fencing, graceful-drain protection, backup/retention/metrics integration, and real-process crash evidence |
| Loop 50: Release Artifact Qualification | Complete | Wheel-only isolated install, scrubbed import environment, installed production-module and command contract checks, Beta metadata, and release-preflight enforcement |
| Loop 51: Secure Service Bootstrap | Complete | Non-overwriting owner-only workspace, generated ingress secret, absolute versioned configuration, installed CLI contract, and authenticated real-process first-run evidence |
| Loop 52: Installed Controlled Quickstart | Complete | Bundled standard Skill, validated DSL, immutable SQLite publication, one human gate, one-step resume, and installed-wheel authenticated trigger evidence |
| Loop 53: Operational Readiness Doctor | Complete | Fixed secret-free startup checks, descriptor-bound token validation, private runtime directories, stable exits, and real CLI failure evidence |
| Loop 54: Descriptor-bound Connector Credentials | Complete | Private descriptor-bound value reads, bounded UTF-8 input, atomic rotation, fixed errors, and real transport-suppression evidence |
| Loop 55: Authenticated Live Operator Snapshot | Complete | Zero-write authenticated service snapshot, fixed collection and byte bounds, safe CLI retrieval, private atomic output, and real-process observability evidence |
| Loop 56: Linux systemd Supervision | Complete | Non-overwriting CLI unit generation, fixed Linux sandboxing, state-only write access, SIGTERM-only shutdown, target-host verification steps, and portable real-CLI evidence |
| Loop 57: Authenticated Human-Gate Decisions | Complete | Exact authenticated resume body, durable success/failure branch, waiting-only conflict, compact audit evidence, and real threaded-service verification |
| Loop 58: Protected Remote Operator Action Clients | Complete | Token-file authenticated resume/cancel CLI, fixed origin and response safety, compact errors, and installed-wheel command evidence |
| Loop 59: Authenticated Redacted Run Detail | Complete | Fixed redacted run-detail schema, authenticated service route, protected `service-show` client, and bounded leakage/read-only evidence |
| Loop 60: Authenticated Redacted Run Discovery | Complete | Fixed redacted run-list schema, authenticated service route, protected `service-runs` client, and bounded leakage/read-only evidence |
| Loop 61: Authenticated Redacted Support Bundle | Complete | Fixed redacted support-bundle schema, structured aggregate observability, protected `service-support-bundle` client, 0600 atomic output, and bounded leakage/read-only evidence |
| Loop 62: Durable SQLite Trigger Idempotency | Complete | Atomic SQLite trigger claims, compact replay, fixed conflicts, unresolved-outcome fencing, and backup/restore replay-safety evidence |
| Loop 63: Bounded Active Execution Timeout | Complete | Bounded active execution deadline, fixed timeout evidence, human-gate pause semantics, and policy/schema validation |
| Loop 64: Declarative Fallback Transitions | Complete | Explicit connector fallback transition, failed-attempt preservation, fixed audit evidence, compiler validation, and LiteGraph projection |
| Loop 65: SQLite Audit Integrity | Complete | SHA-256 audit links, compact verification result, legacy-column upgrade, backup rejection, and retained-copy rechain |
| Loop 66: Bounded Trigger Inputs | Complete | Shared canonical input limit and fixed oversize failure contract across CLI, schedules, recurring schedules, and webhooks |
| Loop 67: Declarative Trigger Input Contracts | Complete | Optional bounded `input_schema`, publication/runtime validation, fixed path-only errors, and legacy open-object compatibility |
| Loop 68: Bounded Service Request Admission | Complete | Fixed 16-slot process-local business-handler budget, retryable `429`, probe availability, and slot-release regression evidence |
| Loop 69: Stable Workflow Version Promotion Aliases | Complete | Bounded workflow aliases, explicit promotion, exact-version precedence, deprecation cleanup, and alias-scoped replay-safe trigger resolution |
| Loop 70: Published Artifact Integrity Verification | Complete | Registry checksum verification before artifact reads, promotion, trigger validation, and execution, with fixed redacted failures and side-effect suppression |
| Loop 71: Reviewable Workflow Releases | Complete | Bounded structural `workflow-diff`, value redaction, and compare-and-swap alias promotion protection |
| Loop 72: Atomic Workflow Alias Promotion | Complete | SQLite transactionally couples compare-and-swap validation, alias mutation, and the promotion audit append under concurrent operators |
| Loop 73: Atomic Workflow Registry Mutations | Complete | SQLite transactionally couples immutable publication/deprecation registry changes with audit evidence and preserves concurrent versions |
| Loop 74: Workflow Artifact Consistency | Complete | Bounded registry/file consistency report, guarded known-failure cleanup, and installed CLI/schema contract |
| Loop 75: Run Audit Consistency | Complete | Atomic run-audit batches, bounded cross-database consistency report, and installed CLI/schema contract |
| Loop 76: Remote Run Audit Consistency | Complete | Authenticated zero-write endpoint, exact bounded remote client, readiness-independent diagnostics, telemetry/docs/package evidence |
| Loop 77: Targeted Remote Run Audit Inspection | Complete | Safe targeted route and CLI selection beyond the global report window, exact report compatibility, and operator evidence |
| Loop 78: Remote Recurring-Schedule Inventory | Complete | Authenticated zero-write schedule inventory, fixed redacted schema, bounded client/CLI, telemetry/docs/package evidence |
| Loop 79: Protected Remote Recurring-Schedule Actions | Complete | Protected idempotent schedule enable/disable, fixed action schema, dispatcher-safe SQLite mutation, bounded audit evidence, and installed client/CLI contract |

## Release Direction

Release tags follow semantic versioning. Capability loops are planning units, not version promises. `v0.1.0` is the first public bootstrap release and supports Workflow DSL `0.1.0` on Python 3.9+ with a standard-library runtime.

- Release: `https://github.com/pearjelly/skill2workflow/releases/tag/v0.1.0`
- Notes: `docs/releases/v0.1.0.md`
- Process: `docs/release-process.md`

Compatible `0.1.x` releases may package completed hardening, documentation, and narrow capabilities that preserve Workflow DSL `0.1.0`. Production maturity claims require evidence from the readiness gates rather than a speculative version-by-version capability inventory.

## Deferred Work

These areas require their own approved loops:

- Cloud-hosted multi-tenant control plane
- Full RBAC or IAM
- Complete BPMN compatibility
- Distributed scheduling or worker coordination
- Online or incremental backup, cross-version state migration, and remote replication
- Hosted ingress, callback verification, and queues
- OAuth, token refresh, and hosted credential management
- Automatic connector discovery, installation, or marketplace indexing
- Live SaaS behavior beyond the Loop 38-approved `create_task` action
- Guaranteed conversion of arbitrary SOP documents

## Roadmap Rules

- Select only one active loop.
- Preserve Workflow DSL compatibility unless a separately approved contract change defines migration behavior.
- Workflow DSL remains the execution truth source.
- Parser, compiler, validator, executor, connector, storage, or CLI behavior changes start with tests.
- User-facing capabilities need a CLI path before becoming UI-only controls.
- Each loop must define scope, exclusions, acceptance evidence, and verification commands.
- Prefer small closed loops over broad platform shells.
- Avoid runtime dependencies unless they directly unlock an approved, spec-backed capability.
- Update this file when a loop is selected, completed, or explicitly deferred; keep implementation detail in the matching plan or guide.
