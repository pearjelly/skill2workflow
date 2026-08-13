# Loop 68: Bounded Service Request Admission

## Goal

Prevent a single self-hosted service process from accepting an unbounded
amount of concurrent business work while preserving health and readiness
signals for safe proxy traffic management.

## Contract

Every non-probe HTTP route uses a fixed process-local budget of 16 active
handlers. Admission is non-blocking. Exhaustion returns:

- HTTP status `429`
- body `{"error":"service concurrency limit reached"}`
- `Retry-After: 1`

`GET /healthz` and `GET /readyz` bypass the budget. The budget is not a client
quota, distributed queue, or exactly-once guarantee.

## Runtime boundary

Admission occurs before authentication, request-body reads, trigger
normalization, SQLite idempotency claims, run-state creation, and business
audit writes. An acquired slot is released from the request-dispatch `finally`
path, including socket/write failures. Telemetry observes both accepted and
rejected route statuses.

## Evidence

`tests/test_service.py` exhausts all slots, verifies a fixed `429`, and checks
that health remains available. The existing service, cancellation, scheduling,
security, packaging, and full-suite checks remain the release gate.
