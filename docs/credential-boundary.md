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

## Runtime Boundary

The built-in HTTP connector accepts static request metadata so examples can run from a fresh checkout. It does not provide secret storage or runtime secret injection.

The current local runtime does not implement:

- secret managers
- token injection
- credential provider resolution
- runtime redaction
- RBAC or IAM
- product-specific SaaS credential flows
- connector marketplace credentials

Future credential provider work should keep secret material outside immutable Workflow DSL artifacts. Workflow DSL may reference credential handles later, but the referenced secret values should live in a separate provider boundary with its own audit, validation, and redaction rules.

## Contributor Guidance

When adding connector examples:

1. Prefer local deterministic endpoints and local test servers.
2. Use placeholders when a header or body field needs to show shape.
3. Keep real secrets in your local shell or test environment, never in committed fixtures.
4. Run `python3 scripts/secret_hygiene.py examples/workflows` before opening the PR.
5. Document any new placeholder convention in this file before using it in examples.
