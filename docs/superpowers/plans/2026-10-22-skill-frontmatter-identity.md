# Loop 280: Skill Frontmatter Identity And Text

## Evidence And Scope

Loop 279 is verified progress on clean main `ab38ae6`: its final seven CI jobs
and exact feature release preflight passed. Current open issue inventory is
empty. The next-selection rule asks for first-value Skill-to-run evidence.

A source-level reproduction with top-level `name: reviewed-workflow`, a folded
description and `metadata.name: packaging-author` compiles to the wrong
`workflow_packaging_author` identity and description `>-`. The frontmatter
reader currently splits every colon line, ignoring nesting and scalar scope.
This is a real standard-input compatibility defect, not missing UI polish.

The [Agent Skills specification](https://agentskills.io/specification) separates
top-level identity/description from optional string-map metadata. Use the
[YAML scalar rules](https://yaml.org/spec/1.2.2/#81-block-scalar-styles) to support
common literal/folded text without flattening nested data into workflow fields.
Preserve dependency-free Python 3.9 installation, existing plain frontmatter,
body/process selection and exact source lines. Decode ordinary quoted strings
and comments; keep metadata scoped as data. Duplicate/ambiguous supported
declarations must fail with a fixed value-free error rather than choosing an
identity silently. No YAML tags, anchors, aliases, merges, arbitrary object
construction, include/file lookup or execution. Document the supported subset
and remaining YAML exclusions instead of claiming full YAML conformance.

## Acceptance

Write red tests first for nested name/description isolation, folded/literal
text, quotes/comments, duplicate declarations, scalar-content fake metadata,
line mapping and fixed safe refusals. Exercise parse/compile, the existing UI
compile endpoint (without changing UI), portable authoring export and actual
installed CLI. Add mandatory installed qualification, not source-marker proof.
Run focused/full suites, editor regressions, example sync, isolated wheel,
seven feature CI jobs, complete release preflight and final closure CI. No new
runtime dependency, DSL/report schema, published-artifact rewrite, provider
request, release/tag or maturity promotion. Keep the full project goal active.

## Implementation Evidence

The first eight parser tests produced 26 failing cases against the prior
implementation, including identity replacement, lost multiline content and
ambiguous duplicate acceptance. The parser now delegates frontmatter to a
small string-only reader; root fields and one flat optional metadata map retain
separate scopes. Literal/folded text, chomping, indentation, quotes and comments
are data only. Existing body source lines, process grammar and runtime authority
are unchanged. CLI, local compile API and portable authoring tests cover the
same identity/description boundary and fixed value-free refusals.

Before final qualification, adversarial tests exposed padding-sensitive regex
backtracking in the initial implementation's key/comment matching. Both now
use linear scans. The owned child regression first timed out at five seconds,
then passed for a 100,000-space malformed key and a valid long scalar. The
deadline is a test guard, not a product latency SLA. Earlier full-suite/wheel
passes predate these final guards and are not substituted for final-source
qualification.

Using the already installed local PyYAML 6.0.3 only as a development oracle,
784 valid block-text combinations matched and all 216 invalid combinations
were refused. The oracle is not imported by production code or committed tests,
installed as a project dependency, or used to claim full YAML conformance.
Supported syntax, unsupported YAML forms, corrected recompilation behavior and
published-DSL immutability are documented in the authoring, contributor,
compatibility, stability and artifact-qualification guides.

## Final Local Qualification

Frozen final source passed 1,460 Python tests in 104.784 seconds, 118 focused
parser/CLI-helper/UI/authoring tests and all 37 editor regressions. All example
fixtures remain synchronized. The final 784-valid/216-invalid oracle rerun also
reported zero mismatches. Earlier 1,459/1,460 passes are superseded by this
final-source run because the linear comment/key scanners were hardened later.

Isolated-wheel qualification passed at
`/tmp/skill2workflow-package-loop280-qualified`, with 95 members and SHA-256
`35f92b47d0a74af9eb21fcdec1a5fc09c97efc841b6aed95b7a691d416eb9539`.
Both changed runtime modules match the installed wheel byte-for-byte. The
mandatory installed Workflow/Steps drill verifies CLI and local compile API
identity, decoded description, human/verification gates, source provenance and
DSL validation with nested colliding metadata. It uses no source imports or
YAML dependency. The extra wheel member is the standard-library-only reader.

Portable authoring retains the intended name/description without copying
optional metadata. Invalid duplicates are value-free CLI refusals and fixed
local API 400 responses. Secret hygiene passed. A staged whitespace scan found
one extra blank line at the new test file's EOF; the documentation closure
removes it without changing test behavior or runtime source. No UI
source, provider, credential, execution policy, published artifact or DSL/report
schema changed; owned temporary children/once-only listeners have stopped.

An additional wheel-only quickstart reused the qualified folded-description,
colliding-metadata Skill from outside the checkout. It preserved
`workflow_installed_process`, stopped in `waiting`, then completed through the
generated explicit approval command with only manual fixture steps. No external
provider was called. The fresh owner-only test workspace was removed afterward;
the installed wheel and source fixture remain available as qualification evidence.

## Remote Qualification

Implementation `1a24126b1fc54b6f177d796a6244dc25e1afcd62` passed all seven
[CI jobs](https://github.com/pearjelly/skill2workflow/actions/runs/39799059823),
including installed CLI/UI qualification, both Python floors, real user journeys,
recovery/state safety, Docker and systemd. Terminal logs independently record
all 1,460 tests on Python 3.9 (127.331s) and Python 3.14 (121.458s).

[Complete release preflight](https://github.com/pearjelly/skill2workflow/actions/runs/39799120872)
passed on attempt 1 at the same exact implementation, on Python 3.9.25. Its
terminal log explicitly records `PASSED command:production_baseline`; the fixed
19-check suite and existing budgets were not reduced or bypassed. Delayed
remote status propagation was observed until the run and every job were
terminal; no successful run was restarted to resolve that observation delay.
No package version, release/tag, runtime dependency, DSL or maturity change.
