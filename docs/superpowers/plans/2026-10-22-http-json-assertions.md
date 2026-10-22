# Loop 266: Executable HTTP JSON Assertions

## Basis And Decision

The approved design §10.7 requires verification methods, success criteria, and
failure paths. Existing inferred verification nodes record completion without
executing a check. Add the explicit built-in `http_assert` connector for a
tool-call node that reads a result endpoint and checks its JSON fields.

A distinct connector ID is intentional: older runtimes reject the unknown
connector instead of treating a new assertion field as ordinary HTTP success.
This leaves existing verification and HTTP behavior compatible. Authors bind
this connector in reviewed DSL; prose compilation does not invent endpoint
URLs, credentials, expected values, or execution authority.

## Contract

- GET only; no request body; input mapping only into query parameters.
- Reuse HTTP destination policy, credential handles, direct transport without
  redirects/proxies, timeout, strict UTF-8 and the 1 MiB response limit.
- Require 1–16 assertions, each exactly `path` plus scalar JSON `equals`.
  Pointers are at most 1,024 UTF-8 bytes/32 tokens; scalar encodings at most
  4,096 bytes. JSON pointer escapes and canonical array indexes are supported.
- All comparisons must pass. Missing fields fail; JSON numbers compare
  numerically but booleans do not equal numbers. Invalid/duplicate-key JSON,
  nonfinite numbers, and oversized numeric literals fail.
- Validate configuration before credentials or network. Discard response
  body/headers from results; return only fixed error and aggregate outcome.
  Expected values belong to DSL and are not a secret-storage mechanism.
- Existing tool-call success/failure, retries, cancellation and timeout rules
  apply. A GET endpoint may still have provider effects; no such guarantees
  or exactly-once claim are made.

## Acceptance And Exclusions

Tests first: matching/mismatching/missing/type errors, malformed configurations
with no transport, JSON boundaries, inherited HTTP policy, no response-value
retention, real loopback requests, JSON/SQLite failure transitions, CLI and
isolated installed-wheel execution. Keep examples and connector inventory
tests aligned. Full supported-Python CI and release preflight before closure.
No shell commands, expression language, automatic polling, endpoint discovery,
or reinterpretation of published workflows.

## Verification Commands

```bash
PYTHONPATH=src python3 -m unittest tests.test_http_assertions tests.test_connectors tests.test_package_smoke -q
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 scripts/http_assertion_smoke.py
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-loop266
python3 scripts/secret_hygiene.py examples/workflows
```
