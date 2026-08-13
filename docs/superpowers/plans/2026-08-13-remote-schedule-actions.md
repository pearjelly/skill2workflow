# Plan: Protected Remote Recurring-Schedule Actions

## Goal

Close the operator gap after Loop 78: allow a same-team self-hosted operator to
pause or resume one existing recurring schedule over the authenticated service
boundary, without exposing scheduler payloads or changing the single-tenant
execution model.

## Contract

- `POST /api/v1/recurring-schedules/{schedule_id}/disable`
- `POST /api/v1/recurring-schedules/{schedule_id}/enable`
- Bearer authentication is required and is audited through the fixed route
  class `recurring_schedule_action`.
- The body is exactly `{}`; schedule IDs use the existing bounded safe grammar.
- The response is `skill2workflow-recurring-schedule-action-0.1.0` with the
  resulting state and a boolean `changed` field.
- Repeating the same action is a successful no-op (`changed: false`).

## Implementation sequence

1. Extend the recurring store with an idempotent state transition result while
   keeping `BEGIN IMMEDIATE` serialization with dispatcher claims.
2. Add a fixed service route and bounded mutation audit event after the scheduler
   transaction succeeds.
3. Add protected client and installed CLI commands, including origin, token,
   response-header, byte-bound, identifier, and schema validation.
4. Add the versioned JSON Schema, observability route label, support-bundle
   compatibility filtering, public operator guide, and release qualification
   command inventory.
5. Verify unauthorized access, exact body handling, unknown IDs, idempotent
   retries, redaction, audit evidence, and existing support-bundle behavior.

## Exclusions

This loop does not create or delete schedules, claim or dispatch occurrences,
control the scheduler lease, introduce RBAC or multi-tenancy, make the control
and scheduler databases one transaction, or claim exactly-once provider
effects. Scheduler state remains authoritative in `scheduler.sqlite3`; the
control-plane audit entry is bounded operator evidence written after the state
transaction commits.
