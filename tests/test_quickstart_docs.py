from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class InstalledQuickstartDocumentationTests(TestCase):
    def test_failure_cleanup_requires_a_stable_trusted_parent(self):
        guide = (ROOT / 'docs/quickstart.md').read_text(encoding='utf-8')
        bootstrap = (ROOT / 'docs/service-bootstrap.md').read_text(encoding='utf-8')
        for text in (guide, bootstrap):
            self.assertIn('trusted', text)
            self.assertIn('concurrent', text)
            self.assertIn('not atomic', text)
            self.assertIn('secret', text)
            self.assertIn('manual', text)

    def test_first_decision_has_both_paths_and_private_inspection_guidance(self):
        guide = (ROOT / 'docs/quickstart.md').read_text(encoding='utf-8')
        decision = guide[guide.index('## Inspect And Approve'):guide.index('## Start The Service')]
        self.assertIn('resume-published <run_id> --reject', decision)
        self.assertIn('failed', decision)
        self.assertIn('exit status', decision)
        self.assertIn('business input', decision)
        self.assertIn('not redacted', decision)
        self.assertIn('on_failure', decision)

    def test_preview_and_real_admission_share_a_bounded_non_effectful_contract(self):
        guide = (ROOT / 'docs/quickstart.md').read_text(encoding='utf-8')
        for phrase in ('--dry-run', 'dry_run=True', 'ready: false', 'same preflight',
                       'required mapping sources', '1,000 nodes', '128 top-level',
                       'not a', 'neither reserves', '21 passing checks'):
            self.assertIn(phrase, guide)
        self.assertIn('--dry-run', (ROOT / 'README.md').read_text(encoding='utf-8'))

    def test_input_aware_first_run_has_clear_admission_and_approval_boundaries(self):
        guide = (ROOT / 'docs/quickstart.md').read_text(encoding='utf-8')
        for phrase in ('--input', '1 MiB', 'before workspace', 'finite JSON',
                       'quickstart-initial', 'before the first human gate', 'not copied'):
            self.assertIn(phrase, guide)
        source_guide = (ROOT / 'docs/skill-input-contracts.md').read_text(encoding='utf-8')
        self.assertIn('quickstart --skill', source_guide)
        self.assertIn('--input', source_guide)
        self.assertNotIn('first run also has no trigger input', source_guide)

    def test_guide_documents_the_complete_installed_controlled_journey(self):
        guide = (ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8")

        self.assertIn("# Installed Controlled Quickstart", guide)
        self.assertIn("skill2workflow quickstart", guide)
        self.assertIn("ready_for_review", guide)
        self.assertIn("operator_commands", guide)
        self.assertIn("quickstart-result-0.1.0.schema.json", guide)
        self.assertIn("resume-published", guide)
        self.assertIn("skill2workflow service", guide)
        self.assertIn("human gate", guide)
        self.assertIn("must not already exist", guide)
        self.assertIn("does not call an external connector", guide)
        self.assertIn("scripts/quickstart_smoke.py", guide)

    def test_readme_leads_with_installed_quickstart_and_preserves_source_demo(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        quickstart = readme.index("skill2workflow quickstart")
        source_demo = readme.index("scripts/demo_bootstrap.py")

        self.assertLess(quickstart, source_demo)
        self.assertIn("Installed wheel quickstart", readme)
        self.assertIn("Source-checkout contributor demo", readme)
        self.assertIn("Delivery Loops 1-285 are complete", readme)
        self.assertIn("installed controlled quickstart", readme)
        fastest = readme[readme.index('## Fastest Controlled Journey'):readme.index('For executable result checks')]
        first_command = fastest.split('```bash', 1)[1].split('```', 1)[0]
        self.assertNotIn('--skill', first_command)
        self.assertNotIn('--input', first_command)
        self.assertIn('--input', fastest)
        custom_preview = fastest.split('```bash', 2)[2].split('```', 1)[0]
        self.assertIn('--skill', custom_preview)
        self.assertIn('--input', custom_preview)
        self.assertIn('--dry-run', custom_preview)

    def test_roadmap_and_harness_record_completed_loop_52(self):
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        harness = (ROOT / "HARNESS.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("- Completed delivery loops: 1-285", roadmap)
        self.assertIn(
            "- Active loop: None; Loop 285 is complete with reader-focused documentation entrypoints",
            roadmap,
        )
        self.assertIn("| Loop 52: Installed Controlled Quickstart | Complete |", roadmap)
        self.assertIn("scripts/quickstart_smoke.py", harness)
        self.assertIn("Installed controlled quickstart", agents)
