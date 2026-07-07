# Pilot Scenario Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic local pilot scenario pack that proves the current trigger, schedule-adjacent, credential, body input mapping, audit, snapshot, and LiteGraph overlay boundaries generalize beyond the single customer-support smoke.

**Architecture:** Keep `run_pilot_playbook()` as the existing single-scenario smoke. Add `src/skill2workflow/pilot_scenarios.py` as a pack runner that invokes the customer-support pilot and two additional local HTTP scenarios using existing `LocalControlPlane`, `StaticCredentialProvider`, `handle_webhook_request`, `build_control_snapshot`, and `workflow_to_litegraph` APIs. Add a tiny script wrapper under `scripts/` and tests under `tests/`.

**Tech Stack:** Python 3.9 standard library, `unittest`, local HTTP servers, JSON artifacts.

## Global Constraints

- Runtime code must remain Python 3.9 standard library.
- Workflow DSL remains the execution truth source.
- Scenario payloads must use non-secret business metadata only.
- Credential material must stay in local process memory and must not appear in run state, artifacts, result JSON, LiteGraph overlays, or audit output.
- No product-specific SaaS connector packages, OAuth, dynamic connector loading, hosted callbacks, queues, or production schedulers in Loop 32.

---

### Task 1: Scenario Pack Contract

**Files:**
- Create: `tests/test_pilot_scenarios.py`
- Create: `src/skill2workflow/pilot_scenarios.py`
- Create: `scripts/pilot_scenario_pack_smoke.py`

**Interfaces:**
- Consumes: `run_pilot_scenario_pack(repo_root: Path, work_dir: Path, reset: bool = True) -> Dict[str, object]`
- Produces: compact result with `ok`, `scenario_count`, `scenarios`, `artifacts`, and `commands`

- [x] **Step 1: Write failing scenario pack test**

Add `tests/test_pilot_scenarios.py`:

```python
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.pilot_scenarios import run_pilot_scenario_pack


class PilotScenarioPackTests(TestCase):
    def test_pilot_scenario_pack_runs_multiple_local_scenarios(self):
        repo_root = Path(__file__).resolve().parents[1]

        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot-pack"
            result = run_pilot_scenario_pack(repo_root=repo_root, work_dir=work_dir, reset=True)

            index_path = Path(result["artifacts"]["index"])
            self.assertTrue(index_path.exists())
            pack_index = json.loads(index_path.read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["scenario_count"], 3)
        self.assertEqual([item["id"] for item in result["scenarios"]], ["customer_support", "sales_renewal", "risk_exception"])
        self.assertTrue(all(item["run_status"] == "completed" for item in result["scenarios"]))
        self.assertTrue(all(item["connector_request"]["mapped_body_matched"] for item in result["scenarios"]))
        self.assertTrue(all(item["snapshot_summary"]["run_status_counts"] == {"completed": 1} for item in result["scenarios"]))
        self.assertNotIn("local-secret-value", json.dumps(result))
        self.assertEqual(pack_index["scenario_count"], 3)
```

- [x] **Step 2: Verify red**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_pilot_scenarios -v
```

Expected: import error for `skill2workflow.pilot_scenarios`.

- [x] **Step 3: Implement pack runner and script**

Create `src/skill2workflow/pilot_scenarios.py` with:

- `run_pilot_scenario_pack(repo_root, work_dir, reset=True)`
- scenario definitions for `customer_support`, `sales_renewal`, and `risk_exception`
- local HTTP receiver per scenario
- compact connector request summaries with `mapped_body_matched` boolean and body keys only
- JSON artifacts under `<work_dir>/artifacts/<scenario-id>/`

Create `scripts/pilot_scenario_pack_smoke.py` as a thin wrapper over `skill2workflow.pilot_scenarios.main`.

- [x] **Step 4: Verify green**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_pilot_scenarios -v
```

Expected: test passes.

### Task 2: Existing Pilot Mapping Evidence

**Files:**
- Modify: `src/skill2workflow/pilot.py`
- Modify: `tests/test_pilot.py`

**Interfaces:**
- Consumes: existing `run_pilot_playbook(...)`
- Produces: connector request summary with `mapped_body_matched`

- [x] **Step 1: Write failing assertion**

Add to `tests/test_pilot.py`:

```python
self.assertTrue(result["connector_request"]["mapped_body_matched"])
self.assertIn("ticket_id", result["connector_request"]["body_keys"])
```

- [x] **Step 2: Verify red**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_pilot.PilotPlaybookTests.test_pilot_playbook_generates_runnable_local_pilot_artifacts -v
```

Expected: key error for `mapped_body_matched`.

Actual RED evidence was captured through `tests.test_pilot_scenarios`, which failed on the missing customer-support `connector_request.mapped_body_matched` field before the existing pilot was updated.

- [x] **Step 3: Add body-only input mapping to pilot workflow**

Update `_pilot_workflow()` so `call_support_api.connector.request.input_mapping` maps:

```json
[
  {"from": "/input/customer_id", "to": "/body/customer_id", "required": true},
  {"from": "/input/priority", "to": "/body/priority", "required": true},
  {"from": "/input/ticket_id", "to": "/body/ticket_id", "required": true}
]
```

Update `_connector_request_summary()` to return `mapped_body_matched` by checking that the local receiver saw the expected non-secret values.

- [x] **Step 4: Verify green**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_pilot -v
```

Expected: tests pass.

### Task 3: Documentation And Roadmap

**Files:**
- Modify: `docs/pilot-playbook.md`
- Modify: `docs/examples.md`
- Modify: `README.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Consumes: scenario pack script and result shape
- Produces: evaluator-facing commands and Loop 32 completion state

- [x] **Step 1: Document scenario pack command**

Add the command:

```bash
python3 scripts/pilot_scenario_pack_smoke.py --work-dir /tmp/skill2workflow-pilot-pack
```

Document the three scenarios and artifacts.

- [x] **Step 2: Update Roadmap**

Move Loop 32 to completed loops and set Loop 33 as the active Connector Extension Prototype loop.

- [x] **Step 3: Update README and examples docs**

Mention the scenario pack smoke and local-only boundaries.

### Task 4: Verification And PR

**Files:**
- No additional files.

**Interfaces:**
- Consumes: all Loop 32 changes
- Produces: draft PR

- [x] **Step 1: Run focused verification**

```bash
PYTHONPATH=src python3 -m unittest tests.test_pilot tests.test_pilot_scenarios -v
python3 scripts/pilot_scenario_pack_smoke.py --work-dir /tmp/skill2workflow-pilot-pack-loop32
```

- [x] **Step 2: Run full verification**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py
python3 scripts/secret_hygiene.py examples/workflows
git diff --check
```

- [x] **Step 3: Commit and open draft PR**

```bash
git add README.md ROADMAP.md docs/examples.md docs/pilot-playbook.md docs/superpowers/plans/2026-07-07-pilot-scenario-pack.md scripts/pilot_scenario_pack_smoke.py src/skill2workflow/pilot.py src/skill2workflow/pilot_scenarios.py tests/test_pilot.py tests/test_pilot_scenarios.py
git commit -m "feat: add pilot scenario pack"
git push -u origin loop-32-pilot-scenario-pack
```
