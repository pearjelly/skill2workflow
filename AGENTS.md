# Agent Notes

This repository is the `skill2workflow` open-source harness.

## Project Direction

- Product goal: compile standard Agent `SKILL.md` files into controlled, durable enterprise workflows.
- Execution truth source: Workflow DSL, not the visual graph.
- Current implementation language: Python 3.9 standard library for the bootstrap harness.
- Long-term UI direction: LiteGraph-style visual editor, aligned with the approved spec.
- Roadmap index: `ROADMAP.md`; approved product spec remains under `docs/superpowers/specs/`.

## Local Commands

- Tests: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- Parse: `PYTHONPATH=src python3 -m skill2workflow.cli parse examples/skills/approval-flow/SKILL.md`
- Compile: `PYTHONPATH=src python3 -m skill2workflow.cli compile examples/skills/approval-flow/SKILL.md -o /tmp/skill2workflow-workflow.json`
- Validate: `PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json`
- Structured validate: `PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json --format json`
- Visualize: `PYTHONPATH=src python3 -m skill2workflow.cli visualize /tmp/skill2workflow-workflow.json -o /tmp/skill2workflow-litegraph.json`
- Write-back: `PYTHONPATH=src python3 -m skill2workflow.cli write-back /tmp/skill2workflow-workflow.json /tmp/skill2workflow-litegraph.json -o /tmp/skill2workflow-edited-workflow.json`
- Web preview: `python3 -m http.server 4173`, then open `http://localhost:4173/web/`
- Publish: `PYTHONPATH=src python3 -m skill2workflow.cli publish /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-control`
- Run published: `PYTHONPATH=src python3 -m skill2workflow.cli run-published workflow_approval_flow --version 0.1.0 --state-dir /tmp/skill2workflow-control`
- Audit: `PYTHONPATH=src python3 -m skill2workflow.cli audit --state-dir /tmp/skill2workflow-control`

## Working Rules

- Keep changes scoped to the current closed loop.
- Add tests before changing parser, compiler, executor, or CLI behavior.
- Avoid adding runtime dependencies unless they directly support a spec-backed capability.
- Preserve the approved design spec and update it only when product direction changes.
