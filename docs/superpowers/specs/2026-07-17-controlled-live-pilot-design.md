# Controlled Live Connector Pilot Design

## Status

Approved on 2026-07-17 for Loop 40 implementation.

This design advances `skill2workflow` from Local Evaluation to the Controlled Live Pilot gate. It does not claim Self-hosted Beta or general live SaaS readiness.

## Goal

Run the existing sales-renewal-risk workflow as an assisted paid pilot for one consenting real team. The workflow must preserve an explicit human decision before the fixed Lark/Feishu `create_task` action, produce reproducible redacted evidence, exercise failure and rollback boundaries, and end with a documented `continue`, `harden`, or `defer` decision.

The pilot is commercially real only when the partner has agreed to a paid or contractually committed assisted engagement. Repository evidence records only `commercial_engagement_confirmed: true`; customer identity, pricing, contract text, and payment details remain outside the repository.

## Approved Scenario

The only business scenario in Loop 40 is:

1. A sales operator submits a real renewal-risk case.
2. The workflow persists the non-secret business input in a private runtime state directory.
3. A designated operator reviews the case at a human gate.
4. Rejection terminates the run without invoking the Lark connector.
5. Approval resumes the same durable run and invokes the fixed Lark/Feishu `create_task` action.
6. The resulting task is assigned to a consenting real user.
7. A redacted evidence generator derives compact proof from run and audit state without copying raw business values, credentials, provider messages, or task identifiers.

The existing Loop 37 sales-renewal dry-run workflow is the behavioral baseline. Loop 40 introduces a separate controlled-live pilot path rather than changing the dry-run default.

## Options Considered

### Extend the existing pilot runner — selected

Add a controlled-live runner and evidence pack around the current workflow, control plane, SQLite storage, credential provider, external connector, and audit surfaces.

This option reuses the strongest verified path, keeps the scope at one action, and produces workflow-level evidence instead of another connector-only validation.

### Wrap the one-shot validation helper

The existing validation helper can prove a real provider write, but it bypasses workflow publication, trigger input, the human gate, durable resume, and control-plane audit. It cannot satisfy Loop 40 by itself.

### Build the long-running production service first

A service boundary would be useful for Self-hosted Beta, but it belongs to Loop 41. Pulling it into Loop 40 would expand scope without improving the immediate real-team evidence requirement.

## Acceptance Contract

The pilot gate is complete only when all of the following are true:

- A consenting real team has an approved pilot charter.
- The charter records `commercial_engagement_confirmed: true` and the assisted support model without customer identity, price, payment, or contract details.
- At least five approved live workflow runs complete across at least five distinct calendar days.
- The approved runs represent at least two distinct private renewal-risk cases.
- At least one real human-gate rejection completes without any connector invocation.
- One safe failure exercise proves that a disabled live switch prevents credential resolution and provider transport.
- One rollback exercise proves that live behavior can be disabled while the existing dry-run pilot remains operational.
- Every live run uses the fixed Feishu domestic host and fixed `create_task` operation.
- Every live retry for the same execution identity reuses the provider-native idempotency token.
- The generated evidence pack contains no resolved credential, authorization header, raw task value, user id, provider payload, provider message, task id, or idempotency digest.
- The complete automated test suite, focused pilot checks, dry-run smoke, compilation, secret hygiene, and `git diff --check` pass.
- The partner and operator record a final `continue`, `harden`, or `defer` decision with a short redacted rationale.

Five approved runs across five calendar days are a minimum evidence threshold, not a reliability or SLA claim. Failed business runs remain part of the evidence and do not get silently discarded or replaced.

## Architecture

### Controlled pilot command

Introduce one operator-facing command wrapper backed by a focused Python module. The command has explicit phases rather than an auto-approved one-shot flow:

- `init`: validate and persist a redacted pilot charter plus private pilot configuration.
- `start`: read one private business-input JSON file, publish or reuse the immutable workflow version, trigger a run, and stop at the human gate.
- `decide --approve`: resume an existing waiting run and allow the live connector action only when every live guard is present.
- `decide --reject`: resume the run as rejected and prove no connector action occurred.
- `evidence`: regenerate the complete redacted evidence pack from authoritative private state.
- `exercise-failure`: prove the disabled-live preflight boundary without resolving credentials or calling transport.
- `exercise-rollback`: disable live execution and prove the existing dry-run smoke still completes.
- `finalize`: validate all acceptance conditions and write the final decision record.

Command names may be implemented as subcommands or equivalent explicit flags, but the phase separation and safety properties are contract requirements.

### Private runtime state

All raw business input and resolved secrets stay outside the repository in an operator-selected private work directory.

The private directory contains:

- SQLite control-plane and run state;
- private business-input files;
- local execution configuration;
- any operator-only diagnostic material that contains raw values.

The runner must reject a private work directory inside the repository. Newly created private directories and files use owner-only permissions where the platform supports them. The tool must not accept the bot token as a command-line argument. The token is injected into the child process by Vault or an equivalent secret manager as `LARK_BOT_ACCESS_TOKEN` and immediately wrapped by the existing credential-provider interface.

The current durable run-context contract permits user-supplied business values in private run state. It does not permit credentials in trigger input or persisted state.

### Redacted evidence pack

The evidence directory is safe to inspect, review, and commit after validation. It is derived from authoritative runtime and audit state and never serves as execution input.

The pack contains:

- `pilot-charter.json`: scenario id, workflow id/version, support model, consent flags, commercial-confirmation boolean, planned date range, and acceptance thresholds;
- `runs/<sequence>.json`: compact run identity, timestamps, gate decision, terminal status, connector status, approved metadata-presence flags, credential handle names, credential status, provider status, and idempotency-presence boolean;
- `exercises/rejection.json`: proof that a rejected gate produced no connector event;
- `exercises/failure.json`: proof that the disabled live switch stopped before credentials or transport;
- `exercises/rollback.json`: proof that live mode was disabled and the dry-run pilot still completed;
- `evidence-index.json`: aggregate counts, distinct calendar days, distinct private-case count represented only as a count, exercise status, test status, and unmet acceptance conditions;
- `decision.json`: `continue`, `harden`, or `defer`, partner acknowledgement boolean, operator acknowledgement boolean, commercial-confirmation boolean, and a compact redacted rationale.

The evidence pack must not contain the private input path, customer name, account id, renewal-risk text, assignee open id, due date, token, authorization header, request body, response body, provider task guid, provider message, client-token digest, or raw run context.

Evidence generation is deterministic for a given authoritative state except for an explicit generation timestamp. Re-running it replaces derived files atomically rather than appending contradictory summaries.

### Live safety gates

An approved live decision requires all of these conditions in the same process:

- the run is currently waiting at the expected human gate;
- the operator passes an explicit live-confirmation flag;
- `SKILL2WORKFLOW_LARK_TASK_LIVE=1` is exact;
- `LARK_BOT_ACCESS_TOKEN` is present through process injection;
- the workflow connector is `lark_task` with operation `create_task` and mode `live`;
- the credential handle is exactly `lark_bot_access_token`;
- the workflow id, version, run id, and node id needed for provider idempotency are present;
- the pilot charter is valid and has not expired;
- the run has not already reached a terminal state.

Missing gates fail closed. A rejection never requires the live switch or credential. Re-running approval for a completed run must not create another provider request.

### Workflow and data flow

`start` builds the controlled-live workflow from a fixed template, validates it, publishes the immutable version, and triggers it with one private case. It must not mutate the committed Loop 37 dry-run fixture or make live mode the connector default.

The workflow sequence remains:

```text
start -> review_renewal_risk -> create_lark_task -> end
                              \-> failure
review_renewal_risk --reject---------------------> failure
```

Input mapping remains limited to title, description, assignee, and due time. The connector continues to construct the Feishu domestic URL, HTTP method, headers, timeout, and provider body internally.

Approval resumes the same run. The executor supplies `workflow_id + workflow_version + run_id + node_id` ephemerally, and the connector derives the provider-native client token from that identity. Retrying the same node keeps the identity stable; a distinct run gets a distinct token.

## Failure And Rollback Exercises

### Human rejection

Start a valid case, reject it at the gate, and record a terminal rejected/failed run. Audit evidence must include the gate decision and must not include `connector_started`, `connector_completed`, or `connector_failed` for the Lark task node.

### Disabled-live failure

Use a controlled test run with the live connector binding but without the exact live switch. The result must be `provider_status: live_disabled`. Credential resolution and transport must not occur. The evidence records presence/status fields only.

This exercise is safe for routine execution because it cannot write to Feishu.

### Rollback

Remove the live switch, verify that live approval fails closed, and then run the existing dry-run sales-renewal pilot unchanged. The rollback is successful only when the dry-run completes and its redaction checks still pass.

No rollback step edits Workflow DSL compatibility, removes the connector package, or deletes historical evidence.

## Error Handling

- Invalid charter, private input, directory location, file permissions, workflow binding, or run state fails before live execution.
- Missing or expired charter fails before trigger or resume.
- Missing live confirmation, environment switch, credential, or execution identity fails closed with compact status.
- Provider failures retain only the normalized status already approved in Loop 39.
- Evidence validation failures never delete private runtime state; they report the exact evidence contract violation without echoing the sensitive value.
- Finalization fails while any threshold, exercise, acknowledgement, or verification item is missing.
- A failed run remains inspectable and countable; the operator starts a new run only for a new business attempt, not to rewrite history.

## Testing Strategy

Implementation follows test-driven development.

Focused tests cover:

- charter validation, expiry, consent, and commercial-confirmation requirements;
- rejection of repository-contained private work directories;
- owner-only file and directory creation where supported;
- fixed controlled-live workflow shape and unchanged dry-run default;
- start stopping at the expected human gate;
- approval and rejection as separate operations;
- approval guard failures before credential or transport access;
- repeated approval of a terminal run making no connector call;
- fake-transport live success through the complete published workflow;
- fake provider failure and stable retry identity;
- rejection producing no connector events;
- failure and rollback exercise evidence;
- deterministic evidence regeneration and atomic replacement;
- exact evidence allowlist and forbidden-value leakage tests;
- acceptance aggregation for five approved runs across five days and two private cases;
- finalization rejecting incomplete evidence;
- `continue`, `harden`, and `defer` decision validation;
- CLI summaries containing compact metadata only.

Verification commands include:

```bash
PYTHONPATH=src python3 -m unittest tests.test_controlled_lark_pilot -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py examples/connectors/lark_task_connector.py
python3 scripts/secret_hygiene.py examples/workflows
python3 scripts/lark_task_connector_smoke.py --work-dir /tmp/skill2workflow-lark-task-connector
python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot
git diff --check
```

Real provider calls are never part of automated tests or CI.

## Pilot Operating Sequence

1. Create a private pilot directory outside the repository.
2. Initialize and review the redacted charter.
3. Run the unchanged dry-run rehearsal.
4. Inject the token through Vault and start the first private case.
5. Inspect the waiting run and explicitly approve or reject it.
6. Regenerate and inspect the redacted evidence pack.
7. Repeat until at least five approved runs span five calendar days and two private cases.
8. Complete the explicit rejection exercise.
9. Complete the disabled-live failure and rollback exercises.
10. Run the complete verification suite.
11. Record partner and operator acknowledgement plus the final decision.
12. Run finalization; only a successful finalization may advance the Roadmap gate.

## Roadmap Completion

After finalization proves every acceptance condition:

- add the controlled live-pilot runbook;
- commit only validated redacted evidence;
- record the final decision;
- move Loop 40 to complete in `ROADMAP.md`;
- update the completed-loop count to 1-40;
- set current maturity to Controlled Live Pilot;
- select or defer the next loop based on the evidence;
- update the compact `README.md` status without copying the rolling queue;
- preserve Loops 41-43 as candidates unless the final decision explicitly selects one under the Roadmap rules.

Roadmap completion is a separate final task after the multi-day real pilot. Passing fake-transport tests and generating an empty evidence skeleton must not advance the maturity gate.

## Out Of Scope

- Additional Lark/Feishu actions or APIs.
- OAuth, token refresh, hosted callbacks, or public ingress.
- Automatic connector discovery, installation, or marketplace behavior.
- Background workers, queues, distributed scheduling, or production scheduling.
- Multi-tenant control plane, tenant isolation, RBAC, or IAM.
- Hosted secret management or a general credential product.
- Loop 41 long-running service behavior.
- Exactly-once claims, SLA claims, or general production-readiness claims.
- Committing customer identity, commercial terms, raw pilot payloads, or live credentials.

## Implementation Boundaries

- Python 3.9 standard library remains sufficient.
- Workflow DSL remains the execution source of truth.
- SQLite is used for the controlled pilot's private durable state.
- The Lark connector remains out of core and explicitly loaded.
- Dry-run remains the connector and example default.
- Existing Workflow DSL `0.1.0` compatibility is unchanged.
- No new runtime dependency is introduced.
- Parser, compiler, validator, executor, connector, storage, or CLI behavior changes begin with failing tests.

## Completion Evidence Map

| Requirement | Authoritative evidence |
| --- | --- |
| Paid assisted engagement | Validated charter and final decision with `commercial_engagement_confirmed: true` |
| Real-team use | Five redacted approved-run records across five dates plus partner acknowledgement |
| Complete workflow | Published workflow identity, waiting gate evidence, resume evidence, and connector terminal status |
| Human control | Approved-run gate decisions and one rejection with no connector event |
| Live action | `mode: live`, `provider_status: completed`, and task-id-presence boolean |
| Idempotency | Stable execution identity tests and idempotency-presence evidence |
| Failure boundary | Disabled-live exercise with no credential or transport access |
| Rollback boundary | Live-disabled proof plus unchanged successful dry-run smoke |
| Redaction | Evidence allowlist validator, forbidden-value tests, and secret-hygiene verification |
| Business decision | Final validated `continue`, `harden`, or `defer` record |
