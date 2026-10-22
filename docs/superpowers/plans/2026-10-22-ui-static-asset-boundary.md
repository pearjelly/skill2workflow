# Loop 276: Fixed UI Static Asset Boundary

## Evidence And Scope

Loop 275 completed real authoring input checks. Current source inspection shows
that `serve_ui` still delegates all unmatched GETs and every HEAD to Python's
general directory server. Its root is the checkout or installed data directory,
despite the public promise to serve only editor assets and non-sensitive examples.
The issue inventory is empty; the previous loop is verified progress.

Reproduce only with synthetic files in an owned temporary root, never by reading
real credentials. Replace general directory access with the exact packaged UI
asset inventory. Keep both pages, all dependencies, examples, fixed local helpers
and live API routes unchanged. Root/web aliases may show the editor, never a
directory listing. GET and HEAD share the same static admission boundary.

Use descriptor-relative no-follow reads on supported operating systems, reject
symlink components and non-regular/oversized files, and bound the bytes before
responding. Refusals are fixed, value-free and no-store, including HEAD metadata.
Unknown, traversal, encoded and absolute-form paths must not become filesystem
access. Do not add an arbitrary file browser or dynamic asset registration.

## Verification

Write failing real HTTP tests before implementation. Cover every admitted asset,
GET/HEAD parity, aliases, query cache-busting, unknown neighbors, directory and
hidden paths, encoding/traversal, symlinks, special files and a replacement race.
Keep the runtime allowlist equal to strict release-manifest data membership.
Mandatory installed-only qualification must prove public serving and private-file
refusal outside source imports. Run focused and full suites, editor regressions,
isolated-wheel qualification, seven CI jobs and complete release preflight.

No frontend markup, styling, execution truth, DSL, service ingress or maturity
change. Keep the broad goal active and Self-hosted Beta unchanged.

## Implementation And Local Evidence

The initial real HTTP regression returned 200 for a synthetic private neighboring
file. HEAD lacked fixed refusal headers and no runtime asset inventory existed.
The tests failed before the server changed; no real private file was requested.

The product server now admits the exact 26-member release UI/example inventory.
Every admitted file is read through pinned, no-follow directory/file descriptors
and checked as a regular file, with an 8 MiB metadata and actual-read bound.
Missing OS primitives fail closed rather than falling back to path-based access.
No directory listing, source/development metadata or arbitrary neighbor is served.
The boundary does not defend a compromised installation or trusted public asset
intentionally rewritten by an actor with local write authority.

GET and HEAD share static admission. Refusals are fixed 404 JSON with no-store,
nosniff and no path/value echo; HEAD sends metadata without a body and never
invokes a live proxy. Root aliases redirect to `/web/`, preserving relative
browser asset URLs. An additional raw malformed-URL regression first reproduced
an uncaught parser exception, then passed with the same fixed refusal.

Eleven new tests cover every public file byte-for-byte through GET/HEAD, aliases,
cache-busting queries, private neighbors, directory listings, path encodings,
traversal, malformed targets, symlinks, special/oversized files, a leaf swap, a
parent-directory swap and unavailable no-follow support. The runtime inventory
must equal strict release-manifest membership. Existing live routes, local
authoring helpers and all frontend files remain unchanged.

Mandatory installed qualification runs ten HTTP cases with the selected wheel
CLI outside the checkout, without source imports. It creates a synthetic private
neighbor inside the disposable installation, proves exclusion, and removes it
afterward. Incomplete or false evidence fails the package gate.

The final isolated wheel passed qualification with 94 members, SHA-256
`4765161e948d58a254ffaadd2a121443a593f0a86cc8d57cfae323554474e81e`,
at `/tmp/skill2workflow-package-loop276-final`. Its installed `ui.py` matches
source byte-for-byte; a separate installed ten-case drill also passed. All 30
editor regressions, repository secret hygiene and whitespace checks passed.
The initial intermediate wheel preceded the redirect/parser fix and is not used
as final-source evidence. All temporary HTTP processes were closed by the drills.

The complete Python suite passed 1,431 tests in 134.412 seconds. Thirty focused
static-boundary, installed-UI, packaging and package-gate tests also passed.

## Remote Qualification

Pending exact feature-commit CI and complete production-baseline release
preflight. No tag, package release or maturity promotion is authorized by this
loop's completion.
