# Remote Runtime Info

Loop 84 adds a protected, read-only identity report for upgrade and incident
triage. It lets an operator confirm which package and service contract are
running, which Workflow DSL compatibility line they expose, which SQLite state
layout they opened, and whether the current process is ready and owns the
scheduler lease.

## Route and CLI

```text
GET /api/v1/runtime-info
Authorization: Bearer <single-team-token>
```

The request must not include a body. The route is readiness-independent: a
starting, draining, or standby process can still report its identity when the
state directory is readable.

Use the protected client:

```bash
skill2workflow service-runtime-info \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

## Fixed contract

Responses use `skill2workflow-runtime-info-0.1.0`, defined by
[`schemas/runtime-info-0.1.0.schema.json`](../schemas/runtime-info-0.1.0.schema.json).
The report contains only:

- package, service-config, Workflow DSL, and compatibility-line versions;
- SQLite storage and state-layout identities; and
- fixed lifecycle, readiness, and scheduler-lease booleans.

It never includes hostnames, ports, filesystem paths, token metadata,
credentials, workflow identifiers, run identifiers, or request values. The
response is capped at 16 KiB. Authentication, body, and state failures use
fixed `401`, `400`, and `503` responses.

`service_ready` is the live `/readyz` result at collection time and can be
false while `service_status` is `starting`, `draining`, or `ready` without a
current scheduler lease. The report is a point-in-time diagnostic, not a
compatibility proof for an arbitrary future binary or a replacement for the
Doctor and migration preflights.

## Safe upgrade sequence

1. Fetch and record `package_version`, `service_schema_version`,
   `workflow_dsl_schema_version`, and `state_layout_version` from the old
   process.
2. Stop the old service and run the documented Doctor and migration preflight
   before pointing a new binary at the state directory.
3. Fetch the report from the new process and require `/readyz` to return 200
   before returning traffic.

## Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_runtime_info_is_authenticated_bounded_and_reports_compatibility \
  tests.test_service_client.ServiceClientTests.test_runtime_info_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_runtime_info_command_prints_report \
  -v
```
