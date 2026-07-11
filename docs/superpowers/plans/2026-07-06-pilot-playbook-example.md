# Pilot Playbook Example Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a runnable local pilot playbook that demonstrates the current runtime boundary end to end.

**Architecture:** Add a dependency-free pilot smoke helper that builds a local workflow with a manual gate, HTTP connector credential handle, webhook trigger, audit export, control snapshot, and LiteGraph run overlay. Keep the helper thin over existing `LocalControlPlane`, `StaticCredentialProvider`, `handle_webhook_request`, `build_control_snapshot`, and `workflow_to_litegraph` APIs. Document the same scenario as the supported pilot path without adding product-specific SaaS connectors or production deployment claims.

**Tech Stack:** Python 3.9 standard library, `unittest`, existing JSON/SQLite local control-plane storage, existing static UI.

---

### Task 1: Pilot Smoke Contract

**Files:**
- Create: `tests/test_pilot.py`
- Create: `src/skill2workflow/pilot.py`

- [x] **Step 1: Write the failing pilot smoke test**

Add `tests/test_pilot.py` with a test that calls `run_pilot_playbook(repo_root, work_dir, reset=True)` and asserts:

```python
self.assertTrue(result["ok"])
self.assertEqual(result["workflow_id"], "workflow_customer_support_pilot")
self.assertEqual(result["workflow_version"], "0.1.0")
self.assertEqual(result["run_status"], "completed")
self.assertEqual(result["trigger_response"]["source"], "local-webhook")
self.assertEqual(result["trigger_response"]["input_keys"], ["customer_id", "priority", "ticket_id"])
self.assertTrue(Path(result["artifacts"]["workflow"]).exists())
self.assertTrue(Path(result["artifacts"]["snapshot"]).exists())
self.assertTrue(Path(result["artifacts"]["litegraph_overlay"]).exists())
self.assertEqual(result["snapshot_summary"]["run_status_counts"], {"completed": 1})
```

Also inspect generated artifacts:

```python
snapshot = json.loads(Path(result["artifacts"]["snapshot"]).read_text(encoding="utf-8"))
graph = json.loads(Path(result["artifacts"]["litegraph_overlay"]).read_text(encoding="utf-8"))
run_detail = json.loads(Path(result["artifacts"]["run"]).read_text(encoding="utf-8"))

self.assertEqual(run_detail["context"]["input"]["ticket_id"], "ticket_123")
self.assertEqual(run_detail["context"]["trigger"]["source"], "local-webhook")
self.assertNotIn("local-secret-value", json.dumps(run_detail))
self.assertIn("node_overlays", snapshot["runs"][0])
self.assertEqual(snapshot["runs"][0]["node_overlays"]["call_support_api"]["connector_status"], "completed")
self.assertEqual(graph["extra"]["run_overlay"]["trigger"]["input_keys"], ["customer_id", "priority", "ticket_id"])
self.assertNotIn("ticket_123", json.dumps(graph["extra"]["run_overlay"]))
self.assertTrue(result["connector_request"]["authorization_present"])
self.assertTrue(result["connector_request"]["credential_header_matched"])
self.assertNotIn("local-secret-value", json.dumps(result))
```

- [x] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_pilot -v
```

Expected: fail because `skill2workflow.pilot` does not exist.

### Task 2: Pilot Smoke Helper

**Files:**
- Modify: `src/skill2workflow/pilot.py`
- Create: `scripts/pilot_playbook_smoke.py`

- [x] **Step 1: Implement the local pilot runner**

Implement `run_pilot_playbook(repo_root, work_dir=Path(tempfile.gettempdir()) / "skill2workflow-pilot", reset=True)` to:

- reset the work directory with the same safety rules as `demo.py`
- start a local HTTP capture server on port `0`
- build a workflow with nodes `start -> intake_review -> call_support_api -> end`, plus `failure`
- reference credential handle `pilot_api_token` in the HTTP connector Authorization header
- publish the workflow into local control-plane state
- trigger it through `handle_webhook_request()` with source `local-webhook`
- resume the waiting manual gate
- write artifacts: `workflow.json`, `trigger-response.json`, `run.json`, `control-plane-snapshot.json`, `workflow.overlay.litegraph.json`
- return command hints for `scripts/pilot_playbook_smoke.py`, `python3 -m http.server 4173`, and `http://localhost:4173/web/control.html`

- [x] **Step 2: Add the script wrapper**

Add `scripts/pilot_playbook_smoke.py` that mirrors `scripts/demo_bootstrap.py`:

```python
#!/usr/bin/env python3
"""Run the skill2workflow local pilot playbook smoke from a source checkout."""
```

It should insert `src/` into `sys.path`, import `skill2workflow.pilot.main`, and call it.

- [x] **Step 3: Verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_pilot -v
python3 scripts/pilot_playbook_smoke.py --work-dir /tmp/skill2workflow-pilot-loop28
```

Expected: both pass and print a JSON result with `ok: true` and `run_status: completed`.

### Task 3: Pilot Documentation

**Files:**
- Create: `docs/pilot-playbook.md`
- Modify: `README.md`
- Modify: `HARNESS.md`

- [x] **Step 1: Document the supported pilot path**

Create `docs/pilot-playbook.md` with:

- purpose and audience
- scenario: customer support escalation pilot
- one-command smoke path
- artifact list
- how to inspect `control-plane-snapshot.json` in `web/control.html`
- what is supported now
- what remains experimental
- what must stay outside the bootstrap runtime
- verification checklist

- [x] **Step 2: Link the playbook from contributor entry points**

Update README Quickstart/Roadmap and HARNESS local verification sections with:

```bash
python3 scripts/pilot_playbook_smoke.py --work-dir /tmp/skill2workflow-pilot
```

- [x] **Step 3: Verify documentation references**

Run:

```bash
grep -R "pilot_playbook_smoke" -n README.md HARNESS.md docs/pilot-playbook.md
```

Expected: all three files reference the command.

### Task 4: Roadmap And Verification

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/superpowers/plans/2026-07-06-pilot-playbook-example.md`

- [x] **Step 1: Mark Loop 28 complete**

Move Loop 28 into the completed loop table, update Real Team Pilot Readiness to remove the pilot playbook gap, and set the next active loop to a narrowly scoped follow-up such as scheduled trigger boundary.

- [x] **Step 2: Run full verification**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
PYTHONPATH=src python3 -m unittest tests.test_pilot tests.test_demo tests.test_dashboard tests.test_cli -v
python3 scripts/pilot_playbook_smoke.py --work-dir /tmp/skill2workflow-pilot-loop28
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

Expected: all commands pass.

- [x] **Step 3: Publish**

Commit, push, and open a draft PR.
