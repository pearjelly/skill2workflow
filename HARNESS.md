# Project Harness

This file describes the executable project harness for the current open-source bootstrap.

## Local Verification

Run all tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

Run the first-run contributor demo:

```bash
python3 scripts/demo_bootstrap.py --work-dir /tmp/skill2workflow-demo
python3 -m json.tool /tmp/skill2workflow-demo/artifacts/control-plane-snapshot.json >/tmp/skill2workflow-demo-snapshot-check.json
```

Open the local control-plane inspector at `http://localhost:4173/web/control.html` after starting `python3 -m http.server 4173`, then load `/tmp/skill2workflow-demo/artifacts/control-plane-snapshot.json`.

Run the editable install and console-script smoke:

```bash
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke
```

Run the committed-fixture secret hygiene check:

```bash
python3 scripts/secret_hygiene.py examples/workflows
```

Manual editable install path:

```bash
python3 -m venv /tmp/skill2workflow-venv
/tmp/skill2workflow-venv/bin/python -m pip install --upgrade pip "setuptools>=68"
/tmp/skill2workflow-venv/bin/python -m pip install --no-build-isolation -e .
/tmp/skill2workflow-venv/bin/skill2workflow validate examples/workflows/approval-flow.workflow.json --format json
```

Run the CLI closed loop:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli parse examples/skills/approval-flow/SKILL.md
PYTHONPATH=src python3 -m skill2workflow.cli compile examples/skills/approval-flow/SKILL.md -o /tmp/skill2workflow-workflow.json
PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json
PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json --format json
PYTHONPATH=src python3 -m skill2workflow.cli visualize /tmp/skill2workflow-workflow.json -o /tmp/skill2workflow-litegraph.json
PYTHONPATH=src python3 -m skill2workflow.cli write-back /tmp/skill2workflow-workflow.json /tmp/skill2workflow-litegraph.json -o /tmp/skill2workflow-edited-workflow.json
PYTHONPATH=src python3 -m skill2workflow.cli validate examples/workflows/http-connector.workflow.json --format json
PYTHONPATH=src python3 -m skill2workflow.cli visualize examples/workflows/http-connector.workflow.json -o examples/workflows/http-connector.litegraph.json
PYTHONPATH=src python3 -m skill2workflow.cli run /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-state
PYTHONPATH=src python3 -m skill2workflow.cli run /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-sqlite-state --storage sqlite
```

The sample workflow pauses at a human approval gate. Resume it with:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli resume <run_id> --state-dir /tmp/skill2workflow-state
PYTHONPATH=src python3 -m skill2workflow.cli resume <run_id> --state-dir /tmp/skill2workflow-sqlite-state --storage sqlite
```

List summaries and inspect full run logs:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli runs --state-dir /tmp/skill2workflow-state
PYTHONPATH=src python3 -m skill2workflow.cli show <run_id> --state-dir /tmp/skill2workflow-state
PYTHONPATH=src python3 -m skill2workflow.cli runs --state-dir /tmp/skill2workflow-sqlite-state --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli show <run_id> --state-dir /tmp/skill2workflow-sqlite-state --storage sqlite
```

Open the LiteGraph editor:

```bash
python3 -m http.server 4173
```

Then visit `http://localhost:4173/web/`.

Run the minimal control plane closed loop:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli publish /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli publish /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli workflows --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli workflows --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli workflow workflow_approval_flow --version 0.1.0 --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli run-published workflow_approval_flow --version 0.1.0 --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli run-published workflow_approval_flow --version 0.1.0 --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli resume-published <run_id> --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli resume-published <run_id> --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli control-runs --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli control-run <run_id> --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --run-id <run_id> --event-type run_completed
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --run-id <run_id> --event-type connector_completed
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --event-type node_retrying
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --event-type node_recovered
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli connectors --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli control-snapshot --state-dir /tmp/skill2workflow-control -o /tmp/skill2workflow-control-snapshot.json
```

Open the local control-plane inspector at `http://localhost:4173/web/control.html` after starting `python3 -m http.server 4173`.

## Current Scope

Implemented:

- Parser
  - frontmatter extraction
  - hard gate extraction
  - checklist normalization
  - structured step details with source line numbers
  - fenced-code exclusion for rule hints
- Compiler
  - compiles ordered step details into node titles, descriptions, and source metadata
  - generates start, ordered step, failure, and end nodes
  - generates success and failure edges
- Validator
  - documents Workflow DSL `0.1.0` with `schemas/workflow.schema.json`
  - exposes structured validation errors through `validate_workflow_structured`
  - supports `validate --format json` for tool and UI integrations
  - checks node ids and edge ids
  - checks edge endpoint references
  - checks terminal nodes have no outgoing transition
  - checks node transitions have matching edges
  - checks edges are declared by node transitions
  - requires `tool_call` nodes to declare `connector.id`
- Durable local executor
  - supports JSON file run storage by default
  - supports opt-in SQLite run storage through `--storage sqlite`
  - stores queryable run event rows in SQLite
  - records terminal node results
  - records human gate approvals and rejections
  - supports rejected human gate failure paths
  - executes connector-bound `tool_call` nodes through the built-in HTTP connector
  - honors `retry.max_attempts` and `policies.default_retry.max_attempts` for connector nodes
  - records connector start, completion, and failure events in run state
  - records `node_retrying`, `node_recovered`, and `node_failed` runtime policy events for local recovery inspection
  - exposes run summaries and full run details
- LiteGraph visualization
  - converts Workflow DSL into LiteGraph-compatible graph JSON
  - embeds source Workflow DSL in generated LiteGraph JSON for safe write-back
  - preserves workflow node ids, node types, descriptions, source metadata, and run status
  - includes connector metadata in node properties for inspection
  - includes a static web editor that loads Workflow DSL or LiteGraph JSON
  - exposes node parameters in an inspector
  - provides an example workflow gallery
  - supports simple title and description edits in the LiteGraph view
  - supports safe action, retry, and HTTP connector request edits in the LiteGraph view
  - writes title and description edits back to Workflow DSL without changing topology
  - writes allowlisted authoring fields back to Workflow DSL without changing connector identity
  - marks invalid graph connections in the UI
- Minimal local control plane
  - publishes immutable workflow artifacts
  - tracks draft, published, and deprecated lifecycle state through JSON or SQLite registry storage
  - runs published workflow versions
  - resumes waiting published runs
  - lists and shows run state through control-plane commands
  - keeps run state bound to workflow id and version
  - records workflow publish, deprecate, and run events in JSONL or SQLite audit storage
  - filters audit events by workflow id, version, run id, and event type
  - records connector execution events in audit storage for published runs
  - promotes runtime policy events such as retry and recovery into audit storage for published runs
  - imports existing JSON registry and audit files when opening SQLite control-plane storage
  - exposes built-in connector manifests
  - exports a read-only local operator snapshot through `control-snapshot`
  - derives operator insights for attention items, recent events, connector events, and version changes
  - provides a static control-plane inspector for operator insights, workflows, runs, audit events, connectors, and version comparisons
- Demo onboarding
  - generates a resettable local demo workspace through `scripts/demo_bootstrap.py`
  - writes Workflow DSL, LiteGraph, and control-plane snapshot artifacts under the demo work directory
  - exercises parse, compile, validate, publish, run, resume, audit, and snapshot paths without network access or secrets
- Packaging and installability
  - verifies package metadata and empty runtime dependency policy through `tests/test_packaging.py`
  - verifies editable install and the installed `skill2workflow` console script through `scripts/package_smoke.py`
  - keeps source-checkout `PYTHONPATH=src` commands and editable-install commands documented side by side
- Connector runtime
  - provides active `manual` and `http` connector manifests
  - gives compiled `human_gate` nodes a default manual connector binding
  - gives compiled `tool_call` nodes a default HTTP connector binding
  - executes HTTP requests with the Python standard library
  - covers HTTP connector success, HTTP error, invalid request metadata, JSON body, headers, and timeout behavior with deterministic local tests
  - documents retry, timeout, and credential boundaries in `docs/connectors.md`
- Credential boundary and secret hygiene
  - documents safe connector example patterns in `docs/credential-boundary.md`
  - checks committed Workflow DSL and LiteGraph example fixtures for obvious secret-like values through `scripts/secret_hygiene.py`
  - keeps real secrets, token injection, redaction, IAM, and SaaS credential flows outside immutable Workflow DSL artifacts
- Runtime policy and recovery
  - documents retry and recovery semantics in `docs/runtime-policy.md`
  - treats `retry.max_attempts` as retries after the first connector attempt
  - keeps global deadlines, delayed backoff, compensation, queues, and credential management outside the current local runtime boundary
- Open-source release readiness
  - documents contributor setup and PR expectations in `CONTRIBUTING.md`
  - provides GitHub issue templates for bugs, feature requests, and workflow examples
  - documents first release scope in `docs/releases/v0.1.0.md`
  - documents Workflow DSL `0.1.0` compatibility in `docs/workflow-dsl-compatibility.md`
  - documents stable and experimental surfaces in `docs/stability.md`
- CLI
- Tests
- Example Skill

Not implemented yet:

- Production-grade enterprise control plane UI
- Enterprise connector credential management, secret injection, and runtime redaction
- GitHub release automation
