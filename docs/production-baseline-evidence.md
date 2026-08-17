# Production Baseline Evidence Bundle

Loop 152 gives maintainers one bounded command for reviewing the existing
self-hosted production baseline. It does not add runtime behavior; it makes
the already-approved evidence reproducible as one release decision input.

## Run the bundle

Use a new temporary directory outside the checkout:

```bash
python3 scripts/production_baseline_smoke.py \
  --work-dir /tmp/skill2workflow-production-baseline
```

The command runs 19 fixed checks: the unit suite and Python compilation,
qualified/reproducible wheel checks, secret hygiene, security and
observability drills, service boundary and Doctor checks, backup/upgrade/
retention/cancellation/recovery/scheduling drills, and the three-cycle service
soak. Each check is isolated under an owner-only work directory and is bounded
to 180 seconds; the complete bundle is bounded to ten minutes.

Child artifacts are removed after each check. The final directory contains
only the owner-readable safety marker and `production-baseline-evidence.json`.
If the process is interrupted, treat the directory as sensitive until it has
been inspected and removed by the operator.

## Evidence contract

The JSON output uses schema
`skill2workflow-production-baseline-evidence-0.1.0` and contains only the
fixed check name, pass/fail/skip status, exit code, and timeout flag. It never
includes command output, paths, run identifiers, inputs, credentials, or raw
errors. A failed check is intentionally terse; rerun that named check directly
to inspect its documented diagnostics.

`status: "passed"` proves that this checkout and toolchain passed the bounded
local evidence suite. It is not an independent-builder attestation, hosted
availability claim, disaster-recovery guarantee, exactly-once provider claim,
or automatic maturity promotion.

## Release integration

The release preflight keeps the bundle opt-in because it repeats the full unit
suite and several real-process drills. Add `--production-baseline` when a
release or production-boundary review needs the complete evidence:

```bash
PYTHONPATH=src python3 scripts/release_preflight.py \
  --version <version> \
  --notes docs/releases/v<version>.md \
  --dry-run \
  --production-baseline
```

The release-preflight GitHub Actions workflow enables this flag for
release-related pull requests. The bundle remains local and deterministic; it
does not access live providers or credentials.
