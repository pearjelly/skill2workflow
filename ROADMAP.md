# Roadmap

This roadmap turns the approved `skill2workflow` design into an open-source delivery plan. It is intentionally organized around small closed loops: every milestone should produce runnable commands, tests, and a concrete artifact that future contributors can inspect.

The execution source of truth remains the Workflow DSL. LiteGraph and future UI layers are editors and views, not runtime authorities.

## Current Status

The bootstrap MVP is in place across all five architecture layers, with the first two stabilization loops completed:

- Parser: `SKILL.md` to Skill IR
- Compiler and Validator: Skill IR to Workflow DSL
- LiteGraph Viewer: Workflow DSL to visual graph
- Durable Executor: local run, pause, resume, and run log
- Minimal Control Plane: immutable publish, run published version, audit log, connector placeholders
- Workflow DSL Contract: JSON Schema, structured validation errors, and golden fixture coverage
- Visual Write-Back: safe LiteGraph title and description edits back to Workflow DSL

The current persistence layer is dependency-light JSON. The approved product direction still points toward SQLite for local durability once the runtime contract is stable.

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

## Next Priorities

### 1. Runtime Durability Upgrade

Goal: move from JSON files to a stronger local persistence model without changing user-facing semantics.

Status: next engineering loop.

Deliverables:

- Storage boundary that keeps executor semantics independent from file format
- SQLite-backed run state
- Event log table for run events
- Basic migration or import path from current JSON state where practical
- Resume behavior tested across process restarts

Success criteria:

- Run state survives interruption and restart
- Audit and run events are queryable without reading full JSON blobs
- Existing CLI workflows continue to work
- JSON persistence can remain as a simple fallback or compatibility fixture

### 2. Control Plane Hardening

Goal: make the local control plane useful for repeated project work.

Status: follows the SQLite durability loop.

Deliverables:

- `resume-published` or control-plane-aware resume flow
- Audit filters by workflow id, version, run id, and event type
- Run detail command scoped through the control plane
- Explicit lifecycle behavior for deprecated versions

Success criteria:

- Published runs can be started, paused, resumed, listed, and audited through one control-plane surface
- Deprecated versions remain inspectable and immutable
- Audit trails can answer what changed, who/what triggered it, and which run was affected

### 3. Connector Runtime MVP

Goal: turn connector placeholders into a minimal extension boundary.

Status: starts after the run and audit state model is durable enough to record external calls.

Deliverables:

- Connector manifest shape
- Built-in manual connector for human gates
- Minimal HTTP connector for tool-call nodes
- Connector binding metadata in Workflow DSL

Success criteria:

- A node can declare the connector it needs
- Missing connector bindings fail validation before run
- Connector execution is logged in node results and audit events

### 4. Authoring Experience

Goal: improve the visual and CLI authoring flow without weakening Workflow DSL authority.

Deliverables:

- Better LiteGraph parameter forms for supported node fields
- Example workflow gallery
- Documentation for adding node types and compiler rules
- Expanded write-back for explicitly safe node parameters

Success criteria:

- Contributors can inspect and edit example workflows without reading code first
- UI edits are validated through the same DSL contract as CLI edits
- New write-back fields are allowlisted and covered by tests

### 5. Open Source Release Readiness

Goal: make the project easier for external contributors to evaluate, run, and extend.

Deliverables:

- CONTRIBUTING guide
- Issue templates for bug reports, feature requests, and workflow examples
- First release notes and version tag
- Clear compatibility notes for Workflow DSL `0.1.0`

Success criteria:

- A new contributor can run tests and the sample workflow from a fresh checkout
- Early adopters can tell which APIs are stable and which are experimental
- Release notes map product goals to concrete shipped capabilities

## Later Milestones

### v0.2: Authoring Experience

- Better node parameter forms
- Example workflow gallery
- Documentation for adding new node types
- Expanded safe write-back beyond title and description

### v0.3: Durable Runtime

- SQLite persistence
- Structured run and audit queries
- Retry and timeout semantics
- Checkpoint and resume hardening

### v0.4: Connector SDK

- Connector manifests
- Tool-call execution boundary
- Example connectors
- Connector validation and test harness

### v0.5: Local Control Plane UI

- Workflow registry view
- Run list and run detail view
- Audit log view
- Published workflow version comparison

### v1.0: Production Baseline

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
- Executor backends and durability work
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
