---
version: 1
slug: "web-index-html"
primary_target: "web/index.html"
related_targets: ["web/app.js","web/input-review.js","web/styles.css"]
---

# Workflow Editor — Operate

## Current hardening (Loop 283)

Coordinate JSON reads, example responses/fallbacks and Skill staging/compilation
so only the latest unchanged authoring intent may replace or repaint the draft.
The optional scope question has no reply; retain the incumbent world and follow
`docs/superpowers/plans/2026-10-23-current-draft-load-ownership.md`.

## Direction contract (Loop 283)

THESIS: The draft on screen belongs to the author's latest action, not the
slowest old request. Preserve newer work and discard obsolete results.

OWN-WORLD: Keep the white/neutral, blue-accent system-sans editor, native
controls, semantic status pill and existing wrapping inline feedback.

STORY: Choose JSON, an example or a Skill; change your mind or edit while it
loads. The newer choice/edit wins. Correct a current JSON error and retry.

FIRST VIEWPORT: Toolbar above the existing graph/sidebar. Reuse the normally
hidden inline feedback beneath it for current JSON recovery; keep active graph
validation separate. No new panel, control, layout, CSS or source preview.

FORM: Code-led local hardening; seed key not applicable, no comp/new world,
imagery or motion. Signature behavior is cross-source current-intent ownership.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

Absent global design documents are pre-existing drift, not permission to repair.

### Completed-hardening evidence (Loop 283)

The implemented change in `web/app.js` coordinates JSON reads, example fetches
and response-body parsing, and Skill staging/compilation under current authoring
intent. `web/index.html` associates Load JSON and Load Example with the existing
inline feedback. `web/styles.css`, the toolbar/canvas/inspector composition,
native controls and visual vocabulary are unchanged. This is a local hardening
of the incumbent Operate surface, not a new visual world or execution capability.

Keep these surface-local ownership and recovery rules:

- **Latest choice owns immediately:** a JSON, example or Skill selection takes
  ownership before its bytes arrive. Revision and operation-identity guards
  discard obsolete success, failure, body parsing and embedded-example fallback
  results. Abort obsolete example/compile work when supported; revision fencing
  still protects example loading when `AbortController` is unavailable. Only the
  owning unavailable example may install the existing embedded fallback.
- **Edits and snapshots outrank imports:** even an uncommitted inspector input
  invalidates pending work. Connection changes invalidate it too; serialized
  graph/DSL snapshots detect layout and other changes before a result can
  replace the draft. A direct document replacement also abandons pending work.
  Discarding an obsolete result must not repaint status, feedback or validation.
- **Stage, then explicitly compile:** choosing a Skill abandons earlier JSON or
  example work without compiling it. Choosing another document immediately
  cancels an older compile, including while the new file is still being read.
  New selections and document replacement clear staged Skill text, so an older
  source cannot silently remain available for compilation. Explicit Compile
  SKILL and the existing compile-review/diagnostic boundary remain intact.
- **Current failure, adjacent recovery:** a current JSON read or parse failure
  keeps the active graph and its validation list, while the existing status pill
  says “JSON load failed”. Reuse the normally hidden, atomic alert beneath the
  toolbar for the fixed instruction: “Could not load JSON. Choose a valid
  Workflow DSL or LiteGraph JSON file and try again.” Choosing a valid corrected
  document clears the message; JSON and example controls join the existing
  Skill controls' `aria-describedby` association.
- **No source echo or visual expansion:** feedback uses `textContent`, not raw
  parser/network errors, private source excerpts, selected filenames or response
  bodies. The existing red supporting text, 75ch measure, anywhere wrapping and
  canvas resizing accommodate recovery. Preserve the white/neutral, blue-accent
  frame, 340px desktop inspector, 900px stacked breakpoint and local horizontal
  toolbar scrolling. No panel, control, CSS, motion, image or global token is
  added. DSL authority, export, validation, runtime, publication and credentials
  retain their existing boundaries.

The real delayed loopback example check started its old request at
`1792689065.329822`, loaded the newer JSON at `1792689066.114` and finished the
old response at `1792689077.341155`; the newer graph remained on screen. Visual
evidence under `.impeccable/review/loop283/` is `race-current.jpg` (actual
1280 × 720 viewport after the race), `current-error.jpg` (actual viewport,
current JSON failure), `desktop-error.jpg` (1440 × 1000),
`mobile-error-full.jpg` (390px, retained valid graph), `mobile-long-full.jpg`
(390px, long synthetic filename not echoed and visible Fit keyboard focus),
`reflow-640-full.jpg` (640px, narrow reflow and focus), and
`recovered-desktop.jpg` (1440 × 1000, corrected import with feedback gone).
The builder, fresh finish reviewer and this fresh documenter independently
opened all seven captures. They preserve the desktop/sidebar and narrow/stacked
layout, with wrapping recovery separate from active-graph validation. These are
synthetic review captures, not shipping raster assets; no concept comp, new
imagery or raster provenance obligation is introduced.

True 200% browser/text magnification remains **unqualified**. The attempted
shortcut left actual viewport, device-pixel ratio and feedback font size
unchanged; the 640px capture demonstrates reflow only. The fresh independent
finish reviewer, `loop283_finish_reviewer`, returned **SHIP** in the required
five sections, with no material fixes, explicitly treating this qualification
gap as non-blocking for unchanged CSS and the bounded incumbent feedback row.
The reviewer independently passed all 27 recovery/ownership checks.

The main loop reports the final source gates passed: 1,483 Python tests
(107.576 seconds), 64 Node tests and whole-repository secret hygiene. The fresh
isolated wheel passed with 96 members (SHA-256
`4f87962fcd948821c6c4f7eb234ee9bce1e5da8bbaf42a2ca1df6065d24ef27f`).
The installed editor's `app.js` and `index.html` byte-matched final source. A
separate installed qualifier served that actual editor/vendor and passed all
27 mandatory `--browser-module-tests` checks (12 recovery plus 15 ownership),
alongside ten compile cases, four diagnostic cases, two legacy-helper cases and
two CLI cases. The latest ownership suite also rejected the old installed
pre-optional-cancellation editor as a negative control, demonstrating that the
served-module check does not substitute current source. These are local
qualification gates only; remote feature CI, release preflight and loop-closure
CI are not claimed complete here.

The detector ran once. Its inherited Inter finding and actual graph-canvas grid
advisory are not introduced or canonized by this hardening. `PRODUCT.md`,
`DESIGN.md` and `.impeccable/design.json` remain absent and untouched as
pre-existing drift; the finish wording does not authorize global design repair.

## Current clarification (Loop 281)

Explain safe compile refusals with a known reason, original line when available
and a concrete next edit/reselect/recompile action. Keep the existing draft and
discard stale results after selection/draft changes. No preference reply has
arrived; use the narrow non-executing scope in
`docs/superpowers/plans/2026-10-22-skill-compile-recovery.md`.

THESIS: Make a rejected Skill recoverable without guessing or exposing source.

OWN-WORLD: Preserve the incumbent neutral/white, blue-accent system-sans editor,
native controls, semantic feedback and existing wrapping validation list.

STORY: Choose a Skill, compile, read a safe reason/line, correct the local file,
reselect and explicitly compile again; failure never replaces the active draft.

FIRST VIEWPORT: Keep the canvas/sidebar and narrow stacked layout. Compile
remains in the toolbar; a normally hidden, wrapping inline error directly below
the toolbar makes recovery visible immediately. It is text, not a modal, new
panel or source preview; active-graph validation remains in its own inspector.

FORM: Code-led local clarification, seed key not applicable. No comp, imagery,
motion or new system tokens. Signature behavior is current-source-only feedback.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

Missing global design documents are pre-existing drift and remain untouched.

### Completed-clarification evidence (Loop 281)

The implemented change in `web/app.js`, `web/index.html` and `web/styles.css`
puts a normally hidden compile-feedback row directly below the toolbar. Known
frontmatter refusals now explain the problem, an approximate original line when
available, and how to edit, reselect and explicitly compile again. A refusal
does not replace the active draft or overwrite its separate validation list.
This is an ordinary clarification of the incumbent Operate surface, not a new
visual world, global token system or execution capability.

Keep these surface-local recovery rules:

- **Evidence before specificity:** the editor explicitly requests diagnostics
  and maps only the finite, versioned duplicate-field, invalid-frontmatter and
  unsupported-form categories to fixed copy. A line is shown only when it is a
  safe integer within the selected source's line count; “near line” communicates
  its approximate nature. Diagnostic bodies are bounded to 1 KiB and decoded
  as strict UTF-8 before validation. Unknown, malformed, oversized or unsupported
  evidence stays generic; older/static helpers receive fixed availability or
  update guidance, not a fabricated source diagnosis.
- **No source echo:** render feedback with `textContent`. Never repeat private
  keys, rejected values, source excerpts, paths, raw response bodies or exception
  messages. The next action is to correct the local file, choose it again and
  compile explicitly, not to expose source in a new panel.
- **Current selection, current draft:** abort, selection/revision and serialized
  draft-snapshot guards discard late file reads and compile success/failure
  after selection or draft changes. Reselecting or loading another document
  clears old feedback; corrected successful compilation replaces the draft and
  removes the refusal. Failure keeps active-graph validation independent.
- **Adjacent text, not another panel:** associate Choose SKILL.md and Compile
  SKILL with the feedback through `aria-describedby`; use an atomic `role="alert"`
  for the result. Preserve native controls, the white/neutral and blue-accent
  frame, and the existing status pill. The plain error row reuses semantic
  danger (`#b42318`), 12px supporting text with 18px line height, a 75ch maximum
  measure and anywhere wrapping. Its measured contrast against white is 6.57:1.
  It adds no card, accent stripe, imagery, motion, shadow or global token.
- **Make room for the message:** showing or hiding feedback resizes the actual
  graph canvas below the header. Keep the incumbent 340px desktop inspector
  and 900px stacked breakpoint; long recovery copy wraps without document-level
  overflow at 390px and 640px. Horizontal toolbar scrolling remains local.
  Validation, export, runtime and DSL authority remain unchanged.

Visual evidence under `.impeccable/review/loop281/` is `desktop-full.jpg`
(1440 × 1000, duplicate-field refusal), `current-full.jpg` (actual 1280 × 720
viewport, the same refusal), `mobile-full.jpg` (390px, duplicate refusal and
valid active graph), `mobile-long-full.jpg` (390px, longer unsupported-form
guidance and visible Fit keyboard focus), `reflow-640-full.jpg` (640px, long
guidance), and `corrected-desktop.jpg` (real corrected upload success, with the
old feedback gone). The builder and fresh reviewer opened all six; this
documentation pass independently opened all six and checked the desktop/sidebar,
narrow/stacked layout and corrected state. These synthetic-Skill captures are
review evidence, not shipping raster assets; no raster provenance or concept
comp is introduced.

True 200% browser/text magnification remains **unqualified**. The attempted
Super-plus shortcut left the actual viewport at 1280 × 720, device-pixel ratio
at 1, visual scale at 1 and feedback text at 12px. Only the in-app browser and
MCP Apps were available, without a usable zoom capability. The 640px capture
proves narrow reflow, not magnification. The fresh independent finish reviewer
returned **SHIP** in the five required sections (`persistence`, `fidelity`,
`ceiling`, `material_fixes`, `keep`), with no material fixes. The reviewer
explicitly treated this gap as non-blocking for the bounded wrapping feedback
row and unchanged control typography, not as a zoom pass, and independently
passed all 12 recovery module tests.

The main loop reports 1,468 Python tests passed (102.324 seconds), 49 Node tests
passed, and isolated-wheel qualification passed with 95 members (SHA-256
`ee00054793bf83a18d8ee7efff37e62d4b61f374eb4821c22cfc5ef39c278427`). A
separate installed `--browser-module-tests` run supplied four actual backend
reports and passed all 12 recovery tests; 392 baseline acceptance/output
differential cases remained unchanged. These are local qualification gates
only; feature CI, release preflight and closure CI are not claimed complete.

The detector ran exactly once; its `detector.json` records inherited Inter and
validation thick-border warnings plus the actual graph-canvas grid advisory.
None is introduced or canonized by this change. `PRODUCT.md`, `DESIGN.md` and
`.impeccable/design.json` remain absent and untouched as pre-existing drift.
The finish wording above does not authorize creating global design artifacts
or repairing that drift during this narrow refinement.

## Prior clarification (Loop 279)

Explain the existing backend input rejection reasons beside Test input JSON.
Use payload-relative paths, declared types and safe schema constraints; never
repeat rejected values or undeclared input keys. Unknown evidence stays generic.
Preserve all current layout, check-only boundaries, stale-result invalidation
and exports. No preference reply has arrived; use this narrow non-mutating scope.
Acceptance: `docs/superpowers/plans/2026-10-22-input-check-explanations.md`.

THESIS: Turn a blocked input check into a specific, safe next edit.

OWN-WORLD: Preserve the incumbent white/neutral, blue-accent system-sans editor,
native disclosures and existing semantic feedback colors.

STORY: Check a payload, read the reason and declared location, correct JSON,
then explicitly recheck; readiness still never means execution or authorization.

FIRST VIEWPORT: Keep the existing canvas/sidebar and narrow stacked layout.
Explanations wrap in the existing issue list immediately below Check input.

FORM: Code-led copy clarification, seed key not applicable. No new world,
controls, layout, images or motion; current source is the visual authority.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

Preserve missing global PRODUCT.md/DESIGN.md as pre-existing drift, not new work.

### Completed-clarification evidence (Loop 279)

The shipped change is confined to explanation and report-evidence handling in
`web/input-review.js`; `web/index.html`, `web/styles.css`, the graph/sidebar
composition and the existing controls are unchanged. The issue list below
Check input now turns supported backend schema reasons into a next edit instead
of showing the old undifferentiated `input / field` rejection. This is an
ordinary refinement of the incumbent Operate surface, not a new visual system.

Keep these surface-local explanation rules:

- **Declared evidence, specific edit:** required-field guidance is backed by
  the declared parent's `required` list; type guidance uses fixed JSON-type
  language from the declared schema. String-length and numeric bounds appear
  only for compatible types and finite, safely representable constraints.
  Enum failures direct the author to Full input schema without copying values.
- **Payload-relative location:** omit the report's leading `input` segment and
  show a quoted JSON pointer, escaping `~` as `~0` and `/` as `~1`; root guidance
  names the input object. Nested properties and array items resolve through the
  declared contract, not through submitted values.
- **Unknown keys stay private:** undeclared-property guidance names only its
  declared parent object, never the rejected key. Rejected values, arbitrary
  backend messages and unknown reason codes are not repeated. Missing,
  unsupported or inconsistent explanation evidence uses the fixed fallback:
  “Input does not match the contract. Review Full input schema.” Malformed or
  internally inconsistent reports are rejected by the existing safe-error path.
- **Check, correct, explicitly recheck:** the raw-JSON request, ephemeral test
  input, stale-result invalidation, abort/revision/snapshot protections and
  existing mapping diagnostics retain their contracts. The change does not
  run or publish a workflow, resolve credentials, alter exports or establish
  provider availability. Ready still means schema/mapping readiness only.
- **Text within the existing frame:** explanations use `textContent` and the
  existing wrapping issue-list rules. Preserve the current white/neutral
  inspector, blue action, semantic red/green feedback, 6px controls, 12px
  supporting text, monospace JSON and native disclosures; no markup, CSS,
  raster, motion or token vocabulary is added.

Visual evidence under `.impeccable/review/loop279/` includes
`desktop-top.jpg` (1440 × 1000, primary desktop header and diagnostic),
`current-full.png` (actual 1280 × 720 viewport), `mobile-full.png`
(390 × 2358), `mobile-long-full.png` (390 × 2604, long declared field), and
`reflow-640-full.png` (640 × 2445, narrow reflow). `desktop-full.png` and
`desktop.jpg` are earlier scrolled supplemental desktop views, not substitutes
for the top-of-page evidence. The builder opened all captures; this
documentation pass independently opened the primary desktop, actual viewport,
long mobile and 640px views. They retain the desktop sidebar and narrow stacked
layout, with the new diagnostic wrapping beside the existing check boundary.
These synthetic-input captures are review evidence, not shipping raster assets;
no new asset provenance is required. The scoped code-led refinement did not
introduce a concept comp or a new QUALITY BAR artifact.

True 200% browser/text magnification remains **unqualified**: the attempted
native Super-plus shortcut had no observed effect. The 640px capture proves
narrow reflow only and must not be described as magnification evidence. The
fresh independent finish reviewer, `loop279_finish_reviewer`, returned **SHIP**
in the required five-section review with no material fixes, explicitly treating
this qualification gap as non-blocking for the unchanged-CSS, JavaScript-copy-only
scope. That reviewer decoded the required captures and independently passed
all 15 input-review module tests.

The main loop also reports 1,445 Python tests passed (100.778 seconds), 37 Node
tests passed, isolated-wheel qualification passed with 94 members, and a separate installed
`--browser-module-tests` run passing eight real backend reports and all module
checks. The ordinary source real-report test body runs only when its fixture
environment is supplied; the installed qualification supplies actual reports.
These are local gates, not a claim that remote feature/release or roadmap-closure
CI has completed.

The once-run `detector.json` reports inherited Inter use and an advisory for the
actual graph canvas grid; neither is newly introduced or canonized as a rule.
`PRODUCT.md`, `DESIGN.md` and `.impeccable/design.json` remain absent and untouched
as pre-existing documentation drift. The finish wording above does not authorize
inventing global design artifacts or repairing that drift during this refinement.

## Prior extension (Loop 275)

Add workflow-level input review and a local draft preflight before the existing
node parameters. Preserve the canvas, node editing, HTTP inspection, download
contracts and light system-sans/blue language. No new world or runtime authority.
The user was offered contract-plus-preflight versus contract-only; no further
preference has arrived, so implementation follows the non-mutating combined path.
Acceptance: `docs/superpowers/plans/2026-10-22-editor-input-preflight.md`.

## Direction contract

THESIS: Let an author see the required input and check a candidate payload while
staying beside the draft graph, without turning validation into execution.

OWN-WORLD: Inherit white/neutral form surfaces, the existing blue action and
semantic feedback colors, system sans labels, 6px controls and native disclosure.

STORY: Open Workflow input, review declared fields or the absent-contract note,
check non-secret JSON, correct a named field/mapping, then export the unchanged
draft. Loading another workflow clears the test payload and old result.

FIRST VIEWPORT: Keep the graph at left on desktop and the scrolling inspector
at right. Workflow input leads the inspector before Node; a declared contract
opens it. On mobile/actual 810px width it follows the existing graph and wraps
all names. Check input sits directly below its labeled textarea and above the
live result, not in a modal or the already crowded toolbar.

FORM: Code-led local extension of the incumbent Operate surface. No concept
seed applies (seed key: not applicable); no visual-world replacement, imagery,
animation or global token change. Signature interaction is stale-result
invalidation on edits/replacement, followed by explicit recheck.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

This ordinary extension preserves incumbent design files; missing global
PRODUCT.md/DESIGN.md is pre-existing drift, not permission to invent either.

### Completed-extension evidence (Loop 275)

The implemented disclosure in `web/index.html` leads the Node inspector, with
declared field/type/required text, a nested read-only schema, labeled test JSON,
adjacent Check input/Clear input actions, and a polite live status. Its visible
boundary copy distinguishes checking from execution, publication, credential
resolution and provider availability. This is an extension of the incumbent
Operate component language, not a new design system.

Source comparison: `web/styles.css` retains its root palette, incumbent sans
stack, 340px desktop inspector and 900px single-column breakpoint. The new panel
reuses white/neutral fields, blue accent and semantic green/red feedback, 6px
controls, 12px supporting text and monospace JSON. Its 14px native summary,
wrapping names, flexible action row and visible blue focus outlines fit the
existing inspector. No global token, display-face, shadow or motion vocabulary
is introduced.

Preserve these surface-local rules:

- **Contract before parameters:** keep workflow input ahead of Node, opened for
  a declared schema; no-schema and graph-only sources get explicit explanations.
- **Check, never run:** keep Check input beside the ephemeral JSON field and its
  boundary copy. Ready describes schema and required mapping-source readiness
  only, never authorization or provider success.
- **Recheck after change:** `web/input-review.js` invalidates results on input
  edits, clear, document replacement and editor changes; abort/revision and
  snapshot checks prevent stale readiness. `web/app.js` supplies the validated,
  synchronized current draft rather than making the graph a new authority.
- **Private draft, explicit availability:** reset clears input on document
  replacement; exports remain separate from the panel state. Static hosting
  explains the installed helper requirement instead of presenting a pass.
- **Text, not markup:** field names, issue paths and mapping sources render as
  text; long content wraps within the existing responsive inspector.

Visual evidence is the existing native-viewport capture set under
`.impeccable/review/loop275/`: `desktop.png`, `mobile.png`, `mobile-input.png`,
`user-811.png` and `user-input.png`. Desktop, mobile-input and current-width
input captures were inspected during documentation; they show the graph and
input panel retaining their desktop/sidebar and narrow/stacked relationships.
These are synthetic-input review captures, not shipping product raster assets.
The finish-review handoff reports **ship**, with no material fixes. Native
viewport captures plus complementary scrolled input views are the scoped
evidence; the unavailable full-page browser API is not claimed as exercised.

No actual system drift is introduced by this extension. The once-run
`detector.json` records inherited Inter and validation-list side-stripe warnings
and the actual-canvas grid advisory; none becomes a new reusable design rule.
`PRODUCT.md`, `DESIGN.md` and `.impeccable/design.json` remain absent and untouched
as pre-existing documentation drift. This documentation check does not claim
completion of the main loop's Python, CI or release qualification gates.

## Current hardening (Loop 271)

Keep Save Graph exports compatible with strict CLI write-back by materializing
actual live titles, including registered defaults. Do not invent replacement
text for blank titles or relax identity/topology checks. Synchronize pending
parameter edits before serialization in both DSL-backed and graph-only modes. Preserve the existing
editor world and all HTTP inspection behavior. Save feedback must distinguish a
completed graph export from validation alone. This is a scoped harden → polish
correction, with no visual redesign or global context rewrite. Acceptance:
`docs/superpowers/plans/2026-10-22-graph-export-titles.md`.

## Prior hardening (Loop 270)

Preserve configured versus omitted HTTP fields when inspecting, editing, and
saving a node. Unchanged controls must not create a body, headers, method, or
request object. Apply changed fields atomically; reverting restores the selected
baseline. Errors explain explicit reset values. Existing assertion review,
write-back permissions, and the incumbent light/system-sans/blue visual language
remain authoritative. Follow the scoped harden → polish playbooks; this is a
behavioral correction, not a new surface or visual world. Current acceptance:
`docs/superpowers/plans/2026-10-22-http-inspector-roundtrip.md`.

## Prior extension (Loop 268)

## Scope

The editor currently hides HTTP request fields for `http_assert` nodes.
Add a read-only review above the ordinary node fields: method/endpoint,
typed JSON expectations, success/failure destinations from the source DSL,
and expandable complete connector configuration. Selection changes clear the
review. Plain HTTP editing and all write-back permissions retain their contract.
No endpoint requests, credential resolution, new graph authority, or runtime
semantics are introduced.

## Direction contract

THESIS: Let an operator review why this node allows or blocks progress at the
moment they select it. The selected node's actual criteria lead the panel.

OWN-WORLD: Preserve the incumbent light editor, blue accent, neutral form
surfaces, system sans, 6px controls, and standard details disclosure.

STORY: Select a result-check node, read the endpoint and every expected JSON
value, then follow the named match/mismatch destinations. Expand configuration
only when reviewing headers, mappings, or credential handles.

FIRST VIEWPORT: Existing graph at left and inspector at right on desktop;
the new review leads the inspector before generic fields. At narrow widths
it follows the graph in the incumbent single-column layout. Long values wrap.

FORM: Scoped Operate-mode extension of the existing inspector. No concept seed
or new visual world; the existing surface is authoritative. Selection reveals
the review immediately; there is no decorative motion or new primary action.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

This is an ordinary extension: preserve existing design-system files and use
the incumbent code as visual evidence; no new global visual identity is approved.

## Acceptance

Execute the renderer against real-shaped fixtures and DOM stubs: typed scalar
values and hostile strings render as text, not markup; selecting another node
clears stale data; rendering never mutates bindings. Browser verification uses
an imported synthetic Skill, node selection, read-only controls, and unchanged
DSL export. Capture desktop, mobile, and actual viewport in one inspection
batch, with at most one correction round. Finish review and documentation
follow the Impeccable workflow. Full package/CI gates close the loop.

```bash
node --test tests/test_assertion_inspector.cjs
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-loop268
```
