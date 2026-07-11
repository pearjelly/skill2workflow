"""Deterministic local scheduled-trigger smoke helper."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict

from .compiler import validate_workflow
from .control_plane import LocalControlPlane
from .dashboard import build_control_snapshot
from .schedules import LocalScheduleRunner


DEFAULT_WORK_DIR = Path(tempfile.gettempdir()) / "skill2workflow-schedule-loop29"
DEFAULT_NOW = "2026-07-06T00:00:00Z"
DEFAULT_UI_URL = "http://localhost:4173/web/control.html"


def run_schedule_smoke(
    repo_root: Path,
    work_dir: Path = DEFAULT_WORK_DIR,
    now: str = DEFAULT_NOW,
    reset: bool = True,
) -> Dict[str, object]:
    """Publish an example workflow and trigger it through a deterministic local schedule."""
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    if reset:
        _reset_work_dir(repo_root, work_dir)

    artifacts_dir = work_dir / "artifacts"
    state_dir = work_dir / "state"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    source_workflow_path = repo_root / "examples" / "workflows" / "approval-flow.workflow.json"
    workflow = json.loads(source_workflow_path.read_text(encoding="utf-8"))
    errors = validate_workflow(workflow)
    if errors:
        raise ValueError("; ".join(errors))

    workflow_meta = workflow.get("workflow", {})
    if not isinstance(workflow_meta, dict):
        raise ValueError("workflow.workflow must be an object")
    workflow_id = str(workflow_meta.get("id", "workflow"))
    workflow_version = str(workflow_meta.get("version", "0.1.0"))

    control = LocalControlPlane(state_dir)
    control.publish_workflow(workflow)

    schedule = {
        "schema_version": "skill2workflow-schedule-0.1.0",
        "schedule": {
            "id": "schedule_approval_flow_daily",
            "workflow_id": workflow_id,
            "version": workflow_version,
            "run_at": DEFAULT_NOW,
        },
        "trigger": {
            "input": {
                "customer_id": "customer_123",
                "report_date": "2026-07-06",
            }
        },
    }

    runner = LocalScheduleRunner(state_dir)
    stored_schedule = runner.add_schedule(schedule)
    run_due_result = runner.run_due(now)
    if run_due_result["count"] != 1:
        raise ValueError(f"expected exactly one scheduled run, got {run_due_result['count']}")

    run_id = str(run_due_result["runs"][0]["run_id"])
    run_state = control.get_run(run_id)
    if run_state.get("status") == "waiting":
        run_state = control.resume_published_run(run_id, approved=True)

    snapshot = build_control_snapshot(state_dir)

    workflow_path = artifacts_dir / "workflow.json"
    schedule_path = artifacts_dir / "schedule.json"
    run_due_path = artifacts_dir / "schedule-run-due.json"
    run_path = artifacts_dir / "run.json"
    snapshot_path = artifacts_dir / "control-plane-snapshot.json"

    _write_json(workflow_path, workflow)
    _write_json(schedule_path, stored_schedule)
    _write_json(run_due_path, run_due_result)
    _write_json(run_path, run_state)
    _write_json(snapshot_path, snapshot)

    return {
        "ok": True,
        "work_dir": str(work_dir),
        "state_dir": str(state_dir),
        "workflow_id": workflow_id,
        "workflow_version": workflow_version,
        "schedule_id": "schedule_approval_flow_daily",
        "run_id": run_id,
        "run_status": run_state.get("status", ""),
        "schedule_run_due": run_due_result,
        "snapshot_summary": snapshot.get("summary", {}),
        "artifacts": {
            "workflow": str(workflow_path),
            "schedule": str(schedule_path),
            "schedule_run_due": str(run_due_path),
            "run": str(run_path),
            "snapshot": str(snapshot_path),
        },
        "commands": {
            "run_schedule_smoke": f"python3 scripts/schedule_smoke.py --work-dir {work_dir}",
            "schedule_run_due": (
                "PYTHONPATH=src python3 -m skill2workflow.cli schedule-run-due "
                f"--state-dir {state_dir} --now {now}"
            ),
            "serve_ui": "python3 -m http.server 4173",
            "ui_url": DEFAULT_UI_URL,
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="schedule_smoke",
        description="Generate and run a deterministic local scheduled-trigger scenario.",
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--now", default=DEFAULT_NOW, help="ISO-8601 timestamp used for deterministic due checks.")
    parser.add_argument("--no-reset", action="store_true", help="Keep existing schedule smoke work directory contents.")
    args = parser.parse_args(argv)

    result = run_schedule_smoke(args.repo_root, args.work_dir, now=args.now, reset=not args.no_reset)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _reset_work_dir(repo_root: Path, work_dir: Path) -> None:
    if work_dir == repo_root or repo_root in work_dir.parents:
        raise ValueError("schedule smoke work_dir must be outside the repository when reset is enabled")
    if work_dir == Path(work_dir.anchor):
        raise ValueError("schedule smoke work_dir cannot be a filesystem root")
    if work_dir.exists():
        shutil.rmtree(work_dir)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
