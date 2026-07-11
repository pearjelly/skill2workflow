# Lark Task Pilot Scenario Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Loop 37 by running the Lark/Feishu task dry-run connector inside a sales renewal risk pilot workflow.

**Architecture:** The pilot helper publishes a generated Workflow DSL through the existing local control plane, starts it through the local webhook trigger boundary, pauses at a manual control gate, resumes the run, and then invokes the explicitly loaded `lark_task` connector package. The helper writes workflow, trigger, run, audit, connectors, snapshot, and LiteGraph overlay artifacts under a caller-provided work directory.

**Tech Stack:** Python 3.9 standard library, existing `LocalControlPlane`, `handle_webhook_request`, `ConnectorRuntime`, `load_external_connector`, `workflow_to_litegraph`, and `unittest`.

## Global Constraints

- Workflow DSL remains the execution source of truth.
- The Lark/Feishu task connector stays outside the built-in connector registry.
- Loop 37 uses `operation: create_task` with `mode: dry_run` only.
- No live Lark API call, OAuth, hosted callback, automatic discovery, marketplace behavior, queue, production scheduler, or token refresh.
- Credential values must remain outside Workflow DSL, connector output, connector audit metadata, committed fixtures, and smoke summaries.
- Trigger input may persist in run context by existing trigger design, but raw mapped task values must not be duplicated into connector output or audit metadata.

---

### Task 1: Sales Renewal Lark Task Pilot Smoke

**Files:**
- Create: `tests/test_lark_task_pilot.py`
- Create: `src/skill2workflow/lark_task_pilot.py`
- Create: `scripts/lark_task_pilot_smoke.py`

**Interfaces:**
- Consumes: `load_external_connector(path)`, `ConnectorRuntime([external_connector])`, `LocalControlPlane`, `handle_webhook_request`, `workflow_to_litegraph`
- Produces: `run_lark_task_pilot(repo_root: Path, work_dir: Path, reset: bool = True) -> Dict[str, object]`

- [x] **Step 1: Write failing pilot smoke test**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_task_pilot -v
```

Expected: fail because `skill2workflow.lark_task_pilot` does not exist.

- [x] **Step 2: Implement pilot helper and CLI wrapper**

Create `run_lark_task_pilot(...)` and `scripts/lark_task_pilot_smoke.py`. The helper must explicitly load `examples/connectors/lark_task_connector.py`, publish `workflow_lark_task_pilot`, trigger it through `/webhooks/workflow_lark_task_pilot/0.1.0`, resume the manual gate, write artifacts, and return a compact summary.

- [x] **Step 3: Verify focused pilot test and CLI smoke**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_task_pilot -v
python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot
```

Expected: pass.

### Task 2: Documentation And Roadmap

**Files:**
- Modify: `docs/examples.md`
- Modify: `docs/connectors.md`
- Modify: `ROADMAP.md`
- Modify: `tests/test_product_connector_pilot_roadmap.py`

**Interfaces:**
- Consumes: `scripts/lark_task_pilot_smoke.py`
- Produces: documented Loop 37 smoke command and roadmap transition to Loop 38 candidate work

- [x] **Step 1: Update docs**

Document the sales renewal risk pilot smoke in `docs/examples.md` and reference it from the Lark/Feishu connector docs. Keep live API and hosted integration behavior out of scope.

- [x] **Step 2: Advance Roadmap**

Move Loop 37 to complete, set Loop 38 as next, and keep live connector work behind a readiness review rather than implementation.

- [x] **Step 3: Verify docs contracts**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_product_connector_pilot_roadmap -v
```

Expected: pass.

### Task 3: Full Verification And PR

**Files:**
- Modify: `docs/superpowers/plans/2026-07-09-lark-task-pilot-scenario.md`

**Interfaces:**
- Consumes: Task 1 and Task 2 implementation
- Produces: draft PR for Loop 37

- [x] **Step 1: Run full verification**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

Expected: all commands exit 0.

- [x] **Step 2: Commit and open draft PR**

Run:

```bash
git add ROADMAP.md docs/connectors.md docs/examples.md docs/superpowers/plans/2026-07-09-lark-task-pilot-scenario.md scripts/lark_task_pilot_smoke.py src/skill2workflow/lark_task_pilot.py tests/test_lark_task_pilot.py tests/test_product_connector_pilot_roadmap.py
git commit -m "feat: add lark task pilot scenario"
git push -u origin loop-37-lark-task-pilot
```
