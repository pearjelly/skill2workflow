# Roadmap

This roadmap turns the approved `skill2workflow` design into an open-source delivery plan. It is intentionally organized around small closed loops: every milestone should produce runnable commands, tests, and a concrete artifact that future contributors can inspect.

The execution source of truth remains the Workflow DSL. LiteGraph and future UI layers are editors and views, not runtime authorities.

## Current Status

`main` now contains a runnable local harness. It demonstrates the five-layer architecture in local form and proves the core product direction: standard Agent skills can be compiled into workflow definitions that are controlled by a durable execution and control-plane layer.

Current capability snapshot:

- Skill ingestion: `SKILL.md` frontmatter, hard gates, and ordered checklist steps become Skill IR
- DSL authority: Skill IR compiles to Workflow DSL, with JSON Schema and structured validation errors
- Visual layer: Workflow DSL renders to LiteGraph JSON, and safe visual edits can write back to DSL
- Runtime: local executor supports run state, initial run context, human-gate pause/resume, connector retry policy, recovery events, run listing, and run detail
- Control plane: immutable workflow publish, version lifecycle, published-version runs, local trigger API with durable input context, resume, audit log, filtered audit queries, and promoted runtime policy events
- Durability: JSON/JSONL remains the dependency-light default; SQLite is available for run state, workflow registry metadata, and audit events
- Connector runtime: built-in manual and HTTP connector manifests, `tool_call` binding validation, HTTP execution, local credential handles, deterministic local connector tests, normalized HTTP errors/timeouts, connector docs, and connector audit events
- Credential boundary and secret hygiene: documented placeholder and handle rules, local credential-file provider, committed-fixture scanner, and CI guardrail for obvious secret-like values
- Authoring experience: example workflow gallery, richer LiteGraph inspector fields, safe action/retry/HTTP request write-back, and authoring docs
- Workflow example pack: sales follow-up, customer service escalation, risk review, and operations analysis examples with synchronized DSL and LiteGraph fixtures
- Open-source readiness: contributor guide, issue templates, release notes, Workflow DSL compatibility policy, and stability boundaries
- Local control-plane UI: read-only snapshot export, derived operator insights, and static inspector for attention items, recent events, connector events, workflows, runs, audit events, connectors, and version comparisons
- Demo onboarding: one-command local demo workspace generation with Workflow DSL, LiteGraph, run state, audit, and control-plane snapshot artifacts
- Packaging and installability: package metadata guardrails, editable install smoke, and installed `skill2workflow` console-script verification
- Runtime policy and recovery: connector-node retry execution, retry/recovery run events, and published-run policy audit promotion
- Local webhook adapter: dependency-free local `POST /webhooks/<workflow_id>/<version>` path that invokes the existing trigger boundary without hosted ingress
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
- Reference connector credentials through local handles without storing resolved values in Workflow DSL, run state, or audit events.
- Receive local HTTP webhook events and route them through the same published trigger boundary.

Still needed before serious pilots:

- Better run/audit overlays in the visual authoring experience.
- Clear pilot playbooks that define what is supported, what is experimental, and what must stay outside the bootstrap runtime.

Pilot sequencing rule: do not add product-specific SaaS connectors before local webhook/adapters and pilot playbooks are tested and documented. Trigger input is durable, but credential material must stay outside trigger input and immutable workflow artifacts.

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

## Active Roadmap

Future work should stay in small closed loops. A loop is complete only when it has a CLI path, tests, documentation, and a merged PR.

Post-`v0.1.0` work now has one active priority after Loop 26 added a local webhook adapter:

1. connect run state and audit evidence back into the visual workflow editor without making the graph the execution authority.

### Loop 27: Run Overlay In Visual Editor

Goal: let local operators inspect run status, node outcomes, connector events, and audit evidence directly on top of the workflow graph.

Why this is next: Loops 23-26 created controlled trigger, input, credential, and webhook ingress boundaries. The next pilot-readiness gap is operator visibility: users need to understand what happened in a run without stitching together CLI JSON, audit output, and the static graph manually.

Status: next engineering loop.

Initial PR boundary:

- Keep Workflow DSL authoritative and published workflow artifacts immutable.
- Treat run and audit overlays as read-only view data.
- Reuse existing run state, audit events, and control snapshot exports where possible.
- Do not add live collaboration, hosted dashboards, mutation from the graph, or runtime dependencies.

Scope:

- Define a small graph overlay data shape derived from run state and audit events
- Render node status, current node, connector outcomes, retry/recovery evidence, and trigger metadata in the static editor or control-plane UI
- Keep visual overlay data separate from Workflow DSL source data
- Document how to generate and load overlay inputs from a fresh checkout

Acceptance criteria:

- A local operator can load a workflow plus run/audit evidence and see node-level execution state on the graph
- Overlay data is read-only and cannot mutate Workflow DSL
- Existing control snapshot or visualization commands have tests for any new exported fields
- Documentation explains the publish, trigger/webhook, run, audit, snapshot, and visual inspection flow
- No hosted UI, auth layer, live server mode, or runtime dependency is introduced

Loop 27 implementation slices:

1. Overlay data contract
   - Define a small read-only overlay shape that maps `node_id` to run status, attempt count, connector outcome, retry/recovery evidence, and selected audit references.
   - Derive overlay data from existing run state and audit events. Do not duplicate Workflow DSL topology or mutate workflow artifacts.
   - Preserve the existing `workflow_to_litegraph(..., run_state=...)` path where possible, and add only the minimum fields needed for operator inspection.
2. Snapshot and CLI export path
   - Decide whether overlay data belongs in `control-snapshot`, `visualize --run-state`, or both. Prefer reusing existing snapshot and visualization commands before adding a new command.
   - Keep JSON and SQLite behavior equivalent for any exported run/audit evidence.
   - Ensure exported data remains compact: include identifiers, statuses, event types, node ids, connector ids, attempts, timestamps, and summaries rather than raw connector payloads or trigger input values.
3. Static UI overlay
   - Render node-level status on the LiteGraph editor or control-plane inspector using the overlay data.
   - Make connector failures, retry/recovery events, waiting gates, current node, and terminal status easy to scan.
   - Keep overlay controls read-only. Do not add workflow mutation, graph topology editing, or run control actions in this loop.
4. Tests and fixtures
   - Add unit coverage for overlay derivation from completed, waiting, failed, connector, and retry/recovery runs.
   - Update snapshot or LiteGraph fixture tests only when the committed fixture shape changes.
   - Add focused UI fixture coverage if static assets need deterministic sample data.
5. Documentation and operator flow
   - Document how to publish, trigger or webhook a run, export the relevant artifact, and inspect run/audit evidence visually.
   - Keep the docs explicit that overlay data is view state, not workflow source.
   - Update README/HARNESS only for commands a contributor should actually run from a fresh checkout.

Loop 27 explicit non-goals:

- Do not add a hosted control plane, live multi-user UI, auth, RBAC, IAM, or websocket transport.
- Do not let graph overlay data mutate Workflow DSL, published artifacts, connector identity, edges, transitions, or node ids.
- Do not add workflow run control actions from the static UI.
- Do not store or display resolved credential values, raw authorization headers, raw webhook bodies, or full trigger input payloads in overlay data.
- Do not introduce frontend build tooling or runtime dependencies.

Loop 27 expected file changes:

- `src/skill2workflow/visualizer.py` if overlay data is attached to LiteGraph nodes.
- `src/skill2workflow/dashboard.py` if overlay data is exported through control snapshots.
- `tests/test_visualizer.py` and/or `tests/test_dashboard.py` for overlay shape and fixture coverage.
- `web/` static assets, likely `web/index.html` or `web/control.html`, for read-only overlay rendering.
- `examples/control-plane-snapshot.json` only if the snapshot fixture changes.
- `README.md`, `HARNESS.md`, `docs/authoring.md`, or a focused docs page for the operator inspection flow.

Loop 27 verification commands:

- `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- `python3 -m py_compile src/skill2workflow/*.py`
- `PYTHONPATH=src python3 -m unittest tests.test_visualizer tests.test_dashboard tests.test_cli -v`
- `python3 scripts/demo_bootstrap.py --work-dir /tmp/skill2workflow-demo-loop27`
- `python3 scripts/secret_hygiene.py examples/workflows`
- `git diff --check`

Loop 27 done means:

- Operators can visually inspect run and audit evidence on top of workflow structure without leaving the local artifact workflow.
- Overlay data is deterministic, compact, and read-only.
- Workflow DSL remains the execution source of truth.
- No hosted UI, auth layer, live server mode, or dependency expansion is added.

## Near-Term Loop Queue

This queue is ordered by what most improves open-source adoption after the first release. Treat it as a planning queue, not a commitment to implement all items without review.

| Loop | Status | Goal | Expected artifact |
| --- | --- | --- | --- |
| Loop 24: Workflow Inputs And Run Context | Complete | Carry trigger input metadata into run state and node execution context | input contract, run context persistence, executor tests |
| Loop 25: Credential Provider Interface | Complete | Reference credentials without storing secret values in Workflow DSL | provider protocol, placeholder-to-handle docs, local tests |
| Loop 26: Local Webhook Adapter | Complete | Let local HTTP events trigger published runs through the trigger boundary | stdlib webhook adapter, trigger examples, audit tests |
| Loop 27: Run Overlay In Visual Editor | Next | Inspect run state and audit evidence on top of the workflow graph | graph overlay export, static UI updates, snapshot tests |
| Loop 28: Pilot Playbook And Example | Planned | Document an end-to-end enterprise pilot path with supported limits | pilot guide, runnable scenario, verification checklist |

Loop selection rules:

- Pick the next loop only after the previous loop is merged or explicitly deferred.
- Keep implementation local-first and dependency-light unless a spec-backed capability requires otherwise.
- Prefer examples and guardrails that make the current runtime easier to trust before adding new platform surface area.
- Do not add product-specific SaaS connectors until local webhook/adapters and pilot playbooks are in place.

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

Status: first MVP shipped in Loop 10. Runtime hardening shipped in Loop 17. Retry execution shipped in Loop 21. Credential fixture hygiene shipped in Loop 22. Local credential handles shipped in Loop 25. Future work should add product-specific extensions only when backed by tests and docs.

- Connector manifests
- Connector binding validation
- Manual and HTTP connector implementations
- Connector execution audit events
- Connector test fixtures
- Connector-node retry execution
- Committed-fixture secret hygiene guardrails
- Local credential-provider boundary for handle-based HTTP headers
- Future: product-specific connector packages

### v0.3: Authoring Experience

Status: first MVP shipped in Loop 11. Enterprise example pack shipped in Loop 16. Future work should improve editor ergonomics and broaden safe write-back only where semantics are explicit.

- Better LiteGraph parameter forms
- Example workflow gallery
- Enterprise example pack for sales, customer service, risk review, and operations analysis
- Expanded safe write-back beyond title and description
- Contributor docs for node types and compiler rules
- Future: node creation flows, schema-backed forms, and run/audit overlays in the editor

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

Status: first MVP shipped in Loop 13. Operator insights shipped in Loop 18. Future work should connect run/audit overlays back into the graph view.

- Workflow registry view
- Run list and run detail view
- Audit log view
- Connector manifest view
- Published workflow version comparison
- Operator attention, recent event, connector event, and version change summaries
- Future: live local server mode, graph overlays, and workflow artifact diff views

### v0.6: Local Trigger And Input Runtime

Status: trigger API shipped in Loop 23; input runtime shipped in Loop 24; local webhook adapter shipped in Loop 26.

- Controlled local trigger envelope
- Published-run API/helper path
- Dependency-free local webhook adapter for published workflow triggers
- Structured trigger response
- Trigger metadata on `run_started` audit events
- Audit coverage for triggered runs
- Durable trigger input values under run context
- Compact audit boundary for trigger input keys
- Future: scheduled triggers

### v0.7: Pilot Integration Boundary

Status: planned after local trigger, input, credential, and webhook semantics are stable. Visual run/audit overlay work starts in Loop 27.

- Credential provider interface
- Secret-handle documentation without secret storage in Workflow DSL
- Local webhook adapter for pilot integration tests
- Visual run/audit overlays
- Pilot playbook and runnable scenario
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
