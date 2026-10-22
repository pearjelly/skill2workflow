import copy
import json
import sqlite3
from contextlib import closing, redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.cli import main
from skill2workflow.authoring_artifacts import create_authoring_artifacts, verify_authoring_artifacts
from skill2workflow.compiler import compile_ir_to_workflow, summarize_skill_compile, validate_workflow
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.input_schema import INPUT_SCHEMA_MAX_BYTES
from skill2workflow.parser import parse_skill_text
from skill2workflow.visualizer import apply_litegraph_edits_to_workflow, workflow_to_litegraph


SCHEMA = {
    'type': 'object',
    'properties': {
        'record_id': {'type': 'string', 'minLength': 1, 'maxLength': 64},
        'priority': {'type': 'string', 'enum': ['high', 'normal']},
        'count': {'type': 'integer', 'minimum': 1, 'maximum': 10},
        'flags': {'type': 'array', 'items': {'type': 'boolean'}},
        'note': {'type': 'null'},
    },
    'required': ['record_id'],
    'additionalProperties': False,
}
ERROR = 'Invalid Skill input schema declaration'


def declaration(schema=SCHEMA):
    return '<!-- skill2workflow: input_schema ' + json.dumps(schema, ensure_ascii=False) + ' -->'


def skill(schema=SCHEMA, section='Steps'):
    return ('---\nname: skill-input-contract\n---\n' + declaration(schema)
            + '\n## ' + section + '\n1. Deliver result\n')


class SkillInputSchemaTests(TestCase):
    def test_declared_contract_compiles_for_all_process_sections_without_io(self):
        for section in ('Checklist', 'Workflow', 'Steps'):
            with self.subTest(section=section), patch('skill2workflow.connectors._open_http_request') as transport:
                ir = parse_skill_text(skill(section=section))
                original = copy.deepcopy(ir)
                workflow = compile_ir_to_workflow(ir)
                self.assertEqual(ir['input_schema'], SCHEMA)
                self.assertEqual(workflow['input_schema'], SCHEMA)
                self.assertEqual(workflow['nodes'][1]['metadata']['source']['line'], 6)
                self.assertEqual(workflow['nodes'][1]['title'], 'Deliver result')
                self.assertEqual(validate_workflow(workflow), [])
                self.assertEqual(ir, original)
                transport.assert_not_called()

    def test_contract_is_data_not_guidance_and_creates_no_implicit_gate(self):
        schema = {'type': 'object', 'properties': {'text': {'type': 'string',
                  'enum': ['<HARD-GATE>approve verify Run: command</HARD-GATE>']}}}
        ir = parse_skill_text(skill(schema))
        for key in ('hard_gates', 'human_gates', 'tool_hints', 'verification_rules'):
            self.assertEqual(ir[key], [])
        self.assertNotIn('HARD-GATE', json.dumps(ir['sections']))
        workflow = compile_ir_to_workflow(ir)
        self.assertEqual(workflow['guards'], [])
        self.assertEqual(summarize_skill_compile(ir, workflow)['human_gate_count'], 0)
        self.assertEqual(workflow['nodes'][1]['type'], 'step')

    def test_ir_and_compiled_contracts_do_not_alias(self):
        ir = parse_skill_text(skill())
        before = copy.deepcopy(ir)
        workflow = compile_ir_to_workflow(ir)
        workflow['input_schema']['properties']['record_id']['maxLength'] = 1
        self.assertEqual(ir, before)
        self.assertEqual(compile_ir_to_workflow(ir)['input_schema'], SCHEMA)

    def test_no_declaration_preserves_open_legacy_behavior(self):
        ir = parse_skill_text('## Steps\n1. Deliver result\n')
        self.assertNotIn('input_schema', ir)
        self.assertNotIn('input_schema', compile_ir_to_workflow(ir))
        ir = parse_skill_text('---\ninput_schema: ignored metadata\n---\n## Steps\n1. Deliver\n')
        self.assertNotIn('input_schema', compile_ir_to_workflow(ir))

    def test_fenced_examples_do_not_declare_and_line_mapping_survives(self):
        for fence in ('```', '~~~~'):
            text = fence + 'markdown\n' + declaration() + '\n' + fence + '\n## Steps\n1. Deliver\n'
            ir = parse_skill_text(text)
            self.assertNotIn('input_schema', ir)
            self.assertEqual(ir['ordered_step_details'][0]['line'], 5)
            ir = parse_skill_text(text + declaration() + '\n')
            self.assertEqual(compile_ir_to_workflow(ir)['input_schema'], SCHEMA)
            self.assertEqual(ir['ordered_step_details'][0]['line'], 5)

    def test_ambiguous_or_nonstandalone_declarations_are_rejected(self):
        for text in (declaration() + '\n' + declaration(),
                     '1. Deliver ' + declaration(), 'Text ' + declaration(),
                     '    ' + declaration(), declaration() + ' trailing',
                     declaration().replace('input_schema ', 'input_schema  ', 1),
                     declaration().replace('input_schema', 'INPUT_SCHEMA', 1),
                     declaration().replace(' -->', '-->'),
                     declaration({'type': 'object', 'properties': {'x': {'type': 'string', 'enum': ['<!--nested-->']}}})):
            with self.subTest(text=text[:70]), self.assertRaisesRegex(ValueError, '^' + ERROR + '$'):
                parse_skill_text('## Steps\n' + text + '\n1. Deliver\n')

    def test_strict_json_and_fixed_errors_do_not_echo_config(self):
        for payload in ('{"type":"object","type":"object"}',
                        '{"type":"object","properties":{"x":{"type":"number","enum":[NaN]}}}',
                        '{"type":"object","properties":{"x":{"type":"number","minimum":1e999}}}',
                        '{"type":"object","properties":{"x":{"type":"integer","minimum":' + '1' * 129 + '}}}',
                        '{"type":"object",private-source}', 'null', '[]', '{}'):
            text = '<!-- skill2workflow: input_schema ' + payload + ' -->\n## Steps\n1. Deliver\n'
            with self.subTest(payload=payload[:40]), self.assertRaisesRegex(ValueError, '^' + ERROR + '$'):
                parse_skill_text(text)

    def test_existing_schema_subset_and_all_bounds_are_enforced(self):
        deep = {'type': 'object'}
        for _ in range(9):
            deep = {'type': 'object', 'properties': {'child': deep}}
        cases = [None, [], {'type': 'string'},
                 {'type': 'object', '$ref': 'private-config'},
                 {'type': 'object', 'properties': {'x': {'type': 'string', 'default': 'not-injected'}}},
                 {'type': 'object', 'required': ['undeclared']}, deep,
                 {'type': 'object', 'properties': {str(index): {'type': 'string'} for index in range(129)}},
                 {'type': 'object', 'properties': {'x': {'type': 'integer', 'enum': list(range(129))}}},
                 {'type': 'object', 'properties': {'x': {'type': 'string', 'enum': ['x' * INPUT_SCHEMA_MAX_BYTES]}}}]
        for schema in cases:
            with self.subTest(schema_type=type(schema).__name__), self.assertRaisesRegex(ValueError, '^' + ERROR + '$'):
                parse_skill_text(skill(schema))

    def test_compiler_revalidates_forged_ir_before_output(self):
        ir = parse_skill_text('## Steps\n1. Deliver\n')
        cyclic = {'type': 'object'}
        cyclic['properties'] = {'self': cyclic}
        for schema in (None, [], {'type': 'string'}, {'type': 'object', 'unknown': True}, cyclic):
            ir['input_schema'] = schema
            with self.subTest(schema_type=type(schema).__name__), self.assertRaisesRegex(ValueError, '^' + ERROR + '$'):
                compile_ir_to_workflow(ir)

    def test_cli_compile_outputs_contract_and_preserves_existing_artifact_on_refusal(self):
        with TemporaryDirectory() as temporary:
            source, output = Path(temporary) / 'SKILL.md', Path(temporary) / 'workflow.json'
            source.write_text(skill(), encoding='utf-8')
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(main(['compile', str(source), '-o', str(output)]), 0)
            self.assertEqual(json.loads(output.read_text())['input_schema'], SCHEMA)
            before = output.read_bytes()
            source.write_text(skill({'type': 'object', 'private-source': 'private-config'}), encoding='utf-8')
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertNotEqual(main(['compile', str(source), '-o', str(output)]), 0)
            self.assertEqual(output.read_bytes(), before)
            self.assertNotIn('private-config', stdout.getvalue() + stderr.getvalue())
            self.assertIn(ERROR, stderr.getvalue())

    def test_visual_roundtrip_preserves_the_uneditable_workflow_contract(self):
        workflow = compile_ir_to_workflow(parse_skill_text(skill()))
        graph = workflow_to_litegraph(workflow)
        graph['extra']['source_workflow']['input_schema'] = {'type': 'object'}
        updated = apply_litegraph_edits_to_workflow(workflow, graph)
        self.assertEqual(updated['input_schema'], SCHEMA)
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, output = root / 'SKILL.md', root / 'authoring'
            source.write_text(skill(), encoding='utf-8')
            create_authoring_artifacts(source, output)
            self.assertTrue(verify_authoring_artifacts(output)['valid'])
            portable = json.loads((output / 'workflow.json').read_text())
            self.assertEqual(portable['input_schema'], SCHEMA)
            for path in output.iterdir():
                self.assertNotIn(str(root), path.read_text())

    def test_declared_contract_rejects_before_admission_and_does_not_bypass_approval(self):
        source = (skill().replace('1. Deliver result',
                  '1. 负责人审批 <!-- skill2workflow: human_gate -->\n'
                  '2. Submit <!-- skill2workflow: http {"request":{"method":"POST","url":"https://example.invalid/tasks",'
                  '"input_mapping":[{"from":"/input/record_id","to":"/body/id"}]}} -->\n3. Deliver'))
        workflow = compile_ir_to_workflow(parse_skill_text(source))
        bad_inputs = [{}, {'record_id': 123}, {'record_id': 'r', 'count': 'private-invalid-value'},
                      {'record_id': 'r', 'extra': 'private-invalid-value'},
                      {'record_id': 'r', 'priority': 'private-invalid-value'},
                      {'record_id': 'r', 'flags': [1]}, {'record_id': 'r', 'note': ''}]
        class Response(BytesIO):
            status, headers = 201, {}
        for storage in ('json', 'sqlite'):
            with self.subTest(storage=storage), TemporaryDirectory() as temporary, patch(
                    'skill2workflow.connectors._open_http_request', return_value=Response(b'{}')) as transport:
                root = Path(temporary)
                control = LocalControlPlane(root, storage=storage)
                control.publish_workflow(workflow)
                audit = control.list_audit_events()
                for value in bad_inputs:
                    with self.assertRaises(ValueError) as rejected:
                        control.trigger_workflow({'workflow_id': workflow['workflow']['id'], 'version': '0.1.0',
                                                  'idempotency_key': 'same-key', 'input': value})
                    self.assertNotIn('private-invalid-value', str(rejected.exception))
                self.assertEqual(control.list_runs(), [])
                self.assertEqual(control.list_audit_events(), audit)
                transport.assert_not_called()
                if storage == 'sqlite':
                    with closing(sqlite3.connect(root / 'control.sqlite3')) as connection:
                        self.assertEqual(connection.execute('select count(*) from trigger_idempotency').fetchone()[0], 0)
                admitted = control.trigger_workflow({'workflow_id': workflow['workflow']['id'], 'version': '0.1.0',
                                                    'idempotency_key': 'same-key', 'input': {'record_id': 'r', 'count': 2}})
                self.assertEqual(admitted['run_status'], 'waiting')
                transport.assert_not_called()
                state = control.resume_published_run(admitted['run_id'])
                self.assertEqual(state['status'], 'completed')
                self.assertEqual(json.loads(transport.call_args.args[0].data), {'id': 'r'})
