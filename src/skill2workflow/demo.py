"""Deterministic local demo bootstrap for contributor onboarding."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict

from .compiler import compile_ir_to_workflow, validate_workflow
from .control_plane import LocalControlPlane
from .dashboard import build_control_snapshot
from .parser import parse_skill_file
from .visualizer import workflow_to_litegraph


DEFAULT_WORK_DIR = Path(tempfile.gettempdir()) / "skill2workflow-demo"
DEFAULT_UI_URL = "http://localhost:4173/web/control.html"


def run_demo_bootstrap(repo_root: Path, work_dir: Path = DEFAULT_WORK_DIR, reset: bool = True) -> Dict[str, object]:
    """Generate local demo artifacts from committed examples."""
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    if reset:
        _reset_work_dir(repo_root, work_dir)

    artifacts_dir = work_dir / "artifacts"
    state_dir = work_dir / "state"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    skill_path = repo_root / "examples" / "skills" / "approval-flow" / "SKILL.md"
    if not skill_path.exists():
        raise ValueError(f"demo skill not found: {skill_path}")

    workflow = compile_ir_to_workflow(parse_skill_file(skill_path))
    errors = validate_workflow(workflow)
    if errors:
        raise ValueError("; ".join(errors))

    workflow_path = artifacts_dir / "workflow.json"
    litegraph_path = artifacts_dir / "workflow.litegraph.json"
    snapshot_path = artifacts_dir / "control-plane-snapshot.json"

    _write_json(workflow_path, workflow)
    _write_json(litegraph_path, workflow_to_litegraph(workflow))

    workflow_meta = workflow.get("workflow", {})
    if not isinstance(workflow_meta, dict):
        raise ValueError("workflow.workflow must be an object")
    workflow_id = str(workflow_meta.get("id", "workflow"))
    workflow_version = str(workflow_meta.get("version", "0.1.0"))

    control = LocalControlPlane(state_dir)
    control.publish_workflow(workflow)
    run_state = control.run_published_workflow(workflow_id, workflow_version)
    if run_state.get("status") == "waiting":
        run_state = control.resume_published_run(str(run_state["run_id"]), approved=True)

    snapshot = build_control_snapshot(state_dir)
    _write_json(snapshot_path, snapshot)

    return {
        "ok": True,
        "work_dir": str(work_dir),
        "state_dir": str(state_dir),
        "workflow_id": workflow_id,
        "workflow_version": workflow_version,
        "run_id": run_state.get("run_id", ""),
        "run_status": run_state.get("status", ""),
        "artifacts": {
            "workflow": str(workflow_path),
            "litegraph": str(litegraph_path),
            "snapshot": str(snapshot_path),
        },
        "snapshot_summary": snapshot.get("summary", {}),
        "commands": {
            "run_demo": f"python3 scripts/demo_bootstrap.py --work-dir {work_dir}",
            "serve_ui": "python3 -m http.server 4173",
            "ui_url": DEFAULT_UI_URL,
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="demo_bootstrap", description="Generate local demo onboarding artifacts.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--no-reset", action="store_true", help="Keep existing demo work directory contents.")
    args = parser.parse_args(argv)

    result = run_demo_bootstrap(args.repo_root, args.work_dir, reset=not args.no_reset)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _reset_work_dir(repo_root: Path, work_dir: Path) -> None:
    if work_dir == repo_root or repo_root in work_dir.parents:
        raise ValueError("demo work_dir must be outside the repository when reset is enabled")
    if work_dir == Path(work_dir.anchor):
        raise ValueError("demo work_dir cannot be a filesystem root")
    if work_dir.exists():
        shutil.rmtree(work_dir)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
