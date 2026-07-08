# First Product Connector Candidate

Selected candidate: Lark/Feishu Task Connector.

Loop 35 selects the first product-specific connector package candidate without adding implementation code. The decision is intentionally narrow: prove that one enterprise workflow connector can fit the Loop 34 package boundary, stay out-of-core, use handle-based credentials, and produce compact audit evidence before Loop 36 writes the package.

## Decision Summary

| Candidate | Decision | Rationale |
| --- | --- | --- |
| Lark/Feishu task | Selected | Strong enterprise workflow fit, durable task semantics, and a narrow first action surface that can be exercised with a local dry-run smoke. |
| GitHub Issues | Deferred | Easy to dry-run and relevant to open-source contributors, but weaker as the first enterprise work-management signal. |
| Slack message or workflow notification | Deferred | Useful notification surface, but less process-stateful than tasks and still requires workspace token handling for live execution. |

The first product connector should demonstrate workflow control, not only outbound messaging. A task connector fits the product thesis because the workflow can create or route a durable work item after a controlled decision point.

## Minimum First Action Surface

The first action surface is intentionally one operation: `create_task`.

Loop 36 should implement operation: `create_task` in a dry-run package first. There must be no live Lark API call in Loop 36. A live API path can be considered only after the dry-run package proves the contract, credential boundary, and audit behavior.

Initial task fields:

| Field | Requirement | Notes |
| --- | --- | --- |
| `title` | Required | Mapped from trigger input or supplied in connector binding. |
| `description` | Optional | Should be summarized in connector output only as presence/length metadata. |
| `assignee_open_id` | Optional | Treated as a routing identifier, not a credential. |
| `due_at` | Optional | ISO-like string accepted by the dry-run fixture. |
| `source_run_id` | Optional | May be copied from workflow/run context when available. |

Non-goals for the first action surface:

- Updating existing tasks.
- Reading task status.
- Syncing task comments.
- OAuth, token refresh, or tenant installation.
- Hosted callbacks or event subscriptions.
- Automatic connector discovery or marketplace registration.

## Package Layout

Loop 36 should use the Loop 34 explicit-loading package convention:

```text
examples/connectors/
  lark_task_connector.py
scripts/
  lark_task_connector_smoke.py
```

Expected loading shape:

```python
from pathlib import Path

from skill2workflow.connectors import ConnectorRuntime
from skill2workflow.external_connectors import load_external_connector

external_connector = load_external_connector(Path("examples/connectors/lark_task_connector.py"))
runtime = ConnectorRuntime([external_connector])
```

The connector module must expose:

```python
MANIFEST = {...}

def execute(binding, credential_provider=None, context=None):
    ...
```

The exact callable signature is `execute(binding, credential_provider=None, context=None)`.

## Manifest And Executor Scope

The Loop 36 manifest should be package-local and explicit:

| Manifest field | Planned value |
| --- | --- |
| `id` | `lark_task` |
| `kind` | `lark_task` |
| `status` | `active` |
| `node_types` | `["tool_call"]` |
| `execution_contract.mode` | `external` |
| `execution_contract.entrypoint` | `examples/connectors/lark_task_connector.py:execute` |
| `credential_contract.supports_handles` | `True` |
| `credential_contract.targets` | `["header"]` |
| `audit_contract.value_policy` | `compact_no_payload_values` |

The executor should accept a connector binding shaped like this:

```json
{
  "id": "lark_task",
  "kind": "lark_task",
  "operation": "create_task",
  "mode": "dry_run",
  "request": {
    "body": {
      "source": "skill2workflow"
    },
    "input_mapping": [
      {"from": "/input/title", "to": "/body/title", "required": true},
      {"from": "/input/description", "to": "/body/description", "required": false},
      {"from": "/input/assignee_open_id", "to": "/body/assignee_open_id", "required": false},
      {"from": "/input/due_at", "to": "/body/due_at", "required": false}
    ]
  },
  "credentials": [
    {
      "target": "header",
      "name": "Authorization",
      "handle": "lark_bot_access_token",
      "prefix": "Bearer "
    }
  ]
}
```

The dry-run executor should validate the operation, resolve configured handles, apply input mapping, and return only compact task metadata. It should not call Lark APIs, create real tasks, or return raw task field values.

## Credential Handles And Secret Boundaries

The planned credential handle is `lark_bot_access_token`.

Credential rules:

- Workflow DSL may reference the handle name, but not the token value.
- The smoke may create a temporary local credential provider under the work directory.
- The executor may resolve the handle to prove the credential path works.
- Resolved credential values must never be returned from `execute(...)`.
- In other words, resolved credential values must never be returned.
- Resolved credential values must never appear in connector result summaries, audit events, committed fixtures, or docs examples.
- Missing credentials should fail before any live network path exists.

Because Loop 36 is dry-run only, the credential exists to prove the boundary, not to authenticate against Lark.

## Local Or Dry-Run Smoke

Loop 36 should add one smoke command:

```bash
python3 scripts/lark_task_connector_smoke.py --work-dir /tmp/skill2workflow-lark-task-connector
```

The smoke should:

- Load `examples/connectors/lark_task_connector.py` with `load_external_connector(...)`.
- Confirm `ConnectorRuntime().list_connectors()` still returns only the built-in registry by default.
- Register the external connector explicitly with `ConnectorRuntime([external_connector])`.
- Publish a generated local workflow using the `lark_task` binding.
- Trigger the workflow with non-secret input such as `title`, `description`, `assignee_open_id`, and `due_at`.
- Use a temporary local credential provider for `lark_bot_access_token`.
- Write workflow, run, audit, connector, trigger, and control-plane snapshot artifacts under the work directory.
- Assert that connector result summaries and audit metadata do not include the resolved credential value or raw task payload values.

Trigger input values may still exist in durable run context because the trigger subsystem intentionally persists input. The connector package must not duplicate raw mapped values into connector output or audit metadata.

## Compact Audit Metadata

Connector output and promoted audit metadata should prove execution without exposing payloads or secrets.

Expected compact metadata:

| Field | Meaning |
| --- | --- |
| `connector_id` | `lark_task` |
| `connector_status` | `completed` or `failed` |
| `operation` | `create_task` |
| `mode` | `dry_run` |
| `task_title_present` | Boolean, not the title value |
| `task_description_present` | Boolean, not the description value |
| `assignee_present` | Boolean, not the assignee value |
| `due_at_present` | Boolean, not the due date value |
| `input_mapping_keys` | Input key names only |
| `credential_status` | `resolved`, `missing`, or `skipped` |
| `credential_handles` | Handle names such as `lark_bot_access_token` |

The package must not return raw `title`, `description`, token values, authorization headers, or live API response payloads.

## Conditions Before Loop 36

Loop 36 may implement the package only if these conditions stay true:

- No automatic discovery.
- No package installer.
- No marketplace indexing.
- No OAuth.
- No token refresh system.
- No hosted callback.
- No production queue or scheduler.
- No live Lark API call in the first package smoke.
- The connector remains out-of-core and explicitly loaded.
- The smoke can run from a fresh checkout with generated local artifacts.
- Credential handles remain visible while resolved values stay hidden.

If any of those conditions cannot hold, the candidate should be re-opened before implementation.
