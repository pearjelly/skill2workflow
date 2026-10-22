# Loop 268: HTTP Assertion Inspector

## Scope

The editor currently hides HTTP request fields for `http_assert` nodes.
Add a read-only review above the ordinary node fields: method/endpoint,
typed JSON expectations, success/failure destinations from the source DSL,
and expandable complete connector configuration. Selection changes clear the
review. Plain HTTP editing and all write-back permissions retain their contract.
No endpoint requests, credential resolution, new graph authority, or runtime
semantics are introduced.
Keep the desktop canvas within the viewport while the inspector scrolls, and
anchor hidden file inputs to their labels to prevent mobile body overflow.

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

## Implementation And Review

The new panel renders typed values as literal text, clears all prior data when
selection changes, and uses source DSL for named success/failure destinations.
Complete connector configuration remains available in a readonly disclosure;
existing HTTP editing and all write-back permissions are unchanged. Expected
values and literal headers are stored configuration, not a secret store.

Five executable JavaScript renderer tests cover typed values, hostile strings,
non-mutation, stale clearing, absent source data, and malformed JSON-shaped
methods/destination titles. The malformed-value regression reproduced a
coercion failure before guarded rendering fixed it. Python tests lock the
readonly markup and integration; the release artifact CI job executes the
JavaScript tests without adding Python runtime dependencies.

Browser checks imported a synthetic Skill, selected the check node, verified
readonly controls and configuration disclosure, and exported an unchanged,
valid connector with unchanged success/failure destinations. Desktop 1440×1000,
mobile 390×844, and actual 811×895 CSS viewports were inspected. Actual-width
full-page capture changed viewport-height layout, so it was replaced with
three overlapping viewport captures covering the entire document.

The independent full review accepted that corrected evidence and requested
one type-coercion fix. Its subsequent verdict scored that fix resolved and
returned `ship`; that verdict covers the listed fix, not a new whole-surface
certification. The documentation handoff compared the addition with incumbent
CSS and confirmed no new global design system was needed. Existing unrelated
visual advisories were preserved rather than redesigned.
