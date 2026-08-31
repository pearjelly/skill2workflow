import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.authoring_artifacts import (
    create_authoring_artifacts,
    load_verified_authoring_workflow,
    verify_authoring_artifacts,
)


class AuthoringArtifactTests(TestCase):
    def test_creates_private_reviewable_artifacts_without_copying_skill_source(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / "SKILL.md"
            output_dir = root / "authoring"
            private_text = "private Skill instruction"
            skill.write_text(
                "---\nname: authoring-pack\n---\n\n## Checklist\n\n"
                f"1. {private_text}\n",
                encoding="utf-8",
            )

            result = create_authoring_artifacts(skill, output_dir)
            workflow = json.loads((output_dir / "workflow.json").read_text(encoding="utf-8"))
            graph = json.loads(
                (output_dir / "workflow.litegraph.json").read_text(encoding="utf-8")
            )
            review = json.loads(
                (output_dir / "compile-review.json").read_text(encoding="utf-8")
            )
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(output_dir.stat().st_mode & 0o777, 0o700)
            for filename in result["files"]:
                self.assertEqual(
                    (output_dir / filename).stat().st_mode & 0o777,
                    0o600,
                )
            self.assertFalse((output_dir / "SKILL.md").exists())

        self.assertEqual(result["schema_version"], "skill2workflow-authoring-artifacts-result-0.1.0")
        self.assertEqual(result["status"], "created")
        self.assertTrue(result["valid"])
        self.assertEqual(workflow["workflow"]["id"], "workflow_authoring_pack")
        self.assertEqual(graph["extra"]["truth_source"], "workflow_dsl")
        self.assertEqual(review["schema_version"], "skill2workflow-skill-compile-review-0.1.0")
        self.assertEqual(manifest["schema_version"], "skill2workflow-authoring-artifacts-0.1.0")
        self.assertNotIn(private_text, json.dumps(review))
        self.assertNotIn(private_text, json.dumps(manifest))
        self.assertEqual({item["path"] for item in manifest["files"]}, {
            "workflow.json",
            "workflow.litegraph.json",
            "compile-review.json",
        })

    def test_refuses_to_replace_an_existing_output_directory(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / "SKILL.md"
            output_dir = root / "authoring"
            skill.write_text("## Checklist\n\n1. Review draft\n", encoding="utf-8")
            output_dir.mkdir()
            sentinel = output_dir / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "must not already exist"):
                create_authoring_artifacts(skill, output_dir)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_verifies_export_without_reflecting_artifact_content(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / "SKILL.md"
            output_dir = root / "authoring"
            skill.write_text(
                "---\nname: verified-pack\n---\n\n## Checklist\n\n1. Review draft\n",
                encoding="utf-8",
            )
            create_authoring_artifacts(skill, output_dir)

            report = verify_authoring_artifacts(output_dir)

        self.assertEqual(
            report["schema_version"],
            "skill2workflow-authoring-artifacts-verification-0.1.0",
        )
        self.assertTrue(report["valid"])
        self.assertEqual(report["files"], 4)
        self.assertEqual(report["workflow"]["schema_version"], "0.1.0")
        self.assertEqual(report["errors"], [])
        self.assertNotIn("Review draft", json.dumps(report))
        self.assertNotIn("verified_pack", json.dumps(report))

    def test_verification_rejects_tampered_workflow_without_echoing_values(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / "SKILL.md"
            output_dir = root / "authoring"
            skill.write_text("## Checklist\n\n1. Review draft\n", encoding="utf-8")
            create_authoring_artifacts(skill, output_dir)
            workflow_path = output_dir / "workflow.json"
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            workflow["workflow"]["description"] = "private-tampered-authoring-value"
            workflow_path.write_text(json.dumps(workflow), encoding="utf-8")

            report = verify_authoring_artifacts(output_dir)

        self.assertFalse(report["valid"])
        self.assertEqual(report["errors"], [{"code": "artifact_file_digest_mismatch"}])
        self.assertNotIn("private-tampered-authoring-value", json.dumps(report))

    def test_verification_rejects_a_graph_that_is_not_derived_from_the_workflow(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / "SKILL.md"
            output_dir = root / "authoring"
            skill.write_text("## Checklist\n\n1. Review draft\n", encoding="utf-8")
            create_authoring_artifacts(skill, output_dir)
            graph_path = output_dir / "workflow.litegraph.json"
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            graph["extra"]["truth_source"] = "private-tampered-graph-value"
            graph_path.write_text(json.dumps(graph), encoding="utf-8")
            self._refresh_manifest_file_digest(output_dir, "workflow.litegraph.json")

            report = verify_authoring_artifacts(output_dir)

        self.assertFalse(report["valid"])
        self.assertEqual(report["errors"], [{"code": "artifact_graph_mismatch"}])
        self.assertNotIn("private-tampered-graph-value", json.dumps(report))

    def test_verification_requires_owner_only_artifacts(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / "SKILL.md"
            output_dir = root / "authoring"
            skill.write_text("## Checklist\n\n1. Review draft\n", encoding="utf-8")
            create_authoring_artifacts(skill, output_dir)
            (output_dir / "workflow.json").chmod(0o644)

            report = verify_authoring_artifacts(output_dir)

        self.assertFalse(report["valid"])
        self.assertEqual(report["errors"], [{"code": "artifact_permissions_invalid"}])

    def test_verified_load_returns_only_the_same_workflow_after_all_checks(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / "SKILL.md"
            output_dir = root / "authoring"
            skill.write_text(
                "---\nname: verified-load\n---\n\n## Checklist\n\n1. Review draft\n",
                encoding="utf-8",
            )
            create_authoring_artifacts(skill, output_dir)

            workflow = load_verified_authoring_workflow(output_dir)

        self.assertEqual(workflow["workflow"]["id"], "workflow_verified_load")

    def test_verified_load_refuses_tampered_artifacts_with_a_fixed_error(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / "SKILL.md"
            output_dir = root / "authoring"
            skill.write_text("## Checklist\n\n1. Review draft\n", encoding="utf-8")
            create_authoring_artifacts(skill, output_dir)
            (output_dir / "workflow.json").write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "verification failed"):
                load_verified_authoring_workflow(output_dir)

    @staticmethod
    def _refresh_manifest_file_digest(output_dir, filename):
        manifest_path = output_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload = (output_dir / filename).read_bytes()
        for item in manifest["files"]:
            if item["path"] == filename:
                item["bytes"] = len(payload)
                item["sha256"] = hashlib.sha256(payload).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
