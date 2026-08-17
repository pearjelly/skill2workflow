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

For an explicit, read-only live view of one running service, configure both the
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

The live mode does not add TLS, public ingress, RBAC, mutations, or provider
reconciliation. Keep the UI on loopback or place it behind an operator-managed
HTTPS boundary when serving a wider network.

Use `--once` for a bounded packaging or smoke-test request. The command does
not provide TLS, public ingress, authentication, or a reverse-proxy boundary;
keep it on loopback or place it behind an operator-controlled HTTPS boundary
when serving a wider network.

The same assets are available from a source checkout with the existing
`python3 -m http.server 4173` command. The installed command is the preferred
path for wheel users because it validates that the UI and example assets came
from the installed artifact.
