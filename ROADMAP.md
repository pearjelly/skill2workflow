# Roadmap

## Current maturity

**Self-hosted Beta**, for a single instance and one tenant. The published
package is `v0.1.0`; the improvements below are unreleased. Production Baseline
remains a future gate, requiring sustained operating evidence.

Workflow DSL is the execution truth source. The LiteGraph editor is a view and
an authoring tool. Python 3.9 and a standard-library-only runtime remain the
baseline. The [approved design](docs/superpowers/specs/2026-07-01-skill2workflow-design.md)
continues to guide the product.

## Available now

- DSL `0.1.0` remains supported; DSL `0.2.0` adds DAG decision branches over
  persisted input and connector output, plus explicit Agent connectors with
  filtered dependencies and validated structured results.
- HTTP requests, executable HTTP assertions and human approvals are enforced.
  Plain instructions, steps and verification prose are visibly descriptive.
  Agent execution uses an explicitly registered external adapter; the repository
  supplies a deterministic example, with no LLM SDK dependency.
- CLI state defaults to SQLite. Explicit JSON remains supported. The service
  provides authenticated ingress, durable schedules, pause/resume, cancellation,
  audit, backup/restore and recovery for one instance.
- The original licensed corpus has 24 Skills and 96 process nodes: inference
  accuracy 100%, false human gates 0, enforced coverage 51.04%. These metrics
  describe this corpus, not arbitrary community Skills.

## Next goals

Select one delivery loop at a time. Prioritize executable business behavior;
additional boundary work needs a reproduced defect.

| Priority | Goal | Exit criteria |
| --- | --- | --- |
| 1 | Broaden real Skill coverage | At least 40 licensed Skills, 100% expected type accuracy, zero false human gates, and at least 65% enforced coverage, with independent expectations and end-to-end examples. |
| 2 | Validate a real Agent adapter | One external provider adapter completes a fixed business task set through structured output, decision and human approval; restart/resume and failed output validation are demonstrated. |
| 3 | Complete visual authoring | Authors can review and edit decision branches and Agent contracts, publish, and inspect outcomes through the editor without manually editing JSON; DSL/graph round trips preserve execution semantics. |
| 4 | Qualify Production Baseline | One team supplies 30 consecutive days of operation, incident records, and demonstrated restart plus backup/restore recovery; release, upgrade and compatibility gates pass. |

## Evidence and history

Delivery loops 1–285 are preserved in the [history archive](docs/loops/history.md).
The [improvement ledger](docs/improvement-implementation.md) records T0–T14,
tests and installed-artifact evidence. The [task guide](docs/README.md),
[API reference](docs/api-reference.md) and [command reference](docs/reference.md#command-reference)
are the current contributor and operator entry points.

Future work must preserve published Workflow DSL compatibility or define a
reviewed versioned migration. Do not claim exactly-once external execution,
multi-node coordination or general live SaaS readiness from the local drills.
