import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.agent_protocol import AGENT_PROTOCOL_VERSION
from skill2workflow.compiler import compile_ir_to_workflow, validate_workflow_structured, validate_workflow_notices
from skill2workflow.connectors import ConnectorRuntime, ExternalConnector, ConnectorExecutionError
from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.executor import LocalExecutor
from skill2workflow.external_connectors import load_external_connector
from skill2workflow.parser import parse_skill_text
from tests.test_http_assertions import Response


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'examples/connectors/deterministic_agent_connector.py'
OUTPUT = {
    'type': 'object',
    'properties': {'risk': {'type': 'string', 'enum': ['high', 'low']},
                   'reason': {'type': 'object', 'properties': {'source': {'type': 'string'}},
                              'required': ['source'], 'additionalProperties': False}},
    'required': ['risk', 'reason'], 'additionalProperties': False,
}


def source(requires=None):
    config = {'connector': 'deterministic_agent', 'instruction': 'Classify request',
              'requires': requires or [], 'output_schema': OUTPUT}
    return ('---\nname: agent-flow\n---\n## Steps\n'
            '1. Classify request <!-- skill2workflow: agent ' + json.dumps(config) + ' -->\n'
            '2. Route <!-- skill2workflow: decision {"branches":[{"when":{"path":"/nodes/1/output/risk","equals":"high"},"to":3}],"default":"end"} -->\n'
            '3. Manual approval <!-- skill2workflow: human_gate -->\n')


class AgentConnectorTests(TestCase):
    def test_agent_decision_and_human_gate_preserve_structured_output_across_restart(self):
        fixture = load_external_connector(FIXTURE)
        self.assertEqual(fixture.manifest['execution_contract']['protocol'], AGENT_PROTOCOL_VERSION)
        for storage in ('json', 'sqlite'):
            for risk in ('high', 'low'):
                with self.subTest(storage=storage, risk=risk), TemporaryDirectory() as temporary:
                    calls = []
                    def execute(payload, **kwargs):
                        calls.append(copy.deepcopy(payload))  # noqa: B023 - fixture lifetime ends in this iteration.
                        return fixture.executor(payload, **kwargs)
                    runtime = ConnectorRuntime([ExternalConnector(fixture.manifest, execute)])
                    workflow = compile_ir_to_workflow(parse_skill_text(source()))
                    self.assertEqual(workflow['schema_version'], '0.2.0')
                    self.assertEqual(validate_workflow_structured(workflow), [])
                    control = LocalControlPlane(Path(temporary), storage=storage, connector_runtime=runtime)
                    control.publish_workflow(workflow)
                    state = control.run_published_workflow('workflow_agent_flow', '0.1.0', trigger={'input': {'risk': risk, 'private': 'business-canary'}})
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(set(calls[0]), {'instruction', 'context'})
                    self.assertEqual(set(calls[0]['context']), {'input', 'nodes'})
                    self.assertEqual(calls[0]['context']['nodes'], {})
                    self.assertEqual(calls[0]['context']['input']['risk'], risk)
                    node_id = workflow['nodes'][1]['id']
                    output = state['node_results'][node_id]['output']
                    self.assertEqual(output, {'risk': risk, 'reason': {'source': 'deterministic'}})
                    if risk == 'high':
                        self.assertEqual(state['status'], 'waiting')
                        # A new process can resume with no adapter registration: the Agent already ran.
                        control = LocalControlPlane(Path(temporary), storage=storage)
                        state = control.resume_published_run(state['run_id'])
                    self.assertEqual(state['status'], 'completed')
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(control.get_run(state['run_id'])['node_results'][node_id]['output'], output)
                    self.assertNotIn('business-canary', json.dumps(control.list_audit_events(run_id=state['run_id'])))

    def test_requires_filter_node_outputs_before_calling_the_adapter(self):
        fixture = load_external_connector(FIXTURE)
        text = source().replace('1. Classify request', '3. Classify request').replace('2. Route', '4. Route').replace('3. Manual approval', '5. Manual approval')
        text = text.replace('"requires": []', '"requires": [1]').replace('/nodes/1/output/risk', '/nodes/3/output/risk').replace('"to":3', '"to":5')
        text = text.replace('## Steps\n', '## Steps\n1. Required fetch <!-- skill2workflow: http {"request":{"url":"https://example.invalid/one","response_mode":"full"}} -->\n2. Unrelated fetch <!-- skill2workflow: http {"request":{"url":"https://example.invalid/two","response_mode":"full"}} -->\n')
        workflow = compile_ir_to_workflow(parse_skill_text(text))
        calls = []
        def execute(payload, **kwargs):
            calls.append(payload)
            return fixture.executor(payload, **kwargs)
        runtime = ConnectorRuntime([ExternalConnector(fixture.manifest, execute)])
        with TemporaryDirectory() as temporary, patch('skill2workflow.connectors._open_http_request', side_effect=[Response(b'{"record":1}'), Response(b'{"private":"unrelated-canary"}')]):
            state = LocalExecutor(Path(temporary), connector_runtime=runtime).run(workflow, context={'input': {'risk': 'low'}})
        self.assertEqual(state['status'], 'completed')
        self.assertEqual(set(calls[0]['context']['nodes']), {workflow['nodes'][1]['id']})
        self.assertEqual(calls[0]['context']['nodes'][workflow['nodes'][1]['id']]['output']['body'], {'record': 1})
        self.assertNotIn('unrelated-canary', json.dumps(calls))
        self.assertFalse(any(notice['path'] == ['nodes', 3, 'requires'] for notice in validate_workflow_notices(workflow)))

    def test_invalid_or_missing_outputs_fail_without_persisting_unvalidated_values(self):
        fixture = load_external_connector(FIXTURE)
        workflow = compile_ir_to_workflow(parse_skill_text(source()))
        for output in ({'risk': 7, 'reason': {'source': 'invalid-canary'}}, [], None):
            with self.subTest(output=output), TemporaryDirectory() as temporary:
                def execute(payload, **kwargs):
                    return {'status': 'completed', 'output': output}  # noqa: B023 - fixture lifetime ends in this iteration.
                runtime = ConnectorRuntime([ExternalConnector(fixture.manifest, execute)])
                state = LocalExecutor(Path(temporary), connector_runtime=runtime).run(workflow)
                self.assertEqual(state['status'], 'failed')
                self.assertEqual(state['node_results'][workflow['nodes'][1]['id']]['output'], {})
                self.assertNotIn('invalid-canary', json.dumps(state))

    def test_missing_runtime_dependencies_do_not_invoke_an_adapter(self):
        fixture = load_external_connector(FIXTURE)
        called = []
        runtime = ConnectorRuntime([ExternalConnector(fixture.manifest, lambda *args, **kwargs: called.append(args))])
        node = {'type': 'tool_call', 'connector': {'id': 'deterministic_agent', 'kind': 'agent'},
                'action': {'kind': 'agent_instruction', 'instruction': 'Classify'},
                'requires': ['missing'], 'output_schema': OUTPUT}
        with self.assertRaises(ConnectorExecutionError):
            runtime.execute_connector(node, context={'input': {}, 'nodes': {}})
        self.assertEqual(called, [])

    def test_unregistered_adapter_cannot_turn_a_descriptive_node_into_agent_work(self):
        workflow = compile_ir_to_workflow(parse_skill_text(source()))
        with TemporaryDirectory() as temporary:
            state = LocalExecutor(Path(temporary)).run(workflow)
        self.assertEqual(state['status'], 'failed')

    def test_ordinary_external_connector_cannot_opt_into_business_output_by_spoofing_kind(self):
        fixture = load_external_connector(ROOT / 'examples/connectors/local_echo_connector.py')
        def execute(binding, **kwargs):
            return {'status': 'completed', 'output': {'risk': 'secret-canary', 'reason': {'nested': True}}}
        runtime = ConnectorRuntime([ExternalConnector(fixture.manifest, execute)])
        workflow = compile_ir_to_workflow(parse_skill_text('## Steps\n1. Prepare\n'))
        node = workflow['nodes'][1]
        node.update(type='tool_call', connector={'id': 'local_echo', 'kind': 'agent'}, action={'kind': 'agent_instruction', 'instruction': 'Classify'}, output_schema=OUTPUT)
        workflow['schema_version'] = '0.2.0'
        with TemporaryDirectory() as temporary:
            state = LocalExecutor(Path(temporary), connector_runtime=runtime).run(workflow)
        self.assertNotIn('secret-canary', json.dumps(state))

    def test_dependency_and_output_contract_validation_rejects_forward_missing_and_wrong_schemas(self):
        workflow = compile_ir_to_workflow(parse_skill_text(source()))
        for change in (lambda n: n.update(requires=['missing']),
                       lambda n: n.update(requires=[workflow['nodes'][2]['id']]),
                       lambda n: n.pop('output_schema'),
                       lambda n: n.update(output_schema={'type': 'object', 'pattern': 'unsupported'})):
            with self.subTest(change=change):
                candidate = copy.deepcopy(workflow)
                change(candidate['nodes'][1])
                self.assertTrue(validate_workflow_structured(candidate))

    def test_dependency_must_dominate_the_agent_across_all_decision_paths(self):
        config = {'connector': 'deterministic_agent', 'instruction': 'Classify', 'requires': [2], 'output_schema': OUTPUT}
        text = ('## Steps\n'
                '1. Choose <!-- skill2workflow: decision {"branches":[{"when":{"path":"/input/left","exists":true},"to":2}],"default":3} -->\n'
                '2. Left fetch <!-- skill2workflow: http {"request":{"url":"https://example.invalid/left"},"next":4} -->\n'
                '3. Right fetch <!-- skill2workflow: http {"request":{"url":"https://example.invalid/right"}} -->\n'
                '4. Classify <!-- skill2workflow: agent ' + json.dumps(config) + ' -->\n')
        with self.assertRaises(ValueError):
            compile_ir_to_workflow(parse_skill_text(text))
