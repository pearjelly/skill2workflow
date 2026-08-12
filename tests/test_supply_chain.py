import re
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
USE_PATTERN = re.compile(
    r"^\s*-\s+uses:\s+([^@\s]+)@([^\s#]+)\s+#\s+(v\d+\.\d+\.\d+)\s*$",
    re.MULTILINE,
)


class SupplyChainContractTests(TestCase):
    def _workflows(self):
        return sorted(WORKFLOW_DIR.glob("*.yml"))

    def test_third_party_actions_are_pinned_to_reviewable_commits(self):
        for path in self._workflows():
            workflow = path.read_text(encoding="utf-8")
            uses_lines = [
                line.strip() for line in workflow.splitlines() if "uses:" in line
            ]
            matches = USE_PATTERN.findall(workflow)

            self.assertTrue(uses_lines, path)
            self.assertEqual(len(uses_lines), len(matches), path)
            for action, revision, version in matches:
                self.assertRegex(action, r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
                self.assertRegex(revision, r"^[0-9a-f]{40}$")
                self.assertRegex(version, r"^v\d+\.\d+\.\d+$")

    def test_workflows_use_read_only_permissions_and_bounded_jobs(self):
        for path in self._workflows():
            workflow = path.read_text(encoding="utf-8")
            job_count = workflow.count("    runs-on:")

            self.assertIn("\npermissions:\n  contents: read\n", workflow, path)
            self.assertGreater(job_count, 0, path)
            self.assertEqual(
                workflow.count("    timeout-minutes: 30"), job_count, path
            )

    def test_checkout_does_not_persist_repository_credentials(self):
        for path in self._workflows():
            workflow = path.read_text(encoding="utf-8")
            checkout_steps = workflow.count("uses: actions/checkout@")

            self.assertGreater(checkout_steps, 0, path)
            self.assertEqual(
                workflow.count("          persist-credentials: false"),
                checkout_steps,
                path,
            )

    def test_dependabot_tracks_github_actions_updates(self):
        config = (ROOT / ".github" / "dependabot.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("version: 2", config)
        self.assertIn('package-ecosystem: "github-actions"', config)
        self.assertIn('directory: "/"', config)
        self.assertIn('interval: "weekly"', config)
        self.assertIn("open-pull-requests-limit: 5", config)
        self.assertIn('package-ecosystem: "pip"', config)
