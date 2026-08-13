# Remote Workflow Diff

Loop 88 adds a read-only remote review surface for the release path. The
protected `service-workflow-diff` command compares two exact published
Workflow DSL versions through the service, reusing the existing structural
diff contract. It returns identifiers, checksums, aliases, and changed
sections only; workflow values never cross the service boundary.

## Command

```bash
skill2workflow service-workflow-diff workflow_approval_flow \
  --from-version 0.1.0 \
  --to-version 0.2.0 \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The client reads the Bearer token from an owner-only file, rejects redirects
and ambiguous origins, validates the safe workflow references, and enforces a
64 KiB response bound. The route is read-only and does not require readiness or
the scheduler lease.

## Request boundary

```text
GET /api/v1/workflow-diffs/<workflow_id>/<from_version>/<to_version>
Authorization: Bearer <single-team-token>
```

The request has no body. Path components are URL-quoted by the client and use
the same safe reference validation as remote trigger and promotion commands.
Missing versions return `404`; malformed bodies or paths return `400`/`404`;
unavailable or unverifiable artifacts return `503`.

## Fixed response

The response is exactly the existing
`skill2workflow-workflow-diff-0.1.0` contract documented in
[`workflow-releases.md`](workflow-releases.md) and
[`schemas/workflow-diff-0.1.0.schema.json`](../schemas/workflow-diff-0.1.0.schema.json).
It contains no titles, descriptions, connector requests, input values,
credentials, artifact paths, or arbitrary field values.

This route does not promote aliases, publish versions, trigger runs, approve a
release, or provide semantic business-risk analysis. Operators still choose
the target and use `service-workflow-promote` with an expected-current-version
guard when moving the alias.

## Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_diff_is_authenticated_value_free_and_read_only \
  tests.test_service_client.ServiceClientTests.test_service_workflow_diff_uses_fixed_redacted_contract \
  tests.test_cli.CliTests.test_service_workflow_diff_command_uses_version_options \
  -v
```
