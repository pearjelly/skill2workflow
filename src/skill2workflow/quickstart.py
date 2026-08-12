"""Installed first-run controlled workflow quickstart."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Callable, Dict, Optional

from .compiler import compile_ir_to_workflow, validate_workflow
from .control_plane import LocalControlPlane
from .parser import parse_skill_file
from .service_bootstrap import initialize_service_workspace


QUICKSTART_RESULT_SCHEMA_VERSION = "skill2workflow-quickstart-result-0.1.0"
QUICKSTART_SKILL = """---
name: controlled-quickstart
description: Demonstrate a controlled workflow with an explicit human decision.
---

# Controlled Quickstart

Use this skill to verify that a workflow cannot finish before operator approval.

<HARD-GATE>
Do NOT complete the controlled action until the operator approves it.
</HARD-GATE>

## Checklist

1. Inspect the request
2. Prepare the controlled action
3. Ask the operator for approval
4. Record the completion audit

## Verification

- Confirm the run paused at the human gate.
- Confirm the resumed run recorded a completed audit trail.
"""


def initialize_quickstart_workspace(
    root: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
    token_factory: Optional[Callable[[], str]] = None,
) -> Dict[str, object]:
    """Create a secure service workspace and one waiting example workflow."""

    bootstrap = initialize_service_workspace(
        root,
        host=host,
        port=port,
        token_factory=token_factory,
    )
    workspace = Path(str(bootstrap["root"]))
    try:
        example_dir = workspace / "example"
        example_dir.mkdir(mode=0o700)
        os.chmod(example_dir, 0o700)
        skill_path = example_dir / "SKILL.md"
        workflow_path = example_dir / "workflow.json"
        _write_private_file(skill_path, QUICKSTART_SKILL)

        workflow = compile_ir_to_workflow(parse_skill_file(skill_path))
        errors = validate_workflow(workflow)
        if errors:
            raise ValueError("; ".join(errors))
        _write_private_file(
            workflow_path,
            json.dumps(workflow, ensure_ascii=False, indent=2) + "\n",
        )
        metadata = workflow.get("workflow", {})
        if not isinstance(metadata, dict):
            raise ValueError("quickstart workflow metadata must be an object")
        workflow_id = str(metadata.get("id", ""))
        workflow_version = str(metadata.get("version", ""))
        if workflow_id != "workflow_controlled_quickstart":
            raise ValueError("quickstart workflow identity is invalid")

        control = LocalControlPlane(
            Path(str(bootstrap["state_dir"])), storage="sqlite"
        )
        control.publish_workflow(workflow)
        run = control.run_published_workflow(workflow_id, workflow_version)
        if str(run.get("status", "")) != "waiting":
            raise ValueError("quickstart run did not stop at its human gate")
    except Exception:
        shutil.rmtree(workspace, ignore_errors=True)
        raise

    return {
        "schema_version": QUICKSTART_RESULT_SCHEMA_VERSION,
        "status": "ready_for_review",
        "root": str(workspace),
        "config_file": str(bootstrap["config_file"]),
        "state_dir": str(bootstrap["state_dir"]),
        "token_file": str(bootstrap["token_file"]),
        "credential_directory": str(bootstrap["credential_directory"]),
        "skill_file": str(skill_path),
        "workflow_file": str(workflow_path),
        "workflow_id": workflow_id,
        "workflow_version": workflow_version,
        "run_id": str(run["run_id"]),
        "run_status": str(run["status"]),
    }


def _write_private_file(path: Path, value: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    os.chmod(path, 0o600)
