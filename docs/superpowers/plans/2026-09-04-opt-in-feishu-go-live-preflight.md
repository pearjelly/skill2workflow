# Loop 262 — Opt-In Feishu Credential Go-Live Preflight

## Goal

Let an operator request one value-free composite deployment report that also
checks an already configured Feishu China tenant credential, without weakening
the existing local-only go-live gate or creating any business work.

## Prior basis

Loop 261 adds `service-lark-tenant-credential-check`, an explicit bounded
preflight that derives a short-lived tenant token only in memory. The normal
`service-go-live-check` intentionally remains local: Doctor, service Probe,
and protected operational readiness do not contact a provider. Operators must
therefore manually run and interpret two commands when a deployment uses the
approved derived Feishu credential.

## Scope

- Add `--verify-lark-tenant-credential` to `service-go-live-check`.
- Call the existing credential-check implementation only when the flag is
  present and the local Doctor has reported `ready`.
- Add a fixed, value-free `lark_tenant_credential` summary only to explicitly
  opted-in reports.
- Stop before the service Probe and ingress-token read when the selected
  credential check is not ready.
- Document the pre-start standalone command and post-start composite option.

## Contract

The existing command keeps its exact default behavior and output shape:

```bash
skill2workflow service-go-live-check \
  --config /srv/skill2workflow/config/service.json \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /srv/skill2workflow/secrets/ingress.token
```

With the explicit flag, the report adds only:

```json
{
  "lark_tenant_credential": {
    "status": "ready",
    "provider": "lark_tenant_access_token",
    "reason": "validated"
  }
}
```

The only accepted selected-check reasons are `validated`, `invalid_config`,
`not_configured`, and `credential_unavailable`. If Doctor is not ready, the
summary is instead `not_checked` with `blocked_by_local_doctor`, and no
provider call occurs. Invalid or unexpected internal check values normalize to
`not_ready` / `credential_unavailable` at the composite boundary.

The selected sequence is:

```text
local Doctor -> optional Feishu credential preflight -> service Probe -> protected operational readiness
```

The first non-ready stage short-circuits later stages. The credential preflight
is selected only by the explicit flag; ordinary go-live remains:

```text
local Doctor -> service Probe -> protected operational readiness
```

## Safety boundaries

- No provider call occurs without the flag.
- The feature uses only the already-approved Feishu China tenant-token
  exchange; it adds no generic OAuth, international Lark endpoint, token
  caching, token persistence, background refresh, or hosted secret manager.
- It does not start a service or workflow, publish an artifact, resolve a
  connector credential for business work, or create a Feishu task.
- The report never returns an App Secret, tenant token, provider message,
  configuration path, request payload, or raw exception.
- Local Doctor retains its existing authority. A successful provider check
  does not replace Probe or protected operational readiness.

## Acceptance evidence

1. The default composite gate never calls the Feishu credential check and
   retains its previous response shape.
2. With the flag, Doctor failure prevents a provider call; a non-ready
   credential result prevents Probe and ingress-token access.
3. A ready selected credential result precedes and preserves the existing
   Probe and operational-readiness sequence.
4. CLI forwarding, exit status, value-free normalization, documentation,
   focused regression, and isolated-wheel qualification pass.
