# Loop 284: Preflight Input Admission Boundary

## Evidence And Scope

Previous progress is verified: clean main `896cfbd` and all seven exact CI jobs
passed. Open issues are empty. A local reproduction passes a JSON object over
the shared 1 MiB canonical input limit to ordinary preflight: it reports ready,
while trigger normalization rejects the same object. Bundle, quickstart and
editor paths already normalize inputs, but the shared report builder does not.
An authenticated service request can also expand above the canonical bound
after parsing even while its compact numeric wire representation fits.

Make preflight use the existing canonical input normalization and its exact
UTF-8 byte bound, preserving the stronger finite-JSON requirement and fixed,
source-free refusal. Normalize before schema/mapping analysis. Reject invalid
service input as an existing fixed 400 request refusal, not an internal 503;
clients must refuse invalid supplied input before token reads or network I/O.
Omitted input remains `{}` and ignores an unused Python argument as before.

No readiness/result schema or issue vocabulary changes, no runtime admission
change, no raised wire/body/CLI/file limits, no provider/credential lookup,
state mutation, publication or execution is added. Reports remain admission
hints, not proof of provider/credential availability or workflow success.
No frontend or CSS change; no new dependency, version, release or maturity.

## Acceptance

Start with failing shared-builder, CLI, client-before-I/O and real service tests.
Cover exact canonical limit and one byte over, ASCII and multibyte text,
compact numeric expansion, nonfinite/unencodable/cyclic values, omitted input,
unchanged schema/mapping reports, source-free failures and no state/audit writes.
Keep ordinary JSON wire-size enforcement independent of canonical input size.

Require a separate actual installed-CLI qualification in wheel smoke: compile,
publish, exact-limit preflight/trigger, oversize preflight/trigger refusals,
multibyte/canonical-expansion checks and unchanged run/audit inventory after
refused work. Source imports/help markers cannot qualify the installed path.
Run full Python/Node, isolated wheel, hygiene, exact feature CI seven jobs and
full production-baseline release preflight, then roadmap closure and exact CI.
Keep the broad goal active.

## Local Qualification

The baseline builder returned ready for an over-limit object that trigger
normalization rejected. New boundary tests failed before implementation;
the real authenticated service returned 200 instead of the required fixed
400 for a compact numeric input whose canonical form exceeds 1 MiB.
The required installed-gate contract also failed before its helper existed.

Final local checks passed: 1,490 Python tests in 112.943 seconds, all 64 editor
tests, Python compilation and focused report/client/real-service/documentation
checks. The final real-service extension separately proves nonfinite input
uses fixed 400 refusal and preserves audit inventory. No frontend change.

The isolated 96-member wheel passed with SHA-256
`ac9aef8f4c753377c131fa3ff34a4d044cf64e4ce60b0c4bc3d855d0c0c7da3a`.
A separate run of the selected installed CLI passed all eight mandatory
checks, including an exact-limit trigger actually reaching its gate and
unchanged run/audit inventory after rejected work. The installed preflight
module byte-matches source. The same current qualifier correctly rejected
the previous installed wheel while the current source passed, proving no
source substitution. Whole-repository secret hygiene passed.

## Remote Feature Qualification And Closure

Feature commit `e8723d0ddc666c0b9f5920a825f6f72b2cc264a6` passed all seven
completed jobs in [CI run 39825998518](https://github.com/pearjelly/skill2workflow/actions/runs/39825998518),
attempt 1. Python 3.9 passed 1,490 tests in 122.626 seconds; Python 3.14 passed
them in 119.821 seconds. Their package checks and the separate artifact job
require the actual installed-CLI boundary qualifier, not source imports.

[Release-preflight run 39826020053](https://github.com/pearjelly/skill2workflow/actions/runs/39826020053)
completed with success on the same exact feature commit, attempt 1, using
Python 3.9.25. Complete logs confirm unit tests, Python compilation, installed
wheel, reproducible wheel and full `production_baseline` command passed. Only
the documented dry-run git/tag availability checks were skipped. No rerun,
cancellation or duplicate dispatch was needed.

The documentation-only closure advances existing completed-loop assertions and
adds the Loop 284 outcome; the new roadmap assertions first failed before the
entry existed. All 1,490 local closure tests passed in 111.444 seconds and
whole-repository secret hygiene passed. All seven exact pushed-commit CI jobs
remain required before handoff. No UI/runtime follow-up, PR, release, tag,
version or maturity promotion. The broad iterative goal remains active.
