# Runtime Policy And Recovery

This document describes the local runtime policy behavior currently implemented by `skill2workflow`.

Workflow DSL remains the execution truth source. Runtime policy fields are read from workflow nodes and top-level workflow policies; visual graphs can edit allowlisted fields only after writing back to Workflow DSL.

## Retry Semantics

Connector nodes can declare retry policy:

```json
{
  "id": "call_api",
  "type": "tool_call",
  "retry": {
    "max_attempts": 1,
    "backoff_ms": 250
  }
}
```

`retry.max_attempts` means retries after the first attempt. A value of `1` allows at most two total connector executions: the first attempt and one retry.
`retry.backoff_ms` is an optional fixed delay before each retry. It is bounded
to 60,000 milliseconds; values above the bound are clamped for legacy
documents. The default is `0`, preserving immediate retries when no delay is
declared. This bounded connector retry backoff is intentionally fixed rather
than exponential. Node policy takes precedence over `policies.default_retry`.

If a node does not declare `retry.max_attempts`, the executor falls back to:

```json
{
  "policies": {
    "default_retry": {
      "max_attempts": 0
    }
  }
}
```

Missing, invalid, negative, and boolean retry values are treated as `0`;
legacy `backoff_ms` values above the bound are clamped to `60000`.

## Timeout Boundary

`connector.request.timeout_ms` is the built-in HTTP connector request timeout. The
top-level `policies.default_timeout_ms` is a separate active-execution segment
budget: `0` disables it, positive values are bounded to 24 hours, and the
executor checks it before each node and after connector returns. A timeout
fails the run with fixed `error_code: "execution_timeout"` evidence; it never
interrupts an outbound request already in flight. The budget is persisted with
the run and is cleared while a human gate is waiting, so operator review time
does not consume execution budget. It does not cover queueing, downstream
systems after a returned connector call, or local process scheduling.

`policies.workflow_timeout_ms` is an optional global wall-clock deadline for the
whole run. `0` disables it; positive values are bounded to 30 days and start
when the run is created. Unlike `default_timeout_ms`, the global deadline keeps
running while a human gate is waiting and fails closed with fixed
`error_code: "workflow_timeout"` evidence when the operator resumes after the
deadline. The executor checks it before each node, after connector returns, and
after retry backoff. It is persisted in the run's internal execution state and
cleared only at terminal completion, cancellation, or failure. It cannot
forcefully interrupt a provider call already in flight, and it does not provide
background expiry when used as a standalone local executor. The self-hosted
SQLite service adds a bounded deadline sweep on the active scheduler lease:
roughly once per second it atomically expires waiting runs whose deadline has
passed, records the same fixed failure evidence, and reconciles the terminal
audit event. A pending cancellation wins over expiry. The sweep is capped at
256 candidates per pass and never resumes the workflow or executes a successor.

The local executor does not yet implement node-level wall-clock deadlines or
general scheduled recovery. A configured retry backoff is part of the active
execution segment and is checked against `default_timeout_ms` after the delay.

## Fallback Transitions

Connector failures normally follow `on_failure`. A `tool_call` can instead
declare an explicit `on_fallback` edge for a controlled alternate path:

- all declared retries run first;
- the failed node result, connector attempt metadata, and `node_failed` event
  remain durable;
- `node_fallback` records the target and the executor continues there;
- no alternate provider call is synthesized and no failed output is erased.

Use a fallback node for a safe notification, manual escalation, or compensating
workflow step. It is not an exactly-once guarantee and it must not be used to
blindly repeat an effect whose provider outcome is unknown.

## Run Events

The executor records policy and recovery visibility in run state:

| Event | Meaning |
| --- | --- |
| `connector_started` | A connector attempt started. Includes `attempt` and `max_attempts`. |
| `connector_failed` | A connector attempt failed. Includes connector metadata, `attempt`, `max_attempts`, and `error`. |
| `node_retrying` | A failed connector node will be retried. Includes `attempt`, `next_attempt`, `max_attempts`, `backoff_ms`, and `error`. |
| `node_recovered` | A connector node succeeded after at least one failed attempt. Includes final `attempt`, `max_attempts`, and last error. |
| `node_failed` | A connector node failed after exhausting available retry attempts; it may still route through `on_fallback`. |
| `node_fallback` | A failed connector node routed to its explicit `on_fallback` target after retries were exhausted. |
| `run_interrupted` | A replacement service fenced an active execution owned by a lost process. The external outcome is unknown and no automatic retry occurs. |

Node results for connector nodes include:

```json
{
  "status": "completed",
  "attempts": 2,
  "max_attempts": 1,
  "backoff_ms": 250,
  "last_error": "HTTP 503"
}
```

`last_error` is present only when an earlier failed attempt exists.

## Control-Plane Audit

Published runs promote connector and runtime policy events into control-plane audit logs.

Useful filters:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --event-type node_retrying
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --event-type node_recovered
PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --event-type node_failed
```

The audit events include workflow identity, run id, node id, attempt metadata, and error text when available.

## Current Limits

The local runtime intentionally does not yet provide:

- background workers
- distributed scheduling
- automatic idempotency enforcement for JSON/local evaluation (SQLite service enforcement is documented in `docs/triggers.md`)
- compensation or rollback handlers
- node-level wall-clock deadlines
- enterprise credential management
- secret injection or redaction

For local pilots, use deterministic test endpoints and non-sensitive example data. Keep secrets out of Workflow DSL and follow `docs/credential-boundary.md` for allowed placeholder patterns and fixture hygiene checks.
