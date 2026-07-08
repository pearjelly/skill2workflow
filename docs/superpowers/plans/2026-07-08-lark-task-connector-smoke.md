# Lark Task Connector Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the selected Lark/Feishu task connector as an explicitly loaded dry-run package with a deterministic local smoke.

**Architecture:** The connector lives under `examples/connectors/` and is loaded explicitly with `load_external_connector(...)`. A smoke helper under `src/skill2workflow/` publishes and triggers a generated workflow through the existing control plane, while a thin `scripts/` wrapper exposes the CLI. Core runtime changes are limited to promoting connector-provided compact audit metadata under a nested `connector_metadata` key.

**Tech Stack:** Python 3.9 standard library, existing connector runtime, existing control plane, unittest.

## Global Constraints

- Workflow DSL remains the execution source of truth.
- The Lark/Feishu task connector must stay outside the built-in connector registry.
- Loop 36 supports `operation: create_task` with `mode: dry_run` only.
- No live Lark API call, OAuth, hosted callback, automatic discovery, marketplace behavior, queue, or production scheduler.
- Credential values must remain outside Workflow DSL, connector output, run connector summaries, audit metadata, committed fixtures, and smoke summaries.
- Trigger input may persist in run context by existing trigger design, but raw mapped values must not be duplicated into connector output or audit metadata.

---

### Task 1: Connector Package Contract

**Files:**
- Create: `tests/test_lark_task_connector.py`
- Create: `examples/connectors/lark_task_connector.py`
- Modify: `src/skill2workflow/connectors.py`
- Modify: `src/skill2workflow/executor.py`
- Modify: `src/skill2workflow/control_plane.py`

**Interfaces:**
- Consumes: `load_external_connector(path)`, `ConnectorRuntime([external_connector])`, `StaticCredentialProvider`
- Produces: `examples/connectors/lark_task_connector.py:MANIFEST`, `examples/connectors/lark_task_connector.py:execute`

- [x] **Step 1: Write failing connector tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_task_connector -v
```

Expected: fail because `examples/connectors/lark_task_connector.py` does not exist.

- [x] **Step 2: Implement compact audit metadata support**

Allow external connector results to carry an `audit` object. Normalize it to compact scalar/list metadata, persist it in node results, emit it on connector runtime events as `connector_metadata`, and promote it into control-plane audit events.

- [x] **Step 3: Implement Lark task dry-run connector**

Create `MANIFEST` and `execute(binding, credential_provider=None, context=None)`. Validate `operation == "create_task"`, `mode == "dry_run"`, map allowed task fields from `/input/...` into `/body/...`, resolve `lark_bot_access_token`, and return compact metadata only.

- [x] **Step 4: Verify connector tests pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_task_connector -v
```

Expected: pass.

### Task 2: Smoke Helper And Docs

**Files:**
- Create: `src/skill2workflow/lark_task_connector_smoke.py`
- Create: `scripts/lark_task_connector_smoke.py`
- Create: `tests/test_lark_task_connector_smoke.py`
- Modify: `docs/connectors.md`
- Modify: `docs/examples.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Consumes: `examples/connectors/lark_task_connector.py`
- Produces: `run_lark_task_connector_smoke(repo_root, work_dir, reset=True)`

- [x] **Step 1: Write failing smoke test**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_task_connector_smoke -v
```

Expected: fail because `skill2workflow.lark_task_connector_smoke` does not exist.

- [x] **Step 2: Implement smoke helper and CLI wrapper**

Create the module and script that load the connector, publish a generated workflow, trigger it with non-secret task input, resolve a temporary local credential handle, write artifacts, and return a compact JSON summary.

- [x] **Step 3: Update docs and roadmap**

Document the Lark/Feishu task dry-run connector in `docs/connectors.md` and `docs/examples.md`. Move Loop 36 to complete and set Loop 37 as next.

- [x] **Step 4: Verify focused tests and smoke**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_task_connector tests.test_lark_task_connector_smoke -v
python3 scripts/lark_task_connector_smoke.py --work-dir /tmp/skill2workflow-lark-task-connector
```

Expected: pass.

### Task 3: Full Verification And PR

**Files:**
- Modify: `docs/superpowers/plans/2026-07-08-lark-task-connector-smoke.md`

**Interfaces:**
- Consumes: Task 1 and Task 2 implementation
- Produces: draft PR for Loop 36

- [x] **Step 1: Run full verification**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

Expected: all commands exit 0.

- [x] **Step 2: Commit and open draft PR**

Run:

```bash
git add ROADMAP.md docs/connectors.md docs/examples.md docs/superpowers/plans/2026-07-08-lark-task-connector-smoke.md examples/connectors/lark_task_connector.py scripts/lark_task_connector_smoke.py src/skill2workflow/connectors.py src/skill2workflow/control_plane.py src/skill2workflow/executor.py src/skill2workflow/lark_task_connector_smoke.py tests/test_lark_task_connector.py tests/test_lark_task_connector_smoke.py
git commit -m "feat: add lark task connector smoke"
git push -u origin loop-36-lark-task-connector-smoke
```
