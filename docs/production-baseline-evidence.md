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
soak. Check execution shares one 600-second monotonic budget. Each check receives
the smaller of 180 seconds and the remaining suite budget, including time spent
starting its process. The absolute shared deadline is passed through rather
than restarted during command preparation. Exhausted budgets launch no child:
not-yet-admitted entries are `skipped` with `suite_timeout`, and the bundle fails.
An admitted check that loses its budget during preparation is a failed timeout
without process creation. A zero exit observed after its deadline is also a
timeout, not a pass.

Each built-in check runs in its own POSIX session/process group. On a running
check's timeout or interruption, the supervisor sends SIGKILL only to that owned
group and waits up to five seconds to reap its direct child before cleaning the
known child work directory. This covers ordinary descendants that inherit the
group, not a program that deliberately detaches, arbitrary process trees or a
container/host security boundary. Safe process-group supervision is required
before launch; this qualification path is verified on Linux/macOS, not Windows.

The 600 seconds bound check execution, not an absolute wall-clock guarantee over
OS scheduling, process creation stalls, reap handling or filesystem cleanup.
Reap handling and directory/evidence writes can add wall time. The legacy
injected command runner exists for unit tests; the CLI/release path always uses
the built-in supervisor, not an untrusted runner's claimed verdict.

Owned HTTP test fixtures use the shared test-only short-polling servers from
`tests/http_fixtures.py`. They still perform real protocol requests and ordinary
joined shutdown/close; only avoidable idle teardown waits are shortened.
Production server classes, check membership, assertions and the 180/600-second
guards are unchanged. Faster fixture teardown adds deadline headroom, but does
not prove the cause of an earlier timing failure or guarantee future CI timing.

Known child artifacts are removed after a check has stopped. If group signaling
or direct-child reaping cannot be confirmed, the bundle stops immediately with a
fixed cleanup error and preserves the owner-only work directory; no successful
evidence is written and later checks are not launched. Inspect that directory
and any surviving processes before operator cleanup. This does not search for
or delete arbitrary temporary files created elsewhere by a check.
After an ordinary completed bundle, the final directory contains
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

The 19-check bundle does not build or run the optional Linux Docker image.
For a Docker deployment or image release review, also run the independent
[`docker_service_smoke.py` gate](docker-self-host.md) on a local Linux Docker
Engine (or require its dedicated CI job). A passing baseline bundle alone is
not Docker deployment evidence.

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
