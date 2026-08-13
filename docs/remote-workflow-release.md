# Remote Workflow Publication

Loop 86 adds one controlled CI/CD entry point for a self-hosted service. The
protected `service-workflow-publish` command sends one Workflow DSL document to
the service, which reuses the existing immutable SQLite publication transaction
and returns a redacted record. Version promotion remains a separate operator
decision and is not performed by this command.

## Command

```bash
skill2workflow service-workflow-publish \
  /path/to/workflow.workflow.json \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The client reads the Bearer token from an owner-only file, refuses ambiguous
origins and redirects, and never prints the submitted Workflow DSL or service
artifact path. The service requires readiness and the active SQLite scheduler
lease before accepting the mutation.

## Request boundary

```text
POST /api/v1/workflow-releases
Authorization: Bearer <single-team-token>
```

The JSON body is exactly `{"workflow": <Workflow DSL object>}`. The complete
request is capped at 1 MiB, and the existing Workflow DSL validator remains the
source of truth for schema and graph validity. Invalid requests are rejected
before publication. Do not put credentials, access tokens, or confidential
business payloads in a workflow artifact; credential handles remain references
to the separate local provider boundary.

## Fixed response

Successful publication returns exactly:

```json
{
  "schema_version": "skill2workflow-workflow-release-0.1.0",
  "workflow_id": "workflow_approval_flow",
  "version": "0.1.0",
  "status": "published",
  "checksum": "sha256-hex"
}
```

The response contains no filesystem path, workflow content, credentials, or
request values. Publishing the same immutable version with identical content
is safe to retry and returns the same compact record. Publishing different
content under an existing version returns `409`; malformed DSL and envelope
errors return `400`; an oversized body returns `413`; unavailable service/state
returns `503`.

The server reuses the existing publication transaction: SQLite couples the
immutable artifact, registry record, and `workflow_published` audit row. This
route does not promote an alias, trigger a run, deprecate a version, or upload
an artifact elsewhere.

## Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_publication_is_authenticated_immutable_and_redacted \
  tests.test_service_client.ServiceClientTests.test_service_workflow_publish_uses_fixed_contract \
  tests.test_cli.CliTests.test_service_workflow_publish_command_loads_workflow \
  -v
```
