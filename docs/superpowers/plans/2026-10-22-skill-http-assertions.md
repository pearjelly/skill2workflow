# Loop 267: Skill HTTP Assertion Declarations

## Basis And Decision

Loop 266 made HTTP result assertions executable, but authors still had to edit
DSL bindings and transitions by hand. The approved design §10.5/10.7 supports
explicit tool requirements and verification methods. Extend the existing
single-step declaration grammar with a concrete HTTP assertion configuration.

Use `<!-- skill2workflow: http_assert {JSON} -->` at the end of a selected
Checklist/Workflow/Steps item. JSON supplies `request`, `assertions`, and
optional credential-handle metadata. The parser emits explicit `tool_call`
and `http_assert` binding IR; the compiler preserves source lines and clean
display text and emits ordinary sequential success/failure transitions.

## Contract And Compatibility

- One case-sensitive single-line declaration on one nonempty selected step.
  It takes precedence over keyword inference. Use separate steps for approval
  and assertion; no declaration may be silently combined or ignored.
- Strict JSON rejects duplicates, nonfinite numbers, oversized number literals,
  and literal nested comment delimiters. Unknown configuration/request fields
  and unsupported assertion configurations fail with a fixed annotation error.
- Validate transport metadata and handle descriptors without reading a
  credential, touching runtime state, or calling an endpoint at compilation.
- Copy explicit bindings so compiled edits cannot mutate caller-owned IR.
  Reject forged explicit IR connector identities and incomplete typed records.
- Treat parsed configuration as data: exclude it from legacy hard-gate and
  textual hint scans, while preserving the original source sections in IR.
- Compile review counts explicit HTTP assertion tool calls as verification
  nodes. Its existing keys/version stay unchanged; the count is guidance and
  does not prove a check has executed.
- Unmarked Skills, existing approval declarations, committed fixtures, published
  artifacts, and runtime behavior retain compatibility. No endpoint/expected
  value inference, arbitrary code, DSL version change, or new dependency.

## Acceptance

Parser/compiler red-green tests; no-I/O compilation; malformed/refused input;
CLI and real UI parity; approval then actual assertion controls successor
execution with JSON/SQLite state; isolated installed CLI compiles Chinese
Skill and performs real matching/failing HTTP requests. Full supported-Python
CI and release preflight are completion gates.

```bash
PYTHONPATH=src python3 -m unittest tests.test_skill_http_assertions tests.test_explicit_approval tests.test_http_assertions tests.test_ui -q
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-loop267
python3 scripts/secret_hygiene.py examples/workflows
```

## Verified Outcome

Implementation `cfaf906` plus guidance-data correction `6e7ae2c` passed the
local full suite (1,358 tests) and isolated-wheel qualification on 2026-10-22.
Focused red-green cases cover declaration grammar, copied bindings, no-I/O
compilation, credential descriptors, preserved existing output on refusal,
and configuration text excluded from legacy guidance scans. Approval then
actual assertion controls delivery in both JSON and SQLite storage.

The installed CLI compiles Chinese Skill source with review, validates the
generated DSL, and performs real matching and failing HTTP requests. Request
counts prove compile/validate make no HTTP request and execution makes exactly
one per case. Source provenance and review counts are checked, and response
canaries do not enter durable results. Repository/example secret hygiene passes.

- [Implementation CI](https://github.com/pearjelly/skill2workflow/actions/runs/39713786295):
  all seven jobs passed, including full Python 3.9/3.14 tests, installed wheel,
  deployment, recovery/state safety, and user journeys.
- [Release preflight](https://github.com/pearjelly/skill2workflow/actions/runs/39713828640):
  successful dry run with the production-baseline gate.

The project remains Self-hosted Beta on Workflow DSL 0.1.0.
