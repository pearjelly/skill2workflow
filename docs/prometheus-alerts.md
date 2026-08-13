# Prometheus Alert Rules

The repository includes a dependency-free starter pack at
[`examples/observability/prometheus-alerts.yml`](../examples/observability/prometheus-alerts.yml)
for the fixed service metrics documented in [`observability.md`](observability.md).
It is an operator-owned configuration artifact, not a service route or an
automatic alerting integration.

## Install

Copy the file into the Prometheus rules directory or reference it from the
operator-managed `rule_files` configuration, then run the Prometheus rule
validation appropriate for the target version before reload. Keep the
notification receivers, routing, silences, and retention policy outside this
repository.

The rules intentionally use only the service's fixed labels:

- `Skill2WorkflowServiceNotReady` fires when the fixed readiness gauge remains
  false for five minutes.
- `Skill2WorkflowSchedulerLeaseLost` fires when a ready process has not owned
  the recurring scheduler lease for two minutes.
- `Skill2WorkflowUncertainDispatch` fires when durable dispatch evidence reports
  an uncertain external outcome. Operators must follow the recovery procedure;
  the alert is not permission to replay the task.
- `Skill2WorkflowBusinessRequestSaturation` fires when all 16 fixed request
  admission slots remain occupied for five minutes.
- `Skill2WorkflowHttp5xxResponses` fires after any server-class response in the
  last five minutes.

## Safety boundary

These rules are signals, not execution controls. They do not cancel runs,
retry provider calls, mutate schedules, or change service lifecycle state.
`skill2workflow_schedule_dispatches{status="uncertain"}` represents an
unknown external outcome; use the documented dispatch inspection and operator
retry semantics before taking any business action. The rule file contains no
credentials, workflow values, run identifiers, or provider payloads.

The fixed request-admission threshold is 16, matching
`MAX_CONCURRENT_BUSINESS_REQUESTS`. If a future compatible release changes that
constant, update this starter pack and its operator review together.

## Verification

The repository smoke checks the file's required groups, alert names, fixed
metric vocabulary, bounded labels, and absence of credential-like values:

```bash
python3 scripts/observability_rules_smoke.py
```

Prometheus itself remains the authority for parsing and evaluating the rule
file; run its version-specific `promtool check rules` command during deployment.
