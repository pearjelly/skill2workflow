# Loop 261 — Self-Hosted Feishu Tenant Credentials

## Goal

Make the already-approved, China-only live Feishu `create_task` connector
usable by a long-running single-tenant service without an operator manually
replacing a short-lived tenant access token. The service will derive the
existing `lark_bot_access_token` handle from a non-secret App ID in service
configuration plus an owner-only App Secret file at execution time.

## Why now

The controlled Pilot already exchanges `LARK_APP_ID` and Vault-injected
`LARK_APP_SECRET` in memory, then immediately uses the short-lived returned
token. The production service's directory provider instead accepts only a
static token file. That is a real operational gap: an otherwise durable
single-tenant deployment eventually stops sending approved Feishu tasks when
the manually supplied token expires.

## Scope

- Add one optional `lark_tenant_access_token` block to the existing directory
  credential configuration.
- Configure a public target handle (normally `lark_bot_access_token`), a
  non-secret `app_id`, and a private source `app_secret_handle`.
- Wrap the existing directory provider so resolving the target handle reads
  the App Secret through the existing descriptor-bound boundary, exchanges it
  directly with the fixed Feishu China tenant-token endpoint, and returns the
  resulting token only in memory to the requesting connector.
- Extend `service-init` with explicit non-secret configuration flags, and add
  service, connector, config, documentation, wheel, and secret-hygiene
  evidence.
- Provide one installed, explicit preflight command that performs a bounded
  exchange without starting a workflow or creating a Feishu task, and returns
  only a fixed value-free readiness result.

## Contract

The optional service configuration shape is:

```json
{
  "credentials": {
    "provider": "directory",
    "directory": "/srv/skill2workflow/secrets/connectors",
    "lark_tenant_access_token": {
      "handle": "lark_bot_access_token",
      "app_id": "cli_example",
      "app_secret_handle": "lark_app_secret"
    }
  }
}
```

The App Secret itself remains only in the private directory file named by
`app_secret_handle`; it is never accepted on a command line or stored in
configuration. The source handle is reserved: normal connector bindings cannot
resolve it directly. Existing configurations with only `provider` and
`directory` retain their exact behavior.

Every resolution of the configured target handle performs one fresh exchange.
There is no cache, token file, token persistence, background refresh process,
or token-exchange record. This avoids extending the durable state or backup
boundary with provider credentials and makes operator rotation effective on
the next execution.

The exchange is a `POST` only to
`https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`, uses a
five-second timeout, disables ambient proxy configuration, accepts at most
64 KiB of UTF-8 JSON, and requires a Feishu `code: 0` plus a non-empty
`tenant_access_token`. Any transport, bound, decoding, or provider failure is
normalized to the existing credential-resolution failure; raw provider values,
messages, headers, and response bodies never cross into run state, audit,
telemetry, console responses, or CLI output.

## Safety boundaries

- This is only for the approved Feishu China tenant-token exchange and the
  existing live `create_task` connector; it does not add a generic OAuth
  provider, token refresh framework, Lark international endpoint, hosted
  secret manager, or automatic connector discovery.
- The exchange occurs only after normal workflow validation reaches connector
  credential resolution. Doctor, readiness, inventory, backup, publication,
  and UI reads do not access the App Secret or the external endpoint.
- The App Secret source handle must differ from the target handle, obey the
  existing handle grammar, and is denied to ordinary connector resolution.
- The workflow still needs the existing explicit live mode, connector
  idempotency identity, human authorization, and external network policy.
  This does not claim exactly-once provider effects or automatic reconciliation
  after an ambiguous provider outcome.

## Acceptance evidence

1. Legacy static-directory credentials retain exact behavior and service
   configuration remains fail-closed for malformed derived configuration.
2. A fake transport proves the exchanged tenant token reaches only the
   connector's in-memory authorization boundary; the App Secret and token are
   absent from output, audit, run state, telemetry, and errors.
3. The reserved App Secret handle cannot be requested by a connector, and no
   exchange occurs before normal credential resolution.
4. Transport, proxy, timeout, oversized response, malformed JSON, and nonzero
   Feishu response code fail with a fixed credential error and no raw values.
5. A service lifecycle drill proves the configuration is safe to load and
   Doctor remains local-only; a live connector execution performs one bounded
   fake exchange, and changing the private App Secret file is observed by the
   next execution.
6. Documentation covers private file setup, rotation, scope, non-goals, and
   the installed `service-init` flags. The explicit credential-check command
   has a fixed value-free CLI result and cannot create business work. Full
   regression, package smoke, secret hygiene, and the production-baseline
   bundle pass.
