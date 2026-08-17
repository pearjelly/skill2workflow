# Authenticated Redacted Support Bundle

Loop 61 provides one operator-safe artifact for incident triage. It combines
the service lifecycle state, fixed aggregate observability counters, and the
bounded redacted run list without requiring an operator to copy several
responses by hand.

## Service Contract

```http
GET /api/v1/support-bundle
Authorization: Bearer <service-ingress-token>
Accept: application/json
```

The response follows
[`schemas/support-bundle-0.1.0.schema.json`](../schemas/support-bundle-0.1.0.schema.json)
and is versioned as `skill2workflow-support-bundle-0.1.0`. It contains only:

- lifecycle, readiness, SQLite, and scheduler-lease booleans;
- fixed aggregate workflow, run, dispatch, audit, schedule, uptime, and HTTP
  counters; and
- the existing `skill2workflow-run-list-0.1.0` projection with at most 100
  compact run summaries.

It does not include service paths, configuration values, workflow DSL, trigger
input, node-result payloads, connector responses, credential values, raw
errors, audit event payloads, or request headers. The route is read-only: it
does not append audit events, does not acquire the scheduler lease, or change run state.
It remains available while the service is starting, draining, or standby when
the authenticated SQLite state is readable.

The support-bundle `0.1.0` HTTP matrix is intentionally fixed: newer read-only
routes such as `audit_consistency`, `recurring_schedule_list`,
`recurring_schedule_create`, `recurring_schedule_action`,
`recurring_schedule_update`, `retention_readiness`, and
`operational_readiness` remain in the
live metrics route matrix but are omitted from this older bundle contract.

Responses use `Cache-Control: no-store` and are bounded to 128 KiB after UTF-8
encoding. Missing authentication returns `401`; a non-empty request body
returns `400`; and a storage, validation, or response-bound failure returns
the fixed `{"error":"support bundle unavailable"}` response.

## Protected CLI client

Write the bundle directly to an owner-only file. The token stays in its
protected file and the bundle is atomically published with mode `0600`:

```bash
skill2workflow service-support-bundle \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --output /var/lib/skill2workflow/support-bundle.json
```

The command prints only the schema version and output path. Send the resulting
file to a support channel only after reviewing the deployment's own privacy
and retention requirements. Use `service-runs` and `service-show` when a
single run needs deeper redacted inspection; do not send the full SQLite
directory or an offline control snapshot unless its wider metadata is
intended for the recipient.

## Verification

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_support_bundle_is_authenticated_redacted_bounded_and_read_only \
  tests.test_service_client.ServiceClientTests.test_support_bundle_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_support_bundle_writes_private_output \
  -v
```

## Boundary

This is a single-tenant support artifact, not remote log shipping, tracing,
RBAC, a hosted support portal, automatic upload, or a full forensic export.
It deliberately keeps aggregate counters and compact run references while
requiring operators to make the final disclosure decision.
