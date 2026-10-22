from pathlib import Path
from unittest import TestCase

from skill2workflow.compiler import compile_ir_to_workflow
from skill2workflow.parser import parse_skill_text


ROOT = Path(__file__).resolve().parents[1]


class SkillWorkflowVersionDocumentationTests(TestCase):
    def test_complete_documented_skill_compiles_with_the_intended_identity_version_and_gate(self):
        guide = (ROOT / 'docs/skill-workflow-versions.md').read_text(encoding='utf-8')
        source = guide.split('```markdown\n', 1)[1].split('```', 1)[0]
        workflow = compile_ir_to_workflow(parse_skill_text(source))
        self.assertEqual(workflow['workflow']['id'], 'workflow_team_review')
        self.assertEqual(workflow['workflow']['version'], '0.1.0')
        self.assertEqual(workflow['nodes'][1]['type'], 'human_gate')
        next_version = compile_ir_to_workflow(parse_skill_text(source.replace('workflow_version 0.1.0', 'workflow_version 0.2.0')))
        self.assertEqual(next_version['workflow']['id'], workflow['workflow']['id'])
        self.assertEqual(next_version['workflow']['version'], '0.2.0')

    def test_guides_explain_version_intent_compatibility_and_separate_publication(self):
        guide = (ROOT / 'docs/skill-workflow-versions.md').read_text(encoding='utf-8')
        for phrase in ('1–128 ASCII', 'Invalid Skill workflow version declaration', 'version-pinned',
                       'bundle-diff', 'authoring-repair', '0.1.0', 'immutable', 'metadata', 'schema_version'):
            self.assertIn(phrase, guide)
        for path in ('README.md', 'docs/README.md', 'docs/authoring.md', 'docs/quickstart.md',
                     'docs/installed-ui.md', 'docs/stability.md', 'docs/workflow-dsl-compatibility.md', 'docs/skill-input-boundary.md'):
            self.assertIn('skill-workflow-versions.md', (ROOT / path).read_text(encoding='utf-8'))

    def test_contributor_and_artifact_guides_require_real_installed_evidence(self):
        for path in ('CONTRIBUTING.md', 'docs/release-artifact-qualification.md'):
            text = (ROOT / path).read_text(encoding='utf-8')
            self.assertIn('scripts/skill_version_smoke.py', text)
            self.assertIn('version-pinned', text)
