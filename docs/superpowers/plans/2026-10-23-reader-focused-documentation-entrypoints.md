# Loop 285: Reader Focused Documentation Entrypoints

## Evidence And Scope

Previous progress is verified: clean main `53c018b` and all seven exact CI jobs
passed; open issues are empty. README has grown to 2,101 lines, with duplicated
quickstart material, a long command cookbook and more than 1,000 lines of
per-loop history. The approved roadmap design requires a compact README
summary and specialist guides rather than repeated capability/history lists.
The existing documentation hub has useful task groups but omits many public
boundary guides. Historical tests often require technical details and loop
announcements in README, encouraging further duplication.

Make README a bounded first-use entrypoint: purpose, a safe runnable controlled
journey, custom-Skill preview, UI, product limits, visuals, compact architecture,
contributor entry and maturity. Keep public section anchors where practical.
Use the existing docs hub for authoring, operation, diagnosis and contribution;
add one complete public-guide reference linked from that hub. Existing topic
guides and ROADMAP retain detailed contracts and historical evidence. Do not
copy the old README into a second oversized guide or remove runtime safety
conditions to make the entrypoint shorter.

Use the write-page writing-quality guidance while honoring established local
repository destinations. No cloud Page write, frontend/CSS/image change or
new runtime dependency. Preserve approved specs, current maturity, public
command behavior, schemas, fixtures and release/package versions.

## Acceptance

Add failing entrypoint tests before rewriting: README at most 300 lines,
compact roadmap summary, task hub at most 180 lines, valid local links/anchors
and every public top-level guide reachable from README within three links.
Add a stdlib developer checker and focused malformed-link/fence/anchor/escape
regressions; external URLs must never be fetched by this check.

Move historical README contract assertions to their authoritative guide or
ROADMAP and require actual navigation paths instead of silently removing the
coverage. Preserve core first-use, source-of-truth, side-effect, approval,
credential and honest maturity contracts. Verify the documented first-run
commands through the real installed CLI and inspect installed wheel metadata
for the revised README. Run full Python/Node tests, isolated wheel, secret
hygiene, exact feature CI seven jobs and complete release preflight, then
roadmap closure and final exact CI. Keep the broad goal active.

## Local Qualification

The initial entrypoint regressions failed on the 2,101-line README, its long
roadmap section and the absent complete reference. The revised README has
207 lines; all 102 public top-level documents are reachable within two links.
The stdlib checker validates every entrypoint link/anchor, complete reference
membership and budgets without fetching external URLs. Missing-entrypoint
reporting also started with a failing regression.

Historical README assertions now check real navigation routes and authoritative
guides/history. Detailed API/schema/size/approval/maturity assertions remain;
one redundant recurring-schedule history echo was removed because the same test
already requires its exact ROADMAP heading. No old README copy or replacement
capability/history dump was introduced. Existing primary section anchors and
the public screenshots are retained.

The isolated 96-member wheel passed with SHA-256
`ffe198b3a3fcef59b84288a0b841e86cfda3224b26b7606e3504697b78f63170`.
Its installed METADATA body exactly matches the revised README. With source
imports disabled, the documented bundled quickstart produced a waiting run,
the actual inspection command confirmed waiting, and custom Skill/input preview
reported ready without creating its destination. Only owned synthetic paths
were substituted for the README's unused-root examples; no approval or provider
effect was performed in this reader check. Existing package qualification also
passed its complete controlled and input-aware installed journeys.

All 1,500 Python tests passed in 114.752 seconds, and all 64 editor tests and
whole-repository secret hygiene passed. The focused migration keeps specialist
contracts while replacing README repetition with actual bounded link routes.
The immutable feature README was reviewed in GitHub's actual rendered preview:
the first-run commands, approval boundary and custom preview are readable.
Two real link clicks reached the complete reference and then the SQLite trigger
ledger boundary guide; its title and 64 KiB contract remained visible. A local
review capture was retained, not added as a shipping asset. The owned preview
tab was closed. No runtime/frontend/spec/schema/fixture or maturity change.

## Remote Qualification

Feature commit `e19c9380652fe3c475d42433a88244da7cc505ad` is the exact target of
[CI run 39830011540](https://github.com/pearjelly/skill2workflow/actions/runs/39830011540),
attempt 1. Python 3.9 passed 1,500 tests in 135.412 seconds; Python 3.14 passed
them in 128.545 seconds. All seven jobs and the aggregate run are now terminal
success. Python 3.14 job 120003343629 temporarily retained in-progress metadata
after every execution step succeeded. The original job was left unchanged;
its final completed/success response was confirmed on 2026-10-23 before
committing the completion record. No rerun or cancellation was used.

[Release-preflight run 39830045785](https://github.com/pearjelly/skill2workflow/actions/runs/39830045785)
completed with success on that exact feature commit, attempt 1, using Python
3.9.25. Full logs confirm unit tests, compilation, installed wheel, reproducible
wheel and the full `production_baseline` command passed. Only documented dry-run
git/tag checks were skipped. No duplicate dispatch, cancellation or rerun.

The local documentation-closure draft passed all 1,500 Python tests in 114.590
seconds, documentation navigation/budget checks and whole-repository secret
hygiene. Its new roadmap assertions first failed before the entry existed.
The feature-job reconciliation gate is satisfied. All seven final exact
pushed-commit CI jobs remain the handoff gate for the completion record.
The broad project objective remains unfinished; maturity stays Self-hosted Beta.
