# Remote Workflow Inventory

Loop 91 adds a bounded, authenticated read surface for the published Workflow
registry. Remote publication, diff, promotion, and deprecation are useful only
if an operator can first discover which versions exist; this endpoint supplies
that missing inventory without exporting Workflow content or filesystem data.

## Command

```bash
skill2workflow service-workflows \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The token is read from the owner-only file and is never printed. The command
uses the same redirect, proxy, origin, response-size, and Bearer-token
boundaries as the other installed service clients.

## Fixed HTTP contract

The client sends an authenticated body-less `GET /api/v1/workflows`. The route
is available while the service is starting, draining, or standby, provided
authentication and SQLite state are readable. It does not acquire the scheduler
lease and does not append audit state.

The response is capped at 64 KiB and contains at most 100 versions:

```json
{
  "schema_version": "skill2workflow-workflow-inventory-0.1.0",
  "summary": {
    "total": 2,
    "status_counts": {"published": 1, "deprecated": 1, "other": 0}
  },
  "versions": [
    {
      "workflow_id": "workflow_approval_flow",
      "version": "0.2.0",
      "status": "published",
      "aliases": ["production"],
      "checksum": "<64 lowercase hex characters>"
    }
  ],
  "window": {"max_items": 100, "total": 2, "returned": 1, "truncated": true}
}
```

Only stable identifiers, lifecycle status, bounded aliases, and checksums cross
the boundary. The response never includes the Workflow name or DSL, artifact
path, `published_at`/`deprecated_at`, audit events, credentials, trigger input,
or provider data. The client validates the exact schema, status counts, window
arithmetic, and lowercase SHA-256 checksums before printing anything.

## Operator sequence and safety boundary

Use `service-workflows` to select known versions, `service-workflow-diff` to
review a structural change, `service-workflow-promote` with an expected-current
version to move an alias, and `service-workflow-deprecate` to retire a version.
Inventory is read-only: it does not publish, promote, deprecate, trigger,
repair, delete artifacts, or perform semantic business-risk analysis.

Invalid body, transfer encoding, malformed state, authentication failure, and
oversized responses fail with fixed generic errors. No user-controlled value is
turned into a telemetry label or error detail.

## Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_inventory_is_authenticated_bounded_and_read_only \
  tests.test_service_client.ServiceClientTests.test_service_workflow_inventory_uses_fixed_redacted_contract \
  tests.test_cli.CliTests.test_service_workflows_command_prints_inventory \
  -v
```
