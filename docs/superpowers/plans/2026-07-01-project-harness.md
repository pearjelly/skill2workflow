# skill2workflow Project Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first open-source project harness for `skill2workflow`: a tested CLI that parses `SKILL.md`, compiles Workflow DSL, runs a durable local workflow, and prepares the repository for GitHub publication.

**Architecture:** Use a dependency-light Python implementation for the first executable harness because this machine does not currently have Node.js or npm. Keep the design aligned with the TypeScript/LiteGraph long-term spec by separating parser, compiler, executor, CLI, examples, and docs.

**Tech Stack:** Python 3.9 standard library, `unittest`, JSON files for local run persistence, Git for repository initialization.

---

## File Structure

- Create `pyproject.toml`: Python package metadata and CLI entry point.
- Create `README.md`: open-source project narrative, quickstart, architecture, roadmap.
- Create `LICENSE`: Apache-2.0 license.
- Create `.gitignore`: Python, editor, build, and local run state ignores.
- Create `AGENTS.md`: project conventions for future agent work.
- Create `src/skill2workflow/__init__.py`: package exports and version.
- Create `src/skill2workflow/parser.py`: parse standard `SKILL.md` into Skill IR.
- Create `src/skill2workflow/compiler.py`: compile Skill IR into Workflow DSL and validate DSL.
- Create `src/skill2workflow/executor.py`: durable local executor with run/resume/list.
- Create `src/skill2workflow/cli.py`: `parse`, `compile`, `validate`, `run`, `resume`, `runs` commands.
- Create `examples/skills/approval-flow/SKILL.md`: sample Skill with hard gate, checklist, and user approval.
- Create `tests/test_parser.py`: parser behavior tests.
- Create `tests/test_compiler.py`: compiler and validator behavior tests.
- Create `tests/test_executor.py`: durable execution and human gate resume tests.
- Create `.github/workflows/ci.yml`: GitHub Actions test workflow.
- Preserve `docs/superpowers/specs/2026-07-01-skill2workflow-design.md`: approved product spec.

## Task 1: Parser Red-Green

**Files:**
- Create: `tests/test_parser.py`
- Create: `src/skill2workflow/parser.py`
- Create: `src/skill2workflow/__init__.py`

- [ ] **Step 1: Write the failing parser test**

```python
from pathlib import Path
from textwrap import dedent
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.parser import parse_skill_file


class ParserTests(TestCase):
    def test_parse_standard_skill_into_ir(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text(dedent("""\
                ---
                name: approval-flow
                description: Convert approval work into a controlled workflow.
                ---

                <HARD-GATE>
                Do NOT publish until the user approves the draft.
                </HARD-GATE>

                ## Checklist

                1. Explore project context
                2. Draft workflow
                3. Ask user for approval
                4. Publish workflow
                """), encoding="utf-8")

            ir = parse_skill_file(path)

        self.assertEqual(ir["metadata"]["name"], "approval-flow")
        self.assertEqual(ir["metadata"]["description"], "Convert approval work into a controlled workflow.")
        self.assertEqual(ir["hard_gates"], ["Do NOT publish until the user approves the draft."])
        self.assertEqual(ir["ordered_steps"], [
            "Explore project context",
            "Draft workflow",
            "Ask user for approval",
            "Publish workflow",
        ])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests.test_parser -v`

Expected: FAIL because `skill2workflow.parser` does not exist.

- [ ] **Step 3: Implement the minimal parser**

Implement `parse_skill_file(path)` with standard-library parsing for frontmatter, hard gate blocks, and checklist items.

- [ ] **Step 4: Run parser test to verify it passes**

Run: `PYTHONPATH=src python3 -m unittest tests.test_parser -v`

Expected: PASS.

## Task 2: Compiler Red-Green

**Files:**
- Create: `tests/test_compiler.py`
- Create: `src/skill2workflow/compiler.py`

- [ ] **Step 1: Write the failing compiler test**

```python
from unittest import TestCase

from skill2workflow.compiler import compile_ir_to_workflow, validate_workflow


class CompilerTests(TestCase):
    def test_compile_ordered_steps_to_valid_workflow(self):
        ir = {
            "metadata": {"name": "approval-flow", "description": "Approval workflow"},
            "hard_gates": ["Do NOT publish until the user approves the draft."],
            "ordered_steps": ["Explore", "Ask user for approval", "Publish"],
            "tool_hints": [],
            "human_gates": [],
            "verification_rules": [],
            "source_path": "SKILL.md",
        }

        workflow = compile_ir_to_workflow(ir)
        errors = validate_workflow(workflow)

        self.assertEqual(errors, [])
        self.assertEqual(workflow["entry"], "start")
        self.assertIn("node_002_ask_user_for_approval", {node["id"] for node in workflow["nodes"]})
        human_node = next(node for node in workflow["nodes"] if node["id"] == "node_002_ask_user_for_approval")
        self.assertEqual(human_node["type"], "human_gate")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests.test_compiler -v`

Expected: FAIL because `skill2workflow.compiler` does not exist.

- [ ] **Step 3: Implement the minimal compiler and validator**

Implement `compile_ir_to_workflow(ir)` and `validate_workflow(workflow)` with start/end/failure nodes, ordered edges, and human-gate step detection.

- [ ] **Step 4: Run compiler test to verify it passes**

Run: `PYTHONPATH=src python3 -m unittest tests.test_compiler -v`

Expected: PASS.

## Task 3: Executor Red-Green

**Files:**
- Create: `tests/test_executor.py`
- Create: `src/skill2workflow/executor.py`

- [ ] **Step 1: Write the failing executor test**

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.executor import LocalExecutor


class ExecutorTests(TestCase):
    def test_run_pauses_at_human_gate_and_resume_completes(self):
        workflow = {
            "schema_version": "0.1.0",
            "workflow": {"id": "workflow_approval", "name": "approval", "version": "0.1.0", "status": "published"},
            "entry": "start",
            "nodes": [
                {"id": "start", "type": "start", "title": "Start", "on_success": "review"},
                {"id": "review", "type": "human_gate", "title": "Review", "on_success": "end", "on_failure": "failure"},
                {"id": "failure", "type": "failure", "title": "Failure"},
                {"id": "end", "type": "end", "title": "End"},
            ],
            "edges": [],
        }

        with TemporaryDirectory() as tmp:
            executor = LocalExecutor(Path(tmp))
            waiting = executor.run(workflow)
            self.assertEqual(waiting["status"], "waiting")
            self.assertEqual(waiting["current_node"], "review")

            completed = executor.resume(waiting["run_id"], approved=True)

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["current_node"], "end")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests.test_executor -v`

Expected: FAIL because `skill2workflow.executor` does not exist.

- [ ] **Step 3: Implement the minimal durable executor**

Implement `LocalExecutor.run(workflow)`, `LocalExecutor.resume(run_id, approved=True)`, and JSON persistence under a run directory.

- [ ] **Step 4: Run executor test to verify it passes**

Run: `PYTHONPATH=src python3 -m unittest tests.test_executor -v`

Expected: PASS.

## Task 4: CLI and Project Harness

**Files:**
- Create: `src/skill2workflow/cli.py`
- Create: `pyproject.toml`
- Create: `examples/skills/approval-flow/SKILL.md`
- Create: `README.md`
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `.github/workflows/ci.yml`
- Create: `AGENTS.md`

- [ ] **Step 1: Add CLI smoke tests through manual commands**

Run after implementation:

```bash
PYTHONPATH=src python3 -m skill2workflow.cli parse examples/skills/approval-flow/SKILL.md
PYTHONPATH=src python3 -m skill2workflow.cli compile examples/skills/approval-flow/SKILL.md -o /tmp/skill2workflow-workflow.json
PYTHONPATH=src python3 -m skill2workflow.cli validate /tmp/skill2workflow-workflow.json
PYTHONPATH=src python3 -m skill2workflow.cli run /tmp/skill2workflow-workflow.json --state-dir /tmp/skill2workflow-state
```

Expected: parse and compile output JSON, validate prints `valid`, run pauses at the approval human gate.

- [ ] **Step 2: Add open-source project metadata**

Add README, Apache-2.0 license, pyproject metadata, CI workflow, .gitignore, and contributor-facing AGENTS.md.

- [ ] **Step 3: Run all tests**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`

Expected: PASS.

## Task 5: Git and GitHub Publication

**Files:**
- Modify: repository metadata only.

- [ ] **Step 1: Initialize local git repository**

Run:

```bash
git init
git add .
git commit -m "feat: bootstrap skill2workflow harness"
```

Expected: local `main` branch has the initial open-source project commit.

- [ ] **Step 2: Attempt GitHub publication**

If `gh` is installed and authenticated, run:

```bash
gh repo create skill2workflow --public --source . --remote origin --push
```

Expected: public GitHub repository is created and local `main` is pushed.

If `gh` is unavailable, stop after the local commit and ask for either an existing GitHub remote URL or an authenticated `gh` installation.

