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
        self.assertIn("python scripts/security_boundary_smoke.py", workflow)
        self.assertIn("python scripts/observability_smoke.py", workflow)
        self.assertIn("python scripts/service_boundary_smoke.py", workflow)
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
        self.assertIn("--systemd-analyze-verify", guide)

    def test_ci_verifies_generated_systemd_units_on_linux(self):
        workflow = (
            Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("systemd-verify:", workflow)
        self.assertIn("systemd_service_smoke.py", workflow)
        self.assertIn("--systemd-analyze-verify", workflow)

    def test_ci_runs_recovery_and_state_safety_gates(self):
        workflow = (
            Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("operational-gates:", workflow)
        self.assertIn("backup_restore_smoke.py", workflow)
        self.assertIn("state_upgrade_smoke.py", workflow)
        self.assertIn("retention_smoke.py", workflow)
        self.assertIn("cancellation_smoke.py", workflow)
        self.assertIn("interrupted_recovery_smoke.py", workflow)
        self.assertIn("schedule_smoke.py", workflow)
        self.assertIn("recurring_scheduler_smoke.py", workflow)
        self.assertIn("service_doctor_smoke.py", workflow)
        self.assertIn(
            "service_soak_smoke.py --work-dir /tmp/skill2workflow-service-soak-ci --cycles 3 --triggers-per-cycle 6",
            workflow,
        )

    def test_ci_runs_release_artifact_gates(self):
        workflow = (
            Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("artifact-gates:", workflow)
        self.assertIn("name: release artifact gates", workflow)
        self.assertIn(
            "package_smoke.py --work-dir /tmp/skill2workflow-package-artifact-ci",
            workflow,
        )
        self.assertIn(
            "reproducible_build.py --work-dir /tmp/skill2workflow-reproducible-build-ci",
            workflow,
        )
        self.assertIn("secret_hygiene.py --repository-root .", workflow)

    def test_contributor_and_release_docs_reproduce_production_boundary_drills(self):
        root = Path(__file__).resolve().parents[1]
        contributing = (root / "CONTRIBUTING.md").read_text(encoding="utf-8")
        release = (root / "docs" / "release-process.md").read_text(encoding="utf-8")

        for script in (
            "security_boundary_smoke.py",
            "observability_smoke.py",
            "service_boundary_smoke.py",
        ):
            self.assertIn(script, contributing)
            self.assertIn(script, release)

    def test_contributor_and_release_docs_reproduce_state_safety_gates(self):
        root = Path(__file__).resolve().parents[1]
        contributing = (root / "CONTRIBUTING.md").read_text(encoding="utf-8")
        release = (root / "docs" / "release-process.md").read_text(encoding="utf-8")

        for script in (
            "backup_restore_smoke.py",
            "state_upgrade_smoke.py",
            "retention_smoke.py",
            "cancellation_smoke.py",
            "interrupted_recovery_smoke.py",
            "schedule_smoke.py",
            "recurring_scheduler_smoke.py",
            "service_doctor_smoke.py",
        ):
            self.assertIn(script, contributing)
            self.assertIn(script, release)
