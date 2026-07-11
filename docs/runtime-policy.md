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
    "max_attempts": 1
  }
}
```

`retry.max_attempts` means retries after the first attempt. A value of `1` allows at most two total connector executions: the first attempt and one retry.

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

Missing, invalid, negative, and boolean retry values are treated as `0`.

## Timeout Boundary

`connector.request.timeout_ms` is the built-in HTTP connector request timeout. It is not a whole-workflow deadline and does not cover queueing, human approval, retry backoff, downstream systems, or local process scheduling.

The local executor does not yet implement global workflow deadlines, node-level wall-clock deadlines, delayed retry backoff, or scheduled recovery. Those remain future runtime policy work.

## Run Events

The executor records policy and recovery visibility in run state:

| Event | Meaning |
| --- | --- |
| `connector_started` | A connector attempt started. Includes `attempt` and `max_attempts`. |
| `connector_failed` | A connector attempt failed. Includes connector metadata, `attempt`, `max_attempts`, and `error`. |
| `node_retrying` | A failed connector node will be retried. Includes `attempt`, `next_attempt`, `max_attempts`, and `error`. |
| `node_recovered` | A connector node succeeded after at least one failed attempt. Includes final `attempt`, `max_attempts`, and last error. |
| `node_failed` | A node reached terminal failure after exhausting available retry attempts. |

Node results for connector nodes include:

```json
{
  "status": "completed",
  "attempts": 2,
  "max_attempts": 1,
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
- delayed retry backoff
- idempotency keys
- compensation or rollback handlers
- global workflow deadlines
- enterprise credential management
- secret injection or redaction

For local pilots, use deterministic test endpoints and non-sensitive example data. Keep secrets out of Workflow DSL and follow `docs/credential-boundary.md` for allowed placeholder patterns and fixture hygiene checks.
