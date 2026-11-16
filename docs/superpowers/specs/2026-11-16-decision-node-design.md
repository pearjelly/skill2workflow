# Decision nodes and durable data — Workflow DSL 0.2.0

Status: reviewed for implementation on 2026-11-16 against the improvement
report T4/T6 and the approved 2026-07-01 product design §7.2. The review checks
below are the implementation acceptance criteria; the original spec is intact.

## Product behavior

A reviewed Skill can fetch a risk record, route high-risk work to a human,
and send low-risk work directly to an automatic action. Branches use durable
input/output data, including after a process restart at a human gate. A canvas
remains a view of executable DSL, with a port for each ordered branch and one
for the default. Graph write-back preserves topology and branch predicates;
authors edit predicates/targets in the source DSL before importing a new graph.

## Version and routing contract

- `schema_version: "0.2.0"` enables `decision`; 0.1.0 remains runnable unchanged.
  Skills without 0.2 features still compile to 0.1.0. Workflow publication
  versions remain independent of the DSL schema version.
- A decision has nonempty ordered `branches: [{when, to}]` and a mandatory
  `default` target. First matching branch wins, otherwise default wins. It has
  no `on_success`, `on_failure`, `on_fallback` or connector binding.
- `when` contains `path` and exactly one of `equals`, `in`, `exists`, `gt`, `lt`.
  Paths are RFC 6901 JSON Pointers rooted at `/input` or
  `/nodes/<node-id>/output`. Escape handling, list indexes and scalar JSON
  equality reuse the HTTP assertion pointer rules. Numeric equality accepts
  integer/float equivalence, never boolean/number equivalence. `in` is a
  nonempty list of JSON scalars; `exists` takes a boolean; `gt` and `lt` take
  finite numbers. No expression syntax, templates, code or dynamic references.
- Missing pointers fail a comparison, except `exists: false`. Numeric tests
  on nonnumbers do not match. Null is an existing value. Ordered branch
  evaluation is deterministic; business values never enter decision events.
- All destinations exist, all nodes are reachable, and the 0.2 graph is a DAG.
  Matching edges must exist for every branch/default transition. The executor
  retains the `len(node_map) + 1` execution limit. No loops are introduced.

Example node:

```json
{"id":"route","type":"decision","title":"Route risk","branches":[
  {"when":{"path":"/nodes/fetch/output/body/risk","equals":"high"},"to":"review"},
  {"when":{"path":"/input/amount","gt":10000},"to":"review"}
],"default":"auto"}
```

## Durable data

The context contains `input` from run context and `nodes.<id>.output` from
completed persisted node results, never credentials or in-flight results.
Full HTTP response output retains its legacy string `body` for compatibility.
For decision data access, a valid JSON body is decoded in the evaluation
context only; the stored HTTP result is unchanged. Authors must explicitly
choose `response_mode: "full"` to route on a response body; metadata mode has
no body. Agent output uses the same node-output namespace (T5).

## Skill grammar and convergence

```markdown
1. Fetch risk <!-- skill2workflow: http {"request":{"url":"https://example.invalid/risk","response_mode":"full"}} -->
2. Route risk <!-- skill2workflow: decision {"branches":[{"when":{"path":"/nodes/1/output/body/risk","equals":"high"},"to":3}],"default":4} -->
3. Manual approval <!-- skill2workflow: human_gate {"next":"end"} -->
4. Automatically approve <!-- skill2workflow: http {"request":{"url":"https://example.invalid/approve","method":"POST"}} -->
```

Branch/default/`next` destinations accept a one-based step number, a unique
exact title, or the terminal names `end`/`failure`. `/nodes/<step-number>/output`
in annotations is resolved to the generated durable node ID. Missing/ambiguous
references are compile errors. Optional `next` on explicit `step`, `human_gate`
and HTTP annotations lets alternatives converge without accidentally running
the other branch. A bare `human_gate` annotation stays compatible. Predicates
and transition targets are never inferred from prose.

## Reserved DSL fields (T6)

`guards`/node `guard` are descriptive HARD-GATE text, not executable policy.
`produces`, `state_schema`, `checkpoints` and `edges[].condition` remain reserved
and ignored at runtime; 0.2 routing is exclusively `decision` plus node
transitions. Existing nonempty reserved fields produce separate validator
notices without becoming publication errors. In 0.1, `requires` is also
reserved. T5 defines explicit 0.2 Agent `requires` as node-output dependencies.
No generated label is a promise that an action was executed.

## Review and verification

Design review outcome: ordered predicates/default meet §7.2; explicit `next`
is necessary to terminate/converge alternatives; no 0.1 state rewrite is
required; decoding only the evaluation view preserves legacy HTTP output.
The source remains the authority across Python/JavaScript graph generation.

Before acceptance: invalid destinations, malformed predicates, missing default,
cycles/unreachable nodes and topology tampering must fail validation/write-back.
Both routes in `examples/skills/risk-routing/SKILL.md` need end-to-end tests,
including restart/resume and input/nested escaped-pointer evaluation. Persist
`decision_evaluated` with the zero-based branch index or null for default, and
no looked-up values. Run the corpus benchmark, Python/JS suites, example sync
and secret hygiene, and publish `workflow-0.2.0.schema.json`.
