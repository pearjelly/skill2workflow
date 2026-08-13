# Authenticated Run Detail

The self-hosted service exposes one bounded, read-only projection for an
operator who needs to inspect a run before approving or cancelling it:

```http
GET /runs/{run_id}
Authorization: Bearer <service-ingress-token>
```

The response is versioned as
`skill2workflow-run-detail-0.1.0` and follows
[`schemas/run-detail-0.1.0.schema.json`](../schemas/run-detail-0.1.0.schema.json).
It contains the run identity and status, a compact per-node operational
overlay, and at most the latest 50 allowlisted run events. The `window` object
states the total event count, returned count, and truncation status.

This is an operator read surface, not a state export. It never returns the
workflow DSL, trigger context or input values, node-result payloads, connector
responses, credential values, or raw error strings. Errors are represented only
by the boolean `has_error` flag. The endpoint does not append audit events and
does not require the scheduler lease or service readiness, so a standby can be
used for diagnosis when its SQLite state is readable.

Unauthenticated requests return `401`; an unavailable token provider returns
`503`; a missing run returns `404`; a non-empty request body returns `400`; and
an internal or oversized projection returns the fixed `503` response
`{"error":"run detail unavailable"}`. Responses carry `Cache-Control:
no-store` and are capped at 64 KiB.

## Protected CLI client

The installed CLI reads the Bearer token from an owner-only file and applies
the same origin, redirect, proxy, response-size, and schema checks as the
action clients:

```bash
skill2workflow service-show run_example \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The command prints only the redacted detail contract. It does not retry, write
state, or place the token in argv.

To discover a suitable `run_id` first, use the bounded [`service-runs`](run-list.md)
client. The list → detail → decision sequence keeps broad registry and audit
collections out of a routine operator handoff.

## Verification

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_run_detail_is_bounded_and_redacts_context_results_and_errors \
  tests.test_service.RuntimeServiceTests.test_run_detail_is_authenticated_redacted_bounded_and_read_only \
  tests.test_service_client.ServiceClientTests.test_run_detail_uses_authenticated_get_and_validates_redacted_contract \
  -v
```
