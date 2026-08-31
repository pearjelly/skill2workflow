# Authoring Workflows

This guide describes the current authoring surface for `skill2workflow`.

Workflow DSL remains the execution truth source. The LiteGraph editor is an inspection and editing surface that must round-trip back through Workflow DSL validation before a workflow is published or run.

The installed editor bundles its pinned LiteGraph JavaScript and stylesheet.
Opening it through `skill2workflow ui` therefore needs no CDN access, internet
egress, or browser-time dependency install. The version, MIT license, and
asset SHA-256 records live in `web/vendor/litegraph-0.7.18/` for review.

## Compile A Local SKILL.md

When the editor is served by the installed `skill2workflow ui` command, choose
one local `SKILL.md` and select **Compile SKILL**. The loopback UI process parses
and compiles that one in-memory document into a draft Workflow DSL document,
then loads the result into the normal editor for review and allowlisted edits.

The request is bounded to 2 MiB and decoded from the selected file's bytes as
strict UTF-8. Invalid UTF-8 stops the import rather than replacing bytes with
look-alike characters. It has no filesystem output, does not access the runtime
state directory or a service token, and never executes, publishes, or persists
the result. The generated source reference is the fixed `SKILL.md`, not the
browser's local file path. The editor renders the returned Workflow DSL only
after its normal local validation. Use the CLI `compile` command when you need
a durable JSON artifact in a specified filesystem location.

After a successful compile, the editor shows a source-free **SKILL Compile
Review**: inferred executable, human-gate, verification, and hard-gate
declaration counts, plus fixed notices when a checklist, approval node, or
verification node was not inferred. This is a conservative review aid, not a
proof of business safety or an execution policy. Review and edit the Workflow
DSL before publication; the summary neither changes the draft nor authorizes a
side effect.

The same review is available to local automation. To write the ordinary DSL
artifact while emitting only the source-free review on standard output:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli compile path/to/SKILL.md \
  -o /tmp/workflow.json --review > /tmp/skill-compile-review.json
```

Without `-o`, `compile --review` intentionally prints an explicit
`{"workflow": ..., "review": ...}` wrapper. Plain `compile` without
`--review` keeps its existing DSL-only output for compatibility.

## Export A Reviewable Local Authoring Set

When an author needs durable review artifacts instead of an in-memory editor
draft, create a fresh destination directory in one command:

```bash
skill2workflow authoring-export path/to/SKILL.md \
  --output-dir /tmp/skill2workflow-authoring-set
```

The command refuses to replace an existing destination and creates the new
directory with owner-only permissions. Its files are also owner-only:

- `workflow.json` — the authoritative compiled Workflow DSL;
- `workflow.litegraph.json` — the derived LiteGraph inspection view;
- `compile-review.json` — the fixed source-free structural compile review;
- `manifest.json` — workflow identity plus byte counts and SHA-256 values.

The original `SKILL.md` is read for compilation but is never copied into this
set. The command does not publish or execute a workflow, resolve credentials,
or access runtime/service state. Review `workflow.json` and validate it before
using a separate publish or run command.

Node source mapping retains the compiled Skill's line and section information,
but the exported file reference is always the fixed `SKILL.md`. The local path
passed to the command is never written into an authoring set or a Bundle
created from it.

Before creating the directory, the compiler-generated Workflow DSL passes the
same conservative secret-hygiene scan used by portable Bundles. Obvious
secret-like values cause a fixed refusal and leave no output directory. This is
not a replacement for secret management or human review; do not put tokens,
customer data, or credentials in a Skill.

Before accepting a set from another local workspace or using it in CI, verify
the exact artifact names, owner-only permission boundary, file digests,
Workflow DSL validity, source-free review consistency, and that the graph is
still derived from that Workflow DSL:

```bash
skill2workflow authoring-verify /tmp/skill2workflow-authoring-set
```

The result is a value-free report with fixed error codes and a nonzero exit
status when verification fails. Hashes detect accidental or untrusted local
modification; they are not an authenticity signature. Protect the directory
and use an authenticated sharing channel when provenance matters.
Verification also rejects a Workflow DSL containing an obvious secret-like
value, including a historical set whose digests were rewritten after a manual
edit.

## Repair A Local Authoring Set

If verification reports a damaged local set and the original `SKILL.md` is
available, rebuild it with an explicit sibling backup:

```bash
skill2workflow authoring-repair path/to/SKILL.md \
  /tmp/skill2workflow-authoring-set \
  --backup-dir /tmp/skill2workflow-authoring-set-before-repair
```

Before replacing anything, run the identical rebuild and verification path in
preflight mode:

```bash
skill2workflow authoring-repair path/to/SKILL.md \
  /tmp/skill2workflow-authoring-set \
  --backup-dir /tmp/skill2workflow-authoring-set-before-repair \
  --dry-run
```

`--dry-run` creates and removes only a private temporary candidate. It leaves
the selected authoring directory and requested backup path unchanged, while
checking the source can produce a fully verified replacement. Its `ready`
result includes only fixed status, prior validity, workflow identity, and
digest; use it to review repair readiness before running the mutating command.

The destination must already be a regular directory and the backup must be a
new directory in the same parent. The command first compiles and completely
verifies a fresh private replacement. Only then does it rename the old set to
the requested backup and place the verified replacement at the original path.
If compilation or replacement preparation fails, the existing set is left
unchanged; if the final replacement rename fails, it attempts to restore the
old set. The compact result reports only whether the prior set was valid, its
fixed verification error codes, and the new workflow identity/digest—never
Skill contents or verification values.

Repair is not an in-place edit, a merge, a provenance signature, or a way to
recover a lost source Skill. Review the preserved backup before deleting it;
publish and execute remain separate explicit actions.

To turn an unchanged, verified authoring set into the existing portable
Workflow Bundle without manually reopening `workflow.json`, use:

```bash
skill2workflow authoring-bundle /tmp/skill2workflow-authoring-set \
  --output /tmp/skill2workflow-authoring-set.s2w
```

This command reads the same descriptor-bound bytes that pass full
`authoring-verify`, then invokes the normal deterministic, secret-checked
Bundle writer. A modified or invalid authoring set cannot produce a Bundle;
the output file is not created. The result is still only a distribution
artifact. Use `bundle-verify` to inspect it and `bundle-publish` separately
when a deliberate immutable publication is appropriate.

## Publish A Verified Local Authoring Set

When the authoring set stays on the same trusted machine as the local control
plane, publish it directly without creating a transport Bundle:

```bash
skill2workflow authoring-publish /tmp/skill2workflow-authoring-set \
  --state-dir /srv/skill2workflow/control \
  --storage sqlite
```

`authoring-publish` reads only the same descriptor-bound Workflow DSL bytes
that pass full authoring-artifact verification, then uses the normal immutable
local publication path. A damaged or altered set is refused before the control
plane is initialized. Repeating an identical publication follows the existing
idempotent publication contract; a different document for the same workflow
version is rejected.

It only publishes. It does not trigger a run, resolve credentials, call a
connector, promote an alias, or approve a human gate. Use the separate
`trigger` or `run-published` command after reviewing the publication result.
Use `authoring-bundle` instead when the set must cross a workstation or review
handoff boundary.

## Preflight And Publish To A Self-Hosted Service

When the verified authoring set is local but the self-hosted control plane runs
behind its authenticated service boundary, preserve the same verified-read
contract for both remote steps:

```bash
skill2workflow authoring-service-release-preflight \
  /tmp/skill2workflow-authoring-set \
  --service-url https://workflow.example.internal \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow authoring-service-publish \
  /tmp/skill2workflow-authoring-set \
  --service-url https://workflow.example.internal \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The first command performs only the existing remote release preflight; it does
not write an artifact or call a connector. The second is a separate explicit
immutable publication action. Both refuse a damaged local set before they read
the token or make a network request. Remote publication still does not trigger
work, resolve credentials, promote an alias, or decide a human gate. A
preflight response is a point-in-time review result, not an authorization or a
lock on later publication; inspect the explicit publication receipt.

## Reproduce The Controlled Local Delivery Path

To exercise the complete safe handoff from a standard Skill through controlled
runtime completion, run:

```bash
python3 scripts/authoring_delivery_smoke.py \
  --work-dir /tmp/skill2workflow-authoring-delivery
```

The drill creates a private authoring set, deliberately damages it to prove
verification detection, repairs it from the original Skill with an explicit
backup, and then verifies and bundles the recovered set. It publishes the
resulting DSL to an isolated SQLite control plane and proves both human gate
outcomes: one run is explicitly approved to completion and an independent
second run is explicitly rejected to a safe `failed` terminal state. It writes
Bundle, verification, repair, run, audit, and snapshot evidence under the work
directory. It has no network listener, external connector, or credential; it
is a local contract drill rather than a business-workflow or live-provider
validation.

## Validate Before Download

For a draft opened in the installed editor, select **Validate DSL**. The fixed
loopback route validates the assembled Workflow DSL with the same compiler
validator as the CLI. Its bounded response reports only stable issue codes, so
author-entered content and local paths cannot be reflected into the result. An
issue that applies to a node can additionally report only its zero-based node
ordinal; the editor renders that ordinal without accepting a server-provided
node name. **Save DSL** repeats the same check before downloading the artifact.

This is a structural contract check, not business approval, credential
validation, publication, execution, or a guarantee that a workflow's effects
are appropriate. A generic static server can still provide local graph checks,
but it cannot provide this compiler-backed result; use `skill2workflow ui` or
`skill2workflow validate path/to/workflow.json --format json` before release.

This local compile route is intentionally unavailable from a generic static
server such as `python3 -m http.server`; use `skill2workflow ui` for the
interactive compiler path. Do not place credentials, tokens, customer data, or
other secrets in a Skill document.

## Example Gallery

The web editor can load example Workflow DSL files from:

```text
examples/workflows/
```

Current examples:

- `approval-flow.workflow.json`: approval-oriented flow with a manual human gate
- `sales-follow-up.workflow.json`: sales follow-up with account-owner approval and CRM update boundary
- `customer-service-escalation.workflow.json`: support escalation with SLA check, lead approval, and handoff audit
- `risk-review.workflow.json`: risk decisioning with policy check, analyst approval, and disposition audit
- `operations-analysis.workflow.json`: operating metrics analysis with owner confirmation and action tracking
- `http-connector.workflow.json`: authoring example with manual approval followed by an HTTP connector request and input mapping

See `docs/examples.md` for scenario notes and inspection commands.

Regenerate a LiteGraph fixture from a Workflow DSL file:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli visualize examples/workflows/http-connector.workflow.json -o examples/workflows/http-connector.litegraph.json
```

## Run Overlay Inspection

The editor can also inspect read-only execution evidence when a run-state file is supplied:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli visualize examples/workflows/approval-flow.workflow.json --run-state /tmp/skill2workflow-state/runs/<run_id>.json -o /tmp/approval-flow-overlay.litegraph.json
```

Overlay data is attached under `properties.run_overlay` for each LiteGraph node and summarized under `extra.run_overlay`. It is derived from run state and, when available through control snapshots, promoted audit events. It can include status, current-node marker, event count, latest event type, connector id/kind/status, attempts, retry/recovery flags, compact trigger metadata, and audit event counts.

Overlay data is view state only:

- It is not part of Workflow DSL.
- It is not written back by `write-back`.
- It must not contain raw connector output, resolved credentials, authorization headers, raw webhook bodies, or full trigger input values.

For control-plane inspection, export a snapshot and open the Nodes tab in `web/control.html`:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli control-snapshot --state-dir /tmp/skill2workflow-control -o /tmp/skill2workflow-control-snapshot.json
python3 -m http.server 4173
```

Wheel users can serve the packaged editor and inspector with
`skill2workflow ui --port 4173`; see [`installed-ui.md`](installed-ui.md).

## Safe Write-Back

`write-back` preserves topology and execution identity:

- Node ids are not changed.
- Edges and transition targets are not changed.
- Source metadata, guards, policies, and connector identity are not changed.
- Connector `id` and `kind` are not changed by visual edits.
- Run overlay fields are ignored.

Allowlisted fields:

- Node `title`
- Node `description`
- `action.prompt` for `human_approval`
- `action.instruction` for instruction-like actions
- `retry.max_attempts`
- HTTP `connector.request.method`
- HTTP `connector.request.url`
- HTTP `connector.request.headers`
- HTTP `connector.request.body`
- HTTP `connector.request.response_mode` (`full` or `metadata`)
- HTTP `connector.request.timeout_ms`
- Node active timeout `timeout_ms` (0..86400000 milliseconds)

Unsupported visual edits should be rejected or ignored rather than silently changing execution semantics.

## Adding Node Types

When adding a node type:

1. Update `schemas/workflow.schema.json`.
2. Update `compile_ir_to_workflow()` if the parser/compiler can emit the node type.
3. Update `validate_workflow_structured()` with node-specific requirements.
4. Update `workflow_to_litegraph()` and `web/app.js` so the editor can render and inspect it.
5. Add tests before behavior changes.
6. Add or update an example workflow if the node type is user-facing.

## Adding Compiler Rules

Compiler rules should stay conservative:

- Prefer explicit Skill IR signals over broad keyword matching.
- Preserve source mapping in `metadata.source`.
- Generate failure transitions for non-terminal executable nodes.
- Keep generated workflows valid under `validate_workflow_structured()`.
- Avoid adding runtime dependencies unless the rule directly supports a spec-backed capability.

Useful test targets:

```bash
PYTHONPATH=src python3 -m unittest tests.test_compiler tests.test_dsl_contract tests.test_visualizer -v
```
