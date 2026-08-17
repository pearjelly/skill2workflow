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
non-sensitive example JSON. It does not read runtime state or the service state directory,
resolve credentials, expose an ingress token, or mutate workflows. The
control-plane page still accepts an exported snapshot file; by default it is
not a live authenticated service console.

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

This live mode adds one explicit human-gate mutation only. It does not add TLS,
public ingress, RBAC, workflow publication, cancellation, automatic retries,
or provider reconciliation. Keep the UI on loopback or place it behind an
operator-managed HTTPS boundary when serving a wider network.

Use `--once` for a bounded packaging or smoke-test request. The command does
not provide TLS, public ingress, authentication, or a reverse-proxy boundary;
keep it on loopback or place it behind an operator-controlled HTTPS boundary
when serving a wider network.

The same assets are available from a source checkout with the existing
`python3 -m http.server 4173` command. The installed command is the preferred
path for wheel users because it validates that the UI and example assets came
from the installed artifact.
