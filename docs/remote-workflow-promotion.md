# Remote Workflow Promotion

Loop 87 closes the controlled CI/CD path after remote publication. The
protected `service-workflow-promote` command moves one immutable published
version to a stable alias through the service, using the existing SQLite
compare-and-swap transaction. It does not publish, trigger, or mutate the
Workflow DSL artifact.

## Command

```bash
skill2workflow service-workflow-promote workflow_approval_flow \
  --version 0.2.0 \
  --alias production \
  --expected-current-version 0.1.0 \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

`--expected-current-version` is optional for a first promotion, but is
recommended whenever an operator is moving an existing alias. If another
operator moves the alias first, the request fails with `409` and makes no
alias or audit change.

## Request boundary

```text
POST /api/v1/workflow-promotions
Authorization: Bearer <single-team-token>
```

The JSON body is exactly:

```json
{
  "workflow_id": "workflow_approval_flow",
  "version": "0.2.0",
  "alias": "production",
  "expected_current_version": "0.1.0"
}
```

The service requires readiness and the active scheduler lease. Workflow and
alias identifiers use the same safe grammar as the local `promote` command;
the complete request is capped at 1 MiB. The token is read from an owner-only
file and is never included in the request body or output.

## Fixed response

Successful promotion returns exactly:

```json
{
  "schema_version": "skill2workflow-workflow-promotion-0.1.0",
  "workflow_id": "workflow_approval_flow",
  "version": "0.2.0",
  "alias": "production",
  "status": "promoted",
  "checksum": "sha256-hex"
}
```

The response contains no filesystem path, workflow content, credentials, or
request values beyond the selected identifiers. Missing target versions return
`404`; a stale expected version returns `409`; malformed requests return
`400`; an unavailable service or state store returns `503`.

SQLite couples the compare-and-swap check, alias metadata update, and
`workflow_promoted` audit row in one transaction. A repeated promotion to the
same alias target is safe and returns the same fixed summary. This route does
not publish or deprecate versions, trigger runs, upload artifacts, perform
rollbacks, or claim exactly-once provider effects.

## Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_promotion_is_authenticated_cas_and_redacted \
  tests.test_service_client.ServiceClientTests.test_service_workflow_promote_uses_fixed_contract \
  tests.test_cli.CliTests.test_service_workflow_promote_command_uses_cas_options \
  -v
```
