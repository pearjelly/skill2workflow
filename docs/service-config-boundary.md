# Runtime Service Configuration Boundary

Loop 167 hardens the configuration file read performed before the
self-hosted service starts.

## Contract

`skill2workflow service` and `service-doctor` accept at most `65,536` bytes
(`64 KiB`) of service configuration. The loader requires a regular,
non-symlink file, checks its size before opening it, binds the read to the
same device/inode, reads at most one byte beyond the limit, and rechecks the
path after reading. A replacement, growth race, unavailable file, invalid
UTF-8, or malformed JSON fails closed with a stable configuration error.

The limit protects startup parsing and does not replace the separate runtime
Doctor checks for state, credentials, authentication, SQLite integrity, and
loopback binding. The generated service workspace still publishes
`config/service.json` as an owner-only `0600` file; this loader intentionally
does not claim to establish filesystem ownership or permissions on hand-made
configurations.

## Scope and exclusions

This is a local startup-file boundary for the versioned
`skill2workflow-service-0.2.0` document. It does not change the service HTTP
body limits, credential-file reads, Workflow DSL compatibility, or the
single-tenant deployment model. It does not provide encrypted configuration,
secret management, remote configuration, or multi-tenant isolation.
