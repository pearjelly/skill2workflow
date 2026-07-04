# Runtime Policy And Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make local retry and recovery behavior explicit, tested, and inspectable in run state and control-plane audit output.

**Architecture:** Keep Workflow DSL as the source of policy truth. Implement the smallest deterministic executor behavior for existing `retry.max_attempts` fields on connector nodes, record policy/recovery events in run state, and promote those events into published-run audit logs.

**Tech Stack:** Python 3.9 standard library, `unittest`, existing JSON/SQLite storage.

---

### Task 1: Runtime Policy Tests

**Files:**
- Modify: `tests/test_executor.py`
- Modify: `src/skill2workflow/executor.py`

- [x] **Step 1: Write retry/recovery failing test**

Add an executor test with a local HTTP server that returns `503` once and `200` on the second request. The workflow should set:

```python
"retry": {"max_attempts": 1}
```

on the `tool_call` node. Assert the completed run contains:

```python
self.assertEqual(state["status"], "completed")
self.assertEqual(len(server.requests), 2)
self.assertEqual(state["node_results"]["call_api"]["attempts"], 2)
self.assertIn("node_retrying", event_types)
self.assertIn("node_recovered", event_types)
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_executor.ExecutorTests.test_retry_policy_retries_failed_connector_and_records_recovery -v
```

Expected: fail because the executor does not retry connector failures yet.

- [x] **Step 3: Implement retry policy behavior**

Update `LocalExecutor._execute_connector_node()` to:

- resolve `retry.max_attempts` from the node, falling back to `workflow.policies.default_retry.max_attempts`
- execute connector nodes up to `1 + max_attempts`
- emit `node_retrying` after a failed attempt that will be retried
- emit `node_recovered` after a later attempt succeeds
- store `attempts`, `max_attempts`, and `last_error` in node results

- [x] **Step 4: Run focused executor tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_executor -v
```

Expected: pass.

### Task 2: Control-Plane Policy Audit

**Files:**
- Modify: `tests/test_control_plane.py`
- Modify: `src/skill2workflow/control_plane.py`

- [x] **Step 1: Write failing audit promotion test**

Add a published-run test using a flaky local HTTP server and a retry-enabled workflow. Assert control-plane audit includes:

```python
self.assertEqual(control.list_audit_events(event_type="node_retrying")[0]["node_id"], "call_api")
self.assertEqual(control.list_audit_events(event_type="node_recovered")[0]["node_id"], "call_api")
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_control_plane.ControlPlaneTests.test_published_retry_policy_promotes_policy_events_to_audit -v
```

Expected: fail because the control plane currently promotes only connector events.

- [x] **Step 3: Promote runtime policy events**

Update `LocalControlPlane` to promote selected runtime events into audit logs:

```python
{"node_retrying", "node_recovered", "node_failed"}
```

Include `run_id`, `workflow_id`, `workflow_version`, `node_id`, `attempt`, `max_attempts`, and `error` when present.

- [x] **Step 4: Run focused control-plane tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_control_plane -v
```

Expected: pass.

### Task 3: Runtime Policy Docs And Roadmap

**Files:**
- Create: `docs/runtime-policy.md`
- Modify: `docs/connectors.md`
- Modify: `HARNESS.md`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `ROADMAP.md`

- [x] **Step 1: Document retry and recovery semantics**

Create `docs/runtime-policy.md` explaining:

- `retry.max_attempts` counts retries after the first attempt
- connector request `timeout_ms` remains the HTTP request timeout
- `node_retrying`, `node_recovered`, and `node_failed` are inspectable run/audit events
- no background queue, distributed scheduling, or credential system exists yet

- [x] **Step 2: Update connector boundary docs**

Update `docs/connectors.md` so the Retry And Timeout Boundary section says local executor retry behavior now applies to connector nodes.

- [x] **Step 3: Advance roadmap**

Mark Loop 21 complete only after tests and docs are in place, then set the next closed loop to credential boundary or trigger/API work.

### Task 4: Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-07-04-runtime-policy-recovery.md`

- [x] **Step 1: Run final verification**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/demo_bootstrap.py --work-dir /tmp/skill2workflow-demo-loop21
python3 scripts/package_smoke.py --work-dir /tmp/skill2workflow-package-smoke
git diff --check
```

Expected: all pass.
