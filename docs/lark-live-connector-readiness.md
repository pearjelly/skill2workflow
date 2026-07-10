# Lark/Feishu Live Connector Readiness Review

Decision: proceed to a scoped live `create_task` implementation in Loop 39.

This decision approves one narrow follow-up implementation path. It does not make live SaaS connector behavior part of the default runtime, and it does not change the Workflow DSL authority model.

## Evidence From Prior Loops

Loop 36 package-level dry-run smoke proved that the Lark/Feishu task connector can remain out-of-core, be explicitly loaded by file path, validate a `create_task` request, resolve `lark_bot_access_token` through the local credential provider, and return compact connector metadata without raw mapped task values.

Loop 37 pilot-workflow dry-run smoke proved the same connector inside a business workflow with webhook trigger input, a manual control gate, durable audit evidence, a control snapshot, and LiteGraph overlay artifacts:

```bash
python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot
```

The remaining risk is no longer whether the local connector package shape works. The remaining risk is whether a single live Lark/Feishu API action can be executed with explicit credentials, idempotency, failure handling, audit redaction, and rollback boundaries.

## Approved Live Action Surface

Loop 39 may implement only this live action surface:

- connector id: `lark_task`
- operation: `create_task`
- mode: `live`
- node type: `tool_call`
- credential handle: `lark_bot_access_token`

| Field | Approved value |
| --- | --- |
| connector id | `lark_task` |
| connector kind | `lark_task` |
| operation | `create_task` |
| mode | `live` |
| node type | `tool_call` |
| credential handle | `lark_bot_access_token` |

The live request body may use the same business fields already validated by dry-run mode: `title`, `description`, `assignee_open_id`, and `due_at`.

`examples/connectors/lark_task_connector.py remains dry-run-only in Loop 38`. Loop 39 must introduce live behavior behind an explicit opt-in path, not as an implicit change to existing dry-run examples.

Explicit non-goals:

- No OAuth.
- No hosted callback.
- No automatic connector discovery.
- No token refresh system.
- No connector marketplace or package installer.
- No queue, worker pool, or production scheduler.
- No broad Lark/Feishu connector catalog.
- No live behavior for any operation except `create_task`.

## Credential Model

The approved credential handle is `lark_bot_access_token`.

The token is resolved only through the credential provider at connector execution time. It must not be stored in:

- not Workflow DSL
- not trigger input
- not run state
- not audit events
- not LiteGraph fixtures
- not smoke artifacts

Workflow DSL may reference the handle name, but the resolved credential value must remain outside immutable workflow artifacts and persisted run evidence. Missing credentials, unsupported credential targets, or provider resolution errors must become failed connector results with compact error metadata.

## Idempotency And Duplicate Prevention

Live `create_task` must require an idempotency key before making a task creation request.

The local runtime should derive the default key from `workflow_id + version + run_id + node_id` unless the future API contract exposes a better first-class idempotency field. If Lark/Feishu does not support a native idempotency header for task creation, Loop 39 must still record the derived key in local connector metadata and reject unsafe re-execution for the same key before attempting duplicate task creation.

Duplicate task creation is the primary live-operation hazard. The connector should prefer a safe failure over guessing whether a previous call succeeded when the idempotency record is ambiguous.

## Failure Modes

Loop 39 must map expected live failures into normalized connector results rather than leaking provider-specific details through exceptions:

| Failure | Required behavior |
| --- | --- |
| `401 or 403` | Failed connector result with compact authorization status and no token echo. |
| Permission denied for task creation | Failed connector result with compact permission status. |
| `rate limit` | Failed connector result that allows existing retry policy to decide whether to retry. |
| `network timeout` | Failed connector result or existing connector execution error path, with no raw request body in audit. |
| Provider validation error | Failed connector result with field-level category only. |
| Unexpected provider response | Failed connector result without raw response payload leakage. |

Audit and run output should preserve enough state for operators to understand whether the live call was attempted, completed, failed, or skipped. It should not preserve raw provider responses unless a future redaction contract explicitly allows safe structured fields.

## Audit Redaction

Allowed compact audit fields:

- `operation`
- `mode`
- `task_title_present`
- `task_description_present`
- `assignee_present`
- `due_at_present`
- `lark_task_id_present`
- `credential_handles`
- `credential_status`
- `idempotency_key_present`
- `provider_status`

Disallowed audit and run-state fields:

- raw task values
- raw `title`
- raw `description`
- raw `assignee_open_id`
- raw `due_at`
- resolved credential values
- authorization headers
- raw request bodies
- raw response payloads

The live result may expose a Lark task id only through a compact presence flag by default. If Loop 39 needs the task id for operator diagnostics, the PR must justify why the id is non-secret and must still keep the default audit path compact.

## Local Test Strategy

Loop 39 should test live-mode behavior with a fake Lark HTTP receiver or injected fake transport. There must be no live network in CI.

Required tests before any live API implementation can merge:

- dry-run remains the default when `mode` is missing
- mode `dry_run` remains the default
- `mode: live` requires `lark_bot_access_token`
- live mode sends only the approved `create_task` request shape
- the fake receiver can simulate success, `401 or 403`, rate limit, network timeout, validation error, and malformed response cases
- raw task values and resolved credentials do not appear in result summaries, run state, audit logs, or snapshot artifacts
- the idempotency key blocks duplicate task creation attempts for the same `workflow_id + version + run_id + node_id`

The existing dry-run tests and smoke commands must continue to pass unchanged.

## Rollback Boundaries

Loop 39 must keep live behavior behind a feature flag or equivalent explicit opt-in setting. The default remains dry-run.

Rollback requirements:

- A maintainer can disable live mode without removing the dry-run connector package.
- Reverting Loop 39 must not require changing Workflow DSL compatibility.
- A maintainer must be able to revert Loop 39 without changing Workflow DSL compatibility.
- Reverting Loop 39 must not invalidate existing dry-run smokes, pilot artifacts, or connector package documentation.
- Live-mode failures must not prevent the dry-run connector from being loaded explicitly.

Loop 39 should be considered complete only when the implementation proves these rollback boundaries with tests and documentation.
