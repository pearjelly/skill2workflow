# Workflow trigger preflight

Trigger preflight answers whether a JSON object satisfies a workflow's
published input contract and whether HTTP request mappings have all required
source fields. Query-target scalar conversion remains an execution-time
connector check. It is an admission check, not a dry-run: it never starts a run,
calls a connector, resolves a credential, writes state, or includes input
values in its result.

The fixed result is `skill2workflow-workflow-preflight-0.1.0`, documented by
[`schemas/workflow-preflight-0.1.0.schema.json`](../schemas/workflow-preflight-0.1.0.schema.json).

## Local draft check

```bash
PYTHONPATH=src python3 -m skill2workflow.cli preflight \
  examples/workflows/http-connector.workflow.json

PYTHONPATH=src python3 -m skill2workflow.cli preflight \
  examples/workflows/http-connector.workflow.json \
  --input /path/to/trigger-input.json --format text
```

Without `--input`, preflight validates an empty object and reports
`provided: false`. A non-zero exit means `ready` is false; the JSON or text
report remains safe to share with an operator because it contains counts,
stable issue codes, and paths only.

## Quickstart source preview

For an uncompiled local Skill, `quickstart --skill SKILL.md --input input.json
--root /absolute/unused-root --dry-run` returns this same report after checking
the quickstart approval and location boundaries. It creates no workspace and
does not start a run. Real quickstart initialization also requires ready input
and mappings; general trigger admission is unchanged. See
[quickstart preview](quickstart.md#preview-before-creating-a-workspace).

## Published service check

The authenticated client calls:

```text
POST /api/v1/workflow-preflights/{workflow_id}/{version}
```

The body is either `{}` or `{"input": <object>}`. The route is available
before runtime readiness, is bounded to the normal service request limit, and
does not append an audit event because it has no durable or external side
effect. Unknown workflow versions return the same fixed 404 contract as the
other published-version inspection routes.

```bash
skill2workflow service-workflow-preflight workflow_http_connector \
  --version 0.1.0 --service-url http://127.0.0.1:8080 \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --input /path/to/trigger-input.json
```

The report includes per-node mapping status (`not_applicable`, `ready`,
`skipped`, or `blocked`), connector and credential-handle counts, and a fixed
safety block proving that no connector call or credential resolution occurred.
It deliberately does not inspect credential stores or external connector
preflight hooks; those remain execution-time concerns.
