# Authenticated Ingress And Production Credentials

Loop 42 makes the self-hosted service fail closed for business requests. It adds one single-team Bearer boundary, execution-time file-backed credential resolution, compact authentication audit events, and an explicit external TLS termination contract. It is not multi-tenant RBAC, OAuth, or a hosted secret manager.

## Required Service Security Configuration

The `skill2workflow-service-0.2.0` configuration requires both security providers:

```json
{
  "auth": {
    "provider": "bearer_token_file",
    "token_file": "/run/secrets/skill2workflow-ingress-token"
  },
  "credentials": {
    "provider": "directory",
    "directory": "/run/secrets/skill2workflow-connectors"
  }
}
```

The configuration must not contain secret values. It stores absolute external file locations and provider names only. Inline tokens, the legacy service schema, missing providers, relative paths, and unknown fields fail validation.

Create the single-team ingress token with at least 32 random bytes, store one token line in the file, and restrict it to the service account:

```bash
chmod 600 /run/secrets/skill2workflow-ingress-token
```

The process refuses a short token, a symbolic-link or non-regular token path, a token above 16 KiB, or a token file accessible by group or others. Each read is bound to one no-follow regular-file descriptor and rejects path replacement between inspection and open. It rereads the file for every business request, so an atomic replacement rotates the token without restarting the service. Missing, malformed, and incorrect Bearer credentials receive HTTP 401 with the same compact response. If the token provider becomes unavailable, readiness changes to `503 not_ready` and business requests fail closed.

Service startup also requires the state and connector credential directories to
be non-symlink directories inaccessible to group or others. Run the read-only
[`service-doctor`](service-doctor.md) preflight before startup or cutover; it
uses the same filesystem and state guards without printing configured values.

`GET /healthz` and `GET /readyz` remain anonymous and expose only process and readiness status. Every other route, including `GET /metrics`, `GET /runs`, `GET /runs/{run_id}`, and the live snapshot, requires `Authorization: Bearer <token>`. Metrics remain scrapeable when readiness is false so operators can diagnose standby or failure state, but they export only the aggregate fixed-label contract in [`observability.md`](observability.md). Authenticated request bodies are capped at 1 MiB before they are read; ambiguous multiple content lengths and transfer-encoded bodies are rejected at this origin boundary.

## Execution-time Connector Credentials

The production service uses credentials provider: `directory`. Each valid Workflow DSL credential handle maps to one file with the same name beneath the configured directory:

```text
/run/secrets/skill2workflow-connectors/demo_api_token
```

The runtime resolves the file at connector execution time, not service startup. Atomic file replacement therefore rotates the next outbound connector call without a process restart. Handles containing path separators or traversal are rejected. The private directory must be `0700`; each value must be a `0600` regular non-symlink UTF-8 file no larger than 64 KiB. Reads are bound to the inspected directory and file identities through one no-follow descriptor, so replacement races and linked files fail closed. Resolved values remain excluded from Workflow DSL, run state, connector audit, ingress audit, and smoke evidence.

The directory is an integration boundary for an operator-managed mount such as a local secret volume. `skill2workflow` does not encrypt, distribute, renew, or host these values.

## Compact Authentication Audit

SQLite audit records contain only:

- `ingress_authenticated` or `ingress_authentication_denied`;
- HTTP method;
- normalized route class (`workflow_trigger`, `run_resume`, `run_cancel`, `run_list`, `run_detail`, or `unknown`);
- timestamp;
- a compact denial reason.

They never store the Authorization header, supplied token, expected token, request body, remote address, or credential value. Operators should monitor denial volume outside the process and protect the loopback proxy from unbounded hostile traffic.

Metrics scrapes do not append authentication audit records, so a normal scrape interval cannot grow the durable business audit log. Their normalized result classes are counted only in process-local telemetry and reset on restart.

## External TLS Termination

The Python service intentionally has no TLS listener. External TLS termination must run on the same host or in the same trusted network namespace and proxy only to the configured loopback address.

The operator boundary is:

```text
client HTTPS -> TLS reverse proxy -> http://127.0.0.1:<service-port>
```

The reverse proxy must:

- accept external workflow traffic only over HTTPS;
- forward the `Authorization` header to the service;
- never log Authorization or request bodies;
- proxy to loopback, never expose the Python port directly;
- apply request-rate and connection limits;
- keep health and readiness probes private to the operator plane;
- replace, rather than trust, inbound forwarding headers.

The application does not trust `X-Forwarded-For`, `X-Forwarded-Proto`, or similar headers for authorization. TLS certificate issuance, cipher policy, and reverse-proxy configuration remain operator responsibilities.

## Verification

Run the real-process compact security evidence smoke:

```bash
python3 scripts/security_boundary_smoke.py \
  --work-dir /tmp/skill2workflow-security-boundary
```

It proves default denial, blocks an overexposed connector credential before any outbound request (`unsafe_credential_file_blocked`), restores mode `0600`, rotates both the ingress token and connector credential without restarting, exits gracefully, and excludes values from audit evidence. `security-boundary-smoke.json` contains only booleans and event counts.

Loop 42 remains a one-team security boundary. It is not multi-tenant RBAC, an OAuth platform, certificate automation, or a hosted credential service.
