# Remote Recurring-Schedule Dispatch Diagnostics

Loop 80 adds a bounded, authenticated read surface for diagnosing durable
recurring-schedule dispatches without shell access to the service host. It is
an operator evidence projection, not a scheduler control plane.

## Routes

The loopback service accepts Bearer-authenticated `GET` requests to:

```text
GET /api/v1/recurring-schedule-dispatches
GET /api/v1/recurring-schedules/{schedule_id}/dispatches
```

The second route uses the same safe identifier grammar as schedule actions:
ASCII letters, digits, `_`, `-`, and `.`, with a maximum of 128 characters.
Requests must have no body. The route is available while the service is
starting or draining because it is read-only; it does not require scheduler
lease ownership.

The installed client exposes the same operation through:

```bash
skill2workflow service-recurring-dispatches \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /path/to/ingress.token

skill2workflow service-recurring-dispatches \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /path/to/ingress.token \
  --schedule-id schedule_hourly_report
```

## Fixed response and redaction

Successful responses use
`skill2workflow-recurring-schedule-dispatch-list-0.1.0`, defined by
[`schemas/recurring-schedule-dispatch-list-0.1.0.schema.json`](../schemas/recurring-schedule-dispatch-list-0.1.0.schema.json).
The projection contains fixed status counts, a chronological bounded window,
and compact dispatch metadata: dispatch ID, schedule ID, scheduled time,
status, coalesced occurrence count, run/trigger IDs, a sanitized error type,
and completion time.

It never returns trigger input, connector payloads, credential handles,
scheduler owner IDs, lease expiry timestamps, or raw persisted records. Error
types are limited to short identifier-like values; other values become an
empty string. The global and targeted reports are limited to 100 records and
64 KiB. The targeted response repeats the requested schedule ID and every
returned record must belong to it.

`uncertain` means the scheduler cannot prove whether the external effect was
observed before ownership was lost. Operators should inspect the linked run or
provider idempotency evidence before deciding whether to retry; this endpoint
does not replay or reconcile that effect.

Unauthenticated requests return a fixed `401`; provider authentication
failures return `503`; body-bearing requests and unavailable state use fixed
errors. Read requests do not append audit rows, but route counters remain
visible in the low-cardinality metrics export.

## Verification

The focused evidence command is:

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_recurring_dispatch_list_is_bounded_and_excludes_lease_or_input_values \
  tests.test_service.RuntimeServiceTests.test_recurring_schedule_dispatch_list_is_authenticated_bounded_and_redacted \
  tests.test_service_client.ServiceClientTests.test_recurring_dispatch_list_uses_authenticated_global_and_targeted_paths \
  tests.test_cli.CliTests.test_service_recurring_dispatches_command_supports_schedule_filter \
  -v
```

This capability does not provide schedule mutation, lease ownership, bulk
retry, automatic reconciliation, RBAC, hosted TLS, or exactly-once provider
execution.
