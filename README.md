# skill2workflow

From Agent Skills to Controlled Enterprise Workflows.

`skill2workflow` is an open-source Agent Workflow Runtime for enterprise AI adoption. It converts standard `SKILL.md` capability descriptions into controlled workflows that can be validated, visualized, executed, resumed, and audited.

The core idea is simple:

- Skills answer: "Can the agent do this?"
- Workflows answer: "Will it follow the required process every time?"
- A durable executor answers: "Can the process recover, pause, resume, and leave an audit trail?"

This repository is intentionally starting with a small executable harness instead of a large platform shell. The first closed loop is:

```text
SKILL.md -> Skill IR -> Workflow DSL -> Local Executor -> Run Log
```

LiteGraph visualization, enterprise control plane features, and connector expansion are part of the staged roadmap in the approved spec.

## Visual Overview

### Controlled Workflow Authoring

<p align="center">
  <img src="docs/assets/skill2workflow-editor.jpg" alt="skill2workflow LiteGraph editor showing a sales follow-up workflow with node validation and an HTTP connector node selected" width="100%">
</p>

The visual editor loads Workflow DSL, renders it as a LiteGraph-compatible graph, and exposes allowlisted edits for node text, retry policy, actions, and HTTP connector request metadata. The graph is a view and editor; Workflow DSL remains the execution truth source.
When a run-state file is provided, the editor also shows read-only node overlay evidence such as current node, status, connector outcome, attempts, retry/recovery markers, and compact trigger metadata.

### Local Control Plane And Audit Trail

![Control-plane screenshot showing workflow registry metrics, audit events, connector count, and snapshot detail](docs/assets/skill2workflow-control-plane.jpg)

The local control-plane inspector reads exported snapshots so operators can inspect published workflow versions, runs, audit events, connectors, and version comparisons without adding a server dependency.
Snapshot runs include compact per-node overlays, and the inspector's Nodes view lets operators scan run evidence without opening raw JSON.

### System Design

![System design diagram showing SKILL.md compiled into Skill IR, Workflow DSL, LiteGraph, executor, connectors, and control-plane audit](docs/assets/skill2workflow-system-design.svg)

## Why This Exists

Agent skills have already proven useful for adapting AI systems to new tasks. They are fast to write, easy to share, and effective for many lightweight tasks.

Enterprise workflows need more control:

- Mandatory execution order
- Human approval gates
- Durable state
- Failure handling
- Recoverability
- Versioning
- Auditability
- Integration hooks

`skill2workflow` bridges that gap by compiling skills into an execution-controlled workflow runtime.

## Current Harness

The current implementation is a dependency-light Python harness because the local bootstrap environment does not include Node.js or npm. It implements the first executable slice of the product:

- Parse standard `SKILL.md` into Skill IR
- Preserve checklist source mapping with step title, detail, section, and line number
- Normalize numbered lists, bullet lists, and markdown task checkboxes
- Ignore fenced code blocks when extracting rule hints
- Compile Skill IR into Workflow DSL
- Carry parser source mapping into workflow node metadata
- Validate Workflow DSL
- Document the Workflow DSL with a versioned JSON Schema
- Validate edge ids, edge endpoints, terminal-node edges, and node transition consistency
- Emit structured machine-readable validation errors
- Execute workflows locally
- Pause at `human_gate`
- Resume waiting runs
- Persist run state as JSON or opt-in SQLite
- List run summaries and inspect full run logs
- Store queryable run event rows when SQLite storage is enabled
- Bind `human_gate` nodes to the built-in manual connector
- Bind and validate `tool_call` connector metadata
- Execute minimal HTTP connector calls from connector-bound `tool_call` nodes
- Resolve local credential handles for HTTP connector request headers without storing secret values in Workflow DSL or audit output
- Cover HTTP connector success, failure, invalid request metadata, JSON body, headers, and timeout behavior with local tests
- Honor connector-node `retry.max_attempts` and record retry/recovery events
- Convert Workflow DSL into LiteGraph-compatible graph JSON
- Derive read-only node-level run overlays from run state and audit evidence
- Open a static LiteGraph visual editor for graph inspection and parameter edits
- Write safe LiteGraph title and description edits back to Workflow DSL
- Write safe action, retry, and HTTP connector request edits back to Workflow DSL
- Load example workflows from the editor gallery
- Publish immutable workflow versions into a local control plane
- Run published workflow versions and write audit events
- Trigger published workflow versions through a compact local API envelope
- Persist trigger input values in durable run context without logging full input values to audit by default
- Trigger published workflow versions from local HTTP webhook POST requests
- Trigger published workflow versions from deterministic one-shot local schedules
- Store workflow registry and audit metadata in JSON/JSONL or opt-in SQLite
- List built-in connector manifests
- Audit connector execution events through the control plane
- Audit runtime policy events such as `node_retrying`, `node_recovered`, and `node_failed` through the control plane
- Export a read-only control-plane snapshot with derived operator insights
- Inspect operator attention items, recent events, connector events, per-node run overlays, workflows, runs, audit events, and version deltas in a static local control-plane UI
- Inspect enterprise example workflows for sales, customer service, risk review, and operations analysis
- Generate a deterministic first-run demo workspace for contributor onboarding
- Run a deterministic local pilot playbook with webhook trigger, credential handle, audit, snapshot, and node overlay artifacts
- Run a deterministic local scheduled-trigger smoke with schedule, run, audit, and snapshot artifacts
- Verify editable install, package metadata, and the installed `skill2workflow` console script
- Check committed Workflow DSL and LiteGraph examples for obvious secret-like connector values
- Run read-only release preflight checks for package version, release notes, tag availability, tests, and Python compilation
- Provide contributor, release, compatibility, and stability documentation for open-source evaluation

## Quickstart

Run the shortest local demo from a fresh checkout:

```bash
python3 scripts/demo_bootstrap.py --work-dir /tmp/skill2workflow-demo
```

The demo compiles `examples/skills/approval-flow/SKILL.md`, publishes and runs the workflow, resumes the approval gate, and writes artifacts under `/tmp/skill2workflow-demo/artifacts/`:

- `workflow.json`
- `workflow.litegraph.json`
- `control-plane-snapshot.json`

Open the local control-plane inspector:

```bash
python3 -m http.server 4173
```

Then open:

```text
http://localhost:4173/web/control.html
```

Load `/tmp/skill2workflow-demo/artifacts/control-plane-snapshot.json` to inspect the generated operator snapshot, including the Nodes view for per-node run evidence. Rerunning the demo resets the work directory by default; pass `--no-reset` to keep existing files.

Run the local pilot playbook smoke:

```bash
python3 scripts/pilot_playbook_smoke.py --work-dir /tmp/skill2workflow-pilot
```

The pilot playbook publishes and triggers a customer-support escalation workflow through the local webhook boundary, resumes a manual gate, calls a local HTTP receiver with a credential handle, and writes inspection artifacts under `/tmp/skill2workflow-pilot/artifacts/`.
See `docs/pilot-playbook.md` for the supported pilot boundary and checklist.

Run the local scheduled-trigger smoke:

```bash
python3 scripts/schedule_smoke.py --work-dir /tmp/skill2workflow-schedule-loop29
```

The schedule smoke publishes the approval example, writes a local one-shot schedule, runs due schedules with a fixed timestamp, resumes the manual gate, and writes inspection artifacts under `/tmp/skill2workflow-schedule-loop29/artifacts/`.

Run the package install smoke:

```bash
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke
```

Run the committed-fixture secret hygiene check:

```bash
python3 scripts/secret_hygiene.py examples/workflows
```

Or install the checkout in editable mode and use the console script directly:

```bash
python3 -m venv /tmp/skill2workflow-venv
/tmp/skill2workflow-venv/bin/python -m pip install --upgrade pip "setuptools>=68"
/tmp/skill2workflow-venv/bin/python -m pip install --no-build-isolation -e .
/tmp/skill2workflow-venv/bin/skill2workflow --help
/tmp/skill2workflow-venv/bin/skill2workflow validate examples/workflows/approval-flow.workflow.json --format json
```

The `PYTHONPATH=src python3 -m skill2workflow.cli ...` commands below remain the no-install source-checkout path.

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Parse a Skill:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli parse examples/skills/approval-flow/SKILL.md
```

Compile a workflow:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli compile examples/skills/approval-flow/SKILL.md -o /tmp/skill2workflow-workflow.json
```

Validate it:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json
```

Emit structured validation errors:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json --format json
```

Generate LiteGraph JSON:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli visualize /tmp/skill2workflow-workflow.json -o /tmp/skill2workflow-litegraph.json
```

Generate LiteGraph JSON with read-only run overlay evidence:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli visualize /tmp/skill2workflow-workflow.json --run-state /tmp/skill2workflow-state/runs/<run_id>.json -o /tmp/skill2workflow-overlay.litegraph.json
```

Apply safe LiteGraph edits back to Workflow DSL:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli write-back /tmp/skill2workflow-workflow.json /tmp/skill2workflow-litegraph.json -o /tmp/skill2workflow-edited-workflow.json
```

Open the LiteGraph editor:

```bash
python3 -m http.server 4173
```

Then open:

```text
http://localhost:4173/web/
```

The editor can load either Workflow DSL JSON or the LiteGraph JSON generated by `visualize`. `Save DSL` writes edited node titles and descriptions back to Workflow DSL while preserving node ids, edges, transitions, source metadata, guards, checkpoints, and policies.
It also supports allowlisted authoring fields for actions, retry attempts, and HTTP connector request metadata.

Run it:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli run /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-state
```

Run it with SQLite-backed run storage:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli run /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-state --storage sqlite
```

Resume a waiting run:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli resume <run_id> --state-dir /tmp/skill2workflow-state
```

For SQLite-backed runs, pass `--storage sqlite` to `resume`, `runs`, and `show` as well.

List local run summaries:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli runs --state-dir /tmp/skill2workflow-state
```

Inspect a full run log:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli show <run_id> --state-dir /tmp/skill2workflow-state
```

Publish a workflow version:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli publish /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-control
```

Publish with SQLite-backed control-plane metadata:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli publish /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-control --storage sqlite
```

List and inspect published workflow versions:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli workflows --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli workflow workflow_approval_flow --version 0.1.0 --state-dir /tmp/skill2workflow-control
```

Run a published version and inspect audit events:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli run-published workflow_approval_flow --version 0.1.0 --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli resume-published <run_id> --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli control-runs --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli control-run <run_id> --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control
```

Trigger a published version through the local trigger boundary:

```bash
printf '{"customer_id":"customer_123"}' >/tmp/skill2workflow-trigger-input.json
PYTHONPATH=src python3 -m skill2workflow.cli trigger workflow_approval_flow --version 0.1.0 --state-dir /tmp/skill2workflow-control --source local-cli --idempotency-key example-001 --input /tmp/skill2workflow-trigger-input.json
```

Triggered runs store input values under `context.input` and compact trigger metadata under `context.trigger`. Audit events and trigger responses expose `input_keys`, not full input values.

Trigger a published version through a deterministic local schedule:

```bash
cat >/tmp/skill2workflow-schedule.json <<'JSON'
{
  "schema_version": "skill2workflow-schedule-0.1.0",
  "schedule": {
    "id": "schedule_approval_flow_daily",
    "workflow_id": "workflow_approval_flow",
    "version": "0.1.0",
    "run_at": "2026-07-06T00:00:00Z"
  },
  "trigger": {
    "input": {
      "customer_id": "customer_123"
    }
  }
}
JSON
PYTHONPATH=src python3 -m skill2workflow.cli schedule-add /tmp/skill2workflow-schedule.json --state-dir /tmp/skill2workflow-control
PYTHONPATH=src python3 -m skill2workflow.cli schedule-run-due --state-dir /tmp/skill2workflow-control --now 2026-07-06T00:00:00Z
```

Scheduled runs use the same trigger boundary as CLI and webhook triggers. The local schedule helper is not a hosted scheduler, cron manager, queue, auth layer, or production daemon.

Start a local webhook adapter for pilot integration testing:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli webhook-server --state-dir /tmp/skill2workflow-control --host 127.0.0.1 --port 8080
```

Then send a local webhook request:

```bash
curl -sS -X POST http://127.0.0.1:8080/webhooks/workflow_approval_flow/0.1.0 -H 'Content-Type: application/json' -d '{"source":"local-webhook","idempotency_key":"example-001","input":{"customer_id":"customer_123"}}'
```

Webhook requests use the same published trigger boundary as the CLI command. The local adapter is not a hosted ingress, auth layer, queue, or production daemon.

Run with a local credential file when a connector references credential handles:

```bash
printf '{"credentials":{"demo_api_token":"local-secret-value"}}' >/tmp/skill2workflow-credentials.json
PYTHONPATH=src python3 -m skill2workflow.cli run /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-state --credential-file /tmp/skill2workflow-credentials.json
```

Credential files are local-only and must not be committed. Workflow DSL stores handles, not resolved secret values.

Use SQLite run storage for published runs:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli run-published workflow_approval_flow --version 0.1.0 --state-dir /tmp/skill2workflow-control --storage sqlite
```

For SQLite-backed control-plane metadata, pass `--storage sqlite` to `workflows`, `workflow`, `deprecate`, and `audit` as well.

Filter audit events:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --workflow-id workflow_approval_flow --version 0.1.0
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --run-id <run_id> --event-type run_completed
```

List connector manifests:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli connectors --state-dir /tmp/skill2workflow-control
```

Export a control-plane snapshot:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli control-snapshot --state-dir /tmp/skill2workflow-control -o /tmp/skill2workflow-control-snapshot.json
```

Open the local control-plane inspector:

```bash
python3 -m http.server 4173
```

Then open:

```text
http://localhost:4173/web/control.html
```

The inspector can load `examples/control-plane-snapshot.json` or a local snapshot exported by `control-snapshot`.
It opens on the Operator view, which summarizes attention items, recent audit events, connector event counts, and version changes without mutating workflow artifacts.
Use the Nodes tab to inspect the read-only `node_overlays` exported for each run. Overlay data is view state only; it is not written back to Workflow DSL.

Inspect the enterprise example pack:

```bash
PYTHONPATH=src python3 -m unittest tests.test_examples -v
PYTHONPATH=src python3 -m skill2workflow.cli validate examples/workflows/sales-follow-up.workflow.json --format json
```

The examples are documented in `docs/examples.md` and can be loaded from the web editor gallery.

Run release preflight in CI-style dry-run mode:

```bash
PYTHONPATH=src python3 scripts/release_preflight.py --version 0.1.0 --notes docs/releases/v0.1.0.md --dry-run --skip-git
```

For real release preparation, follow `docs/release-process.md` and do not skip git checks.

## Architecture

The approved architecture has five layers:

1. Skill Ingestion / Parser
2. DSL Compiler / Validator
3. LiteGraph Editor
4. Durable Executor
5. Enterprise Control Plane

The current harness implements all five layers in minimal local form. Run state, lifecycle registry state, and audit events can use JSON/JSONL or SQLite. Published workflow artifacts remain immutable JSON documents in both modes.

## Repository Layout

```text
src/skill2workflow/
  parser.py       # SKILL.md -> Skill IR
  compiler.py     # Skill IR -> Workflow DSL + validation
  connectors.py    # Built-in connector manifests and local connector execution
  control_plane.py # Local workflow registry, audit log, and connector audit events
  dashboard.py     # Read-only control-plane snapshot aggregation
  executor.py     # Durable local execution
  storage.py      # JSON and SQLite local persistence backends
  visualizer.py   # Workflow DSL -> LiteGraph JSON and read-only run overlays
  secret_hygiene.py # Fixture secret hygiene scanner
  credentials.py  # Local credential provider boundary
  triggers.py     # Local trigger envelope helpers
  schedules.py    # Deterministic local schedule helpers
  webhooks.py     # Local webhook adapter for published triggers
  schedule_smoke.py # Local scheduled-trigger smoke helper
  release.py      # Read-only release preflight checks
  cli.py          # Command line interface
scripts/          # Maintainer command helpers
examples/skills/  # Example SKILL.md inputs
examples/workflows/ # Example Workflow DSL and LiteGraph graph JSON
examples/control-plane-snapshot.json # Example control-plane UI snapshot
schemas/           # Versioned Workflow DSL JSON Schema
tests/            # Unit tests
docs/             # Product spec and implementation plans
docs/assets/      # README screenshots and system design diagrams
docs/connectors.md # Connector runtime behavior and boundary guide
docs/credential-boundary.md # Safe credential and fixture hygiene boundary
docs/examples.md  # Enterprise workflow example pack guide
docs/pilot-playbook.md # Supported local pilot path and checklist
docs/triggers.md  # Local trigger API boundary guide
docs/releases/    # Release notes
web/              # Static LiteGraph editor and control-plane inspector
.github/          # CI and issue templates
CONTRIBUTING.md   # Contributor guide
ROADMAP.md        # Open-source delivery roadmap
```

## Roadmap

The bootstrap MVP now covers all five approved architecture layers in minimal local form:

- Parser
- Compiler and Validator
- LiteGraph Editor
- Durable Executor
- Minimal Control Plane
- Workflow DSL Contract
- Visual Write-Back
- SQLite durability for run state, workflow registry, and audit events
- Control Plane Hardening
- Connector Runtime MVP
- Authoring Experience
- Open Source Release Readiness
- Local Control Plane UI
- Release Automation
- Workflow Example Pack
- Connector Runtime Hardening
- Control Plane Operator UX
- Demo And Contributor Onboarding
- Packaging And Installability
- Runtime Policy And Recovery
- Credential Boundary And Secret Hygiene
- Trigger And Local Run API
- Workflow Inputs And Run Context
- Credential Provider Interface
- Local Webhook Adapter
- Run Overlay In Visual Editor
- Pilot Playbook And Example
- Scheduled Trigger Boundary

Next priority is trigger input mapping.

See:

- `CONTRIBUTING.md`
- `ROADMAP.md`
- `docs/authoring.md`
- `docs/connectors.md`
- `docs/credential-boundary.md`
- `docs/examples.md`
- `docs/pilot-playbook.md`
- `docs/release-process.md`
- `docs/releases/v0.1.0.md`
- `docs/runtime-policy.md`
- `docs/stability.md`
- `docs/triggers.md`
- `docs/workflow-dsl-contract.md`
- `docs/workflow-dsl-compatibility.md`
- `docs/superpowers/specs/2026-07-01-skill2workflow-design.md`

## License

Apache-2.0
