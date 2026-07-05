# Trigger And Local Run API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a controlled local trigger boundary that starts published workflow runs without bypassing version binding, validation, storage, or audit.

**Architecture:** Introduce a small dependency-free trigger envelope module and a control-plane helper that delegates to the existing `run_published_workflow` path. The trigger API returns structured trigger/run identity and annotates `run_started` audit events with trigger metadata; it does not implement webhook hosting, queues, auth, secret injection, or run input context semantics.

**Tech Stack:** Python 3.9 standard library, `unittest`, existing JSON/SQLite storage.

---

### Task 1: Trigger Envelope Contract

**Files:**
- Create: `tests/test_triggers.py`
- Create: `src/skill2workflow/triggers.py`

- [x] **Step 1: Write failing trigger envelope tests**

Add tests for:

```python
normalized = normalize_trigger_request(
    {
        "workflow_id": "workflow_control",
        "version": "1.0.0",
        "source": "local-test",
        "idempotency_key": "demo-1",
        "input": {"customer_id": "customer_123", "priority": "high"},
    }
)
self.assertTrue(normalized["trigger_id"].startswith("trigger_"))
self.assertEqual(normalized["input_keys"], ["customer_id", "priority"])
```

and invalid envelopes:

```python
with self.assertRaisesRegex(ValueError, "workflow_id is required"):
    normalize_trigger_request({"version": "1.0.0"})
with self.assertRaisesRegex(ValueError, "trigger input must be a JSON object"):
    normalize_trigger_request({"workflow_id": "workflow_control", "version": "1.0.0", "input": []})
```

- [x] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_triggers -v
```

Expected: fail because `skill2workflow.triggers` does not exist yet.

- [x] **Step 3: Implement trigger envelope helpers**

Create `src/skill2workflow/triggers.py` with:

```python
def normalize_trigger_request(request):
    ...

def trigger_audit_fields(trigger):
    ...

def trigger_response(trigger, state):
    ...
```

The helper should validate required `workflow_id` and `version`, accept optional `source`, `idempotency_key`, and JSON-object `input`, generate `trigger_id`, and expose only `input_keys` instead of persisting full input payload.

- [x] **Step 4: Run focused trigger tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_triggers -v
```

Expected: pass.

### Task 2: Control-Plane Trigger Helper

**Files:**
- Modify: `tests/test_control_plane.py`
- Modify: `src/skill2workflow/control_plane.py`

- [x] **Step 1: Write failing control-plane trigger tests**

Add a test that publishes a workflow, calls:

```python
result = control.trigger_workflow(
    {
        "workflow_id": "workflow_control",
        "version": "10.0.0",
        "source": "local-test",
        "idempotency_key": "demo-1",
        "input": {"customer_id": "customer_123"},
    }
)
```

Assert:

```python
self.assertEqual(result["workflow_id"], "workflow_control")
self.assertEqual(result["workflow_version"], "10.0.0")
self.assertEqual(result["run_status"], "completed")
self.assertEqual(result["input_keys"], ["customer_id"])
```

and `run_started` / `run_completed` audit events are present, with `run_started.trigger_id` matching the result.

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_control_plane.ControlPlaneTests.test_trigger_workflow_starts_published_run_with_trigger_metadata -v
```

Expected: fail because `LocalControlPlane.trigger_workflow` does not exist yet.

- [x] **Step 3: Implement control-plane helper**

Update `LocalControlPlane` to:

- accept optional trigger metadata in `run_published_workflow`
- add trigger fields to the `run_started` audit event only when provided
- expose `trigger_workflow(request)` that normalizes the request, delegates to `run_published_workflow`, and returns a compact trigger response

- [x] **Step 4: Run focused control-plane tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_control_plane -v
```

Expected: pass.

### Task 3: CLI Trigger Command

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `src/skill2workflow/cli.py`

- [x] **Step 1: Write failing CLI test**

Add a test that publishes a workflow, writes an input JSON object, runs:

```bash
skill2workflow trigger workflow_demo --version 0.1.0 --state-dir <state> --source local-cli --idempotency-key demo-1 --input <input.json>
```

Assert the JSON output contains `trigger_id`, `run_id`, `run_status`, and `input_keys`, and the control-plane audit has `run_started` and `run_completed`.

- [x] **Step 2: Run CLI test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_cli.CliTests.test_trigger_command_starts_published_workflow_with_input_metadata -v
```

Expected: fail because the `trigger` subcommand does not exist yet.

- [x] **Step 3: Implement CLI command**

Add `trigger` with arguments:

```text
workflow_id
--version <version>
--state-dir <path>
--storage json|sqlite
--source <source>
--idempotency-key <key>
--input <json-object-file>
```

The command should print the compact trigger response and return `1` with a clear error for invalid envelopes or input JSON shape.

- [x] **Step 4: Run focused CLI tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_cli -v
```

Expected: pass.

### Task 4: Docs And Roadmap

**Files:**
- Create: `docs/triggers.md`
- Modify: `README.md`
- Modify: `HARNESS.md`
- Modify: `AGENTS.md`
- Modify: `ROADMAP.md`
- Modify: `docs/stability.md`

- [x] **Step 1: Document local trigger boundary**

Create `docs/triggers.md` explaining:

- the trigger request envelope
- the compact trigger response
- CLI usage
- audit fields added to `run_started`
- current non-goals: webhook hosting, queues, auth, RBAC, secret injection, idempotency enforcement, and run input execution context

- [x] **Step 2: Update project entry docs**

Update README, HARNESS, AGENTS, and stability docs with the new trigger command and boundary.

- [x] **Step 3: Advance Roadmap**

Mark Loop 23 complete and set Loop 24 `Workflow Inputs And Run Context` as next. Keep Loop 24 scoped to carrying trigger input metadata into run state and node execution context.

### Task 5: Verification And PR

**Files:**
- Modify: `docs/superpowers/plans/2026-07-05-trigger-local-run-api.md`

- [x] **Step 1: Run final verification**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/demo_bootstrap.py --work-dir /tmp/skill2workflow-demo-loop23
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

Expected: all pass.

- [x] **Step 2: Commit, push, and open draft PR**

Use:

```bash
git add .
git commit -m "feat: add local trigger run api"
git push -u origin loop-23-trigger-local-run-api
gh pr create --draft --title "feat: add local trigger run api" --body-file /tmp/skill2workflow-loop23-pr.md
```
