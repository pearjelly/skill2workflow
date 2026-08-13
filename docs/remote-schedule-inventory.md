# Remote Recurring Schedule Inventory

The self-hosted service exposes the durable recurring schedules needed for
remote operator diagnosis without granting schedule mutation access. This is
a read-only inventory: it never enables, disables, claims, dispatches, or
rewrites a schedule.

## HTTP Contract

```http
GET /api/v1/recurring-schedules
Authorization: Bearer <service-ingress-token>
```

The response follows
[`schemas/recurring-schedule-list-0.1.0.schema.json`](../schemas/recurring-schedule-list-0.1.0.schema.json)
and is versioned as `skill2workflow-recurring-schedule-list-0.1.0`. It contains
at most the latest 100 recurring definitions, fixed active/disabled counts,
workflow references, interval and missed-run policy, next scheduled time, and
compact last-run metadata. The response omits trigger input values, idempotency prefixes, scheduler
owner IDs, credentials, and provider payloads never cross the boundary.

The endpoint is available while the service is starting, draining, or standby
when authenticated SQLite state is readable. It does not acquire or inspect
the scheduler lease and returns `Cache-Control: no-store`. Responses are
bounded to 64 KiB. Missing authentication returns `401`; a non-empty request
body returns `400`; and a storage or response-bound failure returns the fixed
`{"error":"recurring schedule list unavailable"}` response.

## Protected CLI client

```bash
skill2workflow service-recurring-schedules \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The CLI keeps the token out of argv, disables proxies and redirects, validates
the response headers and schema, and prints only the fixed redacted contract.
Use the local `schedule-enable`, `schedule-disable`, and
`schedule-dispatches` commands for deliberate changes on the service host;
this remote inventory intentionally provides no write operation.

## Evidence

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_recurring_schedule_list_is_bounded_and_excludes_trigger_input \
  tests.test_service.RuntimeServiceTests.test_recurring_schedule_list_is_authenticated_redacted_and_available_before_readiness \
  tests.test_service_client.ServiceClientTests.test_recurring_schedule_list_uses_authenticated_get_and_validates_contract \
  tests.test_service_client.ServiceClientTests.test_recurring_schedule_list_rejects_oversized_response \
  tests.test_cli.CliTests.test_service_recurring_schedules_command_prints_redacted_inventory \
  -v
```
