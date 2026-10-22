# Loop 272: Skill-Declared Trigger Input Contracts

## Problem And Scope

HTTP actions and assertions compile from Skill source, but a business input
contract still requires editing generated DSL. Runtime `input_schema` already
supports bounded typed admission before claims, state, audit or outbound effects.
Expose that existing contract through one explicit standalone body declaration:

```markdown
<!-- skill2workflow: input_schema {"type":"object","properties":{"record_id":{"type":"string","minLength":1}},"required":["record_id"],"additionalProperties":false} -->
```

Accept one case-sensitive single-line declaration outside fenced examples,
indented at most three spaces and not attached to a step or prose. Keep source
line counts intact while removing active configuration from guidance inference.
Reject duplicates, malformed/duplicate-key/nonfinite JSON, literal nested comment
delimiters, and the existing unsupported/unbounded schema shapes with a fixed
value-free declaration error. Limit raw schema JSON to the existing 64 KiB bound.

Copy and revalidate typed IR in the compiler; an absent declaration adds no DSL
field and preserves open-object legacy behavior. This emits the existing DSL
contract, not a new schema dialect, default injection, coercion, expressions,
implicit approval, runtime policy, credential access or endpoint inference.
Do not alter published workflows or expand transport/provider authority.

## Acceptance And Evidence Plan

The new 12-test suite fails against the unchanged parser/compiler, including
the unsupported source declaration and ignored forged-IR contracts. Tests come
before implementation. Cover all three process headings, data/guidance isolation,
source lines, strict JSON, bounds, placement/fences, aliasing, forged IR, unchanged
legacy behavior, fixed CLI refusal/output preservation, and visual write-back.

Compile and publish a declared contract through JSON and SQLite. Prove wrong,
missing and unknown inputs fail before a run, audit, idempotency claim or network
request; a corrected retry using the same key can still enter the human gate.
Approval must remain explicit before HTTP effects.

Update the existing HTTP action example with a bounded input declaration and
regenerate only its DSL/graph fixtures. Extend the installed CLI HTTP journey
with missing/type/unknown input refusals, no-claim/no-run/no-audit/no-request
evidence and accepted retry, while retaining match/mismatch/HTTP failure/rejection
checks. Exercise local editor compilation without changing UI code or design.

```bash
PYTHONPATH=src python3 -m unittest tests.test_skill_input_schema -v
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 scripts/skill_http_action_smoke.py
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-loop272
```

Full Python and editor tests, example sync, secret hygiene, isolated wheel,
all CI jobs and complete production-baseline preflight close the loop. No release,
live provider pilot or maturity promotion is implied.

## Implementation And Local Qualification

A pure source-declaration factory reuses the existing input-schema validator
and returns a deep copy with a fixed error boundary. The parser recognizes the
standalone comment outside fences, replaces only that line with an empty line,
and retains the typed contract in IR. The compiler revalidates it and adds the
existing root field. Legacy inputs without the declaration keep their prior
IR and DSL shapes. No runtime validator or execution path is changed.

The 12 feature tests pass, including the JSON/SQLite no-admission evidence,
corrected same-key retry, explicit approval and mapped HTTP continuation.
Portable authoring artifacts preserve the contract without local source paths;
visual write-back cannot change it. Editor compile API tests retain fixed
refusal, and the new real-editor/LiteGraph regression carries the root contract
through browser-style graph save and strict CLI write-back.

The HTTP example now explicitly requires bounded `record_id` and `title`
strings and rejects additional fields. Its regenerated fixtures differ only in
the new contract and resulting source-line offsets. All other example fixtures
remain unchanged. The installed HTTP qualification now requires seven cases,
not the old four: three rejected inputs cause no claims/runs/audit/requests,
then the same key accepts a corrected input and the existing four HTTP outcomes
retain approval, failure suppression and response/credential exclusion.

Local full suite: 1,393 tests passed in 122.350 seconds. All 22 editor behavior
tests passed, including root-contract preservation; 57 local UI API/asset tests
passed. Example synchronization, repository/example secret hygiene and whitespace
checks passed. The isolated wheel passed all gates with 93 members, including
the seven-case installed journey, in `/tmp/skill2workflow-package-loop272`.
SHA-256: `a978e031d3c6a83fef174c757763ee15d55e5e5193b2bc6dba66e100e64406e2`.
Installed parser/compiler/declaration modules match source byte-for-byte.

This is specifically trigger admission. Direct raw-executor and non-triggered
published runs retain their existing behavior. The current custom-Skill
quickstart has no business-input option and starts its first run without a
trigger; it is not claimed qualified for required-input business workflows.
The guide therefore directs these workflows to compile/publish/trigger with
explicit non-secret input. This is a separate first-value handoff to investigate,
not a hidden change to the runtime boundary.

An installed quickstart probe using the updated HTTP example confirmed a waiting
first run with empty input despite required `record_id`/`title`. It was not
approved or served; the owned probe run was cancelled after inspection. No
endpoint request was made. This preserves evidence for the separate input-aware
first-value path instead of claiming it is already covered.

## Remote Qualification

Qualified implementation: `23ea8cfdad695c70eb8266c3635beb799f3d9916`.
[CI](https://github.com/pearjelly/skill2workflow/actions/runs/39761972222)
passed all seven jobs, including Python 3.9/3.14, isolated installed admission
and HTTP journeys, editor regressions, Docker, systemd and recovery/state safety.
[Release preflight](https://github.com/pearjelly/skill2workflow/actions/runs/39761979306)
passed the complete production-baseline dry-run on Python 3.9.25. No tag,
package release, live provider pilot or maturity promotion was performed.
