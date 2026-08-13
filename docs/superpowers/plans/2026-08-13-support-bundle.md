# Loop 61: Authenticated Redacted Support Bundle

**Status:** Complete.

**Goal:** Give self-hosted operators one safe, bounded artifact for incident
triage instead of manually combining readiness, metrics, and run-discovery
responses.

## Contract

- `GET /api/v1/support-bundle` requires the existing file-backed Bearer token.
- The response is `skill2workflow-support-bundle-0.1.0` and is capped at 128 KiB.
- The bundle includes fixed lifecycle/readiness/lease fields, structured
  aggregate observability, and the existing redacted run-list projection.
- It is read-only and available before readiness when authenticated SQLite
  state can be read.
- The client writes an owner-only `0600` JSON file atomically and prints no
  bundle contents by default.

## Exclusions

The bundle does not include workflow DSL, trigger input, node-result payloads,
connector responses, credentials, service paths, raw errors, audit payloads,
request headers, remote upload, tracing, RBAC, or a full SQLite export.

## Evidence

The exit gate is the focused service/client/CLI contract test, the full test
suite, wheel smoke with the installed command, secret hygiene, and `git diff
--check`. The public guide is [`docs/support-bundle.md`](../../support-bundle.md)
and the machine-readable contract is
[`schemas/support-bundle-0.1.0.schema.json`](../../../schemas/support-bundle-0.1.0.schema.json).
