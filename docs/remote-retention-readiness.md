# Remote Retention Readiness

Loop 92 adds a read-only, policy-bound preflight for the existing local
copy-on-write retention procedure. It lets an operator validate a normalized
retention policy and see whether the service is quiesced before stopping it.
It never deletes, copies, vacuums, uploads, or changes runtime state.

## Route and CLI

```text
POST /api/v1/retention-readiness
Authorization: Bearer <single-team-token>
Content-Type: application/json

{"policy": { ...retention-policy-0.3.0... }}
```

Use the protected client:

```bash
skill2workflow service-retention-readiness \
  /etc/skill2workflow/retention.json \
  --service-url https://service.example \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

## Fixed contract

Responses use `skill2workflow-retention-readiness-0.1.0`, defined by
[`schemas/retention-readiness-0.1.0.schema.json`](../schemas/retention-readiness-0.1.0.schema.json).
The policy is normalized by the same implementation used by local
`state-retention-plan`; its SHA-256 digest and normalized UTC cutoff are
returned so an approval record can bind to the exact policy.

When the scheduler lease is active, the response is `blocked` and all
eligibility counts are `null`. Reading multiple SQLite databases while the
service is writing cannot safely claim to be one retention plan. After the
service is quiesced, the response is `ready` and returns only aggregate counts
for eligible and preserved records. The local `state-retention-plan` remains
authoritative and rechecks the stopped-service boundary immediately before
apply.

Authentication, malformed policy/body, oversized body, and state failures use
fixed `401`, `400`, `413`, and `503` responses. The response is capped at 16 KiB;
the request is capped at 64 KiB by the protected client. The stable support
bundle 0.1.0 projection intentionally omits this route's telemetry counter.

## Safe operating sequence

1. Fetch the report and record its policy digest and status with the retention
   approval.
2. If blocked, drain and stop the service through the host supervisor.
3. Run the local [`state-retention-plan`](data-retention.md#read-only-plan),
   compare its digest and counts, then use the documented copy-on-write apply.

The endpoint exposes no paths, workflow values, run payloads, credentials,
lease-owner identities, or deleted data.

## Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_retention.StateRetentionTests.test_remote_readiness_returns_counts_only_when_state_is_quiesced \
  tests.test_service.RuntimeServiceTests.test_retention_readiness_is_authenticated_bounded_and_blocks_live_service \
  tests.test_service_client.ServiceClientTests.test_retention_readiness_posts_policy_and_validates_fixed_contract \
  tests.test_cli.CliTests.test_service_retention_readiness_command_loads_policy_and_prints_report \
  -v
```
