# Run Overlay Visual Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add read-only run/audit overlay data so local operators can inspect execution evidence on workflow graph nodes.

**Architecture:** Keep Workflow DSL as the source of truth. Derive compact overlay data from run state and audit events in `src/skill2workflow/visualizer.py`, attach that data to LiteGraph node properties, and expose the same run summaries through `src/skill2workflow/dashboard.py`. Static web files render the overlay as read-only view state.

**Tech Stack:** Python 3.9 standard library, `unittest`, existing static HTML/CSS/JS, existing local control-plane snapshot flow.

---

### Task 1: Overlay Data Contract

**Files:**
- Modify: `tests/test_visualizer.py`
- Modify: `src/skill2workflow/visualizer.py`

- [x] **Step 1: Write failing visualizer tests**

Add tests for a compact node overlay derived from run state:
- completed node includes status, event count, latest event type, and result summary
- waiting current node is marked current and waiting
- connector node includes connector status and attempt count from connector/retry events
- trigger metadata is represented by keys only, not full input values

- [x] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_visualizer -v
```

Expected: fail because `run_overlay` is missing from LiteGraph node properties.

- [x] **Step 3: Implement minimal overlay derivation**

Add a public helper such as `run_overlay_for_nodes(node_ids, run_state, audit_events=None)` and attach each node overlay under `properties.run_overlay` in `workflow_to_litegraph`.

- [x] **Step 4: Verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_visualizer -v
```

Expected: visualizer tests pass.

### Task 2: Control Snapshot Overlay

**Files:**
- Modify: `tests/test_dashboard.py`
- Modify: `src/skill2workflow/dashboard.py`

- [x] **Step 1: Write failing dashboard tests**

Add tests proving each run summary can include a compact `node_overlays` list or map with node id, status, current marker, event count, connector status, and attempt count.

- [x] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_dashboard -v
```

Expected: fail because snapshot run summaries do not export node overlay data.

- [x] **Step 3: Reuse visualizer overlay derivation**

Update `_run_summary` to derive node overlays from full run detail and matching audit events. Keep the export compact and omit raw trigger input, connector payloads, and secrets.

- [x] **Step 4: Verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_dashboard -v
```

Expected: dashboard tests pass.

### Task 3: Static UI Rendering

**Files:**
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/control.html`
- Modify: `web/control.js`

- [x] **Step 1: Add read-only fields**

Show node overlay summary in the editor inspector and add a control-plane table for per-node run evidence. Keep all overlay fields readonly.

- [x] **Step 2: Preserve existing editing behavior**

Ensure save/write-back still ignores overlay fields and continues to mutate only existing allowlisted authoring fields.

- [x] **Step 3: Smoke the static assets**

Use the committed example snapshot and generated LiteGraph JSON to verify the files render without syntax errors.

### Task 4: Docs, Roadmap, And Verification

**Files:**
- Modify: `README.md`
- Modify: `HARNESS.md`
- Modify: `docs/authoring.md`
- Modify: `ROADMAP.md`
- Modify: `docs/superpowers/plans/2026-07-06-run-overlay-visual-editor.md`

- [x] **Step 1: Document operator flow**

Document how to generate a run, export or visualize the overlay data, and inspect it in the static UI. State that overlay data is view state, not Workflow DSL source.

- [x] **Step 2: Mark Loop 27 complete**

Move Loop 27 into the completed loop table and make Loop 28 the next active roadmap item.

- [x] **Step 3: Run full verification**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
PYTHONPATH=src python3 -m unittest tests.test_visualizer tests.test_dashboard tests.test_cli -v
python3 scripts/demo_bootstrap.py --work-dir /tmp/skill2workflow-demo-loop27
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

Expected: all commands pass.

- [x] **Step 4: Publish**

Commit, push, and open a draft PR.
