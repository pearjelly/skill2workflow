import copy
import json
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.cli import main
from skill2workflow.compiler import compile_ir_to_workflow
from skill2workflow.parser import parse_skill_text
from skill2workflow.preflight import build_workflow_preflight
from skill2workflow.service_client import fetch_workflow_preflight
from skill2workflow.triggers import MAX_TRIGGER_INPUT_BYTES, normalize_trigger_input


SKILL = '---\nname: input-boundary\n---\n## Steps\n1. Review <!-- skill2workflow: human_gate -->\n2. Finish\n'
ERROR = 'preflight input must be a finite JSON object of at most 1048576 UTF-8 bytes'


def exact_input(character='x'):
    overhead = len(json.dumps({'payload': ''}, separators=(',', ':')).encode('utf-8'))
    size = len(character.encode('utf-8'))
    count, remainder = divmod(MAX_TRIGGER_INPUT_BYTES - overhead, size)
    return {'payload': character * count + 'x' * remainder}


class PreflightInputBoundaryTests(TestCase):
    def setUp(self):
        self.workflow = compile_ir_to_workflow(parse_skill_text(SKILL))

    def test_installed_gate_requires_all_actual_cli_boundary_checks(self):
        from scripts import package_smoke
        from scripts.preflight_input_boundary_smoke import CHECKS
        complete = {'ok': True, 'installed': True, 'checks': {name: True for name in CHECKS}}
        for result in (complete, dict(complete, installed=False), dict(complete, checks={}),
                       dict(complete, checks=dict(complete['checks'], numeric_expansion=False))):
            with self.subTest(result=result), patch('scripts.package_smoke._run', return_value=json.dumps(result)):
                if result == complete:
                    self.assertTrue(package_smoke._qualify_installed_preflight_inputs(Path('/repo'), Path('/installed/skill2workflow'), Path('/isolated')))
                else:
                    with self.assertRaisesRegex(RuntimeError, 'qualification failed'):
                        package_smoke._qualify_installed_preflight_inputs(Path('/repo'), Path('/installed/skill2workflow'), Path('/isolated'))

    def test_exact_canonical_limit_matches_trigger_input_for_ascii_and_unicode(self):
        for character in ('x', '界'):
            value = exact_input(character)
            with self.subTest(character=character):
                self.assertEqual(normalize_trigger_input(value), value)
                self.assertTrue(build_workflow_preflight(self.workflow, value, input_present=True)['ready'])
                value['payload'] += 'x'
                with self.assertRaises(ValueError):
                    normalize_trigger_input(value)
                with self.assertRaisesRegex(ValueError, '^' + ERROR + '$'):
                    build_workflow_preflight(self.workflow, value, input_present=True)

    def test_canonical_numeric_expansion_is_bounded_not_only_source_json(self):
        wire = '{"payload":[' + ','.join(['1e5'] * 125000) + ']}'
        self.assertLess(len(wire.encode('utf-8')), MAX_TRIGGER_INPUT_BYTES)
        value = json.loads(wire)
        with self.assertRaises(ValueError):
            normalize_trigger_input(value)
        with self.assertRaisesRegex(ValueError, '^' + ERROR + '$'):
            build_workflow_preflight(self.workflow, value, input_present=True)

    def test_invalid_values_have_one_source_free_refusal_and_omitted_input_is_unchanged(self):
        cycle = {}; cycle['private-canary'] = cycle
        for value in ({'private-canary': float('nan')}, {'private-canary': float('inf')},
                      {'private-canary': '\ud800'}, {'private-canary': object()}, cycle):
            with self.subTest(kind=type(value.get('private-canary')).__name__):
                with self.assertRaisesRegex(ValueError, '^' + ERROR + '$'):
                    build_workflow_preflight(self.workflow, value, input_present=True)
        self.assertEqual(build_workflow_preflight(self.workflow, cycle), build_workflow_preflight(self.workflow))

    def test_schema_and_mappings_see_the_same_normalized_copy_as_admission(self):
        workflow = copy.deepcopy(self.workflow)
        workflow['input_schema'] = {'type': 'object', 'properties': {'payload': {'type': 'array'}}}
        supplied = {'payload': (1, 2)}
        report = build_workflow_preflight(workflow, supplied, input_present=True)
        self.assertTrue(report['ready'])
        self.assertEqual(supplied, {'payload': (1, 2)})

    def test_cli_does_not_emit_a_ready_report_for_oversize_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workflow = root / 'workflow.json'; workflow.write_text(json.dumps(self.workflow))
            supplied = root / 'input.json'; supplied.write_text(json.dumps({'private-canary': 'x' * MAX_TRIGGER_INPUT_BYTES}))
            output = StringIO()
            errors = StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                status = main(['preflight', str(workflow), '--input', str(supplied)])
            self.assertEqual(status, 1)
            self.assertEqual(output.getvalue(), '')
            self.assertEqual(errors.getvalue().strip(), ERROR)

    def test_remote_client_rejects_invalid_input_before_token_or_network_access(self):
        for value in ({'private-canary': 'x' * MAX_TRIGGER_INPUT_BYTES}, {'private-canary': float('nan')},
                      {'private-canary': '\ud800'}):
            with self.subTest(kind=type(value['private-canary']).__name__), patch('skill2workflow.service_client._post_json') as transport:
                with self.assertRaisesRegex(ValueError, '^' + ERROR + '$'):
                    fetch_workflow_preflight('http://127.0.0.1:9', Path('/missing/token'),
                                             'workflow_input_boundary', '0.1.0', input_value=value, input_present=True)
                transport.assert_not_called()
