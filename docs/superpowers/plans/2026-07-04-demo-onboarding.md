# Demo And Contributor Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one deterministic local demo command that generates onboarding artifacts from committed examples.

**Architecture:** Keep the demo as a thin standard-library helper over existing parser, compiler, visualizer, control-plane, executor, and dashboard APIs. The helper writes artifacts under a caller-provided work directory and does not mutate repository files.

**Tech Stack:** Python 3.9 standard library, `unittest`, existing `skill2workflow` package modules.

---

### Task 1: Demo Helper API

**Files:**
- Create: `tests/test_demo.py`
- Create: `src/skill2workflow/demo.py`
- Create: `scripts/demo_bootstrap.py`

- [x] **Step 1: Write the failing test**

Add `tests/test_demo.py` to assert that `run_demo_bootstrap()` generates workflow, LiteGraph, and control-plane snapshot artifacts from `examples/skills/approval-flow/SKILL.md`.

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_demo -v
```

Expected: fail because `skill2workflow.demo` does not exist.

- [x] **Step 3: Implement minimal demo helper**

Add `src/skill2workflow/demo.py` with `run_demo_bootstrap(repo_root, work_dir, reset=True)` and a `main()` entry point. Add `scripts/demo_bootstrap.py` as a checkout-friendly wrapper.

- [x] **Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_demo -v
```

Expected: pass.

### Task 2: Contributor Docs

**Files:**
- Modify: `README.md`
- Modify: `HARNESS.md`
- Modify: `AGENTS.md`

- [x] **Step 1: Add first-run demo instructions**

Document:

```bash
python3 scripts/demo_bootstrap.py --work-dir /tmp/skill2workflow-demo
python3 -m http.server 4173
```

Then open:

```text
http://localhost:4173/web/control.html
```

- [x] **Step 2: Add reset and artifact notes**

Document that rerunning the helper resets the work directory by default and writes artifacts under `<work-dir>/artifacts/`.

### Task 3: Roadmap And Verification

**Files:**
- Modify: `ROADMAP.md`

- [x] **Step 1: Mark Loop 19 complete**

Move Loop 19 to completed loops and set Loop 20 to the next small closed loop.

- [x] **Step 2: Run final verification**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/demo_bootstrap.py --work-dir /tmp/skill2workflow-demo-loop19
python3 -m json.tool /tmp/skill2workflow-demo-loop19/artifacts/control-plane-snapshot.json >/tmp/skill2workflow-demo-loop19-snapshot-check.json
git diff --check
```

Expected: all pass.
