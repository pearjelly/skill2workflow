# Loop 70: Published Artifact Integrity Guard

## Goal

Close the production-baseline gap where a published artifact checksum is
stored in the control registry but not checked again when the artifact is read
for execution or promotion.

## Design

- Keep the Workflow DSL and published artifact layout unchanged.
- Make `LocalControlPlane.get_workflow()` load the referenced JSON, normalize
  read/parse failures to a fixed redacted error, require a registry checksum,
  and compare the canonical JSON checksum before returning the value.
- Have `promote_workflow()` verify the target artifact before changing alias
  metadata or appending promotion evidence.
- Reuse the existing `get_workflow()` path so exact-version runs, alias
  triggers, webhooks, and schedules share one pre-execution guard.
- Fail closed for missing checksums; never synthesize a checksum from an
  artifact at read time.

## Tests

- Tampering with a published JSON artifact rejects direct reads, published
  runs, and keyed SQLite triggers before run or idempotency state is created.
- Tampering with a release target rejects promotion and leaves the existing
  alias and audit evidence unchanged.
- Existing JSON/SQLite publication, backup/restore, scheduling, and trigger
  compatibility tests remain green.

## Documentation

Document the fixed failure boundary and operator response in
`docs/published-artifact-integrity.md`, then update the roadmap, stability and
compatibility contracts, README, HARNESS, and changelog. This loop does not add
signatures, remote attestation, automatic repair, or multi-tenant isolation.

## Verification

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src scripts
git diff --check
python3 scripts/secret_hygiene.py examples/workflows
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke-loop70
python3 scripts/service_boundary_smoke.py --work-dir /tmp/skill2workflow-service-boundary-loop70
```
