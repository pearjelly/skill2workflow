# Loop 205: Protected Uncertain-Dispatch Reviews

## Goal

Make the scheduler's `uncertain` recovery state operationally reviewable
without pretending to reconcile an external provider or authorizing automatic
replay.

## Contract

- The dispatch remains `status: "uncertain"` for its entire lifetime.
- A review has exactly one fixed outcome: `effect_confirmed`,
  `effect_not_observed`, or `no_conclusion`.
- `completed_at` from the redacted dispatch projection is the compare-and-swap
  token. Same-outcome retries are idempotent; a stale token or contradictory
  outcome is a conflict.
- The review projection never contains trigger input, credentials, connector
  payloads, lease owner, or lease expiry.
- Local and authenticated service CLIs are the operator entry points.

## Implementation

1. Store the bounded review object inside the existing SQLite dispatch record.
2. Add authenticated `POST` and `GET` review routes with fixed response and
   error behavior.
3. Add service-client validators and local/remote CLI commands.
4. Add a bounded allowlisted audit event and a low-cardinality telemetry route,
   while preserving the fixed support-bundle contract.
5. Document backup compatibility, operator workflow, and the no-replay safety
   boundary; add schema, service, client, CLI, telemetry, and package tests.

## Verification

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke-loop205
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_uncertain_dispatch_review_is_cas_idempotent_and_preserves_status \
  tests.test_service.RuntimeServiceTests.test_uncertain_dispatch_review_is_authenticated_cas_and_durable \
  tests.test_service_client.ServiceClientTests.test_recurring_dispatch_review_posts_cas_payload_and_fetches_projection \
  tests.test_cli.CliTests.test_service_recurring_dispatch_review_commands_preserve_cas_and_outcome -v
```

## Explicit exclusions

This loop does not retry, complete, cancel, replay, or reconcile a provider
effect; add RBAC or operator identity; alter the existing dispatch list/page
schemas; introduce a database migration; or claim exactly-once execution.
