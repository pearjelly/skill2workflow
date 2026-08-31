# Installed Static UI

The wheel includes the dependency-free LiteGraph editor and control-plane
inspector. After installing `skill2workflow`, start the UI without returning to
the source checkout:

```bash
skill2workflow ui --host 127.0.0.1 --port 4173
```

Open:

```text
http://127.0.0.1:4173/web/
http://127.0.0.1:4173/web/control.html
```

The server is loopback-only by default and serves static editor assets and
non-sensitive example JSON. It does not read runtime state or the service state
directory, resolve credentials, expose an ingress token, or mutate workflows.
The LiteGraph JavaScript and stylesheet are bundled at a pinned local path in
the wheel, so the editor works without CDN access or general internet egress.
Their upstream version, MIT notice, and SHA-256 digests are recorded beside the
assets at `web/vendor/litegraph-0.7.18/`; no browser dependency is fetched at
runtime.
The editor's **Compile SKILL** action is the one local authoring exception: it
accepts one bounded 2 MiB `SKILL.md` in memory and returns a draft Workflow DSL
document without writing, publishing, executing, or contacting the service.
Its generated source reference is the fixed `SKILL.md`, not a browser file
path. The browser decodes the selected bytes as strict UTF-8, so invalid source
files are rejected instead of silently being rewritten. The control-plane page still accepts an exported snapshot file; by
default it is not a live authenticated service console.

Successful Skill compiles also display a bounded, source-free **SKILL Compile
Review** with inferred node counts and fixed missing-control notices. It is an
authoring prompt only: it does not inspect business intent, change the draft,
validate a real-world action, publish, or execute anything.

For an explicit live view of one running service, configure both the
service origin and its owner-only ingress token file:

```bash
skill2workflow ui \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /run/secrets/skill2workflow-ingress-token
```

The control-plane page's **Load Live Snapshot** action then calls the UI's
fixed same-origin `/api/v1/control-snapshot` route. The UI process reads the
token server-side for each request and forwards only that bounded, authenticated
snapshot request; the browser never receives the token, and arbitrary service
paths are not proxied. Live responses remain read-only, `no-store`, and subject
to the service's bounded snapshot window. If either option is omitted, the live
route is unavailable and static/example/file loading continues to work.

The scope bar also reports the fixed live service probe: `ready`, `not ready`,
`unavailable`, or `static mode`. That badge comes from the UI's
same-origin `/api/v1/service-probe` route, which only composes the existing
`/healthz` and `/readyz` endpoints. It is diagnostic only; the ingress token is
used for the snapshot route and never sent to the browser.

When live mode is configured, **Auto-refresh** can be enabled explicitly. It
refreshes the live snapshot at the fixed 10-second interval, skips requests
while the page is hidden, and preserves the last valid snapshot if a refresh
fails. Switching back to the example or loading a file stops the timer. Static
mode disables the control.

The **Download Support Bundle** action is also available only in live mode. It
fetches the fixed same-origin `/api/v1/support-bundle` route and downloads the
existing bounded, redacted `skill2workflow-support-bundle-0.1.0` artifact. The
route is read-only and uses the protected token file server-side; it does not
upload the bundle or proxy arbitrary service paths.

When a live snapshot run is selected and its status is `waiting`, the detail
panel exposes **Approve run** and **Reject run**. Each action requires an
explicit browser confirmation and sends only the fixed boolean decision to the
same-origin `/api/v1/runs/{run_id}/resume` route. The UI process forwards it
with the protected token file, validates the fixed response, and refreshes the
live snapshot; it never stores the token in browser state or proxies arbitrary
paths. Static, example, and file snapshots never expose these controls.

Selecting any live run also loads the fixed, redacted
`skill2workflow-run-detail-0.1.0` projection from
`GET /api/v1/runs/{run_id}`. The browser receives at most the existing 50-event
and 64 KiB contract; the UI validates the run identifier, schema, event window,
and status before replacing the summary JSON with the evidence view. A detail
failure leaves the bounded run summary visible and never blocks the decision
controls or exposes raw state.

For a live run in `created`, `running`, or `waiting` status, the detail panel
also exposes **Cancel run**. It requires an explicit confirmation and sends
only `{}` to the fixed same-origin `/api/v1/runs/{run_id}/cancel` route. The
existing cooperative semantics remain visible in the UI: an in-flight
connector attempt may finish, and the action never claims rollback or forceful
termination. Terminal runs and all non-live snapshots keep the control hidden.

The live Runs view starts with the control snapshot's newest bounded window.
When its `runs` window is truncated, **Load Older Runs** becomes available. Each
explicit click fetches one fixed 100-item cursor page through
`/api/v1/run-page`; the UI validates the `skill2workflow-run-list-0.2.0`
contract, retains at most 500 rows in browser memory, and never accepts a
user-authored service path or filter. Static, example, and file snapshots keep
the control disabled.

When the live `audit_events` window is truncated, **Load Older Audit** provides
the same bounded handoff for the existing redacted
`skill2workflow-audit-event-list-0.1.0` contract. Each click reaches only the
fixed same-origin `/api/v1/audit-page` route, which requests a 100-event page
without forwarding browser-authored filters. The browser validates the
sequence-cursor response, deduplicates events, and retains at most 500 rows;
static, example, and file snapshots never expose the control.

The live console can also load the existing redacted recurring-schedule
inventory with **Load Live Schedules**. It calls only the fixed same-origin
`/api/v1/recurring-schedules` route, validates the
`skill2workflow-recurring-schedule-list-0.1.0` contract, and displays at most
100 schedule rows with status, next-run, interval, missed-run policy, and
compact last-run metadata. Trigger inputs, scheduler lease details,
credentials, and provider payloads never enter the browser; static, example,
and file snapshots keep the control disabled.

Selecting a live schedule also enables **Load Dispatch Evidence**. The first
click reaches only the fixed same-origin
`/api/v1/recurring-schedule-dispatch-pages/{schedule_id}` route; **Load Older Dispatches**
follows the fixed opaque cursor route without accepting arbitrary
queries. The browser validates the bounded
`skill2workflow-recurring-schedule-dispatch-page-0.1.0` contract, retains at
most 500 dispatch records, and highlights `uncertain` outcomes. This is
read-only evidence: it never claims, replays, reviews, or mutates a dispatch,
and it excludes trigger inputs, credentials, lease identities, and provider
payloads.

If a loaded dispatch page contains an `uncertain` record, the review card also
offers **Record Review**. The operator chooses one of the fixed conclusions
`effect_confirmed`, `effect_not_observed`, or `no_conclusion`; the UI reuses the
record's server-provided completion timestamp and requires browser confirmation
before calling the fixed authenticated
`/api/v1/recurring-schedule-dispatch-reviews/{dispatch_id}` route. The service
performs its existing compare-and-swap check and preserves the `uncertain`
dispatch status. A review never replays, claims, or mutates dispatch execution.

The live console also exposes **Load Live Readiness**. It calls only the fixed
same-origin `/api/v1/operational-readiness` route and validates the
`skill2workflow-operational-readiness-0.1.0` contract before rendering the
service, workflow-artifact, audit-integrity, offline-backup, and blocking-reason
rows. The report is read-only and value-free: it contains no paths, workflow
content, run identifiers, lease identities, credentials, or provider data.
Static, example, and file snapshots keep the control disabled.

The **Load Live Workflows** action exposes the existing redacted published
version inventory through the fixed same-origin `/api/v1/workflows` route. It
validates the `skill2workflow-workflow-inventory-0.1.0` contract and displays
at most 100 versions with lifecycle status, stable aliases, and a shortened
checksum for recognition. Workflow names/DSL, artifact paths, timestamps,
credentials, trigger inputs, and provider data never enter the browser;
static, example, and file snapshots keep the control disabled.

After loading a live snapshot, **Stage Workflow** accepts one local Workflow
DSL JSON document. The browser rejects empty or invalid JSON, missing basic
workflow id/version metadata, and over-1 MiB input before it can reach the UI
process; it keeps the staged document only in browser memory and identifies
its bounded workflow id and version. **Check Staged Workflow** is then required
before publication. It sends only the fixed `{"workflow": <object>}` envelope
to `/api/v1/workflow-release-preflights`; the authenticated service performs
the full DSL validation plus a value-free empty-trigger analysis without
persisting an artifact, resolving credentials, or invoking a connector. A
workflow can still be structurally valid while its empty trigger needs input.

Only a successfully checked candidate enables **Publish Staged Workflow**. It
sends the same fixed envelope to `/api/v1/workflow-releases`; the UI process
reads the ingress token server-side and forwards it to the existing publication
route. A successful compact redacted result refreshes the live inventory,
clears the staged document, and never promotes an alias or executes the
workflow. The service remains the Workflow DSL validation and immutable
publication authority. Do not include credentials, access tokens, or business
payloads in the document.

Selecting a live version enables **Review Workflow Plan** through the fixed
same-origin `/api/v1/workflow-explanations/{workflow_id}/{version}` route. The
browser accepts only the `skill2workflow-workflow-explanation-0.1.0` contract
within its bounded 64 KiB response and renders a read-only topology and policy
review. The review contains no Workflow values, instructions, artifact paths,
credentials, trigger inputs, or provider data, and it never invokes a
connector; static, example, and file snapshots keep the action disabled.

The same review card offers **Check Empty Trigger**. It sends only the fixed
empty JSON object `{}` to `/api/v1/workflow-preflights/{workflow_id}/{version}`
and validates the `skill2workflow-workflow-preflight-0.1.0` response. Operators
can see whether the empty trigger is ready, which required inputs or mappings
would block it, and how many connector nodes are involved. No business input is
accepted by this UI action, and the preflight is side-effect-free. For a
currently selected **published** version whose just-loaded empty preflight is
ready, **Start Empty Trigger** becomes available. After a confirmation it sends
only workflow id, exact version, and a browser-generated opaque idempotency key
to `/api/v1/workflow-empty-triggers`; the UI process fixes `source` to
`live-ui`, fixes input to `{}`, and keeps its ingress token server-side before
using the normal protected trigger route. It never accepts aliases or business
input. If the browser cannot determine the outcome, its explicit retry reuses
the same in-memory key and unchanged empty request; it never automatically
retries. The compact receipt contains identifiers and input keys only, and is
shown in the selected workflow's redacted detail envelope.

For workflows that require business input, **Stage Trigger Input** accepts one
local JSON object within the shared 1 MiB input bound. The file remains only in
browser memory. Its values are never rendered by the console; only the
value-free service preflight and compact trigger receipt are shown. **Check
Staged Input** sends the exact id, exact version, and input object to the fixed
`/api/v1/workflow-input-preflights` proxy. It must report ready before **Start
Staged Input** is enabled. That start requires a separate confirmation and
sends the same exact version, staged input, and one browser-generated
idempotency key to `/api/v1/workflow-input-triggers`; the proxy again fixes the
source to `live-ui` and keeps the ingress token server-side. Input becomes
durable run context when accepted: never put credentials, tokens, or sensitive
business data in the JSON file. A manual retry after an uncertain outcome
reuses the same in-memory key and unchanged staged input; the UI never retries
automatically.

After either live trigger is accepted, **Review Started Run** converts the
validated compact receipt into a selection for the existing fixed
`GET /api/v1/runs/{run_id}` route. It does not refresh, re-trigger, or infer a
provider outcome. The next view contains only the bounded redacted run detail;
the established human-gate and cooperative-cancel controls remain the only
operator actions. A live snapshot refresh preserves this handoff only while the
same browser session still has the same selected exact workflow version in its
already loaded redacted inventory.

The review card also offers **Compare Versions** after the inventory contains
at least two versions of the selected workflow. It calls only the fixed
same-origin `GET /api/v1/workflow-diffs/{workflow_id}/{from_version}/{to_version}`
route and validates the bounded
`skill2workflow-workflow-diff-0.1.0` contract. The result lists changed
structural sections and bounded node/edge identifiers; it does not include
Workflow values, credentials, provider data, or execution side effects.

The same review card offers **Promote to production** for a selected published
version. The operator must confirm in the browser; the UI sends only the
workflow id/version, the fixed `production` alias, and the observed current
alias target to `POST /api/v1/workflow-promotions`. The service applies its
existing compare-and-swap boundary, so stale inventory fails closed. This
action accepts no workflow payload, trigger input, credential, or arbitrary
alias.

The review card also offers **Deprecate version** for a published version with
no active alias. The operator must confirm in the browser; the UI sends the
observed checksum and complete alias set to
`POST /api/v1/workflow-deprecations`. The service checks both values in the
same registry transaction, so stale inventory fails closed. The immutable
artifact remains available for audit and rollback review.

This live mode adds only the existing human-gate resume, cooperative
cancellation, fixed immutable Workflow publication, fixed production-alias
promotion, and CAS-protected version deprecation mutations. It does not add
TLS, public ingress, RBAC, automatic retries, forceful termination, or
provider reconciliation. Keep the UI on loopback or place it behind an
operator-managed HTTPS boundary when serving a wider network.

Use `--once` for a bounded packaging or smoke-test request. The command does
not provide TLS, public ingress, authentication, or a reverse-proxy boundary;
keep it on loopback or place it behind an operator-controlled HTTPS boundary
when serving a wider network.

The same assets are available from a source checkout with the existing
`python3 -m http.server 4173` command. The installed command is the preferred
path for wheel users because it validates that the UI and example assets came
from the installed artifact.
