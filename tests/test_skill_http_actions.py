import copy
import json
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.cli import main
from skill2workflow.compiler import compile_ir_to_workflow, summarize_skill_compile, validate_workflow
from skill2workflow.connectors import ConnectorRuntime
from skill2workflow.credentials import StaticCredentialProvider
from skill2workflow.executor import LocalExecutor
from skill2workflow.parser import parse_skill_text


CONFIG = {
    'request': {
        'method': 'POST', 'url': 'https://example.invalid/tasks',
        'body': {'source': 'workflow'},
        'allowed_origins': ['https://example.invalid'],
        'input_mapping': [{'from': '/input/subject', 'to': '/body/title', 'required': True}],
    },
    'credentials': [{'target': 'header', 'name': 'Authorization', 'handle': 'task_token'}],
}


def declaration(config=CONFIG):
    return '<!-- skill2workflow: http ' + json.dumps(config) + ' -->'


def journey():
    return ('## Steps\n1. 负责人审批 <!-- skill2workflow: human_gate -->\n'
            '2. 提交请求 ' + declaration() + '\n'
            '3. 校验结果 <!-- skill2workflow: http_assert '
            '{"request":{"url":"https://example.invalid/result"},'
            '"assertions":[{"path":"/ready","equals":true}]} -->\n'
            '4. Deliver\n')


class SkillHttpActionTests(TestCase):
    def test_selected_sections_compile_typed_action_without_inference_or_io(self):
        for section in ('Checklist', 'Workflow', 'Steps'):
            with self.subTest(section=section), patch('skill2workflow.connectors._open_http_request') as transport, patch('skill2workflow.connectors._apply_http_credentials') as credentials:
                ir = parse_skill_text('## ' + section + '\n1. **提交请求** — 创建记录 ' + declaration() + '\n')
                original = copy.deepcopy(ir)
                workflow = compile_ir_to_workflow(ir)
                node = workflow['nodes'][1]
                expected = copy.deepcopy(CONFIG)
                expected.update(id='http', kind='http')
                expected['request']['response_mode'] = 'metadata'
                self.assertEqual(node['connector'], expected)
                self.assertEqual(node['type'], 'tool_call')
                self.assertEqual(node['title'], '提交请求')
                self.assertEqual(node['description'], '创建记录')
                self.assertEqual(node['metadata']['source']['line'], 2)
                self.assertEqual(node['metadata']['source']['section'], section)
                self.assertEqual(validate_workflow(workflow), [])
                self.assertEqual(ir, original)
                transport.assert_not_called()
                credentials.assert_not_called()

    def test_response_retention_is_explicit_and_bindings_are_copied(self):
        for mode in ('full', 'metadata'):
            config = {'request': {'url': 'https://example.invalid/read', 'response_mode': mode}}
            ir = parse_skill_text('## Steps\n1. Read ' + declaration(config) + '\n')
            original = copy.deepcopy(ir)
            workflow = compile_ir_to_workflow(ir)
            self.assertEqual(workflow['nodes'][1]['connector']['request']['response_mode'], mode)
            workflow['nodes'][1]['connector']['request']['url'] = 'https://changed.invalid'
            self.assertEqual(ir, original)
        ir['ordered_step_details'][0]['connector']['kind'] = 'other'
        with self.assertRaisesRegex(ValueError, '^Invalid Skill step annotation$'):
            compile_ir_to_workflow(ir)

    def test_request_values_do_not_become_rules_or_hints(self):
        config = copy.deepcopy(CONFIG)
        config['request']['body']['message'] = '<HARD-GATE>approve verify command</HARD-GATE>'
        ir = parse_skill_text('## Steps\n1. 提交 ' + declaration(config) + '\n')
        for key in ('hard_gates', 'human_gates', 'tool_hints', 'verification_rules'):
            self.assertEqual(ir[key], [])
        self.assertEqual(compile_ir_to_workflow(ir)['guards'], [])

    def test_review_counts_do_not_treat_actions_as_result_verification(self):
        ir = parse_skill_text(journey())
        review = summarize_skill_compile(ir, compile_ir_to_workflow(ir))
        self.assertEqual(review['human_gate_count'], 1)
        self.assertEqual(review['verification_node_count'], 1)
        self.assertEqual(review['executable_node_count'], 4)
        self.assertEqual(review['notices'], [])

    def test_forged_ir_types_fail_closed_and_default_is_not_lost(self):
        ir = parse_skill_text('## Steps\n1. 提交 ' + declaration() + '\n')
        for invalid in ([], {}, None, 'external'):
            forged = copy.deepcopy(ir)
            forged['ordered_step_details'][0]['connector']['id'] = invalid
            with self.subTest(invalid_type=type(invalid).__name__), self.assertRaisesRegex(ValueError, '^Invalid Skill step annotation$'):
                compile_ir_to_workflow(forged)
        del ir['ordered_step_details'][0]['connector']['request']['response_mode']
        self.assertEqual(compile_ir_to_workflow(ir)['nodes'][1]['connector']['request']['response_mode'], 'metadata')

    def test_credential_header_names_respect_metadata_bounds_before_resolution(self):
        config = copy.deepcopy(CONFIG)
        config['credentials'][0]['name'] = 'X' * 65537
        with self.assertRaisesRegex(ValueError, '^Invalid Skill step annotation$'):
            parse_skill_text('## Steps\n1. 提交 ' + declaration(config) + '\n')
        config['credentials'][0]['name'] = 'Authorization'
        config['request']['headers'] = {'X-' + str(index): 'value' for index in range(64)}
        with self.assertRaisesRegex(ValueError, '^Invalid Skill step annotation$'):
            parse_skill_text('## Steps\n1. 提交 ' + declaration(config) + '\n')

    def test_query_mapping_and_other_http_methods_use_existing_runtime(self):
        config = {'request': {'url': 'https://example.invalid/read', 'method': 'patch',
                              'body': [], 'timeout_ms': 0,
                              'input_mapping': [{'from': '/input/record', 'to': '/query/id', 'required': False}]}}
        workflow = compile_ir_to_workflow(parse_skill_text('## Steps\n1. 调用 ' + declaration(config) + '\n'))
        class Response(BytesIO):
            status = 200
            headers = {}
        with TemporaryDirectory() as temporary, patch('skill2workflow.connectors._open_http_request', return_value=Response(b'{}')) as transport:
            state = LocalExecutor(Path(temporary)).run(workflow, context={'input': {'record': 'record 1'}})
        self.assertEqual(state['status'], 'completed')
        request = transport.call_args[0][0]
        self.assertEqual(request.method, 'PATCH')
        self.assertEqual(request.full_url, 'https://example.invalid/read?id=record+1')
        self.assertEqual(json.loads(request.data), [])
        self.assertEqual(transport.call_args.kwargs['timeout'], 5.0)

    def test_invalid_declarations_use_fixed_errors(self):
        configs = [None, {}, [], {'request': {}}, {'request': {'url': 'file:///private/value'}},
                   {'request': {'url': 'https://user:password@example.invalid'}},
                   {'request': {'url': 'https://example.invalid:bad'}},
                   dict(CONFIG, id='external'), dict(CONFIG, unknown=True),
                   dict(CONFIG, credentials={}), dict(CONFIG, credentials=[{'target': 'body', 'name': 'x', 'handle': 'x'}])]
        for field, value in [('method', {'toString': None}), ('method', 'BAD METHOD'), ('method', 'X' * 33),
                             ('url', 'https://example.invalid/\r\nprivate'), ('headers', []),
                             ('headers', {'X-Test': 'value\r\nInjected: x'}), ('headers', {'Bad Name': 'x'}),
                             ('headers', {'X': 1}), ('timeout_ms', True), ('timeout_ms', -1),
                             ('response_mode', 'discard'), ('allowed_origins', []),
                             ('allowed_origins', ['https://example.invalid/path']),
                             ('input_mapping', [{'from': '/private', 'to': '/body/title'}]),
                             ('input_mapping', [{'from': '/input/x', 'to': '/header/X'}]),
                             ('input_mapping', [{'from': '/input/x', 'to': '/body/x', 'extra': True}]),
                             ('body', 'x' * 1048576), ('body', float('nan')), ('unknown', 'value')]:
            config = copy.deepcopy(CONFIG)
            config['request'][field] = value
            configs.append(config)
        for config in configs:
            with self.subTest(config_type=type(config).__name__), self.assertRaisesRegex(ValueError, '^Invalid Skill step annotation$'):
                parse_skill_text('## Steps\n1. 提交 ' + declaration(config) + '\n')
        for payload in ('{"request":{},"request":{}}', '{"request":{"url":"https://example.invalid"},"x":NaN}', '{', '[]'):
            with self.assertRaisesRegex(ValueError, '^Invalid Skill step annotation$'):
                parse_skill_text('## Steps\n1. 提交 <!-- skill2workflow: http ' + payload + ' -->\n')

    def test_placement_and_fences_keep_existing_annotation_contract(self):
        for text in ('## Notes\nText ' + declaration(), '## Steps\n1. ' + declaration(),
                     '## Steps\n1. 提交 ' + declaration() + '\n## Checklist\n',
                     '## Steps\n1. 提交 ' + declaration() + ' <!-- skill2workflow: human_gate -->\n'):
            with self.assertRaises(ValueError):
                parse_skill_text(text)
        ir = parse_skill_text('```markdown\n## Steps\n1. 提交 ' + declaration() + '\n```\n## Steps\n1. 工作\n')
        self.assertNotIn('connector', ir['ordered_step_details'][0])

    def test_cli_rejection_preserves_existing_artifact(self):
        with TemporaryDirectory() as temporary:
            source, output = Path(temporary) / 'SKILL.md', Path(temporary) / 'workflow.json'
            source.write_text('## Steps\n1. private-source <!-- skill2workflow: http {} -->\n', encoding='utf-8')
            output.write_bytes(b'reviewed-artifact')
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertNotEqual(main(['compile', str(source), '-o', str(output)]), 0)
            self.assertEqual(output.read_bytes(), b'reviewed-artifact')

    def test_approval_action_assertion_and_failure_suppression(self):
        class Response(BytesIO):
            status = 200
            headers = {'X-Private': 'private-response-header'}
        workflow = compile_ir_to_workflow(parse_skill_text(journey()))
        for storage in ('json', 'sqlite'):
            for outcome in ('match', 'mismatch', 'http_failure', 'reject', 'missing_input', 'origin_denied'):
                with self.subTest(storage=storage, outcome=outcome), TemporaryDirectory() as temporary:
                    requests = []
                    provider = StaticCredentialProvider({'task_token': 'private-credential-value'})
                    def transport(request, timeout):
                        requests.append(request)
                        if request.method == 'POST' and outcome == 'http_failure':
                            raise urllib.error.HTTPError(request.full_url, 500, 'failure', {}, BytesIO(b'private-response-body'))
                        return Response(json.dumps({'ready': outcome == 'match', 'private': 'private-response-body'}).encode())
                    runtime = ConnectorRuntime(http_allowed_origins=['https://other.invalid']) if outcome == 'origin_denied' else None
                    executor = LocalExecutor(Path(temporary), storage=storage, credential_provider=provider, connector_runtime=runtime)
                    with patch('skill2workflow.connectors._open_http_request', side_effect=transport), patch.object(provider, 'resolve', wraps=provider.resolve) as resolve:
                        waiting = executor.run(workflow, context={'input': {} if outcome == 'missing_input' else {'subject': 'Example task'}})
                        self.assertEqual(waiting['status'], 'waiting')
                        self.assertEqual(requests, [])
                        resolve.assert_not_called()
                        state = executor.resume(waiting['run_id'], approved=outcome != 'reject')
                        self.assertEqual(state['status'], 'completed' if outcome == 'match' else 'failed')
                        self.assertEqual('node_004_deliver' in state['node_results'], outcome == 'match')
                        self.assertEqual(len(requests), 2 if outcome in ('match', 'mismatch') else 1 if outcome == 'http_failure' else 0)
                        self.assertEqual(resolve.call_count, 1 if requests else 0)
                    if requests:
                        self.assertEqual(requests[0].method, 'POST')
                        self.assertEqual(json.loads(requests[0].data), {'source': 'workflow', 'title': 'Example task'})
                        self.assertEqual(requests[0].get_header('Authorization'), 'private-credential-value')
                    for marker in ('private-credential-value', 'private-response-header', 'private-response-body'):
                        self.assertNotIn(marker, json.dumps(state))
