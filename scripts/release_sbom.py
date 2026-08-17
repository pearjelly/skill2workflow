#!/usr/bin/env python3
"""Create a value-free SPDX 2.3 SBOM for one skill2workflow wheel."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    from release_manifest import build_release_manifest
except ImportError:  # pragma: no cover - exercised when imported as scripts.release_sbom
    from scripts.release_manifest import build_release_manifest


SBOM_SCHEMA_VERSION = "skill2workflow-release-sbom-0.1.0"
SPDX_VERSION = "SPDX-2.3"
_PACKAGE_SPDX_ID = "SPDXRef-Package-skill2workflow"


def build_release_sbom(wheel: Path) -> Dict[str, object]:
    """Return an SPDX 2.3 document derived from the qualified wheel manifest."""

    manifest = build_release_manifest(Path(wheel))
    artifact = manifest["artifact"]
    distribution = manifest["distribution"]
    files = manifest["files"]
    package_name = str(distribution["name"])
    version = str(distribution["version"])
    wheel_sha256 = str(artifact["sha256"])

    spdx_files = []
    relationships = []
    for entry in files:
        path = str(entry["path"])
        file_id = _file_spdx_id(path)
        spdx_files.append(
            {
                "SPDXID": file_id,
                "fileName": path,
                "checksums": [
                    {
                        "algorithm": "SHA256",
                        "checksumValue": str(entry["sha256"]),
                    }
                ],
                "licenseConcluded": "NOASSERTION",
                "copyrightText": "NOASSERTION",
            }
        )
        relationships.append(
            {
                "spdxElementId": _PACKAGE_SPDX_ID,
                "relationshipType": "CONTAINS",
                "relatedSpdxElement": file_id,
            }
        )

    license_expression = str(distribution.get("license_expression") or "NOASSERTION")
    if license_expression not in {"Apache-2.0", "NOASSERTION"}:
        raise RuntimeError("wheel license expression is unsupported")
    document_namespace = (
        "https://github.com/pearjelly/skill2workflow/releases/download/"
        f"v{version}/{package_name}-{version}.spdx.json"
    )
    return {
        "spdxVersion": SPDX_VERSION,
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{package_name}-{version}",
        "documentNamespace": document_namespace,
        "creationInfo": {
            "created": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "creators": [f"Tool: {SBOM_SCHEMA_VERSION}"],
        },
        "documentComment": (
            f"{SBOM_SCHEMA_VERSION}; wheel-sha256={wheel_sha256}"
        ),
        "packages": [
            {
                "SPDXID": _PACKAGE_SPDX_ID,
                "name": package_name,
                "versionInfo": version,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": True,
                "licenseConcluded": license_expression,
                "licenseDeclared": license_expression,
                "copyrightText": "NOASSERTION",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": f"pkg:pypi/{package_name}@{version}",
                    }
                ],
            }
        ],
        "files": spdx_files,
        "relationships": relationships,
    }


def write_release_sbom(output: Path, sbom: Dict[str, object]) -> None:
    """Atomically write one public SPDX document without exposing source paths."""

    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(sbom, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
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
        prog="release_sbom",
        description="Create a value-free SPDX 2.3 SBOM for one wheel.",
    )
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        sbom = build_release_sbom(args.wheel)
        if args.output:
            write_release_sbom(args.output, sbom)
            package = sbom["packages"][0]
            result = {
                "status": "written",
                "schema_version": SBOM_SCHEMA_VERSION,
                "spdx_version": SPDX_VERSION,
                "output": str(Path(args.output).resolve()),
                "wheel_sha256": _wheel_sha256(sbom),
                "file_count": len(sbom["files"]),
                "package": package["name"],
                "version": package["versionInfo"],
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(sbom, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1


def _file_spdx_id(path: str) -> str:
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()
    return f"SPDXRef-File-{digest}"


def _wheel_sha256(sbom: Dict[str, object]) -> str:
    comment = str(sbom.get("documentComment", ""))
    prefix = f"{SBOM_SCHEMA_VERSION}; wheel-sha256="
    if not comment.startswith(prefix):
        raise ValueError("SBOM document comment is malformed")
    return comment[len(prefix) :]


if __name__ == "__main__":
    raise SystemExit(main())
