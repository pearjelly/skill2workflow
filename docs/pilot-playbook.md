# Pilot Playbook

This playbook describes the current supported path for a local enterprise pilot of `skill2workflow`.

The goal is to help a team evaluate the execution-control layer without guessing which parts are stable. The pilot stays local-first, dependency-light, and explicit about limits.

## Scenario

The bundled pilot smoke models a customer support escalation flow:

1. A local webhook event starts a published workflow version.
2. Trigger input carries non-secret business metadata: `customer_id`, `priority`, and `ticket_id`.
3. A manual review gate pauses the workflow.
4. The runner approves the gate to simulate an operator decision.
5. A `tool_call` node sends a request to a local HTTP receiver.
6. The HTTP connector resolves an `Authorization` header from a credential handle.
7. The control plane records audit events and exports a snapshot with node overlays.
8. A LiteGraph overlay artifact shows run evidence without storing raw trigger input in overlay metadata.

This scenario is intentionally local. It does not call a real SaaS API, store real secrets, or expose a public webhook endpoint.

## One-Command Smoke

From a fresh checkout:

```bash
python3 scripts/pilot_playbook_smoke.py --work-dir /tmp/skill2workflow-pilot
```

The command resets the work directory by default, runs the pilot, and prints a compact JSON result. Use `--no-reset` only when you intentionally want to keep existing local artifacts.

Expected high-level result:

```json
{
  "ok": true,
  "workflow_id": "workflow_customer_support_pilot",
  "workflow_version": "0.1.0",
  "run_status": "completed"
}
```

## Generated Artifacts

Artifacts are written under `/tmp/skill2workflow-pilot/artifacts/`:

| Artifact | Purpose |
| --- | --- |
| `workflow.json` | Workflow DSL used as the execution truth source. |
| `trigger-response.json` | Compact webhook trigger response with `input_keys`, not full input values. |
| `run.json` | Local run detail with durable context and node results. |
| `control-plane-snapshot.json` | Read-only operator snapshot for `web/control.html`. |
| `workflow.overlay.litegraph.json` | LiteGraph graph with read-only run overlay evidence. |

Open the control-plane inspector:

```bash
python3 -m http.server 4173
```

Then visit:

```text
http://localhost:4173/web/control.html
```

Load `/tmp/skill2workflow-pilot/artifacts/control-plane-snapshot.json`. Use the Operator, Runs, Audit, and Nodes views to inspect the completed pilot run. The Nodes view should show `call_support_api` with connector status `completed`.

## What This Pilot Proves

The current local bootstrap can demonstrate:

- immutable workflow publish before execution
- webhook-triggered published runs
- durable trigger input context
- compact audit metadata that exposes input keys instead of full input values
- manual gate pause and resume
- HTTP connector execution through a local receiver
- credential handle resolution outside Workflow DSL
- run and connector audit events
- read-only node overlays in snapshots and LiteGraph JSON
- static local inspection without a hosted service

## Supported Boundaries

Supported for this pilot:

- Python 3.9 standard-library runtime
- JSON/JSONL local state
- SQLite local state for existing CLI paths
- local webhook adapter on `127.0.0.1`
- local HTTP connector targets used for deterministic evaluation
- local credential handles supplied through a provider or credential file
- static UI inspection through exported JSON artifacts

Use non-secret pilot metadata in trigger input. Keep credentials outside Workflow DSL and outside trigger payloads.

## Experimental Boundaries

The following surfaces are useful for evaluation but not yet stable production interfaces:

- internal Python helper APIs
- exact snapshot JSON shape beyond documented user-facing fields
- LiteGraph layout details
- connector runtime beyond built-in `manual` and `http`
- retry behavior beyond the current local connector retry policy

## Out Of Scope

Do not treat this bootstrap as providing:

- public webhook ingress
- hosted control plane
- authentication, RBAC, IAM, or multi-tenant isolation
- production secret management or encryption
- queues, distributed scheduling, or guaranteed idempotency
- product-specific SaaS connector packages
- automatic conversion of arbitrary SOP documents
- production deployment guidance

## Verification Checklist

Run the focused pilot checks:

```bash
PYTHONPATH=src python3 -m unittest tests.test_pilot -v
python3 scripts/pilot_playbook_smoke.py --work-dir /tmp/skill2workflow-pilot
python3 scripts/schedule_smoke.py --work-dir /tmp/skill2workflow-schedule-loop29
python3 -m json.tool /tmp/skill2workflow-pilot/artifacts/control-plane-snapshot.json >/tmp/skill2workflow-pilot-snapshot-check.json
python3 -m json.tool /tmp/skill2workflow-pilot/artifacts/workflow.overlay.litegraph.json >/tmp/skill2workflow-pilot-overlay-check.json
python3 -m json.tool /tmp/skill2workflow-schedule-loop29/artifacts/control-plane-snapshot.json >/tmp/skill2workflow-schedule-snapshot-check.json
```

Run the broader local verification before opening a PR:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

## Next Pilot Work

After this playbook and the local schedule boundary, the next useful closed loops are:

- richer input mapping from trigger context into connector request bodies
- more pilot scenarios that reuse the same support boundary
- explicit extension contracts for product-specific connector packages
