"""Installed first-run controlled workflow quickstart."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, Dict, Optional

from .compiler import compile_ir_to_workflow, validate_workflow
from .control_plane import LocalControlPlane
from .parser import parse_skill_text, read_skill_text
from .service_bootstrap import (
    _cleanup_workspace, _mark_cleanup_unconfirmed, _pin_workspace, initialize_service_workspace,
    validate_service_workspace_location,
)
from .input_schema import validate_trigger_input
from .preflight import build_workflow_preflight
from .triggers import MAX_TRIGGER_INPUT_BYTES, normalize_trigger_input


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
    skill_path: Optional[Path] = None,
    trigger_input: Optional[Dict[str, object]] = None,
    dry_run: bool = False,
) -> Dict[str, object]:
    """Create a controlled workspace, or preview readiness without creating it."""

    skill_text = QUICKSTART_SKILL
    if skill_path is not None:
        skill_text = read_skill_text(Path(skill_path))
    workflow = compile_ir_to_workflow(
        parse_skill_text(skill_text, source_path="SKILL.md")
    )
    if validate_workflow(workflow) or not _has_human_gate(workflow):
        raise ValueError(
            "quickstart SKILL must compile to a valid workflow with a human gate"
        )
    _require_pre_effect_gate(workflow)
    try:
        normalized_input = normalize_trigger_input({} if trigger_input is None else trigger_input)
        json.dumps(normalized_input, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError(
            f"quickstart input must be a finite JSON object of at most {MAX_TRIGGER_INPUT_BYTES} UTF-8 bytes"
        ) from error
    if not dry_run:
        # Preserve existing value-free contract diagnostics for real admission.
        validate_trigger_input(workflow.get('input_schema'), normalized_input)
    readiness = build_workflow_preflight(
        workflow, normalized_input, input_present=trigger_input is not None
    )
    validate_service_workspace_location(root, host=host, port=port)
    if dry_run:
        return readiness
    if not readiness['ready']:
        raise ValueError("quickstart input does not satisfy required connector mappings")

    bootstrap = initialize_service_workspace(
        root,
        host=host,
        port=port,
        token_factory=token_factory,
    )
    workspace = Path(str(bootstrap["root"]))
    workspace_fd = _pin_workspace(workspace)
    try:
        example_dir = workspace / "example"
        example_dir.mkdir(mode=0o700)
        os.chmod(example_dir, 0o700)
        workspace_skill_path = example_dir / "SKILL.md"
        workflow_path = example_dir / "workflow.json"
        _write_private_file(workspace_skill_path, skill_text)
        _write_private_file(
            workflow_path,
            json.dumps(workflow, ensure_ascii=False, indent=2) + "\n",
        )
        metadata = workflow.get("workflow", {})
        if not isinstance(metadata, dict):
            raise ValueError("quickstart workflow metadata must be an object")
        workflow_id = str(metadata.get("id", ""))
        workflow_version = str(metadata.get("version", ""))
        if not workflow_id or not workflow_version:
            raise ValueError("quickstart workflow identity is invalid")

        control = LocalControlPlane(
            Path(str(bootstrap["state_dir"])), storage="sqlite"
        )
        control.publish_workflow(workflow)
        if trigger_input is None:
            run = control.run_published_workflow(workflow_id, workflow_version)
        else:
            triggered = control.trigger_workflow({
                'workflow_id': workflow_id, 'version': workflow_version,
                'source': 'quickstart', 'idempotency_key': 'quickstart-initial',
                'input': normalized_input,
            })
            run = control.get_run(str(triggered['run_id']))
        if str(run.get("status", "")) != "waiting":
            raise ValueError("quickstart run did not stop at its human gate")
    except Exception as error:
        if not _cleanup_workspace(workspace, workspace_fd):
            _mark_cleanup_unconfirmed(error)
        raise
    finally:
        if workspace_fd is not None:
            os.close(workspace_fd)

    run_id = str(run["run_id"])
    state_dir = str(bootstrap["state_dir"])
    config_file = str(bootstrap["config_file"])
    return {
        "schema_version": QUICKSTART_RESULT_SCHEMA_VERSION,
        "status": "ready_for_review",
        "root": str(workspace),
        "config_file": config_file,
        "state_dir": state_dir,
        "token_file": str(bootstrap["token_file"]),
        "credential_directory": str(bootstrap["credential_directory"]),
        "skill_file": str(workspace_skill_path),
        "workflow_file": str(workflow_path),
        "workflow_id": workflow_id,
        "workflow_version": workflow_version,
        "run_id": run_id,
        "run_status": str(run["status"]),
        "operator_commands": {
            "inspect_run": [
                "skill2workflow",
                "control-run",
                run_id,
                "--state-dir",
                state_dir,
                "--storage",
                "sqlite",
            ],
            "approve_run": [
                "skill2workflow",
                "resume-published",
                run_id,
                "--state-dir",
                state_dir,
                "--storage",
                "sqlite",
            ],
            "service_doctor": [
                "skill2workflow",
                "service-doctor",
                "--config",
                config_file,
            ],
            "start_service": [
                "skill2workflow",
                "service",
                "--config",
                config_file,
            ],
        },
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


def _has_human_gate(workflow: Dict[str, object]) -> bool:
    nodes = workflow.get("nodes")
    return isinstance(nodes, list) and any(
        isinstance(node, dict) and node.get("type") == "human_gate"
        for node in nodes
    )


def _require_pre_effect_gate(workflow: Dict[str, object]) -> None:
    """Bound the compiled success prefix before creating a service workspace."""
    nodes = {node['id']: node for node in workflow['nodes']}
    current = workflow.get('entry')
    visited = set()
    while current in nodes and current not in visited:
        visited.add(current)
        node = nodes[current]
        if node.get('type') == 'human_gate':
            return
        connector = node.get('connector')
        if connector and connector.get('id') != 'manual':
            raise ValueError('quickstart SKILL cannot execute a non-manual connector before the first human gate')
        current = node.get('on_success')
    raise ValueError('quickstart SKILL must reach a human gate on its initial success path')
