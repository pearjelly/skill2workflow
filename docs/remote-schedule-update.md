# Remote recurring-schedule updates

Loop 155 adds a protected way to change one durable recurring schedule without
opening the service host shell or resetting dispatch progress. The operation is
designed to preserve durable dispatch progress and complements remote creation
and enable/disable actions.

## Contract

The endpoint requires the service Bearer token, readiness, and one exact
compare-and-swap body:

```text
PUT /api/v1/recurring-schedules/{schedule_id}
```

```json
{
  "schedule": {
    "schema_version": "skill2workflow-schedule-0.2.0",
    "schedule": {
      "id": "schedule_hourly_report",
      "workflow_id": "workflow_hourly_report",
      "version": "1.1.0",
      "starts_at": "2026-08-11T00:00:00Z",
      "interval_seconds": 3600,
      "missed_run_policy": "latest",
      "enabled": true
    },
    "trigger": {
      "idempotency_key_prefix": "schedule_hourly_report",
      "input": {"report": "hourly-v2"}
    }
  },
  "expected_next_run_at": "2026-08-11T01:00:00+00:00"
}
```

`expected_next_run_at` must equal the last value observed by the operator. The
SQLite store compares it inside the same `BEGIN IMMEDIATE` transaction used by
dispatcher claims. A stale value returns:

```json
{"error": "recurring schedule update precondition failed"}
```

with HTTP `409`. The update never accepts persisted progress fields from the
request. `next_run_at`, `last_scheduled_for`, `last_run_id`, and
`last_trigger_id` are copied from the durable row, so a successful update
cannot move scheduling backwards or erase dispatch evidence. The request must
include `schedule.enabled` explicitly to avoid accidentally re-enabling a
disabled schedule.

The response is the fixed redacted
[`recurring-schedule-update-0.1.0`](../schemas/recurring-schedule-update-0.1.0.schema.json)
contract. It returns scheduling metadata and `changed`, but never trigger
input, the derived source, or the idempotency-key prefix. Identical retries
return `200` with `changed: false`.

The request is bounded by the shared 1 MiB body/input limit and the response is
capped at 16 KiB. Unknown IDs return a fixed `404`; malformed bodies and
invalid definitions return fixed `400` errors. Authenticated ingress and
value-free definition-update evidence are written to the control-plane audit.

## CLI

```bash
skill2workflow service-recurring-schedule-update \
  schedule_hourly_report /path/to/recurring-schedule-v2.json \
  --expected-next-run-at 2026-08-11T01:00:00+00:00 \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The installed client validates the HTTPS-or-loopback origin, owner-only token
file, redirect policy, request/response bounds, schedule identifier, and the
complete response schema before printing it.

## Boundary and verification

This is a single-tenant recurring-definition update. It does not delete
schedules, change one-shot schedules, publish workflows, expose trigger
values, or claim exactly-once provider delivery. Use the existing inventory to
obtain `next_run_at`, then retry with that value if a concurrent dispatch causes
a `409`.

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules \
  tests.test_service_client \
  tests.test_service \
  tests.test_cli \
  tests.test_telemetry -v
```
