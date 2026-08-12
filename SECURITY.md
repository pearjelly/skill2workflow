# Security Policy

## Supported Versions

`skill2workflow` is at Self-hosted Beta maturity. Security fixes target the
latest released `0.1.x` version and the current `main` branch. Older snapshots,
forks, modified connector packages, and deployments outside the documented
single-tenant boundary may require their maintainers to port a fix.

| Version | Security fixes |
| --- | --- |
| Current `main` | Yes |
| Latest `0.1.x` release | Yes |
| Older versions | No |

## Report A Vulnerability Privately

Do not open a public issue, discussion, or pull request for a suspected
security vulnerability. Use GitHub's
[private vulnerability report](https://github.com/pearjelly/skill2workflow/security/advisories/new).

If that form is unavailable, open only a detail-free support request asking a
maintainer to establish a private channel. Do not include exploit steps,
credentials, customer data, private workflow state, tokens, provider payloads,
or screenshots containing sensitive values in that request.

A useful private report includes:

- the affected release or commit;
- the security boundary and realistic impact;
- minimal, sanitized reproduction steps;
- whether the issue affects default configuration;
- any safe mitigation already tested.

## Response Targets

Maintainers aim to acknowledge a complete private report within seven calendar
days and provide an initial triage update within fourteen calendar days. These
security response targets are coordination goals, not service-level
guarantees. Remediation and disclosure timing depend on severity, reproducible
evidence, release safety, and reporter coordination.

## Security Boundary

The supported service is loopback-only, self-hosted, single-tenant, and expects
external TLS termination plus operator-managed filesystem permissions. High
value reports include authentication bypass, credential disclosure, unsafe
path or symlink handling, state-integrity failure, cross-workflow data leakage,
or automatic replay after an unknown external side effect.

Executing an intentionally trusted workflow's configured outbound HTTP request
is expected behavior. Hosted multi-tenancy, built-in TLS, OAuth, a managed
secret store, distributed workers, and exactly-once execution are not current
security claims. Read the [service security boundary](docs/security-boundary.md),
[credential boundary](docs/credential-boundary.md), and
[interrupted-run recovery contract](docs/interrupted-recovery.md) before
evaluating those boundaries.

Do not test against a real partner tenant, customer workload, or third-party
account without explicit authorization. Use local fixtures and synthetic data.

## Coordinated Disclosure

Please allow maintainers time to reproduce, fix, test, and release before public
disclosure. The project will credit reporters when requested and safe to do so.
Do not include secrets or private customer evidence in advisories, commits,
release notes, or regression fixtures.
