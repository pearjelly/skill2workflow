import hashlib
import io
import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.bundles import (
    BUNDLE_DIFF_SCHEMA_VERSION,
    BUNDLE_SCHEMA_VERSION,
    create_workflow_bundle,
    diff_workflow_bundles,
    load_verified_workflow_bundle,
    load_verified_workflow_bundle_with_report,
    verify_workflow_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "workflows" / "approval-flow.workflow.json"


class WorkflowBundleTests(TestCase):
    def test_create_is_deterministic_and_verify_is_value_free(self):
        workflow = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.s2w"
            second = root / "second.s2w"
            first_result = create_workflow_bundle(workflow, first)
            second_result = create_workflow_bundle(workflow, second)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first_result["workflow_sha256"], second_result["workflow_sha256"])
            report = verify_workflow_bundle(first)
            with zipfile.ZipFile(first, "r") as archive:
                self.assertEqual(sorted(archive.namelist()), ["manifest.json", "workflow.json"])
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(manifest["schema_version"], BUNDLE_SCHEMA_VERSION)

        self.assertTrue(report["valid"])
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["workflow"]["id"], "workflow_approval_flow")
        self.assertEqual(report["workflow"]["version"], "0.1.0")
        self.assertNotIn("description", json.dumps(report))

    def test_verify_rejects_tampered_workflow_without_echoing_values(self):
        workflow = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "workflow.s2w"
            create_workflow_bundle(workflow, bundle)
            output = io.BytesIO()
            with zipfile.ZipFile(bundle, "r") as source, zipfile.ZipFile(output, "w") as target:
                target.writestr("manifest.json", source.read("manifest.json"))
                changed = json.loads(source.read("workflow.json"))
                changed["workflow"]["description"] = "private-value-must-not-be-echoed"
                target.writestr("workflow.json", json.dumps(changed).encode("utf-8"))
            bundle.write_bytes(output.getvalue())

            report = verify_workflow_bundle(bundle)

        self.assertFalse(report["valid"])
        self.assertEqual(report["errors"][0]["code"], "manifest_workflow_mismatch")
        self.assertNotIn("private-value-must-not-be-echoed", json.dumps(report))

    def test_create_rejects_secret_like_values_and_default_overwrite(self):
        workflow = json.loads(FIXTURE.read_text(encoding="utf-8"))
        workflow["nodes"][0]["description"] = "Bearer sk-live-secret-value"
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "workflow.s2w"
            with self.assertRaisesRegex(ValueError, "secret-like"):
                create_workflow_bundle(workflow, output)

            clean = json.loads(FIXTURE.read_text(encoding="utf-8"))
            create_workflow_bundle(clean, output)
            with self.assertRaisesRegex(ValueError, "already exists"):
                create_workflow_bundle(clean, output)

    def test_create_rejects_an_absolute_local_source_path_before_writing(self):
        workflow = json.loads(FIXTURE.read_text(encoding="utf-8"))
        workflow["nodes"][1]["metadata"]["source"]["file"] = "/private/acme/SKILL.md"
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "workflow.s2w"

            with self.assertRaisesRegex(ValueError, "local source path"):
                create_workflow_bundle(workflow, output)

            self.assertFalse(output.exists())

    def test_verify_rejects_a_digest_matched_absolute_local_source_path(self):
        workflow = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "workflow.s2w"
            create_workflow_bundle(workflow, bundle)
            changed = json.loads(json.dumps(workflow))
            changed["nodes"][1]["metadata"]["source"]["file"] = r"C:\\Users\\private\\SKILL.md"
            workflow_bytes = json.dumps(
                changed, ensure_ascii=False, sort_keys=True, indent=2
            ).encode("utf-8") + b"\n"
            with zipfile.ZipFile(bundle, "r") as archive:
                manifest = json.loads(archive.read("manifest.json"))
            digest = hashlib.sha256(workflow_bytes).hexdigest()
            manifest["workflow"]["bytes"] = len(workflow_bytes)
            manifest["workflow"]["sha256"] = digest
            manifest["files"] = [
                {"path": "workflow.json", "bytes": len(workflow_bytes), "sha256": digest}
            ]
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("manifest.json", json.dumps(manifest).encode("utf-8"))
                archive.writestr("workflow.json", workflow_bytes)

            report = verify_workflow_bundle(bundle)

        self.assertFalse(report["valid"])
        self.assertEqual(report["errors"], [{"code": "local_source_path", "path": "$.workflow"}])
        self.assertNotIn("Users", json.dumps(report))

    def test_verify_rejects_unexpected_members(self):
        with TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bad.s2w"
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("manifest.json", "{}")
                archive.writestr("workflow.json", "{}")
                archive.writestr("extra.txt", "unexpected")
            report = verify_workflow_bundle(bundle)

        self.assertFalse(report["valid"])
        self.assertEqual(report["errors"], [{"code": "too_many_members", "path": "$.members"}])

    def test_load_verified_bundle_returns_workflow_without_extraction(self):
        workflow = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "workflow.s2w"
            create_workflow_bundle(workflow, bundle)
            loaded = load_verified_workflow_bundle(bundle)
            raw_bundle = bundle.read_bytes()
            with patch(
                "skill2workflow.bundles._read_bundle_bytes",
                return_value=raw_bundle,
            ) as reader:
                loaded_with_report, report = load_verified_workflow_bundle_with_report(bundle)

        self.assertEqual(loaded, workflow)
        self.assertEqual(loaded_with_report, workflow)
        reader.assert_called_once_with(bundle)
        self.assertTrue(report["valid"])
        self.assertEqual(
            report["bundle_sha256"],
            hashlib.sha256(raw_bundle).hexdigest(),
        )

    def test_load_verified_bundle_rejects_tampering_with_fixed_error(self):
        with TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "invalid.s2w"
            bundle.write_bytes(b"not a zip")
            with self.assertRaisesRegex(ValueError, "verification failed"):
                load_verified_workflow_bundle(bundle)

    def test_diff_uses_value_free_shared_structural_contract(self):
        first_workflow = json.loads(FIXTURE.read_text(encoding="utf-8"))
        second_workflow = json.loads(FIXTURE.read_text(encoding="utf-8"))
        second_workflow["nodes"][0]["description"] = "private review text"
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.s2w"
            second = root / "second.s2w"
            create_workflow_bundle(first_workflow, first)
            create_workflow_bundle(second_workflow, second)
            report = diff_workflow_bundles(first, second)

        self.assertEqual(report["schema_version"], BUNDLE_DIFF_SCHEMA_VERSION)
        self.assertTrue(report["changed"])
        self.assertIn("nodes", report["changes"]["sections"])
        self.assertIn("start", report["changes"]["nodes"]["changed"])
        self.assertNotIn("private review text", json.dumps(report))

    def test_diff_rejects_bundles_for_different_workflow_ids(self):
        first_workflow = json.loads(FIXTURE.read_text(encoding="utf-8"))
        second_workflow = json.loads(FIXTURE.read_text(encoding="utf-8"))
        second_workflow["workflow"]["id"] = "workflow_other"
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.s2w"
            second = root / "second.s2w"
            create_workflow_bundle(first_workflow, first)
            create_workflow_bundle(second_workflow, second)
            with self.assertRaisesRegex(ValueError, "IDs must match"):
                diff_workflow_bundles(first, second)

    def test_verify_rejects_malformed_workflow_shape_without_traceback(self):
        manifest = {
            "schema_version": BUNDLE_SCHEMA_VERSION,
            "workflow": {},
            "files": [],
            "connectors": [],
            "secret_hygiene": {"status": "passed", "findings": 0},
        }
        with TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "malformed.s2w"
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("manifest.json", json.dumps(manifest))
                archive.writestr(
                    "workflow.json",
                    json.dumps(
                        {
                            "schema_version": "0.1.0",
                            "workflow": {"id": "x", "version": "0.1.0", "status": "draft"},
                            "nodes": None,
                        }
                    ),
                )
            report = verify_workflow_bundle(bundle)

        self.assertFalse(report["valid"])
        self.assertEqual(report["errors"][0]["path"], "$.manifest.workflow")
