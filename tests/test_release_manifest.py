import hashlib
import json
import stat
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from scripts.release_manifest import (
    MANIFEST_SCHEMA_VERSION,
    build_release_manifest,
    write_release_manifest,
)


class ReleaseManifestTests(TestCase):
    def test_manifest_contains_archive_and_sorted_member_hashes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheel = root / "skill2workflow-0.1.0-py3-none-any.whl"
            _write_wheel(wheel)

            manifest = build_release_manifest(wheel)
            raw = wheel.read_bytes()

            self.assertEqual(manifest["schema_version"], MANIFEST_SCHEMA_VERSION)
            self.assertEqual(manifest["artifact"]["filename"], wheel.name)
            self.assertEqual(manifest["artifact"]["size_bytes"], len(raw))
            self.assertEqual(
                manifest["artifact"]["sha256"], hashlib.sha256(raw).hexdigest()
            )
            self.assertEqual(manifest["distribution"]["name"], "skill2workflow")
            self.assertEqual(manifest["distribution"]["version"], "0.1.0")
            paths = [entry["path"] for entry in manifest["files"]]
            self.assertEqual(paths, sorted(paths))
            self.assertTrue(all(len(entry["sha256"]) == 64 for entry in manifest["files"]))

    def test_manifest_write_is_atomic_and_publicly_readable(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheel = root / "skill2workflow-0.1.0-py3-none-any.whl"
            output = root / "nested" / "manifest.json"
            _write_wheel(wheel)
            manifest = build_release_manifest(wheel)

            write_release_manifest(output, manifest)

            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), manifest)
            self.assertEqual(output.stat().st_mode & 0o777, 0o644)
            self.assertEqual(list(output.parent.glob("*.tmp")), [])

    def test_manifest_rejects_traversal_duplicate_and_runtime_dependency_members(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            traversal = root / "traversal.whl"
            _write_wheel(traversal, extra={"../outside.txt": "blocked"})
            with self.assertRaisesRegex(RuntimeError, "unsafe member path"):
                build_release_manifest(traversal)

            duplicate = root / "duplicate.whl"
            _write_wheel(duplicate, duplicate_member=True)
            with self.assertRaisesRegex(RuntimeError, "duplicate"):
                build_release_manifest(duplicate)

            dependency = root / "dependency.whl"
            _write_wheel(dependency, metadata_extra="Requires-Dist: unexpected\n")
            with self.assertRaisesRegex(RuntimeError, "runtime dependencies"):
                build_release_manifest(dependency)

            symlink = root / "symlink.whl"
            _write_wheel(symlink, symlink_member=True)
            with self.assertRaisesRegex(RuntimeError, "symlink"):
                build_release_manifest(symlink)


def _write_wheel(
    path: Path,
    *,
    extra=None,
    duplicate_member: bool = False,
    metadata_extra: str = "",
    symlink_member: bool = False,
) -> None:
    metadata = (
        "Metadata-Version: 2.4\n"
        "Name: skill2workflow\n"
        "Version: 0.1.0\n"
        "Requires-Python: >=3.9\n"
        "License-Expression: Apache-2.0\n"
        + metadata_extra
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("skill2workflow/__init__.py", "__version__ = '0.1.0'\n")
        archive.writestr("skill2workflow-0.1.0.dist-info/METADATA", metadata)
        archive.writestr(
            "skill2workflow-0.1.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\nTag: py3-none-any\n",
        )
        for name, value in (extra or {}).items():
            archive.writestr(name, value)
        if duplicate_member:
            archive.writestr("skill2workflow/__init__.py", "duplicate\n")
        if symlink_member:
            info = zipfile.ZipInfo("skill2workflow/link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, "../outside")
