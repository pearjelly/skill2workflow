# Loop 92 Plan: Remote Retention Readiness

## Goal

Make the existing copy-on-write retention procedure safer to operate from the
authenticated remote control boundary without adding remote deletion or
backup transport.

## Contract

- Add authenticated `POST /api/v1/retention-readiness` with an exact policy body.
- Reuse the local retention-policy normalization and fixed aggregate plan.
- Return `blocked` with null counts while an active scheduler lease exists.
- Return counts only after a current-layout, quiesced read-only inspection.
- Bound requests/responses and keep the route readiness-independent.
- Add protected client/CLI, fixed telemetry, schema, docs, package evidence,
  and support-bundle redaction.

## Explicit non-goals

No remote retention apply, deletion, backup creation, upload, restore, service
shutdown, scheduler mutation, legal-hold inference, or filesystem erasure is
added.
