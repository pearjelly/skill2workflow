# Credential Boundary And Secret Hygiene

This document defines the current credential boundary for `skill2workflow` connector examples and Workflow DSL fixtures.

Workflow DSL is the execution truth source and published workflow artifacts are immutable. For that reason, Workflow DSL fixtures must not contain real secrets, API tokens, customer credentials, private keys, cookies, or production authorization headers.

## Current Rule

Committed Workflow DSL and LiteGraph example fixtures may contain:

- local test URLs such as `http://127.0.0.1:8080/example`
- empty values when the example needs to show a field shape
- documented placeholders such as `<redacted>`, `REDACTED`, `placeholder`, `example-token`, and `token-placeholder`
- non-sensitive example request bodies used by deterministic local tests

Committed fixtures must not contain:

- real `Authorization`, `X-API-Key`, cookie, password, token, or secret values
- private key material
- customer data that acts as a credential
- production SaaS endpoint credentials
- personal access tokens or bot tokens

## Secret Hygiene Check

Run the local guardrail before opening connector or example PRs:

```bash
python3 scripts/secret_hygiene.py examples/workflows
```

The command prints JSON:

```json
{
  "ok": true,
  "scanned": ["examples/workflows/http-connector.workflow.json"],
  "findings": []
}
```

When a finding exists, the command exits with status `1` and reports the file, JSON path, reason, and a shortened value preview.

The scanner is intentionally conservative and dependency-free. It catches obvious secret-like keys and values in committed JSON fixtures; it is not a replacement for repository secret scanning or human review.

## Local Credential Provider

The local runtime supports a minimal credential-provider boundary for connector execution. Workflow DSL may reference a credential handle, while the resolved value lives outside the workflow artifact.

Local credential files use this format:

```json
{
  "credentials": {
    "demo_api_token": "local-secret-value"
  }
}
```

Use the file at runtime:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli run /tmp/skill2workflow-workflow.json \
  --state-dir /tmp/skill2workflow-state \
  --credential-file /tmp/skill2workflow-credentials.json
```

The credential file is local-only. Do not commit it.

Workflow DSL connector bindings may reference handles:

```json
{
  "connector": {
    "id": "http",
    "kind": "http",
    "request": {
      "url": "http://127.0.0.1:8080/example"
    },
    "credentials": [
      {
        "target": "header",
        "name": "Authorization",
        "handle": "demo_api_token",
        "prefix": "Bearer "
      }
    ]
  }
}
```

Only the handle belongs in Workflow DSL. The resolved value is used for the outbound connector request and is not written to node results, run context, or audit events by the built-in runtime.

## Connector Extension Requirements

Connector extensions must preserve the same credential boundary as the built-in HTTP connector:

- Workflow DSL may store credential handles, never resolved credential values.
- Trigger input and input mapping payloads must not carry credentials, tokens, private keys, cookies, or production authorization headers.
- Connector manifests must describe handle support under `credential_contract`.
- Resolved credential values may be used only inside connector execution.
- Connector results, run state, snapshots, LiteGraph overlays, and audit events must not include resolved credential values.
- Audit metadata should expose compact connector status, attempt, policy, and key names only.

Future product-specific connectors must use local handles first. Hosted secret stores, OAuth flows, IAM, and redaction policies require separate design work before they can become runtime features.

## Runtime Boundary

The current local runtime does not implement:

- secret managers
- hosted credential stores
- credential encryption at rest
- runtime redaction
- RBAC or IAM
- product-specific SaaS credential flows
- connector marketplace credentials

The provider boundary is intentionally local and dependency-free. It is not a production secret manager.

## Contributor Guidance

When adding connector examples:

1. Prefer local deterministic endpoints and local test servers.
2. Use placeholders when a header or body field needs to show shape.
3. Keep real secrets in a local credential file or test process memory, never in committed fixtures.
4. Run `python3 scripts/secret_hygiene.py examples/workflows` before opening the PR.
5. Document any new placeholder convention in this file before using it in examples.
