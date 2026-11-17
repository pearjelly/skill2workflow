# Explicit Agent connector protocol

Status: reviewed for implementation on 2026-11-16 against improvement report
T5/T6, the decision/data design, and the existing external connector loading
and result contracts. No provider SDK or runtime dependency is introduced.

## Authoring and adapter contract

An Agent is an explicit DSL 0.2.0 `tool_call` with `connector.kind: "agent"`,
an operator-selected external connector ID, `action.kind: "agent_instruction"`,
a nonempty `action.instruction`, `requires: [<node-id>, ...]` and mandatory
`output_schema`. The schema uses the existing bounded object-root JSON Schema
subset used by trigger inputs. Its limits and typed comparisons are reused.

Skill declaration:

```markdown
1. Classify request <!-- skill2workflow: agent {"connector":"deterministic_agent","instruction":"Classify the request","requires":[],"output_schema":{"type":"object","properties":{"risk":{"type":"string","enum":["high","low"]}},"required":["risk"],"additionalProperties":false}} -->
2. Route <!-- skill2workflow: decision {"branches":[{"when":{"path":"/nodes/1/output/risk","equals":"high"},"to":3}],"default":"end"} -->
3. 人工复核 <!-- skill2workflow: human_gate -->
```

`requires` references step numbers, unique titles or generated node IDs in the
Skill; compiled DSL contains only node IDs. Each dependency must exist and
precede the Agent on every incoming path (validator checks graph dominance).
Runtime checks successful durable output again, so an imported legacy state
or a missing result cannot silently supply an empty dependency. A failed
dependency follows the node's normal failure transition without calling an
adapter. No implicit Agent execution is inferred from ordinary prose.

The adapter must be registered through the existing explicit external connector
loader/registry, with a manifest `kind: "agent"`, `node_types: ["tool_call"]`
and `execution_contract.mode: "external"`. Unknown/unregistered adapters fail
normally; DSL cannot load Python or install an SDK. The default service registry
does not gain discovery or dynamic fixture loading.

The adapter's first positional argument is exactly:

```json
{"instruction":"Classify the request","context":{"input":{},"nodes":{"required_node":{"output":{}}}}}
```

It retains the existing optional `credential_provider`/`context` keyword
signature for loading compatibility; the keyword context contains only the
same filtered context. No complete run state, unrelated node output or
execution metadata is supplied. Adapter code is still reviewed local Python,
not sandboxed; filtering defines the data handoff rather than process isolation.

It returns the normal external result envelope (`status`, `output`, optional
compact metadata). The normalized finite JSON envelope retains its 1 MiB
bound. A completed output must satisfy `output_schema` before the runtime
accepts success. Invalid output becomes a failed node, with normal retry /
failure / fallback behavior. No provider values enter audit events.

## Durable structured output

A registered Agent adapter with a validated completed output explicitly opts
into structured business-data retention in `node_results.<id>.output`.
This is a deliberate exception to the default external metadata-only retention
contract, necessary for real Agent work and decision routing. It is gated by
the registered manifest, 0.2 Agent node and output contract together; changing
only a connector kind cannot opt another external connector into retention.
Failed/unvalidated Agent output is not persisted. Credentials remain outside
output and must not be returned by adapters. Normal external connectors keep
their existing projection unchanged.

The decision context and downstream Agent context read this persisted output;
restart/resume never regenerates a successful upstream Agent result. Requires
is enforced for explicit 0.2 Agents only; 0.1 requires and reserved `produces`,
guards, state schema, checkpoints and edge conditions remain descriptive with
validator notices as defined in the decision design.

## Review and acceptance

Review outcome: this protocol makes Agent work executable without shipping a
provider, maintains explicit code-loading authority, and makes structured
retention visible to workflow authors. Dominance prevents depending on the
unselected side of a decision. The adapter owns provider cancellation/timeouts,
as with all external connectors; the runtime keeps its existing bounded
execution and retry mechanisms.

Provide only `examples/connectors/deterministic_agent_connector.py`, using
deterministic lookup/echo behavior for tests. Verify Agent → decision → human
approval end to end, both classifications, JSON and SQLite persistence and a
restart. Verify filtering with an unrelated output, missing dependencies,
schema-invalid output, unregistered adapters and an ordinary external connector
whose output must remain metadata-only. Run full Python/JS suites, corpus,
example sync, secret hygiene and installed CLI fixture loading.
