# Loop 81 Plan: Remote Workflow Artifact Consistency

## Goal

Expose the existing local workflow artifact consistency report through the
authenticated service so remote operators can detect incomplete or corrupted
published state after a restart, restore, or cutover.

## Contract

- Add read-only `GET /api/v1/workflow-artifacts` behind the existing Bearer boundary.
- Reuse `skill2workflow-workflow-artifact-report-0.1.0` exactly.
- Return at most 64 issue records and 64 KiB over the remote boundary.
- Preserve aggregate full-state counts and truncation semantics.
- Keep workflow content, checksums, trigger input, credentials, and raw errors private.
- Add a protected client and `service-workflow-artifacts` CLI command.
- Keep the route readiness-independent and absent from the stable support-bundle 0.1.0 projection.

## Evidence

Dashboard tests prove remote issue-window bounding and content redaction.
Service tests prove authentication, fixed schema, and value-free responses.
Client tests prove exact path, token header, schema validation, and response
limits. CLI, telemetry, package, documentation, and full-suite tests complete
the installed operator contract.

## Explicit non-goals

No artifact repair, deletion, checksum rewrite, publication, remote mutation,
RBAC, remote upload, or cross-database transaction is added.
