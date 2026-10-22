from unittest import TestCase

from skill2workflow.compiler import compile_ir_to_workflow
from skill2workflow.parser import parse_skill_text
from pathlib import Path
from tempfile import TemporaryDirectory
import copy
import json
import os
import subprocess
import sys


def parse(header):
    return parse_skill_text('---\n' + header + '\n---\n## Steps\n1. Review\n2. Deliver\n')


class SkillFrontmatterTests(TestCase):
    def test_long_malformed_header_has_bounded_refusal_work(self):
        code = ('from skill2workflow.parser import parse_skill_text\n'
                'try: parse_skill_text("---\\nname" + " " * 100000 + "\\n---\\n")\n'
                'except ValueError as error: print(str(error))\n'
                'ir = parse_skill_text("---\\ndescription: a" + " " * 100000 + "b\\n---\\n")\n'
                'print(len(ir["description"]))\n')
        environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
        completed = subprocess.run([sys.executable, '-c', code], env=environment, capture_output=True, text=True, timeout=5)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout.strip(), 'Invalid SKILL.md frontmatter\n100002')

    def test_portable_authoring_preserves_frontmatter_identity_without_metadata_leak(self):
        from skill2workflow.authoring_artifacts import create_authoring_artifacts, verify_authoring_artifacts
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'SKILL.md'
            source.write_text('---\nname: reviewed-workflow\ndescription: >-\n  Reviewed input.\n  Durable approval.\nmetadata:\n  name: private-metadata-canary\n---\n## Steps\n1. Review\n2. Deliver\n', encoding='utf-8')
            create_authoring_artifacts(source, root / 'export')
            workflow = json.loads((root / 'export/workflow.json').read_text())
            self.assertEqual(workflow['workflow']['id'], 'workflow_reviewed_workflow')
            self.assertEqual(workflow['workflow']['description'], 'Reviewed input. Durable approval.')
            self.assertNotIn('private-metadata-canary', json.dumps(workflow))
            self.assertTrue(verify_authoring_artifacts(root / 'export')['valid'])

    def test_installed_qualifier_rejects_wrong_identity_description_and_source_lines(self):
        from scripts.package_smoke import _require_installed_process_compile
        from skill2workflow.compiler import summarize_skill_compile
        text = '---\nname: installed-process\ndescription: >-\n  Compile reviewed input.\n  Keep the intended identity.\nmetadata:\n  name: private-metadata-name-canary\n  description: private-metadata-description-canary\n---\n\n## Steps\n\n1. Prepare output\n2. 等待负责人审核 <!-- skill2workflow: human_gate -->\n3. Verify completion\n'
        ir = parse_skill_text(text)
        workflow = compile_ir_to_workflow(ir)
        compiled = {'workflow': workflow, 'review': summarize_skill_compile(ir, workflow)}
        _require_installed_process_compile(compiled, 'Steps', 'SKILL.md', source_offset=12)
        for mutate in (lambda x: x['workflow']['workflow'].update(id='workflow_wrong'),
                       lambda x: x['workflow']['workflow'].update(description='>-'),
                       lambda x: x['workflow']['nodes'][1]['metadata']['source'].update(line=7)):
            damaged = copy.deepcopy(compiled)
            mutate(damaged)
            with self.assertRaises(RuntimeError):
                _require_installed_process_compile(damaged, 'Steps', 'SKILL.md', source_offset=12)
    def test_nested_metadata_cannot_replace_top_level_workflow_identity(self):
        ir = parse('name: reviewed-workflow\ndescription: Reviewed description.\nmetadata:\n  name: packaging-author\n  description: Packaging description.\n  version: "1.0"')
        self.assertEqual(ir['metadata']['name'], 'reviewed-workflow')
        self.assertEqual(ir['description'], 'Reviewed description.')
        self.assertEqual(ir['metadata']['metadata'], {'name': 'packaging-author', 'description': 'Packaging description.', 'version': '1.0'})
        workflow = compile_ir_to_workflow(ir)
        self.assertEqual(workflow['workflow']['id'], 'workflow_reviewed_workflow')
        self.assertEqual(workflow['workflow']['description'], 'Reviewed description.')
        self.assertEqual(parse('name: original\nmetadata: {} # empty data')['metadata']['metadata'], {})
        self.assertEqual(parse('name: original\nmetadata: {  }')['metadata']['metadata'], {})

    def test_literal_and_folded_description_chomping(self):
        for indicator, expected in [('|', 'First line.\nSecond line.\n'), ('|-', 'First line.\nSecond line.'),
                                    ('|+', 'First line.\nSecond line.\n\n'), ('>', 'First line. Second line.\n'),
                                    ('>-', 'First line. Second line.'), ('>+', 'First line. Second line.\n\n')]:
            with self.subTest(indicator=indicator):
                ir = parse('name: text-example\ndescription: ' + indicator + '\n  First line.\n  Second line.\n')
                self.assertEqual(ir['description'], expected)
                self.assertEqual(ir['ordered_step_details'][0]['line'], 9)

    def test_block_scalar_content_is_not_parsed_as_metadata_or_guidance(self):
        ir = parse('name: original\ndescription: |-\n  name: not-an-identity\n  metadata:\n    name: still-text\n  <!-- skill2workflow: human_gate -->\n  1. approval\nlicense: Apache-2.0')
        self.assertEqual(ir['metadata']['name'], 'original')
        self.assertIn('name: not-an-identity', ir['description'])
        self.assertEqual(ir['metadata']['license'], 'Apache-2.0')
        self.assertEqual(ir['ordered_steps'], ['Review', 'Deliver'])
        self.assertEqual(ir['human_gates'], [])

    def test_folded_paragraphs_and_more_indented_lines(self):
        ir = parse('description: >-\n  First line\n  continued.\n\n  Second paragraph.\n    indented code\n  Final line.')
        self.assertEqual(ir['description'], 'First line continued.\nSecond paragraph.\n  indented code\nFinal line.')

    def test_explicit_indentation_and_empty_scalars(self):
        for indicator in ('|2-', '|-2'):
            self.assertEqual(parse('description: ' + indicator + '\n    indented\n  ordinary')['description'], '  indented\nordinary')
        for indicator in ('|', '>', '|-', '>-'):
            self.assertEqual(parse('description: ' + indicator)['description'], '')

    def test_block_content_retains_delimiters_and_extra_spaces(self):
        ir = parse('name: original\ndescription: |-\n  before\n  ---\n    \n  after')
        self.assertEqual(ir['description'], 'before\n---\n  \nafter')
        self.assertEqual(ir['metadata']['name'], 'original')
        self.assertEqual(parse('description: |+\n    \n    ')['description'], '\n\n')
        self.assertEqual(parse('description: |2\n    \n  text')['description'], '  \ntext\n')

    def test_comment_only_and_yaml_constructs_are_not_literal_identity(self):
        self.assertEqual(parse('description: # comment')['description'], '')
        for value in ('- private-value-canary', '? private-value-canary', ': private-value-canary', '-', '?', ':'):
            with self.assertRaisesRegex(ValueError, '^Invalid SKILL.md frontmatter$'):
                parse('name: ' + value)

    def test_quotes_and_comments_keep_only_the_scalar_value(self):
        cases = [
            ('name: "quoted-name" # comment', 'name', 'quoted-name'),
            ("description: 'It''s a # literal: value' # comment", 'description', "It's a # literal: value"),
            ('description: "Line\\nwith \\"quoted\\" text"', 'description', 'Line\nwith "quoted" text'),
            ('description: https://example.invalid/path#fragment # ignored', 'description', 'https://example.invalid/path#fragment'),
            ('description: true', 'description', 'true'), ('description: 123', 'description', '123'),
        ]
        for header, key, expected in cases:
            with self.subTest(header=header):
                self.assertEqual(parse(header)['metadata'][key], expected)
        self.assertEqual(parse('# name: fake\nname: real')['metadata']['name'], 'real')

    def test_duplicate_or_ambiguous_frontmatter_fails_without_echoing_values(self):
        for header in [
            'name: first\nname: private-value-canary',
            'metadata:\n  name: first\n  name: private-value-canary',
            'description: "private-value-canary', 'description: \'private-value-canary',
            'description: |0\n  private-value-canary', 'description: >--\n  private-value-canary',
            'description: |\n  valid\n broken: private-value-canary',
            'description: *private-value-canary', 'name: &private-value-canary value',
            'description: !!str private-value-canary', 'name: [private-value-canary]',
            'metadata:\n  nested:\n    name: private-value-canary',
        ]:
            with self.subTest(header=header):
                with self.assertRaises(ValueError) as caught:
                    parse(header)
                self.assertEqual(str(caught.exception), 'Invalid SKILL.md frontmatter')

    def test_absent_and_unclosed_frontmatter_keep_legacy_body_behavior(self):
        for text in ('## Steps\n1. Review', '---\nname: unfinished\n## Steps\n1. Review'):
            self.assertEqual(parse_skill_text(text)['ordered_steps'], ['Review'])
