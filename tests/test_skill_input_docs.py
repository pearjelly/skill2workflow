from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class SkillInputDocumentationTests(TestCase):
    def test_explicit_process_sections_document_precedence_and_compatibility(self):
        guide = (ROOT / "docs/skill-input-boundary.md").read_text(encoding="utf-8")
        compatibility = (ROOT / "docs/workflow-dsl-compatibility.md").read_text(encoding="utf-8")
        for phrase in (
            "## Explicit Process Sections",
            "Even an empty Checklist section",
            "`Workflow` or `Steps`",
            "More than one populated",
            "Backtick and tilde fences",
            "tests.test_process_steps",
            "historical `checklist_not_found`",
        ):
            self.assertIn(phrase, guide)
        self.assertIn("only newly compiled drafts", compatibility)
        self.assertIn("artifacts are not recompiled or reinterpreted", compatibility)
        self.assertIn("No supported ordered steps were found", (ROOT / "web/app.js").read_text(encoding="utf-8"))

    def test_skill_input_boundary_documents_the_compile_contract(self):
        guide = (ROOT / "docs" / "skill-input-boundary.md").read_text(
            encoding="utf-8"
        )

        for phrase in (
            "2,097,152",
            "2 MiB",
            "regular, non-symlink",
            "device/inode",
            "source-line mapping",
            "growth rejection",
        ):
            self.assertIn(phrase, guide)

    def test_readme_and_stability_link_to_skill_input_boundary(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        stability = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
        self.assertIn("docs/skill-input-boundary.md", readme)
        self.assertIn("docs/skill-input-boundary.md", stability)
