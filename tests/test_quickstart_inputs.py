import json
from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from skill2workflow.cli import main
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.quickstart import initialize_quickstart_workspace
from skill2workflow.triggers import MAX_TRIGGER_INPUT_BYTES


SCHEMA = {'type': 'object', 'properties': {
    'customer_id': {'type': 'string', 'minLength': 1},
    'count': {'type': 'integer', 'minimum': 1}},
    'required': ['customer_id', 'count'], 'additionalProperties': False}
INPUT = {'customer_id': 'business-input-canary', 'count': 2}
HTTP = {'request': {'method': 'POST', 'url': 'https://example.invalid/tasks',
                   'input_mapping': [{'from': '/input/customer_id', 'to': '/body/id'},
                                     {'from': '/input/count', 'to': '/body/count'}]}}


def write_skill(parent, network_first=False, assertion=False):
    source = parent / 'private-source.SKILL.md'
    schema = dict(SCHEMA, required=[]) if network_first else SCHEMA
    http = {'request': dict(HTTP['request'], input_mapping=[])} if network_first else HTTP
    if assertion:
        annotation = 'http_assert ' + json.dumps({'request': {'url': 'https://example.invalid/result'},
                                                'assertions': [{'path': '/ready', 'equals': True}]})
    else:
        annotation = 'http ' + json.dumps(http)
    steps = ['Review <!-- skill2workflow: human_gate -->',
             'Submit <!-- skill2workflow: ' + annotation + ' -->', 'Deliver']
    if network_first:
        steps[0], steps[1] = steps[1], steps[0]
    source.write_text('---\nname: input-quickstart\n---\n'
                      '<!-- skill2workflow: input_schema ' + json.dumps(schema) + ' -->\n## Steps\n'
                      + '\n'.join(str(index) + '. ' + step for index, step in enumerate(steps, 1)) + '\n',
                      encoding='utf-8')
    return source


class QuickstartInputTests(TestCase):
    def test_installed_gate_requires_every_input_and_approval_check(self):
        from scripts import package_smoke
        checks = {name: True for name in ('custom_input_waiting', 'invalid_input_no_workspace',
                  'network_prefix_refused', 'custom_input_approved_http', 'custom_input_compact_result',
                  'quickstart_preview_no_workspace', 'required_mapping_no_workspace')}
        for result in (checks, dict(checks, network_prefix_refused=False), {'custom_input_waiting': True}):
            with self.subTest(check_count=len(result)), patch('scripts.package_smoke._run', return_value=json.dumps(result)):
                if result == checks:
                    self.assertTrue(package_smoke._qualify_installed_quickstart_inputs(
                        Path('/test/python'), Path('/test/skill2workflow'), Path('/test')))
                else:
                    with self.assertRaisesRegex(RuntimeError, 'qualification failed'):
                        package_smoke._qualify_installed_quickstart_inputs(
                            Path('/test/python'), Path('/test/skill2workflow'), Path('/test'))

    def test_required_input_is_validated_before_bootstrap_even_when_omitted(self):
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            source = write_skill(parent)
            root = parent / 'workspace'
            token = Mock(return_value='q' * 48)
            with self.assertRaisesRegex(ValueError, 'required trigger input property is missing'):
                initialize_quickstart_workspace(root, skill_path=source, token_factory=token)
            token.assert_not_called()
            self.assertFalse(root.exists())

    def test_valid_input_reaches_approval_without_http_and_survives_resume(self):
        class Response(BytesIO):
            status, headers = 201, {}
        with TemporaryDirectory() as temporary, patch('skill2workflow.connectors._open_http_request',
                                                     return_value=Response(b'{}')) as transport:
            parent = Path(temporary)
            source = write_skill(parent)
            root = parent / 'workspace'
            supplied = dict(INPUT)
            result = initialize_quickstart_workspace(root, port=0, skill_path=source,
                                                    trigger_input=supplied, token_factory=lambda: 'q' * 48)
            supplied['count'] = 99
            control = LocalControlPlane(root / 'state', storage='sqlite')
            state = control.get_run(result['run_id'])
            self.assertEqual(state['status'], 'waiting')
            self.assertEqual(state['context']['input'], INPUT)
            self.assertEqual(state['context']['trigger']['source'], 'quickstart')
            transport.assert_not_called()
            self.assertNotIn('business-input-canary', json.dumps(result))
            self.assertNotIn(str(source), json.dumps(result))
            self.assertFalse((root / 'example' / 'input.json').exists())
            completed = control.resume_published_run(result['run_id'])
            self.assertEqual(completed['status'], 'completed')
            self.assertEqual(json.loads(transport.call_args.args[0].data), {'id': INPUT['customer_id'], 'count': 2})
            self.assertNotIn('business-input-canary', json.dumps(control.list_audit_events()))

    def test_invalid_contract_values_leave_no_workspace_token_or_network(self):
        for value in ({}, {'customer_id': 123, 'count': 2},
                      {'customer_id': 'private-value', 'count': 0},
                      dict(INPUT, extra='private-value')):
            with self.subTest(value_type=type(value).__name__), TemporaryDirectory() as temporary, patch(
                    'skill2workflow.connectors._open_http_request') as transport:
                parent = Path(temporary)
                source = write_skill(parent)
                root = parent / 'workspace'
                token = Mock(return_value='q' * 48)
                with self.assertRaises(ValueError) as rejected:
                    initialize_quickstart_workspace(root, skill_path=source, trigger_input=value, token_factory=token)
                self.assertNotIn('private-value', str(rejected.exception))
                self.assertFalse(root.exists())
                token.assert_not_called()
                transport.assert_not_called()

    def test_rejecting_the_input_aware_initial_gate_suppresses_http(self):
        with TemporaryDirectory() as temporary, patch('skill2workflow.connectors._open_http_request') as transport:
            parent = Path(temporary)
            root = parent / 'workspace'
            result = initialize_quickstart_workspace(root, port=0, skill_path=write_skill(parent),
                                                    trigger_input=INPUT, token_factory=lambda: 'q' * 48)
            state = LocalControlPlane(root / 'state', storage='sqlite').resume_published_run(
                result['run_id'], approved=False)
            self.assertEqual(state['status'], 'failed')
            transport.assert_not_called()

    def test_input_normalization_is_bounded_finite_and_value_free_before_bootstrap(self):
        cyclic = {}
        cyclic['self'] = cyclic
        for value in ([], {'value': float('nan')}, {'value': float('inf')}, cyclic,
                      {'value': object()}, {'value': 'private-value' + 'x' * MAX_TRIGGER_INPUT_BYTES}):
            with self.subTest(value_type=type(value).__name__), TemporaryDirectory() as temporary:
                root = Path(temporary) / 'workspace'
                token = Mock(return_value='q' * 48)
                with self.assertRaisesRegex(ValueError, 'quickstart input must be a finite JSON object') as rejected:
                    initialize_quickstart_workspace(root, trigger_input=value, token_factory=token)
                self.assertNotIn('private-value', str(rejected.exception))
                token.assert_not_called()
                self.assertFalse(root.exists())

    def test_network_before_the_first_gate_is_refused_without_bootstrap(self):
        class Response(BytesIO):
            status, headers = 200, {}
        for assertion in (False, True):
            with self.subTest(assertion=assertion), TemporaryDirectory() as temporary, patch(
                    'skill2workflow.connectors._open_http_request', return_value=Response(b'{"ready":true}')) as transport:
                parent = Path(temporary)
                source = write_skill(parent, network_first=True, assertion=assertion)
                root = parent / 'workspace'
                token = Mock(return_value='q' * 48)
                with self.assertRaisesRegex(ValueError, 'before the first human gate'):
                    initialize_quickstart_workspace(root, skill_path=source, token_factory=token)
                token.assert_not_called()
                transport.assert_not_called()
                self.assertFalse(root.exists())

    def test_cli_accepts_input_file_without_echoing_values_or_source_paths(self):
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            source = write_skill(parent)
            input_file = parent / 'private-input.json'
            input_file.write_text(json.dumps(INPUT), encoding='utf-8')
            root = parent / 'workspace'
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(['quickstart', '--root', str(root), '--skill', str(source),
                               '--input', str(input_file), '--port', '0'])
            self.assertEqual(status, 0, stderr.getvalue())
            result = json.loads(stdout.getvalue())
            self.assertEqual(result['run_status'], 'waiting')
            self.assertNotIn('business-input-canary', stdout.getvalue())
            self.assertNotIn(str(input_file), stdout.getvalue())
            self.assertNotIn(str(source), stdout.getvalue())
            state = LocalControlPlane(root / 'state', storage='sqlite').get_run(result['run_id'])
            self.assertEqual(state['context']['input'], INPUT)

    def test_cli_bad_input_files_fail_before_creating_the_workspace(self):
        for raw in (b'null', b'[]', b'{private-input-canary}', b'{"x":"\xff"}',
                    b'{"value":NaN}', b' ' * (8 * 1024 * 1024 + 1)):
            with self.subTest(prefix=raw[:20]), TemporaryDirectory() as temporary:
                parent = Path(temporary)
                input_file = parent / 'private-input.json'
                input_file.write_bytes(raw)
                root = parent / 'workspace'
                stdout, stderr = StringIO(), StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    status = main(['quickstart', '--root', str(root), '--input', str(input_file)])
                self.assertEqual(status, 1)
                self.assertFalse(root.exists())
                self.assertNotIn('private-input-canary', stdout.getvalue() + stderr.getvalue())

    def test_empty_explicit_input_is_supported_but_omission_keeps_legacy_context(self):
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for explicit in (False, True):
                root = parent / str(explicit)
                kwargs = {'trigger_input': {}} if explicit else {}
                result = initialize_quickstart_workspace(root, port=0, token_factory=lambda: 'q' * 48, **kwargs)
                context = LocalControlPlane(root / 'state', storage='sqlite').get_run(result['run_id'])['context']
                self.assertEqual(context.get('input', {}), {})
                self.assertEqual('trigger' in context, explicit)
