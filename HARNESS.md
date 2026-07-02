# Project Harness

This file describes the executable project harness for the current open-source bootstrap.

## Local Verification

Run all tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Run the CLI closed loop:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli parse examples/skills/approval-flow/SKILL.md
PYTHONPATH=src python3 -m skill2workflow.cli compile examples/skills/approval-flow/SKILL.md -o /tmp/skill2workflow-workflow.json
PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json
PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json --format json
PYTHONPATH=src python3 -m skill2workflow.cli visualize /tmp/skill2workflow-workflow.json -o /tmp/skill2workflow-litegraph.json
PYTHONPATH=src python3 -m skill2workflow.cli write-back /tmp/skill2workflow-workflow.json /tmp/skill2workflow-litegraph.json -o /tmp/skill2workflow-edited-workflow.json
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
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite
PYTHONPATH=src python3 -m skill2workflow.cli connectors --state-dir /tmp/skill2workflow-control
```

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
- Durable local executor
  - supports JSON file run storage by default
  - supports opt-in SQLite run storage through `--storage sqlite`
  - stores queryable run event rows in SQLite
  - records terminal node results
  - records human gate approvals and rejections
  - supports rejected human gate failure paths
  - exposes run summaries and full run details
- LiteGraph visualization
  - converts Workflow DSL into LiteGraph-compatible graph JSON
  - embeds source Workflow DSL in generated LiteGraph JSON for safe write-back
  - preserves workflow node ids, node types, descriptions, source metadata, and run status
  - includes a static web editor that loads Workflow DSL or LiteGraph JSON
  - exposes node parameters in an inspector
  - supports simple title and description edits in the LiteGraph view
  - writes title and description edits back to Workflow DSL without changing topology
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
  - imports existing JSON registry and audit files when opening SQLite control-plane storage
  - exposes connector registry placeholders
- CLI
- Tests
- Example Skill

Not implemented yet:

- Enterprise control plane UI
- Connector runtime
- GitHub release automation
