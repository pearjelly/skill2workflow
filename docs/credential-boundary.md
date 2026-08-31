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
python3 scripts/secret_hygiene.py --repository-root .
```

Repository mode examines Git-tracked and unignored candidate paths before a
commit. It rejects private directories, credential/environment files, key and
SQLite artifacts, JSONL state, and binary media outside `docs/assets`. It does
not read rejected binary artifacts. Allowed JSON files receive the existing
value scan through a non-symlink regular-file descriptor with a 2 MiB limit.
Invalid, unavailable, linked, or oversized JSON fails closed, and suspected
values are always reported as `<redacted>`.

The command prints JSON:

```json
{
  "ok": true,
  "scanned": ["examples/workflows/http-connector.workflow.json"],
  "findings": []
}
```

When a finding exists, the command exits with status `1` and reports only the
file, JSON path, reason, and a fixed `<redacted>` or `<not-read>` marker. It
never reports a suspected secret prefix.

The scanner is intentionally conservative and dependency-free. It catches obvious secret-like keys and values in committed JSON fixtures; it is not a replacement for repository secret scanning or human review.

The same scanner also runs before `authoring-export` writes a local authoring
artifact directory, and again while `authoring-verify` reads one. It returns
only fixed refusal information on this path; a rejected export leaves no
artifact directory, while a rejected verification never echoes a matching
value.

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

## Self-hosted Service Provider

The production service path does not accept `--credential-file`. Its required directory provider maps each credential handle to an external file and rereads that file at connector execution time. This supports operator-managed rotation without storing resolved values in service configuration or retaining them in memory at startup.

The directory must be an absolute, non-symlink directory accessible only to
its owner (`0700`). Every resolved handle must name a regular non-symlink UTF-8
file with mode `0600` and at most 64 KiB. Resolution inspects the directory and
file, opens the value with no-follow semantics, then verifies the same directory
and file identities through the opened regular-file descriptor before reading.
Path replacement, symbolic links, devices, sockets, wide permissions, invalid
UTF-8, empty values, and oversized input all fail with the same value-free
`credential handle not found` boundary.

Rotation remains execution-time and atomic: write the replacement as `0600` in
the same private directory, fsync it according to the operator's durability
policy, then atomically rename it onto the handle. An in-place update also
remains visible to the next execution, but atomic replacement avoids partial
reads. The provider never returns a partially inspected replacement.

See [`security-boundary.md`](security-boundary.md) for handle validation, filesystem containment, ingress authentication, audit evidence, and the external TLS termination boundary. The older JSON credential file remains supported only for explicit local CLI evaluation paths. That file is bounded to 2 MiB and read through a regular-file, no-follow, device/inode-checked descriptor; see [`credential-file-boundary.md`](credential-file-boundary.md).

Verified state backups intentionally exclude the service configuration, Bearer token file, mounted credential directory, and unrelated state-directory files. Restore those external providers separately and rotate values according to policy. The backup still contains workflow and run business data and therefore requires its own encryption and access controls; see [`backup-restore.md`](backup-restore.md).

## Connector Extension Requirements

Connector extensions must preserve the same credential boundary as the built-in HTTP connector:

- Workflow DSL may store credential handles, never resolved credential values.
- Trigger input and input mapping payloads must not carry credentials, tokens, private keys, cookies, or production authorization headers.
- Connector manifests must describe handle support under `credential_contract`.
- Resolved credential values may be used only inside connector execution.
- Connector results, run state, snapshots, LiteGraph overlays, and audit events must not include resolved credential values.
- Audit metadata should expose compact connector status, attempt, policy, and key names only.

Future product-specific connectors must use handles first. Hosted secret stores, OAuth flows, and IAM require separate design work before they can become runtime features.

## Runtime Boundary

The current runtime does not implement:

- secret managers
- hosted credential stores
- credential encryption at rest
- RBAC or IAM
- product-specific SaaS credential flows
- connector marketplace credentials

The provider boundary is intentionally dependency-free. The self-hosted service supports an externally mounted credential directory, but it is not a production secret manager by itself.

## Contributor Guidance

When adding connector examples:

1. Prefer local deterministic endpoints and local test servers.
2. Use placeholders when a header or body field needs to show shape.
3. Keep real secrets in a local credential file or test process memory, never in committed fixtures.
4. Run `python3 scripts/secret_hygiene.py examples/workflows` before opening the PR.
5. Run `python3 scripts/secret_hygiene.py --repository-root .` before staging broad changes.
6. Document any new placeholder convention in this file before using it in examples.
