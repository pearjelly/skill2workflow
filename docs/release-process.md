# Release Process

This project keeps release creation manual until the release automation has been exercised on a patch release. The preflight command is read-only: it checks release inputs and verification evidence, but it does not create tags, publish GitHub Releases, upload packages, or write repository state.

## Maintainer Preflight

Before opening a release PR for a future patch release, update all release inputs in the branch:

- `pyproject.toml`
- `src/skill2workflow/__init__.py`
- `CHANGELOG.md`
- `docs/releases/v<version>.md`

Move the finalized user-visible entries from `Unreleased` into exactly one
`## [<version>] - YYYY-MM-DD` target version heading. Keep the `Unreleased`
heading above all released versions for later work. Updating the changelog
does not authorize a version bump or release; version selection remains an
explicit maintainer decision. Release notes may carry the detailed rollout
and migration narrative, while the changelog remains the concise history.

Then run the full local preflight from a clean branch:

```bash
PYTHONPATH=src python3 scripts/release_preflight.py --version 0.1.1 --notes docs/releases/v0.1.1.md --dry-run
```

The command checks:

- package version in `pyproject.toml`
- module version in `src/skill2workflow/__init__.py`
- changelog target version heading and non-empty entry
- release notes filename and content
- clean working tree
- local and `origin` tag availability
- full unit suite
- Python module compilation
- an isolated wheel build, install, console-script, service-help, and validation smoke

The command fails before any GitHub operation when the changelog, release
notes, package version, module version, or tag inputs disagree.

## Release PR Evidence

Release PRs should include the preflight output and any extra release-specific checks. At minimum, include:

```bash
PYTHONPATH=src python3 scripts/release_preflight.py --version <version> --notes docs/releases/v<version>.md --dry-run
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-release-package-smoke
git diff --check
```

If the preflight command already ran the unit suite, compile check, and isolated
wheel qualification, it is acceptable to cite that output once instead of
duplicating the logs. The package smoke must build a wheel and install that
artifact into a separate virtual environment; an editable install is not
release evidence.

When a release changes SQLite state identity, backup manifests, or migration code, also include both recovery drills:

```bash
python3 scripts/backup_restore_smoke.py --work-dir /tmp/skill2workflow-release-backup
python3 scripts/state_upgrade_smoke.py --work-dir /tmp/skill2workflow-release-upgrade
```

Release notes must name the source and target state layouts, whether an explicit upgrade is required, the stop/cutover sequence, and the rollback binary and directory boundary.

When a release changes retention eligibility, deletion SQL, SQLite compaction, or retained-copy publication, also include:

```bash
python3 scripts/retention_smoke.py --work-dir /tmp/skill2workflow-release-retention
```

Release notes must call out any retention policy compatibility change and preserve the stopped-service, protected-state, residual-source, and operator-controlled destruction boundaries.

When a release changes run cancellation, executor safe points, retry behavior, service concurrency, or the cancellation ledger, also include:

```bash
PYTHONPATH=src python3 -m unittest tests.test_cancellation tests.test_cancellation_docs -v
python3 scripts/cancellation_smoke.py --work-dir /tmp/skill2workflow-release-cancellation
```

Release notes must state that cancellation is cooperative, that an already sent external request is not forcefully interrupted, and whether the retention policy version changes.

When a release changes service configuration, ingress-token handling,
credential/state directory checks, SQLite startup validation, or bind behavior,
also include:

```bash
PYTHONPATH=src python3 -m unittest tests.test_service_doctor tests.test_service_doctor_docs -v
python3 scripts/service_doctor_smoke.py --work-dir /tmp/skill2workflow-release-doctor
PYTHONPATH=src python3 -m unittest tests.test_credentials tests.test_security_docs -v
python3 scripts/security_boundary_smoke.py --work-dir /tmp/skill2workflow-release-security
python3 scripts/live_control_snapshot_smoke.py --work-dir /tmp/skill2workflow-release-live-snapshot
```

Release notes must preserve the fixed secret-free check vocabulary, stable exit
codes, read-only workspace boundary, and the distinction between Doctor
preflight and live `/readyz` ownership.

## CI Dry-Run

`.github/workflows/release-preflight.yml` runs a pull-request dry-run for release-related files. It reads the package version from `pyproject.toml`, derives `docs/releases/v<version>.md`, and runs:

```bash
PYTHONPATH=src python scripts/release_preflight.py --version <version> --notes docs/releases/v<version>.md --dry-run --skip-git
```

CI skips git cleanliness and tag availability because pull-request checkouts are not the release source of truth and the current released tag may already exist. Local maintainer preflight must not skip git checks before a real release.

## Manual Fallback

The `v0.1.0` release was created manually from verified `main`. Keep this path available until a patch release proves the automation:

```bash
git switch main
git pull --ff-only
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-release-package-smoke
PYTHONPATH=src python3 -m skill2workflow.cli validate examples/workflows/approval-flow.workflow.json --format json
PYTHONPATH=src python3 -m skill2workflow.cli validate examples/workflows/http-connector.workflow.json --format json
git tag -a v<version> -m "skill2workflow v<version>"
git push origin v<version>
gh release create v<version> --title "skill2workflow v<version>" --notes-file docs/releases/v<version>.md
```

Use the manual fallback only after the release PR has merged and `main` is clean.

## Current Boundary

Release automation is a guardrail, not a publisher. It intentionally does not:

- auto-publish GitHub Releases from pushed tags
- upload packages to a registry
- sign release artifacts
- manage credentials or release approvals
