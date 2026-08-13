# Linux systemd Supervision

Loop 56 supplies one safe, reviewable path from a prepared self-hosted
workspace to a Linux `systemd` service unit. It generates the unit but never
installs it, enables it, starts it, creates an operating-system account, or
changes host firewall, TLS, proxy, or secret-management settings.

## Prerequisites

Use a current Linux distribution with `systemd` and run the service as a
dedicated pre-provisioned account. Your operating-system administrator remains
responsible for selecting that account, granting it access to its workspace,
and applying the organisation's account lifecycle policy.

Create the workspace as the account that will run the service. Its parent must
already permit that account to create the one owner-only workspace:

```bash
sudo -u skill2workflow -- /usr/local/bin/skill2workflow service-init \
  --root /srv/skill2workflow/team-a \
  --host 127.0.0.1 \
  --port 8080

sudo -u skill2workflow -- /usr/local/bin/skill2workflow service-doctor \
  --config /srv/skill2workflow/team-a/config/service.json
```

The Doctor must report `ready` before the unit is generated. Choose a fixed,
available non-zero port. Port `0` is useful for test fixtures but is rejected
for a supervised service because it cannot provide a stable operator endpoint.

## Generate, Verify, And Enable

Use the installed console script's absolute path and an absolute destination
whose filename ends in `.service`. The generator never overwrites an existing
file, so stage a corrected unit at a new path or remove the old file only after
the operating-system change has been reviewed.

```bash
sudo /usr/local/bin/skill2workflow systemd-unit \
  --config /srv/skill2workflow/team-a/config/service.json \
  --output /etc/systemd/system/skill2workflow-team-a.service \
  --service-user skill2workflow \
  --service-group skill2workflow \
  --executable /usr/local/bin/skill2workflow

sudo systemd-analyze verify /etc/systemd/system/skill2workflow-team-a.service
sudo systemctl daemon-reload
sudo systemctl enable --now skill2workflow-team-a.service
sudo systemctl status skill2workflow-team-a.service
```

`systemd-analyze verify` is the target-host grammar and directive check; run it
before enabling because supported systemd directive versions vary by Linux
distribution. The generator deliberately performs no `systemctl` operation.

For a normal stop or upgrade, use `systemctl stop`. The generated unit sends
`SIGTERM` and does not escalate to `SIGKILL`; this preserves the runtime's
graceful-drain and interrupted-run boundaries. If a process cannot stop, retain
its state for the documented interrupted-run recovery procedure instead of
assuming a provider side effect can be safely replayed.

## Local Journal

The generated unit explicitly sends standard output and standard error to the
local system journal. The service's standard-output events are the allowlisted
operational NDJSON contract described in [observability.md](observability.md):
they carry only fixed lifecycle/request fields, never workflow identifiers,
request values, or credentials. Follow those structured events on the target
host with:

```bash
sudo journalctl --unit skill2workflow-team-a.service --output cat --follow
```

Use the durable workflow audit and run state for business evidence; the journal
is only host-local operational output. Its retention, access control, export,
and any forwarding remain the operating-system administrator's responsibility.
Do not treat the unit generator as a log shipper or a remote audit store.

## Unit Contract

The generated file is a non-secret `0644` systemd unit. It contains only the
absolute console-script, configuration, state, token-file, and credential
directory paths; it never contains a token value, connector value, or
`Environment=` directive. The input configuration itself must be an absolute
private `0600` regular file and is read through one no-follow descriptor with a
64 KiB bound before it is parsed. The executable must be an absolute regular
non-symlink executable file.

The unit fixes `User`, `Group`, `UMask=0077`, `ExecStart`, restart backoff,
`KillSignal=SIGTERM`, `SendSIGKILL=no`, and `WantedBy=multi-user.target`. It uses systemd hardening
including `NoNewPrivileges`, `PrivateTmp`, `PrivateDevices`, protected kernel
and host views, an empty capability set, native system-call architecture, and
only Unix/IPv4/IPv6 address families. `ProtectSystem=strict` is paired with one
`ReadWritePaths=` entry for the SQLite state directory. The configuration,
ingress-token file, and connector credential directory are explicitly listed
under `ReadOnlyPaths=` and must not overlap the writable state directory. The
console executable must also live outside that writable directory, so a state
writer cannot replace the program used by a later supervised restart.

The generated process still listens only on its configured loopback address.
For external traffic, keep the reverse-proxy and TLS boundary in
[security-boundary.md](security-boundary.md); do not bind the service directly
to a public interface merely because it now has a supervisor.

## Verification

The portable evidence drill uses the real CLI, a newly bootstrapped workspace,
and a disposable executable wrapper. It verifies the non-overwrite rule,
redacted output, unit permissions, fixed least-privilege paths, and required
hardening directives without requiring systemd on the development machine:

```bash
python3 scripts/systemd_service_smoke.py \
  --work-dir /tmp/skill2workflow-systemd-service-loop56
```

This drill is generator evidence, not proof that a particular Linux host has
accepted or started the unit. On each deployment target, run `service-doctor`,
`systemd-analyze verify`, then explicitly review and enable the unit.

## Boundary

Loop 56 covers one manually enabled, single-tenant Linux systemd unit. It does
not provide system account provisioning, automatic installation or restart,
Launchd, Windows services, containers, Kubernetes, log shipping, TLS or proxy
automation, remote monitoring, multi-instance coordination, secret rotation,
or forceful provider-request abortion.
