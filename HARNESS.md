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
PYTHONPATH=src python3 -m skill2workflow.cli visualize /tmp/skill2workflow-workflow.json -o /tmp/skill2workflow-litegraph.json
PYTHONPATH=src python3 -m skill2workflow.cli run /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-state
```

The sample workflow pauses at a human approval gate. Resume it with:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli resume <run_id> --state-dir /tmp/skill2workflow-state
```

List summaries and inspect full run logs:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli runs --state-dir /tmp/skill2workflow-state
PYTHONPATH=src python3 -m skill2workflow.cli show <run_id> --state-dir /tmp/skill2workflow-state
```

Open the LiteGraph editor:

```bash
python3 -m http.server 4173
```

Then visit `http://localhost:4173/web/`.

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
  - checks node ids and edge ids
  - checks edge endpoint references
  - checks terminal nodes have no outgoing transition
  - checks node transitions have matching edges
  - checks edges are declared by node transitions
- Durable local executor
  - records terminal node results
  - records human gate approvals and rejections
  - supports rejected human gate failure paths
  - exposes run summaries and full run details
- LiteGraph visualization
  - converts Workflow DSL into LiteGraph-compatible graph JSON
  - preserves workflow node ids, node types, descriptions, source metadata, and run status
  - includes a static web editor that loads Workflow DSL or LiteGraph JSON
  - exposes node parameters in an inspector
  - supports simple title and description edits in the LiteGraph view
  - marks invalid graph connections in the UI
- CLI
- Tests
- Example Skill

Not implemented yet:

- DSL write-back from the visual editor
- SQLite persistence
- Enterprise control plane UI
- Connector registry runtime
- GitHub release automation
