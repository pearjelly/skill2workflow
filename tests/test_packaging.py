from pathlib import Path
from unittest import TestCase


class PackagingMetadataTests(TestCase):
    def test_pyproject_declares_expected_package_metadata(self):
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")

        self.assertIn('name = "skill2workflow"', text)
        self.assertIn('version = "0.1.0"', text)
        self.assertIn('readme = "README.md"', text)
        self.assertIn('requires-python = ">=3.9"', text)
        self.assertIn('license = { text = "Apache-2.0" }', text)
        self.assertIn('skill2workflow = "skill2workflow.cli:main"', text)

    def test_pyproject_keeps_runtime_dependencies_empty(self):
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")

        self.assertNotIn("[project.dependencies]", text)
        self.assertNotIn("dependencies = [", text)

    def test_package_smoke_script_verifies_editable_console_script_path(self):
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "scripts" / "package_smoke.py"
        text = script.read_text(encoding="utf-8")

        self.assertIn("--no-build-isolation", text)
        self.assertIn("-e", text)
        self.assertIn("setuptools>=68", text)
        self.assertIn("skill2workflow", text)
        self.assertIn("validate", text)
