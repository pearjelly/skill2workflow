# Loop 62: Durable SQLite Trigger Idempotency

**Status:** Complete.

**Goal:** Prevent a retried self-hosted trigger from starting a second workflow
run when the first request may already have produced a side effect.

## Contract

- A non-empty trigger key is limited to 128 UTF-8 bytes and a fixed safe
  character set.
- SQLite claims `(workflow_id, version, idempotency_key)` atomically before
  execution.
- The request fingerprint covers source and canonical input values but only
  its SHA-256 digest is persisted.
- Completed identical retries return the compact original trigger response
  without a second run or duplicate run-lifecycle audit event. Authenticated
  HTTP ingress still records its normal authentication event per request.
- Mismatched requests, concurrent claims, and unresolved claims return fixed
  `409` conflicts and do not execute a second run.
- A generated `trigger_id` is not part of the fingerprint, so rebuilding a
  request envelope does not change replay identity.
- JSON/local evaluation keeps the previous metadata-only behavior.

## Exclusions

The loop does not claim exactly-once provider effects, automatically retry an
unknown external outcome, expire or garbage-collect keys, coordinate
distributed workers, add tenant identity, or add idempotency enforcement to
JSON/local evaluation.

The ledger contains no trigger input values, credential values, request
headers, provider payloads, or raw exception text. It is part of the verified
SQLite backup boundary and is therefore copied by stopped-service backup and
restore.

## Evidence

The public contract is [`docs/triggers.md`](../../triggers.md). The focused
evidence covers normalization, stable fingerprints, replay, mismatch,
concurrency, unresolved-outcome fencing, authenticated service `409` errors,
recurring dispatch compatibility, input-value exclusion, and backup/restore
replay safety. The full suite and package qualification remain the release
gates.
