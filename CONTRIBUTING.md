# Contributing to skill2workflow

For executable HTTP result checks, see [HTTP JSON assertions](docs/http-json-assertions.md).
The package smoke runs their real loopback CLI checks against the isolated
wheel; keep that contract aligned when changing connector execution.

Thank you for helping improve `skill2workflow`. The project is currently at
Self-hosted Beta maturity, so the most valuable contributions are scoped,
runnable, and easy to verify without overstating the production boundary.

## Project Direction

`skill2workflow` converts standard Agent `SKILL.md` files into controlled workflows that can be validated, visualized, executed, resumed, and audited.

The Workflow DSL is the execution truth source. LiteGraph JSON and the web editor are views and authoring surfaces; they must round-trip through Workflow DSL before execution or publication.

UI static resources are a fixed public inventory, not a directory tree. Keep
`UI_STATIC_FILES`, package data and the strict release-manifest inventory equal
when adding an asset. Run `tests.test_ui_static_boundary` and the package smoke;
the latter requires installed-only GET/HEAD and synthetic private-file refusal
evidence. The static loader requires no-follow descriptor-relative file support;
do not add a path-based fallback or loosen the gate to bypass that requirement.

## Local Setup

Requirements:

- Python 3.9 or newer
- Git
- A shell that can run the commands below

This bootstrap harness intentionally uses the Python standard library for runtime code. No runtime dependency install is required for tests.

Run the full test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Use `tests.http_fixtures.HTTPServer` or `ThreadingHTTPServer` for owned local
HTTP fixtures. They inherit the real stdlib protocol and shutdown behavior but
use a 10 ms idle polling interval, avoiding repeated half-second teardown waits.
Explicit intervals remain supported. Keep this optimization test-only: do not
change production server polling, bypass network assertions, or relax release
deadlines to speed up tests. Restore scoped substitutions and join/close owned
servers during cleanup.

The optional production-baseline bundle keeps all 19 checks within a shared
execution budget on qualified POSIX hosts. Its supervisor must stop the owned
process group and reap its direct child before normal artifact cleanup; an
unconfirmed stop preserves the work directory and fails the bundle. Do not
replace this with direct-child-only termination, reset the suite budget between
checks, or treat skipped checks as a passing release. See
[execution/cleanup limits](docs/production-baseline-evidence.md).

Editor renderer/export changes also run the dependency-free JavaScript behavior
tests with Node.js (development only, not a Python runtime dependency). Graph
export tests use the real bundled LiteGraph and invoke the Python write-back CLI:

```bash
node --test tests/test_*.cjs
```

The release artifact CI job runs these checks alongside wheel qualification.

For the local draft-input helper and packaged editor module, the focused drill
compiles a synthetic Skill and checks omitted, invalid, corrected and missing-
mapping input without a live provider:

```bash
PYTHONPATH=src python3 scripts/draft_input_ui_smoke.py
```

Package qualification also runs it through the isolated installed CLI with
source imports disabled, including all eight existing schema rejection reasons.
The release-artifact job additionally requires the actual served module to
render those real reports through the Node regression suite:

```bash
python3 scripts/draft_input_ui_smoke.py --executable /path/to/installed/skill2workflow --browser-module-tests
```

This optional local flag is mandatory in that CI job; Node remains development
tooling only. Keep new browser modules in both the wheel data list
and the release artifact's strict public-member allowlist.

CI repeats the full release-relevant checks on Python 3.9 and 3.14, covering
the supported floor and the primary runtime baseline. The Python 3.9 matrix
entry and release preflight use Ubuntu 24.04 because `setup-python` does not
provide Python 3.9 for Ubuntu 26.04; Python 3.14 continues on `ubuntu-latest`.
Each matrix entry also
runs the security-boundary, observability, and service restart-continuity
smokes, while a dedicated Python 3.14 job runs the backup, migration,
retention, cancellation, crash-recovery, scheduling, and Doctor gates. A green
unit suite therefore cannot hide a broken real-process or state-safety
boundary. Contributors may use any supported Python locally;
compatibility-sensitive changes should be reviewed against both matrix
endpoints.

Parser changes must preserve the checked-in Checklist fixtures and exercise
the explicit `Workflow`/`Steps` fallback through `tests.test_process_steps`,
CLI/editor compilation, and installed-wheel qualification. The accepted
heading/list grammar is documented in [the Skill input boundary](docs/skill-input-boundary.md#explicit-process-sections).

Run `tests.test_skill_frontmatter` for identity isolation, quoted/commented
strings, block-scalar folding/chomping and fixed refusals. The installed
process-section drill now also requires the intended root name, decoded folded
description and unchanged source lines despite colliding nested metadata. The
documented [frontmatter subset](docs/skill-input-boundary.md#frontmatter-identity-and-text)
is not full YAML support; do not add constructors, alias resolution or a runtime
dependency as an incidental parser fix.

Run `tests.test_skill_compile_diagnostics` and
`node --test tests/test_skill_compile_recovery.cjs` for safe refusal wording,
legacy/opt-in boundaries, draft retention and stale-request fencing. The
installed package gate requires ten CLI/API recovery cases; the artifact CI
also requires real installed reports rendered through the served editor and
pinned vendor modules, not source markers:

```bash
python3 scripts/skill_compile_recovery_smoke.py --executable /path/to/installed/skill2workflow --browser-module-tests
```

Node is development qualification only, not a runtime dependency. Keep error
evidence source-free and preserve the library's fixed `ValueError` text.

Versioned Skill iteration is covered by `tests.test_skill_workflow_version` and
the installed-only package gate. Run the full synthetic two-version journey:

```bash
python3 scripts/skill_version_smoke.py
python3 scripts/skill_version_smoke.py --executable /path/to/installed/skill2workflow
```

It requires compile/export/repair, Bundle review, immutable publication and
version-pinned runs plus quickstart/local-helper evidence, with no live provider.
Keep the no-declaration `0.1.0` output and original source lines unchanged;
ordinary metadata must never become deployment version intent.

Run `node --test tests/test_draft_load_ownership.cjs` for latest-intent import
ownership, cross-source cancellation, edit/snapshot fencing, fallback suppression
and fixed JSON recovery. The existing installed
`scripts/skill_compile_recovery_smoke.py --executable … --browser-module-tests`
qualification now requires both recovery and ownership suites against the actual
served app/vendor modules. That flag remains mandatory in artifact CI; Node is
development-only and ordinary Python installation remains unchanged. The Python
gate test verifies both suites are required without adding Node to the unit-suite
requirements.

A separate Python 3.14 CI job also runs the local end-user journeys: the
customer-support Pilot, the three-scenario Pilot pack, explicit external
connector loading, and the installed-wheel quickstart. These drills use local
receivers and fixtures only; they do not call a live provider or require a
credential.

Optionally install the checkout in editable mode to use the `skill2workflow` console script:

```bash
python3 -m venv /tmp/skill2workflow-venv
/tmp/skill2workflow-venv/bin/python -m pip install --upgrade pip "setuptools>=77.0.1"
/tmp/skill2workflow-venv/bin/python -m pip install --no-build-isolation -e .
/tmp/skill2workflow-venv/bin/skill2workflow --help
/tmp/skill2workflow-venv/bin/skill2workflow --version
```

The version check should report the package version from the active
environment. It is useful for catching an unintended PATH or virtualenv
mismatch before reproducing a bug.

You can also run the package smoke helper, which builds a wheel, installs it
into a separate temporary virtual environment, and validates the installed
console script outside the checkout with source-import paths disabled:

```bash
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke
python3 scripts/reproducible_build.py --work-dir /tmp/skill2workflow-reproducible-build
```

The same run emits `release-artifact-manifest.json` and
`release-artifact-sbom.json`, public value-free archive/member integrity and
SPDX inventory companions for release review. The dedicated CI artifact gate
repeats this package qualification on Python 3.14.

The reproducible-build command separately builds the wheel twice with a fixed
epoch and writes `reproducible-build.json`; it proves equality for the current
checkout and toolchain without signing or publishing the artifact.

On Linux, run the systemd smoke with `--systemd-analyze-verify` to exercise the
host parser against the generated unit. This check never installs, enables, or
starts a service; the same verification runs in the Linux CI job.

For the single-service Docker path, use a local Linux Docker Engine and a
non-root operator account:

```bash
python3 scripts/docker_service_smoke.py
```

This builds the wheel-backed image, creates only a temporary private
workspace, verifies the actual container mount and user boundary, checks
service readiness and authenticated go-live, proves an offline backup,
verification, and fresh restore without mounting credentials, then restarts
the original and restored states separately to prove go-live and SQLite file
continuity. It never contacts a live
connector provider.
The dedicated Linux CI job runs the same drill. See the
[Docker self-hosting guide](docs/docker-self-host.md) for deployment commands.

To reproduce the production-boundary CI drills locally:

```bash
python3 scripts/security_boundary_smoke.py --work-dir /tmp/skill2workflow-security-ci
python3 scripts/observability_smoke.py --work-dir /tmp/skill2workflow-observability-ci
python3 scripts/observability_rules_smoke.py
python3 scripts/observability_dashboard_smoke.py
python3 scripts/service_boundary_smoke.py --work-dir /tmp/skill2workflow-service-boundary-ci
python3 scripts/service_soak_smoke.py --work-dir /tmp/skill2workflow-service-soak-ci --cycles 3 --triggers-per-cycle 6
# Full production-baseline evidence is release-scoped and repeats the suite.
python3 scripts/production_baseline_smoke.py --work-dir /tmp/skill2workflow-production-baseline-ci
```

The CI recovery and state-safety gate can be reproduced locally as one isolated
sequence:

```bash
python3 scripts/backup_restore_smoke.py --work-dir /tmp/skill2workflow-backup-ci
python3 scripts/state_upgrade_smoke.py --work-dir /tmp/skill2workflow-state-upgrade-ci
python3 scripts/retention_smoke.py --work-dir /tmp/skill2workflow-retention-ci
python3 scripts/cancellation_smoke.py --work-dir /tmp/skill2workflow-cancellation-ci
python3 scripts/interrupted_recovery_smoke.py --work-dir /tmp/skill2workflow-interrupted-ci
python3 scripts/schedule_smoke.py --work-dir /tmp/skill2workflow-schedule-ci
python3 scripts/recurring_scheduler_smoke.py --work-dir /tmp/skill2workflow-recurring-scheduler-ci
python3 scripts/service_doctor_smoke.py --work-dir /tmp/skill2workflow-service-doctor-ci
```

Each command owns a fresh work directory; the gate never uses live providers,
credentials, or a host service manager.

To reproduce the local user-journey CI gate:

```bash
python3 scripts/pilot_playbook_smoke.py --work-dir /tmp/skill2workflow-pilot-ci
python3 scripts/pilot_scenario_pack_smoke.py --work-dir /tmp/skill2workflow-pilot-pack-ci
python3 scripts/external_connector_smoke.py --work-dir /tmp/skill2workflow-external-connector-ci
python3 scripts/quickstart_smoke.py --work-dir /tmp/skill2workflow-quickstart-ci
python3 scripts/authoring_delivery_smoke.py --work-dir /tmp/skill2workflow-authoring-delivery-ci
```

These commands exercise only local deterministic fixtures and an isolated
installed wheel. They are evidence for the documented user journeys, not a
claim of live-provider reliability or hosted service operation.

Run a fresh-checkout CLI smoke:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli compile examples/skills/approval-flow/SKILL.md -o /tmp/skill2workflow-workflow.json
PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json --format json
PYTHONPATH=src python3 -m skill2workflow.cli visualize /tmp/skill2workflow-workflow.json -o /tmp/skill2workflow-litegraph.json
PYTHONPATH=src python3 -m skill2workflow.cli write-back /tmp/skill2workflow-workflow.json /tmp/skill2workflow-litegraph.json -o /tmp/skill2workflow-edited-workflow.json
```

Run the local executor:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli run /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-state
```

The sample workflow pauses at a human gate. Resume it with the returned run id:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli resume <run_id> --state-dir /tmp/skill2workflow-state
```

Run the deterministic local scheduled-trigger smoke:

```bash
python3 scripts/schedule_smoke.py --work-dir /tmp/skill2workflow-schedule-loop29
```

For durable recurring schedule, runtime service, or scheduler lease changes, run:

```bash
python3 scripts/recurring_scheduler_smoke.py --work-dir /tmp/skill2workflow-recurring-scheduler-loop43
```

For backup, restore, SQLite state layout, or recovery changes, run:

```bash
python3 scripts/backup_restore_smoke.py --work-dir /tmp/skill2workflow-backup-restore-loop44
```

For state layout identity, upgrade, migration, cutover, or rollback changes, also run:

```bash
python3 scripts/state_upgrade_smoke.py --work-dir /tmp/skill2workflow-state-upgrade-loop45
```

For service metrics, route classification, or operational logging changes, also run:

```bash
python3 scripts/observability_smoke.py --work-dir /tmp/skill2workflow-observability-loop46
```

For retention policy, state disposal, or retained-copy cutover changes, also run:

```bash
python3 scripts/retention_smoke.py --work-dir /tmp/skill2workflow-retention-loop47
```

For run lifecycle, cancellation, retry safe-point, or concurrent service changes, also run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_cancellation tests.test_cancellation_docs -v
python3 scripts/cancellation_smoke.py --work-dir /tmp/skill2workflow-cancellation-loop48
```

For service ownership, lease takeover, crash recovery, or stale-writer fencing changes, also run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_interrupted_recovery tests.test_interrupted_recovery_docs -v
python3 scripts/interrupted_recovery_smoke.py --work-dir /tmp/skill2workflow-interrupted-loop49
```

Open the web editor:

```bash
python3 -m http.server 4173
```

Then visit:

```text
http://localhost:4173/web/
```

Generate a control-plane snapshot and inspect it locally:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli control-snapshot --state-dir /tmp/skill2workflow-control -o /tmp/skill2workflow-control-snapshot.json
```

Then visit:

```text
http://localhost:4173/web/control.html
```

## Contribution Lanes

Good first contribution lanes:

- Parser coverage for real-world `SKILL.md` formats
- Workflow node types and compiler rules
- Validator improvements and JSON Schema coverage
- LiteGraph node UI and allowlisted write-back fields
- Executor policies such as retry, timeout, and checkpoint behavior
- Connector manifests and example connectors
- Example workflows for sales, approvals, customer service, risk review, and operations analysis
- Documentation and enterprise adoption guides
- Portable Workflow DSL bundles and reproducible example artifacts

Before changing behavior, read:

- `docs/README.md`
- `ROADMAP.md`
- `HARNESS.md`
- `SECURITY.md`
- `SUPPORT.md`
- `GOVERNANCE.md`
- `CODE_OF_CONDUCT.md`
- `docs/credential-boundary.md`
- `docs/workflow-dsl-contract.md`
- `docs/workflow-dsl-compatibility.md`
- `docs/stability.md`
- `docs/authoring.md`
- `docs/release-process.md`

## Change Rules

- Keep changes scoped to one closed loop.
- Add tests before changing parser, compiler, executor, validator, visualizer, storage, connector, or CLI behavior.
- Keep Workflow DSL as the execution truth source.
- Do not make LiteGraph JSON authoritative for execution.
- Preserve published workflow immutability.
- Do not commit secrets, credentials, private keys, cookies, production authorization headers, or customer data in Workflow DSL or LiteGraph fixtures.
- Avoid runtime dependencies unless they directly support a spec-backed capability.
- Update docs and examples when user-facing behavior changes.
- Add user-visible changes to the `Unreleased` section of `CHANGELOG.md` without choosing a release version in an ordinary feature PR.

## Connector Example Safety

Connector examples should be deterministic and safe from a fresh checkout. Prefer local endpoints such as `http://127.0.0.1` or documented placeholders such as `<redacted>`, `REDACTED`, `placeholder`, `example-token`, and `token-placeholder`.

Connector manifest changes must follow the extension contract in `docs/connectors.md`. Add or update manifest contract tests when changing connector registry metadata. Do not add product-specific SaaS connector packages, dynamic plugin loading, OAuth flows, hosted credential stores, or connector marketplaces without a dedicated roadmap loop.

Run the committed-fixture secret hygiene check before opening connector or example PRs:

```bash
python3 scripts/secret_hygiene.py examples/workflows
python3 scripts/secret_hygiene.py --repository-root .
```

The focused command catches obvious secret-like keys and values in committed
JSON fixtures. Repository mode enumerates tracked files plus unignored local
candidates, rejects private state, credential files, key material, and media
outside `docs/assets`, then scans allowed JSON. Findings never echo suspected
secret values. These checks are guardrails, not replacements for review.

## Pull Request Checklist

Before opening a PR:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke
python3 scripts/reproducible_build.py --work-dir /tmp/skill2workflow-reproducible-build
python3 scripts/secret_hygiene.py examples/workflows
python3 scripts/secret_hygiene.py --repository-root .
git diff --check
```

For Workflow DSL or visualizer changes, also run:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli validate examples/workflows/approval-flow.workflow.json --format json
PYTHONPATH=src python3 -m skill2workflow.cli validate examples/workflows/http-connector.workflow.json --format json
PYTHONPATH=src python3 -m skill2workflow.cli visualize examples/workflows/http-connector.workflow.json -o /tmp/http-connector.litegraph.json
```

For trigger, schedule, connector, or control-plane changes, also run:

```bash
python3 scripts/schedule_smoke.py --work-dir /tmp/skill2workflow-schedule-loop29
```

For recurring schedule or service coordination changes, also run:

```bash
python3 scripts/recurring_scheduler_smoke.py --work-dir /tmp/skill2workflow-recurring-scheduler-loop43
```

For backup, restore, SQLite state layout, or disaster-recovery changes, also run:

```bash
python3 scripts/backup_restore_smoke.py --work-dir /tmp/skill2workflow-backup-restore-loop44
```

For state upgrade or migration changes, also run:

```bash
python3 scripts/state_upgrade_smoke.py --work-dir /tmp/skill2workflow-state-upgrade-loop45
```

For metrics or operational log changes, also run:

```bash
python3 scripts/observability_smoke.py --work-dir /tmp/skill2workflow-observability-loop46
```

For retention or disposal changes, also run:

```bash
python3 scripts/retention_smoke.py --work-dir /tmp/skill2workflow-retention-loop47
```

For cancellation behavior or service concurrency changes, also run:

```bash
python3 scripts/cancellation_smoke.py --work-dir /tmp/skill2workflow-cancellation-loop48
```

For interrupted-run recovery or execution fencing changes, also run:

```bash
python3 scripts/interrupted_recovery_smoke.py --work-dir /tmp/skill2workflow-interrupted-loop49
```

For release PRs, run the release preflight with the target version and notes:

```bash
PYTHONPATH=src python3 scripts/release_preflight.py --version <version> --notes docs/releases/v<version>.md --dry-run
```

Before that command, move the finalized entries from `Unreleased` into the
matching dated version heading in `CHANGELOG.md`. A version bump remains a
separate maintainer decision.

For docs-only changes, the full test suite should still pass unless the PR description explains why local verification was not possible.

PR descriptions should include:

- What changed
- Why it changed
- User or contributor impact
- Validation commands and results
- Any compatibility or migration notes

## Issue Reports

Use the GitHub issue templates for:

- Bugs
- Feature requests
- Real-world workflow examples

Workflow examples are especially useful when they expose where standard Agent skills need stronger execution control.
