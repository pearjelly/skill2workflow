# Loop 274: Quickstart Readiness Preview

## Observed Gap And Scope

Loop 273 validates declared input types but a required HTTP input mapping can
still reference a missing nested field. Quickstart then persists a waiting run
whose approval deterministically fails before its HTTP request. Close that
first-value handoff rather than reporting such a workspace ready for review.

Add `quickstart --dry-run` (Python `dry_run=True`) to compile the same bounded
Skill and finite input, check the same initial approval boundary and workspace
location, and return the existing value-free workflow-preflight contract. Ready
reports exit zero; input or mapping issues produce `ready: false` and exit one.
Malformed source/input and unsafe connector prefixes retain fixed refusals.
No root, token, publication, run, credential resolution or HTTP call is created.
This is a point-in-time local input/mapping preview, not a reservation, provider
health check, service-port probe or approval authority.

Real initialization must pass the same bounded preflight, including required
mapping presence, before bootstrap. Optional mappings remain optional and null
is present. Existing JSON Pointer object/array/escape rules remain authoritative.
No value coercion, schema default, runtime admission or DSL/result-schema change.
The existing preflight limits apply to quickstart readiness as documented.

## Verification

Tests precede CLI and initializer changes. Prove the current missing-mapping
waiting-run behavior without approving or calling an endpoint. Cover omitted
input, typed-but-incomplete nested input, escaped keys/arrays, optional mappings,
explicit null, no root/token/network on preview or refusal, unchanged existing
paths and invalid destination/host/port. Extend mandatory installed-wheel input
qualification and the complete quickstart drill to exercise failed preview,
corrected preview, real admission refusal, and subsequent successful approval.

Run focused tests, the full Python/editor suites, isolated wheel qualification,
all seven remote CI jobs and the complete production-baseline release preflight.
Keep Self-hosted Beta maturity and the broad project goal unchanged.

## Implementation And Local Evidence

Six initial feature tests failed against the prior implementation: required
mapping omissions were accepted into waiting workspaces, and neither CLI nor
Python supported a preview. A later regression also failed on the first preview
CLI branch because it bypassed quickstart's fixed filesystem-error wrapper.
The final branch shares that wrapper and its value-free error.

The initializer now reuses `build_workflow_preflight` before bootstrap. Real
initialization retains existing typed-contract diagnostics and refuses missing
required mapping sources. Preview returns the unmodified preflight contract,
including blocked issue codes, without publishing or executing. The original
bootstrap root/host/port checks were extracted without semantic changes into a
read-only helper; actual bootstrap rechecks instead of trusting a prior preview.

Eight preview tests cover schema/no-schema omissions, nested paths, array and
escaped-key lookup, explicit null, optional sources, finite/byte/property bounds,
unsafe network prefixes, location checks, fixed filesystem errors, CLI exit
status, corrected preview/initialization parity and no token/network creation.
One guide test locks the preview bounds and limitations. Existing quickstart
and bootstrap behavior remains covered. No UI or general preflight/runtime
behavior was changed and no new dependency was added.

The full installed quickstart drill passed 20 checks. The package gate now
requires all seven input/onboarding checks, including a blocked preview, real
refusal with no schema, and a corrected preview using the same unused root.
The existing explicit approval sends exactly one expected request to an owned
loopback receiver. Every receiver/service is closed; no live provider or real
credential was used.

The final isolated wheel passed all qualification with 93 members in
`/tmp/skill2workflow-package-loop274-final`, SHA-256
`effb5bd0dc50e541c891e36d70be509171961b35a748a20980ef94c8cc11fa8d`.
Installed CLI, initializer, bootstrap and qualification modules match source
byte-for-byte. A separate installed bundled preview returned ready while its
requested root remained absent. All 22 editor regressions, repository secret
hygiene and whitespace checks passed.

After the final CLI error-wrapper fix and added regression, the complete local
suite passed 1,413 tests in 126.417 seconds. The earlier 1,412-test run also
passed, but is not used as final-source qualification.

## Remote Qualification

Qualified implementation: `a4659e480dfd82d572b40432560f2d10e8aa2569`.
[CI](https://github.com/pearjelly/skill2workflow/actions/runs/39768118607)
passed all seven jobs, including Python 3.9/3.14, isolated installed preview
qualification, user journeys, editor regressions, Docker, systemd and recovery
and state-safety drills.
[Release preflight](https://github.com/pearjelly/skill2workflow/actions/runs/39768121973)
passed the complete production-baseline dry-run on Python 3.9.25. The terminal
job log explicitly records `PASSED command:production_baseline`.

Roadmap closure passed 106 focused feature/documentation tests, repository
secret hygiene and whitespace checks. README's custom-Skill example now leads
with the read-only preview and explicitly requires removing `--dry-run` to
initialize. The default bundled first command remains directly runnable.
No tag, package release, live-provider pilot or maturity promotion was performed.
