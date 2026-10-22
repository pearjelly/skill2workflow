# Loop 277: Fast HTTP Test Fixture Teardown

## Evidence And Scope

The previous loop is verified progress: fixed UI asset admission shipped with
complete CI and same-code release-preflight retry evidence. The current checkout
is clean at `e140119`, final CI is green, and the open issue inventory is empty.
Roadmap selection explicitly calls for investigation of release-gate timing.

The first Loop 276 production-baseline unit replay exceeded its unchanged
180-second command deadline, while the same commit's Python 3.9 CI unit suite
completed in 151.836 seconds and release attempt 2 passed without code changes.
That evidence does not identify the exact cause of the failed run. CI timing
also shows the installed quickstart/build drill at about 44 seconds; packaging
and runner variability remain separate possible contributors.

Source inspection finds 108 HTTP server construction sites across eleven test
modules, plus the new static-boundary fixture. A controlled eight-sample HTTP
request/teardown experiment found the default 0.5-second polling shutdown at
about 0.502 seconds in seven samples (one shutdown raced ahead of the wait).
With 0.01-second polling, samples were 0.0001–0.012 seconds. This is a proven
avoidable cost, not proof that it alone caused the remote timeout.

Introduce test-only HTTPServer/ThreadingHTTPServer subclasses with the short
poll interval, preserving explicit caller intervals and all inherited behavior.
Use them for owned HTTP fixtures; scope any UI-server substitution to the test
context. Keep actual network requests, assertions, protocol behavior, service
timeouts, production classes and the 180/600-second baseline guards unchanged.
Do not skip integration tests, cache/reuse installed qualification, or increase
deadlines to obtain a pass.

## Verification

Write helper contract tests first: default/explicit interval forwarding, actual
HTTP response and joined shutdown, stdlib/production class identity, and fixture
wiring. Record a correctly configured complete pre-change timing run and compare
post-change full-suite timing without claiming a controlled CI speedup from one
sample. Keep every existing test and qualify installed packaging, editor tests,
all seven CI jobs and the complete production-baseline release preflight.

The temporary first profiling harness lacked the repository root on its import
path and did not load the complete suite. Its 1,332-test failed diagnostic run
is excluded from full-suite qualification; the corrected harness must discover
the authoritative full test count before comparison.

No runtime dependencies, product semantics, Workflow DSL, release/tag or maturity
change. The broad project goal remains active.

## Pre-change Measurement

The corrected complete timing run discovered all 1,431 tests and passed in
132.606 seconds. Seventy-one tests took 0.45–0.65 seconds. Module totals included
15.540 seconds for UI proxy tests, 6.413 seconds for connectors, 5.804 seconds
for CLI tests and 4.647 seconds for the static boundary. The quickstart module
still dominated at 35.509 seconds, mostly its installed-wheel drill; that
independent cost is deliberately not removed or cached in this loop.

The helper tests first failed because the new module did not exist. The initial
helper plus all eleven static-boundary regressions then passed 14 tests in
0.308 seconds, including actual requests, refusal/race checks and joined cleanup.
No original assertion or test method was removed.

The shared fixtures live in an explicit repository-local `tests` package so
both discovery and named-module commands resolve the same support module rather
than an unrelated installed `tests` package. A regression first failed against
the prior implicit namespace, then passed with that local package identity.

## Post-change Measurement

The instrumented post-change suite passed all 1,434 tests in 98.273 seconds.
Tests in the 0.45–0.65-second band fell from 71 to 11. UI tests fell from
15.540 to 1.190 seconds; the quickstart module remained near its prior cost
(35.509 versus 34.751 seconds), and real service/recovery drills remained.
The observed total reduction was 34.333 seconds, about 26%; this before/after
observation is not a controlled performance guarantee or proof of the original
remote timeout's sole cause. Final-source standard discovery, installed wheel
qualification and remote release checks remain required independently.

## Final Local Qualification

After the final local-package identity guard, the ordinary documented command
passed all 1,434 tests in 98.775 seconds. All 30 editor regressions passed. No
existing test method or assertion was removed, and the only original test edits
are fixture imports plus the scoped static-UI server substitution.

The isolated wheel passed its complete qualification with 94 members, SHA-256
`11ca2b88a1c05c09237b8e94dc2952aeed9124d2e966b41039df85f46d711420`,
at `/tmp/skill2workflow-package-loop277-final`. Every installed runtime Python
module matches source byte-for-byte. No source runtime, web asset, package
configuration, build/release script or baseline deadline was changed. The test
support package is not distributed in the wheel. Repository secret hygiene and
whitespace checks passed; all owned fixture processes/listeners were closed.

## Remote Qualification

Qualified implementation: `e33326fc63b1d5e52647e9b19d1fa8a8df260675`.
[CI](https://github.com/pearjelly/skill2workflow/actions/runs/39782588784)
passed all seven jobs, including Python 3.9/3.14, unchanged installed qualification,
real user journeys, editor regressions, Docker, systemd and recovery/state safety.
The job logs report all 1,434 tests passing in 123.895 seconds on Python 3.9
and 101.230 seconds on Python 3.14. These are observed runner timings, not a
controlled cross-run comparison or a promised CI latency.
[Release preflight](https://github.com/pearjelly/skill2workflow/actions/runs/39782634553)
passed on its first attempt in 6m19s with Python 3.9.25. The terminal job log
explicitly records `PASSED command:production_baseline`. All check membership
and deadlines remain unchanged. A passing run is evidence for this commit,
not proof that all future runner timing variance has been eliminated.

Roadmap closure passed 109 focused feature/documentation tests in 0.684 seconds,
plus repository secret hygiene and whitespace checks. No tag, package release,
live-provider operation or maturity promotion was performed. The broad project
goal remains active.
