# Agent Notes

This repository is the `skill2workflow` open-source harness.

## Project Direction

- Product goal: compile standard Agent `SKILL.md` files into controlled, durable enterprise workflows.
- Execution truth source: Workflow DSL, not the visual graph.
- Current implementation language: Python 3.9 standard library for the bootstrap harness.
- Long-term UI direction: LiteGraph-style visual editor, aligned with the approved spec.
- Roadmap index: `ROADMAP.md`; approved product spec remains under `docs/superpowers/specs/`.
- Contributor entry point: `CONTRIBUTING.md`.
- Example pack guide: `docs/examples.md`.
- Connector runtime guide: `docs/connectors.md`.
- Credential boundary guide: `docs/credential-boundary.md`.
- Runtime policy guide: `docs/runtime-policy.md`.
- Trigger API guide: `docs/triggers.md`.
- Compatibility notes: `docs/workflow-dsl-contract.md`, `docs/workflow-dsl-compatibility.md`, and `docs/stability.md`.
- Release process: `docs/release-process.md`.

## Local Commands

- Tests: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- Parse: `PYTHONPATH=src python3 -m skill2workflow.cli parse examples/skills/approval-flow/SKILL.md`
- Compile: `PYTHONPATH=src python3 -m skill2workflow.cli compile examples/skills/approval-flow/SKILL.md -o /tmp/skill2workflow-workflow.json`
- Validate: `PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json`
- Structured validate: `PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json --format json`
- Visualize: `PYTHONPATH=src python3 -m skill2workflow.cli visualize /tmp/skill2workflow-workflow.json -o /tmp/skill2workflow-litegraph.json`
- Write-back: `PYTHONPATH=src python3 -m skill2workflow.cli write-back /tmp/skill2workflow-workflow.json /tmp/skill2workflow-litegraph.json -o /tmp/skill2workflow-edited-workflow.json`
- Validate HTTP connector example: `PYTHONPATH=src python3 -m skill2workflow.cli validate examples/workflows/http-connector.workflow.json --format json`
- Visualize HTTP connector example: `PYTHONPATH=src python3 -m skill2workflow.cli visualize examples/workflows/http-connector.workflow.json -o examples/workflows/http-connector.litegraph.json`
- Example fixture sync: `PYTHONPATH=src python3 -m unittest tests.test_examples -v`
- Web preview: `python3 -m http.server 4173`, then open `http://localhost:4173/web/`
- Control UI preview: `python3 -m http.server 4173`, then open `http://localhost:4173/web/control.html`
- Run with SQLite storage: `PYTHONPATH=src python3 -m skill2workflow.cli run /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-sqlite-state --storage sqlite`
- Run with local credential file: `PYTHONPATH=src python3 -m skill2workflow.cli run /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-state --credential-file /tmp/skill2workflow-credentials.json`
- Publish: `PYTHONPATH=src python3 -m skill2workflow.cli publish /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-control`
- Publish with SQLite storage: `PYTHONPATH=src python3 -m skill2workflow.cli publish /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite`
- Run published: `PYTHONPATH=src python3 -m skill2workflow.cli run-published workflow_approval_flow --version 0.1.0 --state-dir /tmp/skill2workflow-control`
- Run published with SQLite storage: `PYTHONPATH=src python3 -m skill2workflow.cli run-published workflow_approval_flow --version 0.1.0 --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite`
- Trigger published: `PYTHONPATH=src python3 -m skill2workflow.cli trigger workflow_approval_flow --version 0.1.0 --state-dir /tmp/skill2workflow-control --source local-cli --idempotency-key example-001 --input /tmp/skill2workflow-trigger-input.json`
- Add schedule: `PYTHONPATH=src python3 -m skill2workflow.cli schedule-add /tmp/skill2workflow-schedule.json --state-dir /tmp/skill2workflow-control`
- List schedules: `PYTHONPATH=src python3 -m skill2workflow.cli schedules --state-dir /tmp/skill2workflow-control`
- Run due schedules: `PYTHONPATH=src python3 -m skill2workflow.cli schedule-run-due --state-dir /tmp/skill2workflow-control --now 2026-07-06T00:00:00Z`
- Local webhook server: `PYTHONPATH=src python3 -m skill2workflow.cli webhook-server --state-dir /tmp/skill2workflow-control --host 127.0.0.1 --port 8080`
- Resume published: `PYTHONPATH=src python3 -m skill2workflow.cli resume-published <run_id> --state-dir /tmp/skill2workflow-control`
- Control runs: `PYTHONPATH=src python3 -m skill2workflow.cli control-runs --state-dir /tmp/skill2workflow-control`
- Control run detail: `PYTHONPATH=src python3 -m skill2workflow.cli control-run <run_id> --state-dir /tmp/skill2workflow-control`
- Audit: `PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control`
- Filter audit: `PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --run-id <run_id> --event-type run_completed`
- Filter connector audit: `PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --run-id <run_id> --event-type connector_completed`
- Filter retry audit: `PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control --event-type node_retrying`
- Audit with SQLite storage: `PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control-sqlite --storage sqlite`
- Connectors: `PYTHONPATH=src python3 -m skill2workflow.cli connectors --state-dir /tmp/skill2workflow-control`
- Control snapshot: `PYTHONPATH=src python3 -m skill2workflow.cli control-snapshot --state-dir /tmp/skill2workflow-control -o /tmp/skill2workflow-control-snapshot.json`
- First-run demo: `python3 scripts/demo_bootstrap.py --work-dir /tmp/skill2workflow-demo`
- Pilot smoke: `python3 scripts/pilot_playbook_smoke.py --work-dir /tmp/skill2workflow-pilot`
- Schedule smoke: `python3 scripts/schedule_smoke.py --work-dir /tmp/skill2workflow-schedule-loop29`
- Package smoke: `python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke`
- Secret hygiene: `python3 scripts/secret_hygiene.py examples/workflows`
- Editable install: `python3 -m venv /tmp/skill2workflow-venv && /tmp/skill2workflow-venv/bin/python -m pip install --upgrade pip "setuptools>=68" && /tmp/skill2workflow-venv/bin/python -m pip install --no-build-isolation -e .`
- Installed CLI smoke: `/tmp/skill2workflow-venv/bin/skill2workflow validate examples/workflows/approval-flow.workflow.json --format json`
- Release preflight dry-run: `PYTHONPATH=src python3 scripts/release_preflight.py --version 0.1.0 --notes docs/releases/v0.1.0.md --dry-run --skip-git`
- Release notes: `docs/releases/v0.1.0.md`

## Working Rules

- Keep changes scoped to the current closed loop.
- Add tests before changing parser, compiler, executor, or CLI behavior.
- Avoid adding runtime dependencies unless they directly support a spec-backed capability.
- Preserve the approved design spec and update it only when product direction changes.
- Keep `CONTRIBUTING.md`, issue templates, release notes, and compatibility docs aligned when public contributor workflows change.
- Keep real secrets out of Workflow DSL and LiteGraph fixtures; use documented placeholders and run `python3 scripts/secret_hygiene.py examples/workflows` for connector/example changes.
