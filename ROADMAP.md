# Roadmap

This roadmap turns the approved `skill2workflow` design into an open-source delivery plan. It is intentionally organized around small closed loops: every milestone should produce runnable commands, tests, and a concrete artifact that future contributors can inspect.

The execution source of truth remains the Workflow DSL. LiteGraph and future UI layers are editors and views, not runtime authorities.

## Current Status

`main` now contains a runnable local harness. It demonstrates the five-layer architecture in local form and proves the core product direction: standard Agent skills can be compiled into workflow definitions that are controlled by a durable execution and control-plane layer.

Current capability snapshot:

- Skill ingestion: `SKILL.md` frontmatter, hard gates, and ordered checklist steps become Skill IR
- DSL authority: Skill IR compiles to Workflow DSL, with JSON Schema and structured validation errors
- Visual layer: Workflow DSL renders to LiteGraph JSON, read-only run overlays can be attached to nodes, and safe visual edits can write back to DSL
- Runtime: local executor supports run state, initial run context, human-gate pause/resume, connector retry policy, recovery events, run listing, and run detail
- Control plane: immutable workflow publish, version lifecycle, published-version runs, local trigger API with durable input context, deterministic local schedules, resume, audit log, filtered audit queries, promoted runtime policy events, and compact node overlay export
- Durability: JSON/JSONL remains the dependency-light default; SQLite is available for run state, workflow registry metadata, and audit events
- Connector runtime: built-in manual and HTTP connector manifests, `tool_call` binding validation, HTTP execution, body-only trigger input mapping, local credential handles, deterministic local connector tests, normalized HTTP errors/timeouts, connector docs, and connector audit events
- Credential boundary and secret hygiene: documented placeholder and handle rules, local credential-file provider, committed-fixture scanner, and CI guardrail for obvious secret-like values
- Authoring experience: example workflow gallery, richer LiteGraph inspector fields, safe action/retry/HTTP request write-back, and authoring docs
- Workflow example pack: sales follow-up, customer service escalation, risk review, and operations analysis examples with synchronized DSL and LiteGraph fixtures
- Open-source readiness: contributor guide, issue templates, release notes, Workflow DSL compatibility policy, and stability boundaries
- Local control-plane UI: read-only snapshot export, derived operator insights, and static inspector for attention items, recent events, connector events, node overlays, workflows, runs, audit events, connectors, and version comparisons
- Demo onboarding: one-command local demo workspace generation with Workflow DSL, LiteGraph, run state, audit, and control-plane snapshot artifacts
- Packaging and installability: package metadata guardrails, editable install smoke, and installed `skill2workflow` console-script verification
- Runtime policy and recovery: connector-node retry execution, retry/recovery run events, and published-run policy audit promotion
- Local webhook adapter: dependency-free local `POST /webhooks/<workflow_id>/<version>` path that invokes the existing trigger boundary without hosted ingress
- Pilot playbook: one-command local customer-support pilot smoke with webhook trigger, durable input, manual gate resume, credential handle, HTTP connector execution, audit, snapshot, and LiteGraph overlay artifacts
- Scheduled trigger boundary: deterministic one-shot local schedule definitions, due-run CLI, trigger-boundary execution, audit metadata, and snapshot inspection
- Release automation: read-only release preflight checks, CI dry-run coverage, and maintainer release-process docs

Important boundaries:

- Published workflow artifacts remain immutable JSON documents in both storage modes.
- The visual graph is an editor/view. Workflow DSL remains the execution truth source.
- Connector runtime is an MVP boundary. Enterprise credential management, connector marketplaces, and product-specific connectors remain later work.
- Visual write-back is allowlisted. Topology, node ids, transition targets, and connector identity remain DSL-controlled.
- `0.1.x` compatibility is documented for Workflow DSL `0.1.0`; undocumented internals remain experimental.

## Real Team Pilot Readiness

The project is now useful for local evaluation and contributor onboarding. A real team pilot still needs a few controlled loops before the runtime should be positioned as an operational workflow system.

Ready now:

- Convert structured `SKILL.md` examples into validated Workflow DSL.
- Inspect and safely edit workflows through the LiteGraph-style view.
- Publish immutable workflow versions locally.
- Run and resume published workflows with JSON or SQLite state.
- Audit run lifecycle, connector events, retry/recovery events, and control-plane operations.
- Demonstrate the complete local bootstrap from a fresh checkout.
- Verify package installability and fixture secret hygiene in CI.
- Trigger published workflows through a controlled local API envelope.
- Pass local trigger input values into durable run context while keeping audit output compact.
- Map non-secret trigger input into HTTP connector request bodies through an explicit body-only contract.
- Reference connector credentials through local handles without storing resolved values in Workflow DSL, run state, or audit events.
- Receive local HTTP webhook events and route them through the same published trigger boundary.
- Trigger published workflows from deterministic one-shot local schedules.
- Inspect read-only node-level run and audit overlays in the LiteGraph editor and local control-plane UI.
- Follow a documented local pilot playbook with a runnable customer-support escalation scenario.

Still needed before serious pilots:

- A connector extension contract for product-specific connector packages.
- A broader pilot scenario pack that reuses the same trigger, schedule, credential, mapping, audit, and overlay boundaries.
- Production-grade recurring schedulers remain out of scope until the local trigger, mapping, and extension contracts are stable.

Pilot sequencing rule: do not add product-specific SaaS connectors until the connector extension contract is tested and documented. Trigger input is durable, but credential material must stay outside trigger input and immutable workflow artifacts.

## Completed Loops

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

## Active Roadmap

Future work should stay in small closed loops. A loop is complete only when it has a CLI path, tests, documentation, and a merged PR.

Post-`v0.1.0` work now has one active priority after Loop 30 added body-only trigger input mapping:

1. define a stable connector extension contract before adding product-specific SaaS connectors.

The next queued follow-on is a pilot scenario pack that proves the extension boundary can support more than the current customer-support smoke without adding real SaaS dependencies.

### Loop 31: Connector Extension Contract

Goal: define how future connector packages plug into the local runtime without weakening Workflow DSL authority, credential boundaries, audit compactness, or dependency discipline.

Why this is next: the built-in HTTP connector can now receive event-specific non-secret input. The next adoption blocker is not another product integration; it is a stable extension boundary that lets contributors add product-specific connectors later without baking secrets, SDK assumptions, or platform-specific behavior into the core harness.

Status: next engineering loop.

Initial PR boundary:

- Document a connector extension manifest shape for local, stdlib-first connector packages.
- Define runtime-facing responsibilities: connector identity, supported node types, request/config schema metadata, credential handle expectations, audit fields, and test requirements.
- Keep built-in `manual` and `http` behavior unchanged.
- Add a local contract test fixture or dummy connector only if it proves the extension boundary without introducing a real SaaS dependency.
- Do not add product-specific connectors in this loop.

Loop 31 first implementation cut:

- Treat the existing built-in `manual` and `http` connectors as reference implementations for the contract.
- Document required manifest fields and optional metadata fields without introducing a dynamic plugin loader.
- Define the execution handoff shape for future connector executors: node binding input, run context input, credential provider boundary, normalized result, and audit-safe summary.
- Add contract tests only around stable metadata and registry behavior; avoid test-only loaders that imply extension loading is already supported.
- Update public docs so contributors know where extension packages should live later and which runtime hooks are intentionally not available yet.

Acceptance criteria:

- Contributors can understand what a connector extension must declare and what the core runtime will and will not call.
- Credential values remain outside Workflow DSL, trigger input, run state, and audit events.
- Audit guidance stays compact and value-free by default.
- Existing connector tests and examples continue to pass unchanged.
- Documentation clearly separates built-in connector runtime support from future extension packages.

Loop 31 implementation slices:

1. Extension contract
   - Specify manifest fields, versioning expectations, supported node types, and config/request metadata boundaries.
   - Clarify how extension connectors relate to Workflow DSL `connector.id` and `connector.kind`.
2. Runtime boundary
   - Identify the minimal executor/connector registry seams future extensions need.
   - Avoid a plugin loader unless the contract cannot be documented or tested without one.
3. Credential and audit rules
   - Require handle-based credential references and compact audit metadata.
   - Keep resolved values and mapped payload values out of audit output.
4. Tests and fixtures
   - Add contract-level tests for manifest validity or registry behavior if implementation is touched.
   - Keep tests local-only and dependency-free.
5. Documentation
   - Update `docs/connectors.md`, `docs/credential-boundary.md`, `docs/stability.md`, and contributor guidance.

Loop 31 expected file changes:

- `docs/connectors.md` for the extension manifest and executor contract.
- `docs/credential-boundary.md` for extension credential-handle requirements.
- `docs/stability.md` and `docs/workflow-dsl-compatibility.md` for stable versus experimental connector boundaries.
- `CONTRIBUTING.md` or `HARNESS.md` if contributor workflows change.
- `src/skill2workflow/connectors.py`, `tests/test_connectors.py`, or `tests/test_control_plane.py` only if the registry needs small contract-level metadata changes.
- `ROADMAP.md` when Loop 31 is complete.

Loop 31 explicit non-goals:

- Do not add Salesforce, Feishu/Lark, Slack, GitHub, Jira, or other product-specific connector packages.
- Do not add hosted credential storage, OAuth flows, IAM, callback verification, queues, or a connector marketplace.
- Do not introduce arbitrary expression engines or broaden Loop 30 mapping beyond the documented body-only contract.

Loop 31 verification commands:

- `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- `python3 -m py_compile src/skill2workflow/*.py`
- `python3 scripts/secret_hygiene.py examples/workflows`
- `git diff --check`

Loop 31 done means:

- The project has a documented, test-backed extension boundary that product-specific connectors can follow in later loops.
- Built-in connector behavior remains stable and examples remain valid.
- The public docs make clear that connector extensions must preserve Workflow DSL authority, credential isolation, and compact audit semantics.

### Loop 32: Pilot Scenario Pack

Goal: add more end-to-end local pilot scenarios that prove the current trigger, schedule, credential, input mapping, audit, snapshot, and overlay boundaries generalize beyond one customer-support example.

Status: queued after Loop 31.

Start condition: Loop 31 has documented the connector extension boundary, even if no product-specific connector packages exist yet.

Initial PR boundary:

- Add local-only scenarios that use existing built-in connectors and documented placeholders.
- Prefer business workflows that enterprise evaluators recognize: sales renewal follow-up, risk exception review, operations alert triage, or approval-heavy back-office routing.
- Reuse the same smoke-helper pattern as `scripts/pilot_playbook_smoke.py`.
- Keep real SaaS APIs, OAuth, hosted ingress, and production schedulers out of scope.

Loop 32 done means:

- A fresh checkout can run multiple pilot smokes without external services.
- The examples demonstrate trigger input, body-only mapping, credential handles, manual gates, audit, snapshots, and visual overlays in repeatable ways.
- The project has stronger evidence for real team pilots before product-specific connector packages begin.

## Near-Term Loop Queue

This queue is ordered by what most improves open-source adoption after the first release. Treat it as a planning queue, not a commitment to implement all items without review.

| Loop | Status | Goal | Expected artifact |
| --- | --- | --- | --- |
| Loop 24: Workflow Inputs And Run Context | Complete | Carry trigger input metadata into run state and node execution context | input contract, run context persistence, executor tests |
| Loop 25: Credential Provider Interface | Complete | Reference credentials without storing secret values in Workflow DSL | provider protocol, placeholder-to-handle docs, local tests |
| Loop 26: Local Webhook Adapter | Complete | Let local HTTP events trigger published runs through the trigger boundary | stdlib webhook adapter, trigger examples, audit tests |
| Loop 27: Run Overlay In Visual Editor | Complete | Inspect run state and audit evidence on top of the workflow graph | graph overlay export, static UI updates, snapshot tests |
| Loop 28: Pilot Playbook And Example | Complete | Document an end-to-end enterprise pilot path with supported limits | pilot guide, runnable scenario, verification checklist |
| Loop 29: Scheduled Trigger Boundary | Complete | Trigger published workflows from deterministic local schedules | schedule contract, CLI/helper path, audit tests |
| Loop 30: Trigger Input Mapping | Complete | Map trigger context into connector request bodies without leaking secrets | input mapping contract, validator tests, connector examples |
| Loop 31: Connector Extension Contract | Next | Define stable boundaries for product-specific connectors after input mapping | connector protocol docs, manifest contract, local test harness |
| Loop 32: Pilot Scenario Pack | Planned | Add more end-to-end pilot scenarios using triggers, schedules, credentials, and mapped connector input | scenario fixtures, smoke helpers, operator checklist |

Loop selection rules:

- Pick the next loop only after the previous loop is merged or explicitly deferred.
- Keep implementation local-first and dependency-light unless a spec-backed capability requires otherwise.
- Prefer examples and guardrails that make the current runtime easier to trust before adding new platform surface area.
- Do not add product-specific SaaS connectors until the connector extension contract is in place.

## Release Tag Plan

Release tags use semantic versioning. The first public tag is `v0.1.0`; it packages the current local bootstrap through Loop 13, including parser, compiler, validator, LiteGraph editor, durable runtime, local control plane, SQLite durability, connector runtime, authoring experience, open-source readiness, and the local control-plane inspector.

### v0.1.0: First Open-Source Bootstrap Release

Status: published in Loop 14.

Release source:

- Branch: `main`
- Tag: `v0.1.0`
- Release: `https://github.com/pearjelly/skill2workflow/releases/tag/v0.1.0`
- Notes: `docs/releases/v0.1.0.md`
- Compatibility: Workflow DSL `0.1.0`, Python 3.9+, standard-library runtime

Release checklist:

- Release preflight passes for the target version and release notes
- Full unit suite passes
- Python modules compile
- Example Workflow DSL fixtures validate
- Release notes match the shipped scope
- Tag and GitHub release are created from the same clean `main`

After this tag, future `0.1.x` releases should be patch-level hardening and docs updates unless they preserve Workflow DSL `0.1.0` compatibility.

## Capability Milestones

The numbered capability milestones below are product roadmap buckets, not already-created Git tags. The first tag, `v0.1.0`, intentionally includes all completed local bootstrap capability buckets through Loop 13.

### v0.1: Bootstrap Harness

Status: delivered by Loops 1-9.

- Parser, compiler, validator, executor, LiteGraph view, write-back, control plane, JSON/SQLite durability
- Suitable for local evaluation and early contributor onboarding

### v0.2: Connector Runtime

Status: first MVP shipped in Loop 10. Runtime hardening shipped in Loop 17. Retry execution shipped in Loop 21. Credential fixture hygiene shipped in Loop 22. Local credential handles shipped in Loop 25. Future work should add product-specific extensions only after the trigger input mapping and connector extension contracts are documented, tested, and dependency-aware.

- Connector manifests
- Connector binding validation
- Manual and HTTP connector implementations
- Connector execution audit events
- Connector test fixtures
- Connector-node retry execution
- Committed-fixture secret hygiene guardrails
- Local credential-provider boundary for handle-based HTTP headers
- Future: connector extension contract and product-specific connector packages

### v0.3: Authoring Experience

Status: first MVP shipped in Loop 11. Enterprise example pack shipped in Loop 16. Read-only run overlays shipped in Loop 27. Future work should improve editor ergonomics and broaden safe write-back only where semantics are explicit.

- Better LiteGraph parameter forms
- Example workflow gallery
- Enterprise example pack for sales, customer service, risk review, and operations analysis
- Expanded safe write-back beyond title and description
- Read-only run/audit overlays in the editor
- Contributor docs for node types and compiler rules
- Future: node creation flows and schema-backed forms

### v0.4: Open Source Release Baseline

Status: first MVP shipped in Loop 12. Release guardrails shipped in Loop 15.

- CONTRIBUTING guide
- Issue templates
- First release notes
- Workflow DSL `0.1.0` compatibility notes
- Clear stable vs experimental API boundaries
- Read-only release preflight command and CI dry-run
- Future: automated GitHub release publishing and signed release artifacts

### v0.5: Local Control Plane UI

Status: first MVP shipped in Loop 13. Operator insights shipped in Loop 18. Node-level run overlays shipped in Loop 27. Future work should keep the local UI read-only until runtime control actions have explicit safety rules.

- Workflow registry view
- Run list and run detail view
- Audit log view
- Connector manifest view
- Published workflow version comparison
- Operator attention, recent event, connector event, and version change summaries
- Per-node run overlay table for status, event counts, connector outcomes, attempts, and retry/recovery evidence
- Future: live local server mode and workflow artifact diff views

### v0.6: Local Trigger And Input Runtime

Status: trigger API shipped in Loop 23; input runtime shipped in Loop 24; local webhook adapter shipped in Loop 26; deterministic local schedules shipped in Loop 29; body-only trigger input mapping shipped in Loop 30.

- Controlled local trigger envelope
- Published-run API/helper path
- Dependency-free local webhook adapter for published workflow triggers
- Structured trigger response
- Trigger metadata on `run_started` audit events
- Audit coverage for triggered runs
- Durable trigger input values under run context
- Compact audit boundary for trigger input keys
- Deterministic local scheduled triggers
- Body-only HTTP connector request input mapping
- Future: mapping variants beyond the body-only contract when pilot evidence requires them

### v0.7: Pilot Integration Boundary

Status: local trigger, input, credential, webhook, scheduled trigger, visual inspection, body-only input mapping, and pilot playbook semantics are stable enough for local evaluation. Connector extension contract work starts in Loop 31.

- Credential provider interface
- Secret-handle documentation without secret storage in Workflow DSL
- Local webhook adapter for pilot integration tests
- Deterministic schedule smoke for recurring local-run evaluation
- Visual run/audit overlays
- Pilot playbook and runnable scenario
- Body-only trigger input mapping into HTTP connector request bodies
- Next: connector extension contract
- Future: product-specific connector packages and hosted control-plane integrations

### v1.0: Production Baseline

Target: support real team pilots while keeping the project local-first and open-source friendly.

- Stable Workflow DSL
- Stable CLI
- Local runtime and control plane suitable for real team pilots
- Extension points documented for nodes, compiler rules, executors, and connectors

## Contribution Lanes

Contributors can help in these areas:

- Parser coverage for real-world `SKILL.md` formats
- Release automation and package verification
- Workflow node types and compiler rules
- Validator improvements and JSON Schema
- LiteGraph node UI and expanded graph-to-DSL write-back
- Executor policies such as retry, timeout, and checkpoint behavior
- Connector manifests and example connectors
- Credential provider boundaries and safe connector examples
- Example workflows for sales, approval, customer service, risk review, and operations analysis
- Documentation and enterprise deployment guides

## Not Yet In Scope

These are intentionally deferred until the local open-source runtime is stronger:

- Cloud-hosted multi-tenant control plane
- Full RBAC or IAM
- Complete BPMN compatibility
- Distributed scheduling
- Complex enterprise connector marketplace
- Guaranteed automatic conversion of arbitrary SOP documents

## Roadmap Rules

- Every milestone must keep the Workflow DSL as the execution truth source.
- Every runtime or compiler change needs tests before behavior changes.
- Every new user-facing capability should have a CLI path before it becomes UI-only.
- Prefer small closed loops over broad platform shells.
- Avoid runtime dependencies unless they directly unlock a spec-backed capability.
