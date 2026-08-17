# Remote recurring-schedule actions

Loop 79 adds a small, protected operator write surface for the durable
recurring scheduler. It complements the read-only inventory in
[`remote-schedule-inventory.md`](remote-schedule-inventory.md): an operator can
pause a faulty schedule or resume it after remediation without opening the
service host shell.

## Contract

Both endpoints require the service Bearer token. The legacy empty JSON object
(`{}`) body remains supported:

```text
POST /api/v1/recurring-schedules/{schedule_id}/disable
POST /api/v1/recurring-schedules/{schedule_id}/enable
```

For stale-inventory protection, an operator may instead send exactly one
`expected_next_run_at` field:

```json
{"expected_next_run_at": "2026-08-11T01:00:00+00:00"}
```

The value is compared with the persisted schedule inside the same
`BEGIN IMMEDIATE` transaction used by dispatcher claims. A mismatch returns
HTTP `409` with `recurring schedule action precondition failed`; malformed or
null values return `400`. Omitting the field retains the original idempotent
action behavior for compatibility. A successful action still returns the
same fixed response schema and never exposes trigger input.

`schedule_id` is limited to 128 letters, numbers, `_`, `-`, and `.`. The
service must be ready before a mutation is accepted. The response is the
fixed [`recurring-schedule-action-0.1.0`](../schemas/recurring-schedule-action-0.1.0.schema.json)
contract:

```json
{
  "schema_version": "skill2workflow-recurring-schedule-action-0.1.0",
  "schedule_id": "schedule_hourly_report",
  "enabled": false,
  "status": "disabled",
  "changed": true
}
```

The write is idempotent. Repeating the same action returns `200` with
`changed: false`; it does not create another state transition. Unknown IDs
return a fixed `404`, malformed bodies return `400`, and authentication or
service failures do not disclose scheduler state.

The transition uses the recurring store's existing `BEGIN IMMEDIATE` SQLite
transaction, so it serializes with due-dispatch claims. The authenticated
ingress and successful mutation are recorded as bounded control-plane audit
events (`recurring_schedule_action` and `recurring_schedule_updated`). The
control and scheduler databases remain separate; the mutation transaction is
the source of truth for scheduler state, while the control audit records the
operator evidence after that state transaction succeeds.

If the scheduler commit succeeds but the control-audit append fails, the action
can return `503` after the requested enabled state is already durable. Retry the
same enable/disable endpoint after recovery. Because the transition is
idempotent, the retry returns `200` with `changed: false` and completes the
missing operator evidence; it never manufactures a second state transition.

## CLI

```bash
PYTHONPATH=src python3 -m skill2workflow.cli service-recurring-schedules \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /path/to/ingress.token

PYTHONPATH=src python3 -m skill2workflow.cli service-schedule-disable \
  schedule_hourly_report \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /path/to/ingress.token

PYTHONPATH=src python3 -m skill2workflow.cli service-schedule-enable \
  schedule_hourly_report \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /path/to/ingress.token

PYTHONPATH=src python3 -m skill2workflow.cli service-schedule-disable \
  schedule_hourly_report \
  --expected-next-run-at 2026-08-11T01:00:00+00:00 \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /path/to/ingress.token
```

The client validates the HTTPS-or-loopback origin, owner-only token file,
no-redirect policy, response headers, response size, schedule identifier, and
the complete response schema before printing it.

## Observability and compatibility

The complete `/metrics` route matrix includes the low-cardinality
`recurring_schedule_action` route. The fixed support-bundle 0.1.0 contract
continues to omit newer schedule route labels, so existing incident tooling
does not need a schema migration. Schedule action requests never expose
trigger input, workflow DSL, credentials, or raw SQLite content.

Focused verification:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules \
  tests.test_control_plane \
  tests.test_service_client \
  tests.test_service \
  tests.test_cli \
  tests.test_telemetry -v
```
