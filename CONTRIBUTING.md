# Contributing to skill2workflow

Thank you for helping improve `skill2workflow`. The project is currently at
Self-hosted Beta maturity, so the most valuable contributions are scoped,
runnable, and easy to verify without overstating the production boundary.

## Project Direction

`skill2workflow` converts standard Agent `SKILL.md` files into controlled workflows that can be validated, visualized, executed, resumed, and audited.

The Workflow DSL is the execution truth source. LiteGraph JSON and the web editor are views and authoring surfaces; they must round-trip through Workflow DSL before execution or publication.

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

CI repeats the full release-relevant checks on Python 3.9 and 3.14, covering
the supported floor and the current stable interpreter. Contributors may use
any supported Python locally; compatibility-sensitive changes should be
reviewed against both matrix endpoints.

Optionally install the checkout in editable mode to use the `skill2workflow` console script:

```bash
python3 -m venv /tmp/skill2workflow-venv
/tmp/skill2workflow-venv/bin/python -m pip install --upgrade pip "setuptools>=77.0.1"
/tmp/skill2workflow-venv/bin/python -m pip install --no-build-isolation -e .
/tmp/skill2workflow-venv/bin/skill2workflow --help
```

You can also run the package smoke helper, which builds a wheel, installs it
into a separate temporary virtual environment, and validates the installed
console script outside the checkout with source-import paths disabled:

```bash
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke
```

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

Before changing behavior, read:

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
