# Remote recurring-schedule creation

Loop 154 adds one protected operator write path for creating a durable
recurring schedule without opening the service host shell. It complements the
remote inventory and enable/disable actions while keeping SQLite scheduling
semantics unchanged.

## Contract

The endpoint requires the service Bearer token, readiness, the active scheduler
lease, and an exact wrapper body:

```text
POST /api/v1/recurring-schedules
```

```json
{
  "schedule": {
    "schema_version": "skill2workflow-schedule-0.2.0",
    "schedule": {
      "id": "schedule_hourly_report",
      "workflow_id": "workflow_hourly_report",
      "version": "0.1.0",
      "starts_at": "2026-08-11T00:00:00Z",
      "interval_seconds": 3600,
      "missed_run_policy": "latest",
      "enabled": true
    },
    "trigger": {
      "idempotency_key_prefix": "schedule_hourly_report",
      "input": {"report": "hourly"}
    }
  }
}
```

The response is the fixed redacted
[`recurring-schedule-create-0.1.0`](../schemas/recurring-schedule-create-0.1.0.schema.json)
contract. It returns scheduling metadata and a `created` flag, but never
returns trigger input, the source, or the idempotency-key prefix:

```json
{
  "schema_version": "skill2workflow-recurring-schedule-create-0.1.0",
  "schedule_id": "schedule_hourly_report",
  "workflow_id": "workflow_hourly_report",
  "workflow_version": "0.1.0",
  "status": "active",
  "enabled": true,
  "starts_at": "2026-08-11T00:00:00+00:00",
  "next_run_at": "2026-08-11T00:00:00+00:00",
  "interval_seconds": 3600,
  "missed_run_policy": "latest",
  "created": true
}
```

The request is bounded by the shared 1 MiB body/input limits and the response
is capped at 16 KiB. Invalid JSON or a wrong wrapper returns `400`; a changed definition
for an existing `schedule_id` returns fixed `409`; authentication,
readiness, or storage failures do not disclose scheduler state.

Creation is retry-safe. An identical definition returns `200` with
`created: false`. A changed retry never resets `next_run_at` or other durable
dispatch progress. The store uses `BEGIN IMMEDIATE`, serializing creation with
dispatcher claims. The control-plane audit records bounded authentication and
creation/replay events; trigger values remain in the scheduler database only.

If the scheduler transaction commits but the separate control-audit append
fails, the request can return `503`. Retrying the identical definition repairs
the missing operator evidence without creating a second schedule or resetting
progress.

## CLI

```bash
PYTHONPATH=src python3 -m skill2workflow.cli service-recurring-schedule-add \
  /path/to/recurring-schedule.json \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /path/to/ingress.token
```

The installed client validates the origin, owner-only token file, redirect
policy, request/response bounds, and the complete fixed response schema before
printing it.

## Boundary

This loop creates recurring SQLite schedules only. It does not update or
delete an existing definition, create one-shot JSON schedules, publish a
workflow, or claim exactly-once delivery. Use the existing enable/disable
action to pause or resume a created schedule and the dispatch diagnostics to
inspect uncertain outcomes.

Focused verification:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules \
  tests.test_service_client \
  tests.test_service \
  tests.test_cli \
  tests.test_telemetry -v
```
