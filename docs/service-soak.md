# Service Soak And Cutover Evidence

Loop 151 adds a bounded, repeatable operating drill for the self-hosted
service. It is designed to catch regressions that a single startup smoke can
miss: repeated process cutovers, durable trigger replay, idempotency conflicts,
and state/audit continuity across restarts.

## Evidence command

```bash
python3 scripts/service_soak_smoke.py \
  --work-dir /tmp/skill2workflow-service-soak \
  --cycles 3 \
  --triggers-per-cycle 6
```

Each cycle starts a real service process against the same SQLite directory,
waits for `/readyz`, checks `/healthz`, submits six authenticated trigger
requests, replays one request with the same idempotency key, and sends a
conflicting request with the same key and different input. It then performs a
graceful `SIGTERM` cutover and checks that every persisted run is completed.
After the final cutover it starts one more process to verify authenticated
audit integrity and audit consistency diagnostics.

The defaults are intentionally bounded: three cycles, six triggers per cycle,
at most eight cycles, and at most 128 total triggers. The workflow is a local
start-to-end fixture; it never calls an external provider or uses a live
credential.

## Evidence contract

The command writes `service-soak-smoke.json` with schema
`skill2workflow-service-soak-evidence-0.1.0`. It contains only booleans,
cycle/trigger counts, restart counts, and the persisted run count. It does not
write run identifiers, input values, token values, paths, or operational log
contents. A successful report proves the bounded drill passed; it does not
claim indefinite capacity, zero downtime, exactly-once provider effects, or
disaster recovery.

## Release integration

The `operational-gates` CI job runs the same three-cycle drill on Python 3.14.
Contributors and release operators should run it after service, scheduler,
SQLite, or request-boundary changes. The existing two-cycle
`service_boundary_smoke.py` remains the smaller continuity check; this drill
adds repeated cutovers and idempotency behavior without changing the runtime
contracts.

## Operating boundary

The service remains one loopback-bound, single-tenant process with an external
TLS boundary and a cooperative scheduler lease. The soak is deterministic
local evidence, not a load test, performance target, hosted availability
claim, multi-process scale claim, or external side-effect reconciliation.
