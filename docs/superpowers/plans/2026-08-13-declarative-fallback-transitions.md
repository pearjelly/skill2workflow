# Loop 64: Declarative Fallback Transitions

**Status:** Complete.

**Goal:** Let a connector failure enter an explicitly authored recovery path
without hiding the failed attempt or synthesizing another provider call.

## Contract

- A nonterminal `tool_call` may declare an optional `on_fallback` target.
- The target must be an existing node and must have a matching Workflow DSL
  edge. Only `tool_call` nodes may declare the field.
- The executor uses the fallback only after all declared connector retries are
  exhausted. The failed node result, connector metadata, `connector_failed`,
  and `node_failed` evidence remain durable.
- The executor records `node_fallback` with the explicit target and continues
  from that node. It never invokes an alternate provider automatically and it
  never claims exactly-once side effects.
- LiteGraph exposes a third `fallback` output slot while preserving the DSL as
  the topology authority.

## Exclusions

This loop does not add provider failover, automatic compensation, retry
backoff, queues, arbitrary expression evaluation, hidden transition mutation,
or exactly-once execution. Existing `on_failure` behavior remains unchanged
when `on_fallback` is absent.

## Evidence

The contract is documented in [`docs/workflow-dsl-contract.md`](../../workflow-dsl-contract.md),
[`docs/runtime-policy.md`](../../runtime-policy.md), and the versioned schema.
Compiler tests cover target and edge validation; executor and control-plane
tests cover failed-attempt preservation and fixed audit promotion; visualizer
tests cover the fallback output slot. Full-suite and package checks remain
release gates.
