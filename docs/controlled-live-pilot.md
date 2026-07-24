# Controlled Lark/Feishu Live Pilot Runbook

This runbook operates Loop 40 as a paid assisted engagement for one consenting real team. It is not a general live-connector guide. Team consent, the designated assignee's consent, and a paid or contractually committed engagement must all be confirmed before initialization. Customer identity, pricing, payment, and contract details remain outside this repository.

The dry-run remains the default. Controlled live behavior is limited to one `create_task` action through the explicitly loaded `lark_task` connector and the fixed Feishu domestic Task API host. Do not adapt these commands to another action, host, API, connector, or provider.

The operator phases are: init preflight start decide evidence exercise-failure exercise-rollback verify finalize . Each successful phase prints one compact redacted JSON line. Keep run ids and all private working material in the owner-controlled operating environment.

## 1. Prerequisites And Private Workspace

Use an owner-controlled directory outside the source repository. This runbook uses:

```bash
export PRIVATE_PILOT="$HOME/.local/share/skill2workflow/pilots/loop-40"
```

Do not place the private workspace, case files, decision draft, credentials, provider diagnostics, or terminal captures in the repository. The tool rejects a work directory inside the repository and creates pilot directories with owner-only permissions where the platform supports them.

Before proceeding, the operator must verify all three facts directly with the partner:

- the team consents to the assisted pilot;
- the real task assignee consents to task creation;
- the engagement is paid or contractually committed.

Only confirmation booleans are recorded. Do not enter a customer name, price, payment detail, contract text, or other business detail in the init command.

## 2. Initialize The Fixed Charter

From the source checkout, run the exact init command for the approved engagement window:

```bash
python3 scripts/controlled_lark_pilot.py init \
  --work-dir "$PRIVATE_PILOT" \
  --starts-on 2026-07-18 \
  --expires-on 2026-08-15 \
  --confirm-team-consent \
  --confirm-assignee-consent \
  --confirm-commercial-engagement
```

The command constructs the fixed charter in code. Its only operator-selected values are the two dates and the three required consent/commercial-confirmation booleans. Inspect `$PRIVATE_PILOT/private/charter.json` locally and confirm the scenario, workflow version, `assisted` support model, `Asia/Shanghai` timezone, and thresholds of five approved runs, five days, and two cases. Do not copy the private path or local inspection output into repository evidence.

Run the unchanged dry-run rehearsal before live work:

```bash
python3 scripts/lark_task_pilot_smoke.py \
  --work-dir "$PRIVATE_PILOT/private/rehearsal"
```

The rehearsal must complete in `dry_run` mode. A dry-run failure stops the pilot.

## 3. Prepare One Private Case

Create each case file below an owner-controlled location such as `$PRIVATE_PILOT/private/cases/`. The file must conform to this exact schema:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["pilot_case_id", "account_name", "renewal_risk", "owner_open_id", "due_at"],
  "properties": {
    "pilot_case_id": {"type": "string", "const": "case-001"},
    "account_name": {"type": "string", "minLength": 1},
    "renewal_risk": {"type": "string", "minLength": 1},
    "owner_open_id": {"type": "string", "minLength": 1},
    "due_at": {"type": "string", "format": "date-time"}
  }
}
```

`case-001` is an opaque pilot identifier, not an account name. For the fourth approved calendar date, use the Day 4 exact schema below. It differs only in the required opaque id:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["pilot_case_id", "account_name", "renewal_risk", "owner_open_id", "due_at"],
  "properties": {
    "pilot_case_id": {"type": "string", "const": "case-002"},
    "account_name": {"type": "string", "minLength": 1},
    "renewal_risk": {"type": "string", "minLength": 1},
    "owner_open_id": {"type": "string", "minLength": 1},
    "due_at": {"type": "string", "format": "date-time"}
  }
}
```

This exact second schema ensures the acceptance evidence represents at least two private cases. Put real partner-approved values only in the private file; do not put them in shell arguments, documentation, tickets, or repository files.

Protect the case before start:

```bash
chmod 600 "$PRIVATE_PILOT/private/cases/day-1.json"
python3 scripts/controlled_lark_pilot.py preflight \
  --input "$PRIVATE_PILOT/private/cases/day-1.json"
python3 scripts/controlled_lark_pilot.py start \
  --work-dir "$PRIVATE_PILOT" \
  --input "$PRIVATE_PILOT/private/cases/day-1.json"
```

`preflight` constructs the exact fixed Task v2 request body locally and returns only compact presence and readiness fields. It does not resolve Vault credentials, enable live mode, does not make a network request, and does not create a Feishu task. A `ready` result is a local contract check only; it does not replace the human review, the explicit approval, or a real provider result. An `invalid` result stops the case before `start`; correct the owner-only case file and run preflight again.

The start result must show `run_status: waiting` and `current_node: review_renewal_risk`. Record the opaque run id privately. Before any decision, the designated operator must inspect the compact waiting summary and the owner-only case file, confirm the intended assignee and task contents, and verify that the run is still waiting at that exact human gate.

## 4. Make The Explicit Human Decision

### Approval: Vault injection only

Only an approved, inspected waiting run may receive the live switch and token. Use this exact approve-only command shape:

```bash
vibe vault run --env LARK_BOT_ACCESS_TOKEN -- \
  env SKILL2WORKFLOW_LARK_TASK_LIVE=1 \
  python3 scripts/controlled_lark_pilot.py decide \
    --work-dir "$PRIVATE_PILOT" \
    --run-id "$APPROVED_RUN_ID" \
    --approve \
    --confirm-live-create
```

Never paste a token into the command, a file, or shell history. Approval must fail closed unless the run is waiting, the explicit confirmation is present, the live switch is exactly `1`, the Vault-injected `LARK_BOT_ACCESS_TOKEN` exists, and the fixed live workflow binding is unchanged. Success reports normalized status and presence booleans only; it must not print task values, provider messages, provider task ids, token material, or request/response bodies.

### Rejection: no Vault

Rejection neither needs nor permits live confirmation. After inspecting a separate waiting run, run without Vault and without either live environment variable:

```bash
env -u SKILL2WORKFLOW_LARK_TASK_LIVE -u LARK_BOT_ACCESS_TOKEN \
  python3 scripts/controlled_lark_pilot.py decide \
    --work-dir "$PRIVATE_PILOT" \
    --run-id "$REJECTED_RUN_ID" \
    --reject
```

The result must report `gate_decision: rejected` and `connector_invoked: false`. `--reject --confirm-live-create` is an operator error.

## 5. Regenerate Evidence After Every Run

After every approved, rejected, or failed run, regenerate the complete private evidence pack:

```bash
python3 scripts/controlled_lark_pilot.py evidence \
  --work-dir "$PRIVATE_PILOT"
```

Inspect `$PRIVATE_PILOT/evidence` for compact statuses and presence flags only. Retain failed historical runs; never replace them with clean runs. Do not export or commit an incomplete pack.

Complete at least five approved live runs across five distinct calendar days in `Asia/Shanghai`. Use `case-001` for the first three dates, `case-002` on the fourth date, and either opaque id on the fifth. This threshold is not an SLA or general reliability claim. The pack must also contain at least one rejected human-gate run with no connector invocation.

## 6. Exercise Failure And Rollback

Run both safe exercises with live variables removed:

```bash
env -u SKILL2WORKFLOW_LARK_TASK_LIVE -u LARK_BOT_ACCESS_TOKEN \
  python3 scripts/controlled_lark_pilot.py exercise-failure \
    --work-dir "$PRIVATE_PILOT"

env -u SKILL2WORKFLOW_LARK_TASK_LIVE -u LARK_BOT_ACCESS_TOKEN \
  python3 scripts/controlled_lark_pilot.py exercise-rollback \
    --work-dir "$PRIVATE_PILOT"
```

The disabled-live exercise must report `provider_status: live_disabled` with no credential resolution and no provider transport. Rollback must prove that live approval is blocked while the unchanged dry-run pilot still completes. Regenerate private evidence after both exercises.

## 7. Run The Fixed Sanitized Verification

After the five-day gate and exercises are complete, run:

```bash
env -u SKILL2WORKFLOW_LARK_TASK_LIVE -u LARK_BOT_ACCESS_TOKEN \
  python3 scripts/controlled_lark_pilot.py verify \
    --work-dir "$PRIVATE_PILOT"
```

The fixed verify phase runs exactly seven checks: focused controlled-pilot tests, the full suite, Python compilation, secret hygiene, connector smoke, dry-run pilot smoke, and `git diff --check`. All seven must pass. Verification output contains command ids, exit status, pass/fail state, and duration only; it excludes captured command output.

## 8. Prepare The Redacted Decision

Partner and operator choose `continue`, `harden`, or `defer`. Create `$PRIVATE_PILOT/private/decision.json` using this exact allowlisted schema and a short rationale with no customer, account, user, task, token, provider, price, or contract detail:

```json
{
  "schema_version": "controlled-lark-pilot-decision-0.1.0",
  "decision": "defer",
  "partner_acknowledged": true,
  "operator_acknowledged": true,
  "commercial_engagement_confirmed": true,
  "rationale": "The controlled evidence supports the recorded next-step decision within the approved boundary."
}
```

Protect the file before finalization:

```bash
chmod 600 "$PRIVATE_PILOT/private/decision.json"
```

The decision file must be an owner-only regular file outside the repository, not a symbolic link. Rationale is accepted only through this file; it is never a command-line argument.

## 9. Finalize And Export Only After Every Gate Passes

Run the exact finalize command from the repository root:

```bash
python3 scripts/controlled_lark_pilot.py finalize \
  --work-dir "$PRIVATE_PILOT" \
  --decision-file "$PRIVATE_PILOT/private/decision.json" \
  --output-dir docs/pilot-evidence/loop-40
```

Finalization must fail while any threshold, rejection, exercise, verification, commercial confirmation, acknowledgement, or decision condition is missing. The only permitted repository export target is exactly `docs/pilot-evidence/loop-40`. Review the generated allowlisted JSON before committing; never commit private state, raw payloads, provider values, or credentials.

After the engagement, rotate or delete the pilot token according to the partner's credential policy, remove the live switch, and retain only the agreed private retention set and validated redacted repository evidence.

## Incident Stop And Deferral

Stop immediately if a run exposes a forbidden value, bypasses the human gate, creates an unexpected duplicate, targets the wrong assignee, encounters a permission or redaction anomaly, uses a non-normalized provider result, or deviates from the fixed domestic endpoint and action. Remove the live switch, do not approve another run, retain authoritative private state, record a `defer` candidate decision, and return with a failing regression test. Never hide or replace the failed run.

Offline tests, fake transport, an empty evidence skeleton, and implementation readiness must not advance Loop 40. A deferred Pilot remains at Local Evaluation; any replacement Pilot requires a fresh authorization boundary and must successfully finalize the paid five-day real-team evidence gate before the separate Roadmap completion task may run.
