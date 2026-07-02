# Roadmap

This roadmap turns the approved `skill2workflow` design into an open-source delivery plan. It is intentionally organized around small closed loops: every milestone should produce runnable commands, tests, and a concrete artifact that future contributors can inspect.

The execution source of truth remains the Workflow DSL. LiteGraph and future UI layers are editors and views, not runtime authorities.

## Current Status

`main` now contains a runnable v0.1 bootstrap harness. It demonstrates the five-layer architecture in local form and proves the core product direction: standard Agent skills can be compiled into workflow definitions that are controlled by a durable execution and control-plane layer.

Current capability snapshot:

- Skill ingestion: `SKILL.md` frontmatter, hard gates, and ordered checklist steps become Skill IR
- DSL authority: Skill IR compiles to Workflow DSL, with JSON Schema and structured validation errors
- Visual layer: Workflow DSL renders to LiteGraph JSON, and safe visual edits can write back to DSL
- Runtime: local executor supports run state, human-gate pause/resume, run listing, and run detail
- Control plane: immutable workflow publish, version lifecycle, published-version runs, resume, audit log, and filtered audit queries
- Durability: JSON/JSONL remains the dependency-light default; SQLite is available for run state, workflow registry metadata, and audit events

Important boundaries:

- Published workflow artifacts remain immutable JSON documents in both storage modes.
- The visual graph is an editor/view. Workflow DSL remains the execution truth source.
- Connector execution is still a placeholder boundary. The next loop turns it into a minimal runtime capability.

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

## Active Roadmap

Future work should stay in small closed loops. A loop is complete only when it has a CLI path, tests, documentation, and a merged PR.

### Loop 10: Connector Runtime MVP

Goal: turn connector placeholders into a minimal extension boundary.

Status: next engineering loop.

Scope:

- Connector manifest shape
- Built-in manual connector for human gates
- Connector binding metadata in Workflow DSL
- Minimal HTTP connector for connector-capable nodes
- Connector execution records in run state and audit events

Acceptance criteria:

- A node can declare the connector it needs
- Missing connector bindings fail validation before run
- Connector execution is logged with workflow id, workflow version, run id, and node id
- JSON storage and SQLite storage both support the same connector event model
- Existing non-connector workflows keep working without migration

### Loop 11: Authoring Experience

Goal: improve the visual and CLI authoring flow without weakening Workflow DSL authority.

Status: after Loop 10, or earlier for independent documentation-only pieces.

Scope:

- Better LiteGraph parameter forms for supported node fields
- Example workflow gallery
- Documentation for adding node types and compiler rules
- Expanded write-back for explicitly safe node parameters

Acceptance criteria:

- Contributors can inspect and edit example workflows without reading code first
- UI edits are validated through the same DSL contract as CLI edits
- New write-back fields are allowlisted and covered by tests

### Loop 12: Open Source Release Readiness

Goal: make the project easier for external contributors to evaluate, run, and extend.

Status: follows Loop 10/11, with small docs-only PRs allowed in parallel.

Scope:

- CONTRIBUTING guide
- Issue templates for bug reports, feature requests, and workflow examples
- First release notes and version tag
- Clear compatibility notes for Workflow DSL `0.1.0`

Acceptance criteria:

- A new contributor can run tests and the sample workflow from a fresh checkout
- Early adopters can tell which APIs are stable and which are experimental
- Release notes map product goals to concrete shipped capabilities

## Version Milestones

### v0.1: Bootstrap Harness

Status: current `main` baseline.

- Loops 1-9
- Parser, compiler, validator, executor, LiteGraph view, write-back, control plane, JSON/SQLite durability
- Suitable for local evaluation and early contributor onboarding

### v0.2: Connector Runtime

Target: make external work execution explicit and auditable.

- Connector manifests
- Connector binding validation
- Manual and HTTP connector implementations
- Connector execution audit events
- Connector test fixtures

### v0.3: Authoring Experience

Target: make workflow inspection and editing easier without making the visual graph authoritative.

- Better LiteGraph parameter forms
- Example workflow gallery
- Expanded safe write-back beyond title and description
- Contributor docs for node types and compiler rules

### v0.4: Open Source Release Baseline

Target: make the project ready for broader external evaluation.

- CONTRIBUTING guide
- Issue templates
- First release notes
- Workflow DSL `0.1.0` compatibility notes
- Clear stable vs experimental API boundaries

### v0.5: Local Control Plane UI

Target: give the local runtime an inspectable operator surface.

- Workflow registry view
- Run list and run detail view
- Audit log view
- Published workflow version comparison

### v1.0: Production Baseline

Target: support real team pilots while keeping the project local-first and open-source friendly.

- Stable Workflow DSL
- Stable CLI
- Local runtime and control plane suitable for real team pilots
- Extension points documented for nodes, compiler rules, executors, and connectors

## Contribution Lanes

Contributors can help in these areas:

- Parser coverage for real-world `SKILL.md` formats
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
