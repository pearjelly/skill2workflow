# Roadmap

This roadmap turns the approved `skill2workflow` design into small, verifiable delivery loops. Each loop should leave behind a runnable command, tests, documentation, and an inspectable artifact.

## Product Direction

The near-term target is a self-hosted, single-tenant workflow runtime for one team. The project remains local-first and dependency-light while adding the minimum controls needed for a durable production path.

Workflow DSL remains the authoritative execution source of truth. LiteGraph and future UI layers are editors and views, not runtime authorities. The approved foundation remains in `docs/superpowers/specs/2026-07-01-skill2workflow-design.md`, and the production roadmap design is recorded in `docs/superpowers/specs/2026-07-11-production-roadmap-design.md`.

## Status At A Glance

- Published release: `v0.1.0`
- Workflow DSL compatibility line: `0.1.x` artifacts using `schema_version: "0.1.0"`
- Completed delivery loops: 1-108
- Current maturity: Self-hosted Beta
- Active loop: None; Loop 108 is complete with live in-flight request pressure metrics
- Next maturity gate: Production Baseline
- Next decision: select the next Production Baseline loop after reviewing the production-boundary CI gate evidence

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

**Status:** Directional; Loops 44-108 complete, further loop numbers unassigned.

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
The follow-on production hardening continues through Loop 108; the detailed
entries below record the operator-action recovery, audit-projection, metrics,
startup-shutdown, atomic lifecycle-state, shutdown-admission, and scheduler
dispatch boundaries, and live request-pressure telemetry.

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

Candidate evidence includes backup and restore, upgrade and migration policy, cancellation and retention behavior, logs or metrics export, fault drills, contract stability, and sustained real-team operating evidence. Backup/restore became Loop 44, state upgrade/migration became Loop 45, observability export became Loop 46, data retention/disposal became Loop 47, durable cooperative cancellation became Loop 48, interrupted-run crash recovery became Loop 49, release-artifact qualification became Loop 50, secure service bootstrap became Loop 51, the installed controlled quickstart became Loop 52, the operational readiness Doctor became Loop 53, descriptor-bound connector credentials became Loop 54, the authenticated live Operator snapshot became Loop 55, a manually reviewed Linux systemd unit became Loop 56, an authenticated human-gate decision endpoint became Loop 57, protected remote operator action clients became Loop 58, authenticated redacted run detail became Loop 59, authenticated redacted run discovery became Loop 60, authenticated redacted support bundle became Loop 61, durable trigger idempotency became Loop 62, bounded active execution timeout became Loop 63, declarative fallback transitions became Loop 64, SQLite audit integrity became Loop 65, bounded trigger inputs became Loop 66, declarative trigger input contracts became Loop 67, bounded service request admission became Loop 68, stable workflow version promotion aliases became Loop 69, published artifact integrity verification became Loop 70, and reviewable workflow releases became Loop 71 after review of the preceding evidence; atomic workflow alias promotion became Loop 72 after review of the release-review drill; atomic workflow registry mutations became Loop 73 after review of the promotion transaction drill; workflow artifact consistency diagnostics became Loop 74 after review of the registry mutation drill; atomic run-audit emission and consistency diagnostics became Loop 75 after review of the artifact consistency drill; authenticated remote run-audit consistency became Loop 76 after review of the remote diagnostic drill; targeted remote run-audit inspection became Loop 77 after review of the global-window operator gap; remote recurring-schedule inventory became Loop 78 after review of the remote operator scheduling gap; protected remote recurring-schedule actions became Loop 79 after review of the inventory drill; remote recurring-schedule dispatch diagnostics became Loop 80 after review of the schedule action drill; remote workflow artifact consistency diagnostics became Loop 81 after review of the remote dispatch evidence; remote backup readiness diagnostics became Loop 82 after review of the remote artifact consistency evidence; remote audit-chain verification became Loop 83 after review of the backup-readiness evidence; remote runtime identity diagnostics became Loop 84 after review of the remote audit-integrity evidence; protected remote workflow triggering became Loop 85 after review of the remote runtime-info evidence; protected remote Workflow publication became Loop 86 after review of the remote-trigger evidence; protected remote Workflow promotion became Loop 87 after review of the remote-publication evidence; protected remote Workflow diff became Loop 88 after review of the remote-promotion evidence; protected local ingress-token rotation became Loop 89 after review of the remote-diff evidence; protected remote Workflow deprecation became Loop 90 after review of the token-rotation evidence; bounded remote Workflow inventory became Loop 91 after review of the remote-deprecation evidence; policy-bound remote retention readiness became Loop 92 after review of the remote-inventory evidence; aggregate remote operational readiness became Loop 93 after review of the retention evidence; bounded request-body reads became Loop 94 after review of the operational-readiness evidence; and the deployment service probe became Loop 95 after review of the transport-boundary evidence; exact-length request-body reads became Loop 96 after review of the service-probe evidence; the fail-closed service exception boundary became Loop 97 after review of the body-read evidence. Remaining capabilities become numbered loops only after preceding evidence is reviewed.

Verified offline backup/restore, copy-on-write state migration, bounded telemetry export, copy-on-write retention/disposal, durable cooperative cancellation, fail-closed interrupted-run recovery, isolated wheel qualification, secure first-run initialization, an installed first-value workflow journey, read-only startup diagnostics, descriptor-bound connector credentials, a bounded live Operator read surface, a manually reviewed least-privilege Linux systemd unit, an authenticated human-gate decision endpoint, protected remote operator action clients, bounded redacted run detail, bounded redacted run discovery, a bounded redacted support bundle, durable SQLite trigger idempotency, bounded active execution timeout, declarative connector fallback transitions, tamper-evident SQLite audit verification, bounded trigger input validation, declarative trigger input contracts, bounded service request admission, stable workflow version promotion aliases, published artifact integrity verification, and reviewable workflow releases, plus atomic workflow alias promotion, atomic workflow registry mutations, workflow artifact consistency diagnostics, atomic run-audit emission and consistency diagnostics, targeted remote run-audit inspection, remote recurring-schedule inventory, protected remote recurring-schedule actions, bounded remote recurring-schedule dispatch diagnostics, remote workflow artifact consistency diagnostics, remote backup readiness diagnostics, remote audit-chain verification, remote runtime identity diagnostics, protected remote workflow triggering, protected remote Workflow publication, protected remote Workflow promotion, protected remote Workflow diff, protected local ingress-token rotation, protected remote Workflow deprecation, bounded remote Workflow inventory, policy-bound remote retention readiness, aggregate remote operational readiness, bounded request-body reads, the fixed deployment service probe, exact-length request-body reads, lifecycle event-logger isolation, deterministic service teardown, production-boundary CI gates for security, observability, and restart continuity, the uniform zero-body metrics boundary, startup-shutdown race protection, atomic lifecycle state transitions, atomic shutdown admission, and atomic scheduler dispatch admission, and live in-flight request pressure metrics, are achieved by Loops 44-108. Production Baseline remains directional until the remaining candidate evidence is selected, delivered, and reviewed; these controls do not advance project maturity by themselves.

## Active Loop

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

## Rolling Loop Queue

This rolling queue is ordered. Loop 108 is complete and there is no active delivery loop; select the next Production Baseline item only after reviewing the production-boundary CI gate evidence.

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

Loop 63 covers only the bounded active execution segment controlled by `policies.default_timeout_ms`. It excludes global wall-clock deadlines, human-gate expiry, delayed retry backoff, background workers, forceful provider cancellation, and exactly-once execution.

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
| Control plane | Transactionally publish/deprecate immutable workflow versions and promote stable SQLite aliases, publish/promote/deprecate/inventory bounded versions through the authenticated service, inspect registry/file artifact consistency, trigger runs from CLI/webhook/schedules with SQLite idempotency, query audit evidence, export read-only operator snapshots, inspect redacted runs, write a redacted support bundle, rotate the local ingress token atomically, preflight a normalized retention policy through the authenticated service, and consume aggregate operational readiness through the authenticated service |
| Extensions and safety | Run built-in and explicitly loaded connectors behind manifest, credential-handle, input-mapping, audit-redaction, and secret-hygiene boundaries |

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
