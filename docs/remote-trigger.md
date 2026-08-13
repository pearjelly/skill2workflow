# Remote Workflow Trigger

Loop 85 turns the existing authenticated webhook boundary into a usable
installed-CLI path. `service-trigger` starts one published workflow through the
self-hosted service without requiring callers to hand-build URLs or response
parsers.

## Command

```bash
skill2workflow service-trigger workflow_approval_flow \
  --version production \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --idempotency-key partner-event-001 \
  --source partner-system \
  --input /path/to/non-secret-input.json
```

`--idempotency-key` is required. The client reads the Bearer token from the
owner-only token file, refuses ambiguous origins and redirects, and never
prints the token or request input. `--input` must contain one JSON object; an
omitted file means `{}`. Trigger inputs are durable run context, not a secret
store, so credentials and confidential payloads must stay outside the input
file.

## Request and response boundary

The client calls the existing protected route:

```text
POST /webhooks/<workflow_id>/<version-or-alias>
Authorization: Bearer <single-team-token>
```

The canonical request envelope contains only `source`, `idempotency_key`, and
`input`. The shared canonical UTF-8 JSON-object input limit remains 1 MiB, and
the complete remote request is capped at the service's 1 MiB body boundary.
Workflow IDs and versions are validated as one safe path component before URL
quoting; aliases such as `production` are allowed.

The client validates the compact existing trigger response exactly:

```json
{
  "trigger_id": "trigger_opaque",
  "workflow_id": "workflow_approval_flow",
  "workflow_version": "0.1.0",
  "run_id": "run_opaque",
  "run_status": "waiting",
  "source": "partner-system",
  "idempotency_key": "partner-event-001",
  "input_keys": ["customer_id"]
}
```

The returned version is the resolved immutable version, even when the request
used an alias. The response contains keys rather than input values.

## Retry and failure semantics

For SQLite service state, retrying the same workflow, requested version,
source, idempotency key, and canonical input replays the compact response
without starting a second run. Reusing the key with a different request, or
retrying an unresolved external outcome, returns `409`; the client surfaces a
fixed `trigger idempotency conflict` error. Authentication, malformed input,
oversized bodies, unavailable service, and missing workflows retain the
existing `401`, `400`, `413`, `503`, and `404` boundaries.

## Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service_client.ServiceClientTests.test_service_trigger_posts_bounded_idempotent_envelope \
  tests.test_service_client.ServiceClientTests.test_service_trigger_requires_idempotency_and_rejects_unsafe_path_before_network \
  tests.test_service_client.ServiceClientTests.test_service_trigger_rejects_oversized_complete_body_before_network \
  tests.test_cli.CliTests.test_service_trigger_command_loads_input_and_requires_retry_key \
  -v
```

The service boundary smoke also exercises the authenticated webhook with a
real service process and SQLite restart continuity.
