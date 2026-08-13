# Loop 83 Plan: Remote Audit Integrity

## Goal

Let a self-hosted operator verify the SQLite audit chain through the existing
authenticated service boundary without exporting event payloads or requiring
shell access.

## Contract

- Add authenticated `GET /api/v1/audit-integrity` with no request body.
- Reuse `skill2workflow-audit-integrity-0.1.0` exactly.
- Return valid, invalid, and legacy-unsealed diagnostics as payload-free data.
- Bound the response to 16 KiB and keep the route readiness-independent.
- Add the protected client/CLI, fixed telemetry label, package evidence, docs,
  and support-bundle redaction.

## Evidence

Service tests prove Bearer authentication, fixed body handling, invalid-state
redaction, and read-only operation. Client tests prove the exact path, token
header, schema semantics, and response limit. CLI, telemetry, documentation,
and wheel smoke tests complete the operator contract.

## Explicit non-goals

No remote repair, chain rewrite, event export, digital signature, key
management, backup transport, restore, RBAC, or hosted compliance claim is
added.
