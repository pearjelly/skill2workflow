# Roadmap

This roadmap turns the approved `skill2workflow` design into an open-source delivery plan. It is intentionally organized around small closed loops: every milestone should produce runnable commands, tests, and a concrete artifact that future contributors can inspect.

The execution source of truth remains the Workflow DSL. LiteGraph and future UI layers are editors and views, not runtime authorities.

## Current Status

The bootstrap MVP is in place across all five architecture layers:

- Parser: `SKILL.md` to Skill IR
- Compiler and Validator: Skill IR to Workflow DSL
- LiteGraph Viewer: Workflow DSL to visual graph
- Durable Executor: local run, pause, resume, and run log
- Minimal Control Plane: immutable publish, run published version, audit log, connector placeholders

The current persistence layer is dependency-light JSON. The approved product direction still points toward SQLite for local durability once the runtime contract is stable.

## Completed Loops

| Loop | Status | Delivered |
| --- | --- | --- |
| Loop 1: Parser | Complete | Frontmatter, hard gates, checklist normalization, source line mapping |
| Loop 2: Compiler / Validator | Complete | Ordered workflow generation, node and edge validation, terminal-node checks |
| Loop 3: Executor | Complete | Local JSON-backed run state, human gate pause/resume, run list and detail |
| Loop 4: LiteGraph | Complete | Static LiteGraph editor, node inspector, run-state coloring, graph validation |
| Loop 5: Control Plane | Complete | Immutable publish, workflow lifecycle index, published-version runs, audit JSONL, connector placeholders |

## Next Priorities

### 1. Workflow DSL Contract

Goal: make the DSL stable enough for external contributors and future UI write-back.

Status: initial contract in progress. Workflow DSL `0.1.0` now has a JSON Schema, structured validation errors, and golden fixture coverage.

Deliverables:

- JSON Schema for Workflow DSL
- Golden fixture tests for sample workflows
- CLI command or validator mode that reports structured validation errors
- Versioned migration policy for DSL changes

Success criteria:

- Invalid workflow documents fail with machine-readable error locations
- Examples can be used as compatibility fixtures
- Contributors can add node types without guessing required fields

### 2. Visual Editor Write-Back

Goal: make LiteGraph edits round-trip safely into Workflow DSL.

Deliverables:

- Save edited title and description back to Workflow DSL
- Preserve source metadata and execution transitions
- Reject or mark invalid graph mutations before write-back
- Add tests for graph-to-DSL conversion

Success criteria:

- A workflow can be loaded, edited visually, saved, validated, and run
- The saved DSL remains the only runtime input
- Invalid edges cannot silently enter a published workflow

### 3. Runtime Durability Upgrade

Goal: move from JSON files to a stronger local persistence model without changing user-facing semantics.

Deliverables:

- SQLite-backed run state
- Event log table for run events
- Basic migration from current JSON state where practical
- Resume behavior tested across process restarts

Success criteria:

- Run state survives interruption and restart
- Audit and run events are queryable without reading full JSON blobs
- Existing CLI workflows continue to work

### 4. Control Plane Hardening

Goal: make the local control plane useful for repeated project work.

Deliverables:

- `resume-published` or control-plane-aware resume flow
- Audit filters by workflow id, version, run id, and event type
- Run detail command scoped through the control plane
- Explicit lifecycle behavior for deprecated versions

Success criteria:

- Published runs can be started, paused, resumed, listed, and audited through one control-plane surface
- Deprecated versions remain inspectable and immutable
- Audit trails can answer what changed, who/what triggered it, and which run was affected

### 5. Connector Runtime MVP

Goal: turn connector placeholders into a minimal extension boundary.

Deliverables:

- Connector manifest shape
- Built-in manual connector for human gates
- Minimal HTTP connector for tool-call nodes
- Connector binding metadata in Workflow DSL

Success criteria:

- A node can declare the connector it needs
- Missing connector bindings fail validation before run
- Connector execution is logged in node results and audit events

## Later Milestones

### v0.2: Authoring Experience

- Visual DSL write-back
- Better node parameter forms
- Example workflow gallery
- Documentation for adding new node types

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
- LiteGraph node UI and graph-to-DSL write-back
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
