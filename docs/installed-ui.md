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
control-plane page still accepts an exported snapshot file; it is not a live
authenticated service console.

Use `--once` for a bounded packaging or smoke-test request. The command does
not provide TLS, public ingress, authentication, or a reverse-proxy boundary;
keep it on loopback or place it behind an operator-controlled HTTPS boundary
when serving a wider network.

The same assets are available from a source checkout with the existing
`python3 -m http.server 4173` command. The installed command is the preferred
path for wheel users because it validates that the UI and example assets came
from the installed artifact.
