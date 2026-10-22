import copy
import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.compiler import compile_ir_to_workflow, validate_workflow
from skill2workflow.connectors import ConnectorExecutionError, ConnectorRuntime, execute_connector
from skill2workflow.executor import LocalExecutor
from skill2workflow.parser import parse_skill_text


def node():
    return {'id': 'check', 'type': 'tool_call', 'connector': {
        'id': 'http_assert', 'kind': 'http_assert',
        'request': {'url': 'https://example.invalid/status', 'method': 'GET'},
        'assertions': [{'path': '/ready', 'equals': True}],
    }}


class Response(BytesIO):
    status = 200
    headers = {}


class HttpAssertionTests(TestCase):
    def test_destination_policy_refuses_before_credentials_and_transport(self):
        candidate = node()
        candidate['connector']['credentials'] = [{'target': 'header', 'name': 'Authorization', 'handle': 'token'}]
        with patch('skill2workflow.connectors._apply_http_credentials') as credentials, patch('skill2workflow.connectors._open_http_request') as transport:
            with self.assertRaises(ConnectorExecutionError):
                ConnectorRuntime(http_allowed_origins=['https://allowed.invalid']).execute_connector(candidate)
            credentials.assert_not_called()
            transport.assert_not_called()

    def test_http_failures_discard_response_values(self):
        import urllib.error
        failure = urllib.error.HTTPError('https://example.invalid', 500, 'private-message', {'X-Private': 'header-secret'}, BytesIO(b'response-secret'))
        with patch('skill2workflow.connectors._open_http_request', side_effect=failure):
            result = execute_connector(node())
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['output']['status_code'], 500)
        self.assertNotIn('secret', json.dumps(result))
        self.assertEqual(result['error'], 'http assertion request failed')

    def test_public_schema_describes_bounded_assertions(self):
        schema = json.loads((Path(__file__).resolve().parents[1] / 'schemas/workflow.schema.json').read_text())
        assertions = schema['$defs']['connector_binding']['properties']['assertions']
        self.assertEqual(assertions['maxItems'], 16)
        self.assertFalse(assertions['items']['additionalProperties'])

    def test_matches_and_mismatches_return_only_fixed_summary(self):
        for body, status in ((b'{"ready":true,"private":"response-secret"}', 'completed'),
                             (b'{"ready":false,"private":"response-secret"}', 'failed'),
                             (b'{"ready":1}', 'failed'), (b'{}', 'failed')):
            with self.subTest(body=body), patch('skill2workflow.connectors._open_http_request', return_value=Response(body)):
                result = execute_connector(node())
                self.assertEqual(result['status'], status)
                self.assertEqual(result['connector']['id'], 'http_assert')
                self.assertNotIn('response-secret', json.dumps(result))
                self.assertNotIn('body', result['output'])
                self.assertNotIn('headers', result['output'])

    def test_malformed_assertions_are_rejected_before_credentials_or_transport(self):
        for assertions in ([], [{}], [{'path': '/x', 'equals': []}],
                           [{'path': '/bad~2', 'equals': True}],
                           [{'path': '/x', 'equals': float('nan')}],
                           [{'path': '/x', 'equals': True, 'unknown': 1}],
                           [{'path': '/x', 'equals': True}] * 17):
            bad = node()
            bad['connector']['assertions'] = assertions
            with self.subTest(assertions=assertions), patch('skill2workflow.connectors._open_http_request') as transport:
                with self.assertRaisesRegex(ConnectorExecutionError, '^http assertion configuration is invalid$'):
                    execute_connector(bad)
                transport.assert_not_called()

    def test_only_get_without_body_or_body_mapping_is_supported(self):
        for update in ({'method': 'POST'}, {'body': {}}, {'response_mode': 'metadata'},
                       {'input_mapping': [{'from': '/input/x', 'to': '/body/x'}]}):
            bad = node()
            bad['connector']['request'].update(update)
            with self.subTest(update=update), patch('skill2workflow.connectors._open_http_request') as transport:
                with self.assertRaises(ConnectorExecutionError):
                    execute_connector(bad)
                transport.assert_not_called()

    def test_invalid_json_duplicate_keys_and_nonfinite_numbers_fail_without_values(self):
        for payload in (b'not-json-secret', b'{"ready":true,"ready":false}', b'{"ready":NaN}', b'{"x":1e9999}'):
            with self.subTest(payload=payload), patch('skill2workflow.connectors._open_http_request', return_value=Response(payload)):
                result = execute_connector(node())
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['error'], 'http assertion response is invalid')

    def test_escaped_pointer_array_null_and_numeric_equality(self):
        candidate = node()
        candidate['connector']['assertions'] = [
            {'path': '/a~1b/~0key/0', 'equals': None}, {'path': '/n', 'equals': 1.0},
        ]
        with patch('skill2workflow.connectors._open_http_request', return_value=Response(b'{"a/b":{"~key":[null]},"n":1}')):
            self.assertEqual(execute_connector(candidate)['status'], 'completed')

    def test_validator_rejects_bad_binding_and_runtime_obeys_failure_transition(self):
        workflow = compile_ir_to_workflow(parse_skill_text('## Steps\n1. Run status probe\n2. Deliver output\n'))
        workflow['nodes'][1]['connector'] = copy.deepcopy(node()['connector'])
        self.assertEqual(validate_workflow(workflow), [])
        invalid = copy.deepcopy(workflow)
        invalid['nodes'][1]['connector']['assertions'] = []
        self.assertTrue(validate_workflow(invalid))
        for storage in ('json', 'sqlite'):
            for ready in (True, False):
                with self.subTest(storage=storage, ready=ready), TemporaryDirectory() as temporary:
                    with patch('skill2workflow.connectors._open_http_request', return_value=Response(json.dumps({'ready': ready}).encode())):
                        state = LocalExecutor(Path(temporary), storage=storage).run(workflow)
                    self.assertEqual(state['status'], 'completed' if ready else 'failed')
                    self.assertEqual(workflow['nodes'][2]['id'] in state['node_results'], ready)
