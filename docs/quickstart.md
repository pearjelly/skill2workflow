# Installed Controlled Quickstart

Loop 52 gives an installed `skill2workflow` wheel a complete first-value path
without requiring the source checkout or an external connector. One command
creates a secure service workspace, compiles Workflow DSL, publishes it into
SQLite, starts a run, and stops at a real human gate.

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
contains the generated ingress value. It also includes four secret-free
`operator_commands` argv arrays (`inspect_run`, `approve_run`,
`service_doctor`, and `start_service`) so an installer or wrapper can continue
the journey without reconstructing paths or shell-quoting user input. The
result contract is defined by
[`schemas/quickstart-result-0.1.0.schema.json`](../schemas/quickstart-result-0.1.0.schema.json).

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

## Use Your Own Skill

To start with a local Skill instead of the bundled example, pass one explicit
path:

```bash
skill2workflow quickstart \
  --root /srv/skill2workflow/customer-review \
  --skill /srv/customer-workflows/review/SKILL.md \
  --host 127.0.0.1 \
  --port 8080
```

Before it creates the workspace, quickstart reads that one local regular file
through the standard bounded, no-symlink Skill boundary and compiles it in
memory. The resulting workflow must be valid and contain a `human_gate`; a
Skill without one is refused and no workspace is created. The accepted bytes
are copied to the new private `example/SKILL.md` and the generated DSL uses
the fixed `SKILL.md` source marker. The supplied source path is not retained
in the generated Workflow DSL or printed in the JSON result.

Quickstart does not add a human gate to an uncontrolled Skill. Author the
approval instruction explicitly, review the generated waiting run, and approve
or reject it through the normal operator command.

## Inspect And Approve

Copy `run_id` and `state_dir` from the command result. Inspect the waiting run:

The equivalent `operator_commands.inspect_run` array is already present in the
JSON result; the expanded command below is shown for interactive shells.

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

An authenticated webhook trigger starts another durable run of the generated
workflow version, which again waits for a human decision. Follow
[`service-bootstrap.md`](service-bootstrap.md) for safe local token use and
[`security-boundary.md`](security-boundary.md) before exposing traffic.

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
installed bundled and custom-Skill quickstarts, verifies their waiting runs,
resumes the bundled run to completion, starts the generated service unchanged,
submits an authenticated webhook, and proves the second run waits at the same
human gate before graceful shutdown.
