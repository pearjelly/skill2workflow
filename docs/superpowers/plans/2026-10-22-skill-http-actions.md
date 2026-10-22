# Loop 269: Skill HTTP Action Declarations

## Problem And Scope

Explicit Skill approvals and HTTP result checks already compile into executable
bindings. Ordinary business HTTP calls still require manual DSL edits, leaving
the authoring journey incomplete. Add an explicit selected-step declaration:

```markdown
2. 提交请求 <!-- skill2workflow: http {"request":{"method":"POST","url":"https://example.invalid/tasks","body":{"source":"workflow"}}} -->
```

Emit the existing `http` tool-call contract with clean text and source mapping.
Support the existing request methods, JSON body, body/query trigger-input
mappings, origin policy, timeout, and header credential handles. New declarations
default response retention to `metadata`; explicit `full` remains available.
This default affects only new declarations, not existing DSL or inferred nodes.
Configuration remains data, not inferred prose guidance. Unknown/malformed
fields fail with the existing fixed annotation error before output replacement.

No HTTP transport semantics, DSL fields, implicit approvals, automatic
endpoint inference, retries, credential resolution, or live SaaS pilot are added.
Compilation and validation perform no HTTP calls. Running an explicitly
configured workflow can cause the declared provider effects; authors must review
the request and choose human gates and retry policy explicitly. Existing
`human_gate` / `http_assert` declarations and unmarked fixtures stay compatible.

## Acceptance

Add tests before parser/compiler changes. Cover Checklist/Workflow/Steps,
typed request/body/mappings/handles, clean titles/provenance, copying forged IR,
data/guidance separation, invalid metadata/JSON/body/credentials, placement,
fixed CLI/editor refusal, and unchanged legacy fixtures. Verify approval,
rejection, missing inputs, HTTP failure, result mismatch, and service-origin
denial using JSON and SQLite storage without credential/response leakage.

Qualify a real installed CLI journey against an isolated loopback server:
Skill compilation, validation, publication, input trigger, human resume,
POST action, GET result assertion, and delivery suppression on failure.
No hand-editing compiled DSL. Integrate this qualification into package CI.

```bash
PYTHONPATH=src python3 -m unittest tests.test_skill_http_actions -v
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 scripts/skill_http_action_smoke.py
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-loop269
```

## Implementation And Local Evidence

The parser recognizes explicit `http` declarations using the existing strict
JSON/placement boundary. A pure factory reuses HTTP metadata/mapping/origin
validation, copies the binding, and adds the new-declaration metadata retention
default. The compiler revalidates explicit IR and retains that default without
mutating IR. HTTP connector/executor semantics and UI code are unchanged;
the takeover activation correction below was required during qualification.

Eleven feature tests cover source compilation, data/guidance separation,
configuration rejection, forged IR, retention, query/body mapping, and six
runtime outcomes across JSON/SQLite. Editor compilation and documentation
tests cover the public handoff. The loopback published-run smoke qualifies four
real CLI scenarios and checks both state and audit for credential/response
canaries. The installed-wheel gate executes that smoke without source imports.

The new example has synchronized Skill, DSL, and graph fixtures. Initial
qualification correctly rejected the additional wheel data members; a
red-green inventory test and two exact release allowlist entries reconciled
the fixture inventory without weakening the artifact boundary.

Initial feature full suite: 1,374 tests passed in 119.269 seconds. The initial
isolated wheel passed all qualification, including the new journey, with 92
members in `/tmp/skill2workflow-package-loop269-final-20261022`. Its SHA-256 is
`4e827ce537338eab7ee0cf79e28464d067b6e83bad8093bfe03d7ae057d64fe9`.
The five unchanged editor renderer tests, example fixture checks, repository
and example secret hygiene, and whitespace checks also passed.

## Qualification Correction: Takeover Activation

The initial release preflight at `3eae43e` passed unit tests, wheel qualification,
and reproducible builds, but its production-baseline aggregate reported a failed
interrupted-recovery drill. That aggregate discards child output, so the exact
failure detail from that run is unavailable. The same drill passed separately
in CI and twice locally; this is not evidence of a diagnosed one-off cause.

Inspection and a new deterministic blocked-recovery test independently proved
that a standby could report readiness and dispatch after lease acquisition but
before takeover reconciliation completed. The test failed before the fix.
An internal completion barrier now gates readiness and dispatch until recovery
succeeds; lease loss, failure, and shutdown clear it. This is a narrow existing
recovery-contract correction, not a new retry, replay, or execution authority.
No assertion is made that the unavailable original failure had only this cause.
The complete qualification must pass again on the corrected service.

Post-correction local evidence: 1,375 tests passed in 129.082 seconds; the
blocked-recovery regression and real process-loss drill passed. The corrected
isolated wheel passed all gates (92 members) in
`/tmp/skill2workflow-package-loop269-takeover-20261022`, SHA-256
`a9979589fb2f48ad5f43e69a17141179503b055b1124788cc360ac8f118a21e8`.
Its installed service module matched the corrected source byte-for-byte.
