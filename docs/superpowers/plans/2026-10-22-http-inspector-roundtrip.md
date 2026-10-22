# Loop 270: Intent-Preserving HTTP Inspector

## Problem And Scope

Selecting an HTTP node and saving without edits currently inserts omitted
method, headers, and body fields. A bodyless GET gains `{}` as a request body;
an unconfigured legacy connector becomes a configured but invalid request.
Invalid JSON/timeout edits can also partially mutate earlier request fields.
Eight executable browser-code tests reproduce seven failures before changes;
a real compiled-Skill export independently demonstrates the extra fields.

Preserve original HTTP request values and property absence until the operator
changes a control. Build request edits from the selected node's baseline and
commit only after all changed controls validate. Reverting the controls restores
the baseline, including omitted fields. Selection changes reset that baseline.
Explicit JSON values (including null/false/zero/empty string) remain data.

Blank fields represent omission, not generated defaults. Clearing a previously
declared value requires an explicit replacement: GET for method, `{}` for
literal headers, `null` for no body, and 0 for the runtime's default timeout.
Give actionable errors rather than silently retaining a cleared payload.
No backend field-deletion protocol, write-back allowlist, connector identity,
HTTP transport, runtime policy, credential access, or topology is changed.

## Interface Direction And Verification

This is a scoped Operate-mode hardening pass using the Impeccable harden →
polish playbooks. Preserve the incumbent light/system-sans/blue editor and
existing controls. Only absent-field presentation, reset guidance, validation,
and intent-preserving editing change; no new visual world or global design
system is approved. Inspect the existing rendered surface before editing.

Use executable JavaScript tests for complete render/sync/export behavior,
then real mouse/keyboard browser interaction. Verify a compiled bodyless
request saves unchanged, edits/reverts preserve omission, invalid JSON does
not export, and explicit null sends no body. Review wide, narrow, and actual
window captures in one batch, with at most one correction round. Run the
requested detector once after the UI is finished. No unrelated cosmetic drift
is repaired. Full Python, installed package, CI, and release gates close the loop.

```bash
node --test tests/test_*inspector.cjs
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-loop270
```

## Implementation And Local Evidence

The inspector snapshots the selected HTTP request and raw control values.
Unchanged saves restore that baseline; changed controls build a separate copy,
which replaces the request only after every change validates. A selection reset
discards the old baseline. This preserves mappings, retention, credentials and
origin constraints without making any backend field-deletion promises.

Nine executable regressions run the actual complete editor IIFE in a Node VM,
exercise render/sync/DSL export, and use string-coercing form controls. Together
with the five assertion-inspector cases, all 14 pass. CI and contributor checks
now run both inspector suites. Python checks also cover reset/omission guidance
and its accessible field descriptions.

A real locally compiled synthetic Skill was selected and exported in the
browser. The unedited and edit/reverted exports deep-equal the original HTTP
binding; an explicit `null` body adds only that property. Invalid JSON visibly
blocks saving. Executing all three downloaded requests through a mocked HTTP
transport proves GET, `data is None`, and no generated Content-Type. No reserved
endpoint was contacted and no real credential was used.

One batched inspection covered 1440×1000, 390×844 and the actual 1280×720
window. The hint and controls wrap within the existing inspector; mobile page
width and scroll width both measure 390, and browser error logs are empty.
Screenshots are local review evidence under `.impeccable/review/loop270/`.
No additional cosmetic correction or redesign was needed.

The one required static detector pass reported the incumbent Inter font and
warning-panel left border, plus the existing canvas grid advisory. None is
introduced by this change. They are retained as narrow scope exceptions rather
than changing the existing visual world or suppressing detector rules.

The isolated installed wheel passed all qualification with 92 members,
SHA-256 `22a5cb32edbc9567581893fa7a24440d6cd337682e1ce84fa415ef59ff151ae0`.
Its three modified editor assets match the source byte-for-byte. Repository
secret hygiene and whitespace checks pass.
The complete local Python suite passed 1,376 tests in 119.239 seconds.

## Remote Qualification

Qualified implementation: `7c189b8728b8eb6f5152db84d6a1b72193165718`.
[CI](https://github.com/pearjelly/skill2workflow/actions/runs/39724125808)
passed all seven jobs, including Python 3.9/3.14, Docker, systemd, user journeys,
recovery/state safety, and release artifacts with both inspector suites.
[Release preflight](https://github.com/pearjelly/skill2workflow/actions/runs/39724137298)
passed the complete production-baseline dry-run on Python 3.9.25. No tag,
package release, provider pilot, or maturity promotion was performed.

## Separate Follow-Up Evidence

An additional Save Graph → CLI write-back probe rejected the browser's graph
because default Start/Failure/End node titles are omitted by LiteGraph
serialization (`graph node start title must not be empty`). Save DSL retains
the source titles and the verified HTTP behavior above. This existing graph
export/default-title boundary is not claimed fixed here and should be the next
authoring delivery investigation, with a regression before any correction.

Subsequently resolved by [Loop 271](2026-10-22-graph-export-titles.md), which
retains this failed probe as historical evidence rather than changing its result.
