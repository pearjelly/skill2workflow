# Single-Instance Go-Live Checklist

This guide turns the existing self-hosted Beta controls into one operator
sequence for a single team. It does not create accounts, install a supervisor,
configure TLS, or issue credentials. The optional Feishu credential preflight
in step 2a is the sole exception: it contacts the fixed Feishu China
tenant-token endpoint without creating business work. Complete each step with
your deployment's own change-control and privacy requirements.

## 1. Prepare a secure workspace

Install the wheel and create a non-overwriting workspace. The command creates
an owner-only ingress token without printing it:

```bash
skill2workflow service-init \
  --root /srv/skill2workflow \
  --host 127.0.0.1 \
  --port 8080
```

Read the returned JSON and retain the reported `config_path` and
`auth_token_file` privately. Add reviewed connector credentials only through
the documented owner-only credential directory; do not place credentials in a
Workflow DSL document.

## 2. Check before starting

To diagnose the prepared workspace before the service exists, run the local,
read-only Doctor directly:

```bash
skill2workflow service-doctor \
  --config /srv/skill2workflow/config/service.json
```

Proceed only when every fixed check is `passed` and `status` is `ready`. A
failed check does not modify the workspace. Correct configuration, permission,
credential-directory, state, or bind problems first; see
[Service Doctor](service-doctor.md).

### 2a. Preflight a configured Feishu China credential

Only when `config/service.json` contains the approved
`lark_tenant_access_token` descriptor, run this separate, explicit preflight
after the App Secret file has been created and before sending any business
work:

```bash
skill2workflow service-lark-tenant-credential-check \
  --config /srv/skill2workflow/config/service.json
```

It performs one bounded direct tenant-token exchange and exits `0` only when
the result is `ready`. It does not start the service, publish or start a
workflow, retain a token, or create a Feishu task. Its fixed result is
value-free; use `not_ready` to correct the private App Secret or approved
application configuration through normal change control. Do not run it for a
deployment without that descriptor: it returns `not_configured` and does not
contact Feishu. The ordinary Doctor and composite go-live gate intentionally
remain local/provider-free, so this explicit step cannot be skipped by
mistaking local readiness for provider credential validity.

## 3. Start under reviewed supervision

For a Linux host, generate and manually review the least-privilege systemd
unit before enabling it:

```bash
skill2workflow systemd-unit \
  --config /srv/skill2workflow/config/service.json \
  --output /tmp/skill2workflow.service \
  --service-user skill2workflow \
  --executable /usr/local/bin/skill2workflow
```

Follow [Systemd supervision](systemd-service.md) for the required host-side
account creation, `systemd-analyze verify`, review, installation, and service
manager actions. For a non-systemd deployment, use an equivalent reviewed
supervisor that sends `SIGTERM` and preserves the same private filesystem
boundary. The project does not install or enable a supervisor for you.

## 4. Verify the running service

After the service is started under your reviewed supervisor, use the composite
read-only gate to run the checks in the safe order. It runs the local Doctor,
then the unauthenticated fixed Probe, and only then reads the protected
operational readiness report:

```bash
skill2workflow service-go-live-check \
  --config /srv/skill2workflow/config/service.json \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /srv/skill2workflow/secrets/ingress.token
```

The command exits `0` only for `status: "ready"`. If the local Doctor is not
ready, it does not access the service or token file. If the Probe is not ready,
it does not access the protected operational-readiness route. Its output is a
fixed, value-free summary; it contains no paths, credentials, workflow content,
inputs, or raw errors. Because this command runs after the service starts, its
local Doctor report marks only the port-bind check as `skipped` with
`running_service`; the Probe is the authoritative running-service check. The
configuration, authentication, credential-directory, and state checks still
must pass.

Use the unauthenticated fixed probe to distinguish ready, not-ready, and
unavailable service state:

```bash
skill2workflow service-probe --service-url http://127.0.0.1:8080
```

`ready` means the local service is accepting its documented runtime boundary;
it does not prove provider availability or external side effects. A deployment
exposed beyond loopback needs an operator-managed TLS and network boundary as
described in [Service](service.md).

## 5. Review authenticated operational readiness

After the probe is ready, use the protected aggregate check. It reads the
token only from its owner-only file and returns a bounded, value-free report:

```bash
skill2workflow service-operational-readiness \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /srv/skill2workflow/secrets/ingress.token
```

Investigate every `blocking_reasons` entry before business traffic. The report
checks service readiness, state layout, workflow-artifact consistency, audit
integrity, and offline-backup readiness without exporting workflow content,
inputs, credentials, paths, or audit payloads. See
[Remote operational readiness](remote-operational-readiness.md).

For normal go-live verification, prefer the preceding `service-go-live-check`
command so this protected read cannot run before the Doctor and Probe succeed.

## 6. Publish and operate deliberately

Publish reviewed Workflow DSL only through immutable release controls; review
the execution plan and trigger preflight before starting a run. Use an
idempotency key for every trigger. Human decisions, cancellations, promotion,
deprecation, and uncertain-dispatch reviews remain explicit operator actions.
If the live console reports a conflict, reload the indicated bounded evidence
before another confirmation; it never retries a write automatically.

For a first controlled workflow, use [Quickstart](quickstart.md). For remote
operator actions, use the installed clients documented in [Human approval](human-approval.md),
[Remote trigger](remote-trigger.md), and [Workflow releases](workflow-releases.md).

## 7. Preserve recovery evidence

Before a planned upgrade or retention cutover, run the documented backup,
Doctor, and operational-readiness checks. Use [Backup and restore](backup-restore.md)
for offline verified snapshots, [Upgrade and migration](upgrade-migration.md)
for copy-on-write upgrades, and [Production Baseline Evidence](production-baseline-evidence.md)
for the repository's repeatable qualification bundle.

This checklist supports one self-hosted, single-tenant service. It does not
claim multi-tenant RBAC, high availability, hosted secret management, automatic
external-effect reconciliation, or exactly-once provider execution.
