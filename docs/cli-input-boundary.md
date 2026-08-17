# CLI JSON Input Boundary

Loop 166 gives the local CLI one predictable boundary for JSON files supplied
as workflow, LiteGraph, run-state, schedule, policy, or remote-operation
inputs.

## Contract

The generic JSON file loader accepts at most `8,388,608` bytes (`8 MiB`) of
UTF-8 input. It checks the file size before opening it, reads at most one byte
past the limit, and rejects a file that grows between those two operations.
The parser never receives an unbounded byte stream.

The loader rejects invalid UTF-8 and malformed JSON with exit status `1` and a
concise stderr message. It does not print a Python traceback for operator input
failures. This is a local file boundary, not a claim that a workflow can
execute arbitrary-size values in memory.

Domain-specific limits remain stricter where they already exist:

- trigger input keeps its canonical 1 MiB JSON-object contract;
- one-shot schedule files keep their 2 MiB persisted-document contract;
- authenticated service request bodies keep their documented request limits.

Those contracts are evaluated after the generic file boundary and are not
weakened by this loop.

## Scope and exclusions

This boundary applies to JSON operands loaded by the installed CLI, including
`validate`, `visualize`, `write-back`, `run`, `bundle-preflight`,
`bundle-run --input`, `publish`, retention policy commands, and protected
service clients. Bundle input then passes through the stricter 1 MiB trigger
object boundary and the side-effect-free preflight contract. It does not
change Workflow DSL schema compatibility, JSON/SQLite state storage, service
HTTP framing, or credential-provider semantics. It also does not turn local
file inputs into a multi-tenant or remotely trusted upload surface.

The limit is intentionally fixed in the source and is covered by regression
tests. Operators who need larger authored workflows should split the workflow
or use a separately approved compatibility change rather than bypassing the
loader.
