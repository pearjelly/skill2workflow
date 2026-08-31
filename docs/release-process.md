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
PYTHONPATH=src python3 scripts/release_preflight.py --version 0.1.1 --notes docs/releases/v0.1.1.md --dry-run --production-baseline
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

When `--production-baseline` is supplied, it also runs the fixed 19-check
Production Baseline evidence bundle. Without that flag, the preflight keeps its
historical artifact-only command set for faster routine checks.

The isolated wheel smoke also executes the installed `systemd-unit` command
against a fixed-port secure workspace and checks its redacted least-privilege
unit output. This proves the deployment command is present in the distributed
artifact; it does not claim that the release host runs Linux systemd.

The command fails before any GitHub operation when the changelog, release
notes, package version, module version, or tag inputs disagree.

## Release PR Evidence

Release PRs should include the preflight output and any extra release-specific checks. At minimum, include:

```bash
PYTHONPATH=src python3 scripts/release_preflight.py --version <version> --notes docs/releases/v<version>.md --dry-run
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-release-package-smoke
python3 scripts/reproducible_build.py --work-dir /tmp/skill2workflow-release-reproducible-build
python3 scripts/service_soak_smoke.py --work-dir /tmp/skill2workflow-release-service-soak --cycles 3 --triggers-per-cycle 6
python3 scripts/pilot_playbook_smoke.py --work-dir /tmp/skill2workflow-release-pilot
python3 scripts/pilot_scenario_pack_smoke.py --work-dir /tmp/skill2workflow-release-pilot-pack
python3 scripts/external_connector_smoke.py --work-dir /tmp/skill2workflow-release-external-connector
python3 scripts/quickstart_smoke.py --work-dir /tmp/skill2workflow-release-quickstart
python3 scripts/production_baseline_smoke.py --work-dir /tmp/skill2workflow-release-production-baseline
git diff --check
```

The package smoke output includes the generated
`release-artifact-manifest.json` and `release-artifact-sbom.json`; attach or
publish both companion files with a release when users need an independently
verifiable wheel hash, member inventory, and SPDX package inventory. See
[`release-artifact-manifest.md`](release-artifact-manifest.md) and
[`release-artifact-sbom.md`](release-artifact-sbom.md).

The reproducibility command writes `reproducible-build.json` after two
fixed-epoch wheel builds compare byte-for-byte. Review its schema and limits in
[`reproducible-builds.md`](reproducible-builds.md); it is evidence for this
checkout and toolchain, not an artifact signature or registry attestation.

The CI `artifact-gates` job repeats the isolated package qualification, the
fixed-epoch reproducibility proof, and repository secret-hygiene scan on
Python 3.14. A release PR must keep this job green; the generated evidence
files remain value-free and are not a signing or registry publication step.

The CI `operational-gates` job also runs the state-safety and recovery drills
on Python 3.14: backup/restore, state upgrade, retention, cancellation,
interrupted recovery, one-shot and recurring scheduling, and the service
Doctor. Reproduce the same isolated sequence before a release PR:

It also runs the three-cycle service soak and cutover drill, which verifies
repeated authenticated triggers, idempotency replay/conflict handling, graceful
shutdown, and SQLite/audit continuity. See
[`service-soak.md`](service-soak.md) for its bounded evidence contract.

The separate CI `user-journey-gates` job runs the local Pilot, scenario pack,
explicit connector fixture, and installed quickstart journeys on Python 3.14.
They use only loopback receivers, local fixtures, and isolated wheel installs;
they do not validate a live SaaS provider or hosted deployment.

```bash
python3 scripts/backup_restore_smoke.py --work-dir /tmp/skill2workflow-release-backup-ci
python3 scripts/state_upgrade_smoke.py --work-dir /tmp/skill2workflow-release-upgrade-ci
python3 scripts/retention_smoke.py --work-dir /tmp/skill2workflow-release-retention-ci
python3 scripts/cancellation_smoke.py --work-dir /tmp/skill2workflow-release-cancellation-ci
python3 scripts/interrupted_recovery_smoke.py --work-dir /tmp/skill2workflow-release-interrupted-ci
python3 scripts/schedule_smoke.py --work-dir /tmp/skill2workflow-release-schedule-ci
python3 scripts/recurring_scheduler_smoke.py --work-dir /tmp/skill2workflow-release-recurring-ci
python3 scripts/service_doctor_smoke.py --work-dir /tmp/skill2workflow-release-doctor-ci
python3 scripts/production_baseline_smoke.py --work-dir /tmp/skill2workflow-release-production-baseline-ci
```

These are local deterministic drills, not a claim of hosted disaster recovery,
exactly-once delivery, external-provider availability, or automatic service
orchestration.

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

When a release changes run cancellation, executor safe points, retry behavior
(including retry delay/backoff), service concurrency, or the cancellation ledger,
also include:

```bash
PYTHONPATH=src python3 -m unittest tests.test_cancellation tests.test_cancellation_docs -v
python3 scripts/cancellation_smoke.py --work-dir /tmp/skill2workflow-release-cancellation
```

Release notes must state that cancellation is cooperative, that an already sent external request is not forcefully interrupted, and whether the retention policy version changes.

For cross-database operator-action recovery changes, also run the focused
resume/cancellation reconciliation tests and document that a `503` can follow
a durable state commit; operators retry the same idempotent action rather than
starting a new workflow or decision.

When a release changes service configuration, ingress-token handling,
credential/state directory checks, SQLite startup validation, or bind behavior,
also include:

```bash
PYTHONPATH=src python3 -m unittest tests.test_service_doctor tests.test_service_doctor_docs -v
python3 scripts/service_doctor_smoke.py --work-dir /tmp/skill2workflow-release-doctor
PYTHONPATH=src python3 -m unittest tests.test_credentials tests.test_security_docs -v
python3 scripts/security_boundary_smoke.py --work-dir /tmp/skill2workflow-release-security
python3 scripts/live_control_snapshot_smoke.py --work-dir /tmp/skill2workflow-release-live-snapshot
python3 scripts/observability_smoke.py --work-dir /tmp/skill2workflow-release-observability
python3 scripts/service_boundary_smoke.py --work-dir /tmp/skill2workflow-release-service-boundary
```

Release notes must preserve the fixed secret-free check vocabulary, stable exit
codes, read-only workspace boundary, and the distinction between Doctor
preflight and live `/readyz` ownership.

## CI Dry-Run

`.github/workflows/release-preflight.yml` runs a pull-request dry-run for release-related files. It reads the package version from `pyproject.toml`, derives `docs/releases/v<version>.md`, and runs:

```bash
PYTHONPATH=src python scripts/release_preflight.py --version <version> --notes docs/releases/v<version>.md --dry-run --skip-git --production-baseline
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
python3 scripts/reproducible_build.py --work-dir /tmp/skill2workflow-release-reproducible-build
python3 scripts/service_soak_smoke.py --work-dir /tmp/skill2workflow-release-service-soak --cycles 3 --triggers-per-cycle 6
python3 scripts/production_baseline_smoke.py --work-dir /tmp/skill2workflow-release-production-baseline
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
