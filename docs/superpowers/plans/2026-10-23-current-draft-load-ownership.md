# Loop 283: Current Draft Load Ownership

## Evidence And Scope

The previous turn is verified progress: clean main `53e9944` and its exact
seven CI jobs passed; the versioned-Skill feature's complete release preflight
also passed. There are no open issues. Source review and new red tests show
that older JSON reads, example responses/body parsing and embedded fallbacks
can overwrite a newer draft or repaint stale errors. Skill compile has partial
revision fencing, but a newer JSON selection does not invalidate it until the
file finishes loading. Form edits and other pending reads are not coordinated.

Protect one current authoring intent across JSON, example and Skill entry
points. Selection begins ownership immediately, aborting obsolete fetch/compile
work and invalidating unabortable reads; check revision plus the current graph/
DSL snapshot after every await. Direct replacement and uncommitted form edits
invalidate pending imports; layout changes are covered by the snapshot. Only
the latest unchanged intent may replace the draft, show an error or install
the existing embedded-example fallback. New document loads clear old staged
Skill text rather than leaving an earlier source silently available.

Keep the existing canvas/inspector, controls, CSS, normal example fallback and
explicit Compile SKILL behavior. Reuse the inline feedback row for a current
JSON read/parse failure with fixed recovery copy, not raw parser text or an
invalid label on the retained graph. Associate the affected existing controls
with that feedback. This is an Impeccable harden → polish refinement of the
incumbent Operate surface, not a visual redesign or new source/file format.
No structured-question reply has arrived; continue this narrow non-executing
default while preserving later user direction. Missing global design documents
are pre-existing drift and remain untouched.

## Acceptance

The actual-editor-module regressions start red for latest JSON selection,
late JSON failure, late example success/failure/body parsing, staged/compiled
Skill replacement, immediate cross-source cancellation, pending Skill bytes,
uncommitted form edits, layout edits, direct document replacement and safe JSON
recovery, with an additional no-AbortController regression preserving basic
example loading through revision fencing. Preserve the current fallback for the owning request. Run both this
suite and existing recovery checks against the actual served installed editor
and vendor, not only source markers or source-module tests.

Use real browser controls and an owned delayed loopback example response to
verify a later JSON import survives; inspect current failure/recovery at desktop,
mobile and actual viewport together, plus long text/focus/overflow. At most one
builder correction/confirmation round; then one detector, a fresh finish reviewer
and fresh surface documenter as the skill requires. Run full Python/Node tests,
isolated wheel, secret hygiene, exact feature CI seven jobs and full release
preflight, then documentation closure and its exact CI. Preserve source/DSL,
export, validation, runtime, publication and credential boundaries; no dependency,
release, tag, PR, version or maturity change. Keep the broad goal active.

## Local Verification

- Baseline actual-editor tests: 13 failures out of the first 14 ownership
  checks; the existing current-example fallback already passed. Added a separate
  failing no-AbortController regression and a failing installed-driver contract
  test before the corresponding fixes.
- Final source checks: 64 Node tests passed; all 1483 Python tests passed in
  107.576 seconds. No runtime dependency or backend behavior changed.
- Fresh isolated wheel qualification passed with 96 files and SHA-256
  `4f87962fcd948821c6c4f7eb234ee9bce1e5da8bbaf42a2ca1df6065d24ef27f`.
  Installed app/index bytes match source. The mandatory actual-served-editor
  flag passed all 27 recovery/ownership module checks plus ten CLI/API cases;
  the same latest suite correctly rejected an older installed editor while
  source passed. Whole-repository secret hygiene passed.
- Real native controls with an owned delayed example response demonstrated
  newer JSON success at `1792689066.114`, between the old request at
  `1792689065.329822` and its completion at `1792689077.341155`; the newer graph
  survived. Current JSON failure, long synthetic text, keyboard focus and
  corrected recovery were captured at desktop, actual viewport and narrow
  widths. Seven captures live under `.impeccable/review/loop283/`.
- Builder and fresh reviewer opened all seven captures. Fresh finish verdict:
  **ship**, no material fixes, independently 27 checks passed. The single
  detector run found only inherited font/grid advisories. CSS/layout unchanged.
  True 200% zoom remains unqualified: the shortcut did not change the observed
  viewport/font metrics; 640px evidence is reflow only, not a zoom pass. This is
  a documented nonblocking limitation for this unchanged-CSS scope.

Remote feature CI, complete release preflight and roadmap closure remain
required before marking Loop 283 complete. No release or maturity promotion.
