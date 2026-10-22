# Loop 282: Versioned Skill Iteration

## Evidence And Direction

The previous loop is verified progress: clean main `214bf60` and its exact
seven-job CI passed, with complete feature release preflight. Open issues are
empty. A real local SQLite reproduction shows that an edited Skill still
compiles as `0.1.0`; its second publication is refused by the correct immutable-
version boundary. Ordinary `metadata.version` is data, not workflow deployment
intent. Authors currently must edit generated JSON to create the next version.

Add one explicit standalone source declaration:
`<!-- skill2workflow: workflow_version 0.2.0 -->`. It affects only the generated
`workflow.version`, not the package/DSL schema version, identity, gates or runtime
authority. Missing declarations retain `0.1.0`; never auto-increment a version or
infer it from unrelated metadata. A source declaration, instead of a CLI-only
override, keeps compile, editor helper, private export, repair and custom
quickstart consistent without adding independently drifting defaults.

Accept exactly one active declaration outside Markdown fences, on a standalone
line with zero to three leading spaces. A version is 1–128 ASCII characters,
starts alphanumeric, and otherwise uses letters, digits, period, underscore or
hyphen. This bounded authoring subset is safe for current local filenames and
remote references; it does not narrow existing hand-authored DSL versions.
Malformed, duplicate and misplaced declarations fail with one fixed source-free
message before authoring output/workspace creation. Preserve original lines,
and never turn the declaration into a step, inference hint or execution command.
The compiler revalidates explicit IR so callers cannot bypass the source rule.

## Acceptance

Start with red parser/compiler tests, including boundaries, metadata isolation,
fences, placement, malformed evidence, original line mapping and unchanged
default fixtures. Exercise actual CLI compile, local UI API, private export,
backup repair/dry-run and custom quickstart. Prove the complete iteration with
two independently verified artifact sets/Bundles, a value-free diff, both
immutable published versions, version-pinned waiting runs, approval/rejection,
and conflict preservation. No endpoint/credential/provider call is required.

Make the actual installed CLI journey mandatory in wheel qualification; a
source import or help marker is insufficient. Keep Python 3.9 stdlib runtime,
existing DSL/review/result schemas, published bytes and execution policies.
No UI layout/control change, auto-migration, new release/tag/version/maturity
claim or visual redesign. Run full Python/Node suites, installed wheel and
hygiene, exact feature CI seven jobs and complete release preflight, then
documentation closure and its exact CI. Keep the broad goal active.

## Local Qualification

Before implementation, new tests reproduced rejection of the source declaration,
ignored explicit IR versions and the absent installed-gate contract. The actual
SQLite baseline reproduction compiled two changed Skills as `0.1.0`; the second
publication correctly refused an immutable conflict.

After implementation, 1,482 Python tests passed in 107.981 seconds and all 49
editor module tests passed. The focused 24-test version/document/package group
also passed after final evidence checks were added. Unchanged example fixtures
passed. No frontend asset or visual/control behavior was modified.

The final isolated wheel passed with 96 members and SHA-256
`90239a86eab7392e073cd5b1dfb65328996a2af9c82eb7cca8dd42dd46c1c10e`.
Installed parser/compiler/version-boundary files byte-match source. A separate
selected-installed-CLI run passed all ten required checks: default/explicit
compilation, verified private artifacts, repair/preview, Bundle diff, two-version
publication, conflict refusal preserving registry and published bytes, pinned
approval/rejection, versioned custom quickstart, actual loopback compile and
invalid-source refusal. Source imports were disabled outside the checkout;
synthetic manual steps required no provider request or credential resolution.
Repository secret hygiene passed without findings. Exact feature CI, complete
release preflight and roadmap closure remain required before delivery.
