# Durable Cooperative Run Cancellation

Loop 48 gives the self-hosted single-tenant runtime an authenticated, durable way to stop future workflow progress. Cancellation is cooperative: it becomes effective at an executor safe point and never pretends that an external side effect was rolled back.

## Operator Interfaces

Cancel a published run locally:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli cancel-run run_0123456789ab \
  --state-dir /var/lib/skill2workflow \
  --storage sqlite
```

The public `cancel-run` command is intentionally SQLite-only. JSON storage remains available for dependency-light evaluation, but it does not provide the cross-process serialization required for a production cancellation guarantee.

Through the service, send an authenticated empty JSON object:

```http
POST /runs/{run_id}/cancel
Authorization: Bearer <team ingress token>
Content-Type: application/json

{}
```

The route has the same loopback, external TLS, rotating Bearer-token, request-size, and `Cache-Control: no-store` boundaries as workflow triggers. It accepts no operator-supplied reason or metadata, so cancellation audit evidence cannot become an accidental business-data channel.

Responses are deliberately compact:

- `cancel_requested`: a running or newly created run has a durable request and will stop at its next safe point;
- `cancelled`: a waiting run stopped immediately, or an earlier request already completed;
- HTTP `401`: authentication failed;
- HTTP `404`: the run does not exist;
- HTTP `409`: the run is already `completed`, `failed`, or `interrupted` and cannot be rewritten.

Repeating cancellation is idempotent. It creates one `run_cancel_requested` audit event and one terminal `run_cancelled` event, without a reason, request body, credential, connector response, or workflow payload.

## Safe-point Semantics

The executor checks the durable request:

1. before entering the first node;
2. before every subsequent node;
3. before every connector attempt;
4. after a failed connector attempt and before a retry; and
5. after a connector result is recorded and before its successor starts.

A `waiting` human gate is safe and becomes `cancelled` immediately. It cannot then be resumed. A concurrent stale save cannot overwrite that decision: SQLite run writes consult the independent cancellation ledger before committing active state.

The runtime uses a `run_cancellations` table in `runs.sqlite3`, separate from the whole-run JSON snapshot. This avoids losing a request when an executor saves state it loaded earlier. The ledger contains only `run_id`, request/apply timestamps, and the fixed `requested` or `applied` status. It is an additive table within the current layout: older valid state can start without it, and the service creates it before accepting work; backup verification validates its exact columns whenever it is present.

## External Side-effect Boundary

Cancellation does not interrupt an external request that a connector already sent. Python threads, HTTP servers, and remote providers do not offer a portable safe kill primitive, and closing a local socket would not prove that the provider abandoned the operation.

When cancellation arrives during a connector call, that attempt is allowed to return or time out. Its completion or failure evidence is persisted, the run becomes `cancelled`, and no retry or successor node starts. Operators must inspect connector evidence and rely on provider idempotency or a separately designed compensation workflow before assuming that no external side effect occurred.

This contract does not provide forceful thread termination, provider-side task deletion, transaction rollback across systems, or compensation.

## Service Concurrency And Shutdown

The service accepts requests on concurrent handler threads so a cancellation can be persisted while another request is executing. SQLite remains the durable serialization boundary. During graceful shutdown, readiness is withdrawn and no new business request is accepted; already accepted handlers are allowed to finish, and the process waits for them before closing.

If the process stops after a request is persisted but before the executor reaches a safe point, Loop 49 takeover records the run as `interrupted`, applies the pending cancellation ledger entry, and fences stale writes. Operators must inspect the run and external provider outcome; neither cancellation nor interruption automatically retries or retracts the external operation.

## Backup, Observability, And Retention

Verified backups copy the complete `runs.sqlite3` database and validate the cancellation ledger when present. Restores therefore preserve both terminal `cancelled` state and pending requests.

Prometheus export includes the fixed low-cardinality run status `cancelled` and HTTP route `run_cancel`; neither exposes a run identifier.

Use retention policy `skill2workflow-retention-policy-0.3.0` to dispose of expired `completed`, `failed`, `cancelled`, and operator-reviewed `interrupted` runs. It removes linked run events, audit events, `run_cancellations`, and execution tickets from the retained copy. Policies `0.1.0` and `0.2.0` remain accepted for compatibility with their narrower terminal sets.

## Evidence

Run the real-process drill:

```bash
python3 scripts/cancellation_smoke.py \
  --work-dir /tmp/skill2workflow-cancellation-loop48
```

The drill starts a real service and a deliberately blocked provider, submits cancellation concurrently, proves the completed external attempt is recorded while the successor is suppressed, cancels a waiting run twice, restarts the service, and checks compact audit output. Evidence contains only booleans and aggregate counts.

## Deferred Boundary

Loop 48 does not add forceful connector abort, provider compensation, bulk cancellation, cancellation deadlines, user-defined reasons, RBAC, distributed workers, or exactly-once execution. Loop 49 adds fail-closed interruption detection and fencing, not automatic replay or reconciliation.
