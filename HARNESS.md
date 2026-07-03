# Project Harness

This file describes the executable project harness for the current open-source bootstrap.

## Local Verification

Run all tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
git diff --check
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
  - records connector start, completion, and failure events in run state
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
  - imports existing JSON registry and audit files when opening SQLite control-plane storage
  - exposes built-in connector manifests
  - exports a read-only local operator snapshot through `control-snapshot`
  - provides a static control-plane inspector for workflows, runs, audit events, connectors, and version comparisons
- Connector runtime
  - provides active `manual` and `http` connector manifests
  - gives compiled `human_gate` nodes a default manual connector binding
  - gives compiled `tool_call` nodes a default HTTP connector binding
  - executes HTTP requests with the Python standard library
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
- Enterprise connector credential management
- GitHub release automation
