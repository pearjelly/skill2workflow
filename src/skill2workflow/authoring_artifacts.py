"""Create one private, reviewable local artifact set from a ``SKILL.md`` file."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Dict, Optional

from .artifact_io import MAX_WORKFLOW_ARTIFACT_BYTES
from .compiler import (
    SKILL_COMPILE_REVIEW_SCHEMA_VERSION,
    compile_ir_to_workflow,
    summarize_skill_compile,
    validate_workflow_structured,
)
from .parser import parse_skill_file
from .visualizer import workflow_to_litegraph


AUTHORING_ARTIFACT_SCHEMA_VERSION = "skill2workflow-authoring-artifacts-0.1.0"
AUTHORING_ARTIFACT_RESULT_SCHEMA_VERSION = "skill2workflow-authoring-artifacts-result-0.1.0"
AUTHORING_ARTIFACT_VERIFICATION_SCHEMA_VERSION = (
    "skill2workflow-authoring-artifacts-verification-0.1.0"
)
_ARTIFACT_FILENAMES = (
    "workflow.json",
    "workflow.litegraph.json",
    "compile-review.json",
    "manifest.json",
)
_DATA_FILENAMES = _ARTIFACT_FILENAMES[:-1]
_MAX_TOTAL_ARTIFACT_BYTES = MAX_WORKFLOW_ARTIFACT_BYTES * 3
_READ_CHUNK_BYTES = 64 * 1024


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
        for name in _DATA_FILENAMES:
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


def verify_authoring_artifacts(output_dir: Path) -> Dict[str, object]:
    """Verify one local authoring artifact directory without executing it.

    Reports have a deliberately finite, value-free error vocabulary so this can
    run against an untrusted shared directory in CI. Checksums detect accidental
    or untrusted modification, but are not an authenticity signature.
    """

    report = _new_verification_report()
    try:
        members = _read_artifact_members(Path(output_dir))
    except _ArtifactVerificationError as error:
        return _invalid(report, error.code)
    except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return _invalid(report, "artifact_unreadable")

    try:
        workflow = _parse_json_object(members["workflow.json"])
        graph = _parse_json_object(members["workflow.litegraph.json"])
        review = _parse_json_object(members["compile-review.json"])
        manifest = _parse_json_object(members["manifest.json"])
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        return _invalid(report, "artifact_json_invalid")

    manifest_error = _validate_manifest(manifest, members, workflow, review)
    if manifest_error:
        return _invalid(report, manifest_error)
    try:
        workflow_errors = validate_workflow_structured(workflow)
    except (TypeError, KeyError, AttributeError, RecursionError):
        return _invalid(report, "artifact_workflow_invalid")
    if workflow_errors:
        return _invalid(report, "artifact_workflow_invalid")
    if graph != workflow_to_litegraph(workflow):
        return _invalid(report, "artifact_graph_mismatch")
    if not _review_matches_workflow(review, workflow):
        return _invalid(report, "artifact_review_mismatch")

    report["valid"] = True
    report["files"] = len(_ARTIFACT_FILENAMES)
    report["workflow"] = {
        "schema_version": str(workflow.get("schema_version") or ""),
        "bytes": len(members["workflow.json"]),
        "sha256": hashlib.sha256(members["workflow.json"]).hexdigest(),
    }
    return report


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


class _ArtifactVerificationError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _new_verification_report() -> Dict[str, object]:
    return {
        "schema_version": AUTHORING_ARTIFACT_VERIFICATION_SCHEMA_VERSION,
        "valid": False,
        "files": 0,
        "workflow": None,
        "errors": [],
    }


def _invalid(report: Dict[str, object], code: str) -> Dict[str, object]:
    report["errors"] = [{"code": code}]
    return report


def _read_artifact_members(directory: Path) -> Dict[str, bytes]:
    before = directory.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise _ArtifactVerificationError("artifact_directory_unsafe")
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(directory, flags)
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_dev != before.st_dev
            or metadata.st_ino != before.st_ino
        ):
            raise _ArtifactVerificationError("artifact_directory_unsafe")
        if metadata.st_mode & 0o077:
            raise _ArtifactVerificationError("artifact_permissions_invalid")
        names = os.listdir(descriptor)
        if set(names) != set(_ARTIFACT_FILENAMES) or len(names) != len(_ARTIFACT_FILENAMES):
            raise _ArtifactVerificationError("artifact_members_invalid")
        members = {}
        total = 0
        for name in _ARTIFACT_FILENAMES:
            payload = _read_private_member(descriptor, name)
            total += len(payload)
            if total > _MAX_TOTAL_ARTIFACT_BYTES:
                raise _ArtifactVerificationError("artifact_too_large")
            members[name] = payload
        return members
    finally:
        os.close(descriptor)


def _read_private_member(directory_fd: int, name: str) -> bytes:
    before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode):
        raise _ArtifactVerificationError("artifact_file_unsafe")
    if before.st_mode & 0o077:
        raise _ArtifactVerificationError("artifact_permissions_invalid")
    if before.st_size > MAX_WORKFLOW_ARTIFACT_BYTES:
        raise _ArtifactVerificationError("artifact_too_large")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(name, flags, dir_fd=directory_fd)
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != before.st_dev
            or opened.st_ino != before.st_ino
        ):
            raise _ArtifactVerificationError("artifact_file_unsafe")
        if opened.st_size > MAX_WORKFLOW_ARTIFACT_BYTES:
            raise _ArtifactVerificationError("artifact_too_large")
        chunks = []
        remaining = MAX_WORKFLOW_ARTIFACT_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(_READ_CHUNK_BYTES, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) > MAX_WORKFLOW_ARTIFACT_BYTES:
            raise _ArtifactVerificationError("artifact_too_large")
        after = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if after.st_dev != before.st_dev or after.st_ino != before.st_ino:
            raise _ArtifactVerificationError("artifact_file_unsafe")
        return payload
    finally:
        os.close(descriptor)


def _parse_json_object(payload: bytes) -> Dict[str, object]:
    value = json.loads(payload.decode("utf-8"), parse_constant=_reject_json_constant)
    if not isinstance(value, dict):
        raise ValueError("artifact JSON must be an object")
    return value


def _validate_manifest(
    manifest: Dict[str, object],
    members: Dict[str, bytes],
    workflow: Dict[str, object],
    review: Dict[str, object],
) -> Optional[str]:
    if set(manifest) != {"schema_version", "workflow", "review", "files"}:
        return "artifact_manifest_invalid"
    if manifest.get("schema_version") != AUTHORING_ARTIFACT_SCHEMA_VERSION:
        return "artifact_manifest_invalid"
    if manifest.get("review") != review:
        return "artifact_manifest_invalid"
    expected_files = [
        {
            "path": name,
            "bytes": len(members[name]),
            "sha256": hashlib.sha256(members[name]).hexdigest(),
        }
        for name in _DATA_FILENAMES
    ]
    if manifest.get("files") != expected_files:
        return "artifact_file_digest_mismatch"
    metadata = workflow.get("workflow")
    if not isinstance(metadata, dict):
        return "artifact_workflow_invalid"
    expected_workflow = {
        "id": str(metadata.get("id") or ""),
        "version": str(metadata.get("version") or ""),
        "schema_version": str(workflow.get("schema_version") or ""),
        "status": str(metadata.get("status") or ""),
        "bytes": len(members["workflow.json"]),
        "sha256": hashlib.sha256(members["workflow.json"]).hexdigest(),
    }
    if manifest.get("workflow") != expected_workflow:
        return "artifact_file_digest_mismatch"
    return None


def _review_matches_workflow(review: Dict[str, object], workflow: Dict[str, object]) -> bool:
    if set(review) != {
        "schema_version",
        "ordered_step_count",
        "executable_node_count",
        "human_gate_count",
        "verification_node_count",
        "hard_gate_count",
        "notices",
    }:
        return False
    if review.get("schema_version") != SKILL_COMPILE_REVIEW_SCHEMA_VERSION:
        return False
    count_names = (
        "ordered_step_count",
        "executable_node_count",
        "human_gate_count",
        "verification_node_count",
        "hard_gate_count",
    )
    if any(
        isinstance(review.get(name), bool)
        or not isinstance(review.get(name), int)
        or review[name] < 0
        for name in count_names
    ):
        return False
    nodes = workflow.get("nodes")
    guards = workflow.get("guards")
    if not isinstance(nodes, list) or not isinstance(guards, list):
        return False
    types = [node.get("type") for node in nodes if isinstance(node, dict)]
    executable = sum(
        node_type in {"step", "human_gate", "tool_call", "verification", "instruction"}
        for node_type in types
    )
    if review["executable_node_count"] != executable:
        return False
    if review["human_gate_count"] != types.count("human_gate"):
        return False
    if review["verification_node_count"] != types.count("verification"):
        return False
    if review["hard_gate_count"] != len(guards):
        return False
    notices = review.get("notices")
    if not isinstance(notices, list) or any(not isinstance(item, str) for item in notices):
        return False
    expected_notices = []
    if review["ordered_step_count"] == 0:
        expected_notices.append("checklist_not_found")
    if review["human_gate_count"] == 0:
        expected_notices.append("human_gate_not_inferred")
    if review["verification_node_count"] == 0:
        expected_notices.append("verification_not_inferred")
    return notices == expected_notices


def _reject_json_constant(value: str):
    raise ValueError("artifact JSON must contain finite values")
