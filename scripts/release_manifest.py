#!/usr/bin/env python3
"""Create a value-free provenance manifest for one skill2workflow wheel."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
import zipfile
from email.parser import Parser
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional


MANIFEST_SCHEMA_VERSION = "skill2workflow-release-artifact-manifest-0.1.0"
_PACKAGE_ROOT = "skill2workflow"
_FORBIDDEN_PARTS = {"__pycache__", "pilot-evidence", "private", "secrets"}
_FORBIDDEN_SUFFIXES = {
    ".db",
    ".env",
    ".jsonl",
    ".key",
    ".pem",
    ".pyc",
    ".sqlite",
    ".sqlite3",
    ".token",
}
PACKAGED_UI_DATA_FILES = frozenset(
    {
        "data/share/skill2workflow/web/app.js",
        "data/share/skill2workflow/web/control.css",
        "data/share/skill2workflow/web/control.html",
        "data/share/skill2workflow/web/control.js",
        "data/share/skill2workflow/web/index.html",
        "data/share/skill2workflow/web/styles.css",
        "data/share/skill2workflow/web/vendor/litegraph-0.7.18/LICENSE",
        "data/share/skill2workflow/web/vendor/litegraph-0.7.18/README.md",
        "data/share/skill2workflow/web/vendor/litegraph-0.7.18/litegraph.css",
        "data/share/skill2workflow/web/vendor/litegraph-0.7.18/litegraph.min.js",
        "data/share/skill2workflow/examples/control-plane-snapshot.json",
        "data/share/skill2workflow/examples/workflows/approval-flow.litegraph.json",
        "data/share/skill2workflow/examples/workflows/approval-flow.workflow.json",
        "data/share/skill2workflow/examples/workflows/customer-service-escalation.litegraph.json",
        "data/share/skill2workflow/examples/workflows/customer-service-escalation.workflow.json",
        "data/share/skill2workflow/examples/workflows/http-connector.litegraph.json",
        "data/share/skill2workflow/examples/workflows/http-connector.workflow.json",
        "data/share/skill2workflow/examples/workflows/operations-analysis.litegraph.json",
        "data/share/skill2workflow/examples/workflows/operations-analysis.workflow.json",
        "data/share/skill2workflow/examples/workflows/risk-review.litegraph.json",
        "data/share/skill2workflow/examples/workflows/risk-review.workflow.json",
        "data/share/skill2workflow/examples/workflows/sales-follow-up.litegraph.json",
        "data/share/skill2workflow/examples/workflows/sales-follow-up.workflow.json",
    }
)


def build_release_manifest(wheel: Path) -> Dict[str, object]:
    """Return a deterministic, independently verifiable wheel manifest."""

    wheel = Path(wheel).resolve()
    try:
        raw_wheel = wheel.read_bytes()
        with zipfile.ZipFile(wheel) as archive:
            all_infos = archive.infolist()
            if any(_is_symlink(info) for info in all_infos):
                raise RuntimeError("wheel contains a symlink member")
            all_names = [info.filename for info in all_infos]
            _validate_member_names(all_names)
            if len(all_names) != len(set(all_names)):
                raise RuntimeError("wheel contains duplicate member names")
            infos = [info for info in all_infos if not info.is_dir()]
            names = [info.filename for info in infos]

            dist_info = _dist_info_root(names)
            data_root = f"{dist_info[:-len('.dist-info')]}.data"
            roots = {PurePosixPath(name).parts[0] for name in names}
            unexpected = sorted(roots - {_PACKAGE_ROOT, dist_info, data_root})
            if unexpected:
                raise RuntimeError("wheel contains unexpected top-level content")
            if data_root in roots:
                data_members = {
                    name[len(data_root) + 1 :]
                    for name in names
                    if name.startswith(f"{data_root}/")
                }
                if data_members != PACKAGED_UI_DATA_FILES:
                    raise RuntimeError("wheel data area contains unexpected or missing members")

            metadata_name = f"{dist_info}/METADATA"
            if metadata_name not in names:
                raise RuntimeError("wheel metadata is missing")
            metadata = Parser().parsestr(
                archive.read(metadata_name).decode("utf-8")
            )
            name = metadata.get("Name", "")
            version = metadata.get("Version", "")
            if name != _PACKAGE_ROOT or not version:
                raise RuntimeError("wheel metadata does not identify skill2workflow")
            if dist_info != f"{_PACKAGE_ROOT}-{version}.dist-info":
                raise RuntimeError("wheel dist-info identity does not match metadata")
            runtime_dependencies = metadata.get_all("Requires-Dist") or []
            if runtime_dependencies:
                raise RuntimeError("wheel declares unexpected runtime dependencies")

            entries = []
            for info in sorted(infos, key=lambda item: item.filename):
                content = archive.read(info)
                entries.append(
                    {
                        "path": info.filename,
                        "size_bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                )

            wheel_tags = _wheel_tags(archive, dist_info, names)
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as error:
        raise RuntimeError("wheel contents could not be inspected") from error

    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "artifact": {
            "filename": wheel.name,
            "size_bytes": len(raw_wheel),
            "sha256": hashlib.sha256(raw_wheel).hexdigest(),
        },
        "distribution": {
            "name": name,
            "version": version,
            "requires_python": metadata.get("Requires-Python", ""),
            "license_expression": metadata.get("License-Expression", ""),
            "runtime_dependencies": [],
            "wheel_tags": wheel_tags,
        },
        "files": entries,
    }


def write_release_manifest(output: Path, manifest: Dict[str, object]) -> None:
    """Atomically write one public JSON manifest without exposing source paths."""

    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{output.name}.", suffix=".tmp", dir=str(output.parent)
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o644)
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="release_manifest",
        description="Create a value-free provenance manifest for one wheel.",
    )
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = build_release_manifest(args.wheel)
        if args.output:
            write_release_manifest(args.output, manifest)
            result = {
                "status": "written",
                "schema_version": MANIFEST_SCHEMA_VERSION,
                "output": str(Path(args.output).resolve()),
                "artifact_sha256": manifest["artifact"]["sha256"],
                "file_count": len(manifest["files"]),
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


def _validate_member_names(names: List[str]) -> None:
    if not names:
        raise RuntimeError("wheel contains no files")
    paths = [PurePosixPath(name) for name in names]
    if any(
        not name
        or "\\" in name
        or path.is_absolute()
        or not path.parts
        or any(part in ("", ".", "..") for part in path.parts)
        for name, path in zip(names, paths)
    ):
        raise RuntimeError("wheel contains an unsafe member path")
    if any(
        _FORBIDDEN_PARTS.intersection(path.parts)
        or path.suffix.lower() in _FORBIDDEN_SUFFIXES
        for path in paths
    ):
        raise RuntimeError("wheel contains private or state artifacts")


def _dist_info_root(names: List[str]) -> str:
    roots = sorted(
        {
            PurePosixPath(name).parts[0]
            for name in names
            if PurePosixPath(name).parts[0].endswith(".dist-info")
        }
    )
    if len(roots) != 1:
        raise RuntimeError("wheel must contain exactly one dist-info directory")
    return roots[0]


def _wheel_tags(archive: zipfile.ZipFile, dist_info: str, names: List[str]) -> List[str]:
    wheel_name = f"{dist_info}/WHEEL"
    if wheel_name not in names:
        return []
    text = archive.read(wheel_name).decode("utf-8")
    return sorted(
        value.strip()
        for line in text.splitlines()
        if line.startswith("Tag:")
        for value in [line.split(":", 1)[1]]
        if value.strip()
    )


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_IFMT(mode) == stat.S_IFLNK


if __name__ == "__main__":
    raise SystemExit(main())
