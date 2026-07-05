# Roadmap

This roadmap turns the approved `skill2workflow` design into an open-source delivery plan. It is intentionally organized around small closed loops: every milestone should produce runnable commands, tests, and a concrete artifact that future contributors can inspect.

The execution source of truth remains the Workflow DSL. LiteGraph and future UI layers are editors and views, not runtime authorities.

## Current Status

`main` now contains a runnable local harness. It demonstrates the five-layer architecture in local form and proves the core product direction: standard Agent skills can be compiled into workflow definitions that are controlled by a durable execution and control-plane layer.

Current capability snapshot:

- Skill ingestion: `SKILL.md` frontmatter, hard gates, and ordered checklist steps become Skill IR
- DSL authority: Skill IR compiles to Workflow DSL, with JSON Schema and structured validation errors
- Visual layer: Workflow DSL renders to LiteGraph JSON, and safe visual edits can write back to DSL
- Runtime: local executor supports run state, human-gate pause/resume, connector retry policy, recovery events, run listing, and run detail
- Control plane: immutable workflow publish, version lifecycle, published-version runs, resume, audit log, filtered audit queries, and promoted runtime policy events
- Durability: JSON/JSONL remains the dependency-light default; SQLite is available for run state, workflow registry metadata, and audit events
- Connector runtime: built-in manual and HTTP connector manifests, `tool_call` binding validation, HTTP execution, deterministic local connector tests, normalized HTTP errors/timeouts, connector docs, and connector audit events
- Credential boundary and secret hygiene: documented placeholder rules, committed-fixture scanner, and CI guardrail for obvious secret-like values
- Authoring experience: example workflow gallery, richer LiteGraph inspector fields, safe action/retry/HTTP request write-back, and authoring docs
- Workflow example pack: sales follow-up, customer service escalation, risk review, and operations analysis examples with synchronized DSL and LiteGraph fixtures
- Open-source readiness: contributor guide, issue templates, release notes, Workflow DSL compatibility policy, and stability boundaries
- Local control-plane UI: read-only snapshot export, derived operator insights, and static inspector for attention items, recent events, connector events, workflows, runs, audit events, connectors, and version comparisons
- Demo onboarding: one-command local demo workspace generation with Workflow DSL, LiteGraph, run state, audit, and control-plane snapshot artifacts
- Packaging and installability: package metadata guardrails, editable install smoke, and installed `skill2workflow` console-script verification
- Runtime policy and recovery: connector-node retry execution, retry/recovery run events, and published-run policy audit promotion
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

Still needed before serious pilots:

- A local trigger boundary so external tools can start published runs without shelling out ad hoc.
- Trigger input and run context semantics so workflows can receive business data safely.
- Credential provider interfaces so connector examples can evolve beyond placeholders without putting secrets in Workflow DSL.
- Optional local webhook or adapter surfaces for integration testing.
- Better run/audit overlays in the visual authoring experience.
- Clear pilot playbooks that define what is supported, what is experimental, and what must stay outside the bootstrap runtime.

Pilot sequencing rule: do not add product-specific SaaS connectors before local trigger, run input, and credential-provider boundaries are tested and documented.

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

## Active Roadmap

Future work should stay in small closed loops. A loop is complete only when it has a CLI path, tests, documentation, and a merged PR.

Post-`v0.1.0` work now has one active priority after Loop 22 made connector examples safer:

1. expose a controlled local trigger surface so external tools can start published workflow runs without bypassing Workflow DSL validation, version binding, or audit.

### Loop 23: Trigger And Local Run API

Goal: let local systems trigger published workflow runs through a small, testable API boundary instead of requiring every integration to shell out directly to `run-published`.

Why this is next: current runs are already durable and auditable, but external systems still need a stable entry point. Loop 23 should create that entry point while keeping all existing control-plane guarantees.

Status: next engineering loop.

Initial PR boundary:

- Start from the existing `run-published` control-plane path.
- Keep Workflow DSL authoritative and published workflow artifacts immutable.
- Prefer a local, dependency-free trigger envelope and deterministic tests before adding background workers.
- Do not add hosted webhooks, SaaS callbacks, RBAC, queues, or distributed scheduling in this loop.

Scope:

- Define a trigger request envelope for workflow id, version, input metadata, and idempotency placeholder fields
- Add a local API/helper path that starts published runs through the existing control plane
- Return structured run identity and status output
- Document local trigger boundaries and future webhook/server responsibilities

Acceptance criteria:

- Triggered runs use immutable published workflow artifacts
- Triggered runs write the same control-plane audit events as `run-published`
- Invalid workflow id/version inputs return structured errors
- Existing CLI and storage behavior remains compatible
- No daemon, hosted service, queue, auth system, or runtime dependency is introduced

Loop 23 implementation slices:

1. Trigger envelope contract
   - Define the local request and response shape without changing Workflow DSL `0.1.0`.
2. Control-plane trigger helper
   - Add a small helper that delegates to the existing published-run path.
3. CLI or script entry
   - Provide a runnable local command for trigger smoke tests.
4. Docs and examples
   - Document how local tools can trigger runs safely.
5. Verification
   - Run full tests, demo onboarding, package smoke, and secret hygiene.

Loop 23 explicit non-goals:

- Do not add hosted webhooks.
- Do not add a long-running daemon.
- Do not add queues or distributed scheduling.
- Do not add RBAC, IAM, or secret injection.
- Do not introduce runtime dependencies.

Loop 23 expected file changes:

- `tests/` for trigger envelope and published-run audit behavior.
- `src/skill2workflow/control_plane.py` or a focused trigger module.
- `src/skill2workflow/cli.py` or `scripts/` for a local trigger command.
- `README.md`, `HARNESS.md`, and a focused trigger doc.

Loop 23 verification commands:

- `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- `python3 -m py_compile src/skill2workflow/*.py`
- `python3 scripts/demo_bootstrap.py --work-dir /tmp/skill2workflow-demo`
- `python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke`
- `python3 scripts/secret_hygiene.py examples/workflows`
- focused trigger tests documented in the PR
- `git diff --check`

Loop 23 done means:

- Local tools have a documented way to start published workflow runs.
- Triggered runs remain version-bound, auditable, and compatible with existing storage modes.
- Future webhook or scheduler work has a tested local boundary to build on.

## Near-Term Loop Queue

This queue is ordered by what most improves open-source adoption after the first release. Treat it as a planning queue, not a commitment to implement all items without review.

| Loop | Status | Goal | Expected artifact |
| --- | --- | --- | --- |
| Loop 23: Trigger And Local Run API | Next | Start published workflow runs through a controlled local trigger boundary | trigger envelope, local trigger command, audit tests |
| Loop 24: Workflow Inputs And Run Context | Planned | Carry trigger input metadata into run state and node execution context | input contract, run context persistence, executor tests |
| Loop 25: Credential Provider Interface | Planned | Reference credentials without storing secret values in Workflow DSL | provider protocol, placeholder-to-handle docs, local tests |
| Loop 26: Local Webhook Adapter | Planned | Let local HTTP events trigger published runs through the Loop 23 boundary | stdlib webhook adapter, trigger examples, audit tests |
| Loop 27: Run Overlay In Visual Editor | Planned | Inspect run state and audit evidence on top of the workflow graph | graph overlay export, static UI updates, snapshot tests |
| Loop 28: Pilot Playbook And Example | Planned | Document an end-to-end enterprise pilot path with supported limits | pilot guide, runnable scenario, verification checklist |

Loop selection rules:

- Pick the next loop only after the previous loop is merged or explicitly deferred.
- Keep implementation local-first and dependency-light unless a spec-backed capability requires otherwise.
- Prefer examples and guardrails that make the current runtime easier to trust before adding new platform surface area.
- Do not add product-specific SaaS connectors until trigger inputs and credential-provider boundaries are in place.

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

Status: first MVP shipped in Loop 10. Runtime hardening shipped in Loop 17. Retry execution shipped in Loop 21. Credential fixture hygiene shipped in Loop 22. Future work should add credential providers and product-specific extensions only when backed by tests and docs.

- Connector manifests
- Connector binding validation
- Manual and HTTP connector implementations
- Connector execution audit events
- Connector test fixtures
- Connector-node retry execution
- Committed-fixture secret hygiene guardrails
- Future: credential providers, secret injection boundaries, and product-specific connector packages

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

Status: planned for Loops 23-24.

- Controlled local trigger envelope
- Published-run API/helper path
- Structured trigger response
- Run input metadata and execution context
- Audit coverage for triggered runs
- Future: local webhook adapter and scheduled triggers

### v0.7: Pilot Integration Boundary

Status: planned after local trigger and input semantics are stable.

- Credential provider interface
- Secret-handle documentation without secret storage in Workflow DSL
- Optional local webhook adapter
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
