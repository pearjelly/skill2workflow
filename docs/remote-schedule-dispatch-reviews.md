# Remote Uncertain-Dispatch Reviews

The scheduler intentionally leaves a recovered dispatch in `uncertain`: a
process may have lost its lease after the provider accepted the effect. Loop
205 adds a narrow operator evidence action for that state without pretending
to reconcile the provider.

## Routes and CLI

```text
POST /api/v1/recurring-schedule-dispatches/{dispatch_id}/review
GET  /api/v1/recurring-schedule-dispatches/{dispatch_id}/review
```

Both routes use the service Bearer token. `POST` requires a JSON body with
exactly the two fields below:

```json
{
  "expected_completed_at": "2026-08-11T00:01:00+00:00",
  "outcome": "effect_not_observed"
}
```

The outcome must be one of:

- `effect_confirmed`: the operator observed the provider-side effect;
- `effect_not_observed`: the operator observed no provider-side effect;
- `no_conclusion`: inspection did not establish either result.

The timestamp is copied from the dispatch list/page projection and is a
compare-and-swap token. A review is idempotent when the same outcome and token
are submitted again. A different outcome, a stale token, a non-uncertain
dispatch, or an invalid identifier returns a fixed conflict/error response.

The installed commands are:

```bash
skill2workflow service-recurring-dispatch-review \
  dispatch_0123456789abcdef \
  --expected-completed-at 2026-08-11T00:01:00+00:00 \
  --outcome effect_not_observed \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-recurring-dispatch-review-get \
  dispatch_0123456789abcdef \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

## Contract and safety boundary

Responses use
[`recurring-schedule-dispatch-review-0.1.0.schema.json`](../schemas/recurring-schedule-dispatch-review-0.1.0.schema.json).
They expose only dispatch/schedule identifiers, scheduling timestamps, the
fixed uncertain status, the supplied outcome, the review timestamp, and an
idempotency `changed` flag. Raw trigger input, connector payloads, credentials,
lease owner, lease expiry, and provider response data never enter the
projection.

The review is stored inside the existing SQLite `record_json` row, so backup,
restore, and audit-chain reads retain it without a schema migration. While the
dispatch record is retained, its status remains `uncertain`. The review does not complete, retry, cancel, or replay work. A
`recurring_schedule_dispatch_reviewed` audit event records the bounded
identifiers, fixed outcome, and whether the write changed durable state.
Operators must use provider-native idempotency and make any subsequent manual
action separately.

## Verification

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_recurring_schedules.RecurringSchedulePersistenceTests.test_uncertain_dispatch_review_is_cas_idempotent_and_preserves_status \
  tests.test_service.RuntimeServiceTests.test_uncertain_dispatch_review_is_authenticated_cas_and_durable \
  tests.test_service_client.ServiceClientTests.test_recurring_dispatch_review_posts_cas_payload_and_fetches_projection \
  -v
```
