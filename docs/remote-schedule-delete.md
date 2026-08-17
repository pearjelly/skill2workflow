# Remote recurring-schedule deletion

Loop 156 adds a protected way to retire one recurring schedule through the
authenticated service boundary. Retirement is deliberately narrower than a
database purge: the schedule definition and compact inventory row are removed,
historical dispatch records remain available for diagnosis, and a tombstone
makes retries safe.

## Contract

The endpoint requires service readiness, the active scheduler lease, a Bearer
token, and an exact confirmation body:

```text
DELETE /api/v1/recurring-schedules/{schedule_id}
```

```json
{
  "expected_next_run_at": "2026-08-11T01:00:00+00:00",
  "confirm": true
}
```

`expected_next_run_at` is the last value observed by the operator. The store
compares it inside the same `BEGIN IMMEDIATE` transaction used by dispatcher
claims. The schedule must already be disabled and there must be no active claim
(`claimed` dispatch) for it. Stale, active, or enabled schedules return fixed `409`
responses; unknown IDs return fixed `404` responses.

The successful response is the fixed redacted
[`recurring-schedule-delete-0.1.0`](../schemas/recurring-schedule-delete-0.1.0.schema.json)
contract:

```json
{
  "schema_version": "skill2workflow-recurring-schedule-delete-0.1.0",
  "schedule_id": "schedule_hourly_report",
  "deleted": true
}
```

An identical retry after the definition has been retired returns `200` with
`deleted: false`. The tombstone prevents the schedule ID from being reused, so
a delayed retry can never remove a different schedule. Dispatch history is
not deleted, and no trigger input, workflow content, credential, or provider
response is returned.

If the scheduler transaction succeeds but the separate control-plane audit
append fails, the request may return `503`. Retrying the same request observes
the tombstone, appends the missing value-free evidence, and returns the fixed
no-op response.

## CLI

```bash
skill2workflow service-recurring-schedule-delete \
  schedule_hourly_report \
  --expected-next-run-at 2026-08-11T01:00:00+00:00 \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The installed client validates the HTTPS-or-loopback origin, owner-only token
file, redirect policy, request/response bounds, safe schedule identifier, and
the complete fixed response schema before printing it.

## Boundary and verification

This is a single-tenant schedule retirement boundary. It does not delete
dispatch evidence, cancel an in-flight provider call, reclaim tombstones,
delete one-shot schedules, publish workflows, or claim exactly-once provider
effects.

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules \
  tests.test_service_client \
  tests.test_service \
  tests.test_cli \
  tests.test_telemetry -v
```
