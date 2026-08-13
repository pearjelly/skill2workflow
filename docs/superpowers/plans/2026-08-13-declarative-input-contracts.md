# Loop 67: Declarative Trigger Input Contracts

## Goal

Make published workflow business inputs explicit while preserving the
Workflow DSL `0.1.0` contract and the historical open-object behavior for
workflows that do not opt in.

## Contract

An optional top-level `input_schema` uses a bounded JSON-Schema-like subset:

- root `type: "object"`
- nested `object`, `array`, `string`, `integer`, `number`, `boolean`, and `null`
- `properties`, `required`, `additionalProperties`, `items`, `minLength`,
  `maxLength`, `minimum`, `maximum`, and `enum` where applicable
- 64 KiB canonical schema size, eight nesting levels, 128 properties, and 128
  enum items

Unsupported keywords fail validation rather than being silently ignored.

## Runtime boundary

The control plane validates normalized trigger input before SQLite idempotency
claims, run-state creation, audit emission, or connector execution. Errors are
fixed and path-aware without echoing rejected values. Direct published-run
execution validates defensively as well. Webhook, schedule, recurring
schedule, and CLI paths converge on the same control-plane boundary.

## Evidence

`tests/test_input_schema.py` covers valid contracts, malformed contracts,
bounded schemas, required/type/unknown-field failures, idempotency non-claims,
and legacy compatibility. The full test suite and repository hygiene checks
remain the release gate.
