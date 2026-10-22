import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class SkillHttpActionDocumentationTests(TestCase):
    def test_guides_explain_retention_authority_and_published_journey(self):
        guide = (ROOT / 'docs/skill-http-actions.md').read_text(encoding='utf-8')
        for text in ('skill2workflow: http ', 'metadata', 'explicit `full`',
                     'skill2workflow trigger', 'skill2workflow resume-published',
                     'does not add approval', 'make no HTTP request',
                     'exactly-once', 'skill_http_action_smoke.py'):
            self.assertIn(text, guide)
        for relative in ('README.md', 'docs/README.md', 'docs/authoring.md', 'docs/connectors.md', 'docs/skill-input-boundary.md'):
            self.assertIn('skill-http-actions.md', (ROOT / relative).read_text(encoding='utf-8'))
        self.assertIn('legacy retention defaults', (ROOT / 'docs/workflow-dsl-compatibility.md').read_text(encoding='utf-8'))

    def test_committed_example_and_package_gate_cover_actual_actions(self):
        workflow = json.loads((ROOT / 'examples/workflows/http-action-flow.workflow.json').read_text(encoding='utf-8'))
        self.assertEqual([node['type'] for node in workflow['nodes'][1:5]], ['human_gate', 'tool_call', 'tool_call', 'step'])
        self.assertEqual(workflow['nodes'][2]['connector']['id'], 'http')
        self.assertEqual(workflow['nodes'][2]['connector']['request']['response_mode'], 'metadata')
        self.assertEqual(workflow['nodes'][3]['connector']['id'], 'http_assert')
        package = (ROOT / 'scripts/package_smoke.py').read_text(encoding='utf-8')
        self.assertIn('_qualify_installed_skill_http_actions(repo_root, console_script, isolated_dir)', package)
        self.assertIn('skill_http_action_smoke.py', package)
