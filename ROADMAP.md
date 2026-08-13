# Roadmap

This roadmap turns the approved `skill2workflow` design into small, verifiable delivery loops. Each loop should leave behind a runnable command, tests, documentation, and an inspectable artifact.

## Product Direction

The near-term target is a self-hosted, single-tenant workflow runtime for one team. The project remains local-first and dependency-light while adding the minimum controls needed for a durable production path.

Workflow DSL remains the authoritative execution source of truth. LiteGraph and future UI layers are editors and views, not runtime authorities. The approved foundation remains in `docs/superpowers/specs/2026-07-01-skill2workflow-design.md`, and the production roadmap design is recorded in `docs/superpowers/specs/2026-07-11-production-roadmap-design.md`.

## Status At A Glance

- Published release: `v0.1.0`
- Workflow DSL compatibility line: `0.1.x` artifacts using `schema_version: "0.1.0"`
- Completed delivery loops: 1-70
- Current maturity: Self-hosted Beta
- Active loop: None; Loop 70 is complete with published artifact integrity verification
- Next maturity gate: Production Baseline
- Next decision: select the next Production Baseline loop after reviewing the published-artifact integrity drill

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

**Status:** Directional; Loops 44-70 complete, further loop numbers unassigned.

Candidate evidence includes backup and restore, upgrade and migration policy, cancellation and retention behavior, logs or metrics export, fault drills, contract stability, and sustained real-team operating evidence. Backup/restore became Loop 44, state upgrade/migration became Loop 45, observability export became Loop 46, data retention/disposal became Loop 47, durable cooperative cancellation became Loop 48, interrupted-run crash recovery became Loop 49, release-artifact qualification became Loop 50, secure service bootstrap became Loop 51, the installed controlled quickstart became Loop 52, the operational readiness Doctor became Loop 53, descriptor-bound connector credentials became Loop 54, the authenticated live Operator snapshot became Loop 55, a manually reviewed Linux systemd unit became Loop 56, an authenticated human-gate decision endpoint became Loop 57, protected remote operator action clients became Loop 58, authenticated redacted run detail became Loop 59, authenticated redacted run discovery became Loop 60, authenticated redacted support bundle became Loop 61, durable trigger idempotency became Loop 62, bounded active execution timeout became Loop 63, declarative fallback transitions became Loop 64, SQLite audit integrity became Loop 65, bounded trigger inputs became Loop 66, declarative trigger input contracts became Loop 67, bounded service request admission became Loop 68, stable workflow version promotion aliases became Loop 69, and published artifact integrity verification became Loop 70 after review of the preceding evidence; remaining capabilities become numbered loops only after preceding evidence is reviewed.

Verified offline backup/restore, copy-on-write state migration, bounded telemetry export, copy-on-write retention/disposal, durable cooperative cancellation, fail-closed interrupted-run recovery, isolated wheel qualification, secure first-run initialization, an installed first-value workflow journey, read-only startup diagnostics, descriptor-bound connector credentials, a bounded live Operator read surface, a manually reviewed least-privilege Linux service unit, an authenticated human-gate decision route, protected remote operator action clients, bounded redacted run detail, bounded redacted run discovery, a bounded redacted support bundle, durable SQLite trigger idempotency, bounded active execution timeout, declarative connector fallback transitions, tamper-evident SQLite audit verification, bounded trigger input validation, declarative trigger input contracts, bounded service request admission, stable workflow version promotion aliases, and published artifact integrity verification are achieved by Loops 44-70. Production Baseline remains directional until the remaining candidate evidence is selected, delivered, and reviewed; these controls do not advance project maturity by themselves.

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

## Rolling Loop Queue

This rolling queue is ordered. Loop 70 is complete and there is no active delivery loop; select the next Production Baseline item only after reviewing the artifact-integrity evidence.

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
| Control plane | Publish immutable workflow versions, promote stable aliases, trigger runs from CLI/webhook/schedules with SQLite idempotency, query audit evidence, export read-only operator snapshots, inspect redacted runs, and write a redacted support bundle |
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
