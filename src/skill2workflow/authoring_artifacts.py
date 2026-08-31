"""Create one private, reviewable local artifact set from a ``SKILL.md`` file."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict

from .compiler import compile_ir_to_workflow, summarize_skill_compile, validate_workflow_structured
from .parser import parse_skill_file
from .visualizer import workflow_to_litegraph


AUTHORING_ARTIFACT_SCHEMA_VERSION = "skill2workflow-authoring-artifacts-0.1.0"
AUTHORING_ARTIFACT_RESULT_SCHEMA_VERSION = "skill2workflow-authoring-artifacts-result-0.1.0"
_ARTIFACT_FILENAMES = (
    "workflow.json",
    "workflow.litegraph.json",
    "compile-review.json",
    "manifest.json",
)


def create_authoring_artifacts(skill: Path, output_dir: Path) -> Dict[str, object]:
    """Compile one Skill into a new private local authoring artifact directory.

    The caller explicitly chooses the destination. The source Skill is read by
    the existing bounded parser but is never copied into the artifact set.
    Existing directories are never replaced.
    """

    ir = parse_skill_file(Path(skill))
    workflow = compile_ir_to_workflow(ir)
    errors = validate_workflow_structured(workflow)
    if errors:
        raise ValueError("compiled workflow is invalid")
    review = summarize_skill_compile(ir, workflow)
    graph = workflow_to_litegraph(workflow)

    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise ValueError("authoring artifact output directory must not already exist")
    destination.parent.mkdir(parents=True, exist_ok=True)

    artifacts = {
        "workflow.json": workflow,
        "workflow.litegraph.json": graph,
        "compile-review.json": review,
    }
    staged = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        os.chmod(staged, 0o700)
        files = []
        for name in _ARTIFACT_FILENAMES[:-1]:
            payload = _json_bytes(artifacts[name])
            _write_private_file(staged / name, payload)
            files.append(
                {
                    "path": name,
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
        metadata = workflow.get("workflow", {})
        workflow_file = files[0]
        manifest = {
            "schema_version": AUTHORING_ARTIFACT_SCHEMA_VERSION,
            "workflow": {
                "id": str(metadata.get("id") or ""),
                "version": str(metadata.get("version") or ""),
                "schema_version": str(workflow.get("schema_version") or ""),
                "status": str(metadata.get("status") or ""),
                "bytes": workflow_file["bytes"],
                "sha256": workflow_file["sha256"],
            },
            "review": review,
            "files": files,
        }
        _write_private_file(staged / "manifest.json", _json_bytes(manifest))
        if destination.exists() or destination.is_symlink():
            raise ValueError("authoring artifact output directory must not already exist")
        os.rename(staged, destination)
    except Exception:
        shutil.rmtree(staged, ignore_errors=True)
        raise

    return {
        "schema_version": AUTHORING_ARTIFACT_RESULT_SCHEMA_VERSION,
        "status": "created",
        "valid": True,
        "workflow_id": str(metadata.get("id") or ""),
        "workflow_version": str(metadata.get("version") or ""),
        "output_dir": str(destination),
        "files": list(_ARTIFACT_FILENAMES),
        "workflow_sha256": workflow_file["sha256"],
    }


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _write_private_file(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
