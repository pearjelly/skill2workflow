---
version: 1
slug: "web-index-html"
primary_target: "web/index.html"
related_targets: ["web/app.js","web/input-review.js","web/styles.css"]
---

# Workflow Editor — Operate

## Current clarification (Loop 279)

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
tests passed, 94 isolated-wheel checks passed, and a separate installed
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
