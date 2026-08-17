import hashlib
import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from scripts.release_sbom import (
    SBOM_SCHEMA_VERSION,
    SPDX_VERSION,
    build_release_sbom,
    write_release_sbom,
)


class ReleaseSbomTests(TestCase):
    def test_sbom_is_spdx_23_and_matches_the_qualified_wheel(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheel = root / "skill2workflow-0.1.0-py3-none-any.whl"
            _write_wheel(wheel)

            sbom = build_release_sbom(wheel)
            self.assertEqual(sbom["spdxVersion"], SPDX_VERSION)
            self.assertEqual(sbom["SPDXID"], "SPDXRef-DOCUMENT")
            self.assertEqual(sbom["dataLicense"], "CC0-1.0")
            self.assertEqual(sbom["name"], "skill2workflow-0.1.0")
            self.assertRegex(
                sbom["creationInfo"]["created"],
                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$",
            )
            self.assertEqual(
                sbom["creationInfo"]["creators"],
                [f"Tool: {SBOM_SCHEMA_VERSION}"],
            )
            self.assertIn("wheel-sha256=", sbom["documentComment"])
            package = sbom["packages"][0]
            self.assertEqual(package["SPDXID"], "SPDXRef-Package-skill2workflow")
            self.assertEqual(package["licenseDeclared"], "Apache-2.0")
            self.assertEqual(package["externalRefs"][0]["referenceType"], "purl")
            self.assertEqual(len(sbom["files"]), 3)
            self.assertEqual(len(sbom["relationships"]), len(sbom["files"]))

            expected_hashes = {}
            with zipfile.ZipFile(wheel) as archive:
                for name in archive.namelist():
                    if not name.endswith("/"):
                        expected_hashes[name] = hashlib.sha256(
                            archive.read(name)
                        ).hexdigest()
            self.assertEqual(
                {entry["fileName"]: entry["checksums"][0]["checksumValue"] for entry in sbom["files"]},
                expected_hashes,
            )
            self.assertTrue(
                all(entry["SPDXID"].startswith("SPDXRef-File-") for entry in sbom["files"])
            )
            self.assertTrue(all(not Path(entry["fileName"]).is_absolute() for entry in sbom["files"]))
            self.assertTrue(
                all(
                    relationship["spdxElementId"] == package["SPDXID"]
                    for relationship in sbom["relationships"]
                )
            )

    def test_sbom_write_is_atomic_and_publicly_readable(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheel = root / "skill2workflow-0.1.0-py3-none-any.whl"
            output = root / "nested" / "release-artifact-sbom.json"
            _write_wheel(wheel)

            sbom = build_release_sbom(wheel)
            write_release_sbom(output, sbom)

            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), sbom)
            self.assertEqual(output.stat().st_mode & 0o777, 0o644)
            self.assertEqual(list(output.parent.glob("*.tmp")), [])

    def test_sbom_reuses_manifest_safety_boundary(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheel = root / "dependency.whl"
            _write_wheel(wheel, metadata_extra="Requires-Dist: unexpected\n")

            with self.assertRaisesRegex(RuntimeError, "runtime dependencies"):
                build_release_sbom(wheel)

            proprietary = root / "proprietary.whl"
            _write_wheel(proprietary, license_expression="Proprietary")
            with self.assertRaisesRegex(RuntimeError, "license expression"):
                build_release_sbom(proprietary)


def _write_wheel(
    path: Path,
    *,
    metadata_extra: str = "",
    license_expression: str = "Apache-2.0",
) -> None:
    metadata = (
        "Metadata-Version: 2.4\n"
        "Name: skill2workflow\n"
        "Version: 0.1.0\n"
        "Requires-Python: >=3.9\n"
        f"License-Expression: {license_expression}\n"
        + metadata_extra
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("skill2workflow/__init__.py", "__version__ = '0.1.0'\n")
        archive.writestr("skill2workflow/cli.py", "def main(): pass\n")
        archive.writestr("skill2workflow-0.1.0.dist-info/METADATA", metadata)
