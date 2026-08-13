# Local Trigger API

This document describes the current local trigger boundary for published workflow runs.

Workflow DSL remains the execution truth source. The trigger API does not execute draft workflows and does not mutate published workflow artifacts. It accepts a small request envelope, delegates to the existing published-run control-plane path, and returns compact trigger/run identity. The `version` may be an exact immutable version or a control-plane alias such as `production`; the response always reports the resolved immutable version.

When the control plane uses SQLite (the self-hosted service production path), a
non-empty `idempotency_key` is durable and enforced before execution. JSON/local
evaluation remains metadata-only so the dependency-light behavior stays
backward-compatible.

## Trigger Request Envelope

A trigger request targets one immutable published workflow version or a stable alias:

```json
{
  "workflow_id": "workflow_approval_flow",
  "version": "0.1.0",
  "source": "local-cli",
  "idempotency_key": "example-001",
  "input": {
    "customer_id": "customer_123"
  }
}
```

Supported fields:

| Field | Required | Behavior |
| --- | --- | --- |
| `workflow_id` | Yes | Published workflow id to run. |
| `version` | Yes | Exact published workflow version or a published control-plane alias to resolve. |
| `source` | No | Local trigger source label. Defaults to `local`; the CLI uses `local-cli`. |
| `idempotency_key` | No | In SQLite, a safe non-empty key is durably enforced per workflow version; JSON/local evaluation records it as metadata only. |
| `input` | No | JSON object accepted as trigger input. Values are persisted in run context; audit and trigger responses expose only keys. |

`input` must be a JSON object when supplied. Trigger input keys are normalized as strings. The canonical UTF-8 JSON representation of the object is capped at **1 MiB (1,048,576 bytes)** before it is copied into durable run state or used to compute a SQLite idempotency fingerprint. CLI, one-shot schedule, and recurring schedule paths share this limit and reject oversized input with a fixed `ValueError`. The webhook parser maps that validation failure to HTTP 400; its earlier transport body bound may reject the larger wire request with HTTP 413. The limit bounds durable context and fingerprint work; it is not a confidentiality or redaction feature.

If the published workflow declares `input_schema`, the same trigger boundary
also validates the normalized object against that optional, bounded contract.
The root is an object and the supported subset is documented in
[`docs/workflow-dsl-contract.md`](workflow-dsl-contract.md). Validation runs
before SQLite idempotency claims, run-state creation, audit emission, and
connector execution. Invalid values receive a fixed error with a JSON path;
the rejected value is not included in the error. Workflows without
`input_schema` keep the historical open-object behavior.

Do not put secrets, credentials, access tokens, private keys, or long confidential documents in trigger input. Connector credentials should use the separate local credential-provider boundary documented in `docs/credential-boundary.md`. The current runtime does not provide secret redaction, encryption, or IAM.

## CLI Usage

Publish a workflow first:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli publish /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-control
```

Write local trigger input metadata:

```bash
printf '{"customer_id":"customer_123"}' >/tmp/skill2workflow-trigger-input.json
```

Trigger the published workflow:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli trigger workflow_approval_flow \
  --version 0.1.0 \
  --state-dir /tmp/skill2workflow-control \
  --source local-cli \
  --idempotency-key example-001 \
  --input /tmp/skill2workflow-trigger-input.json
```

The command prints a compact response:

```json
{
  "trigger_id": "trigger_abc123def456",
  "workflow_id": "workflow_approval_flow",
  "workflow_version": "0.1.0",
  "run_id": "run_abc123def456",
  "run_status": "waiting",
  "source": "local-cli",
  "idempotency_key": "example-001",
  "input_keys": ["customer_id"]
}
```

Use `--storage sqlite` when the control plane is using SQLite-backed metadata and run storage.

For SQLite, retry the same request with the same key to receive the original
compact response without starting another run. Reusing that key with a
different source or input is rejected with a fixed conflict. A request whose
first execution outcome is unresolved remains fail-closed; choose a new key
only after investigating the original run.

## Stable Workflow Version Aliases

The control plane can assign a bounded, human-readable alias to one published
version without changing that version's immutable artifact. Aliases are scoped
to one `workflow_id`; the default CLI alias is `production`, and safe names
start with a lowercase letter and contain only lowercase letters, numbers,
`.`, `_`, or `-` (at most 64 UTF-8 bytes).

Promote a version and then trigger through the alias:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli promote workflow_approval_flow \
  --version 0.2.0 \
  --alias production \
  --state-dir /tmp/skill2workflow-control \
  --storage sqlite

PYTHONPATH=src python3 -m skill2workflow.cli trigger workflow_approval_flow \
  --version production \
  --state-dir /tmp/skill2workflow-control \
  --storage sqlite \
  --idempotency-key production-example-001
```

Promotion moves an alias to the selected published version and records a
`workflow_promoted` audit event. An exact version always wins if its text also
matches an alias. Deprecating a version clears its aliases; an alias never
silently falls back to another version. JSON and SQLite registry metadata both
retain aliases, while the published Workflow DSL artifact remains untouched.

For a reviewed multi-operator release, pass
`--expected-current-version <version>` to `promote`. The alias is moved only if
it still points to that exact published version; otherwise the command returns
`workflow alias precondition failed: <workflow_id>@<alias>` without changing
registry or audit state. See [`workflow-releases.md`](workflow-releases.md) for
the structural diff command and bounded output contract.

Alias resolution happens before input validation and execution. For SQLite
idempotency, the requested alias is the durable scope: retrying the same key
after a later promotion replays the original compact response (and does not
run the new version), while a new key resolves and runs the newly promoted
version. Webhooks and both schedule formats use the same trigger boundary, so
their version field can use an alias as well.

Inspect the run context:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli control-run <run_id> --state-dir /tmp/skill2workflow-control
```

Triggered run details include:

```json
{
  "context": {
    "trigger": {
      "trigger_id": "trigger_abc123def456",
      "source": "local-cli",
      "idempotency_key": "example-001",
      "input_keys": ["customer_id"]
    },
    "input": {
      "customer_id": "customer_123"
    }
  }
}
```

## Local Webhook Adapter

The local webhook adapter exposes the same trigger boundary over a dependency-free local HTTP server. It is intended for local pilot integration testing, not hosted ingress.
It accepts only loopback bind hosts (`127.0.0.1`, `::1`, or `localhost`) and
rejects public-interface bindings.

Start the local server:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli webhook-server \
  --state-dir /tmp/skill2workflow-control \
  --host 127.0.0.1 \
  --port 8080
```

Send a local webhook request:

```bash
curl -sS -X POST http://127.0.0.1:8080/webhooks/workflow_approval_flow/0.1.0 \
  -H 'Content-Type: application/json' \
  -d '{"source":"local-webhook","idempotency_key":"example-001","input":{"customer_id":"customer_123"}}'
```

For deterministic local smoke tests, add `--once` so the server handles one request and exits:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli webhook-server \
  --state-dir /tmp/skill2workflow-control \
  --host 127.0.0.1 \
  --port 8080 \
  --once
```

Webhook route:

| Method | Path | Behavior |
| --- | --- | --- |
| `POST` | `/webhooks/<workflow_id>/<version-or-alias>` | Triggers the exact published workflow version or control-plane alias through `LocalControlPlane.trigger_workflow`. |

Request body:

```json
{
  "source": "local-webhook",
  "idempotency_key": "example-001",
  "input": {
    "customer_id": "customer_123"
  }
}
```

Supported fields:

| Field | Required | Behavior |
| --- | --- | --- |
| `source` | No | Local webhook source label. Defaults to `local-webhook`. |
| `idempotency_key` | No | SQLite service requests enforce the durable replay contract below; local JSON webhook runs record it only. |
| `input` | No | JSON object copied into durable run context. Responses and audit events expose only keys. |

The local adapter accepts at most 1 MiB of request body. It rejects transfer
encoding, duplicate/invalid/negative `Content-Length` values, and oversized
bodies before reading or triggering a workflow. An oversized request receives
HTTP `413`; malformed length metadata receives HTTP `400`.

The response shape matches the CLI trigger response:

```json
{
  "trigger_id": "trigger_abc123def456",
  "workflow_id": "workflow_approval_flow",
  "workflow_version": "0.1.0",
  "run_id": "run_abc123def456",
  "run_status": "waiting",
  "source": "local-webhook",
  "idempotency_key": "example-001",
  "input_keys": ["customer_id"]
}
```

The adapter rejects unsupported methods, malformed webhook paths, invalid JSON bodies, non-object bodies, and non-object `input` fields with JSON error responses. It does not persist raw HTTP headers or raw request bodies by default.

## Local Scheduled Triggers

Local schedules are deterministic one-shot trigger definitions stored under the control-plane state directory. They are intended for local evaluation of recurring workflow shapes, not for production scheduling.

A schedule document targets one immutable published workflow version and stores a compact trigger template:

```json
{
  "schema_version": "skill2workflow-schedule-0.1.0",
  "schedule": {
    "id": "schedule_approval_flow_daily",
    "workflow_id": "workflow_approval_flow",
    "version": "0.1.0",
    "run_at": "2026-07-06T00:00:00Z"
  },
  "trigger": {
    "input": {
      "customer_id": "customer_123",
      "report_date": "2026-07-06"
    }
  }
}
```

Supported schedule fields:

| Field | Required | Behavior |
| --- | --- | --- |
| `schema_version` | No | Defaults to `skill2workflow-schedule-0.1.0` when omitted. |
| `schedule.id` | Yes | Local schedule id. It is used in the schedule file name and trigger source. |
| `schedule.workflow_id` | Yes | Published workflow id to trigger. |
| `schedule.version` | Yes | Exact published workflow version or a published control-plane alias to trigger. |
| `schedule.run_at` | Yes | ISO-8601 timestamp used by deterministic due checks. |
| `schedule.enabled` | No | Boolean flag. Defaults to `true`. |
| `trigger.source` | No | Optional source suffix. The runtime prefixes it with `local-schedule:<schedule.id>`. |
| `trigger.idempotency_key` | No | Defaults to `<schedule.id>:<normalized run_at>`. It is recorded only. |
| `trigger.input` | No | JSON object copied into durable run context. Responses and audit events expose only keys. |

Add a schedule:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli schedule-add /tmp/skill2workflow-schedule.json \
  --state-dir /tmp/skill2workflow-control
```

List schedules:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli schedules --state-dir /tmp/skill2workflow-control
```

Run due schedules with an explicit timestamp:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli schedule-run-due \
  --state-dir /tmp/skill2workflow-control \
  --now 2026-07-06T00:00:00Z
```

`schedule-run-due` does not sleep, poll, or manage cron. It selects enabled schedules whose `run_at` is less than or equal to `--now`, triggers each due workflow through `LocalControlPlane.trigger_workflow`, and marks each successful one-shot schedule as `completed`.

The scheduled trigger response uses the same compact trigger response shape plus `schedule_id`. The `run_started` audit event records the schedule identity through `trigger_source`, for example `local-schedule:schedule_approval_flow_daily`.

Run the deterministic smoke:

```bash
python3 scripts/schedule_smoke.py --work-dir /tmp/skill2workflow-schedule-loop29
```

The smoke publishes the approval example, writes a local schedule, runs due schedules with a fixed timestamp, resumes the manual gate, and exports a control-plane snapshot under `/tmp/skill2workflow-schedule-loop29/artifacts/`.

## Durable Recurring Scheduled Triggers

The self-hosted SQLite service also supports persistent interval schedules using `schema_version: "skill2workflow-schedule-0.2.0"`. Unlike the legacy one-shot format above, recurring definitions survive service restarts, retain a durable dispatch ledger, require an explicit `latest` or `skip` missed-run policy, and share a global SQLite dispatcher lease.

The service performs claim-before-execute and marks an expired in-flight claim `uncertain` instead of retrying an effect whose outcome is unknown. This is duplicate suppression, not exactly-once execution. Full contract, CLI examples, recovery guidance, and real-process evidence are in [`docs/recurring-scheduling.md`](recurring-scheduling.md).

## Durable Trigger Idempotency

The authenticated SQLite service and any `LocalControlPlane(storage="sqlite")`
trigger share one durable ledger in `control.sqlite3`. The ledger stores only
the workflow/requested-version scope, the safe key, a SHA-256 request fingerprint, a
small lifecycle status, timestamps, and the compact trigger response. It never
stores trigger input values, credentials, headers, or provider payloads.

Keys are at most 128 UTF-8 bytes and use only letters, numbers, `_`, `.`, `:`,
`+`, or `-`. The fingerprint covers workflow id, requested version (exact
version or alias), source, key, and the canonical JSON input; the generated `trigger_id` is intentionally excluded so
a client can retry after rebuilding its request envelope.

The fixed behavior is:

- The first request atomically claims the key before workflow execution.
- A completed identical request returns the stored response and creates no
  second run or duplicate run-lifecycle audit event. The authenticated
  service still records its normal ingress-authentication event for each
  accepted HTTP request.
- A different request using the same key returns HTTP/CLI conflict and does
  not execute.
- A concurrent, interrupted, or otherwise unresolved claim returns a fixed
  conflict. The runtime never guesses whether an external effect occurred and
  never automatically replays that key.

The service maps idempotency conflicts to HTTP `409` with one of the fixed
messages `idempotency key conflicts with an existing request` or `idempotency
key has an unresolved outcome; use a new key`. The ledger is inside the
verified SQLite backup boundary, so replay safety survives a stopped-service
backup and restore.

## Run Context Semantics

Triggered runs use the same published-run execution path as `run-published`, plus an initial run context.

The durable run context has two top-level fields:

| Field | Behavior |
| --- | --- |
| `context.trigger` | Compact trigger metadata: trigger id, source, idempotency key, and input keys. |
| `context.input` | A copied JSON object containing trigger input values. |

The context is stored with the run state in both JSON and SQLite storage modes. It does not mutate the published workflow artifact and does not change Workflow DSL `0.1.0`.

Node execution code can inspect `state["context"]` while running. Trigger input is not used for connector credential resolution. The current runtime supports a constrained HTTP connector body mapping from `/input/...` to `/body/...` through `connector.request.input_mapping`; see `docs/connectors.md`.

## Audit Semantics

The `run_started` audit event includes trigger metadata:

```json
{
  "type": "run_started",
  "run_id": "run_abc123def456",
  "workflow_id": "workflow_approval_flow",
  "workflow_version": "0.1.0",
  "trigger_id": "trigger_abc123def456",
  "trigger_source": "local-cli",
  "idempotency_key": "example-001",
  "input_keys": ["customer_id"]
}
```

The terminal audit event remains `run_completed`, `run_waiting`, or `run_failed`, depending on workflow execution.

Audit events intentionally do not include full `context.input` values by default. Use run detail commands for local debugging when input values are needed.

## Current Limits

The trigger API intentionally does not provide:

- hosted webhooks or public ingress
- public hosted ingress or a managed service supervisor
- cron/calendar expressions, queues, or distributed scheduling
- authentication, RBAC, or IAM
- secret injection
- automatic alias promotion, rollback, or health-based version selection
- automatic idempotency enforcement for JSON/local evaluation (SQLite service enforcement is documented above)
- automatic retry of uncertain recurring effects across process restarts
- arbitrary input templating or connector request interpolation
- header, URL, query string, credential, environment, or file mapping
- schema-based input mapping beyond the explicit body-only contract
- product-specific SaaS callbacks

Future hosted scheduler and integration adapters should call this trigger boundary instead of bypassing the control plane.
