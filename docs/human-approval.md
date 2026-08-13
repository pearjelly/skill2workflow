# Authenticated Human-Gate Decisions

The self-hosted service can expose a waiting `human_gate` as one narrow,
authenticated decision boundary. An operator may approve or reject exactly one
waiting run; the existing durable executor then follows the workflow's
declared `on_success` or `on_failure` transition.

This is a single-tenant control-plane capability. It is not a hosted approval
product, a multi-tenant identity layer, or a replacement for the external TLS
and access-control boundary described in [`security-boundary.md`](security-boundary.md).

## Endpoint

```http
POST /runs/{run_id}/resume
Authorization: Bearer <service-ingress-token>
Content-Type: application/json
```

The request body must be exactly one JSON object with one boolean field:

```json
{"approved": true}
```

`false` rejects the gate. Extra fields, missing fields, non-boolean values,
empty bodies, malformed JSON, and oversized or ambiguous HTTP bodies are
rejected. The body intentionally does not accept a free-form reason or an
operator-supplied identity: the service's authenticated ingress audit records
the request class, while the durable run audit records the boolean decision.

On success the service returns a compact result:

```json
{"run_id": "run_example", "status": "completed", "approved": true}
```

The status is the resulting run status and may be `completed`, `failed`, or
another non-terminal status when the resumed workflow continues to a later
node.

## Failure contract

- `401` means the Bearer token is missing or invalid. `503` means the token
  provider is unavailable or the service is not ready.
- `400` means the decision body is invalid.
- `404` means the run does not exist in the published control plane.
- `409` means the run is no longer waiting at a human gate. Repeating a
  decision never replays a completed run.

The endpoint delegates to the same `LocalControlPlane.resume_published_run`
and executor path used by the CLI. It therefore preserves waiting-only checks,
durable `run_resumed` audit evidence, the declared success/failure branch, and
connector retry policy. It does not claim exactly-once effects for a provider
request that was already sent before a process failure.

Run state and control audit are separate SQLite databases. If the gate decision
is committed but the audit transaction fails, the request can return `503`
after the run has already advanced. Retrying the same boolean decision is safe:
the control plane recognizes the committed `human_gate_resumed` event and
repairs only missing bounded audit evidence; it does not execute the gate a
second time. If the decision has already been fully audited, the normal `409`
non-waiting response remains in force. When a resumed workflow reaches a later
human gate, repair of an earlier evidence gap is completed before accepting the
later decision.

## Example

Keep the token outside source files and avoid putting real secrets in shell
history. Replace the placeholders below through your deployment's secret
manager or an owner-only environment:

```bash
curl -sS -X POST \
  "https://service.example/runs/run_example/resume" \
  -H "Authorization: Bearer ${SKILL2WORKFLOW_INGRESS_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"approved":true}'
```

Terminate TLS and apply team authentication, authorization, rate limiting, and
audit retention at the deployment boundary. The built-in service authenticates
one mounted Bearer secret and deliberately does not implement multi-user RBAC.

## Protected CLI client

An installed operator can use the same boundary without placing the token in
the command line or writing request JSON by hand. The CLI reads the token from
the owner-only file, disables proxy and redirect handling, validates the
service origin, and prints only the compact response:

```bash
skill2workflow service-resume run_example \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-resume run_example --reject \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token

skill2workflow service-cancel run_example \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The client refuses remote plain HTTP, embedded URL credentials, query strings,
redirects, oversized or non-JSON responses, and unsafe run identifiers. It
does not retry a decision or cancellation automatically.

Before choosing a run, use the authenticated, redacted [`service-runs`](run-list.md)
client to discover candidates, then [`service-show`](run-detail.md) to inspect
one run without fetching the full control snapshot:

```bash
skill2workflow service-show run_example \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

For incident handoff, `service-support-bundle` writes one bounded, redacted
diagnostic artifact without exporting the full control snapshot; see
[`support-bundle.md`](support-bundle.md).

## Verification

The real threaded-service regression covers the full route, exact body
contract, auth audit classification, durable resume audit, rejection branch,
and repeat-decision conflict:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service.RuntimeServiceTests.test_authenticated_resume_endpoint_requires_exact_decision_and_reuses_audit_path \
  -v
```

For the complete repository gate, run the test and smoke commands in
[`CONTRIBUTING.md`](../CONTRIBUTING.md).
