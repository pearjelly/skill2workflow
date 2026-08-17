# SQLite Run-State Boundary

Loop 174 closes the production persistence gap left by the dependency-light
JSON run-state boundary. SQLite is the recommended self-hosted storage backend,
so its complete durable run document must have the same predictable size
ceiling instead of becoming an unbounded escape hatch.

## Contract

Every SQLite run-state insert or update serializes the complete state as UTF-8
JSON and enforces a fixed **8 MiB** (`8,388,608` byte) limit before the
transaction can commit. The runtime uses the compact canonical representation
for this check; the limit covers workflow definition, trigger context, node
results, execution metadata, and the accumulated run-event list.

Reads through `load`, complete listing, cancellation, deadline expiry,
interrupted-run recovery, and startup summary repair check the stored UTF-8
document before JSON decoding. Oversized, malformed, or non-object documents
fail with a fixed `ValueError`; bounded summary and page projections continue
to avoid reading the full run document when they do not need it.

The JSON backend keeps its existing 8 MiB contract. The SQLite bound is a
durability and decoder-memory boundary, not a retention policy: terminal runs
still require the documented retention workflow, and large business payloads
should be stored in an appropriate external system rather than in run state.

## Safety boundary

This loop does not split workflow state, compress or encrypt SQLite rows, cap
individual event payloads separately, change the Workflow DSL, or guarantee
that a provider-side effect can be rolled back. The external connector result
envelope and trigger-input limits remain independent earlier boundaries.

Focused evidence:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_storage \
  tests.test_json_run_state_docs \
  -v
```
