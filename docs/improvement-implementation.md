# Improvement report implementation

Scope: all tasks T0–T14 in the 2026-11-16 improvement report, starting at
`03aa8d1`. Each row records a separate implementation loop; structural
refactors are committed separately from behavior changes. Python 3.9 and a
standard-library-only runtime remain requirements.

| Task | Deliverable and acceptance evidence | Status |
| --- | --- | --- |
| T0 | umask-independent package fixture; ensurepip-aware quickstart test; full suites under 0002 and 0022 | Complete |
| T1 | whole-word/Chinese inference, explicit HTTP actions, inference provenance and review notices; example regeneration | Complete |
| T2 | validation/publication reject HTTP bindings without requests | Complete |
| T13 | 20–50 original licensed Skills, type expectations, benchmark and CI thresholds | Complete |
| T3 | descriptive/enforced results and audit, CLI/UI run detail | Complete |
| T4 | reviewed decision/data design, DSL 0.2, compiler/runtime/editor/write-back, risk-routing example and both paths | Complete |
| T6 | enforced data dependencies and documented reserved fields with notices | Complete |
| T5 | reviewed Agent protocol, filtered context, output validation and durable results, deterministic end-to-end adapter | Complete |
| T7 | service route modules/table; unchanged service/client tests and both boundary smokes | Complete |
| T8 | CLI command functions and argparse dispatch; unchanged CLI tests | Complete |
| T9 | development-only Ruff/mypy CI and typed IR/DSL/state contracts | Complete |
| T12 | JSON Schema/validator agreement for examples and invalid cases; versioned 0.2 schema | Complete |
| T10 | testing/demo/pilot modules excluded from runtime wheel; smoke entry points preserved | Complete |
| T11 | SQLite CLI default; explicit JSON compatibility and documentation | Complete |
| T14 | one-page roadmap, archived loop history, consolidated API reference, short agent notes and command reference | Complete |

Completion also requires the full Python and JavaScript suites, example and
secret hygiene checks, installed artifact qualification, and a verified GitHub
branch update. Evidence below is updated only after a check finishes.

## Evidence

- T0: 1,552 tests passed with umask `0002`; after T1/T2, 1,556 tests passed
  with umask `0022`. The quickstart test checks ensurepip availability before
  its isolated-venv journey.
- T1: whole-word, Chinese, provenance, explicit-action and source-free notice
  regressions pass; 82 JavaScript tests pass. Regenerated approval-flow and
  http-action-flow fixtures add provenance. The four enterprise fixtures retain
  node types through explicit reserved-endpoint HTTP declarations; their graph
  fixtures are regenerated from DSL. Example sync and secret hygiene pass.
- T2: missing/non-object requests for both HTTP connectors fail library/CLI
  validation and publication; no workflow is published. Full suite: 1,556 tests
  passed (111.559 s).

- T13: 24 original Skills / 96 process nodes / 71 inferred nodes. Against
  `03aa8d1`: accuracy 53.52% → 100%, false human gates 6 → 0, enforced
  coverage 46.88% → 51.04%. CI thresholds are 100% / 0 / 25%. Independent
  expectation and gate-failure tests pass; full suite: 1,558 tests (111.351 s).

- T3: full suite 1,562 tests passed (111.580 s), 82 JavaScript tests pass.
  Both stores, CLI, compact remote detail, connector attempts, gate resume,
  and legacy unlabelled audit consistency are covered. The old closed detail
  schema remains intact; 0.2 carries execution labels. Corpus remains 100% /
  0 / 51.04%; example sync and secret hygiene pass. Two pre-existing muted
  text contrast findings were fixed through the shared muted color; the design
  hook reports no deterministic CSS findings in that pass. No ignores were added.

- T4/T6: reviewed decision/data design committed before implementation. Full
  suite: 1,568 tests passed (110.799 s); 83 JavaScript tests pass, including
  real LiteGraph duplicate-destination ports and CLI write-back. The new
  risk-routing Skill/DSL/graph fixtures prove high-risk, large-amount and default
  routes against a real HTTP fixture, both stores and restart/resume. Stored
  HTTP bodies remain strings; only the evaluation view is decoded. Decision
  audit/detail exposes branch indexes only. Reserved-field notices do not change
  validity or runtime behavior. Example sync and secret hygiene pass; the
  installed asset inventory includes the new example. Corpus remains 100% /
  0 / 51.04%. JSON Schema semantic agreement is independently tracked in T12.

- T5: eight Agent protocol tests cover both decisions, both stores, restart,
  filtered dependencies, dominance, output rejection and generic-adapter kind
  spoofing. Full suite: 1,576 tests passed (111.655 s); 83 JavaScript tests pass.
  `agent_connector_smoke.py` passes 11 CLI checks against both source and an
  isolated installed wheel (JSON/SQLite, high/low routing and restart). Package
  smoke passes; corpus stays 100% / 0 / 51.04%, example sync and hygiene pass.
  The installed Agent drill is now part of the CI artifact gate.

- T7: 38 resource method ASTs match the originals after reversing only the
  closure/global lookup move. Fixed table: 26 routes; ordered parameter table:
  14 entries. `service.py` drops from 3,973 to 1,516 lines. The service/client
  test files retain their pre-refactor SHA-256 digests; all 176 tests pass.
  Service and security boundary smoke drills pass. Full suite: 1,576 tests
  passed (112.412 s). This pure refactor is committed separately from features.

- T8: extracted 112 command functions with identical body ASTs; argument
  construction AST is unchanged and dispatch uses argparse `set_defaults`.
  `_main` shrinks to 1,175 lines including its retained argument builder.
  `tests/test_cli.py` keeps its pre-refactor SHA-256; all 122 tests pass. Full
  suite: 1,576 tests passed (112.350 s); 83 JavaScript tests and the Agent CLI
  drill pass. This pure refactor is committed separately from features.

- T9: Ruff checks all runtime, script and test Python with E/F/B rules;
  documented exceptions cover line wrapping, checkout bootstrap imports and
  exact iteration-scoped fixture callback reads. Mypy 1.20.2 checks the four
  core modules including unannotated bodies against Python 3.9; both gates pass.
  Shared TypedDict contracts replace IR/DSL/state object-dictionary aliases.
  Tools are pinned only in requirements-dev.txt and a separate CI job.
  Full suite: 1,576 tests passed (112.013 s); JavaScript/corpus/hygiene pass.

- T12: both versioned JSON Schemas and the dependency-free validator agree on
  every committed DSL example, an Agent workflow, and malformed known-field,
  HTTP, decision and nested input-contract shapes. Cross-node graph semantics
  remain explicit runtime checks. The optional development conformance suite
  runs as a mandatory CI quality gate. Old smoke/test fixtures now carry their
  required titles and use the documented step type. Full development suite:
  1,581 tests passed; Ruff/mypy, example sync and secret hygiene pass.

- T10: moved 18 checkout tool modules under scripts/skill2workflow_testing.
  Shared anchored JSON I/O and the production tenant-credential check retain
  their runtime behavior under neutral module names. All migrated local script
  entry points and help-only live entry points pass; the full development suite
  passes 1,583 tests (including the real installed quickstart). Package smoke
  and isolated installed Agent qualification pass. The inspected wheel has no
  demo/pilot/smoke/Lark tool modules; its inspector rejects accidental inclusion.
  A stale local build cache was detected by that gate and cleared before the
  successful clean build. Ruff/mypy, 83 JavaScript tests, corpus, example sync
  and repository/example secret hygiene pass.

- T11: all 33 CLI storage selectors now default to SQLite (26 defaults changed).
  New tests check every selector plus publish/trigger/gate resume/inspection in
  default SQLite and explicit JSON workspaces. Existing CLI integration readers
  select the matching SQLite backend. Full development suite: 1,586 tests passed
  (114.294 s). Installed package and Agent drills pass; Ruff/mypy, 83 JavaScript
  tests, corpus, example sync and secret hygiene pass. Library defaults, JSON run
  files and the existing registry/audit import behavior remain unchanged.

- T14: ROADMAP is 52 lines with four goals and exit criteria. All 285 loops
  remain in docs/loops/history.md; a text comparison preserves the historical
  body apart from relocated links. The 26 remote guides become one API reference
  with stable resource/subsection anchors; all contract text is preserved apart
  from headings and links. Tests read individual resource sections. AGENTS keeps
  ten commands; all 63 original command entries remain in docs/reference.md.
  The approved design specs are unchanged. Full development suite: 1,591 tests
  passed (115.119 s); Ruff/mypy and 83 JavaScript tests pass. All 89 public
  document/archive files have valid local targets and anchors; all 78 top-level
  guides are reachable within two hops. Corpus and secret hygiene pass.

## Final qualification

All T0–T14 tasks are complete. The final development suite passes 1,591 Python
and 83 JavaScript tests; schema conformance, Ruff, core mypy, corpus and secret
hygiene gates pass. The production-baseline runner passes all 19 checks,
including isolated wheel installation, reproducible builds, service/security
boundaries, observability, backup/restore, upgrade, retention, cancellation,
interrupted recovery, scheduling and the service soak. Installed Agent routing
and restart checks pass for JSON and SQLite.

[Machine-readable verification](verification/2026-11-16-improvement-report.json)
records the tested commit and fixed outcome facts. GitHub publication is tracked
by the branch/PR containing this ledger; no package release is performed.

The release-preflight path filter also follows the consolidated API/history
documents and extracted service-route modules; its CI contract tests pass.

## Post-Stop design triage

The deep design pass found the new decision explanation inheriting uppercase
section-label styling. It now shares sentence-case inspector-note typography
with the assertion help (12 px, normal weight, 18 px line height). Browser
checks confirm normal case and wrapping on desktop and mobile; editor and UI
regressions pass. The full development suite also passes 1,591 tests
(115.100 s), and all 83 JavaScript tests pass.

Two Inter findings predate this work: both font stacks are unchanged from
03aa8d1. On 2026-11-17 the user confirmed retaining Inter and recording two
file-scoped exceptions. The Impeccable CLI recorded `overused-font=inter` only
for `web/index.html` and `web/control.html` in
[the shared detector configuration](../.impeccable/config.json), with the user's
decision recorded as the reason. The three Stop findings are resolved through
one fix and two approved exceptions; the two contrast fixes remain valid.

A later stylesheet scan flagged the validation list's 3 px side border. The
warning, `ok` and `error` variants use it as a semantic status marker alongside
the validation message, unchanged from 03aa8d1. This is a false positive for the
decorative-card rule. The CLI recorded a `side-tab` exception scoped only to
`web/styles.css`, with the agent's evidence as the reason. The interface and
the two user-approved font exceptions are unchanged.
