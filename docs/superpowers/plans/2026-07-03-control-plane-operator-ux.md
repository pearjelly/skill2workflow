# Control Plane Operator UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only operator insight layer to exported control-plane snapshots and expose it in the static control-plane inspector.

**Architecture:** Keep Workflow DSL and published artifacts authoritative and immutable. Build derived `operator_insights` in `src/skill2workflow/dashboard.py` from existing workflows, runs, audit events, connectors, and version comparisons, then render those derived records in `web/control.html` and `web/control.js`.

**Tech Stack:** Python 3.9 standard library, `unittest`, static HTML/CSS/JS.

---

### Task 1: Snapshot Operator Insights

**Files:**
- Modify: `tests/test_dashboard.py`
- Modify: `src/skill2workflow/dashboard.py`

- [x] **Step 1: Write the failing test**

Add assertions that `build_control_snapshot()` returns `operator_insights` with:

```python
self.assertEqual(snapshot["operator_insights"]["attention_counts"]["failed"], 1)
self.assertEqual(snapshot["operator_insights"]["attention_counts"]["waiting"], 1)
self.assertEqual(snapshot["operator_insights"]["connector_event_counts"]["connector_failed"], 1)
self.assertEqual(snapshot["operator_insights"]["recent_events"][-1]["type"], "connector_failed")
self.assertEqual(snapshot["operator_insights"]["version_changes"][0]["workflow_id"], "workflow_dashboard")
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_dashboard -v
```

Expected: fail because `operator_insights` is missing.

- [x] **Step 3: Implement derived snapshot fields**

Add helpers in `src/skill2workflow/dashboard.py` that derive:

```python
operator_insights = {
    "attention_counts": {"failed": 0, "waiting": 0},
    "attention_items": [],
    "recent_events": [],
    "connector_event_counts": {},
    "version_changes": [],
}
```

- [x] **Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_dashboard tests.test_control_plane -v
```

Expected: pass.

### Task 2: Static Operator View

**Files:**
- Modify: `web/control.html`
- Modify: `web/control.js`
- Modify: `web/control.css`
- Modify: `examples/control-plane-snapshot.json`

- [x] **Step 1: Add Operator tab and panel**

Add a read-only Operator tab with attention, recent event, connector event, and version change tables.

- [x] **Step 2: Render `operator_insights`**

Update `web/control.js` to validate optional `operator_insights`, render tables, include filtering, and show detail JSON on row click.

- [x] **Step 3: Refresh example snapshot**

Regenerate or update `examples/control-plane-snapshot.json` so the UI loads the new snapshot shape by default.

### Task 3: Docs, Roadmap, And Verification

**Files:**
- Modify: `README.md`
- Modify: `HARNESS.md`
- Modify: `ROADMAP.md`

- [x] **Step 1: Document operator insight flow**

Document that `control-snapshot` exports read-only operator insights and the static UI can inspect them.

- [x] **Step 2: Advance Roadmap**

Mark Loop 18 complete and set the next loop to a small follow-up only if the implementation meets acceptance criteria.

- [x] **Step 3: Run final verification**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
PYTHONPATH=src python3 -m unittest tests.test_dashboard tests.test_control_plane -v
PYTHONPATH=src python3 -m skill2workflow.cli control-snapshot --state-dir /tmp/skill2workflow-control -o /tmp/skill2workflow-control-snapshot.json
git diff --check
```

Expected: all pass.
