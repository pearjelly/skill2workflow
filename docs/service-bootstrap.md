# Secure Service Bootstrap

Loop 51 provides the shortest safe path from an installed wheel to one ready
self-hosted service workspace. It creates configuration, durable-state, ingress
secret, and connector-credential locations together so operators do not have to
hand-assemble absolute paths or file permissions.

## Initialize

Choose an absolute path whose parent already exists. The target itself must not
already exist:

```bash
skill2workflow service-init \
  --root /srv/skill2workflow/team-a \
  --host 127.0.0.1 \
  --port 8080
```

The command creates this layout:

```text
team-a/                              0700
  config/                            0700
    service.json                     0600
  state/                             0700
  backups/                           0700
  secrets/                           0700
    ingress-token                    0600
    connectors/                      0700
```

The generated ingress secret contains at least 32 random bytes. The command
never prints its value; its compact JSON output contains paths only. The service
configuration contains only provider names and absolute file locations, never
inline secrets.

The owner-only `backups/` directory is recorded as the optional
`runtime.backup_parent_dir` setting. It is a read-only source for the protected
remote backup inventory; the service never creates or deletes backup sets
through HTTP.

Initialization is fail-closed. A relative root, non-loopback host, invalid port,
missing parent, symlink target, weak generated secret, or existing target is
rejected. The target must not already exist, and there is no force or overwrite
mode. If configuration publication fails, the partially created workspace is
removed.

## Start And Verify

Run the generated configuration through the read-only Doctor before startup:

```bash
skill2workflow service-doctor \
  --config /srv/skill2workflow/team-a/config/service.json
```

All five fixed checks must pass. See [`service-doctor.md`](service-doctor.md)
for stable failure codes and the distinction between preflight and live
readiness.

After installation, use [`service-token-rotation.md`](service-token-rotation.md)
to rotate the generated ingress credential atomically; do not edit the token
file in place.

Start the generated configuration directly:

```bash
skill2workflow service \
  --config /srv/skill2workflow/team-a/config/service.json
```

Readiness is available at `http://127.0.0.1:8080/readyz`. Authenticated local
requests can read the secret into a process-local shell variable without
printing it:

```bash
TOKEN="$(cat /srv/skill2workflow/team-a/secrets/ingress-token)"
curl -H "Authorization: Bearer ${TOKEN}" http://127.0.0.1:8080/metrics
unset TOKEN
```

Add connector credential files beneath `secrets/connectors/` using the Workflow
DSL credential handle as the filename and mode `0600`. The runtime resolves them
at execution time.

## Data And Security Boundary

The generated listener remains loopback-only. Public or cross-host traffic still
requires the external TLS reverse-proxy boundary described in
[`security-boundary.md`](security-boundary.md). The initializer does not create
certificates, proxy rules, firewall policy, or a service account. For a
manually reviewed Linux systemd unit after bootstrap, see
[`systemd-service.md`](systemd-service.md); initialization itself never writes,
installs, or enables a supervisor.

Only `state/` belongs to the runtime backup and migration commands. The ingress
secret and connector files are not included in state backups; protect, rotate,
and recover them through an operator-managed secret system. Do not copy the
entire bootstrap root as a substitute for the verified backup procedure.

## Evidence

Run the real-process drill:

```bash
python3 scripts/service_bootstrap_smoke.py \
  --work-dir /tmp/skill2workflow-service-bootstrap-loop51
```

It initializes a fresh workspace through the CLI, checks owner-only permissions
and redacted output, proves a second initialization cannot overwrite the secret,
starts the generated service unchanged, verifies readiness and authenticated
metrics, rejects an unauthenticated request, sends `SIGTERM`, and confirms the
durable SQLite state was initialized.
