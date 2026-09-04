# Operational Readiness Doctor

Loop 53 adds one read-only command for checking whether a self-hosted service
configuration is ready to start. Run it after `service-init`, after restoring
or upgrading state, and before changing a supervisor or reverse proxy to a new
workspace:

```bash
skill2workflow service-doctor --config /srv/skill2workflow/config/service.json
```

The Doctor never starts the service, acquires the scheduler lease, creates a
database, writes a marker, or binds a long-lived listener. It does not modify
the configuration, token, credential directory, or state directory. The bind
probe is advisory: it briefly binds and closes the configured loopback address,
so another process can still claim the address before service startup.

## Result Contract

The command writes one compact JSON object to stdout. Its fixed checks are
`config`, `auth`, `credentials`, `state`, and `bind`, in that order. Each check
contains only `id`, `status`, and `code`; it does not include configured paths,
token contents, connector credential values, workflow data, run identifiers,
or raw exception messages.

Example success:

```json
{
  "schema_version": "skill2workflow-service-doctor-result-0.1.0",
  "status": "ready",
  "checks": [
    {"id": "config", "status": "passed", "code": "valid"},
    {"id": "auth", "status": "passed", "code": "ready"},
    {"id": "credentials", "status": "passed", "code": "ready"},
    {"id": "state", "status": "passed", "code": "initializable"},
    {"id": "bind", "status": "passed", "code": "address_available"}
  ]
}
```

The command returns exit code `0` only when every check passes. It returns exit code `1`
with `status: "not_ready"` when any check fails. If configuration
cannot be loaded, `config` fails with `invalid` and dependent checks are
`skipped` with `blocked_by_config`.

Stable failure codes are deliberately coarse:

| Code | Operator action |
| --- | --- |
| `invalid` | Validate the versioned configuration or current SQLite state. |
| `unsafe_permissions` | Restrict the named runtime directory or token file to its owner. |
| `unsafe_path` | Replace a symbolic link or non-regular path with the documented file/directory type. |
| `oversized` | Replace the token file with one valid single-line value below 16 KiB. |
| `unavailable` | Restore the missing or unreadable provider. |
| `address_unavailable` | Stop the conflicting listener or select a different loopback port. |

The `state` check reports `initializable` for a secure empty workspace or a
current marker whose first service initialization has not completed. An
initialized state must pass current-layout identity, required database schema,
SQLite integrity, and workflow-artifact reference checks. Legacy or future
layouts remain fail-closed and require the documented upgrade path.

## Shared Startup Boundary

Doctor and `service` use the same token, credential-directory, state-directory,
layout, and integrity validation. Both reject symbolic-link token files,
path-replacement races while reading the token, token input above 16 KiB, and
state or credential directories accessible by group or others. The token is
read through one no-follow regular-file descriptor and is never printed.

The Doctor does not acquire the scheduler lease and therefore cannot prove that
this process will become the active instance. After startup, use `GET /readyz`
as the authoritative live readiness signal.

## Running-Service Go-Live Check

`service-doctor` is a pre-start diagnostic: its `bind` check deliberately
verifies that the configured loopback address is available. Do not treat a
busy address from this command as a failure of an already-running service.
For post-start deployment verification, use the ordered read-only gate instead:

```bash
skill2workflow service-go-live-check \
  --config /srv/skill2workflow/config/service.json \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /srv/skill2workflow/secrets/ingress.token
```

The gate reuses the same local safety checks while reporting only `bind` as
`skipped` with `running_service`; configuration, ingress authentication,
credential-directory, and state checks must still pass. It then checks the
fixed Probe before reading the protected operational-readiness endpoint. By
default it does not contact credential providers. The optional
`--verify-lark-tenant-credential` flag is the sole explicit Feishu China
provider preflight: it runs only after Doctor passes and short-circuits before
the Probe or protected token read when it is not ready. See the
[single-instance go-live checklist](go-live.md) for the complete operator
sequence.

## Evidence

Run the real CLI drill:

```bash
python3 scripts/service_doctor_smoke.py \
  --work-dir /tmp/skill2workflow-service-doctor-loop53
```

The drill proves a passing secure workspace, unchanged workspace content,
fixed check ordering, nonzero failure exits, unsafe permission detection, busy
address detection, and value redaction.
