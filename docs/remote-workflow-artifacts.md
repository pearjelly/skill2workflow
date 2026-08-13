# Remote Workflow Artifact Consistency

Loop 81 exposes the existing value-free `workflow-artifacts` consistency
diagnostic through the authenticated self-hosted service. This lets an
operator verify a deployment after a crash, manual state copy, backup restore,
or package cutover without shell access to the service host.

## Route and CLI

```text
GET /api/v1/workflow-artifacts
Authorization: Bearer <single-team-token>
```

The request must not include a body. The route is read-only and remains
available while the service is starting, draining, or on standby when SQLite
state is readable. It does not acquire the scheduler lease, mutate registry
records, delete artifacts, or append audit events.

The installed client validates the existing
`skill2workflow-workflow-artifact-report-0.1.0` contract:

```bash
skill2workflow service-workflow-artifacts \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

## Fixed report and bounds

The report is the same schema used by the local `workflow-artifacts` command.
It contains aggregate registry/filesystem counts and at most 64 issue records
over the remote boundary, within a 64 KiB UTF-8 response bound. `summary.issue_count`
and `summary.truncated` retain the full-state count and indicate when the
returned issue window is incomplete.

Issue kinds are `missing`, `unsafe_reference`, `unsafe_artifact`, `invalid_json`,
`oversized`, `checksum_mismatch`, and `orphaned`. Each issue contains only its
kind, bounded artifact reference, and optional workflow/version identifiers.
Workflow titles, instructions, connector requests, checksums, trigger input,
credentials, and raw exception text are never returned.

An empty report has `status: "clean"`; any issue has `status: "attention"`.
The service returns fixed `401`, `400`, and `503` errors for authentication,
body, and state/response failures. Responses are `Cache-Control: no-store`.

## Operator sequence

1. Fetch the report remotely and record the schema version, status, and counts.
2. If status is `attention`, use the bounded issue references to identify the
   affected state copy without attempting automatic repair.
3. Preserve the private state and follow [`backup-restore.md`](backup-restore.md)
   or [`upgrade-migration.md`](upgrade-migration.md) before manual repair.

The route does not repair or delete artifacts, rewrite registry checksums,
publish workflows, or claim a cross-database transaction boundary.

## Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_dashboard.DashboardTests.test_remote_workflow_artifact_report_is_bounded_and_reuses_fixed_contract \
  tests.test_service.RuntimeServiceTests.test_workflow_artifact_report_is_authenticated_bounded_and_value_free \
  tests.test_service_client.ServiceClientTests.test_workflow_artifact_report_uses_authenticated_get_and_validates_contract \
  tests.test_cli.CliTests.test_service_workflow_artifacts_command_prints_report \
  -v
```
