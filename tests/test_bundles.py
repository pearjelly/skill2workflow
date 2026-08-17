import io
import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.bundles import (
    BUNDLE_SCHEMA_VERSION,
    create_workflow_bundle,
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
