# Roadmap

This roadmap turns the approved `skill2workflow` design into small, verifiable delivery loops. Each loop should leave behind a runnable command, tests, documentation, and an inspectable artifact.

## Product Direction

The near-term target is a self-hosted, single-tenant workflow runtime for one team. The project remains local-first and dependency-light while adding the minimum controls needed for a durable production path.

Workflow DSL remains the authoritative execution source of truth. LiteGraph and future UI layers are editors and views, not runtime authorities. The approved foundation remains in `docs/superpowers/specs/2026-07-01-skill2workflow-design.md`, and the production roadmap design is recorded in `docs/superpowers/specs/2026-07-11-production-roadmap-design.md`.

## Status At A Glance

- Published release: `v0.1.0`
- Workflow DSL compatibility line: `0.1.x` artifacts using `schema_version: "0.1.0"`
- Completed delivery loops: 1-40
- Current maturity: Controlled Live Pilot
- Active loop: None; Loop 40 is complete with validated redacted evidence
- Next maturity gate: Self-hosted Beta
- Next decision: select or defer Loop 41 after the controlled-Pilot review

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

This gate requires a long-running service boundary, authenticated ingress, a production credential boundary, durable recurring scheduling, restart recovery, and concurrency-safe dispatch for one self-hosted instance.

SQLite is the minimum production persistence baseline for Self-hosted Beta. JSON and JSONL remain supported for examples, local development, and evaluation.

### Production Baseline

**Status:** Directional; no loop numbers assigned.

Candidate evidence includes backup and restore, upgrade and migration policy, cancellation and retention behavior, logs or metrics export, fault drills, contract stability, and sustained real-team operating evidence. These capabilities become numbered loops only after Self-hosted Beta evidence is reviewed.

## Active Loop

### Loop 40: Controlled Live Connector Pilot

**Status:** Complete with the recorded `continue` decision.

**Prior basis:** The Lark/Feishu task connector has package-level and pilot-workflow dry-run evidence, including the sales renewal risk workflow after a manual control gate. Loop 39 also produced the redacted connector-validation note at `docs/lark-live-connector-validation.md`. Live behavior remains limited to the fixed `create_task` action. The one scoped live connector validation is not the controlled real-team business-workflow pilot required for Loop 40.

**Outcome:** A separately authorized paid assisted Pilot completed five approved real task creations across five distinct `Asia/Shanghai` calendar days, using two opaque private case identifiers. It also recorded one independent human rejection with no connector invocation, completed the disabled-live and rollback exercises, and passed all seven fixed verification commands. Partner and operator both acknowledged the final `continue` decision.

**Evidence:** [`docs/pilot-evidence/loop-40/`](docs/pilot-evidence/loop-40/) contains the finalized allowlisted charter, run summaries, safety exercises, verification result, decision, and evidence index. It intentionally excludes business values, task identifiers, provider response bodies, and credentials.

**Safety outcome:** The earlier failed workspace remains closed and retained as a historical incident record; it was never retried. The completed Pilot used a fresh authorization boundary. Each approved run remained human-gated, used only a short-lived token in memory, and the finalized evidence contains no raw provider or credential material. The connector continues to provide a no-Vault, no-network `preflight` before a future human-gated run.

**Historical deferral:** [`docs/controlled-pilot-deferral-review.md`](docs/controlled-pilot-deferral-review.md) records the prior normalized failure and its stop rule. It is not completion evidence and did not contribute to this completed Pilot.

The dry-run behavioral baseline remains available through:

```bash
python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot
```

Loop 40 advances maturity only to Controlled Live Pilot. It does not authorize additional Lark/Feishu API behavior, hosted multi-tenancy, or Self-hosted Beta claims.

## Rolling Loop Queue

This rolling queue is ordered. Loop 40 is complete and there is no active delivery loop; select the next loop after reviewing the completed controlled-Pilot evidence.

| Loop | Status | Goal | Exit artifact |
| --- | --- | --- | --- |
| Loop 39: Scoped Live Lark Task Connector | Complete | Explicit live `create_task` opt-in, fake-transport coverage, native provider idempotency, redaction and rollback boundaries, and one redacted real-validation evidence note |
| Loop 40: Controlled Live Connector Pilot | Complete | Paid assisted Pilot completed under the fixed live `create_task` boundary with five approved real tasks, five days, two cases, a rejection, safety exercises, and verification | Finalized redacted evidence at `docs/pilot-evidence/loop-40/`; maturity advances to Controlled Live Pilot |
| Loop 41: Self-hosted Runtime Service Boundary | Candidate | Add one long-running service entry point with validated configuration | Health/readiness checks, graceful shutdown, and restart continuity evidence |
| Loop 42: Authenticated Ingress And Production Credentials | Candidate | Require authentication by default for the production service path and resolve credential handles at execution time | Compact security audit evidence and a documented external TLS termination boundary |
| Loop 43: Durable Recurring Scheduling And Safe Dispatch | Candidate | Persist recurring schedules with restart recovery and a defined missed-run policy | Durable dispatch records and lease or locking semantics for one SQLite-backed service instance |

Loop 40 is complete. Any future Pilot must begin under a new authorization boundary and still produce reproducible controlled live-pilot evidence, explicit failure and rollback exercises, and a decision to continue, harden, or defer broader live integration work. The repository must not commit live credentials or raw live payload evidence.

Loop 41 keeps the runtime scope single-instance and single-tenant. It does not introduce worker coordination or a multi-tenant service boundary.

Loop 42 requires authentication by default on the production service path, credential-handle resolution, compact security audit evidence, and external TLS termination. It does not introduce multi-tenant RBAC, an OAuth platform, or a hosted secret manager.

Loop 43 covers persistent recurring schedules, restart recovery, missed-run policy, durable dispatch records, and lease or locking semantics for one SQLite-backed service instance. Duplicate suppression relies on persisted dispatch state and workflow or connector idempotency; the roadmap must not claim exactly-once execution.

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
| Runtime | Execute and resume durable runs with JSON or SQLite state, human gates, retry/recovery policy, run context, and connector events |
| Control plane | Publish immutable workflow versions, trigger runs from CLI/webhook/schedules, query audit evidence, and export read-only operator snapshots |
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
