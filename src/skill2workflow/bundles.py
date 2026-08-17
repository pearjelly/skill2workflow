"""Portable, deterministic Workflow DSL bundles.

Bundles are deliberately small and boring: a ZIP archive containing one
validated Workflow DSL document and a value-free manifest.  They are useful
for sharing examples, reviewing a change outside a checkout, and moving a
workflow between local evaluation workspaces without turning a bundle into a
second execution format or a credential container.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Optional, Tuple

from .artifact_io import MAX_WORKFLOW_ARTIFACT_BYTES
from .compiler import validate_workflow_structured
from .secret_hygiene import scan_json_value
from .workflow_diff import workflow_diff_changes


BUNDLE_SCHEMA_VERSION = "skill2workflow-workflow-bundle-0.1.0"
BUNDLE_VERIFICATION_SCHEMA_VERSION = "skill2workflow-workflow-bundle-verification-0.1.0"
BUNDLE_DIFF_SCHEMA_VERSION = "skill2workflow-workflow-bundle-diff-0.1.0"
MAX_BUNDLE_ARCHIVE_BYTES = 8 * 1024 * 1024
MAX_BUNDLE_MEMBER_BYTES = MAX_WORKFLOW_ARTIFACT_BYTES
MAX_BUNDLE_TOTAL_MEMBER_BYTES = 4 * 1024 * 1024
MAX_BUNDLE_MEMBERS = 2
_BUNDLE_MEMBERS = ("manifest.json", "workflow.json")
_READ_CHUNK_BYTES = 64 * 1024


def create_workflow_bundle(
    workflow: Dict[str, object],
    output: Path,
    *,
    overwrite: bool = False,
) -> Dict[str, object]:
    """Create one deterministic bundle and return a redacted summary.

    The operation validates the Workflow DSL and rejects obvious secret-like
    values before writing.  Output is assembled beside the destination and
    atomically replaced, so a failed build cannot leave a partial bundle.
    """

    _validate_bundle_workflow(workflow)
    workflow_bytes = _canonical_json_bytes(workflow, "workflow artifact")
    workflow_digest = _sha256(workflow_bytes)
    metadata = workflow.get("workflow", {})
    connectors = _connector_ids(workflow)
    manifest = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "workflow": {
            "id": str(metadata.get("id") or ""),
            "version": str(metadata.get("version") or ""),
            "schema_version": str(workflow.get("schema_version") or ""),
            "status": str(metadata.get("status") or ""),
            "bytes": len(workflow_bytes),
            "sha256": workflow_digest,
        },
        "files": [
            {
                "path": "workflow.json",
                "bytes": len(workflow_bytes),
                "sha256": workflow_digest,
            }
        ],
        "connectors": connectors,
        "secret_hygiene": {"status": "passed", "findings": 0},
    }
    manifest_bytes = _canonical_json_bytes(manifest, "bundle manifest")
    archive_bytes = _build_archive(manifest_bytes, workflow_bytes)
    if len(archive_bytes) > MAX_BUNDLE_ARCHIVE_BYTES:
        raise ValueError(
            f"workflow bundle exceeds {MAX_BUNDLE_ARCHIVE_BYTES} bytes"
        )

    destination = Path(output)
    _check_output_path(destination, overwrite=overwrite)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_fd, temporary_name = tempfile.mkstemp(
        prefix=".{}.".format(destination.name),
        suffix=".tmp",
        dir=str(destination.parent),
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(temporary_fd, "wb") as handle:
            handle.write(archive_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, destination)
    except Exception:
        try:
            temporary.unlink()
        except OSError:
            pass
        try:
            os.close(temporary_fd)
        except OSError:
            pass
        raise

    return {
        "schema_version": BUNDLE_VERIFICATION_SCHEMA_VERSION,
        "status": "created",
        "valid": True,
        "workflow_id": str(metadata.get("id") or ""),
        "workflow_version": str(metadata.get("version") or ""),
        "workflow_sha256": workflow_digest,
        "bundle_bytes": len(archive_bytes),
        "members": list(_BUNDLE_MEMBERS),
    }


def verify_workflow_bundle(bundle: Path) -> Dict[str, object]:
    """Verify one bundle without extracting or executing it.

    Malformed archives return a stable ``valid: false`` report.  Values from
    the archive are never copied into errors, which keeps verification safe to
    use in CI and on untrusted shared artifacts.
    """

    report = {
        "schema_version": BUNDLE_VERIFICATION_SCHEMA_VERSION,
        "valid": False,
        "bundle_bytes": 0,
        "members": 0,
        "workflow": None,
        "errors": [],
    }
    try:
        raw = _read_bundle_bytes(Path(bundle))
    except (OSError, ValueError, zipfile.BadZipFile):
        report["errors"] = [{"code": "bundle_unreadable", "path": "$"}]
        return report
    report["bundle_bytes"] = len(raw)
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r"):
            pass
    except zipfile.BadZipFile:
        report["errors"] = [{"code": "bundle_unreadable", "path": "$"}]
        return report

    try:
        workflow = _inspect_bundle(raw, report)
    except (
        OSError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
        NotImplementedError,
        RuntimeError,
        EOFError,
        TypeError,
        KeyError,
        AttributeError,
        RecursionError,
    ):
        _invalid(report, "invalid_archive", "$")
        return report

    if workflow is None:
        return report

    metadata = workflow.get("workflow", {})
    workflow_digest = report.pop("_workflow_sha256")
    report["workflow"] = {
        "id": str(metadata.get("id") or ""),
        "version": str(metadata.get("version") or ""),
        "schema_version": str(workflow.get("schema_version") or ""),
        "status": str(metadata.get("status") or ""),
        "bytes": report.pop("_workflow_bytes"),
        "sha256": workflow_digest,
    }
    report["valid"] = True
    report["errors"] = []
    return report


def load_verified_workflow_bundle(bundle: Path) -> Dict[str, object]:
    """Load a bundle's Workflow DSL only after the full verification boundary.

    This is the explicit local-import primitive used by ``bundle-publish``.
    It reads the archive in memory, never extracts files, and raises one fixed
    error for any invalid or unreadable bundle so callers cannot accidentally
    turn archive contents into an error response.
    """

    report = {
        "schema_version": BUNDLE_VERIFICATION_SCHEMA_VERSION,
        "valid": False,
        "bundle_bytes": 0,
        "members": 0,
        "workflow": None,
        "errors": [],
    }
    try:
        raw = _read_bundle_bytes(Path(bundle))
        report["bundle_bytes"] = len(raw)
        workflow = _inspect_bundle(raw, report)
    except (
        OSError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
        NotImplementedError,
        RuntimeError,
        EOFError,
        TypeError,
        KeyError,
        AttributeError,
        RecursionError,
    ) as error:
        raise ValueError("workflow bundle verification failed") from error
    if workflow is None:
        raise ValueError("workflow bundle verification failed")
    return workflow


def diff_workflow_bundles(from_bundle: Path, to_bundle: Path) -> Dict[str, object]:
    """Compare two verified bundles using the published diff semantics.

    Only workflow identity, versions, digests, changed sections, and item IDs
    are returned.  The command is read-only and never publishes or executes a
    workflow.
    """

    from_report = verify_workflow_bundle(from_bundle)
    to_report = verify_workflow_bundle(to_bundle)
    if not from_report.get("valid") or not to_report.get("valid"):
        raise ValueError("workflow bundle verification failed")
    from_workflow = load_verified_workflow_bundle(from_bundle)
    to_workflow = load_verified_workflow_bundle(to_bundle)
    from_meta = from_report.get("workflow") or {}
    to_meta = to_report.get("workflow") or {}
    workflow_id = str(from_meta.get("id") or "")
    if not workflow_id or workflow_id != str(to_meta.get("id") or ""):
        raise ValueError("workflow bundle IDs must match")
    changes = workflow_diff_changes(from_workflow, to_workflow)
    return {
        "schema_version": BUNDLE_DIFF_SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "from": {
            "version": str(from_meta.get("version") or ""),
            "status": str(from_meta.get("status") or ""),
            "sha256": str(from_meta.get("sha256") or ""),
        },
        "to": {
            "version": str(to_meta.get("version") or ""),
            "status": str(to_meta.get("status") or ""),
            "sha256": str(to_meta.get("sha256") or ""),
        },
        "changed": bool(changes["sections"]),
        "changes": changes,
    }


def _inspect_bundle(raw: bytes, report: Dict[str, object]):
    archive = zipfile.ZipFile(io.BytesIO(raw), "r")

    try:
        infos = archive.infolist()
        report["members"] = len(infos)
        if len(infos) > MAX_BUNDLE_MEMBERS:
            return _invalid(report, "too_many_members", "$.members")
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            return _invalid(report, "duplicate_member", "$")
        if tuple(sorted(names)) != tuple(sorted(_BUNDLE_MEMBERS)):
            return _invalid(report, "unexpected_members", "$.members")
        total = 0
        member_data = {}
        for info in infos:
            if _is_symlink(info) or info.filename.endswith("/"):
                return _invalid(report, "unsafe_member", "$.members")
            if info.file_size > MAX_BUNDLE_MEMBER_BYTES:
                return _invalid(report, "member_too_large", "$.members")
            total += info.file_size
            if total > MAX_BUNDLE_TOTAL_MEMBER_BYTES:
                return _invalid(report, "members_too_large", "$.members")
            member_data[info.filename] = _read_member_bounded(
                archive, info, MAX_BUNDLE_MEMBER_BYTES
            )

        try:
            manifest = _parse_object(member_data["manifest.json"])
            workflow = _parse_object(member_data["workflow.json"])
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return _invalid(report, "invalid_json", "$")

        manifest_error = _validate_manifest(manifest, workflow, member_data["workflow.json"])
        if manifest_error:
            return _invalid(report, manifest_error[0], manifest_error[1])
        workflow_errors = validate_workflow_structured(workflow)
        if workflow_errors:
            return _invalid(report, "invalid_workflow", "$.workflow")
        try:
            findings = scan_json_value(workflow, source="workflow.json")
        except RecursionError:
            return _invalid(report, "workflow_too_deep", "$.workflow")
        if findings:
            return _invalid(report, "secret_like_value", "$.workflow")

        report["_workflow_bytes"] = len(member_data["workflow.json"])
        report["_workflow_sha256"] = _sha256(member_data["workflow.json"])
        return workflow
    finally:
        archive.close()


def _validate_bundle_workflow(workflow: object) -> None:
    if not isinstance(workflow, dict):
        raise ValueError("workflow must be a JSON object")
    try:
        errors = validate_workflow_structured(workflow)
    except (TypeError, KeyError, AttributeError, RecursionError) as error:
        raise ValueError("workflow is invalid") from error
    if errors:
        first = errors[0]
        raise ValueError("workflow is invalid: {}".format(first.get("code", "invalid_workflow")))
    try:
        findings = scan_json_value(workflow, source="workflow.json")
    except RecursionError as error:
        raise ValueError("workflow is too deeply nested") from error
    if findings:
        raise ValueError("workflow contains secret-like values")


def _canonical_json_bytes(value: object, label: str) -> bytes:
    try:
        raw = (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ValueError(f"{label} must be finite JSON") from error
    limit = MAX_WORKFLOW_ARTIFACT_BYTES if label == "workflow artifact" else MAX_BUNDLE_MEMBER_BYTES
    if len(raw) > limit:
        raise ValueError(f"{label} exceeds {limit} bytes")
    return raw


def _build_archive(manifest_bytes: bytes, workflow_bytes: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in (
            ("manifest.json", manifest_bytes),
            ("workflow.json", workflow_bytes),
        ):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return output.getvalue()


def _check_output_path(path: Path, *, overwrite: bool) -> None:
    if path.exists() or path.is_symlink():
        if not overwrite:
            raise ValueError(f"bundle output already exists: {path}")
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ValueError("bundle output must be a regular file")


def _read_bundle_bytes(path: Path) -> bytes:
    before = path.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ValueError("workflow bundle must be a regular non-symlink file")
    if before.st_size > MAX_BUNDLE_ARCHIVE_BYTES:
        raise ValueError(f"workflow bundle exceeds {MAX_BUNDLE_ARCHIVE_BYTES} bytes")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != before.st_dev
            or opened.st_ino != before.st_ino
        ):
            raise ValueError("workflow bundle changed while being read")
        chunks = []
        remaining = MAX_BUNDLE_ARCHIVE_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(_READ_CHUNK_BYTES, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_BUNDLE_ARCHIVE_BYTES:
            raise ValueError(f"workflow bundle exceeds {MAX_BUNDLE_ARCHIVE_BYTES} bytes")
        after = path.lstat()
        if after.st_dev != before.st_dev or after.st_ino != before.st_ino:
            raise ValueError("workflow bundle changed while being read")
        if after.st_size > MAX_BUNDLE_ARCHIVE_BYTES:
            raise ValueError(f"workflow bundle exceeds {MAX_BUNDLE_ARCHIVE_BYTES} bytes")
        return raw
    finally:
        os.close(descriptor)


def _read_member_bounded(archive: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int) -> bytes:
    with archive.open(info, "r") as handle:
        chunks = []
        remaining = limit + 1
        while remaining:
            chunk = handle.read(min(_READ_CHUNK_BYTES, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
    if len(raw) > limit:
        raise ValueError("bundle member exceeds size limit")
    return raw


def _parse_object(raw: bytes) -> Dict[str, object]:
    value = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
    if not isinstance(value, dict):
        raise ValueError("bundle JSON member must be an object")
    return value


def _validate_manifest(
    manifest: Dict[str, object], workflow: Dict[str, object], workflow_bytes: bytes
) -> Optional[Tuple[str, str]]:
    if set(manifest) != {
        "schema_version",
        "workflow",
        "files",
        "connectors",
        "secret_hygiene",
    }:
        return "manifest_fields", "$.manifest"
    if manifest.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        return "manifest_schema", "$.manifest.schema_version"
    workflow_meta = manifest.get("workflow")
    if not isinstance(workflow_meta, dict):
        return "manifest_workflow", "$.manifest.workflow"
    if set(workflow_meta) != {
        "id",
        "version",
        "schema_version",
        "status",
        "bytes",
        "sha256",
    }:
        return "manifest_workflow_fields", "$.manifest.workflow"
    actual_meta = workflow.get("workflow")
    if not isinstance(actual_meta, dict):
        return "invalid_workflow", "$.workflow"
    expected = {
        "id": str(actual_meta.get("id") or ""),
        "version": str(actual_meta.get("version") or ""),
        "schema_version": str(workflow.get("schema_version") or ""),
        "status": str(actual_meta.get("status") or ""),
        "bytes": len(workflow_bytes),
        "sha256": _sha256(workflow_bytes),
    }
    if workflow_meta != expected:
        return "manifest_workflow_mismatch", "$.manifest.workflow"
    files = manifest.get("files")
    expected_file = {
        "path": "workflow.json",
        "bytes": len(workflow_bytes),
        "sha256": _sha256(workflow_bytes),
    }
    if files != [expected_file]:
        return "manifest_files_mismatch", "$.manifest.files"
    expected_connectors = _connector_ids(workflow)
    if manifest.get("connectors") != expected_connectors:
        return "manifest_connectors_mismatch", "$.manifest.connectors"
    if not isinstance(manifest.get("connectors"), list) or not all(
        isinstance(item, str) and item for item in manifest["connectors"]
    ):
        return "manifest_connectors", "$.manifest.connectors"
    if manifest.get("secret_hygiene") != {"status": "passed", "findings": 0}:
        return "manifest_secret_hygiene", "$.manifest.secret_hygiene"
    return None


def _invalid(report: Dict[str, object], code: str, path: str):
    report["errors"] = [{"code": code, "path": path}]
    return None


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _connector_ids(workflow: Dict[str, object]):
    nodes = workflow.get("nodes", [])
    if not isinstance(nodes, list):
        return []
    return sorted(
        {
            str((node.get("connector") or {}).get("id") or "")
            for node in nodes
            if isinstance(node, dict)
            and isinstance(node.get("connector"), dict)
            and str((node.get("connector") or {}).get("id") or "")
        }
    )


def _reject_json_constant(value: str):
    raise ValueError("bundle JSON must contain finite values")
