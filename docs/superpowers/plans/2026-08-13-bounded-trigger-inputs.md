# Loop 66: Bounded Trigger Inputs

**Status:** Complete

## Goal

Bound the durable trigger-input object consistently across CLI, webhook,
one-shot schedule, and recurring schedule entry paths without changing the
Workflow DSL `0.1.0` contract or the existing run-context shape.

## Contract

- The canonical UTF-8 JSON encoding uses sorted keys and compact separators.
- The object is limited to 1 MiB (`1,048,576` bytes).
- The limit is checked before the value is copied into durable context or used
  by SQLite idempotency fingerprinting.
- Oversized input raises a fixed, payload-free `ValueError`; the direct webhook
  parser maps it to HTTP 400, while the earlier 1 MiB wire-body guard may
  reject the larger HTTP request with HTTP 413.
- The limit bounds size only. It does not encrypt, redact, classify, or make
  provider effects exactly once.

## Evidence

- `tests/test_triggers.py` covers the shared normalizer and oversize rejection.
- `tests/test_cli.py` proves the CLI rejects oversized input before opening
  state.
- `tests/test_schedules.py` and `tests/test_recurring_schedules.py` cover both
  schedule contracts.
- `tests/test_webhooks.py` preserves the transport body bound and trigger path.
- `docs/triggers.md`, `docs/recurring-scheduling.md`, and `docs/stability.md`
  publish the operator and compatibility boundary.

## Exclusions

No request quotas, rate limiting, streaming uploads, field-level business
schemas, encryption, redaction, JSON/JSONL historical rewrite, or exactly-once
provider guarantee is introduced.
