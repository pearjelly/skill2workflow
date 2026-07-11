# Workflow Inputs And Run Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist trigger input values into durable run state and expose them through a constrained executor run context without changing Workflow DSL `0.1.0`.

**Architecture:** Keep Workflow DSL as the runtime authority. Trigger envelopes normalize and retain JSON-object input values for run context, while audit events and trigger responses continue to expose only compact metadata such as trigger id, source, idempotency key, and input keys. The executor accepts an optional initial context and persists it with the run state.

**Tech Stack:** Python 3.9 standard library, `unittest`, existing JSON/SQLite storage.

---

### Task 1: Trigger Input Context Contract

**Files:**
- Modify: `tests/test_triggers.py`
- Modify: `src/skill2workflow/triggers.py`

- [x] **Step 1: Write failing trigger-context tests**

Add tests that prove `normalize_trigger_request` retains input values and a helper builds run context:

```python
trigger = normalize_trigger_request(
    {
        "workflow_id": "workflow_control",
        "version": "1.0.0",
        "source": "local-test",
        "idempotency_key": "demo-1",
        "input": {"customer_id": "customer_123", "priority": "high"},
    }
)
context = trigger_run_context(trigger)
self.assertEqual(context["input"]["customer_id"], "customer_123")
self.assertEqual(context["trigger"]["input_keys"], ["customer_id", "priority"])
```

Also assert `trigger_audit_fields(trigger)` and `trigger_response(trigger, state)` do not include full `input` values.

- [x] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_triggers -v
```

Expected: fail because full input values and `trigger_run_context` are not implemented yet.

- [x] **Step 3: Implement trigger run-context helper**

Update `src/skill2workflow/triggers.py` so normalized triggers retain a copy of `input` and expose:

```python
def trigger_run_context(trigger):
    ...
```

The helper should return:

```json
{
  "trigger": {
    "trigger_id": "...",
    "source": "local-cli",
    "idempotency_key": "example-001",
    "input_keys": ["customer_id"]
  },
  "input": {
    "customer_id": "customer_123"
  }
}
```

Audit fields and trigger responses must remain compact and must not include full input values.

### Task 2: Executor Context Persistence

**Files:**
- Modify: `tests/test_executor.py`
- Modify: `src/skill2workflow/executor.py`

- [x] **Step 1: Write failing executor context test**

Add a test that calls:

```python
state = LocalExecutor(Path(tmp)).run(
    workflow,
    context={"input": {"customer_id": "customer_123"}},
)
self.assertEqual(state["context"]["input"]["customer_id"], "customer_123")
```

Then reload the run through `get_run` and assert the same context is durable.

- [x] **Step 2: Implement optional executor context**

Update `LocalExecutor.run(workflow, context=None)` to deep-copy JSON-like context into run state before execution starts. Existing callers without context should still get an empty context.

### Task 3: Control Plane And CLI Coverage

**Files:**
- Modify: `tests/test_control_plane.py`
- Modify: `tests/test_cli.py`
- Modify: `src/skill2workflow/control_plane.py`

- [x] **Step 1: Write failing control-plane test**

Extend the trigger workflow test to fetch the run detail and assert:

```python
detail = control.get_run(result["run_id"])
self.assertEqual(detail["context"]["input"]["customer_id"], "customer_123")
self.assertEqual(detail["context"]["trigger"]["trigger_id"], result["trigger_id"])
```

Also assert `run_started` audit has `input_keys` but not full `input`.

- [x] **Step 2: Write failing CLI test**

Extend the trigger CLI test to inspect `control-run <run_id>` and assert the persisted context carries the trigger input values.

- [x] **Step 3: Bridge trigger context into published runs**

Update `LocalControlPlane.run_published_workflow(..., trigger=None)` to pass `trigger_run_context(trigger)` into `LocalExecutor.run(...)` only for triggered runs.

### Task 4: Docs And Roadmap

**Files:**
- Modify: `docs/triggers.md`
- Modify: `README.md`
- Modify: `HARNESS.md`
- Modify: `AGENTS.md`
- Modify: `ROADMAP.md`
- Modify: `docs/stability.md`

- [x] **Step 1: Document run input semantics**

Document that trigger input values are stored under `run_state.context.input`, while trigger metadata lives under `run_state.context.trigger`.

- [x] **Step 2: Document audit boundary**

Clarify that audit events and trigger responses expose only compact trigger metadata and input keys by default.

- [x] **Step 3: Advance Roadmap**

Mark Loop 24 complete, move active priority to Loop 25, and update the real pilot readiness section.

### Task 5: Verification And PR

**Files:**
- All changed files

- [x] **Step 1: Run focused tests**

```bash
PYTHONPATH=src python3 -m unittest tests.test_triggers tests.test_executor tests.test_control_plane tests.test_cli -v
```

- [x] **Step 2: Run full verification**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/demo_bootstrap.py --work-dir /tmp/skill2workflow-demo-loop24
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke-loop24
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

- [x] **Step 3: Commit, push, and open draft PR**

Commit with an intentional message, push `loop-24-workflow-inputs-run-context`, open a draft PR, and monitor CI.
