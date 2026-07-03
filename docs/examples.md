# Workflow Examples

The example pack shows how standard Agent `SKILL.md` files become controlled Workflow DSL fixtures. Each example keeps Workflow DSL as the execution truth source; LiteGraph JSON is committed only as an inspectable visual fixture.

## Example Matrix

| Scenario | Source Skill | Workflow DSL | LiteGraph | Control Pattern |
| --- | --- | --- | --- | --- |
| Approval flow | `examples/skills/approval-flow/SKILL.md` | `examples/workflows/approval-flow.workflow.json` | `examples/workflows/approval-flow.litegraph.json` | Manual approval before publication |
| Sales follow-up | `examples/skills/sales-follow-up/SKILL.md` | `examples/workflows/sales-follow-up.workflow.json` | `examples/workflows/sales-follow-up.litegraph.json` | Account-owner approval before CRM update |
| Customer service escalation | `examples/skills/customer-service-escalation/SKILL.md` | `examples/workflows/customer-service-escalation.workflow.json` | `examples/workflows/customer-service-escalation.litegraph.json` | SLA check, lead approval, handoff audit |
| Risk review | `examples/skills/risk-review/SKILL.md` | `examples/workflows/risk-review.workflow.json` | `examples/workflows/risk-review.litegraph.json` | Policy check, analyst approval, disposition audit |
| Operations analysis | `examples/skills/operations-analysis/SKILL.md` | `examples/workflows/operations-analysis.workflow.json` | `examples/workflows/operations-analysis.litegraph.json` | Metrics query, threshold check, owner confirmation |
| HTTP connector | n/a | `examples/workflows/http-connector.workflow.json` | `examples/workflows/http-connector.litegraph.json` | Editable HTTP connector request fixture |

## Inspecting Examples

Compile a source skill into Workflow DSL:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli compile examples/skills/sales-follow-up/SKILL.md -o examples/workflows/sales-follow-up.workflow.json
```

Validate a Workflow DSL fixture:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli validate examples/workflows/sales-follow-up.workflow.json --format json
```

Generate a LiteGraph fixture:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli visualize examples/workflows/sales-follow-up.workflow.json -o examples/workflows/sales-follow-up.litegraph.json
```

Open the static editor:

```bash
python3 -m http.server 4173
```

Then visit:

```text
http://localhost:4173/web/
```

## Scenario Notes

### Sales Follow-Up

This example keeps customer-facing sales activity controlled. The workflow requires the account owner to approve the follow-up before the CRM update command can run, then verifies the audit trail.

### Customer Service Escalation

This example separates support triage from escalation authority. It checks SLA context, drafts an escalation plan, pauses for support lead approval, runs the handoff command, and verifies acknowledgement.

### Risk Review

This example models a risk decision where the AI can collect and summarize evidence but cannot apply a hold, release, or escalation state without analyst approval.

### Operations Analysis

This example starts with a metrics query command, checks threshold breaches, drafts an operating narrative, waits for business owner confirmation, and verifies that every action has an owner and due date.

## Fixture Synchronization

`tests/test_examples.py` keeps the example pack synchronized:

- every required enterprise scenario must have a source `SKILL.md`
- every source skill must compile to its committed Workflow DSL fixture
- every Workflow DSL fixture must render to its committed LiteGraph fixture

Run the focused check with:

```bash
PYTHONPATH=src python3 -m unittest tests.test_examples -v
```
