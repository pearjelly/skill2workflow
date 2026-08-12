from pathlib import Path
from unittest import TestCase


class ContinuousIntegrationContractTests(TestCase):
    def test_ci_covers_supported_floor_and_current_stable_python(self):
        workflow = (
            Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")

        self.assertIn('python-version: ["3.9", "3.14"]', workflow)
        self.assertIn('python-version: ${{ matrix.python-version }}', workflow)
        self.assertIn("fail-fast: false", workflow)

    def test_each_ci_matrix_entry_runs_release_relevant_checks(self):
        workflow = (
            Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("python -m unittest discover -s tests -v", workflow)
        self.assertIn("python -m py_compile src/skill2workflow/*.py", workflow)
        self.assertIn("python scripts/package_smoke.py", workflow)
        self.assertIn("python scripts/secret_hygiene.py examples/workflows", workflow)
        self.assertIn(
            "python scripts/secret_hygiene.py --repository-root .", workflow
        )

    def test_contributor_guide_explains_the_compatibility_matrix(self):
        guide = (
            Path(__file__).resolve().parents[1] / "CONTRIBUTING.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Python 3.9 and 3.14", guide)
        self.assertIn("supported floor", guide)
