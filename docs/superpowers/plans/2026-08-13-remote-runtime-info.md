# Loop 84 Plan: Remote Runtime Info

## Goal

Give a self-hosted operator a safe, authenticated way to identify the running
package and compatibility boundary during upgrade, rollback, and incident
triage.

## Contract

- Add authenticated `GET /api/v1/runtime-info` with no request body.
- Publish a fixed `skill2workflow-runtime-info-0.1.0` schema.
- Report package, service, Workflow DSL, storage/layout, lifecycle, readiness,
  and lease metadata without paths or business values.
- Keep the route readiness-independent and bound to 16 KiB.
- Add protected client/CLI, telemetry, package evidence, and docs.

## Evidence

Service tests prove authentication, body handling, readiness-independent state,
and fixed output. Client tests prove the exact path, token header, schema
validation, and response limit. CLI, telemetry, schema, documentation, and
wheel smoke tests complete the operator contract.

## Explicit non-goals

No remote upgrade, rollback, shutdown, migration, configuration disclosure,
host inventory, runtime dependency dump, RBAC, or compatibility guarantee for a
future binary is added.
