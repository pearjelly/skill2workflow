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
| T13 | 20–50 original licensed Skills, type expectations, benchmark and CI thresholds | Pending |
| T3 | descriptive/enforced results and audit, CLI/UI run detail | Pending |
| T4 | reviewed decision/data design, DSL 0.2, compiler/runtime/editor/write-back, risk-routing example and both paths | Pending |
| T6 | enforced data dependencies and documented reserved fields with notices | Pending |
| T5 | reviewed Agent protocol, filtered context, output validation and durable results, deterministic end-to-end adapter | Pending |
| T7 | service route modules/table; unchanged service/client tests and both boundary smokes | Pending |
| T8 | CLI command functions and argparse dispatch; unchanged CLI tests | Pending |
| T9 | development-only Ruff/mypy CI and typed IR/DSL/state contracts | Pending |
| T12 | JSON Schema/validator agreement for examples and invalid cases; versioned 0.2 schema | Pending |
| T10 | testing/demo/pilot modules excluded from runtime wheel; smoke entry points preserved | Pending |
| T11 | SQLite CLI default; explicit JSON compatibility and documentation | Pending |
| T14 | one-page roadmap, archived loop history, consolidated API reference, short agent notes and command reference | Pending |

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
