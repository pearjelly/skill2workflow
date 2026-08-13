# Deployment Service Probe

Loop 95 adds the installed `service-probe` command for supervisors, reverse
proxies, and CI cutovers that need one stable answer about the live service.
It performs two read-only requests to the existing public probe endpoints; it
does not add an HTTP route, require an ingress token, or mutate runtime state.

## Command

```bash
skill2workflow service-probe --service-url https://service.example
```

The URL must be an HTTPS origin without credentials, query, fragment, or path.
Plain HTTP is accepted only for loopback origins, which keeps local smoke tests
possible without weakening the external TLS boundary. The client disables
proxies and redirects, uses a five-second timeout per request, and accepts at
most 8 KiB from each endpoint.

## Fixed contract

The command first reads `GET /healthz`, then `GET /readyz`. Its JSON output is
defined by [`schemas/service-probe-0.1.0.schema.json`](../schemas/service-probe-0.1.0.schema.json):

```json
{
  "schema_version": "skill2workflow-service-probe-0.1.0",
  "status": "ready",
  "health": {"status": "ok", "http_status": 200},
  "readiness": {"status": "ready", "http_status": 200}
}
```

`status` is `ready` only when both fixed payloads return HTTP 200. It is
`not_ready` when health is valid and readiness returns the service's exact
HTTP 503 `{"service":"skill2workflow","status":"not_ready"}` payload. Any
network failure, redirect, unsafe response headers, invalid JSON, unexpected
status, or unexpected payload produces `unavailable`. The output never copies
server error bodies, headers, URLs, paths, or credentials.

The process exit codes are stable for automation:

| Exit code | Meaning |
| ---: | --- |
| `0` | `status: "ready"` |
| `1` | `status: "not_ready"`, or a locally invalid URL |
| `2` | `status: "unavailable"` |

The health and readiness endpoints remain intentionally unauthenticated so a
process supervisor can use them before protected application traffic is
enabled. Expose them externally only through the deployment's existing TLS and
network policy.

## Safe operating sequence

1. Run `service-doctor` against the generated configuration before startup.
2. Use `service-probe` for the live cutover gate and require exit code `0`.
3. Use the authenticated `service-operational-readiness` report for deeper
   artifact, audit, and backup checks; this probe does not replace it.

## Verification

```bash
PYTHONWARNINGS=ignore::ResourceWarning PYTHONPATH=src python3 -m unittest \
  tests.test_service_client.ServiceClientTests.test_service_probe_returns_fixed_ready_contract_without_credentials \
  tests.test_service_client.ServiceClientTests.test_service_probe_distinguishes_not_ready_from_unavailable \
  tests.test_cli.CliTests.test_service_probe_command_prints_contract_and_maps_ready_exit_code \
  -v
```
