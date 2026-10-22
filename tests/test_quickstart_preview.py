import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from skill2workflow.cli import main
from skill2workflow.quickstart import initialize_quickstart_workspace


def write_skill(parent, mappings, schema=None):
    source = parent / 'preview.SKILL.md'
    declaration = '' if schema is None else '<!-- skill2workflow: input_schema ' + json.dumps(schema) + ' -->\n'
    request = {'url': 'https://example.invalid/tasks', 'method': 'POST', 'input_mapping': mappings}
    source.write_text('---\nname: readiness-preview\n---\n' + declaration + '## Steps\n'
                      '1. Review <!-- skill2workflow: human_gate -->\n'
                      '2. Submit <!-- skill2workflow: http ' + json.dumps({'request': request}) + ' -->\n'
                      '3. Deliver\n', encoding='utf-8')
    return source


class QuickstartPreviewTests(TestCase):
    def test_missing_required_mapping_refuses_before_bootstrap_without_schema(self):
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            source = write_skill(parent, [{'from': '/input/customer/id', 'to': '/body/id'}])
            token = Mock(return_value='q' * 48)
            with patch('skill2workflow.connectors._open_http_request') as transport:
                for value in (None, {'customer': {}}):
                    with self.subTest(value=value), self.assertRaisesRegex(
                            ValueError, 'quickstart input does not satisfy required connector mappings'):
                        initialize_quickstart_workspace(parent / 'workspace', skill_path=source,
                                                        trigger_input=value, token_factory=token)
            self.assertFalse((parent / 'workspace').exists())
            token.assert_not_called()
            transport.assert_not_called()

    def test_typed_input_can_still_be_missing_a_required_mapping(self):
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            schema = {'type': 'object', 'properties': {'customer': {'type': 'object'}}, 'required': ['customer']}
            source = write_skill(parent, [{'from': '/input/customer/id', 'to': '/body/id'}], schema)
            with self.assertRaisesRegex(ValueError, 'required connector mappings'):
                initialize_quickstart_workspace(parent / 'workspace', skill_path=source,
                                                trigger_input={'customer': {}})
            self.assertFalse((parent / 'workspace').exists())

    def test_preview_reports_missing_contract_and_mapping_without_side_effects(self):
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            schema = {'type': 'object', 'properties': {'id': {'type': 'string'}}, 'required': ['id']}
            source = write_skill(parent, [{'from': '/input/id', 'to': '/body/id'}], schema)
            token = Mock(return_value='q' * 48)
            with patch('skill2workflow.connectors._open_http_request') as transport:
                report = initialize_quickstart_workspace(parent / 'workspace', skill_path=source,
                                                        token_factory=token, dry_run=True)
            self.assertFalse(report['ready'])
            self.assertEqual(report['schema_version'], 'skill2workflow-workflow-preflight-0.1.0')
            self.assertEqual({issue['code'] for issue in report['issues']},
                             {'input_invalid', 'required_mapping_input_missing'})
            self.assertFalse(report['input']['provided'])
            token.assert_not_called()
            transport.assert_not_called()
            self.assertEqual(set(parent.iterdir()), {source})

    def test_corrected_preview_and_initialization_share_pointer_semantics(self):
        mappings = [{'from': '/input/a~1b/~0key/0/id', 'to': '/body/id'},
                    {'from': '/input/null', 'to': '/body/nullable'},
                    {'from': '/input/absent', 'to': '/body/optional', 'required': False}]
        supplied = {'a/b': {'~key': [{'id': 'private-business-canary'}]}, 'null': None}
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            source = write_skill(parent, mappings)
            token = Mock(return_value='q' * 48)
            with patch('skill2workflow.connectors._open_http_request') as transport:
                report = initialize_quickstart_workspace(parent / 'workspace', skill_path=source,
                                                        trigger_input=supplied, dry_run=True, token_factory=token)
                self.assertTrue(report['ready'])
                self.assertEqual(report['summary']['mapping_count'], 3)
                self.assertNotIn('private-business-canary', json.dumps(report))
                self.assertNotIn(str(source), json.dumps(report))
                self.assertNotIn(str(parent / 'workspace'), json.dumps(report))
                token.assert_not_called()
                self.assertFalse((parent / 'workspace').exists())
                result = initialize_quickstart_workspace(parent / 'workspace', skill_path=source,
                                                        trigger_input=supplied, token_factory=token)
            self.assertEqual(result['run_status'], 'waiting')
            self.assertEqual(token.call_count, 1)
            transport.assert_not_called()

    def test_preview_validates_destination_host_port_without_changing_existing_data(self):
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            occupied = parent / 'occupied'
            occupied.mkdir()
            sentinel = occupied / 'keep'
            sentinel.write_bytes(b'unchanged')
            cases = [(occupied, {}), (Path('relative'), {}), (parent / 'missing' / 'new', {}),
                     (parent / 'new', {'host': '0.0.0.0'}), (parent / 'new', {'port': 65536})]
            for root, options in cases:
                with self.subTest(options=options, root=root), self.assertRaises(ValueError):
                    initialize_quickstart_workspace(root, dry_run=True, **options)
            self.assertEqual(sentinel.read_bytes(), b'unchanged')
            self.assertEqual(set(parent.iterdir()), {occupied})

    def test_cli_preview_has_preflight_exit_status_and_does_not_consume_root(self):
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            source = write_skill(parent, [{'from': '/input/id', 'to': '/body/id'}])
            root = parent / 'workspace'
            payload = parent / 'private-input.json'
            for value, expected in (({}, 1), ({'id': 'cli-private-canary'}, 0)):
                payload.write_text(json.dumps(value), encoding='utf-8')
                output, errors = StringIO(), StringIO()
                with redirect_stdout(output), redirect_stderr(errors):
                    status = main(['quickstart', '--root', str(root), '--skill', str(source),
                                   '--input', str(payload), '--dry-run'])
                self.assertEqual(status, expected, errors.getvalue())
                report = json.loads(output.getvalue())
                self.assertEqual(report['ready'], expected == 0)
                self.assertNotIn('cli-private-canary', output.getvalue())
                self.assertNotIn(str(payload), output.getvalue())
                self.assertFalse(root.exists())

    def test_preview_keeps_source_input_and_approval_boundaries(self):
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            source = write_skill(parent, [])
            original = source.read_text(encoding='utf-8')
            source.write_text(original.replace('1. Review <!-- skill2workflow: human_gate -->',
                                               '1. Prepare').replace('3. Deliver',
                                               '3. Review <!-- skill2workflow: human_gate -->'), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'before the first human gate'):
                initialize_quickstart_workspace(parent / 'workspace', skill_path=source, dry_run=True)
            source.write_text(original, encoding='utf-8')
            for value in ({'bad': float('nan')}, {'large': 'x' * 1048576},
                          {str(index): index for index in range(129)}):
                with self.subTest(keys=len(value)), self.assertRaises(ValueError):
                    initialize_quickstart_workspace(parent / 'workspace', skill_path=source,
                                                    trigger_input=value, dry_run=True)
            self.assertEqual(set(parent.iterdir()), {source})

    def test_cli_preview_preserves_fixed_filesystem_failure(self):
        output, errors = StringIO(), StringIO()
        with patch('skill2workflow.cli.initialize_quickstart_workspace',
                   side_effect=OSError('private-filesystem-canary')), redirect_stdout(output), redirect_stderr(errors):
            status = main(['quickstart', '--root', '/unused/root', '--dry-run'])
        self.assertEqual(status, 1)
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(errors.getvalue(), 'quickstart operation failed\n')
