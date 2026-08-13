# Remote Audit Consistency

The self-hosted service exposes the local run/audit consistency diagnostic to
authenticated operators without requiring shell access to the state directory.
It is a read-only incident diagnostic: it never resumes, retries, repairs, or
deletes a run or an audit event.

## HTTP Contract

```http
GET /api/v1/audit-consistency
Authorization: Bearer <token>
```

When the global 256-run window is truncated, target one run without shell
access using the fixed path form:

```http
GET /api/v1/audit-consistency/run_<opaque-id>
Authorization: Bearer <token>
```

The target identifier must use the same `run_`-prefixed safe identifier grammar
as the run-detail endpoint. A targeted report has one run and is never marked
truncated because of the global window. An unknown target returns the fixed
`503` unavailable response rather than exposing state or filesystem details.

The request must have an empty body. The endpoint returns the existing
`skill2workflow-run-audit-report-0.1.0` contract from
[`run-audit-consistency.md`](run-audit-consistency.md), with a 64 KiB encoded
response bound. Authentication failures use the same fixed `401`/`503`
boundary as the other protected read routes. An invalid body returns `400` and
the fixed message `audit consistency request must not include a body`.

The endpoint is available before readiness when the authentication provider and
SQLite state are readable. It does not append an ingress audit event, acquire
the scheduler lease, or expose workflow instructions, trigger input, connector
output, credentials, or raw errors. If the projection cannot be read or would
exceed its bound, it returns `503` with `{"error":"audit consistency unavailable"}`.

## Installed Client

The installed CLI reads the Bearer token from an owner-only file and validates
the exact response shape before printing it:

```bash
skill2workflow service-audit-consistency \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-audit-consistency \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --run-id run_...
```

The client rejects ambiguous origins, remote plain HTTP, redirects, malformed
headers, oversized responses, and extra or missing report fields. Use the
local `audit-consistency` command when the operator is already on the service
host; use this endpoint for a remote, TLS-terminated self-hosted deployment.

## Evidence

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_audit_consistency_is_authenticated_bounded_and_read_only \
  tests.test_service.RuntimeServiceTests.test_audit_consistency_is_available_before_readiness \
  tests.test_service.RuntimeServiceTests.test_audit_consistency_rejects_oversized_projection_without_disclosure \
  tests.test_service.RuntimeServiceTests.test_audit_consistency_can_target_one_run_beyond_the_global_window \
  tests.test_service_client.ServiceClientTests.test_audit_consistency_uses_authenticated_get_and_validates_contract \
  tests.test_service_client.ServiceClientTests.test_audit_consistency_can_target_one_safe_run_id \
  tests.test_service_client.ServiceClientTests.test_audit_consistency_rejects_unsafe_target_before_network_access \
  tests.test_cli.CliTests.test_service_audit_consistency_command_prints_report \
  tests.test_cli.CliTests.test_service_audit_consistency_command_accepts_one_run_id \
  -v
```
