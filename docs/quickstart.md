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

A custom Skill's explicit `workflow_version` declaration selects the initial
published/run version; otherwise it remains `0.1.0`. This does not change the
package or DSL schema version. See [versioned Skill iteration](skill-workflow-versions.md)
before preparing subsequent immutable versions. Quickstart still requires a
new workspace; it never upgrades or replaces an existing one.

Quickstart refuses a non-manual connector before the first human gate on the
compiled initial success path. HTTP actions and HTTP assertions before approval
are rejected before initialization. Manual preparation steps remain supported.
This conservative onboarding check does not change the general executor or
insert a gate into the Skill.

## Provide Business Input

For a Skill with a [typed input contract](skill-input-contracts.md), prepare a
non-secret JSON object, for example:

```json
{"record_id":"reviewed-record-001","title":"Example task"}
```

Pass its explicit local path:

```bash
skill2workflow quickstart \
  --root /srv/skill2workflow/customer-review \
  --skill /srv/customer-workflows/review/SKILL.md \
  --input /srv/customer-workflows/review/input.json \
  --host 127.0.0.1 --port 8080
```

Input must be a finite JSON object. The existing CLI JSON reader accepts at
most 8 MiB of file bytes; the shared canonical UTF-8 input limit is **1 MiB**.
The compiled `input_schema` is checked before workspace initialization,
ingress-token generation, publication or execution. Missing, wrong-typed,
out-of-range and extra values fail without creating the destination. If input
is omitted, `{}` must still satisfy the declared contract. Correct the input
and rerun against the still-unused root; quickstart never overwrites a root.

Explicit input starts the first run through normal SQLite trigger admission,
with source `quickstart` and the workspace-local key `quickstart-initial`.
The existing private run context retains the values for approval/resume and
input mappings. The input file is not copied into `example/`; its path and
values are not added to the compact result or operator command arrays. The
result schema remains unchanged. When input is omitted and `{}` is valid,
legacy bundled/custom first-run context remains unchanged.

Input is durable business data, not a credential store, encryption or redaction
boundary. Use the separate [credential provider](credential-boundary.md) for
authentication. Custom HTTP workflows may need an explicit credential file
when resumed and can cause their declared effects only after approval; the
generated command does not invent that credential setup. Review endpoints,
origins and response retention before approving.

## Preview Before Creating A Workspace

Add `--dry-run` to the same quickstart command to review input readiness without
creating the workspace:

```bash
skill2workflow quickstart \
  --root /srv/skill2workflow/customer-review \
  --skill /srv/customer-workflows/review/SKILL.md \
  --input /srv/customer-workflows/review/input.json --dry-run
```

This compiles the selected Skill, checks its initial human-gate boundary and
the unused absolute root, existing parent, loopback host and port range. It
returns the existing value-free
[`workflow-preflight` report](workflow-preflight.md), not a quickstart result:
`ready: true` exits zero; invalid typed input or missing required mapping sources
returns `ready: false` and exits one. Malformed files, unsafe pre-approval
connectors and invalid workspace locations are refusals with no report.

No workspace, ingress token, publication, run, audit, credential lookup or HTTP
request is created. The report omits input values, request URLs/bodies, local
source/input/destination paths and generated operator commands. Correct the
input and preview again using the same unused root, then remove `--dry-run` to
explicitly initialize. Python callers can pass `dry_run=True`.

Real initialization now performs the same preflight before bootstrap. Required
mapping sources must be present even without an `input_schema`, or when that
schema permits an object lacking a mapped nested field. JSON Pointer escapes,
array indexes and explicit null retain their existing meaning; optional missing
mappings remain allowed. Refusal uses the fixed error `quickstart input does
not satisfy required connector mappings` without echoing values.

The shared readiness bounds are 1,000 nodes, 128 top-level input properties,
2,000 mappings per node, 64 reported issues and a 64 KiB report, in addition to
the Skill/input byte bounds above. This conservative quickstart check is not a
change to general trigger/runtime admission. It checks source presence, not
query scalar conversion, provider availability, credentials, port availability,
filesystem write access or future workflow success. It neither reserves the
root nor authorizes an effect; initialization rechecks the location and approval
remains explicit. Review property names and issue paths before sharing reports.

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

The bundled example's resumed run completes and preserves the gate and
completion audit trail. Custom workflows depend on their reviewed input,
connector configuration and provider outcomes.

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
It also qualifies typed initial input, invalid-input rejection before workspace
creation, rejection of network-before-approval Skills, and approval to a real
owned loopback HTTP receiver. The same input checks are mandatory in isolated
wheel package qualification; no live SaaS endpoint is contacted.
The full drill requires 20 passing checks, including ready and blocked
read-only previews, corrected input under the same unused root, and real
initialization refusal on a missing required mapping without an input schema.
