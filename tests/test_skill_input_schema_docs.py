import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from scripts.package_smoke import _qualify_installed_skill_http_actions


ROOT = Path(__file__).resolve().parents[1]


class SkillInputSchemaDocumentationTests(TestCase):
    def test_public_guides_explain_source_admission_and_compatibility(self):
        guide = (ROOT / 'docs/skill-input-contracts.md').read_text(encoding='utf-8')
        for phrase in ('skill2workflow: input_schema ', 'standalone', '64 KiB',
                       'before', 'idempotency', 'no default injection',
                       'Invalid Skill input schema declaration', 'published', 'fenced'):
            self.assertIn(phrase, guide)
        for relative in ('README.md', 'docs/README.md', 'docs/skill-input-boundary.md',
                         'docs/skill-http-actions.md', 'docs/authoring.md', 'docs/workflow-dsl-compatibility.md'):
            self.assertIn('skill-input-contracts.md', (ROOT / relative).read_text(encoding='utf-8'))

    def test_example_declares_required_typed_inputs_without_changing_http_authority(self):
        source = (ROOT / 'examples/skills/http-action-flow/SKILL.md').read_text(encoding='utf-8')
        workflow = json.loads((ROOT / 'examples/workflows/http-action-flow.workflow.json').read_text(encoding='utf-8'))
        self.assertIn('<!-- skill2workflow: input_schema ', source)
        self.assertEqual(workflow['input_schema']['required'], ['record_id', 'title'])
        self.assertFalse(workflow['input_schema']['additionalProperties'])
        self.assertEqual(workflow['nodes'][1]['type'], 'human_gate')
        self.assertEqual(workflow['nodes'][2]['connector']['request']['response_mode'], 'metadata')

    def test_installed_gate_rejects_the_old_four_case_evidence(self):
        for count in (4, 7):
            result = json.dumps({'ok': True, 'installed': True, 'cases_verified': count})
            with self.subTest(count=count), patch('scripts.package_smoke._run', return_value=result):
                if count == 4:
                    with self.assertRaisesRegex(RuntimeError, 'qualification failed'):
                        _qualify_installed_skill_http_actions(ROOT, Path('/test/skill2workflow'), Path('/test'))
                else:
                    self.assertTrue(_qualify_installed_skill_http_actions(ROOT, Path('/test/skill2workflow'), Path('/test')))
