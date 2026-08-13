# Changelog

This file records notable user-visible changes. Work remains under
`Unreleased` until maintainers explicitly approve a package version and
release; Roadmap loop completion alone does not publish a new version.

## [Unreleased]

### Added

- Added an authenticated self-hosted runtime service with loopback-safe defaults, health and readiness probes, graceful shutdown, and durable SQLite state.
- Added durable recurring scheduling with explicit missed-run policies, persisted dispatch records, lease takeover, and uncertain-recovery handling.
- Added verified offline backup and restore, explicit copy-on-write state upgrade, and operator-controlled data retention for supported SQLite layouts.
- Added bounded runtime observability through authenticated Prometheus metrics and allowlisted operational NDJSON.
- Added durable cooperative cancellation and interrupted-run recovery with execution tickets, stale-writer fencing, and no automatic replay of unknown external effects.
- Added a secure service bootstrap and an installed controlled quickstart that reaches a durable human approval gate without a source checkout.
- Added a read-only `service-doctor` command with fixed secret-free diagnostics for configuration, authentication, credential directories, SQLite state, and loopback binding.
- Added descriptor-bound connector credential reads with private-directory and file permissions, no-follow identity checks, a 64 KiB limit, and execution-time atomic rotation.
- Added authenticated live Operator snapshots with a machine-readable schema, consistent collection windows, fixed byte bounds, a safe no-redirect CLI client, zero-write polling, and owner-only atomic output.
- Added a manually reviewed Linux systemd unit generator with non-overwriting output, state-only write access, fixed hardening directives, restart backoff, and SIGTERM-only shutdown.
- Added the scoped domestic Feishu task connector and finalized redacted evidence from its controlled paid Pilot.

### Changed

- Advanced the documented maturity to Self-hosted Beta while retaining the single-tenant, one-team deployment boundary.
- Qualified the distributed wheel through an isolated build and install, production CLI coverage, metadata inspection, license verification, and private-artifact exclusion.
- Expanded the supported interpreter evidence to Python 3.9 through 3.14 while keeping runtime code dependency-light.

### Security

- Required authenticated business routes, file-backed ingress secrets, runtime credential-handle resolution, and external TLS termination for network exposure.
- Added repository security, support, moderation, pull-request, and CI supply-chain policies; GitHub Actions now use fixed reviewed commits, read-only permissions, bounded jobs, and non-persistent checkout credentials.
- Added repository-wide pre-commit hygiene scanning that rejects private paths, runtime state, key material, misplaced binary media, and symbolic links without reading rejected artifacts or echoing suspected secret values.
- Hardened explicit JSON hygiene scans to reject symbolic links, non-regular or unavailable files, invalid UTF-8, invalid JSON, and inputs above 2 MiB with fixed redacted findings instead of tracebacks.
- Bound state-layout marker validation to one owner-only regular-file descriptor, rejected path-replacement races, and capped marker input at 16 KiB before decoding.
- Generated systemd units carry no secret values or `Environment=` entries and require a private regular service configuration plus a non-symlink executable.
- Bound ingress-token reads to one owner-only no-follow regular-file descriptor, capped token input at 16 KiB, and made service startup reject unsafe state or credential directory permissions.
- Required directory-backed connector credentials to use `0700` directories and `0600` regular files; symbolic links, replacement races, invalid UTF-8, empty values, and oversized inputs now fail closed without value disclosure.
- Restored the byte-for-byte official Apache License 2.0 text and made wheel qualification reject any modified or truncated license copy.
- Added maintainer-led governance and CODEOWNERS review routing for legal, security, release, schema, and runtime boundaries.

### Compatibility

- Workflow DSL `0.1.0` remains the execution truth source and stays readable by the current runtime.
- Existing unversioned SQLite state requires an explicit verified state upgrade into a new directory before current production commands use it.
- The runtime does not provide exactly-once execution, automatic provider reconciliation, hosted multi-tenancy, built-in TLS, or forceful interruption of an already-sent external request.
- The package remains version `0.1.0` until a separate release change approves and prepares the next version.

## [0.1.0] - 2026-07-03

- Published the first open-source bootstrap release with Skill parsing, Workflow DSL compilation and validation, durable local execution, human-gate pause/resume, connector execution, auditability, LiteGraph visualization, and the initial contributor and compatibility contracts. See the [v0.1.0 release notes](docs/releases/v0.1.0.md).

[Unreleased]: https://github.com/pearjelly/skill2workflow/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pearjelly/skill2workflow/releases/tag/v0.1.0
