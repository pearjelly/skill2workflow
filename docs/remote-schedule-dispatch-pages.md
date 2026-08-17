# Cursor-Paged Remote Recurring-Schedule Dispatch Diagnostics

Loop 159 adds a versioned, read-only page surface for recurring dispatch
evidence. The original `service-recurring-dispatches` command remains a fixed
recent-tail compatibility view; this page surface lets an operator inspect
older records without loading the complete dispatch history into memory.

## Routes and CLI

```text
GET /api/v1/recurring-schedule-dispatch-pages?max_items=100&cursor=<opaque>
GET /api/v1/recurring-schedules/{schedule_id}/dispatch-pages?max_items=100&cursor=<opaque>
```

The request is Bearer-authenticated, has no body, and is available while the
service is starting or draining. The installed client is:

```bash
skill2workflow service-recurring-dispatch-page \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --schedule-id schedule_hourly_report \
  --max-items 50 \
  --cursor <next_cursor-from-the-previous-page>
```

Omit `--schedule-id` and `--cursor` for the first global page. The cursor is
opaque and must be passed back unchanged; it contains only the last returned
dispatch ordering key and is URL-safe. Pages are returned in chronological
order within each newest-to-oldest page, while `next_cursor` walks toward
older records. Concurrently appended records do not invalidate an existing
cursor.

## Fixed contract and safety

Responses use
`skill2workflow-recurring-schedule-dispatch-page-0.1.0`, defined by
[`schemas/recurring-schedule-dispatch-page-0.1.0.schema.json`](../schemas/recurring-schedule-dispatch-page-0.1.0.schema.json).
Each response contains the same redacted dispatch fields as the compatibility
tail, aggregate status counts, and a fixed `max_items`/`has_more`/`next_cursor`
window. `max_items` is bounded from 1 through 100 and the response is capped
at 64 KiB.

The service uses a SQLite ordering key `(scheduled_for, dispatch_id)` and a
bounded `LIMIT max_items + 1` query. It never exports trigger input,
connector payloads, credential handles, scheduler owner identities, lease
expiry timestamps, or raw persisted records. Invalid cursors, duplicate query
fields, unsupported query fields, body-bearing requests, and oversized
responses fail closed with fixed `400`/`503` behavior. The route is read-only:
it does not acquire the scheduler lease, claim or replay dispatches, append
audit state, or reconcile uncertain outcomes.

The page route is deliberately separate from the 0.1.0 compatibility tail,
so existing clients keep their exact response shape. It does not add bulk
retry, automatic provider reconciliation, RBAC, hosted TLS, or exactly-once
provider execution.

## Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_recurring_dispatch_page_is_cursor_paged_and_redacted \
  tests.test_service.RuntimeServiceTests.test_recurring_schedule_dispatch_list_is_authenticated_bounded_and_redacted \
  tests.test_service_client.ServiceClientTests.test_recurring_dispatch_page_uses_cursor_and_validates_contract \
  tests.test_cli.CliTests.test_service_recurring_dispatch_page_command_supports_cursor \
  -v
```
