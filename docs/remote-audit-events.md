# Remote Audit Event Tail

The self-hosted service exposes a bounded, redacted audit tail for remote
incident diagnosis. It is read-only: it never resumes, retries, repairs, or
deletes a run, audit row, workflow, credential, or connector result.

## HTTP contract

```http
GET /api/v1/audit-events?max_items=100&workflow_id=<id>&workflow_version=<version>&run_id=run_<id>&event_type=<type>
Authorization: Bearer <token>
```

The request must have an empty body. `max_items` is 1 through 100. The optional
filters are exact matches and may occur only once. The response uses
[`schemas/audit-event-list-0.1.0.schema.json`](../schemas/audit-event-list-0.1.0.schema.json)
and is capped at 64 KiB. Events are returned in sequence order within each
page. When `window.truncated` is true, pass the opaque `window.next_cursor`
back as `cursor` to read the preceding page. The total is the count for the
selected filter (not a count of raw payload bytes).

Every event is projected through a fixed allowlist: sequence, type, safe
workflow/run identifiers, timestamp, node/connector status, retry counters,
approval state, and an error-presence flag. Workflow DSL, trigger context,
connector metadata/output, credential values, raw provider errors, and arbitrary
payload keys never cross this boundary. Authentication failures use the same
fixed `401`/`503` boundary as the other protected read routes. Invalid query
fields or a non-empty body return `400`; an unreadable SQLite projection
returns `503` with the fixed `audit event page unavailable` message.

The route is available before readiness when authentication and SQLite state are
readable. It does not acquire the scheduler lease, call providers, or append
ingress audit evidence. JSON storage is intentionally rejected for this remote
service surface because cursor paging requires the bounded SQLite index.

## Installed client

The installed CLI reads the Bearer token from an owner-only file, validates the
origin, response headers, byte bound, exact schema, and redaction shape, then
prints the projection:

```bash
skill2workflow service-audit-events \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --max-items 100

skill2workflow service-audit-events \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --run-id run_... \
  --event-type connector_failed \
  --cursor <next_cursor>
```

Use the local `audit --limit` command when shell access is available; use this
endpoint for a TLS-terminated self-hosted deployment where the operator needs
bounded, value-free diagnostics without copying the state directory.

## Evidence

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_storage.StorageTests.test_sqlite_audit_page_filters_and_continues_with_sequence_cursor \
  tests.test_dashboard.DashboardTests.test_audit_event_page_is_cursor_paged_and_redacted \
  tests.test_service.RuntimeServiceTests.test_audit_event_page_is_authenticated_filtered_cursor_paged_and_redacted \
  tests.test_service_client.ServiceClientTests.test_audit_event_page_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_audit_events_command_prints_filtered_page \
  -v
```
