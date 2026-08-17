import hashlib
from pathlib import Path
from unittest import TestCase


class PackagingMetadataTests(TestCase):
    def test_license_is_the_exact_official_apache_2_0_text(self):
        license_path = Path(__file__).resolve().parents[1] / "LICENSE"
        content = license_path.read_bytes()

        self.assertEqual(
            hashlib.sha256(content).hexdigest(),
            "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
        )
        self.assertIn(
            b"APPENDIX: How to apply the Apache License to your work.", content
        )

    def test_pyproject_declares_expected_package_metadata(self):
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")

        self.assertIn('name = "skill2workflow"', text)
        self.assertIn('version = "0.1.0"', text)
        self.assertIn('readme = "README.md"', text)
        self.assertIn('requires-python = ">=3.9"', text)
        self.assertIn('license = "Apache-2.0"', text)
        self.assertIn('license-files = ["LICENSE"]', text)
        self.assertNotIn('"License :: OSI Approved :: Apache Software License"', text)
        self.assertIn('requires = ["setuptools>=77.0.1"]', text)
        self.assertIn('skill2workflow = "skill2workflow.cli:main"', text)
        self.assertIn('"Development Status :: 4 - Beta"', text)
        for version in ("3.9", "3.10", "3.11", "3.12", "3.13", "3.14"):
            self.assertIn(
                f'"Programming Language :: Python :: {version}"', text
            )
        self.assertIn('[project.urls]', text)
        self.assertIn(
            'Homepage = "https://github.com/pearjelly/skill2workflow"', text
        )
        self.assertIn(
            'Documentation = "https://github.com/pearjelly/skill2workflow/tree/main/docs"',
            text,
        )
        self.assertIn(
            'Repository = "https://github.com/pearjelly/skill2workflow"', text
        )
        self.assertIn(
            'Issues = "https://github.com/pearjelly/skill2workflow/issues"', text
        )
        self.assertIn(
            'Changelog = "https://github.com/pearjelly/skill2workflow/blob/main/CHANGELOG.md"',
            text,
        )
        self.assertIn(
            'Security = "https://github.com/pearjelly/skill2workflow/blob/main/SECURITY.md"',
            text,
        )

    def test_pyproject_keeps_runtime_dependencies_empty(self):
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")

        self.assertNotIn("[project.dependencies]", text)
        self.assertNotIn("dependencies = [", text)

    def test_installation_docs_match_minimum_build_backend(self):
        root = Path(__file__).resolve().parents[1]

        for relative in ("README.md", "CONTRIBUTING.md", "HARNESS.md"):
            text = (root / relative).read_text(encoding="utf-8")
            self.assertIn('"setuptools>=77.0.1"', text, relative)
            self.assertNotIn('"setuptools>=68"', text, relative)

    def test_public_contributor_docs_match_beta_maturity(self):
        root = Path(__file__).resolve().parents[1]

        for relative in ("CONTRIBUTING.md", "docs/stability.md"):
            text = (root / relative).read_text(encoding="utf-8")
            self.assertIn("Self-hosted Beta", text, relative)
            self.assertNotIn("pre-alpha", text, relative)

    def test_package_smoke_script_verifies_an_isolated_wheel(self):
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "scripts" / "package_smoke.py"
        text = script.read_text(encoding="utf-8")

        self.assertIn("--no-build-isolation", text)
        self.assertIn('"wheel"', text)
        self.assertNotIn('"-e"', text)
        self.assertIn("setuptools>=77.0.1", text)
        self.assertIn("PYTHONNOUSERSITE", text)
        self.assertIn('"isolated_from_source": True', text)
        self.assertIn("REQUIRED_CONSOLE_COMMANDS", text)
        self.assertIn("skill2workflow", text)
        self.assertIn('command, "--help"', text)
        self.assertIn("validate", text)
        self.assertIn("systemd-unit", text)
        self.assertIn('"live_snapshot_status": live_snapshot_status', text)
        self.assertIn('"systemd_unit_status": systemd_unit_status', text)
        self.assertIn('"release_manifest_status": True', text)
        self.assertIn("release_manifest", text)
        self.assertIn('"release_sbom_status": True', text)
        self.assertIn("release_sbom", text)

    def test_release_docs_define_isolated_wheel_qualification(self):
        root = Path(__file__).resolve().parents[1]
        release_process = (root / "docs" / "release-process.md").read_text(
            encoding="utf-8"
        )
        harness = (root / "HARNESS.md").read_text(encoding="utf-8")

        self.assertIn("isolated wheel", release_process)
        self.assertIn("scripts/package_smoke.py", release_process)
        self.assertIn("systemd-unit", release_process)
        self.assertIn("release-artifact-manifest", release_process)
        self.assertIn("release-artifact-sbom", release_process)
        self.assertIn("reproducible_build.py", release_process)
        self.assertIn("reproducible-builds.md", release_process)
        self.assertIn("service_soak_smoke.py", release_process)
        self.assertIn("service-soak.md", release_process)
        self.assertIn("production_baseline_smoke.py", release_process)
        self.assertIn("--production-baseline", release_process)
        self.assertIn("wheel", harness)
        self.assertNotIn("verifies editable install", harness)

    def test_release_artifact_qualification_is_a_scoped_completed_loop(self):
        root = Path(__file__).resolve().parents[1]
        guide = (root / "docs" / "release-artifact-qualification.md").read_text(
            encoding="utf-8"
        )
        roadmap = (root / "ROADMAP.md").read_text(encoding="utf-8")
        readme = (root / "README.md").read_text(encoding="utf-8")

        self.assertIn("# Release Artifact Qualification", guide)
        self.assertIn("wheel", guide)
        self.assertIn("PYTHONPATH", guide)
        self.assertIn("editable install", guide)
        self.assertIn("does not upload", guide)
        self.assertIn("Apache-2.0", guide)
        self.assertIn("private or state artifacts", guide)
        self.assertIn("project URLs", guide)
        self.assertIn("Changelog", guide)
        self.assertIn("Security", guide)
        self.assertIn("release-artifact-manifest.md", guide)
        self.assertIn("release-artifact-sbom.md", guide)
        self.assertIn("member SHA-256 hashes", guide)
        self.assertIn("Python 3.9 through 3.14", " ".join(guide.split()))
        self.assertIn("- Completed delivery loops: 1-152", roadmap)
        self.assertIn(
            "- Active loop: None; Loop 152 is complete with a Production Baseline evidence bundle",
            roadmap,
        )
        self.assertIn("| Loop 50: Release Artifact Qualification | Complete |", roadmap)
        self.assertIn("Delivery Loops 1-152 are complete", readme)
        self.assertIn("release-artifact qualification", readme)
        self.assertIn("release artifact manifest", readme)
        self.assertIn("reproducible-builds.md", readme)
