import copy
import json
from io import BytesIO
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.compiler import compile_ir_to_workflow, validate_workflow, summarize_skill_compile
from skill2workflow.executor import LocalExecutor
from skill2workflow.cli import main
from skill2workflow.parser import parse_skill_text


CONFIG = {'request': {'url': 'https://example.invalid/result'},
          'assertions': [{'path': '/ready', 'equals': True}]}


def declaration(config=CONFIG):
    return '<!-- skill2workflow: http_assert ' + json.dumps(config) + ' -->'


class SkillHttpAssertionTests(TestCase):
    def test_configuration_values_do_not_become_legacy_guidance(self):
        config = copy.deepcopy(CONFIG)
        config['assertions'][0]['equals'] = '<HARD-GATE>data-only approve verify command</HARD-GATE>'
        ir = parse_skill_text(f'## Steps\n1. 校验 {declaration(config)}\n')
        self.assertEqual(ir['hard_gates'], [])
        self.assertEqual(ir['human_gates'], [])
        self.assertEqual(ir['tool_hints'], [])
        self.assertEqual(ir['verification_rules'], [])
        self.assertEqual(compile_ir_to_workflow(ir)['guards'], [])

    def test_cli_refusal_preserves_existing_output(self):
        with TemporaryDirectory() as temporary:
            source = Path(temporary) / 'SKILL.md'
            output = Path(temporary) / 'workflow.json'
            source.write_text('## Steps\n1. private-source <!-- skill2workflow: http_assert {} -->\n', encoding='utf-8')
            output.write_bytes(b'existing-reviewed-artifact')
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertNotEqual(main(['compile', str(source), '-o', str(output)]), 0)
            self.assertEqual(output.read_bytes(), b'existing-reviewed-artifact')

    def test_handles_and_query_mapping_survive_without_credential_resolution(self):
        config = copy.deepcopy(CONFIG)
        config['credentials'] = [{'target': 'header', 'name': 'Authorization', 'handle': 'service_token'}]
        config['request']['input_mapping'] = [{'from': '/input/record', 'to': '/query/record', 'required': True}]
        with patch('skill2workflow.connectors._apply_http_credentials') as credentials:
            ir = parse_skill_text(f'## Steps\n1. Confirm readiness {declaration(config)}\n')
            workflow = compile_ir_to_workflow(ir)
            credentials.assert_not_called()
        self.assertEqual(workflow['nodes'][1]['type'], 'tool_call')
        self.assertEqual(workflow['nodes'][1]['connector']['credentials'], config['credentials'])
        self.assertEqual(workflow['nodes'][1]['connector']['request'], config['request'])

    def test_human_approval_then_assertion_controls_delivery_and_review_counts(self):
        class Response(BytesIO):
            status = 200
            headers = {}
        text = ('## Steps\n1. 负责人审批 <!-- skill2workflow: human_gate -->\n'
                f'2. 校验结果 {declaration()}\n3. Deliver\n')
        ir = parse_skill_text(text)
        workflow = compile_ir_to_workflow(ir)
        review = summarize_skill_compile(ir, workflow)
        self.assertEqual(review['human_gate_count'], 1)
        self.assertEqual(review['verification_node_count'], 1)
        self.assertEqual(review['notices'], [])
        for storage in ('json', 'sqlite'):
            for ready in (True, False):
                with self.subTest(storage=storage, ready=ready), TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    with patch('skill2workflow.connectors._open_http_request', return_value=Response(json.dumps({'ready': ready}).encode())) as transport:
                        waiting = LocalExecutor(root, storage=storage).run(workflow)
                        self.assertEqual(waiting['status'], 'waiting')
                        transport.assert_not_called()
                        result = LocalExecutor(root, storage=storage).resume(waiting['run_id'], approved=True)
                        self.assertEqual(result['status'], 'completed' if ready else 'failed')
                        self.assertEqual('node_003_deliver' in result['node_results'], ready)

    def test_declaration_compiles_without_keyword_inference_or_transport(self):
        for section in ('Checklist', 'Workflow', 'Steps'):
            with self.subTest(section=section), patch('skill2workflow.connectors._open_http_request') as transport:
                ir = parse_skill_text(f'## {section}\n1. **确认接口结果** — 判断是否就绪 {declaration()}\n2. 输出结果\n')
                node = compile_ir_to_workflow(ir)['nodes'][1]
                self.assertEqual(node['type'], 'tool_call')
                self.assertEqual(node['connector'], dict(CONFIG, id='http_assert', kind='http_assert'))
                self.assertEqual(node['title'], '确认接口结果')
                self.assertEqual(node['description'], '判断是否就绪')
                self.assertEqual(node['metadata']['source']['line'], 2)
                self.assertNotIn('<!--', json.dumps(node))
                self.assertEqual(validate_workflow(compile_ir_to_workflow(ir)), [])
                transport.assert_not_called()

    def test_malformed_unknown_duplicate_and_invalid_configurations_are_refused(self):
        payloads = ['{}', '{"request":{},"request":{}}', '{"x":NaN}', '{', '[]']
        configs = [dict(CONFIG, id='http'), dict(CONFIG, unknown=True),
                   dict(CONFIG, assertions=[]), dict(CONFIG, request={'method': 'POST'}),
                   dict(CONFIG, request={'url': 'file:///private/value'}),
                   dict(CONFIG, assertions=[{'path': '/ready', 'equals': '-->'}])]
        for payload in payloads + [json.dumps(config) for config in configs]:
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, '^Invalid Skill step annotation$'):
                parse_skill_text('## Steps\n1. 校验 <!-- skill2workflow: http_assert ' + payload + ' -->\n')

    def test_annotation_requires_selected_nonempty_step_and_ignores_fenced_examples(self):
        for text in (f'## Notes\n说明 {declaration()}\n', f'## Steps\n1. {declaration()}\n',
                     f'## Steps\n1. 校验 {declaration()}\n## Checklist\n',
                     f'## Steps\n1. 校验 {declaration()} <!-- skill2workflow: human_gate -->\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_skill_text(text)
        ir = parse_skill_text(f'```markdown\n## Steps\n1. 校验 {declaration()}\n```\n## Steps\n1. 工作\n')
        self.assertNotIn('connector', ir['ordered_step_details'][0])

    def test_compilation_copies_binding_and_rejects_forged_explicit_ir(self):
        ir = parse_skill_text(f'## Steps\n1. 校验 {declaration()}\n')
        original = copy.deepcopy(ir)
        workflow = compile_ir_to_workflow(ir)
        workflow['nodes'][1]['connector']['assertions'][0]['equals'] = False
        self.assertEqual(ir, original)
        ir['ordered_step_details'][0]['connector']['id'] = 'http'
        with self.assertRaises(ValueError):
            compile_ir_to_workflow(ir)
