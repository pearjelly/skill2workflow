# Lark/Feishu Live Connector Readiness Review

Decision: proceed to a scoped live `create_task` implementation in Loop 39. That implementation is now available as an explicitly loaded, opt-in connector path while dry-run remains the default.

This decision approves one narrow follow-up implementation path. It does not make live SaaS connector behavior part of the default runtime, and it does not change the Workflow DSL authority model.

## Evidence From Prior Loops

Loop 36 package-level dry-run smoke proved that the Lark/Feishu task connector can remain out-of-core, be explicitly loaded by file path, validate a `create_task` request, resolve `lark_bot_access_token` through the local credential provider, and return compact connector metadata without raw mapped task values.

Loop 37 pilot-workflow dry-run smoke proved the same connector inside a business workflow with webhook trigger input, a manual control gate, durable audit evidence, a control snapshot, and LiteGraph overlay artifacts:

```bash
python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot
```

Loop 39 closes the connector-level implementation risk with fake-transport coverage for explicit credentials, provider-native idempotency, failure handling, audit redaction, and rollback boundaries. A real provider call remains a separately guarded validation action and is never part of CI.

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

Loop 39 implements that scoped path against one fixed provider boundary:

```text
POST https://open.feishu.cn/open-apis/task/v2/tasks?user_id_type=open_id
```

The connector constructs the method, Feishu domestic host, Task API v2 path, `user_id_type=open_id` query, and headers internally. Workflow input cannot override them. The required provider scope is either `task:task:write` or `task:task:writeonly`, the documented limit is 10 create requests per second, and the connector uses a fixed 10-second timeout.

Live activation requires both `mode: live` in the explicitly loaded connector binding and the exact environment switch `SKILL2WORKFLOW_LARK_TASK_LIVE=1`. Missing mode and explicit `mode: dry_run` both retain dry-run behavior. Any other environment value returns compact `provider_status: live_disabled` metadata before credential resolution or transport invocation.

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

Normal connector execution resolves only that approved handle through the configured credential provider. Unrelated header-target handles are not materialized. `LARK_BOT_ACCESS_TOKEN` is not a general connector configuration surface; it is read only by the guarded live-validation helper, which immediately wraps it in the existing credential provider and never accepts or prints the token as a command-line value.

## Idempotency And Duplicate Prevention

Live `create_task` requires all four runtime-owned identity values from `workflow_id + version + run_id + node_id` before making a request. The connector canonicalizes those values and hashes them into the provider's native `client_token`. This native token is the provider idempotency key: it is stable for retries of the same execution identity and changes for a different version, run, or node.

Retries may still invoke transport; the stable native `client_token` and unchanged request parameters let Feishu perform provider-side deduplication. This provider mechanism controls duplicate task creation: the connector does not locally block retry transport calls and Loop 39 adds no local idempotency database. Connector-produced state records only `idempotency_key_present`, never the token digest. A provider-reported idempotency conflict becomes a safe failure with compact metadata instead of a guessed retry.

## Failure Modes

Loop 39 maps expected live failures into normalized connector results rather than leaking provider-specific details through exceptions. The compact `provider_status` categories are:

| Failure | `provider_status` | Required behavior |
| --- | --- | --- |
| Live switch absent | `live_disabled` | Fail before credential or transport access. |
| Invalid local input or execution identity | `validation_failed` | Fail before transport access. |
| Missing credential | `credential_failed` | Preserve only the handle and compact status. |
| HTTP `401 or 403` | `authorization_failed` or `permission_denied` | Fixed error text with no token echo. |
| HTTP 429 / `rate limit` | `rate_limited` | Existing retry policy decides whether to retry. |
| Provider validation, missing resource, or idempotency conflict | `validation_failed`, `resource_not_found`, or `idempotency_conflict` | Do not retain provider messages or identifiers. |
| HTTP 5xx/provider unavailable | `provider_unavailable` | A retry reuses the same `client_token`. |
| `network timeout` | `timeout` | No raw request body or token in the error. |
| Unexpected provider response | `malformed_response` | Failed connector result without raw response payload leakage. |

Recognized Feishu provider codes take precedence over generic HTTP status classification. If no recognized code is available, the connector falls back to the HTTP status category.

Normalized `provider_status` values are exactly: `live_disabled`, `validation_failed`, `credential_failed`, `authorization_failed`, `permission_denied`, `rate_limited`, `resource_not_found`, `idempotency_conflict`, `provider_unavailable`, `timeout`, `malformed_response`, and `completed`.

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

The live connector must not copy raw task values into connector-produced state. It also must not copy raw provider messages, the provider task guid, the resolved token, the idempotency digest, request bodies, or response bodies into connector output, audit, events, snapshots, or summaries. A successful call exposes the task guid only as `lark_task_id_present: true`.

This connector boundary does not rewrite the existing durable-input contract. Values explicitly supplied by a user remain unchanged in durable `run.context.input`; those values may include the task input used by mapping. Connector redaction applies to connector-produced and promoted state, while credential values remain prohibited from all persistent state.

## Local Test Strategy

Loop 39 tests live-mode behavior with a fake Lark HTTP receiver implemented as an injected fake transport. There is no live network in CI.

Required tests before any live API implementation can merge:

- dry-run remains the default when `mode` is missing
- mode `dry_run` remains the default
- `mode: live` requires `lark_bot_access_token`
- live mode sends only the approved `create_task` request shape
- the fake receiver can simulate success, `401 or 403`, rate limit, network timeout, validation error, and malformed response cases
- raw task values and resolved credentials do not appear in result summaries, run state, audit logs, or snapshot artifacts
- retries for the same `workflow_id + version + run_id + node_id` reuse the stable native `client_token` and unchanged parameters so Feishu performs provider-side deduplication; the connector does not locally block retry transport calls

The existing dry-run tests and smoke commands continue to pass unchanged. After CI-safe fake-transport tests pass, an operator may run the separately guarded validation helper outside CI:

```bash
vibe vault run --env LARK_BOT_ACCESS_TOKEN -- env SKILL2WORKFLOW_LARK_TASK_LIVE=1 python3 scripts/lark_task_live_validation.py \
  --confirm-live-create \
  --validation-run-id '<stable-run-id>' \
  --assignee-open-id '<open_id>' \
  --title '<task-title>' \
  --description '<task-description>'
```

Use Avibe Vault as shown, or an equivalent secret manager that injects `LARK_BOT_ACCESS_TOKEN` only into the child process. Never paste the token into the command or shell history. The helper is inert without the confirmation flag, the exact environment switch, a token injected through the environment, a stable validation run id, and an assignee open id. It prints compact presence/status metadata only and writes no run state.

## Rollback Boundaries

Loop 39 keeps live behavior behind a feature flag: the exact environment switch. The default remains dry-run.

Rollback requirements:

- A maintainer can disable live mode without removing the dry-run connector package by removing `SKILL2WORKFLOW_LARK_TASK_LIVE=1` (or setting any value other than the exact string `1`).
- Reverting Loop 39 must not require changing Workflow DSL compatibility.
- A maintainer must be able to revert Loop 39 without changing Workflow DSL compatibility.
- Reverting Loop 39 must not invalidate existing dry-run smokes, pilot artifacts, or connector package documentation.
- Live-mode failures must not prevent the dry-run connector from being loaded explicitly.

Loop 39 should be considered complete only when the implementation proves these rollback boundaries with tests and documentation.
