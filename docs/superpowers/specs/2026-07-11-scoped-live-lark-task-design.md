# Scoped Live Lark Task Connector Design

**Date:** 2026-07-11

**Status:** Approved for implementation planning

## Purpose

Complete Loop 39 by adding one explicitly enabled live action to the out-of-core `lark_task` connector: create one Feishu task through Task API v2.

The live path must preserve the existing dry-run default, Workflow DSL compatibility, credential-handle boundary, durable trigger-input contract, compact audit contract, and explicit connector-loading model. It must also support one manually confirmed live validation after local fake-transport evidence passes.

## Decision Summary

- Product endpoint: Feishu domestic service only.
- Connector id and kind: `lark_task`.
- Operation: `create_task`.
- Live activation: `mode: live` plus `SKILL2WORKFLOW_LARK_TASK_LIVE=1`.
- Default mode: `dry_run`.
- Credential handle: `lark_bot_access_token`.
- HTTP implementation: Python standard library.
- Test transport: injectable callable; no live network in CI.
- Idempotency: native Feishu `client_token`, derived from execution identity.
- Real validation: one explicitly confirmed task assigned to the consenting current user.
- Runtime scope: single action, single fixed domain, no OAuth or token refresh.

## Verified Provider Contract

The implementation targets the documented Feishu Task API v2 create endpoint:

```text
POST https://open.feishu.cn/open-apis/task/v2/tasks?user_id_type=open_id
```

Official documentation:

- Create task: `https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/task-v2/task/create`
- Task v2 overview and idempotency: `https://open.feishu.cn/document/task-v2/overview?lang=zh-CN`

Relevant provider facts:

- `summary` is required.
- `description` is optional.
- `members` can contain an assignee identified by `open_id`.
- `due.timestamp` is an epoch-millisecond string.
- `client_token` activates provider-native idempotency.
- Repeated calls using the same `client_token` must keep request parameters unchanged.
- The documented endpoint limit is 10 requests per second.
- Either `task:task:write` or `task:task:writeonly` is sufficient for create access.
- Both bot and user access tokens are supported; Loop 39 uses the existing bot-token handle.

Loop 39 does not target `open.larksuite.com`, accept a custom base URL, or support Task API v1.

## Architecture

### 1. Ephemeral Execution Identity

`LocalExecutor` already stores these fields outside `state.context`:

- `workflow_id`
- `workflow_version`
- `run_id`
- current node id

Before each connector invocation, the executor will create a deep copy of the durable run context and overwrite a reserved `_execution` object:

```json
{
  "_execution": {
    "workflow_id": "workflow_example",
    "workflow_version": "0.1.0",
    "run_id": "run_example",
    "node_id": "create_lark_task"
  }
}
```

This enriched object is passed only to `ConnectorRuntime.execute_connector(...)`. It is not written back to `state.context`, run state, audit, snapshots, or workflow artifacts. User-provided `_execution` data is never trusted; runtime-owned values replace it.

The existing `input` and `trigger` context objects remain unchanged.

### 2. External Connector Boundary

The implementation remains in `examples/connectors/lark_task_connector.py`. The connector stays out of the built-in registry and must still be loaded explicitly with `load_external_connector(...)`.

The public entrypoint remains backward compatible:

```python
execute(binding, credential_provider=None, context=None, transport=None)
```

The optional `transport` parameter exists only to inject deterministic fake HTTP behavior in tests and the validation helper. Normal runtime calls omit it and use the standard-library sender.

No live behavior is added to the built-in HTTP connector.

### 3. Dual Live Activation

Live network activity requires both:

1. connector binding `mode` equals `live`; and
2. environment variable `SKILL2WORKFLOW_LARK_TASK_LIVE` equals the exact string `1`.

If `mode` is missing, the connector continues in `dry_run`. If `mode` is `live` but the environment switch is absent or has any other value, the connector returns a compact failed result with `provider_status: live_disabled` before credential resolution or transport invocation.

No other truthy spellings are accepted. This makes rollback a one-variable operation and prevents accidental activation.

### 4. Fixed Network Boundary

The live connector constructs the method, URL, query string, and headers internally:

- method: `POST`
- scheme and host: `https://open.feishu.cn`
- path: `/open-apis/task/v2/tasks`
- query: `user_id_type=open_id`
- headers: `Authorization: Bearer <resolved token>` and `Content-Type: application/json; charset=utf-8`

Workflow DSL and connector bindings cannot override the endpoint, method, query, authorization header, content type, or arbitrary extra headers.

This prevents the live connector from becoming a general outbound HTTP or SSRF surface.

## Request Transformation

The connector continues to map the existing local business fields:

| Local field | Feishu request field | Rule |
| --- | --- | --- |
| `title` | `summary` | Required, non-empty string |
| `description` | `description` | Optional string |
| `assignee_open_id` | `members[0]` | Optional member `{id, type: "user", role: "assignee"}` |
| `due_at` | `due` | Optional timezone-aware RFC 3339 value converted to epoch milliseconds |

`due_at` accepts `Z` or an explicit UTC offset. Naive timestamps are rejected before network activity. The request uses `is_all_day: false`; all-day date support is outside Loop 39.

Unknown local body keys are ignored by the provider request builder. Raw `source` or other dry-run fixture metadata is not forwarded.

## Idempotency

Live mode requires all four runtime-owned execution fields:

- workflow id
- workflow version
- run id
- node id

The connector serializes those four strings as a canonical JSON array and derives a deterministic UUID v5. The canonical UUID becomes Feishu `client_token`.

Properties:

- stable across retry attempts within one run and node;
- different for different workflow versions, runs, or nodes;
- safe to record only as `idempotency_key_present: true`, not as the digest itself;
- compatible with provider-native retry behavior after timeout or server error.

Live mode fails before transport invocation if execution identity is absent or incomplete.

Because Feishu supports native `client_token`, Loop 39 does not add a local idempotency database. Fake-transport tests prove stable token derivation and unchanged request parameters across retries. The one real validation call uses a stable validation run id; an accidental repeat with identical parameters therefore uses the same provider token instead of creating a new task.

## Credential Handling

The connector resolves `lark_bot_access_token` only at live execution time. The resolved value is held in a local variable long enough to construct the in-memory Authorization header.

The resolved token must never appear in:

- Workflow DSL
- connector binding copies returned to callers
- trigger input
- persisted run state
- node results
- events or audit
- snapshots
- smoke or validation artifacts
- exception text

The result retains only the existing credential summary:

```json
{
  "status": "resolved",
  "handles": ["lark_bot_access_token"]
}
```

The manual validation helper obtains the token from `LARK_BOT_ACCESS_TOKEN`, injected through Avibe Vault, and immediately wraps it in the existing `StaticCredentialProvider`. The command never accepts the token as a CLI argument and never prints it.

## Transport Contract

The default transport uses `urllib.request` with a fixed 10-second timeout. The transport contract is:

```python
transport(request: urllib.request.Request, timeout: float) -> response
```

The response exposes an HTTP status and a `read() -> bytes` method. Fake transports capture the `Request` for assertions and return deterministic response objects or raise deterministic exceptions.

Tests must not use live network access. They inject deterministic responses or exceptions for every required path.

The transport layer may read a provider response into memory for parsing, but raw response bytes and provider messages are never returned, logged, persisted, or embedded in an exception.

## Response Normalization

A successful provider response must satisfy all of these conditions:

- HTTP status is successful;
- JSON decodes to an object;
- top-level `code` equals `0`;
- `data.task.guid` is a non-empty string.

The raw guid is not returned. The compact result contains only:

```json
{
  "operation": "create_task",
  "mode": "live",
  "task_title_present": true,
  "task_description_present": true,
  "assignee_present": true,
  "due_at_present": false,
  "credential_status": "resolved",
  "idempotency_key_present": true,
  "provider_status": "completed",
  "lark_task_id_present": true
}
```

The `output` and `audit` objects can share compact metadata. Neither contains raw task values, the idempotency digest, or the provider task guid.

## Failure Normalization

Expected failures become connector failed results with fixed, provider-independent error text and compact `provider_status` values:

| Failure | `provider_status` | Required behavior |
| --- | --- | --- |
| Live environment switch absent | `live_disabled` | Fail before credential or transport access |
| Missing/invalid local input or execution identity | `validation_failed` | Fail before transport access |
| Missing credential | `credential_failed` | Existing compact credential error path; no token |
| HTTP 401 or code `99991663` | `authorization_failed` | Fixed error text |
| HTTP 403 or code `1470403` | `permission_denied` | Fixed error text |
| HTTP 429 | `rate_limited` | Failed result compatible with existing retry policy |
| code `1470400` | `validation_failed` | Do not retain provider message |
| code `1470404` | `resource_not_found` | Do not retain provider identifiers |
| code `1470422` | `idempotency_conflict` | Safe failure; no concurrent call behavior added |
| HTTP 5xx or code `1470500` | `provider_unavailable` | Retry reuses the same `client_token` |
| Timeout | `timeout` | No request body or token in error |
| Non-JSON or structurally invalid response | `malformed_response` | No raw response leakage |

When an HTTP error carries a valid Feishu JSON error object, provider `code` classification takes precedence over the generic HTTP status. Otherwise the connector falls back to the HTTP status class; for example, an unparseable HTTP 400 response becomes `validation_failed` and an unparseable HTTP 500 response becomes `provider_unavailable`.

The current executor retry policy remains unchanged. Loop 39 does not add backoff, retry classification, queues, or worker coordination.

## Redaction And Durable Input Clarification

Loop 24 intentionally persists the normalized trigger input under `run.context.input`. Loop 39 preserves that contract.

The live connector redaction rule therefore means:

- the connector must not copy raw task values into `node_results`, connector `output`, connector `audit`, runtime events, control-plane audit, snapshots, or connector summaries;
- values explicitly supplied as durable trigger input remain in `run.context.input` under the existing contract;
- credential values are never trigger input and remain prohibited everywhere persistent.

Tests scan every connector-produced and promoted surface for token, title, description, assignee, due value, raw request JSON, and raw response content. A separate assertion confirms that the runtime-owned `_execution` object is not persisted.

Adding sensitive-input declarations, encryption, field-level retention, or trigger redaction would require a separate approved loop.

## Manual Live Validation

Loop 39 adds:

- `src/skill2workflow/lark_task_live_validation.py`
- `scripts/lark_task_live_validation.py`

The command is inert unless all of these are present:

- `--confirm-live-create`
- `--validation-run-id <stable value>`
- `--assignee-open-id <open_id>`
- `SKILL2WORKFLOW_LARK_TASK_LIVE=1`
- `LARK_BOT_ACCESS_TOKEN` injected in the environment

The task title and description are supplied at runtime. The validation performed for this loop uses the exact task content and current-user assignment already approved in the conversation, but those raw values and the user's open id are not committed to repository artifacts.

The helper directly exercises the explicitly loaded connector through `ConnectorRuntime`. It does not write run state. It prints only compact status and presence metadata.

After fake-transport tests and the full verification suite pass, the agent will request or locate `LARK_BOT_ACCESS_TOKEN` through Avibe Vault and execute the confirmed live write once. If Vault approval is required, the normal protected-secret approval flow applies.

The created task is retained as visible validation evidence. The repository receives only a redacted evidence note containing:

- validation timestamp;
- connector id and operation;
- live opt-in present;
- credential resolved flag;
- idempotency key present flag;
- provider completed status;
- task id present flag;
- assignee present flag.

It does not contain the token, task guid, task title, description, assignee id, raw request, or raw response.

## Testing Strategy

### Connector Tests

Extend `tests/test_lark_task_connector.py` using injected transports for:

- missing mode remains dry-run;
- explicit dry-run remains unchanged;
- live mode without the environment switch invokes no credential provider or transport;
- live mode requires `lark_bot_access_token`;
- exact method, fixed URL, query, headers, and provider request shape;
- title, description, assignee, and due transformations;
- unknown body fields are not forwarded;
- stable `client_token` for the same execution identity;
- different client tokens for different run or node identities;
- HTTP 401, 403, 429, and 5xx;
- provider codes `1470400`, `1470403`, `1470404`, `1470422`, and `1470500`;
- timeout;
- non-JSON, missing code, nonzero code, missing task, and missing guid responses;
- success metadata;
- recursive leakage scans over result data.

### Executor Tests

Extend `tests/test_executor.py` to prove:

- the connector receives the runtime-owned `_execution` object;
- a user-provided `_execution` object is overwritten;
- persisted `state.context` does not acquire `_execution`;
- trigger input remains durable and unchanged.

### Validation Helper Tests

Create `tests/test_lark_task_live_validation.py` for:

- missing confirmation flag;
- missing environment switch;
- missing token environment variable;
- missing validation run id or assignee;
- fake successful live validation;
- compact output only;
- no state-directory writes;
- token and task-value leakage scan.

### Regression Verification

Required verification includes:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_task_connector tests.test_executor tests.test_lark_task_live_validation -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py examples/connectors/lark_task_connector.py
python3 scripts/secret_hygiene.py examples/workflows
python3 scripts/lark_task_connector_smoke.py --work-dir /tmp/skill2workflow-lark-task-connector
python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot
git diff --check
```

No CI command performs live network access.

## Documentation And Roadmap Transition

Implementation updates:

- `docs/connectors.md` with the live activation, fixed endpoint, credential, idempotency, error, and redaction contracts;
- `docs/lark-live-connector-readiness.md` with the confirmed native `client_token` decision and durable-input clarification;
- a redacted live-validation evidence note after the successful manual call;
- `ROADMAP.md` after all evidence is complete.

When Loop 39 is complete:

- completed delivery loops become 1-39;
- Loop 39 moves to Delivery History;
- current maturity remains Local Evaluation until the complete controlled-pilot gate is met;
- Loop 40 becomes the next loop: Controlled Live Connector Pilot;
- the one connector-level validation call is not presented as the Loop 40 business-workflow pilot.

`README.md` receives only the matching active-loop summary update.

## Rollback

Immediate rollback is setting or leaving `SKILL2WORKFLOW_LARK_TASK_LIVE` to anything other than `1`.

Code rollback removes the live branch and validation helper while retaining the existing dry-run connector package, examples, smokes, credential handle, manifest, and Workflow DSL `0.1.0` compatibility.

No rollback requires schema migration or state conversion.

## Explicit Non-goals

- Lark international domain
- Custom API base URLs
- OAuth or token refresh
- Tenant token acquisition
- Hosted secret management
- Other Feishu task operations
- Task API v1
- All-day due dates
- General outbound HTTP behavior
- Backoff or retry-policy redesign
- Local idempotency database
- Sensitive trigger-input declarations or persistence redaction
- Connector discovery, installer, or marketplace
- Queue, worker pool, or production scheduler
- Committed live credentials, task ids, user ids, raw request bodies, or raw responses

## Acceptance Criteria

Loop 39 is complete only when:

- dry-run remains the default and all existing dry-run tests and smokes pass unchanged;
- live mode requires both binding intent and the exact environment switch;
- only the fixed Feishu Task API v2 create endpoint can be called;
- the token is resolved by handle and absent from every persistent or returned surface;
- native `client_token` is stable for one execution identity and changes across distinct identities;
- success and all documented failure categories produce compact normalized results;
- raw task and provider values are absent from connector-produced run, audit, snapshot, and summary surfaces;
- `_execution` metadata is ephemeral;
- one confirmed live validation task is created for the consenting user through Vault-injected credentials;
- the committed validation evidence is redacted;
- full tests, compilation, secret hygiene, dry-run smokes, and diff checks pass;
- Loop 39 documentation and Roadmap state are updated without changing Workflow DSL compatibility.
