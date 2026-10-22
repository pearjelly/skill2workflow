---
version: 1
slug: "web-index-html"
primary_target: "web/index.html"
related_targets: ["web/app.js","web/styles.css"]
---

# Workflow Editor — Operate

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
