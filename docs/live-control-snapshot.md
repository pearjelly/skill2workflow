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

The live console remains a single-team operator boundary. The Loop 211 UI
proxy adds only the existing human-gate resume decision; it excludes browser
credential storage, CORS, workflow publication, cancellation, RBAC, pagination
cursors, remote audit storage, multi-tenant filtering, automatic retries,
provider reconciliation, and hosted TLS. Network exposure still requires the
external TLS and private operator boundary documented in
[security-boundary.md](security-boundary.md).
