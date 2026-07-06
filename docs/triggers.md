# Local Trigger API

This document describes the current local trigger boundary for published workflow runs.

Workflow DSL remains the execution truth source. The trigger API does not execute draft workflows and does not mutate published workflow artifacts. It accepts a small request envelope, delegates to the existing published-run control-plane path, and returns compact trigger/run identity.

## Trigger Request Envelope

A trigger request targets one immutable published workflow version:

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
| `version` | Yes | Published workflow version to run. |
| `source` | No | Local trigger source label. Defaults to `local`; the CLI uses `local-cli`. |
| `idempotency_key` | No | Recorded as trigger metadata only. It is not enforced in this loop. |
| `input` | No | JSON object accepted as trigger input. Values are persisted in run context; audit and trigger responses expose only keys. |

`input` must be a JSON object when supplied. Trigger input keys are normalized as strings. The input payload is copied into durable run state and should contain local-pilot business metadata, identifiers, and other non-secret values.

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
| `POST` | `/webhooks/<workflow_id>/<version>` | Triggers the published workflow version through `LocalControlPlane.trigger_workflow`. |

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
| `idempotency_key` | No | Recorded as trigger metadata only. It is not enforced. |
| `input` | No | JSON object copied into durable run context. Responses and audit events expose only keys. |

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
| `schedule.version` | Yes | Published workflow version to trigger. |
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

## Run Context Semantics

Triggered runs use the same published-run execution path as `run-published`, plus an initial run context.

The durable run context has two top-level fields:

| Field | Behavior |
| --- | --- |
| `context.trigger` | Compact trigger metadata: trigger id, source, idempotency key, and input keys. |
| `context.input` | A copied JSON object containing trigger input values. |

The context is stored with the run state in both JSON and SQLite storage modes. It does not mutate the published workflow artifact and does not change Workflow DSL `0.1.0`.

Node execution code can inspect `state["context"]` while running. Trigger input is not used for connector credential resolution. The current runtime does not add input templating, connector request interpolation, or schema-based input mapping.

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

The local trigger API intentionally does not provide:

- hosted webhooks or public ingress
- a supervised production daemon
- cron management, queues, or distributed scheduling
- authentication, RBAC, or IAM
- secret injection
- idempotency enforcement
- recurring retry semantics across process restarts
- input templating or connector request interpolation
- schema-based input mapping
- product-specific SaaS callbacks

Future hosted scheduler and integration adapters should call this trigger boundary instead of bypassing the control plane.
