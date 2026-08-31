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
