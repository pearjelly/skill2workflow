# Authenticated Live Operator Snapshot

Loop 55 turns the existing offline `control-snapshot` artifact into a safe,
read-only view of one running self-hosted service. It does not make the visual
graph authoritative and does not add a remote mutation API.

## Service Contract

The service exposes:

```text
GET /api/v1/control-snapshot
Authorization: Bearer <single-team-token>
Accept: application/json
```

The route requires the same file-backed Bearer authentication as workflow
traffic. Missing, malformed, or invalid credentials return `401`; an unavailable
token provider returns `503`. The response always carries
`Cache-Control: no-store`. Authenticated requests with a body, transfer encoding,
or an invalid content length are rejected before snapshot construction.

The endpoint remains available while `/readyz` is not ready. This lets an
operator inspect a starting, draining, or standby process, provided its
authentication and SQLite control state remain readable. Storage or snapshot
construction failures return the fixed `503 control snapshot unavailable`
response without exception or state details.

Every live response is bounded to the most recent 100 items in each top-level
collection and to 1 MiB after UTF-8 JSON encoding. The `summary` reports total
state counts. The `window` object reports the fixed limit plus total, returned,
and truncated counts for each returned collection. Operator insights describe
the returned window, not hidden older records. SQLite workflow, run, and audit
windows are selected with bounded queries rather than loading complete history
and trimming it in process memory.

The machine-readable shape is published at
[`schemas/control-snapshot-0.1.0.schema.json`](../schemas/control-snapshot-0.1.0.schema.json).
The `window` member is optional for complete offline exports and required by the
live client. In addition to structural validation, the client verifies that
summary totals, collection lengths, returned counts, and truncation flags agree.

The endpoint does not append persisted audit events. This prevents polling from
changing the state it observes or creating unbounded audit growth. Requests are
still visible through the fixed `control_snapshot` route in process-local HTTP
metrics and allowlisted operational NDJSON. Neither surface records the raw URL,
Bearer token, workflow identifiers, or response body.

## Safe CLI Client

Use the installed CLI so the token is read from its protected file instead of
placing it in shell history or process arguments:

```bash
skill2workflow control-snapshot \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /run/secrets/skill2workflow-ingress-token \
  --output /var/lib/skill2workflow/operator-snapshot.json
```

The client accepts HTTPS or loopback HTTP origins only. A base URL cannot
contain credentials, a path, query, or fragment. The client refuses redirects,
compressed bodies, the wrong media type or schema, a missing `no-store`
directive, invalid JSON, and responses above 1 MiB. These checks prevent the
Bearer token from being redirected to a different endpoint and keep client
memory bounded. Environment-configured HTTP proxies are bypassed so they cannot
receive the Authorization header; HTTPS certificate validation remains enabled.

When `--output` is used, both local and live snapshots are atomically published
as an owner-only `0600` file. Standard output remains an explicit option and may
contain workflow and run metadata, so operators must protect terminals and log
collectors accordingly.

The original offline command remains unchanged in meaning and is unlimited:

```bash
skill2workflow control-snapshot \
  --state-dir /var/lib/skill2workflow \
  --storage sqlite \
  --output /var/lib/skill2workflow/offline-snapshot.json
```

Use the offline form for a complete stopped-state export. Use the live form for
a bounded operational view.

For routine inspection of a long-running local state directory, request a
bounded offline window:

```bash
skill2workflow control-snapshot \
  --state-dir /var/lib/skill2workflow \
  --storage sqlite \
  --max-items 100 \
  --output /var/lib/skill2workflow/operator-snapshot.json
```

`--max-items` accepts `1` through `1000` and adds the same `window` accounting
used by the live snapshot. JSON and SQLite storage retain only the newest
window for runs, audit events, and workflow records while computing aggregate
totals. The flag is rejected for `--service-url`, whose live bound is fixed at
100 items. Omitting it keeps the complete offline export compatibility path.

The existing Operator UI can load either artifact. It labels complete offline
exports separately from bounded snapshots and highlights truncated collections,
while Summary continues to show the total counts. A malformed or internally
inconsistent window is rejected and clears previously displayed snapshot data.

The installed UI can also fetch one live snapshot without placing the service
token in browser state. Start it with both `--service-url` and
`--auth-token-file` as documented in [`installed-ui.md`](installed-ui.md), then
use **Load Live Snapshot**. This is a fixed, read-only same-origin proxy for
`GET /api/v1/control-snapshot`; it does not proxy arbitrary paths or expose the
token. Without both options, the button reports that live mode is unavailable.
The scope bar separately shows the fixed `service-probe` result so a standby,
draining, or unavailable service is distinguishable from static mode; that
diagnostic route only calls `/healthz` and `/readyz` and returns the existing
value-free probe schema.

With live mode configured, the UI's explicit **Auto-refresh** control uses a
fixed 10-second interval, skips hidden pages, and keeps the last valid snapshot
visible when a refresh fails. Loading an example or file stops the timer; there
is no background polling in static mode.

The same live console can download the existing redacted support artifact with
**Download Support Bundle**. This is a fixed read-only proxy for
`GET /api/v1/support-bundle`, retains the service's 128 KiB contract and
`no-store` response, and never sends the ingress token to the browser. It is an
explicit operator download, not automatic support upload.

When the live run table selects a run whose fixed status is `waiting`, the
detail panel also offers **Approve run** and **Reject run**. The browser first
requires an explicit confirmation, then sends exactly `{"approved":true}` or
`{"approved":false}` to the UI's fixed same-origin
`POST /api/v1/runs/{run_id}/resume` route. The UI validates an ASCII `run_*`
identifier, accepts only the one-boolean body, forwards the existing protected
service action with the server-side token, validates the response, and reloads
the snapshot. `404` and `409` remain fixed not-found/not-waiting outcomes;
other upstream failures are reduced to a value-free `503`. Static, example,
and file snapshots never expose the controls.

Selecting a live run also fetches the existing redacted run-detail projection
through the fixed same-origin `GET /api/v1/runs/{run_id}` route. The UI keeps
the service-side 50-event and 64 KiB bounds, validates the schema and event
window before rendering it, and leaves the run summary visible if the detail
fetch fails. The detail route is read-only and uses the same server-side token
boundary; it does not proxy arbitrary paths or return workflow inputs,
connector output, credentials, or raw errors.

The live Runs view can discover history beyond the snapshot tail through the
explicit **Load Older Runs** control. It calls only the UI's fixed
`GET /api/v1/run-page` route, which accepts either no query or one validated
opaque cursor and always requests the service's 100-item
`skill2workflow-run-list-0.2.0` page. The browser deduplicates rows and caps
its retained live list at 500 items. No arbitrary status, workflow, path, or
service query is forwarded from the browser.

The same live detail panel can request **Cancel run** for a `created`,
`running`, or `waiting` run. After explicit confirmation it sends exactly `{}`
to the fixed same-origin `POST /api/v1/runs/{run_id}/cancel` route. The UI
validates the compact `{run_id,status}` response and refreshes the snapshot.
This is the existing cooperative cancellation contract: an in-flight provider
call may finish, no external effect is rolled back, and terminal runs are not
rewritten. Static, example, and file snapshots never expose the control.

The live Audit view can also discover history beyond the snapshot tail through
the explicit **Load Older Audit** control. It calls only the UI's fixed
`GET /api/v1/audit-page` route, which accepts no query or one validated opaque
cursor and always requests the service's 100-item redacted
`skill2workflow-audit-event-list-0.1.0` page without filters. The browser
deduplicates sequence numbers and caps retained live audit rows at 500. No raw
payload, provider error, credential, or arbitrary service query crosses this
boundary.

The live console can explicitly load the existing redacted recurring-schedule
inventory through its fixed `GET /api/v1/recurring-schedules` proxy. The
browser accepts the exact `skill2workflow-recurring-schedule-list-0.1.0`
contract and renders at most 100 schedule rows with next-run and compact
last-run metadata. This is read-only discovery: no schedule mutation,
dispatch claim, trigger input, lease identity, credential, or provider payload
crosses the UI boundary, and static/file snapshots never expose the control.

The live console can also explicitly load the aggregate production-readiness
report through its fixed `GET /api/v1/operational-readiness` proxy. The browser
accepts only the `skill2workflow-operational-readiness-0.1.0` contract and
renders service, workflow-artifact, audit-integrity, offline-backup, and
blocking-reason rows. This remains read-only and value-free: paths, workflow
content, run identifiers, lease identities, credentials, and provider data are
excluded; static/file snapshots never expose the control.

The live console can also explicitly load the redacted published-version
inventory through its fixed `GET /api/v1/workflows` proxy. The browser accepts
only the `skill2workflow-workflow-inventory-0.1.0` contract and renders at most
100 versions with lifecycle status, aliases, and recognition-only checksum
prefixes. Workflow content, artifact paths, timestamps, credentials, trigger
inputs, and provider data remain outside the UI boundary; static/file snapshots
never expose the control.

Selecting a version from the live Registry can load its value-free execution
plan through the fixed `GET /api/v1/workflow-explanations/{workflow_id}/{version}`
proxy. The browser validates the
`skill2workflow-workflow-explanation-0.1.0` contract and bounded topology,
policy, connector-side-effect, retry, timeout, and human-gate metadata. It
does not invoke connectors or resolve credentials, and it excludes Workflow
values, instructions, artifact paths, trigger inputs, and provider data.

The selected-version review also offers a no-input preflight through the fixed
`POST /api/v1/workflow-preflights/{workflow_id}/{version}` proxy. The browser
sends exactly `{}` and accepts only the
`skill2workflow-workflow-preflight-0.1.0` value-free contract, showing whether
the empty trigger is ready, missing required fields, or blocked by mappings.
It never accepts business input, resolves credentials, invokes connectors, or
creates a run.

## Verification

Run the real-process drill:

```bash
python3 scripts/live_control_snapshot_smoke.py \
  --work-dir /tmp/skill2workflow-live-snapshot-loop55
```

The drill starts the CLI service, proves unauthenticated denial, fetches through
the CLI with a protected token file, verifies the bounded schema and `0600`
output, proves persisted audit state is unchanged, and checks fixed metrics and
NDJSON without publishing private values in its evidence.

## Boundary

The live console remains a single-team operator boundary. Loops 211-220 add
only the existing human-gate resume decision, cooperative cancellation, and
redacted run-detail/run-discovery/audit-discovery/schedule-discovery/readiness/workflow-inventory/workflow-explanation reads; the UI excludes browser credential
storage, CORS, workflow publication, forceful termination, RBAC, pagination
cursors beyond the fixed UI page, remote audit storage, multi-tenant filtering,
automatic retries, provider reconciliation, and hosted TLS. Network exposure
still requires the external TLS and private operator boundary documented in
[security-boundary.md](security-boundary.md).
