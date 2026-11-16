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
- Runtime observability guide: `docs/observability.md`.
- Data retention guide: `docs/data-retention.md`.
- Run cancellation guide: `docs/cancellation.md`.
- Compatibility notes: `docs/workflow-dsl-contract.md`, `docs/workflow-dsl-compatibility.md`, and `docs/stability.md`.
- Release process: `docs/release-process.md`.
- Release artifact qualification: `docs/release-artifact-qualification.md`.
- Secure service bootstrap: `docs/service-bootstrap.md`.
- Installed controlled quickstart: `docs/quickstart.md`.
- Operational readiness Doctor: `docs/service-doctor.md`.
- Linux systemd supervision: `docs/systemd-service.md`.
- Linux single-service Docker self-hosting: `docs/docker-self-host.md`.

## Local Commands

- Tests: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- Compile: `PYTHONPATH=src python3 -m skill2workflow.cli compile examples/skills/approval-flow/SKILL.md -o /tmp/skill2workflow-workflow.json`
- Structured validate: `PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json --format json`
- Visualize: `PYTHONPATH=src python3 -m skill2workflow.cli visualize /tmp/skill2workflow-workflow.json -o /tmp/skill2workflow-litegraph.json`
- Write-back: `PYTHONPATH=src python3 -m skill2workflow.cli write-back /tmp/skill2workflow-workflow.json /tmp/skill2workflow-litegraph.json -o /tmp/skill2workflow-edited-workflow.json`
- Installed UI preview: `skill2workflow ui --port 4173`, then open `http://127.0.0.1:4173/web/`; add `--service-url` and `--auth-token-file` only for the fixed read-only live snapshot proxy
- Installed controlled quickstart: `PYTHONPATH=src python3 -m skill2workflow.cli quickstart --root /tmp/skill2workflow-quickstart --port 8080`
- Service Doctor: `PYTHONPATH=src python3 -m skill2workflow.cli service-doctor --config /tmp/skill2workflow-runtime/config/service.json`
- Publish: `PYTHONPATH=src python3 -m skill2workflow.cli publish /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-control`
- Secret hygiene: `python3 scripts/secret_hygiene.py examples/workflows`

The full operation, packaging and smoke command list is in
[the command reference](docs/reference.md#command-reference).

## Working Rules

- Keep changes scoped to the current closed loop.
- Add tests before changing parser, compiler, executor, or CLI behavior.
- Avoid adding runtime dependencies unless they directly support a spec-backed capability.
- Preserve the approved design spec and update it only when product direction changes.
- Keep `CONTRIBUTING.md`, issue templates, release notes, and compatibility docs aligned when public contributor workflows change.
- Keep real secrets out of Workflow DSL and LiteGraph fixtures; use documented placeholders and run `python3 scripts/secret_hygiene.py examples/workflows` for connector/example changes.
