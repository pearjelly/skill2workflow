# Remote Audit Integrity

Loop 83 exposes the existing SQLite SHA-256 audit-chain verification result
through the authenticated service boundary. It lets an operator detect a
truncated, reordered, or tampered control-plane audit chain without shell
access or event-payload export.

## Route and CLI

```text
GET /api/v1/audit-integrity
Authorization: Bearer <single-team-token>
```

The request must not include a body. The route is read-only and remains
available while the service is starting, ready, draining, or standby when the
SQLite control database is readable.

Use the protected client:

```bash
skill2workflow service-audit-integrity \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

## Fixed contract

The response reuses
`skill2workflow-audit-integrity-0.1.0`, defined by
[`schemas/audit-integrity-0.1.0.schema.json`](../schemas/audit-integrity-0.1.0.schema.json).
It contains only the status, algorithm, event count, chain head digest, first
affected sequence, and a fixed reason. It never includes an audit event,
workflow identifier, run identifier, input, connector response, credential, or
raw exception.

`status: "valid"` confirms the locally stored chain is internally consistent.
`status: "invalid"` is still a successful diagnostic response and requires
operator investigation; the route does not repair or rewrite the chain.
`status: "legacy_unsealed"` is the expected result for a legacy JSON audit
path or before an older SQLite audit table is opened by a version that seals
it. The existing local `audit-verify` command remains authoritative for the
host-side stop-and-recovery procedure.

The response is capped at 16 KiB. Authentication, body, and state failures
use fixed `401`, `400`, and `503` responses. The older support-bundle 0.1.0
projection intentionally omits this route's counter.

## Safe operating sequence

1. Fetch the report and record the schema version, status, reason, and event
   count.
2. If the status is `invalid`, stop mutating service state and follow the local
   [`audit-integrity.md`](audit-integrity.md) recovery and backup procedure.
3. Preserve the original state directory and any verified backup before an
   operator-managed restore or migration decision.

The endpoint does not sign evidence, establish operator identity, repair the
database, or replace authenticated backups and access controls.

## Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_audit_integrity_is_authenticated_payload_free_and_read_only \
  tests.test_service_client.ServiceClientTests.test_audit_integrity_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_audit_integrity_command_prints_report \
  -v
```
