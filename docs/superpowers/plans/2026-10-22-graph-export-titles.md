# Loop 271: Write-Back-Ready Graph Export

## Problem And Scope

The actual bundled LiteGraph serializer deliberately omits a node title when
it equals the registered type default. Save Graph forwards that omission,
whereas CLI write-back requires an explicit non-empty title. A downloaded
approval graph fails with `graph node start title must not be empty`.
This was independently observed during Loop 270 and reproduced before changes.

Materialize each live node's actual title in the downloaded graph only. Do not
patch the pinned vendor, infer text from a type/old DSL, repair explicit blank
titles, or weaken the write-back identity/topology/allowlist boundaries.
Preserve custom titles, selected edits, source DSL, graph-only exports, and
the existing HTTP omission contract. Give Save Graph an honest success status.
Another red-green regression proves Save Graph serialized before synchronizing
pending node timeout/retry-backoff controls. Synchronize first in both DSL-backed
and graph-only modes, then serialize and embed the same current edit state.
No new graph authority, runtime behavior, dependencies, credential resolution,
or endpoint requests are introduced.

## UI Direction And Verification

Scoped Operate-mode harden → polish using the incumbent editor. No palette,
typography, layout, or control is redesigned; only export fidelity and save
feedback change. Inspect the actual pre-fix surface and retain the existing
design conventions. One batched desktop/narrow/actual-window review, at most
one correction round, and one required detector run bound the visual work.

Load the complete actual editor and pinned LiteGraph source in Node VM tests,
not a replacement serializer. Test default and customized titles, all registered
types, graph-only mode, repeated reload/save, non-mutation, real Python CLI
write-back, blank/identity/topology rejection, and invalid-inspector refusal.
Six regression cases fail against the unchanged implementation before edits;
a seventh fails against the title-only correction on pending form edits.
Qualify real browser Save Graph downloads with installed CLI write-back and
compare the result to Save DSL. Keep source metadata and execution fields.

```bash
node --test tests/test_*.cjs
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-loop271
```

Full tests, isolated-wheel asset verification, all CI jobs and production-
baseline release preflight close this delivery loop. Overall maturity remains
Self-hosted Beta; this is not a version release or general graph-editing expansion.

## Implementation And Local Evidence

Save Graph now synchronizes the selected form before serializing. DSL-backed
and graph-only modes both reject invalid inputs without downloading a partial
artifact. The new serialized node objects receive their live titles, not text
inferred from a type or from old DSL. The existing serializer and strict Python
write-back validator are unchanged. Successful download preparation sets the
existing status badge to `Graph saved`; the surface's layout and styling remain
unchanged.

Seven graph-export cases load the complete real editor and pinned vendor in a
Node VM. They call the actual Python write-back CLI in temporary directories,
including repeated reload/export, type-default and multilingual custom titles,
pending timeout/backoff edits in both source modes, and unchanged rejection of
explicit blanks, forged identities and topology edits. Together with the prior
inspector suites, all 21 JavaScript tests pass. CI and contributor commands now
include all `tests/test_*.cjs` suites.

The real browser's unedited approval graph passes the installed CLI and returns
the entire original DSL unchanged. After editing a Chinese/Arabic/emoji title,
node timeout 1234 and retry backoff 25, the CLI result deep-equals both Save DSL
and the graph's embedded source workflow. This verifies the originally failing
artifact handoff rather than only testing an in-memory substitute.

One batched visual review covered 1440×1000, 390×844 and the actual 1280×720
window. The existing keyboard-accessible toolbar keeps the success badge visible
at each size; narrow document width and scroll width both measure 390. The
existing horizontal toolbar scrolling remains available, browser error logs
are empty, and no visual correction was needed. Local review screenshots are
under `.impeccable/review/loop271/`. The one required detector pass on the only
changed UI file (`web/app.js`) returned no findings. No global design drift or
incumbent stylesheet was changed or suppressed.

The full local suite passed 1,377 Python tests in 120.668 seconds. The final
isolated wheel passed all qualification with 92 members in
`/tmp/skill2workflow-package-loop271-final`, SHA-256
`db3787c56e146126c463a790a46fb11fa763afb4137898b3162289735621d9cc`.
Its editor script matches the final source byte-for-byte. An earlier title-only
wheel passed but was superseded after the pending-form regression; it is not
the qualified final artifact. Repository secret hygiene and whitespace checks
also pass.

## Remote Qualification

Qualified implementation: `a48146c285350aa1bfb95bf7c6fda6184bb661ac`.
[CI](https://github.com/pearjelly/skill2workflow/actions/runs/39726479156)
passed all seven jobs, including Python 3.9/3.14, the real LiteGraph/export and
inspector suites, isolated artifacts, Docker, systemd, user journeys and recovery.
[Release preflight](https://github.com/pearjelly/skill2workflow/actions/runs/39726487759)
passed the complete production-baseline dry-run on Python 3.9.25. No tag,
release, provider pilot or maturity promotion was performed.
