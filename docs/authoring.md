# Authoring Workflows

This guide describes the current authoring surface for `skill2workflow`.

Workflow DSL remains the execution truth source. The LiteGraph editor is an inspection and editing surface that must round-trip back through Workflow DSL validation before a workflow is published or run.

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
- `http-connector.workflow.json`: authoring example with manual approval followed by an HTTP connector request

See `docs/examples.md` for scenario notes and inspection commands.

Regenerate a LiteGraph fixture from a Workflow DSL file:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli visualize examples/workflows/http-connector.workflow.json -o examples/workflows/http-connector.litegraph.json
```

## Safe Write-Back

`write-back` preserves topology and execution identity:

- Node ids are not changed.
- Edges and transition targets are not changed.
- Source metadata, guards, policies, and connector identity are not changed.
- Connector `id` and `kind` are not changed by visual edits.

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
- HTTP `connector.request.timeout_ms`

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
