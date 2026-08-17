# Local Credential File Boundary

Loop 168 hardens the JSON credential map accepted by the local CLI
`--credential-file` option. The file is a local evaluation convenience; the
self-hosted service uses the separate execution-time directory provider in
[`credential-boundary.md`](credential-boundary.md).

## Read Contract

`load_credential_file` accepts at most **2,097,152 bytes (2 MiB)**. Before JSON
parsing it:

1. inspects the path with `lstat` and requires one regular, non-symlink file;
2. rejects a file already larger than the bound before opening it;
3. opens with no-follow semantics where the platform provides them;
4. binds the descriptor to the inspected device/inode;
5. reads at most one byte beyond the bound and rejects growth races;
6. rechecks the path identity and size after reading; and
7. decodes UTF-8 JSON, failing closed with a value-free unavailable error for
   malformed, deeply nested, or non-UTF-8 input.

The JSON contract is unchanged:

```json
{
  "credentials": {
    "demo_api_token": "local-secret-value"
  }
}
```

The loaded values remain process-local and are used only by connector
execution. They must never be committed, printed, persisted in Workflow DSL,
run state, or audit evidence. This local path intentionally does not add a
permission-bit requirement; operators should still keep credential files
owner-only and use the service directory provider for long-running service
deployments.

## Verification

The boundary is covered by `tests/test_credentials.py` for pre-open size
rejection, symlink and path-replacement fencing, read-growth rejection, and
existing-shape compatibility. The focused command is:

```bash
PYTHONPATH=src python3 -m unittest tests.test_credentials -v
```

This is a local file-read boundary only. It does not provide encryption,
secret-manager integration, remote configuration, multi-tenant isolation, or
exactly-once provider effects.
