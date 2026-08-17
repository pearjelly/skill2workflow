# Workflow Explanation

Loop 178 adds a side-effect-free execution plan for a Workflow DSL artifact.
It is the operator checkpoint between authoring/release review and a real
trigger: it explains the graph and runtime policy without executing a node,
resolving a credential, or calling a connector.

## Local CLI

For a local draft or release candidate:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli explain \
  examples/workflows/http-connector.workflow.json
PYTHONPATH=src python3 -m skill2workflow.cli explain \
  examples/workflows/http-connector.workflow.json --format text
```

The JSON result uses the fixed
`skill2workflow-workflow-explanation-0.1.0` contract in
[`schemas/workflow-explanation-0.1.0.schema.json`](../schemas/workflow-explanation-0.1.0.schema.json).
The text form is a presentation of the same result and is not an execution
input.

## Remote published version

An authenticated self-hosted operator can inspect an immutable published
version before triggering it:

```bash
skill2workflow service-workflow-explain workflow_http_connector \
  --version 0.1.0 \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The service route is:

```text
GET /api/v1/workflow-explanations/{workflow_id}/{version}
Authorization: Bearer <single-team-token>
```

The request must have an empty body. It requires only the protected operator
token, does not acquire the scheduler lease, and does not append audit events
or mutate workflow state. Missing versions return a fixed `404`; malformed
bodies return a fixed `400`; unreadable artifacts return a fixed `503`.

## Contract and redaction

The explanation includes only:

- immutable workflow id/version/status and the entry node;
- node ids and types, declared success/failure/fallback transitions, connector
  id/kind/method, credential and input-mapping counts, retry/timeout policy;
- edge endpoints, fixed labels, and whether a condition exists;
- top-level input property names, types, required flags, and nested markers;
- aggregate counts and the default/workflow timeout and retry policies.

It deliberately excludes node titles/descriptions/instructions, connector URLs,
headers, bodies, mapping values, enum values, resolved credentials, trigger
inputs, and raw condition expressions. The fixed safety marker states that the
operation is side-effect free, made no connector calls, resolved no
credentials, and included no raw values.

The complete response is limited to 64 KiB, 1,000 nodes, 2,000 edges, and 128
top-level input properties. The builder fails closed when a valid artifact
cannot fit those bounds; it never returns a misleading partial plan.

## Verification

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_explain \
  tests.test_workflow_explanation_remote \
  tests.test_service.RuntimeServiceTests.test_remote_workflow_explanation_is_authenticated_bounded_and_value_free \
  -v
```

The explanation is a review aid, not a second workflow authority. Workflow DSL
remains the only execution source of truth.
