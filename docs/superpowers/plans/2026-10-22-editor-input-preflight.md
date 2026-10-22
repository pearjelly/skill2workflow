# Loop 275: Draft Input Review In The Editor

## Evidence And Scope

The current editor imports and preserves Skill `input_schema`, but offers no
workflow-level input contract review or local input preflight. Authors must
leave the visual authoring path to inspect generated JSON and validate payloads.
The open GitHub issue inventory is empty at selection; this loop is based on
the approved visual-authoring goal and direct source/browser inspection.

Extend the incumbent Operate surface without redesigning the editor. Add a
workflow-input disclosure before node parameters: declared field/type/required
summary, expandable complete read-only schema, ephemeral non-secret JSON input,
and an explicit Check input action. Use the existing Python preflight builder,
not a browser schema engine. The graph/DSL remains authoritative and unchanged.

One fixed local endpoint accepts exactly a draft Workflow DSL and optional
object input, with bounded strict JSON and fixed refusal messages. It reuses
finite canonical input normalization, structural validation and the existing
value-free preflight report. No service proxy, token lookup, publication, run,
audit, credential resolution, external request or file output is permitted.
The endpoint remains available with no live service configured.

## Interaction And Safety

The panel distinguishes absent schema, graph-only source, unchecked, checking,
ready, blocked, invalid JSON, unavailable local helper and failed response.
Raw input stays in this tab, is never part of DSL/graph downloads or local
storage, and clears on document replacement. Input edits invalidate results.
Before checking, synchronize allowlisted node edits and validate the current
draft. A response must match the current draft/input snapshot; stale responses
cannot repaint ready after loading another file or editing the draft. Hostile
names and issue paths render as text, not markup. Ready means input schema and
required mapping-source readiness only, not authorization or provider success.

Preserve inspector behavior, export/write-back, no-source graph behavior and
standalone static usage. Static hosting explains that Check input requires the
installed UI helper; it never silently claims local validation passed.

## Verification

Tests precede behavior changes. Cover real local HTTP request boundaries,
omitted/corrected/typed-invalid inputs, missing nested mappings without schema,
finite/byte/property/report bounds, strict JSON, fixed refusals, response cache
policy, no controller/provider calls and input immutability. Browser regressions
exercise rendering, no secret/value echo, loading/reset/stale response behavior,
offline states and export isolation. Mandatory isolated-wheel qualification
must call the installed endpoint rather than source imports.

Use Impeccable's incumbent visual authority, batched desktop/mobile/actual-width
inspection with at most one builder correction pass, one mechanical detector,
fresh finish review and documenter handoff. No new visual world or raster asset.
Run full Python/editor regressions, installed qualification, seven CI jobs and
complete production-baseline release preflight. Keep the broad goal active and
Self-hosted Beta maturity unchanged.

## Implementation And Local Qualification

Implemented the read-only contract disclosure and ephemeral input check beside
the existing node inspector. The fixed local endpoint delegates to the existing
preflight builder. Raw input JSON is retained across the browser request so a
large integer is not silently rounded by JavaScript; no input enters DSL or
LiteGraph exports. Source/input changes invalidate pending and completed checks.
Static HTTP 404/405/501 responses explain the installed-helper requirement.

Backend and browser tests were red before implementation. Package qualification
also caught the new asset missing from package data, then the strict release
manifest allowlist; both were corrected without relaxing the allowlist.

- Full Python suite: 1,420 tests passed in 127.136 seconds.
- Editor regressions: 30 passed, including the final static-hosting cases.
- Focused backend, packaging, manifest and documentation tests: 86 passed.
- Source and mandatory installed smoke: five cases plus module delivery passed.
- Final isolated wheel: 94 members, SHA-256
  `0c1dd2d2063c3e87ec9db42dfa2639561ab796782ba5670dc814d4817a9ebfe4`.
  Its installed backend and four changed editor assets match source byte-for-byte.
- Repository and example secret hygiene: zero findings; diff checks passed.

Actual browser verification imported and compiled the real typed-input Skill,
observed blocked and corrected-ready states, and downloaded both formats. The
DSL equals compilation, the graph retains that same source, strict write-back
is unchanged, and neither download contains the synthetic test input. A plain
static server's real POST 501 correctly produces the unavailable-helper state.
Only owned loopback services and synthetic values were used; all preview
services and the temporary browser tab were closed afterward.

Impeccable preserved the incumbent light, system-sans editor rather than adding
a new visual direction. One detector pass found only legacy advisories. A fresh
finish reviewer returned `ship` with no material fixes, reaffirmed after the
static-status branch correction; the documenter updated only the surface brief.
The five reviewed desktop/mobile/current-width captures are native viewport
captures with complementary scrolled views, not full-page screenshots. The
browser's full-page capture limitation was explicitly disclosed in review.

## Remote Qualification

Pending exact feature-commit CI and production-baseline release preflight.
