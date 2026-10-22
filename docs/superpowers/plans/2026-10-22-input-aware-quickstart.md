# Loop 273: Input-Aware Controlled Quickstart

## Evidence And Scope

Loop 272's installed probe created a waiting custom-Skill run with empty input
despite a required trigger contract. Quickstart currently has no input option
and uses a direct non-trigger run. Add optional `quickstart --input INPUT.json`
and a copied Python `trigger_input` argument. Normalize finite JSON under the
shared canonical 1 MiB bound and validate the compiled input contract before
workspace initialization, ingress-token generation, publication or execution.
Omitted input is `{}` for admission and must satisfy required fields.

Explicit input starts the initial run through the existing durable SQLite
trigger boundary, with fixed source `quickstart` and workspace-local key
`quickstart-initial`. Store values only in existing private run context, not
in the compact result, operator commands or an extra copied input file. Keep
the strict quickstart result schema and non-overwriting workspace contract.
Bundled/legacy no-input runs retain their prior direct-run context.

The pre-change regressions also show a custom Skill can execute HTTP before
its later human gate. Require the compiled success path to reach a real human
gate before any non-manual connector. This is a conservative quickstart-only
onboarding boundary, not a new general runtime policy or an injected gate.
No service or provider call may occur during rejected initialization.

## Acceptance

Eight new tests fail against the unchanged implementation, including omitted
required input, unsupported CLI/API input, and both HTTP action/assertion nodes
before approval. Add tests before CLI/quickstart behavior changes. Cover bounded,
finite, typed input; wrong/missing/extra values; no root/token/network on refusal;
deep-copy semantics; value/path-free results; durable approval continuation with
mapped HTTP body; explicit empty input and unchanged omitted-input context.

Extend installed-wheel qualification with custom input, malformed/contract-invalid
refusal before initialization, pre-approval connector refusal, and approval to
real loopback HTTP delivery. Keep the existing bundled quickstart, service
startup, authenticated webhook and graceful shutdown evidence. Do not connect
to a live SaaS endpoint or resolve a real credential.

```bash
PYTHONPATH=src python3 -m unittest tests.test_quickstart_inputs tests.test_quickstart -v
python3 scripts/quickstart_smoke.py --work-dir /tmp/skill2workflow-quickstart-loop273
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-loop273
```

Full tests, isolated-wheel CLI qualification, all CI jobs, complete production-
baseline release preflight, and aligned public guides close the loop. No new
runtime dependency, DSL field, result field, release or maturity promotion.

## Implementation And Local Evidence

Quickstart validates its compiled success prefix, normalizes/copies finite input
under the existing 1 MiB canonical bound, and checks the compiled schema before
calling service bootstrap. Explicit input uses normal SQLite triggering with a
fixed source/key; omitted valid input retains legacy direct-run context. Compact
results and operator argv are unchanged, while private run context carries
business values through approval and existing request mappings.

The pre-change suite failed as expected. An isolated execution of the old
`35a6c38` initializer with mocked transport additionally proved both network-first
HTTP and HTTP-assertion Skills reached waiting after one pre-approval request.
The new quickstart prefix check rejects both before workspace/token/network
activity. It does not alter the general executor or prevent an author from using
other explicit execution paths under their existing authority.

Ten feature/qualification tests cover input copies, missing/wrong/extra data,
finite/size limits, malformed/oversized/invalid-UTF-8 CLI files, token/workspace
non-creation, compact output, unchanged omitted-input context, real gate approval
and rejection, and mandatory package evidence. The real-process drill was also
red before adding its five required new checks; it now passes all 18 checks.

Installed-only qualification proves invalid inputs and a network-first Skill
create no workspace, valid input waits without HTTP, and approving delivers the
expected typed body to an owned loopback receiver. Response-body canaries are
discarded in metadata mode. Package qualification invokes the installed helper
and CLI with source imports disabled and rejects missing/failed evidence. The
original bundled/custom flow, generated service, authenticated webhook and
graceful shutdown remain covered. No live provider or real credential was used.

The local full suite passed 1,404 tests in 122.709 seconds; all 22 editor
regressions passed. The isolated wheel passed all qualification with 93 members
in `/tmp/skill2workflow-package-loop273`, SHA-256
`e8f27831e65cb9f4804d534dabe139566a73e6fd60148018ff0dd1ae76329888`.
Its quickstart, CLI and qualification modules match source byte-for-byte.
Repository secret hygiene and whitespace checks pass. README now leads with
a directly runnable bundled example and separates the optional custom-input
command; focused documentation checks cover both paths.
