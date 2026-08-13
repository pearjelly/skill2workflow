# Authenticated Run List

Operators can discover run identifiers through the bounded read-only service
route:

```http
GET /runs
Authorization: Bearer <service-ingress-token>
```

The response follows
[`schemas/run-list-0.1.0.schema.json`](../schemas/run-list-0.1.0.schema.json)
and is versioned as `skill2workflow-run-list-0.1.0`. It contains at most the
latest 100 compact run summaries plus fixed status counts. Each summary
contains only the run ID, workflow reference, status, current node, event
count, and node-result count. It never returns workflow DSL, trigger input,
node-result payloads, connector responses, credentials, or raw errors.

The `window` object reports total, returned, and truncation state. The endpoint
is available while the service is starting, draining, or standby when its
authenticated SQLite state is readable; it does not append audit events and does not acquire the scheduler lease.
Responses are `Cache-Control: no-store` and
bounded to 64 KiB. Missing authentication returns `401`; a non-empty request
body returns `400`; and a storage or response-bound failure returns the fixed
`{"error":"run list unavailable"}` response.

## Protected CLI client

```bash
skill2workflow service-runs \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The CLI keeps the token out of argv, disables proxies and redirects, validates
the response headers and schema, and prints only the fixed redacted contract.
Use a returned `run_id` with [`service-show`](run-detail.md),
`service-resume`, or `service-cancel`.

## Verification

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_run_list_is_bounded_and_redacted \
  tests.test_service.RuntimeServiceTests.test_run_list_is_authenticated_bounded_and_read_only \
  tests.test_service_client.ServiceClientTests.test_run_list_uses_authenticated_get_and_validates_contract \
  -v
```
