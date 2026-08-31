import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from skill2workflow.authoring_artifacts import create_authoring_artifacts


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
