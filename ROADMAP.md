# Roadmap

This roadmap turns the approved `skill2workflow` design into small, verifiable delivery loops. Each loop should leave behind a runnable command, tests, documentation, and an inspectable artifact.

## Product Direction

The near-term target is a self-hosted, single-tenant workflow runtime for one team. The project remains local-first and dependency-light while adding the minimum controls needed for a durable production path.

Workflow DSL remains the authoritative execution source of truth. LiteGraph and future UI layers are editors and views, not runtime authorities. The approved foundation remains in `docs/superpowers/specs/2026-07-01-skill2workflow-design.md`, and the production roadmap design is recorded in `docs/superpowers/specs/2026-07-11-production-roadmap-design.md`.

## Status At A Glance

- Published release: `v0.1.0`
- Workflow DSL compatibility line: `0.1.x` artifacts using `schema_version: "0.1.0"`
- Completed delivery loops: 1-38
- Current maturity: Local Evaluation
- Active loop: Loop 39, Scoped Live Lark Task Connector
- Next maturity gate: Controlled Live Pilot
- Next decision: validate the scoped live action in a controlled pilot or explicitly defer broader live behavior

## Production Readiness Path

### Local Evaluation

**Status:** Achieved.

The repository can compile, validate, publish, trigger, execute, pause, resume, audit, and visualize workflows locally. It includes JSON and SQLite state, controlled connector boundaries, local pilot scenarios, and an out-of-core Lark task connector in dry-run mode.

### Controlled Live Pilot

**Target loops:** 39-40.

This gate requires one explicitly enabled live connector action plus controlled pilot evidence. It does not imply general live SaaS readiness.

### Self-hosted Beta

**Target loops:** 41-43.

This gate requires a long-running service boundary, authenticated ingress, a production credential boundary, durable recurring scheduling, restart recovery, and concurrency-safe dispatch for one self-hosted instance.

SQLite is the minimum production persistence baseline for Self-hosted Beta. JSON and JSONL remain supported for examples, local development, and evaluation.

### Production Baseline

**Status:** Directional; no loop numbers assigned.

Candidate evidence includes backup and restore, upgrade and migration policy, cancellation and retention behavior, logs or metrics export, fault drills, contract stability, and sustained real-team operating evidence. These capabilities become numbered loops only after Self-hosted Beta evidence is reviewed.

## Active Loop

### Loop 39: Scoped Live Lark Task Connector

**Status:** Next engineering loop.

**Goal:** Implement only the Loop 38-approved Lark/Feishu `create_task` live action behind explicit opt-in while keeping dry-run mode as the default.

**Why now:** Loop 36 proved the out-of-core package boundary, Loop 37 proved the connector in a sales renewal risk workflow after a manual control gate, and Loop 38 approved implementation after package-level and pilot-workflow dry-run evidence. The remaining risk is disciplined live execution without weakening credential isolation, duplicate prevention, audit redaction, rollback, or Workflow DSL compatibility.

**Decision boundary:** Loop 38 approved only scoped live `create_task` work. Any broader Lark/Feishu API behavior requires another readiness review. The full decision is recorded in `docs/lark-live-connector-readiness.md`.

Approved scope:

- Connector id and kind: `lark_task`
- Operation: `create_task`
- Live mode: `live`
- Default mode: `dry_run`
- Credential handle: `lark_bot_access_token`
- Idempotency key: derived from `workflow_id + version + run_id + node_id`
- Test transport: fake Lark HTTP receiver or injected fake transport; no live network in CI
- Evidence: compact connector and audit metadata only

Implementation order:

1. Add failing tests for opt-in, credential resolution, success, API failures, timeout, malformed responses, and redaction.
2. Add idempotency and duplicate-prevention tests before outbound request code.
3. Implement the minimal live `create_task` action.
4. Prove existing dry-run tests and smokes remain unchanged.
5. Update connector documentation without changing Workflow DSL compatibility.

Acceptance criteria:

- The project can create one live Lark/Feishu task through an explicitly enabled local connector path.
- Live behavior requires a feature flag or equivalent explicit opt-in.
- Dry-run remains the default for examples, CI, and contributor onboarding.
- Credential handling and audit redaction rules are explicit in code, tests, and docs.
- Resolved credentials, authorization headers, raw task values, raw request bodies, and raw response payloads never enter run state, audit, snapshots, or connector summaries.
- Duplicate task creation is blocked for the same derived idempotency key.
- `401 or 403`, rate limits, network timeouts, validation failures, and malformed responses become normalized failures where possible.
- The live path can be disabled or reverted without changing Workflow DSL compatibility.

Required verification:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/secret_hygiene.py examples/workflows
python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot
git diff --check
```

Explicitly excluded from Loop 39:

- OAuth and token refresh
- Hosted callbacks or ingress
- Automatic connector discovery or package installation
- Marketplace indexing
- Queues or production scheduling
- Other Lark/Feishu APIs or operations

## Rolling Loop Queue

This rolling queue is ordered, but only Loop 39 is committed. Select the next loop after reviewing evidence from the previous one; candidate loop numbers may change when that evidence changes the plan.

| Loop | Status | Goal | Exit artifact |
| --- | --- | --- | --- |
| Loop 39: Scoped Live Lark Task Connector | Next | Implement the approved live `create_task` path behind explicit opt-in | Tested live path, fake-transport evidence, and updated docs |
| Loop 40: Controlled Live Connector Pilot | Candidate | Exercise Loop 39 through a controlled real-team pilot | Controlled live-pilot runbook, redacted run and audit evidence, failure and rollback exercises, and a continue/harden/defer decision |
| Loop 41: Self-hosted Runtime Service Boundary | Candidate | Add one long-running service entry point with validated configuration | Health/readiness checks, graceful shutdown, and restart continuity evidence |
| Loop 42: Authenticated Ingress And Production Credentials | Candidate | Require authentication by default for the production service path and resolve credential handles at execution time | Compact security audit evidence and a documented external TLS termination boundary |
| Loop 43: Durable Recurring Scheduling And Safe Dispatch | Candidate | Persist recurring schedules with restart recovery and a defined missed-run policy | Durable dispatch records and lease or locking semantics for one SQLite-backed service instance |

Loop 40 must produce a reproducible controlled live-pilot runbook, redacted evidence, explicit failure and rollback exercises, and a decision to continue, harden, or defer broader live integration work. The repository must not commit live credentials or raw live payload evidence.

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

- Workflow DSL remains the execution truth source.
- Parser, compiler, validator, executor, connector, storage, or CLI behavior changes start with tests.
- User-facing capabilities need a CLI path before becoming UI-only controls.
- Each loop must define scope, exclusions, acceptance evidence, and verification commands.
- Prefer small closed loops over broad platform shells.
- Avoid runtime dependencies unless they directly unlock an approved, spec-backed capability.
- Update this file when a loop is selected, completed, or explicitly deferred; keep implementation detail in the matching plan or guide.
