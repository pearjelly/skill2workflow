# Roadmap

This roadmap turns the approved `skill2workflow` design into an open-source delivery plan. It is intentionally organized around small closed loops: every milestone should produce runnable commands, tests, and a concrete artifact that future contributors can inspect.

The execution source of truth remains the Workflow DSL. LiteGraph and future UI layers are editors and views, not runtime authorities.

## Current Status

`main` now contains a runnable local harness. It demonstrates the five-layer architecture in local form and proves the core product direction: standard Agent skills can be compiled into workflow definitions that are controlled by a durable execution and control-plane layer.

Current capability snapshot:

- Skill ingestion: `SKILL.md` frontmatter, hard gates, and ordered checklist steps become Skill IR
- DSL authority: Skill IR compiles to Workflow DSL, with JSON Schema and structured validation errors
- Visual layer: Workflow DSL renders to LiteGraph JSON, and safe visual edits can write back to DSL
- Runtime: local executor supports run state, human-gate pause/resume, run listing, and run detail
- Control plane: immutable workflow publish, version lifecycle, published-version runs, resume, audit log, and filtered audit queries
- Durability: JSON/JSONL remains the dependency-light default; SQLite is available for run state, workflow registry metadata, and audit events
- Connector runtime: built-in manual and HTTP connector manifests, `tool_call` binding validation, HTTP execution, deterministic local connector tests, normalized HTTP errors/timeouts, connector docs, and connector audit events
- Authoring experience: example workflow gallery, richer LiteGraph inspector fields, safe action/retry/HTTP request write-back, and authoring docs
- Workflow example pack: sales follow-up, customer service escalation, risk review, and operations analysis examples with synchronized DSL and LiteGraph fixtures
- Open-source readiness: contributor guide, issue templates, release notes, Workflow DSL compatibility policy, and stability boundaries
- Local control-plane UI: read-only snapshot export and static inspector for workflows, runs, audit events, connectors, and version comparisons
- Release automation: read-only release preflight checks, CI dry-run coverage, and maintainer release-process docs

Important boundaries:

- Published workflow artifacts remain immutable JSON documents in both storage modes.
- The visual graph is an editor/view. Workflow DSL remains the execution truth source.
- Connector runtime is an MVP boundary. Automatic retry execution, enterprise credential management, connector marketplaces, and product-specific connectors remain later work.
- Visual write-back is allowlisted. Topology, node ids, transition targets, and connector identity remain DSL-controlled.
- `0.1.x` compatibility is documented for Workflow DSL `0.1.0`; undocumented internals remain experimental.

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

## Active Roadmap

Future work should stay in small closed loops. A loop is complete only when it has a CLI path, tests, documentation, and a merged PR.

Post-`v0.1.0` work now has one active priority after Loop 17 hardened the connector runtime:

1. improve local operator visibility while keeping Workflow DSL authoritative.

### Loop 18: Control Plane Operator UX

Goal: connect control-plane state back to workflow inspection so local operators can understand runs, audit events, connector outcomes, and workflow version changes without turning the project into a hosted control plane.

Status: next engineering loop.

Initial PR boundary:

- Start from exported local control-plane state and static UI improvements.
- Keep Workflow DSL and published workflow artifacts read-only from the operator UI.
- Prefer snapshot-driven views before adding any local server mode.
- Do not introduce auth, RBAC, hosted services, or live multi-user coordination in this loop.

Scope:

- Improve local control-plane inspection for run state, audit events, connector outcomes, and published workflow versions
- Add graph-adjacent run/audit overlay data where it helps operators reason about execution without mutating workflow DSL
- Make workflow artifact version differences easier to inspect from exported snapshots
- Document the operator flow from publish/run/audit/snapshot to local UI review

Acceptance criteria:

- A local operator can inspect published versions, run status, connector events, audit events, and version comparisons from a static artifact or local UI path
- The operator UI remains read-only and does not become the execution authority
- Snapshot generation has tests for any new fields
- Documentation explains how to generate and inspect the local operator view from a fresh checkout

Loop 18 implementation slices:

1. Snapshot shape review
   - Identify which run, audit, connector, and version comparison fields are already exported and which small additions would improve inspection.
2. Static operator UI improvement
   - Add read-only panels or graph-adjacent overlays that make execution status and connector failures easier to scan.
3. Version comparison clarity
   - Make published workflow version differences easier to inspect without changing immutable artifacts.
4. Operator docs
   - Document the publish, run, audit, snapshot, and local UI inspection flow.

Loop 18 explicit non-goals:

- Do not add a hosted control plane.
- Do not add authentication, RBAC, or multi-tenant state.
- Do not make the visual graph authoritative for execution.
- Do not add workflow mutation from the operator UI.

Loop 18 expected file changes:

- `tests/test_dashboard.py` for snapshot shape changes.
- `src/skill2workflow/dashboard.py` only if exported snapshot fields need to change.
- `web/control.html` and related static assets for read-only operator UI improvements.
- `examples/control-plane-snapshot.json` when the committed fixture must show new operator data.
- `README.md`, `HARNESS.md`, or a focused docs page for the operator inspection flow.

Loop 18 verification commands:

- `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- `python3 -m py_compile src/skill2workflow/*.py`
- `PYTHONPATH=src python3 -m unittest tests.test_dashboard tests.test_control_plane -v`
- `PYTHONPATH=src python3 -m skill2workflow.cli control-snapshot --state-dir /tmp/skill2workflow-control -o /tmp/skill2workflow-control-snapshot.json`
- `git diff --check`

Loop 18 done means:

- Operators can inspect local control-plane state more clearly from an exported artifact or static UI.
- Published workflow artifacts remain immutable and Workflow DSL remains authoritative.
- No hosted service, auth layer, or runtime dependency is added.

## Near-Term Loop Queue

This queue is ordered by what most improves open-source adoption after the first release. Treat it as a planning queue, not a commitment to implement all items without review.

| Loop | Status | Goal | Expected artifact |
| --- | --- | --- | --- |
| Loop 18: Control Plane Operator UX | Next | Connect control-plane state back to visual inspection | static artifact flow for run/audit overlays and workflow artifact diffs |

Loop selection rules:

- Pick the next loop only after the previous loop is merged or explicitly deferred.
- Keep implementation local-first and dependency-light unless a spec-backed capability requires otherwise.
- Prefer examples and guardrails that make the current runtime easier to trust before adding new platform surface area.

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

Status: first MVP shipped in Loop 10. Runtime hardening shipped in Loop 17. Future work should add explicit retry execution, credential boundaries, and product-specific extensions only when backed by tests and docs.

- Connector manifests
- Connector binding validation
- Manual and HTTP connector implementations
- Connector execution audit events
- Connector test fixtures
- Future: connector credentials, automatic retry execution, and product-specific connector packages

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

Status: first MVP shipped in Loop 13. Future work should connect run/audit overlays back into the graph view.

- Workflow registry view
- Run list and run detail view
- Audit log view
- Connector manifest view
- Published workflow version comparison
- Future: live local server mode, graph overlays, and workflow artifact diff views

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
