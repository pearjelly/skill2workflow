# Changelog

This file records notable user-visible changes. Work remains under
`Unreleased` until maintainers explicitly approve a package version and
release; Roadmap loop completion alone does not publish a new version.

## [Unreleased]

### Added

- Added atomic lifecycle/runtime audit batches and a bounded `audit-consistency`
  report for missing, duplicate, or unexpected projections between durable run
  state and the control-plane audit store.
- Added authenticated remote `GET /api/v1/audit-consistency` and the protected
  `service-audit-consistency` CLI, reusing the exact redacted report contract
  with a fixed response bound and zero-write/readiness-independent behavior.
- Added targeted remote audit inspection with a safe `/run_id` path and
  `service-audit-consistency --run-id`, avoiding global-window truncation while
  preserving the fixed report and error boundaries.
- Added an authenticated, read-only recurring-schedule inventory at
  `GET /api/v1/recurring-schedules` and the protected
  `service-recurring-schedules` CLI, with fixed bounds and trigger-input
  redaction.
- Added protected, idempotent recurring-schedule enable/disable actions at
  `POST /api/v1/recurring-schedules/{schedule_id}/enable|disable` and the
  `service-schedule-enable`/`service-schedule-disable` CLI commands, with
  dispatcher-safe SQLite serialization, fixed response schema, and bounded
  mutation audit evidence.
- Added bounded, authenticated recurring-schedule dispatch diagnostics at
  `GET /api/v1/recurring-schedule-dispatches` and the targeted schedule route,
  plus the protected `service-recurring-dispatches` CLI, with uncertain-state
  visibility and lease/input redaction.
- Added authenticated remote workflow artifact consistency diagnostics at
  `GET /api/v1/workflow-artifacts` and the protected
  `service-workflow-artifacts` CLI, reusing the fixed value-free report with
  bounded issue and response windows.
- Added authenticated remote backup readiness at `GET /api/v1/backup-readiness`
  and the protected `service-backup-readiness` CLI, reusing a fixed redacted
  report with a 16 KiB bound and active-scheduler-lease blocking semantics.
- Added a bounded `workflow-artifacts` registry/file consistency report and
  cleanup of newly-created SQLite publication artifacts after known failures.
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
- Added a Linux CI gate that runs `systemd-analyze verify` against a generated unit without installing or starting a service.
- Added an authenticated human-gate decision endpoint with an exact boolean body, durable success/failure branching, and waiting-only conflict semantics.
- Added protected `service-resume` and `service-cancel` CLI clients that read Bearer tokens from owner-only files and reject unsafe origins, redirects, and unbounded responses.
- Added authenticated redacted run detail at `GET /runs/{run_id}` and the protected `service-show` CLI with a fixed 50-event window and no raw workflow, input, connector, credential, or error payloads.
- Added authenticated redacted run discovery at `GET /runs` and the protected `service-runs` CLI with fixed status counts, a 100-item window, and no payload or credential export.
- Added an authenticated redacted support bundle at `GET /api/v1/support-bundle` and the protected `service-support-bundle` CLI with fixed aggregate observability, a nested run list, and owner-only atomic output.
- Added durable SQLite trigger idempotency: identical keyed retries replay the compact result without a second run, mismatched requests return fixed conflicts, and unresolved outcomes fail closed without storing input values.
- Enforced the existing bounded `policies.default_timeout_ms` runtime boundary at executor safe points, with persisted deadlines, human-gate pause semantics, and fixed timeout failure evidence.
- Added explicit `tool_call.on_fallback` transitions after exhausted connector retries, preserving failed-attempt evidence and promoting fixed fallback audit events.
- Added SQLite `sha256-chain-v1` audit integrity links, compact `audit-verify` verification, legacy-column upgrade, backup rejection for invalid current chains, and retained-copy re-chaining.
- Added a shared 1 MiB canonical UTF-8 trigger-input limit across CLI, webhook, one-shot schedule, and recurring schedule entry paths, with fixed oversize errors and no Workflow DSL compatibility change.
- Added optional bounded declarative `input_schema` contracts for published workflows, with publication validation and pre-idempotency trigger rejection for missing, mistyped, out-of-range, and undeclared input values.
- Added a fixed process-local service admission budget of 16 active business handlers, with a fixed retryable `429` response and probe availability under overload.
- Added stable workflow version promotion aliases with a `promote` CLI command, exact-version precedence, deprecation cleanup, and alias-scoped SQLite idempotency replay across later promotions.
- Added runtime published-artifact integrity verification: reads, promotions, triggers, and executions now compare each artifact with its control-plane checksum and fail closed before side effects when state is missing, malformed, or modified.
- Added reviewable published workflow releases with a bounded `workflow-diff` contract and an optional compare-and-swap precondition for alias promotion.
- Made SQLite workflow alias promotion atomic: the compare-and-swap check, alias mutation, and `workflow_promoted` audit row now commit together, preventing concurrent stale operators from overwriting a newer target.
- Made SQLite workflow publication and deprecation atomic: immutable registry changes and their audit rows commit together, concurrent versions are additive, and same-version matching publication retries are idempotent.
- Added the scoped domestic Feishu task connector and finalized redacted evidence from its controlled paid Pilot.

### Changed

- Advanced the documented maturity to Self-hosted Beta while retaining the single-tenant, one-team deployment boundary.
- Qualified the distributed wheel through an isolated build and install, production CLI coverage, metadata inspection, license verification, and private-artifact exclusion.
- Expanded the supported interpreter evidence to Python 3.9 through 3.14 while keeping runtime code dependency-light.
- Updated the pinned GitHub Actions toolchain to the green Dependabot revisions for checkout 7.0.1 and setup-python 7.0.0.

### Security

- Required authenticated business routes, file-backed ingress secrets, runtime credential-handle resolution, and external TLS termination for network exposure.
- Added a fixed redacted published-artifact integrity failure boundary; the checksum guard detects local artifact tampering but is not a signature or remote-attestation mechanism.
- Added repository security, support, moderation, pull-request, and CI supply-chain policies; GitHub Actions now use fixed reviewed commits, read-only permissions, bounded jobs, and non-persistent checkout credentials.
- Added repository-wide pre-commit hygiene scanning that rejects private paths, runtime state, key material, misplaced binary media, and symbolic links without reading rejected artifacts or echoing suspected secret values.
- Hardened explicit JSON hygiene scans to reject symbolic links, non-regular or unavailable files, invalid UTF-8, invalid JSON, and inputs above 2 MiB with fixed redacted findings instead of tracebacks.
- Hardened the local webhook adapter with the same bounded request-body and strict `Content-Length` contract as the authenticated service boundary.
- Hardened authenticated run-action bodies so malformed, oversized, transfer-encoded, or ambiguous requests return fixed JSON errors instead of terminating the handler.
- Restricted the unauthenticated local webhook adapter to loopback hosts so a local test command cannot be accidentally exposed on a public interface.
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
