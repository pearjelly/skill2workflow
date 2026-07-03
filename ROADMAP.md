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
- Connector runtime: built-in manual and HTTP connector manifests, `tool_call` binding validation, HTTP execution, and connector audit events
- Authoring experience: example workflow gallery, richer LiteGraph inspector fields, safe action/retry/HTTP request write-back, and authoring docs
- Workflow example pack: sales follow-up, customer service escalation, risk review, and operations analysis examples with synchronized DSL and LiteGraph fixtures
- Open-source readiness: contributor guide, issue templates, release notes, Workflow DSL compatibility policy, and stability boundaries
- Local control-plane UI: read-only snapshot export and static inspector for workflows, runs, audit events, connectors, and version comparisons
- Release automation: read-only release preflight checks, CI dry-run coverage, and maintainer release-process docs

Important boundaries:

- Published workflow artifacts remain immutable JSON documents in both storage modes.
- The visual graph is an editor/view. Workflow DSL remains the execution truth source.
- Connector runtime is an MVP boundary. Enterprise credential management, connector marketplaces, and product-specific connectors remain later work.
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

## Active Roadmap

Future work should stay in small closed loops. A loop is complete only when it has a CLI path, tests, documentation, and a merged PR.

Post-`v0.1.0` work now has two active priorities after Loop 16 made enterprise examples inspectable:

1. harden connector behavior without overbuilding a marketplace,
2. improve local operator visibility while keeping Workflow DSL authoritative.

### Loop 17: Connector Runtime Hardening

Goal: improve connector reliability and testability without adding external services or a connector marketplace.

Status: next engineering loop.

Initial PR boundary:

- Start with tests and docs before changing connector runtime behavior.
- Prefer a new `tests/test_connectors.py` fixture harness so connector behavior is isolated from executor lifecycle tests.
- Keep any runtime edits limited to bugs or ambiguity exposed by the new tests.
- Do not change Workflow DSL `0.1.0` shape in this loop unless the compatibility document is updated in the same PR.

Scope:

- Add focused connector tests around HTTP timeout, request body, headers, HTTP error handling, and missing request metadata
- Tighten connector retry/timeout expectations where current DSL policy already expresses them
- Add a connector fixture harness that can run without external network dependencies
- Document the credential boundary clearly: examples may use static local request metadata, but real secrets stay out of Workflow DSL

Loop 17 connector behavior matrix:

| Area | Target behavior | Evidence |
| --- | --- | --- |
| Local fixture harness | Connector tests run against a standard-library local HTTP server or deterministic fake, with no public network dependency | `tests/test_connectors.py` |
| HTTP success | Method, headers, JSON body, and `timeout_ms` are passed through request execution; response is normalized into connector output | Connector unit test plus executor event coverage |
| HTTP error | HTTP 4xx/5xx responses return failed connector results with status code, headers, body, and error string | Connector unit test |
| Invalid request | Missing `connector.request`, missing URL, unsupported URL scheme, and malformed metadata fail before external network calls | Connector unit test |
| Timeout boundary | `timeout_ms` conversion is deterministic; timeout failures become explicit connector execution errors | Connector unit test and docs |
| Retry boundary | `retry.max_attempts` remains a DSL policy field until executor retry behavior is implemented with tests | Docs and compatibility notes |
| Credential boundary | Workflow DSL fixtures do not store secrets; credential management remains outside the built-in connector MVP | Docs |

Acceptance criteria:

- Connector behavior is covered by deterministic local tests
- HTTP failures produce explicit connector results or connector execution errors
- Timeout and retry behavior is documented against the current MVP boundary
- Credential handling remains explicitly out of scope for the built-in connector MVP

Loop 17 implementation slices:

1. Connector fixture harness
   - Add local HTTP server or fake connector tests that do not depend on public network access.
2. HTTP behavior coverage
   - Cover success, HTTP error, invalid URL, missing request metadata, headers, body serialization, and timeout conversion.
3. Retry and timeout boundary docs
   - Clarify what `retry.max_attempts`, connector request timeout, and executor failure behavior mean in the current local runtime.
4. Credential boundary docs
   - Document that Workflow DSL fixtures must not contain secrets and that enterprise credential management remains future work.

Loop 17 explicit non-goals:

- Do not add a connector marketplace.
- Do not add external connector SDK dependencies.
- Do not implement enterprise secret storage or IAM.
- Do not add product-specific SaaS connectors in this loop.

Loop 17 expected file changes:

- `tests/test_connectors.py` for connector behavior coverage; only add to `tests/test_executor.py` when the executor event lifecycle needs coverage.
- `src/skill2workflow/connectors.py` only if tests expose missing MVP guardrails.
- `src/skill2workflow/executor.py` only if retry/timeout semantics need a runtime boundary fix.
- `docs/connectors.md` if a focused connector guide is introduced, or `docs/stability.md` updates for timeout, retry, HTTP failure, and credential boundaries.
- `docs/workflow-dsl-compatibility.md` only if the loop clarifies compatibility guarantees for connector request metadata.
- `examples/workflows/http-connector.workflow.json` updates only when fixture behavior must show a documented connector boundary.

Loop 17 verification commands:

- `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- `python3 -m py_compile src/skill2workflow/*.py`
- `PYTHONPATH=src python3 -m unittest tests.test_connectors tests.test_executor -v` once `tests/test_connectors.py` is introduced
- `PYTHONPATH=src python3 -m skill2workflow.cli validate examples/workflows/http-connector.workflow.json --format json`
- `git diff --check`

Loop 17 done means:

- Connector tests cover the current built-in HTTP connector without depending on the public internet.
- Connector docs make retry, timeout, HTTP failure, and credential boundaries clear.
- Existing examples and executor behavior remain compatible with Workflow DSL `0.1.0`.
- No new runtime dependencies are added.

## Near-Term Loop Queue

This queue is ordered by what most improves open-source adoption after the first release. Treat it as a planning queue, not a commitment to implement all items without review.

| Loop | Status | Goal | Expected artifact |
| --- | --- | --- | --- |
| Loop 17: Connector Runtime Hardening | Next | Improve connector reliability without adding external services | retry/timeout policy coverage, connector fixture harness, clearer credential boundary docs |
| Loop 18: Control Plane Operator UX | Planned | Connect control-plane state back to visual inspection | local server or static artifact flow for run/audit overlays and workflow artifact diffs |

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

Status: first MVP shipped in Loop 10. Future work should harden connector ergonomics and product-specific extensions.

- Connector manifests
- Connector binding validation
- Manual and HTTP connector implementations
- Connector execution audit events
- Connector test fixtures
- Future: connector credentials, retries/timeouts per connector, and product-specific connector packages

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
