"""Prove the local Skill-to-controlled-runtime authoring journey."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional, Sequence

from .authoring_artifacts import (
    create_authoring_artifacts,
    load_verified_authoring_workflow,
    verify_authoring_artifacts,
)
from .bundles import create_workflow_bundle, verify_workflow_bundle
from .control_plane import LocalControlPlane
from .dashboard import build_control_snapshot


AUTHORING_DELIVERY_EVIDENCE_SCHEMA_VERSION = (
    "skill2workflow-authoring-delivery-evidence-0.1.0"
)
DEFAULT_WORK_DIR = Path(tempfile.gettempdir()) / "skill2workflow-authoring-delivery"


def run_authoring_delivery_smoke(
    work_dir: Path = DEFAULT_WORK_DIR,
    *,
    reset: bool = True,
) -> Dict[str, object]:
    """Run a private authoring set through Bundle publication and gate decisions.

    This deterministic local drill creates no network listener, external
    connector, credential, or live provider request. It is evidence that the
    documented authoring handoff reaches the existing durable runtime boundary.
    """

    root = Path(work_dir).resolve()
    if reset:
        _reset_work_dir(root)
    root.mkdir(parents=True, exist_ok=True)
    root.chmod(0o700)

    source = root / "SKILL.md"
    authoring_dir = root / "authoring"
    bundle = root / "authoring-delivery.s2w"
    artifacts_dir = root / "artifacts"
    state_dir = root / "state"
    artifacts_dir.mkdir(mode=0o700)
    state_dir.mkdir(mode=0o700)
    source.write_text(_SMOKE_SKILL, encoding="utf-8")
    source.chmod(0o600)

    export = create_authoring_artifacts(source, authoring_dir)
    authoring_verification = verify_authoring_artifacts(authoring_dir)
    workflow = load_verified_authoring_workflow(authoring_dir)
    bundle_result = create_workflow_bundle(workflow, bundle)
    bundle_verification = verify_workflow_bundle(bundle)

    control = LocalControlPlane(state_dir, storage="sqlite")
    publication = control.publish_workflow(workflow)
    trigger = control.trigger_workflow(
        {
            "workflow_id": str(publication["workflow_id"]),
            "version": str(publication["version"]),
            "source": "local-authoring-delivery-smoke",
            "idempotency_key": "authoring-delivery-001",
            "input": {},
        }
    )
    run_id = str(trigger["run_id"])
    waiting = control.get_run(run_id)
    completed = control.resume_published_run(run_id, approved=True)
    audit_events = control.list_audit_events(run_id=run_id)

    rejected_trigger = control.trigger_workflow(
        {
            "workflow_id": str(publication["workflow_id"]),
            "version": str(publication["version"]),
            "source": "local-authoring-delivery-smoke",
            "idempotency_key": "authoring-delivery-002",
            "input": {},
        }
    )
    rejected_run_id = str(rejected_trigger["run_id"])
    rejected_waiting = control.get_run(rejected_run_id)
    rejected = control.resume_published_run(rejected_run_id, approved=False)
    rejected_audit_events = control.list_audit_events(run_id=rejected_run_id)
    snapshot = build_control_snapshot(state_dir, storage="sqlite")

    _write_private_json(artifacts_dir / "authoring-verification.json", authoring_verification)
    _write_private_json(artifacts_dir / "bundle-verification.json", bundle_verification)
    _write_private_json(artifacts_dir / "run.json", completed)
    _write_private_json(artifacts_dir / "audit.json", audit_events)
    _write_private_json(artifacts_dir / "rejected-run.json", rejected)
    _write_private_json(artifacts_dir / "rejected-audit.json", rejected_audit_events)
    _write_private_json(artifacts_dir / "control-plane-snapshot.json", snapshot)

    checks = {
        "authoring_exported": export.get("valid") is True,
        "authoring_verified": authoring_verification.get("valid") is True,
        "bundle_created": bundle_result.get("valid") is True and bundle.is_file(),
        "bundle_verified": bundle_verification.get("valid") is True,
        "published": publication.get("status") == "published",
        "initial_human_gate_waiting": waiting.get("status") == "waiting",
        "approved_run_completed": completed.get("status") == "completed",
        "audit_recorded": any(event.get("type") == "run_completed" for event in audit_events),
        "rejected_human_gate_waiting": rejected_waiting.get("status") == "waiting",
        "rejected_run_failed": rejected.get("status") == "failed",
        "rejection_audit_recorded": any(
            event.get("type") == "run_failed" for event in rejected_audit_events
        ),
        "snapshot_recorded": snapshot.get("summary", {}).get("run_status_counts")
        == {"completed": 1, "failed": 1},
    }
    return {
        "schema_version": AUTHORING_DELIVERY_EVIDENCE_SCHEMA_VERSION,
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "initial_run_status": str(waiting.get("status") or ""),
        "final_run_status": str(completed.get("status") or ""),
        "rejected_initial_run_status": str(rejected_waiting.get("status") or ""),
        "rejected_final_run_status": str(rejected.get("status") or ""),
        "artifacts": {
            "bundle": str(bundle),
            "authoring_verification": str(artifacts_dir / "authoring-verification.json"),
            "bundle_verification": str(artifacts_dir / "bundle-verification.json"),
            "run": str(artifacts_dir / "run.json"),
            "audit": str(artifacts_dir / "audit.json"),
            "rejected_run": str(artifacts_dir / "rejected-run.json"),
            "rejected_audit": str(artifacts_dir / "rejected-audit.json"),
            "snapshot": str(artifacts_dir / "control-plane-snapshot.json"),
        },
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--no-reset", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_authoring_delivery_smoke(args.work_dir, reset=not args.no_reset)
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


def _reset_work_dir(work_dir: Path) -> None:
    if work_dir == Path(work_dir.anchor):
        raise ValueError("authoring delivery work_dir cannot be a filesystem root")
    if work_dir.exists():
        shutil.rmtree(work_dir)


def _write_private_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


_SMOKE_SKILL = """---
name: authoring-delivery-smoke
description: local authoring delivery verification
---

## Checklist

1. Ask user for approval — private authoring delivery instruction
2. Verify completion
"""
