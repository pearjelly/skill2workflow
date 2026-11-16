import re
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]


class DocumentationConsolidationTests(TestCase):
    def test_roadmap_is_one_page_with_current_capabilities_and_exit_criteria(self):
        text = (ROOT / 'ROADMAP.md').read_text(encoding='utf-8')
        self.assertLessEqual(len(text.splitlines()), 80)
        self.assertLessEqual(len(text.split()), 650)
        for expected in ('Self-hosted Beta', '0.1.0', '0.2.0', 'decision', 'Agent',
                         'Exit criteria', 'docs/loops/history.md'):
            self.assertIn(expected, text)
        self.assertNotRegex(text, r'(?m)^### Loop \d+')
        self.assertGreaterEqual(len(re.findall(r'(?m)^\| [1-5] ', text)), 3)
        self.assertLessEqual(len(re.findall(r'(?m)^\| [1-5] ', text)), 5)

    def test_archived_history_retains_every_completed_delivery_loop(self):
        text = (ROOT / 'docs/loops/history.md').read_text(encoding='utf-8')
        loops = {int(value) for value in re.findall(r'(?m)^\| Loop (\d+):', text)}
        self.assertEqual(loops, set(range(1, 286)))

    def test_remote_contracts_share_one_reference_with_stable_section_anchors(self):
        self.assertEqual(list((ROOT / 'docs').glob('remote-*.md')), [])
        text = (ROOT / 'docs/api-reference.md').read_text(encoding='utf-8')
        anchors = [anchor for anchor in re.findall(r'<a id="(remote-[a-z-]+)"></a>', text)
                   if '--' not in anchor]
        self.assertEqual(len(anchors), 26)
        self.assertEqual(len(set(anchors)), 26)
        for resource in ('remote-trigger', 'remote-workflow-release', 'remote-schedule-create',
                         'remote-audit-events', 'remote-backup-inventory', 'remote-runtime-info'):
            self.assertIn(resource, anchors)

    def test_agent_notes_keep_core_commands_and_link_the_full_reference(self):
        notes = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        commands = notes.split('## Local Commands\n', 1)[1].split('\n## ', 1)[0]
        self.assertLessEqual(len(re.findall(r'(?m)^- .*`', commands)), 12)
        self.assertIn('docs/reference.md#command-reference', notes)
        reference = (ROOT / 'docs/reference.md').read_text(encoding='utf-8')
        self.assertIn('## Command reference', reference)
        self.assertIn('state-upgrade-plan', reference)
        self.assertIn('production_baseline_smoke.py', reference)
