# Controlled Live Connector Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver and operate Loop 40 as a paid, assisted, controlled real-team sales-renewal pilot with explicit human approval, five approved live runs across five calendar days, redacted evidence, failure and rollback exercises, and a final `continue`, `harden`, or `defer` decision.

**Architecture:** Reuse the existing published sales-renewal workflow and out-of-core Lark connector, but add a separate controlled-live orchestration path backed by SQLite private state. Keep raw business input and the Vault-injected token outside the repository; derive a strict allowlisted evidence pack through a separate evidence module. Do not advance the Roadmap until the multi-day real pilot, exercises, commercial acknowledgement, partner acknowledgement, and complete verification all pass.

**Tech Stack:** Python 3.9 standard library, `unittest`, existing `LocalControlPlane`, SQLite storage, `ConnectorRuntime`, `StaticCredentialProvider`, explicit external connector loading, Avibe Vault process injection, JSON evidence, Markdown documentation.

## Global Constraints

- Workflow DSL remains the execution source of truth.
- Python 3.9 standard library remains sufficient; add no runtime dependency.
- The production direction remains self-hosted and single-tenant for one team.
- The only live operation is `lark_task.create_task` against the fixed Feishu domestic boundary.
- The Lark connector remains out of core and must be explicitly loaded.
- `dry_run` remains the connector and committed-example default.
- Existing Workflow DSL `0.1.0` compatibility remains unchanged.
- Private runtime state uses SQLite and must live outside the repository.
- The token may enter only as `LARK_BOT_ACCESS_TOKEN` injected into the approval process; never accept it as a CLI argument or file field.
- Real provider calls never run in unit tests or CI.
- Evidence must omit customer identity, account id/name, renewal-risk text, assignee open id, due time, credentials, authorization headers, request/response bodies, provider messages, task ids, and idempotency digests.
- At least five approved live workflow runs must span five distinct dates in the charter timezone `Asia/Shanghai` and represent at least two opaque private case ids.
- At least one human rejection, one disabled-live failure exercise, and one rollback exercise are mandatory.
- A paid or contractually committed assisted engagement is represented only as `commercial_engagement_confirmed: true`.
- Fake-transport success is implementation evidence, not real-pilot completion evidence.
- Roadmap completion occurs only in the final task after all real evidence passes.
- Parser, compiler, validator, executor, connector, storage, or CLI behavior changes begin with a failing test.

---

## File Map

- Modify `src/skill2workflow/lark_task_pilot.py`: expose the existing sales-renewal Workflow DSL builder without changing dry-run behavior.
- Create `src/skill2workflow/controlled_lark_pilot.py`: private workspace, charter, case validation, workflow start, explicit decision, exercises, verification, and finalization orchestration.
- Create `src/skill2workflow/controlled_lark_pilot_evidence.py`: pure redaction, evidence extraction, acceptance aggregation, validation, and atomic JSON writes.
- Create `scripts/controlled_lark_pilot.py`: thin source-checkout CLI wrapper.
- Modify `tests/test_lark_task_pilot.py`: reusable-template and dry-run regression tests.
- Create `tests/test_controlled_lark_pilot.py`: charter, private-state, start, decision, exercise, verification, and finalization tests.
- Create `tests/test_controlled_lark_pilot_evidence.py`: allowlist, leakage, aggregation, and deterministic-write tests.
- Create `tests/test_controlled_lark_pilot_docs.py`: runbook, command, evidence, and Roadmap-boundary contracts.
- Create `docs/controlled-live-pilot.md`: operator runbook for the assisted paid pilot.
- Modify `docs/connectors.md`: link the controlled pilot while retaining the narrow live boundary.
- Modify `docs/examples.md`: distinguish dry-run scenario evidence from the controlled live pilot.
- Modify `ROADMAP.md`, `README.md`, and existing Roadmap tests only after the real pilot finalizes.
- Generate `docs/pilot-evidence/loop-40/` only from a validated finalized private evidence pack.

---

### Task 1: Reusable Sales-Renewal Workflow Template

**Files:**
- Modify: `tests/test_lark_task_pilot.py`
- Modify: `src/skill2workflow/lark_task_pilot.py`

**Interfaces:**
- Consumes: existing `_lark_task_pilot_workflow()` implementation.
- Produces: `build_lark_task_pilot_workflow(mode: str = "dry_run", workflow_id: str = "workflow_lark_task_pilot", workflow_version: str = "0.1.0", workflow_name: str = "lark-task-sales-renewal-pilot") -> Dict[str, object]`.

- [x] **Step 1: Write failing template and regression tests**

Add the import and tests:

```python
from skill2workflow.lark_task_pilot import (
    build_lark_task_pilot_workflow,
    run_lark_task_pilot,
)


def test_lark_task_pilot_workflow_builder_keeps_dry_run_default(self):
    workflow = build_lark_task_pilot_workflow()
    node = next(item for item in workflow["nodes"] if item["id"] == "create_lark_task")

    self.assertEqual(workflow["workflow"]["id"], "workflow_lark_task_pilot")
    self.assertEqual(workflow["workflow"]["version"], "0.1.0")
    self.assertEqual(node["connector"]["mode"], "dry_run")
    self.assertIn("dry-run", node["description"])


def test_lark_task_pilot_workflow_builder_can_create_separate_live_artifact(self):
    workflow = build_lark_task_pilot_workflow(
        mode="live",
        workflow_id="workflow_controlled_lark_pilot",
        workflow_version="0.1.0",
        workflow_name="controlled-lark-task-sales-renewal-pilot",
    )
    node = next(item for item in workflow["nodes"] if item["id"] == "create_lark_task")

    self.assertEqual(workflow["workflow"]["id"], "workflow_controlled_lark_pilot")
    self.assertEqual(workflow["workflow"]["name"], "controlled-lark-task-sales-renewal-pilot")
    self.assertEqual(node["connector"]["mode"], "live")
    self.assertNotIn("dry-run", node["description"])


def test_lark_task_pilot_workflow_builder_rejects_unknown_mode(self):
    with self.assertRaisesRegex(ValueError, "mode must be dry_run or live"):
        build_lark_task_pilot_workflow(mode="other")
```

- [x] **Step 2: Run the focused test and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_task_pilot -v
```

Expected: import failure because `build_lark_task_pilot_workflow` does not exist.

- [x] **Step 3: Expose and parameterize the existing builder**

Apply these exact edits to the existing dictionary so every unchanged node and edge remains in place:

```diff
-    workflow = _lark_task_pilot_workflow()
+    workflow = build_lark_task_pilot_workflow()
@@
-def _lark_task_pilot_workflow() -> Dict[str, object]:
+def build_lark_task_pilot_workflow(
+    mode: str = "dry_run",
+    workflow_id: str = "workflow_lark_task_pilot",
+    workflow_version: str = "0.1.0",
+    workflow_name: str = "lark-task-sales-renewal-pilot",
+) -> Dict[str, object]:
+    if mode not in ("dry_run", "live"):
+        raise ValueError("mode must be dry_run or live")
+    live = mode == "live"
     return {
@@
-            "id": "workflow_lark_task_pilot",
-            "name": "lark-task-sales-renewal-pilot",
-            "description": "Local sales renewal risk pilot using the Lark/Feishu task dry-run connector.",
-            "version": "0.1.0",
+            "id": workflow_id,
+            "name": workflow_name,
+            "description": (
+                "Controlled sales renewal risk pilot using the scoped live Lark/Feishu task connector."
+                if live
+                else "Local sales renewal risk pilot using the Lark/Feishu task dry-run connector."
+            ),
+            "version": workflow_version,
@@
-                "description": "Validate a Lark/Feishu owner follow-up task request without calling the live API.",
+                "description": (
+                    "Create the approved Lark/Feishu owner follow-up task through the scoped live connector."
+                    if live
+                    else "Validate a Lark/Feishu owner follow-up task request without calling the live API."
+                ),
@@
-                    "instruction": "Create a dry-run Lark/Feishu task for the account owner.",
+                    "instruction": (
+                        "Create the approved live Lark/Feishu task for the account owner."
+                        if live
+                        else "Create a dry-run Lark/Feishu task for the account owner."
+                    ),
@@
-                    "mode": "dry_run",
+                    "mode": mode,
```

- [x] **Step 4: Run focused and fixture tests and verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_lark_task_pilot tests.test_examples -v
```

Expected: all tests pass; the existing smoke still emits `mode: dry_run`.

- [x] **Step 5: Commit the reusable template**

```bash
git add src/skill2workflow/lark_task_pilot.py tests/test_lark_task_pilot.py
git commit -m "refactor: expose lark pilot workflow template"
```

---

### Task 2: Private Workspace And Paid Pilot Charter

**Files:**
- Create: `tests/test_controlled_lark_pilot.py`
- Create: `src/skill2workflow/controlled_lark_pilot.py`

**Interfaces:**
- Consumes: `Path`, JSON, filesystem permissions, the approved design constants.
- Produces:
  - `initialize_pilot(repo_root: Path, work_dir: Path, charter: Dict[str, object], now: datetime = None) -> Dict[str, object]`
  - `load_pilot_charter(work_dir: Path, now: datetime = None) -> Dict[str, object]`
  - `load_private_case(repo_root: Path, input_path: Path) -> Dict[str, object]`
  - constants `PILOT_SCHEMA_VERSION`, `WORKFLOW_ID`, `WORKFLOW_VERSION`, `PILOT_TIMEZONE`.

- [x] **Step 1: Write failing charter, path, permission, and case tests**

Create `tests/test_controlled_lark_pilot.py` with:

```python
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.controlled_lark_pilot import (
    initialize_pilot,
    load_pilot_charter,
    load_private_case,
)


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc)


def _valid_charter():
    return {
        "schema_version": "controlled-lark-pilot-0.1.0",
        "scenario_id": "sales_renewal_risk_followup",
        "workflow_id": "workflow_controlled_lark_pilot",
        "workflow_version": "0.1.0",
        "support_model": "assisted",
        "timezone": "Asia/Shanghai",
        "starts_on": "2026-07-18",
        "expires_on": "2026-08-15",
        "team_consent_confirmed": True,
        "assignee_consent_confirmed": True,
        "commercial_engagement_confirmed": True,
        "required_approved_runs": 5,
        "required_distinct_days": 5,
        "required_distinct_cases": 2,
    }


class ControlledLarkPilotTests(TestCase):
    def test_initialize_pilot_creates_owner_only_private_workspace(self):
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "controlled-pilot"
            result = initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)

            self.assertEqual(result["status"], "initialized")
            self.assertEqual(result["workflow_id"], "workflow_controlled_lark_pilot")
            self.assertEqual(work_dir.stat().st_mode & 0o077, 0)
            self.assertEqual((work_dir / "private" / "charter.json").stat().st_mode & 0o077, 0)
            self.assertTrue((work_dir / "state").is_dir())
            self.assertTrue((work_dir / "evidence").is_dir())

    def test_initialize_pilot_rejects_repository_work_dir(self):
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            initialize_pilot(ROOT, ROOT / ".pilot-private", _valid_charter(), now=NOW)

    def test_charter_requires_consent_commercial_status_thresholds_and_active_dates(self):
        invalid_values = [
            ("team_consent_confirmed", False),
            ("assignee_consent_confirmed", False),
            ("commercial_engagement_confirmed", False),
            ("required_approved_runs", 4),
            ("required_distinct_days", 4),
            ("required_distinct_cases", 1),
            ("timezone", "UTC"),
        ]
        for key, value in invalid_values:
            charter = _valid_charter()
            charter[key] = value
            with self.subTest(key=key), TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):
                    initialize_pilot(ROOT, Path(tmp) / "pilot", charter, now=NOW)

    def test_load_pilot_charter_rejects_expired_charter(self):
        with TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "pilot"
            initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)
            with self.assertRaisesRegex(ValueError, "expired"):
                load_pilot_charter(
                    work_dir,
                    now=datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc),
                )

    def test_load_private_case_requires_external_owner_only_exact_shape(self):
        payload = {
            "pilot_case_id": "case-001",
            "account_name": "Private Account",
            "renewal_risk": "Private Risk",
            "owner_open_id": "ou_private",
            "due_at": "2026-08-15T09:00:00Z",
        }
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            os.chmod(path, 0o600)
            self.assertEqual(load_private_case(ROOT, path), payload)

            os.chmod(path, 0o644)
            with self.assertRaisesRegex(ValueError, "owner-only"):
                load_private_case(ROOT, path)
```

- [x] **Step 2: Run the new test and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_controlled_lark_pilot -v
```

Expected: import failure because `skill2workflow.controlled_lark_pilot` does not exist.

- [x] **Step 3: Implement charter validation and secure workspace helpers**

Create `src/skill2workflow/controlled_lark_pilot.py` with these constants and core helpers:

```python
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict
from zoneinfo import ZoneInfo


PILOT_SCHEMA_VERSION = "controlled-lark-pilot-0.1.0"
WORKFLOW_ID = "workflow_controlled_lark_pilot"
WORKFLOW_VERSION = "0.1.0"
SCENARIO_ID = "sales_renewal_risk_followup"
PILOT_TIMEZONE = "Asia/Shanghai"
REQUIRED_CASE_KEYS = {
    "pilot_case_id",
    "account_name",
    "renewal_risk",
    "owner_open_id",
    "due_at",
}


def initialize_pilot(
    repo_root: Path,
    work_dir: Path,
    charter: Dict[str, object],
    now: datetime = None,
) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    _require_outside_repository(repo_root, work_dir, "pilot work directory")
    normalized = _validate_charter(charter, now=now)

    _mkdir_private(work_dir)
    _mkdir_private(work_dir / "private")
    _mkdir_private(work_dir / "state")
    _mkdir_private(work_dir / "evidence")
    _write_private_json(work_dir / "private" / "charter.json", normalized)
    return {
        "status": "initialized",
        "scenario_id": SCENARIO_ID,
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "commercial_engagement_confirmed": True,
    }


def load_pilot_charter(work_dir: Path, now: datetime = None) -> Dict[str, object]:
    path = Path(work_dir).resolve() / "private" / "charter.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _validate_charter(payload, now=now)


def load_private_case(repo_root: Path, input_path: Path) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    input_path = Path(input_path).resolve()
    _require_outside_repository(repo_root, input_path, "private case input")
    _require_owner_only(input_path)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != REQUIRED_CASE_KEYS:
        raise ValueError("private case input must contain only the approved fields")
    normalized = {key: str(payload.get(key) or "").strip() for key in sorted(REQUIRED_CASE_KEYS)}
    if not all(normalized.values()):
        raise ValueError("private case input fields must be non-empty strings")
    if any(token in normalized["pilot_case_id"].lower() for token in ("account", "customer", "@", " ")):
        raise ValueError("pilot_case_id must be an opaque identifier")
    return normalized


def _validate_charter(charter: object, now: datetime = None) -> Dict[str, object]:
    if not isinstance(charter, dict):
        raise ValueError("pilot charter must be a JSON object")
    normalized = json.loads(json.dumps(charter, ensure_ascii=False))
    required_exact = {
        "schema_version": PILOT_SCHEMA_VERSION,
        "scenario_id": SCENARIO_ID,
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "support_model": "assisted",
        "timezone": PILOT_TIMEZONE,
        "required_approved_runs": 5,
        "required_distinct_days": 5,
        "required_distinct_cases": 2,
    }
    for key, expected in required_exact.items():
        if normalized.get(key) != expected:
            raise ValueError(f"pilot charter {key} must be {expected}")
    for key in (
        "team_consent_confirmed",
        "assignee_consent_confirmed",
        "commercial_engagement_confirmed",
    ):
        if normalized.get(key) is not True:
            raise ValueError(f"pilot charter {key} must be true")
    starts_on = date.fromisoformat(str(normalized.get("starts_on", "")))
    expires_on = date.fromisoformat(str(normalized.get("expires_on", "")))
    current = (now or datetime.now(timezone.utc)).astimezone(
        ZoneInfo(PILOT_TIMEZONE)
    ).date()
    if current < starts_on:
        raise ValueError("pilot charter has not started")
    if current > expires_on:
        raise ValueError("pilot charter expired")
    return normalized


def _require_outside_repository(repo_root: Path, path: Path, label: str) -> None:
    if path == repo_root or repo_root in path.parents:
        raise ValueError(f"{label} must be outside the repository")


def _mkdir_private(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)


def _write_private_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(path, 0o600)


def _require_owner_only(path: Path) -> None:
    if os.name == "posix" and path.stat().st_mode & 0o077:
        raise ValueError("private case input must use owner-only permissions")
```

- [x] **Step 4: Run charter tests and verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_controlled_lark_pilot -v
```

Expected: all charter, path, permission, and input-shape tests pass.

- [x] **Step 5: Commit the private workspace boundary**

```bash
git add src/skill2workflow/controlled_lark_pilot.py tests/test_controlled_lark_pilot.py
git commit -m "feat: add controlled pilot charter boundary"
```

---

### Task 3: Durable Start At The Human Gate

**Files:**
- Modify: `tests/test_controlled_lark_pilot.py`
- Modify: `src/skill2workflow/controlled_lark_pilot.py`

**Interfaces:**
- Consumes: `build_lark_task_pilot_workflow`, `LocalControlPlane`, `ConnectorRuntime`, `load_external_connector`, `StaticCredentialProvider`, charter and private-case helpers.
- Produces:
  - `start_pilot_run(repo_root: Path, work_dir: Path, input_path: Path, now: datetime = None, transport=None) -> Dict[str, object]`
  - `_pilot_control_plane(repo_root: Path, work_dir: Path, credential_provider, transport=None) -> LocalControlPlane`.

- [x] **Step 1: Write the failing durable-start test**

Add:

```python
def _write_private_case(path: Path, case_id: str = "case-001") -> None:
    path.write_text(
        json.dumps(
            {
                "pilot_case_id": case_id,
                "account_name": "Private Account",
                "renewal_risk": "Private Risk",
                "owner_open_id": "ou_private",
                "due_at": "2026-08-15T09:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    os.chmod(path, 0o600)


def _start_waiting_pilot(tmp: str, case_id: str = "case-001"):
    root = Path(tmp)
    work_dir = root / "pilot"
    input_path = root / "case.json"
    initialize_pilot(ROOT, work_dir, _valid_charter(), now=NOW)
    _write_private_case(input_path, case_id=case_id)
    started = start_pilot_run(ROOT, work_dir, input_path, now=NOW)
    return work_dir, started


def test_start_pilot_run_publishes_live_workflow_and_stops_at_gate(self):
    with TemporaryDirectory() as tmp:
        work_dir, result = _start_waiting_pilot(tmp)
        control = LocalControlPlane(work_dir / "state", storage="sqlite")
        run = control.get_run(result["run_id"])
        workflow = control.get_workflow("workflow_controlled_lark_pilot", "0.1.0")
        node = next(item for item in workflow["nodes"] if item["id"] == "create_lark_task")

    self.assertEqual(result["run_status"], "waiting")
    self.assertEqual(result["current_node"], "review_renewal_risk")
    self.assertEqual(result["input_keys"], [
        "account_name", "due_at", "owner_open_id", "pilot_case_id", "renewal_risk"
    ])
    self.assertEqual(run["status"], "waiting")
    self.assertEqual(node["connector"]["mode"], "live")
    self.assertNotIn("Private Account", json.dumps(result))
```

Add imports for `LocalControlPlane` and `start_pilot_run`.

- [x] **Step 2: Run the focused test and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_controlled_lark_pilot.ControlledLarkPilotTests.test_start_pilot_run_publishes_live_workflow_and_stops_at_gate -v
```

Expected: import failure because `start_pilot_run` does not exist.

- [x] **Step 3: Implement fixed workflow publication and trigger**

Add:

```python
from .connectors import ConnectorRuntime, ExternalConnector
from .control_plane import LocalControlPlane
from .credentials import StaticCredentialProvider
from .external_connectors import load_external_connector
from .lark_task_pilot import build_lark_task_pilot_workflow


def start_pilot_run(
    repo_root: Path,
    work_dir: Path,
    input_path: Path,
    now: datetime = None,
    transport=None,
) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    load_pilot_charter(work_dir, now=now)
    pilot_input = load_private_case(repo_root, input_path)
    control = _pilot_control_plane(
        repo_root,
        work_dir,
        credential_provider=StaticCredentialProvider({}),
        transport=transport,
    )
    workflow = build_lark_task_pilot_workflow(
        mode="live",
        workflow_id=WORKFLOW_ID,
        workflow_version=WORKFLOW_VERSION,
        workflow_name="controlled-lark-task-sales-renewal-pilot",
    )
    control.publish_workflow(workflow)
    response = control.trigger_workflow(
        {
            "workflow_id": WORKFLOW_ID,
            "version": WORKFLOW_VERSION,
            "source": "controlled-live-pilot",
            "idempotency_key": "",
            "input": pilot_input,
        }
    )
    run = control.get_run(str(response["run_id"]))
    if run.get("status") != "waiting" or run.get("current_node") != "review_renewal_risk":
        raise ValueError("controlled pilot run did not stop at the expected human gate")
    return {
        "run_id": str(response["run_id"]),
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "run_status": "waiting",
        "current_node": "review_renewal_risk",
        "input_keys": sorted(pilot_input),
    }


def _pilot_control_plane(
    repo_root: Path,
    work_dir: Path,
    credential_provider,
    transport=None,
) -> LocalControlPlane:
    connector = load_external_connector(repo_root / "examples" / "connectors" / "lark_task_connector.py")
    if transport is not None:
        original = connector

        def execute_with_transport(binding, credential_provider=None, context=None):
            return original.executor(
                binding,
                credential_provider=credential_provider,
                context=context,
                transport=transport,
            )

        connector = ExternalConnector(manifest=original.manifest, executor=execute_with_transport)
    runtime = ConnectorRuntime([connector])
    return LocalControlPlane(
        work_dir / "state",
        storage="sqlite",
        credential_provider=credential_provider,
        connector_runtime=runtime,
    )
```

Do not print or return `pilot_input`.

- [x] **Step 4: Run start and existing pilot tests and verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_controlled_lark_pilot tests.test_lark_task_pilot -v
```

Expected: all tests pass and no transport is called during `start`.

- [x] **Step 5: Commit durable start**

```bash
git add src/skill2workflow/controlled_lark_pilot.py tests/test_controlled_lark_pilot.py
git commit -m "feat: start controlled lark pilot runs"
```

---

### Task 4: Explicit Approve Or Reject Decision

**Files:**
- Modify: `tests/test_controlled_lark_pilot.py`
- Modify: `src/skill2workflow/controlled_lark_pilot.py`

**Interfaces:**
- Consumes: waiting SQLite run, environment switch, Vault-injected token, optional fake transport.
- Produces:
  - `decide_pilot_run(repo_root: Path, work_dir: Path, run_id: str, approved: bool, confirmed_live: bool = False, now: datetime = None, transport=None) -> Dict[str, object]`.
  - `_validate_controlled_live_binding(workflow: Dict[str, object], run: Dict[str, object]) -> None`.

- [x] **Step 1: Write failing approval, rejection, guard, repeat, and redaction tests**

Add a fake transport that records calls and returns a compact successful provider response:

```python
class _FakeResponse:
    status = 200

    def read(self):
        return json.dumps(
            {"code": 0, "msg": "success", "data": {"task": {"guid": "private-task-guid"}}}
        ).encode("utf-8")

    def close(self):
        return None


class _FakeTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append((request, timeout))
        return _FakeResponse()
```

Add complete tests that start a fresh waiting run for each decision path:

```python
def test_decide_approve_requires_all_live_guards_and_returns_redacted_summary(self):
    with TemporaryDirectory() as tmp:
        work_dir, started = _start_waiting_pilot(tmp)
        transport = _FakeTransport()
        environment = {
            "SKILL2WORKFLOW_LARK_TASK_LIVE": "1",
            "LARK_BOT_ACCESS_TOKEN": "private-token",
        }
        with patch.dict(os.environ, environment, clear=True):
            result = decide_pilot_run(
                ROOT,
                work_dir,
                started["run_id"],
                approved=True,
                confirmed_live=True,
                now=NOW,
                transport=transport,
            )

        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(result["gate_decision"], "approved")
        self.assertEqual(result["provider_status"], "completed")
        self.assertTrue(result["lark_task_id_present"])
        self.assertEqual(len(transport.calls), 1)
        encoded = json.dumps(result)
        for forbidden in (
            "private-token", "Private Account", "Private Risk", "ou_private",
            "private-task-guid",
        ):
            self.assertNotIn(forbidden, encoded)


def test_decide_reject_needs_no_token_and_never_calls_transport(self):
    with TemporaryDirectory() as tmp:
        work_dir, started = _start_waiting_pilot(tmp)
        transport = _FakeTransport()
        with patch.dict(os.environ, {}, clear=True):
            result = decide_pilot_run(
                ROOT, work_dir, started["run_id"], approved=False, now=NOW,
                transport=transport,
            )
        self.assertEqual(result["run_status"], "failed")
        self.assertEqual(result["gate_decision"], "rejected")
        self.assertFalse(result["connector_invoked"])
        self.assertEqual(transport.calls, [])


def test_decide_approve_fails_before_resume_when_confirmation_switch_or_token_is_missing(self):
    with TemporaryDirectory() as tmp:
        work_dir, started = _start_waiting_pilot(tmp)
        transport = _FakeTransport()
        cases = [
            ({"SKILL2WORKFLOW_LARK_TASK_LIVE": "1", "LARK_BOT_ACCESS_TOKEN": "token"}, False, "confirmation"),
            ({"LARK_BOT_ACCESS_TOKEN": "token"}, True, "SKILL2WORKFLOW_LARK_TASK_LIVE=1"),
            ({"SKILL2WORKFLOW_LARK_TASK_LIVE": "1"}, True, "LARK_BOT_ACCESS_TOKEN"),
        ]
        for environment, confirmed, expected in cases:
            with self.subTest(expected=expected), patch.dict(os.environ, environment, clear=True):
                with self.assertRaisesRegex(ValueError, expected):
                    decide_pilot_run(
                        ROOT,
                        work_dir,
                        started["run_id"],
                        approved=True,
                        confirmed_live=confirmed,
                        now=NOW,
                        transport=transport,
                    )
        self.assertEqual(transport.calls, [])


def test_decide_rejects_second_decision_for_terminal_run_without_transport(self):
    with TemporaryDirectory() as tmp:
        work_dir, started = _start_waiting_pilot(tmp)
        transport = _FakeTransport()
        environment = {
            "SKILL2WORKFLOW_LARK_TASK_LIVE": "1",
            "LARK_BOT_ACCESS_TOKEN": "private-token",
        }
        with patch.dict(os.environ, environment, clear=True):
            decide_pilot_run(
                ROOT, work_dir, started["run_id"], approved=True,
                confirmed_live=True, now=NOW, transport=transport,
            )
            with self.assertRaisesRegex(ValueError, "not waiting"):
                decide_pilot_run(
                    ROOT, work_dir, started["run_id"], approved=True,
                    confirmed_live=True, now=NOW, transport=transport,
                )
        self.assertEqual(len(transport.calls), 1)
```

Import `patch` from `unittest.mock` and `decide_pilot_run` from the new module.

Add a table-driven unit test for `_validate_controlled_live_binding` that mutates each fixed property in turn—workflow id/version, current gate, connector id, operation, mode, credential handle, run id, and node id—and asserts a stable `ValueError` before any credential provider or transport can be constructed.

- [x] **Step 2: Run decision tests and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_controlled_lark_pilot -v
```

Expected: failure because `decide_pilot_run` does not exist.

- [x] **Step 3: Implement explicit decision guards and compact summaries**

Add:

```python
LIVE_SWITCH = "SKILL2WORKFLOW_LARK_TASK_LIVE"
TOKEN_ENVIRONMENT = "LARK_BOT_ACCESS_TOKEN"


def decide_pilot_run(
    repo_root: Path,
    work_dir: Path,
    run_id: str,
    approved: bool,
    confirmed_live: bool = False,
    now: datetime = None,
    transport=None,
) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    load_pilot_charter(work_dir, now=now)

    preflight = _pilot_control_plane(
        repo_root,
        work_dir,
        credential_provider=StaticCredentialProvider({}),
    )
    current = preflight.get_run(str(run_id))
    workflow = preflight.get_workflow(WORKFLOW_ID, WORKFLOW_VERSION)
    _validate_controlled_live_binding(workflow, current)

    token = ""
    if approved:
        if not confirmed_live:
            raise ValueError("live approval requires explicit confirmation")
        if os.environ.get(LIVE_SWITCH) != "1":
            raise ValueError("SKILL2WORKFLOW_LARK_TASK_LIVE=1 is required")
        token = os.environ.get(TOKEN_ENVIRONMENT, "")
        if not token:
            raise ValueError("LARK_BOT_ACCESS_TOKEN is required")

    credentials = {"lark_bot_access_token": token} if approved else {}
    control = _pilot_control_plane(
        repo_root,
        work_dir,
        credential_provider=StaticCredentialProvider(credentials),
        transport=transport,
    )
    state = control.resume_published_run(str(run_id), approved=approved)
    events = control.list_audit_events(run_id=str(run_id))
    connector_events = [
        event for event in events
        if event.get("type") in ("connector_started", "connector_completed", "connector_failed")
        and event.get("node_id") == "create_lark_task"
    ]
    connector_metadata = {}
    for event in reversed(connector_events):
        metadata = event.get("connector_metadata")
        if isinstance(metadata, dict):
            connector_metadata = metadata
            break
    return {
        "run_id": str(run_id),
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "run_status": str(state.get("status", "")),
        "gate_decision": "approved" if approved else "rejected",
        "connector_invoked": bool(connector_events),
        "connector_status": str(connector_events[-1].get("connector_status", "")) if connector_events else "",
        "credential_status": str(connector_events[-1].get("credential_status", "")) if connector_events else "",
        "provider_status": str(connector_metadata.get("provider_status", "")),
        "idempotency_key_present": bool(connector_metadata.get("idempotency_key_present")),
        "lark_task_id_present": bool(connector_metadata.get("lark_task_id_present")),
    }
```

`_validate_controlled_live_binding` checks exact workflow id/version, run id presence, `status == "waiting"`, `current_node == "review_renewal_risk"`, and the `create_lark_task` node's id, connector id `lark_task`, operation `create_task`, mode `live`, and sole credential handle `lark_bot_access_token`. It also requires all execution-identity fields used by provider idempotency to be non-empty. It raises only fixed redacted messages.

Do not include `token`, context, task values, provider payloads, or provider messages in raised errors or summaries.

- [x] **Step 4: Run controlled and connector tests and verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_controlled_lark_pilot tests.test_lark_task_connector tests.test_executor tests.test_control_plane -v
```

Expected: all tests pass; fake approval makes exactly one transport call; rejection makes none.

- [x] **Step 5: Commit explicit decision control**

```bash
git add src/skill2workflow/controlled_lark_pilot.py tests/test_controlled_lark_pilot.py
git commit -m "feat: add controlled lark pilot decisions"
```

---

### Task 5: Strict Redacted Evidence Pack

**Files:**
- Create: `tests/test_controlled_lark_pilot_evidence.py`
- Create: `src/skill2workflow/controlled_lark_pilot_evidence.py`
- Modify: `src/skill2workflow/controlled_lark_pilot.py`

**Interfaces:**
- Consumes: full private run states, control-plane audit events, validated charter, exercise/verification/decision state.
- Produces:
  - `build_run_evidence(run: Dict[str, object], audit_events: List[Dict[str, object]]) -> Dict[str, object]`
  - `build_acceptance_summary(charter: Dict[str, object], runs: List[Dict[str, object]], distinct_private_cases: int, exercises: Dict[str, object], verification: Dict[str, object], decision: Dict[str, object]) -> Dict[str, object]`
  - `validate_evidence_pack(pack: Dict[str, object], forbidden_values: List[str]) -> None`
  - `write_evidence_pack(output_dir: Path, pack: Dict[str, object]) -> Dict[str, object]`
  - `generate_pilot_evidence(repo_root: Path, work_dir: Path, output_dir: Path = None, now: datetime = None) -> Dict[str, object]`.

- [x] **Step 1: Write failing run-evidence allowlist and leakage tests**

Create `tests/test_controlled_lark_pilot_evidence.py` with synthetic full state that includes forbidden raw values and audit that includes only compact connector metadata:

```python
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.controlled_lark_pilot_evidence import (
    build_acceptance_summary,
    build_run_evidence,
    validate_evidence_pack,
    write_evidence_pack,
)


class ControlledLarkPilotEvidenceTests(TestCase):
    def test_build_run_evidence_uses_exact_allowlist(self):
        run = {
            "run_id": "run_001",
            "workflow_id": "workflow_controlled_lark_pilot",
            "workflow_version": "0.1.0",
            "status": "completed",
            "context": {
                "input": {
                    "pilot_case_id": "case-001",
                    "account_name": "Private Account",
                    "renewal_risk": "Private Risk",
                    "owner_open_id": "ou_private",
                    "due_at": "2026-08-15T09:00:00Z",
                }
            },
            "node_results": {"create_lark_task": {"output": {}}},
        }
        audit = [
            {
                "type": "run_started",
                "run_id": "run_001",
                "timestamp": "2026-07-18T01:00:00+00:00",
            },
            {
                "type": "run_resumed",
                "run_id": "run_001",
                "approved": True,
                "timestamp": "2026-07-18T01:01:00+00:00",
            },
            {
                "type": "connector_completed",
                "run_id": "run_001",
                "node_id": "create_lark_task",
                "connector_id": "lark_task",
                "connector_status": "completed",
                "credential_status": "resolved",
                "credential_handles": ["lark_bot_access_token"],
                "connector_metadata": {
                    "operation": "create_task",
                    "mode": "live",
                    "provider_status": "completed",
                    "task_title_present": True,
                    "task_description_present": True,
                    "assignee_present": True,
                    "due_at_present": True,
                    "idempotency_key_present": True,
                    "lark_task_id_present": True,
                },
                "timestamp": "2026-07-18T01:01:01+00:00",
            },
            {
                "type": "run_completed",
                "run_id": "run_001",
                "timestamp": "2026-07-18T01:01:02+00:00",
            },
        ]

        evidence = build_run_evidence(run, audit)

        self.assertEqual(evidence["run_id"], "run_001")
        self.assertEqual(evidence["gate_decision"], "approved")
        self.assertEqual(evidence["provider_status"], "completed")
        self.assertTrue(evidence["case_id_present"])
        encoded = json.dumps(evidence)
        for forbidden in (
            "case-001", "Private Account", "Private Risk", "ou_private",
            "2026-08-15T09:00:00Z"
        ):
            self.assertNotIn(forbidden, encoded)
```

Add rejection coverage that expects `gate_decision: rejected`, `connector_invoked: false`, and empty connector status fields.

- [x] **Step 2: Write failing five-day aggregation and atomic-write tests**

Use five synthetic redacted records with `completed_at` values on July 18–22 in `Asia/Shanghai`; supply only the already-counted private-case cardinality, and assert:

```python
summary = build_acceptance_summary(
    charter=_valid_charter(),
    runs=approved_runs + [rejected_run],
    distinct_private_cases=2,
    exercises={"failure": {"passed": True}, "rollback": {"passed": True}},
    verification={"all_passed": True},
    decision={
        "decision": "continue",
        "partner_acknowledged": True,
        "operator_acknowledged": True,
        "commercial_engagement_confirmed": True,
        "rationale": "The controlled workflow delivered the agreed result.",
    },
)
self.assertTrue(summary["ready_to_finalize"])
self.assertEqual(summary["approved_live_runs"], 5)
self.assertEqual(summary["distinct_calendar_days"], 5)
self.assertEqual(summary["distinct_private_cases"], 2)
self.assertEqual(summary["rejected_runs"], 1)
self.assertEqual(summary["unmet_conditions"], [])
```

For atomic writing:

```python
with TemporaryDirectory() as tmp:
    output = Path(tmp) / "evidence"
    first = write_evidence_pack(output, pack)
    second = write_evidence_pack(output, pack)
    self.assertEqual(first["file_count"], second["file_count"])
    self.assertFalse(any(path.name.endswith(".tmp") for path in output.rglob("*")))
```

- [x] **Step 3: Run evidence tests and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_controlled_lark_pilot_evidence -v
```

Expected: import failure because the evidence module does not exist.

- [x] **Step 4: Implement pure run evidence and acceptance aggregation**

Create the new module with exact allowlisted keys:

```python
RUN_EVIDENCE_KEYS = {
    "schema_version",
    "run_id",
    "workflow_id",
    "workflow_version",
    "started_at",
    "completed_at",
    "run_status",
    "gate_decision",
    "case_id_present",
    "connector_invoked",
    "connector_id",
    "connector_status",
    "credential_status",
    "credential_handles",
    "operation",
    "mode",
    "provider_status",
    "task_title_present",
    "task_description_present",
    "assignee_present",
    "due_at_present",
    "idempotency_key_present",
    "lark_task_id_present",
}


def build_run_evidence(run, audit_events):
    resumed = _last_event(audit_events, "run_resumed")
    connector = _last_connector_event(audit_events)
    metadata = connector.get("connector_metadata", {}) if connector else {}
    if not isinstance(metadata, dict):
        metadata = {}
    trigger_input = run.get("context", {}).get("input", {})
    if not isinstance(trigger_input, dict):
        trigger_input = {}
    evidence = {
        "schema_version": "controlled-lark-pilot-evidence-0.1.0",
        "run_id": str(run.get("run_id", "")),
        "workflow_id": str(run.get("workflow_id", "")),
        "workflow_version": str(run.get("workflow_version", "")),
        "started_at": str(_first_event(audit_events, "run_started").get("timestamp", "")),
        "completed_at": str(_terminal_event(audit_events).get("timestamp", "")),
        "run_status": str(run.get("status", "")),
        "gate_decision": (
            "approved" if resumed.get("approved") is True
            else "rejected" if resumed.get("approved") is False
            else "pending"
        ),
        "case_id_present": bool(str(trigger_input.get("pilot_case_id", "")).strip()),
        "connector_invoked": bool(connector),
        "connector_id": str(connector.get("connector_id", "")) if connector else "",
        "connector_status": str(connector.get("connector_status", "")) if connector else "",
        "credential_status": str(connector.get("credential_status", "")) if connector else "",
        "credential_handles": list(connector.get("credential_handles", [])) if connector else [],
        "operation": str(metadata.get("operation", "")),
        "mode": str(metadata.get("mode", "")),
        "provider_status": str(metadata.get("provider_status", "")),
        "task_title_present": bool(metadata.get("task_title_present")),
        "task_description_present": bool(metadata.get("task_description_present")),
        "assignee_present": bool(metadata.get("assignee_present")),
        "due_at_present": bool(metadata.get("due_at_present")),
        "idempotency_key_present": bool(metadata.get("idempotency_key_present")),
        "lark_task_id_present": bool(metadata.get("lark_task_id_present")),
    }
    if set(evidence) != RUN_EVIDENCE_KEYS:
        raise ValueError("run evidence keys do not match the allowlist")
    return evidence
```

Implement `_first_event`, `_last_event`, `_last_connector_event`, and `_terminal_event` as small deterministic scans over dictionaries only. `build_acceptance_summary` must:

- count an approved live run only when workflow id/version, `gate_decision`, terminal run status, case-id presence, connector invocation/id/status, credential status/sole handle, operation, mode, provider status, all mapped-input presence flags, idempotency presence, and task-id presence exactly match the controlled success contract;
- convert `completed_at` into `Asia/Shanghai` dates with `zoneinfo.ZoneInfo`;
- accept only an integer distinct-case count derived by the private orchestrator; never accept or retain raw case ids in the evidence module;
- require at least one terminal rejected/failed run with `gate_decision == "rejected"` and `connector_invoked == false`;
- require both exercises, complete verification, valid decision, both acknowledgements, and commercial confirmation;
- return every failed predicate as a stable string in `unmet_conditions`.

- [x] **Step 5: Implement evidence validation and atomic per-file replacement**

Use a fixed output map and `os.replace`:

```python
def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(temporary), str(path))


def validate_evidence_pack(pack, forbidden_values):
    encoded = json.dumps(pack, ensure_ascii=False, sort_keys=True)
    leaf_strings = _all_string_leaves(pack)
    for value in forbidden_values:
        if not isinstance(value, str) or not value:
            continue
        if (len(value) >= 4 and value in encoded) or value in leaf_strings:
            raise ValueError("evidence pack contains a forbidden private value")
    for run in pack.get("runs", []):
        if set(run) != RUN_EVIDENCE_KEYS:
            raise ValueError("run evidence keys do not match the allowlist")


def write_evidence_pack(output_dir, pack):
    output_dir = Path(output_dir)
    files = {
        output_dir / "pilot-charter.json": pack["charter"],
        output_dir / "evidence-index.json": pack["index"],
    }
    for sequence, run in enumerate(pack["runs"], start=1):
        files[output_dir / "runs" / f"{sequence:03d}.json"] = run
    for name, exercise in sorted(pack.get("exercises", {}).items()):
        files[output_dir / "exercises" / f"{name}.json"] = exercise
    if pack.get("verification"):
        files[output_dir / "verification.json"] = pack["verification"]
    if pack.get("decision"):
        files[output_dir / "decision.json"] = pack["decision"]
    for path, value in files.items():
        _write_json_atomic(path, value)
    _remove_stale_json_files(output_dir, set(files))
    return {"status": "written", "file_count": len(files), "output_dir": str(output_dir)}
```

Define `_all_string_leaves` as a recursive read-only traversal of dictionaries and lists. Define exact key allowlists for the charter, evidence index, each exercise kind, verification command/result, decision, and top-level pack as well as for runs. `validate_evidence_pack` must reject an unknown or missing key, a wrong primitive/container type, a non-allowlisted credential handle, a non-fixed workflow/connector/operation/mode identity, or a forbidden value anywhere in the encoded pack. Add one negative test per artifact category that inserts an extra raw-looking field and expects fail-closed validation.

`_remove_stale_json_files` may delete only `.json` descendants of the exact `output_dir` passed to it that are absent from the new fixed map. Before scanning, it must reject a filesystem root, an existing symlink, or any path containing a symlink component. This writer never decides whether a repository export path is authorized.

- [x] **Step 6: Implement orchestration from private SQLite state**

In `controlled_lark_pilot.py`, add the exact public signature and one private in-memory builder shared with finalization:

```python
def generate_pilot_evidence(
    repo_root: Path,
    work_dir: Path,
    output_dir: Path = None,
    now: datetime = None,
) -> Dict[str, object]:
```

```python
def _build_pilot_evidence(
    repo_root: Path,
    work_dir: Path,
    decision_override: Dict[str, object] = None,
    now: datetime = None,
) -> Dict[str, object]:
```

Implement it so that it:

1. loads the valid charter;
2. constructs the SQLite control plane with an empty credential provider;
3. lists runs, loads each full run, filters only the controlled workflow id/version, and sorts them deterministically by authoritative start timestamp then run id;
4. builds redacted run evidence and gathers private case ids in memory only for runs that qualify as approved live completions;
5. discards the raw case-id set immediately after calculating its cardinality;
6. derives `exercises/rejection.json` from the first qualifying human-rejected run in that stable order, with only exercise name, passed boolean, run id, gate decision, and connector-invoked boolean;
7. loads optional private failure, rollback, verification, and decision JSON;
8. gathers every string value from private run `context.input` plus any currently injected token into `forbidden_values`;
9. passes only the distinct-case integer to `build_acceptance_summary` and records an explicit `generated_at` derived from `now` in the evidence index;
10. builds and validates the pack;
11. defaults output exactly to `work_dir/evidence`;
12. permits an explicit repository-contained output only after `private/finalization.json` records a successful finalization and only when the resolved path equals `repo_root/docs/pilot-evidence/loop-40`; rejects every other repository-contained output;
13. writes the validated pack and returns only status, counts, unmet conditions, and the output directory.

- [x] **Step 7: Run evidence and controlled tests and verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_controlled_lark_pilot_evidence tests.test_controlled_lark_pilot -v
```

Expected: all tests pass; encoded evidence contains no synthetic private values.

- [x] **Step 8: Commit the evidence boundary**

```bash
git add src/skill2workflow/controlled_lark_pilot.py src/skill2workflow/controlled_lark_pilot_evidence.py tests/test_controlled_lark_pilot.py tests/test_controlled_lark_pilot_evidence.py
git commit -m "feat: add redacted controlled pilot evidence"
```

---

### Task 6: Safe Exercises, Fixed Verification, And Finalization

**Files:**
- Modify: `tests/test_controlled_lark_pilot.py`
- Modify: `tests/test_controlled_lark_pilot_evidence.py`
- Modify: `src/skill2workflow/controlled_lark_pilot.py`
- Modify: `src/skill2workflow/controlled_lark_pilot_evidence.py`

**Interfaces:**
- Produces:
  - `exercise_disabled_live(repo_root: Path, work_dir: Path, now: datetime = None) -> Dict[str, object]`
  - `exercise_rollback(repo_root: Path, work_dir: Path, now: datetime = None) -> Dict[str, object]`
  - `verify_pilot(repo_root: Path, work_dir: Path, command_runner=None) -> Dict[str, object]`
  - `finalize_pilot(repo_root: Path, work_dir: Path, decision: Dict[str, object], output_dir: Path = None, now: datetime = None) -> Dict[str, object]`.

- [x] **Step 1: Write failing disabled-live and rollback exercise tests**

Use a credential spy whose `resolve()` records calls and a transport spy. Assert that `exercise_disabled_live` returns exactly:

```python
{
    "exercise": "disabled_live",
    "passed": True,
    "provider_status": "live_disabled",
    "credential_resolution_attempted": False,
    "transport_attempted": False,
}
```

Assert the private exercise file exists at `private/exercises/failure.json` and contains no synthetic input values.

For rollback, clear both live environment variables, run the helper, and assert:

```python
self.assertEqual(result["exercise"], "rollback")
self.assertTrue(result["passed"])
self.assertEqual(result["live_switch_enabled"], False)
self.assertEqual(result["live_approval_blocked"], True)
self.assertEqual(result["dry_run_status"], "completed")
```

- [x] **Step 2: Write failing fixed-verification tests**

Inject a fake runner that records argument arrays. Assert:

```python
result = verify_pilot(ROOT, work_dir, command_runner=fake_runner)
self.assertTrue(result["all_passed"])
self.assertEqual(
    [item["id"] for item in result["commands"]],
    [
        "focused-tests",
        "full-tests",
        "compile",
        "secret-hygiene",
        "connector-smoke",
        "dry-run-pilot-smoke",
        "diff-check",
    ],
)
self.assertNotIn("LARK_BOT_ACCESS_TOKEN", fake_runner.environments[0])
self.assertNotIn("SKILL2WORKFLOW_LARK_TASK_LIVE", fake_runner.environments[0])
```

The verification result may contain command ids, exit codes, and durations only; it must not persist stdout/stderr.

- [x] **Step 3: Write failing finalization tests**

Build an incomplete pack and assert `finalize_pilot` raises with the stable unmet condition list. Build a complete synthetic pack and decision:

```python
decision = {
    "schema_version": "controlled-lark-pilot-decision-0.1.0",
    "decision": "continue",
    "partner_acknowledged": True,
    "operator_acknowledged": True,
    "commercial_engagement_confirmed": True,
    "rationale": "The controlled workflow delivered the agreed business result.",
}
```

Use a fully temporary synthetic repository root and work directory for export tests; never write test evidence into the checkout. Assert invalid decision values, false acknowledgements, false commercial status, empty rationale, and rationale containing any private case value fail before export. For every failure, assert `private/finalization.json` and the requested repository export are absent. For a complete case, assert both the private evidence pack and requested exact repository export are byte-for-byte equivalent JSON maps, the owner-only finalization marker exists, and a subsequent `generate_pilot_evidence` may replace only that exact repository target. Also assert any other repository-contained output path fails closed.

- [x] **Step 4: Run exercise/finalization tests and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_controlled_lark_pilot tests.test_controlled_lark_pilot_evidence -v
```

Expected: failures because exercise, verification, and finalization functions do not exist.

- [x] **Step 5: Implement disabled-live exercise with spies**

Build a synthetic private case inside the private work directory, start the normal controlled workflow, and ensure the live switch is absent for the exercise. Construct the control plane with a connector wrapper that records transport access and a credential provider that records `resolve()` calls, then call `LocalControlPlane.resume_published_run` directly; do not call `decide_pilot_run`, whose operator guard intentionally rejects the missing switch before the connector boundary is exercised. Persist only the exact compact result above. The exercise passes only when:

```python
passed = (
    provider_status == "live_disabled"
    and credential_resolution_attempted is False
    and transport_attempted is False
)
```

The exercise must restore the caller's environment after execution.

- [x] **Step 6: Implement rollback through a blocked live approval and the unchanged dry-run helper**

With both live environment variables removed, start a fresh synthetic private controlled case and run this exact guard probe with a transport spy:

```python
live_approval_blocked = False
try:
    decide_pilot_run(
        repo_root,
        work_dir,
        started["run_id"],
        approved=True,
        confirmed_live=True,
        now=now,
        transport=transport_spy,
    )
except ValueError as error:
    live_approval_blocked = str(error) == "SKILL2WORKFLOW_LARK_TASK_LIVE=1 is required"
if not live_approval_blocked or transport_spy.calls:
    raise ValueError("rollback did not prove the disabled live boundary")
```

Leave that run waiting as historical proof. Then call:

```python
from .lark_task_pilot import run_lark_task_pilot

dry_run = run_lark_task_pilot(
    repo_root=repo_root,
    work_dir=work_dir / "private" / "rollback-dry-run",
    reset=True,
)
result = {
    "exercise": "rollback",
    "passed": live_approval_blocked and dry_run.get("run_status") == "completed",
    "live_switch_enabled": os.environ.get(LIVE_SWITCH) == "1",
    "live_approval_blocked": live_approval_blocked,
    "dry_run_status": str(dry_run.get("run_status", "")),
}
```

The public rollback command must fail before this helper if the live switch is still exactly `1`; the operator removes it, then runs the exercise.

- [x] **Step 7: Implement the fixed offline verification command set**

Use exact argument arrays, `cwd=repo_root`, a sanitized environment with both live variables removed, and `capture_output=True`. The fixed commands are:

```python
commands = [
    ("focused-tests", [python, "-m", "unittest", "tests.test_controlled_lark_pilot", "tests.test_controlled_lark_pilot_evidence", "tests.test_controlled_lark_pilot_docs", "-v"]),
    ("full-tests", [python, "-m", "unittest", "discover", "-s", "tests", "-v"]),
    ("compile", [python, "-m", "py_compile", *sorted_source_files, connector_file]),
    ("secret-hygiene", [python, "scripts/secret_hygiene.py", "examples/workflows"]),
    ("connector-smoke", [python, "scripts/lark_task_connector_smoke.py", "--work-dir", str(work_dir / "private" / "connector-smoke")]),
    ("dry-run-pilot-smoke", [python, "scripts/lark_task_pilot_smoke.py", "--work-dir", str(work_dir / "private" / "dry-run-smoke")]),
    ("diff-check", ["git", "diff", "--check"]),
]
```

Set `PYTHONPATH=src` in the sanitized environment for Python commands. Persist one compact record per command with `id`, `exit_code`, and `passed`. Set `all_passed` only when every exit code is zero.

- [x] **Step 8: Implement fail-closed finalization and safe export**

Validate the decision exact schema and allowlisted keys. Pass it as `decision_override` to `_build_pilot_evidence` without first persisting it, require `ready_to_finalize: true`, and validate the complete candidate pack against all private values. Always atomically replace the private derived pack in `work_dir/evidence`; when `output_dir` is provided, also require that any repository-contained destination resolves exactly to `repo_root/docs/pilot-evidence/loop-40` before writing the same validated pack there. Only after every requested write succeeds, atomically persist `private/decision.json` and an owner-only `private/finalization.json` marker with exact keys `schema_version`, `finalized`, `decision`, and `finalized_at`. Ordinary `generate_pilot_evidence` may subsequently regenerate the repository export only when that marker is valid. A failed candidate or write leaves no finalization marker and never advances the Roadmap.

The return value is:

```python
{
    "status": "finalized",
    "decision": decision["decision"],
    "approved_live_runs": index["approved_live_runs"],
    "distinct_calendar_days": index["distinct_calendar_days"],
    "distinct_private_cases": index["distinct_private_cases"],
    "rejected_runs": index["rejected_runs"],
    "output_dir": str(output_dir or (work_dir / "evidence")),
}
```

- [x] **Step 9: Run focused tests and verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_controlled_lark_pilot tests.test_controlled_lark_pilot_evidence -v
```

Expected: all exercise, verification, finalization, and leakage tests pass.

- [x] **Step 10: Commit exercises and finalization**

```bash
git add src/skill2workflow/controlled_lark_pilot.py src/skill2workflow/controlled_lark_pilot_evidence.py tests/test_controlled_lark_pilot.py tests/test_controlled_lark_pilot_evidence.py
git commit -m "feat: finalize controlled lark pilot evidence"
```

---

### Task 7: Operator CLI And Controlled Pilot Runbook

**Files:**
- Create: `scripts/controlled_lark_pilot.py`
- Create: `docs/controlled-live-pilot.md`
- Create: `tests/test_controlled_lark_pilot_docs.py`
- Modify: `docs/connectors.md`
- Modify: `docs/examples.md`
- Modify: `README.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: all Task 2–6 public functions.
- Produces: `main(argv=None) -> int` with `init`, `start`, `decide`, `evidence`, `exercise-failure`, `exercise-rollback`, `verify`, and `finalize` subcommands; one complete operator runbook.

- [x] **Step 1: Write failing CLI and documentation contract tests**

Create tests that assert:

```python
def test_controlled_pilot_runbook_documents_every_safe_phase(self):
    runbook = (ROOT / "docs" / "controlled-live-pilot.md").read_text(encoding="utf-8")
    for command in (
        " init ",
        " start ",
        " decide ",
        " evidence ",
        " exercise-failure ",
        " exercise-rollback ",
        " verify ",
        " finalize ",
    ):
        self.assertIn(command, runbook)
    self.assertIn("vibe vault run --env LARK_BOT_ACCESS_TOKEN", runbook)
    self.assertIn("chmod 600", runbook)
    self.assertIn("five distinct calendar days", runbook)
    self.assertIn("must not advance Loop 40", runbook)


def test_docs_preserve_dry_run_and_narrow_live_boundaries(self):
    connectors = (ROOT / "docs" / "connectors.md").read_text(encoding="utf-8")
    examples = (ROOT / "docs" / "examples.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    self.assertIn("docs/controlled-live-pilot.md", connectors)
    self.assertIn("dry-run remains the default", connectors)
    self.assertIn("controlled real-team pilot", examples)
    self.assertIn("Loop 40", readme)
    self.assertIn("Current maturity: Local Evaluation", readme)
```

Add CLI parser tests that call the complete safe argument lists below, capture stdout, and assert it is compact JSON without raw values:

```python
init_args = [
    "init",
    "--work-dir", str(work_dir),
    "--starts-on", "2026-07-18",
    "--expires-on", "2026-08-15",
    "--confirm-team-consent",
    "--confirm-assignee-consent",
    "--confirm-commercial-engagement",
]
reject_args = [
    "decide",
    "--work-dir", str(work_dir),
    "--run-id", started["run_id"],
    "--reject",
]
self.assertEqual(main(init_args), 0)
self.assertEqual(main(reject_args), 0)
```

- [x] **Step 2: Run CLI/docs tests and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_controlled_lark_pilot_docs -v
```

Expected: failure because the script and runbook do not exist.

- [x] **Step 3: Implement the thin CLI wrapper**

The wrapper adds `src` to `sys.path` exactly like existing scripts and imports `main` from `skill2workflow.controlled_lark_pilot`. In the module, build subparsers with these safe inputs:

```text
init --work-dir PATH --starts-on YYYY-MM-DD --expires-on YYYY-MM-DD
     --confirm-team-consent --confirm-assignee-consent --confirm-commercial-engagement
start --work-dir PATH --input PATH
decide --work-dir PATH --run-id RUN_ID (--approve | --reject) [--confirm-live-create]
evidence --work-dir PATH [--output-dir PATH]
exercise-failure --work-dir PATH
exercise-rollback --work-dir PATH
verify --work-dir PATH
finalize --work-dir PATH --decision-file PATH [--output-dir PATH]
```

`init` constructs the exact fixed charter in code; it accepts no customer or commercial details. `decide --approve` is the only phase that reads the injected token. `--reject` must reject `--confirm-live-create` as unnecessary. `finalize` reads a redacted decision JSON file; it does not accept the rationale on the command line.

Every successful command prints one compact JSON summary. Every expected operator error exits nonzero with fixed text that does not contain private input.

- [x] **Step 4: Write the full operator runbook**

Document:

- the paid assisted engagement and consent prerequisite;
- private directory creation outside the repository;
- exact charter initialization command;
- the approved private case JSON schema;
- `chmod 600` before `start`;
- inspection of the waiting run before a decision;
- Vault injection for approval only;
- rejection without Vault;
- evidence regeneration after every run;
- five approved runs across five `Asia/Shanghai` dates and two opaque case ids;
- disabled-live failure and rollback exercises;
- sanitized fixed verification;
- redacted decision-file schema;
- finalization and export to `docs/pilot-evidence/loop-40` only after every gate passes;
- token rotation/deletion after the pilot;
- incident stop conditions and `defer` behavior;
- the explicit statement that implementation readiness must not advance Loop 40.

- [x] **Step 5: Link the runbook without advancing maturity**

Add the script command to `AGENTS.md`, a narrow link in `docs/connectors.md`, a dry-run/live distinction in `docs/examples.md`, and one runbook link in `README.md`. Keep these exact status statements unchanged:

```text
Current maturity: Local Evaluation
Completed delivery loops: 1-39
Active loop: Loop 40, Controlled Live Connector Pilot
```

- [x] **Step 6: Run CLI/docs and Roadmap tests and verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_controlled_lark_pilot_docs tests.test_production_roadmap tests.test_product_connector_pilot_roadmap tests.test_first_product_connector_candidate_docs -v
```

Expected: all pass; Loop 40 remains active and incomplete.

- [x] **Step 7: Commit CLI and runbook**

```bash
git add AGENTS.md README.md docs/connectors.md docs/examples.md docs/controlled-live-pilot.md scripts/controlled_lark_pilot.py src/skill2workflow/controlled_lark_pilot.py tests/test_controlled_lark_pilot_docs.py
git commit -m "docs: add controlled lark pilot runbook"
```

---

### Task 8: Offline Implementation Verification And Review Gate

**Files:**
- Modify: `docs/superpowers/plans/2026-07-17-controlled-live-pilot.md`

**Interfaces:**
- Consumes: Tasks 1–7.
- Produces: implementation-ready controlled Pilot tooling with no claim of real-pilot completion.

- [x] **Step 1: Run all focused controlled-pilot tests**

```bash
PYTHONPATH=src python3 -m unittest tests.test_controlled_lark_pilot tests.test_controlled_lark_pilot_evidence tests.test_controlled_lark_pilot_docs tests.test_lark_task_pilot tests.test_lark_task_connector tests.test_lark_task_live_validation -v
```

Expected: all pass.

- [x] **Step 2: Run the full test suite in an environment that permits local loopback ports**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: all tests pass. If the sandbox blocks `127.0.0.1` binding, rerun the identical command with the required sandbox escalation; do not reinterpret permission errors as code failures.

- [x] **Step 3: Run complete offline safety verification**

```bash
python3 -m py_compile src/skill2workflow/*.py examples/connectors/lark_task_connector.py
python3 scripts/secret_hygiene.py examples/workflows
python3 scripts/lark_task_connector_smoke.py --work-dir /tmp/skill2workflow-lark-task-connector
python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot
git diff --check
```

Expected: every command exits 0; no live provider call occurs.

- [x] **Step 4: Run final code review**

Use `superpowers:requesting-code-review`. Review against the approved design, with special attention to:

- approval never auto-runs;
- token boundary and error redaction;
- private directory rejection and permissions;
- evidence exact allowlist;
- repeated terminal decision suppression;
- exercise truthfulness;
- incomplete evidence failing finalization;
- Roadmap remaining at Local Evaluation.

Expected: no unresolved critical, important, or minor finding.

- [x] **Step 5: Record implementation readiness without advancing Loop 40**

Check Tasks 1–8 in this plan and add a dated verification note containing only command names, pass/fail status, and test count. State explicitly:

```text
Controlled Pilot tooling is implementation-ready. Loop 40 remains incomplete until the five-day paid real-team evidence gate finalizes.
```

- [x] **Step 6: Commit the implementation verification record**

```bash
git add docs/superpowers/plans/2026-07-17-controlled-live-pilot.md
git commit -m "docs: verify controlled pilot tooling"
```

#### Verification note — 2026-07-20

| Command | Status | Test count |
|---|---|---:|
| `expanded-focused-tests` | PASS | 174/174 |
| `full-tests` | PASS | 319/319 |
| `compile` | PASS | 33 files |
| `secret-hygiene` | PASS | 12 fixtures, 0 findings |
| `connector-smoke` | PASS | 1 |
| `dry-run-pilot-smoke` | PASS | 1 |
| `diff-check` | PASS | — |
| `controlled-pilot-verify` | PASS | 7/7 |

Controlled Pilot tooling is implementation-ready. Loop 40 remains incomplete until the five-day paid real-team evidence gate finalizes.

---

### Task 9: Initialize The Paid Pilot And Complete Day 1 Controls

**Files:**
- Private only: `$HOME/.local/share/skill2workflow/pilots/loop-40/`
- No repository evidence is committed in this task.

**Interfaces:**
- Consumes: one consenting paid/contracted partner, Vault credential, assignee consent, real private case file.
- Produces: valid charter, dry-run rehearsal, one approved live run, one rejected run, failure exercise, rollback exercise, and private redacted evidence.

- [ ] **Step 1: Initialize the private charter**

Run with the approved engagement window of 2026-07-18 through 2026-08-15:

```bash
python3 scripts/controlled_lark_pilot.py init \
  --work-dir "$HOME/.local/share/skill2workflow/pilots/loop-40" \
  --starts-on 2026-07-18 \
  --expires-on 2026-08-15 \
  --confirm-team-consent \
  --confirm-assignee-consent \
  --confirm-commercial-engagement
```

Expected: `status: initialized`, three confirmation booleans true, and no partner identity or commercial terms in stdout or the charter.

- [ ] **Step 2: Run the unchanged dry-run rehearsal**

```bash
python3 scripts/lark_task_pilot_smoke.py \
  --work-dir "$HOME/.local/share/skill2workflow/pilots/loop-40/private/rehearsal"
```

Expected: `run_status: completed`, `mode: dry_run`.

- [ ] **Step 3: Prepare the first private real case file**

Create `$HOME/.local/share/skill2workflow/pilots/loop-40/private/cases/day-1.json` with real partner-approved values that validate against this exact schema:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["pilot_case_id", "account_name", "renewal_risk", "owner_open_id", "due_at"],
  "properties": {
    "pilot_case_id": {"type": "string", "const": "case-001"},
    "account_name": {"type": "string", "minLength": 1},
    "renewal_risk": {"type": "string", "minLength": 1},
    "owner_open_id": {"type": "string", "minLength": 1},
    "due_at": {"type": "string", "format": "date-time"}
  }
}
```

Enter the four private business values only in that owner-controlled file, never in the repository or terminal command. Then run:

```bash
chmod 600 "$HOME/.local/share/skill2workflow/pilots/loop-40/private/cases/day-1.json"
python3 scripts/controlled_lark_pilot.py start \
  --work-dir "$HOME/.local/share/skill2workflow/pilots/loop-40" \
  --input "$HOME/.local/share/skill2workflow/pilots/loop-40/private/cases/day-1.json"
```

Expected: a compact waiting summary. Record the returned run id privately as `DAY1_RUN_ID`.

- [ ] **Step 4: Inspect and explicitly approve the first waiting run**

Only after the designated operator confirms the waiting run:

```bash
vibe vault run --env LARK_BOT_ACCESS_TOKEN -- \
  env SKILL2WORKFLOW_LARK_TASK_LIVE=1 \
  python3 scripts/controlled_lark_pilot.py decide \
    --work-dir "$HOME/.local/share/skill2workflow/pilots/loop-40" \
    --run-id "$DAY1_RUN_ID" \
    --approve \
    --confirm-live-create
```

Expected: `run_status: completed`, `provider_status: completed`, and `lark_task_id_present: true`, with no task value or id.

- [ ] **Step 5: Complete the human rejection evidence**

Create `$HOME/.local/share/skill2workflow/pilots/loop-40/private/cases/rejection.json` from the same exact schema as Step 3, using opaque id `case-rejection-001` and partner-approved private values. Protect it, start it, inspect the waiting summary, and record the returned run id privately as `REJECTION_RUN_ID`:

```bash
chmod 600 "$HOME/.local/share/skill2workflow/pilots/loop-40/private/cases/rejection.json"
python3 scripts/controlled_lark_pilot.py start \
  --work-dir "$HOME/.local/share/skill2workflow/pilots/loop-40" \
  --input "$HOME/.local/share/skill2workflow/pilots/loop-40/private/cases/rejection.json"
```

Reject that waiting run without Vault:

```bash
python3 scripts/controlled_lark_pilot.py decide \
  --work-dir "$HOME/.local/share/skill2workflow/pilots/loop-40" \
  --run-id "$REJECTION_RUN_ID" \
  --reject
```

Expected: `gate_decision: rejected`, `connector_invoked: false`, and no Lark connector event.

- [ ] **Step 6: Complete disabled-live failure and rollback exercises**

Run without either live environment variable:

```bash
env -u SKILL2WORKFLOW_LARK_TASK_LIVE -u LARK_BOT_ACCESS_TOKEN \
  python3 scripts/controlled_lark_pilot.py exercise-failure \
    --work-dir "$HOME/.local/share/skill2workflow/pilots/loop-40"

env -u SKILL2WORKFLOW_LARK_TASK_LIVE -u LARK_BOT_ACCESS_TOKEN \
  python3 scripts/controlled_lark_pilot.py exercise-rollback \
    --work-dir "$HOME/.local/share/skill2workflow/pilots/loop-40"
```

Expected: both exercises report `passed: true`; failure reports no credential or transport access; rollback reports live approval blocked and dry-run completed.

- [ ] **Step 7: Regenerate and inspect private redacted evidence**

```bash
python3 scripts/controlled_lark_pilot.py evidence \
  --work-dir "$HOME/.local/share/skill2workflow/pilots/loop-40"
```

Expected: one approved live run, one rejection, both exercises passing, and unmet conditions for the remaining dates/runs, verification, and final decision. Do not commit the incomplete pack.

---

### Task 10: Complete Approved Runs On Days 2–5

**Files:**
- Private only: `$HOME/.local/share/skill2workflow/pilots/loop-40/`
- No repository evidence is committed until Task 11 finalization.

**Interfaces:**
- Consumes: Task 9 private state, the same approved workflow version, continuing paid engagement, and real partner-approved inputs.
- Produces: five total approved live runs across five `Asia/Shanghai` dates and at least two opaque case ids.

- [ ] **Step 1: Complete Day 2 approved run**

Create an owner-only private file with opaque id `case-001`, start it, inspect the waiting run, approve it through Vault, and regenerate evidence using the exact Task 9 commands with `day-2.json` and the returned Day 2 run id.

Expected evidence: `approved_live_runs: 2`, `distinct_calendar_days: 2`, `distinct_private_cases: 1`.

- [ ] **Step 2: Complete Day 3 approved run**

Repeat on a third `Asia/Shanghai` calendar date with opaque id `case-001`.

Expected evidence: `approved_live_runs: 3`, `distinct_calendar_days: 3`, `distinct_private_cases: 1`.

- [ ] **Step 3: Complete Day 4 approved run with the second private case**

Repeat on a fourth date using opaque id `case-002` and real partner-approved values.

Expected evidence: `approved_live_runs: 4`, `distinct_calendar_days: 4`, `distinct_private_cases: 2`.

- [ ] **Step 4: Complete Day 5 approved run**

Repeat on a fifth date using either `case-001` or `case-002`.

Expected evidence: `approved_live_runs: 5`, `distinct_calendar_days: 5`, `distinct_private_cases: 2`, `rejected_runs >= 1`.

- [ ] **Step 5: Stop immediately on a redaction, duplicate, permission, or provider anomaly**

If any run exposes a forbidden value, creates an unexpected duplicate, targets the wrong user, bypasses the gate, or produces non-normalized provider output:

1. remove the exact live switch;
2. do not run another approval;
3. retain private state;
4. record a `defer` candidate decision;
5. return to implementation with a failing regression test.

Do not replace failed historical runs with clean runs.

---

### Task 11: Verify, Finalize, Export Evidence, And Advance The Roadmap

**Files:**
- Generate: `docs/pilot-evidence/loop-40/pilot-charter.json`
- Generate: one sequential JSON file below `docs/pilot-evidence/loop-40/runs/` for every recorded controlled run
- Generate: `docs/pilot-evidence/loop-40/exercises/rejection.json`
- Generate: `docs/pilot-evidence/loop-40/exercises/failure.json`
- Generate: `docs/pilot-evidence/loop-40/exercises/rollback.json`
- Generate: `docs/pilot-evidence/loop-40/verification.json`
- Generate: `docs/pilot-evidence/loop-40/evidence-index.json`
- Generate: `docs/pilot-evidence/loop-40/decision.json`
- Modify: `ROADMAP.md`
- Modify: `README.md`
- Modify: `tests/test_production_roadmap.py`
- Modify: `tests/test_product_connector_pilot_roadmap.py`
- Modify: `tests/test_first_product_connector_candidate_docs.py`
- Modify: `tests/test_controlled_lark_pilot_docs.py`
- Modify: `docs/superpowers/plans/2026-07-17-controlled-live-pilot.md`

**Interfaces:**
- Consumes: complete private multi-day evidence and partner/operator decision.
- Produces: validated commit-safe Loop 40 evidence, Controlled Live Pilot maturity, and the next Roadmap decision.

- [ ] **Step 1: Run fixed sanitized verification**

```bash
env -u SKILL2WORKFLOW_LARK_TASK_LIVE -u LARK_BOT_ACCESS_TOKEN \
  python3 scripts/controlled_lark_pilot.py verify \
    --work-dir "$HOME/.local/share/skill2workflow/pilots/loop-40"
```

Expected: `all_passed: true` and all seven fixed command ids pass.

- [ ] **Step 2: Prepare the redacted decision file**

Create the owner-only private decision file with the chosen decision and a rationale containing no customer, account, user, task, token, price, or contract detail:

```json
{
  "schema_version": "controlled-lark-pilot-decision-0.1.0",
  "decision": "continue",
  "partner_acknowledged": true,
  "operator_acknowledged": true,
  "commercial_engagement_confirmed": true,
  "rationale": "The controlled workflow delivered the agreed business result within the approved safety boundary."
}
```

`decision` may be `continue`, `harden`, or `defer`; do not force `continue` if evidence supports another outcome.

- [ ] **Step 3: Finalize and export the validated pack**

```bash
chmod 600 "$HOME/.local/share/skill2workflow/pilots/loop-40/private/decision.json"
python3 scripts/controlled_lark_pilot.py finalize \
  --work-dir "$HOME/.local/share/skill2workflow/pilots/loop-40" \
  --decision-file "$HOME/.local/share/skill2workflow/pilots/loop-40/private/decision.json" \
  --output-dir docs/pilot-evidence/loop-40
```

Expected: `status: finalized`, five approved live runs, five dates, at least two cases, at least one rejection, all exercises and verification passed, and no unmet condition.

- [ ] **Step 4: Run repository secret and forbidden-value checks on exported evidence**

Run the evidence validator plus targeted searches using only known schema keys, never raw private values:

```bash
python3 scripts/controlled_lark_pilot.py evidence \
  --work-dir "$HOME/.local/share/skill2workflow/pilots/loop-40" \
  --output-dir docs/pilot-evidence/loop-40
python3 scripts/secret_hygiene.py examples/workflows
rg -n '"(owner_open_id|account_name|renewal_risk|due_at|client_token|guid|request|response)"[[:space:]]*:' docs/pilot-evidence/loop-40
rg -n 'Authorization|Bearer |LARK_BOT_ACCESS_TOKEN' docs/pilot-evidence/loop-40
```

Expected: validator passes; both `rg` commands return no matches (exit 1). Allowed boolean fields such as `due_at_present` do not match the exact JSON-key check. Schema documentation outside the evidence directory may contain these terms and is not part of this check.

- [ ] **Step 5: Write failing Roadmap completion tests**

Update exact assertions to require:

```text
Completed delivery loops: 1-40
Current maturity: Controlled Live Pilot
Loop 40: Controlled Live Connector Pilot | Complete
docs/pilot-evidence/loop-40/evidence-index.json
docs/pilot-evidence/loop-40/decision.json
```

Require Loop 41 to become `Next` only when the final decision is `continue` or `harden`; if the decision is `defer`, require no active implementation loop and document the defer decision instead.

- [ ] **Step 6: Run Roadmap tests and verify RED**

```bash
PYTHONPATH=src python3 -m unittest tests.test_production_roadmap tests.test_product_connector_pilot_roadmap tests.test_first_product_connector_candidate_docs tests.test_controlled_lark_pilot_docs -v
```

Expected: failures because Roadmap and README still describe Loop 40 as active and Local Evaluation.

- [ ] **Step 7: Advance Roadmap and README from validated evidence only**

In `ROADMAP.md`:

- set completed loops to 1-40;
- set current maturity to Controlled Live Pilot;
- move Loop 40 to Delivery History with links to the runbook, evidence index, exercises, verification, and decision;
- state the recorded final decision;
- select Loop 41 only if the decision permits it;
- keep the fixed live action boundary and all Loop 41–43 exclusions truthful.

In `README.md`, update only the compact maturity and active-loop summary.

- [ ] **Step 8: Run complete final verification**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/skill2workflow/*.py examples/connectors/lark_task_connector.py
python3 scripts/secret_hygiene.py examples/workflows
python3 scripts/lark_task_connector_smoke.py --work-dir /tmp/skill2workflow-lark-task-connector-final
python3 scripts/lark_task_pilot_smoke.py --work-dir /tmp/skill2workflow-lark-task-pilot-final
git diff --check
```

Expected: every command exits 0.

- [ ] **Step 9: Request final code and evidence review**

Use `superpowers:requesting-code-review` to verify the complete spec and evidence map. The reviewer must independently confirm every acceptance condition from committed evidence and must treat missing or indirect evidence as incomplete.

Expected: no unresolved finding and an explicit statement that the Controlled Live Pilot gate is proven.

- [ ] **Step 10: Update this plan's execution record and commit Loop 40 completion**

Check every completed step, add the final test count and review result, then commit:

```bash
git add ROADMAP.md README.md docs/pilot-evidence/loop-40 docs/superpowers/plans/2026-07-17-controlled-live-pilot.md tests/test_production_roadmap.py tests/test_product_connector_pilot_roadmap.py tests/test_first_product_connector_candidate_docs.py tests/test_controlled_lark_pilot_docs.py
git commit -m "docs: complete controlled live pilot"
```

- [ ] **Step 11: Remove or rotate the live credential outside the repository**

Delete the short-lived Vault credential or rotate the bot token according to the partner's security policy. Verify the credential is absent without printing its value. This external action is required for pilot closeout but produces only a boolean operator acknowledgement, never a committed secret record.
