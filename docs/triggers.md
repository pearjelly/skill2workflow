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

- hosted webhooks
- a long-running daemon
- queues or distributed scheduling
- authentication, RBAC, or IAM
- secret injection
- idempotency enforcement
- input templating or connector request interpolation
- schema-based input mapping
- product-specific SaaS callbacks

Future webhook, scheduler, and integration adapters should call this trigger boundary instead of bypassing the control plane.
