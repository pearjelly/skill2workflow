# Remote Recurring-Schedule Patch

The authenticated `PATCH /api/v1/recurring-schedules/{schedule_id}` endpoint
updates only non-sensitive schedule fields while preserving the stored trigger
input and durable dispatch progress. This is the safe remote alternative when
the inventory endpoint intentionally redacts trigger metadata.

The request body must contain exactly `schedule` and
`expected_next_run_at`:

```json
{
  "schedule": {
    "workflow_id": "workflow_service_v2",
    "version": "2.0.0",
    "interval_seconds": 120,
    "missed_run_policy": "latest",
    "enabled": true
  },
  "expected_next_run_at": "2026-08-11T00:01:00+00:00"
}
```

The safe fields are `workflow_id`, `version`, `starts_at`,
`interval_seconds`, `missed_run_policy`, and `enabled`; `schedule` may contain
only these fields. It must not contain an `id`, `status`, progress fields, or a
`trigger` object. Omitted fields remain unchanged. The path identifier is
authoritative. The server merges the patch inside the same `BEGIN IMMEDIATE`
transaction as the `expected_next_run_at` compare-and-swap check, so a stale
inventory is rejected with `409` and the response
`{ "error": "recurring schedule patch precondition failed" }`.

The response is the fixed redacted contract
`skill2workflow-recurring-schedule-patch-0.1.0`, described by
[`schemas/recurring-schedule-patch-0.1.0.schema.json`](../schemas/recurring-schedule-patch-0.1.0.schema.json).
It never includes trigger input, idempotency prefixes, or audit payloads.

The installed CLI accepts a JSON object containing only the safe patch fields:

```bash
skill2workflow service-recurring-schedule-patch schedule_service_report patch.json \
  --expected-next-run-at 2026-08-11T00:01:00+00:00 \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The operation requires the normal authenticated, ready SQLite service. It
does not change the existing full `PUT` update contract, and it does not claim
exactly-once provider execution.
