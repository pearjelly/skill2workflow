# Service Ingress-Token Rotation

The self-hosted service uses one owner-only Bearer token file. Loop 89 adds a
local, atomic rotation command so an operator can replace that credential
without editing configuration, printing the token, or restarting the service.

```bash
skill2workflow service-token-rotate \
  --config /srv/skill2workflow/config/service.json
```

The command reads and validates the configured token file, creates a new
cryptographically random token in the same private directory, and publishes it
with an atomic `os.replace` after rechecking the original file identity. The
replacement remains owner-only (`0600`) and the parent directory must remain a
private, non-symlink directory. The old token is not returned and is invalid
on the next request. The running service rereads the file per request, so no
restart is required.

The command prints only this fixed result shape:

```json
{
  "schema_version": "skill2workflow-service-token-rotation-result-0.1.0",
  "status": "rotated",
  "token_file": "/srv/skill2workflow/secrets/ingress-token"
}
```

The token value never appears in stdout, stderr, configuration, audit events,
or repository evidence. Read the protected file through the operator's secret
handling mechanism when updating a reverse proxy, scraper, or CLI environment.
Treat rotation as a local filesystem operation and coordinate consumers so the
old token is replaced everywhere before it is discarded.

The command is deliberately not a remote API: making credential replacement a
remote request would make a lost response ambiguous and could strand the only
operator credential. It also does not manage multiple active tokens, expiry,
OAuth, RBAC, external secret managers, or service-manager reloads.

Run the focused checks with:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_service_bootstrap.ServiceBootstrapTests.test_rotate_replaces_valid_token_atomically_without_returning_secret \
  tests.test_service_bootstrap.ServiceBootstrapTests.test_rotate_rejects_unsafe_or_invalid_inputs_without_mutating_old_token \
  tests.test_service_bootstrap.ServiceBootstrapTests.test_rotate_fails_closed_when_token_path_changes_during_generation \
  tests.test_service.RuntimeServiceTests.test_business_routes_require_rotatable_bearer_auth_and_write_compact_audit \
  -v
```
