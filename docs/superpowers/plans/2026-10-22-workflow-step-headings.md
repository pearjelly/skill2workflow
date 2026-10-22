# Loop 264: Explicit Workflow And Steps Headings

## Basis

Loop 263 and its Python 3.9 runner correction passed all seven CI jobs and the
production-baseline release preflight at `3ddf455`. A numbered `## Workflow`
currently produces no ordered steps and compiles into a generic review node.
This misses explicitly structured Skill content covered by the approved
parser/compiler direction, without requiring a new execution model.

## Scope

- Preserve legacy Checklist extraction, list formats, and precedence. An empty
  Checklist section still suppresses the fallback.
- When no Checklist section is recognized, accept exact case-insensitive ATX
  headings `Workflow` and `Steps`, regardless of heading depth or ancestors.
- Extract direct, consistently indented top-level numbered items (`1.` or
  `1)`), preserving order, titles, details, source lines, and section names.
  Numbering need not start at one or be consecutive.
- The next heading ends a section. Do not flatten descendant sections, nested
  lists, bullet inventories, or prose into process steps. In fallback sections,
  the minimum indentation among list markers establishes the top-level list.
- Ignore fallback content inside backtick or tilde fences; match fence
  character and length and retain unclosed fences through end of input.
- Ignore empty candidate sections, but reject multiple populated candidates
  with a fixed error. Do not concatenate independent procedures.
- Reuse the existing DSL, compile review, UI endpoint, and durable human gate.
  Keep the historical `checklist_not_found` notice code, with clearer wording.

## Exclusions And Compatibility

No free-prose interpretation, full Markdown parser, new runtime dependency,
new DSL field, automatic command execution, standalone hard-gate inference,
or new verification semantics. This does not reinterpret published workflows.
Newly compiled non-Checklist Skills can gain real nodes and should be reviewed
before publication. Existing Checklist fixtures must remain unchanged. Legacy
Checklist parsing is not rewritten as part of this fallback addition.

## Acceptance Evidence

1. Parser tests cover heading/list grammar, provenance, Checklist precedence,
   ambiguity, fences, nested lists, and unchanged example fixtures.
2. CLI and real loopback editor compilation produce valid DSL and matching
   source-free review counts, and reject ambiguity without partial output.
3. A compiled process reaches the existing durable human gate, survives a
   new executor instance, and cannot reach its successor before approval.
4. Isolated installed-wheel qualification covers the new heading behavior.
5. Full Python 3.9/3.14 CI, package, example synchronization, and secret-hygiene
   checks pass before completion.

## Verification Commands

```bash
PYTHONPATH=src python3 -m unittest tests.test_process_steps tests.test_parser tests.test_cli tests.test_ui tests.test_examples -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-loop264
python3 scripts/secret_hygiene.py examples/workflows
```

## Verified Outcome

Completed at implementation commit `c68d871` on 2026-10-22:

- Local Python 3.14 full suite: 1,333 tests passed. Independent final review
  also passed 39 focused checks without a blocking finding.
- Actual isolated-wheel smoke passed, including both headings through the
  installed CLI and real local UI, source provenance, valid DSL, and fixed
  ambiguity rejection. The smoke clears source import assistance.
- Repository and example secret-hygiene scans passed; existing Checklist
  fixtures remained unchanged.
- [Implementation CI](https://github.com/pearjelly/skill2workflow/actions/runs/39708641121)
  passed all seven jobs: Python 3.9, Python 3.14, Linux systemd, Linux Docker,
  recovery/state safety, user journeys, and release artifacts. The Python
  jobs include complete tests and installed-wheel qualification.

The local Python 3.9 container could not start because its container-storage
mount failed. It was not counted as evidence; successful Ubuntu 24.04 CI
provides the Python 3.9 qualification. Production maturity remains Self-hosted
Beta, with no DSL version or runtime-dependency change.
