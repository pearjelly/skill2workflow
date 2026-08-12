# Installed Controlled Quickstart

Loop 52 gives an installed `skill2workflow` wheel a complete first-value path
without requiring the source checkout or an external connector. One command
creates a secure service workspace, writes a standard example `SKILL.md`,
compiles Workflow DSL, publishes it into SQLite, starts a run, and stops at a
real human gate.

## Create The Workspace

Choose a new absolute path. Its parent must exist. The target must not already exist:

```bash
skill2workflow quickstart \
  --root /srv/skill2workflow/quickstart \
  --host 127.0.0.1 \
  --port 8080
```

The compact JSON result has `status: "ready_for_review"`, `run_status:
"waiting"`, workflow and run identifiers, and paths to the generated service
configuration, example Skill, Workflow DSL, state, and secret files. It never
contains the generated ingress value.

The workspace uses the owner-only layout documented in
[`service-bootstrap.md`](service-bootstrap.md), plus:

```text
example/                 0700
  SKILL.md               0600
  workflow.json          0600
```

Unlike the source-checkout contributor demo, quickstart has no reset or force
mode. It never deletes or replaces an existing path. If compilation,
validation, publication, or the initial run fails, it removes only the new
workspace it created.

## Inspect And Approve

Copy `run_id` and `state_dir` from the command result. Inspect the waiting run:

```bash
skill2workflow control-run <run_id> \
  --state-dir /srv/skill2workflow/quickstart/state \
  --storage sqlite
```

The run is `waiting` at the example human gate. Approve it once:

```bash
skill2workflow resume-published <run_id> \
  --state-dir /srv/skill2workflow/quickstart/state \
  --storage sqlite
```

The resumed run completes and preserves the gate and completion audit trail.

## Start The Service

The same workspace is ready for the long-running service without configuration
edits:

```bash
skill2workflow service-doctor \
  --config /srv/skill2workflow/quickstart/config/service.json

skill2workflow service \
  --config /srv/skill2workflow/quickstart/config/service.json
```

An authenticated webhook trigger starts another durable run of
`workflow_controlled_quickstart@0.1.0`, which again waits for a human decision.
Follow [`service-bootstrap.md`](service-bootstrap.md) for safe local token use
and [`security-boundary.md`](security-boundary.md) before exposing traffic.

## Boundary

The bundled workflow demonstrates compilation, immutable publication, SQLite
state, audit, and approval control. It does not call an external connector,
create a real business side effect, configure TLS, install a supervisor, or
claim that the example is a production business process. Replace the example
Skill only after understanding the authoring, connector, credential, and
runtime-policy contracts.

## Evidence

Run the installed-wheel real-process journey:

```bash
python3 scripts/quickstart_smoke.py \
  --work-dir /tmp/skill2workflow-quickstart-loop52
```

The drill builds and installs the wheel, disables source imports, invokes the
installed quickstart, verifies the first waiting run, resumes it to completion,
starts the generated service unchanged, submits an authenticated webhook, and
proves the second run waits at the same human gate before graceful shutdown.
