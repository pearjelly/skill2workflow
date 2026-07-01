# Agent Notes

This repository is the `skill2workflow` open-source harness.

## Project Direction

- Product goal: compile standard Agent `SKILL.md` files into controlled, durable enterprise workflows.
- Execution truth source: Workflow DSL, not the visual graph.
- Current implementation language: Python 3.9 standard library for the bootstrap harness.
- Long-term UI direction: LiteGraph-style visual editor, aligned with the approved spec.

## Local Commands

- Tests: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- Parse: `PYTHONPATH=src python3 -m skill2workflow.cli parse examples/skills/approval-flow/SKILL.md`
- Compile: `PYTHONPATH=src python3 -m skill2workflow.cli compile examples/skills/approval-flow/SKILL.md -o /tmp/skill2workflow-workflow.json`
- Validate: `PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json`

## Working Rules

- Keep changes scoped to the current closed loop.
- Add tests before changing parser, compiler, executor, or CLI behavior.
- Avoid adding runtime dependencies unless they directly support a spec-backed capability.
- Preserve the approved design spec and update it only when product direction changes.

