# Remote Operational Readiness

Loop 93 adds one authenticated, read-only report for operators and deployment
automation. It combines the existing service lifecycle, published-artifact
consistency, SQLite audit integrity, and offline-backup preflight checks into a
small fixed contract. It does not replace any individual check and does not
claim an atomic snapshot across SQLite databases.

## Route and CLI

```text
GET /api/v1/operational-readiness
Authorization: Bearer <single-team-token>
```

The request must not include a body. Use the protected client:

```bash
skill2workflow service-operational-readiness \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

## Fixed contract

Responses use `skill2workflow-operational-readiness-0.1.0`, defined by
[`schemas/operational-readiness-0.1.0.schema.json`](../schemas/operational-readiness-0.1.0.schema.json).
The report contains only:

- service lifecycle, readiness, SQLite layout, and lease ownership;
- an aggregate workflow-artifact check with an issue count, never issue values;
- the audit-chain status, never a digest or event payload;
- offline-backup status and active-lease state;
- fixed blocking reasons and the note that offline backup requires a stopped
  service when its lease is active.

`status: "ready"` means the service is ready, the current layout is in use,
the artifact report is clean, and the SQLite audit chain is valid. An active
lease makes offline backup `blocked` but is an expected note while the service
is running; it does not make the overall report fail. `status: "attention"`
means one of the execution-safety checks needs operator action. The report is
best-effort across independent read-only checks, so the individual check
statuses are authoritative for diagnosis.

The response is capped at 16 KiB. Authentication, body, and state failures use
fixed `401`, `400`, and `503` responses. The stable support-bundle 0.1.0
projection intentionally omits this route's telemetry counter.

## Safe operating sequence

1. Fetch the report with the protected CLI and record the schema/status.
2. Stop or drain the service only when the report or the relevant check calls
   require maintenance; this endpoint never changes lifecycle state.
3. For a failed check, follow its authoritative guide: artifact consistency,
   audit integrity, backup readiness, or retention readiness.

The endpoint exposes no paths, workflow DSL, run identifiers, audit payloads,
credentials, lease-owner identities, or provider data.

## Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_operational_readiness_is_authenticated_aggregate_and_redacted \
  tests.test_service_client.ServiceClientTests.test_operational_readiness_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_operational_readiness_command_prints_report \
  -v
```
