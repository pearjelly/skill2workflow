"""Keep the documented JSON shapes and the dependency-free validator aligned."""

import copy
import json
from pathlib import Path
from unittest import TestCase, skipUnless

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None

from skill2workflow.compiler import compile_ir_to_workflow, validate_workflow_structured
from skill2workflow.parser import parse_skill_text

ROOT = Path(__file__).resolve().parents[1]
MISSING = object()


@skipUnless(Draft202012Validator, "JSON Schema conformance requires development dependencies (requirements-dev.txt)")
class WorkflowSchemaConformanceTests(TestCase):
    def schema_valid(self, workflow):
        version = workflow.get('schema_version') if isinstance(workflow, dict) else None
        name = 'workflow-0.2.0.schema.json' if version == '0.2.0' else 'workflow.schema.json'
        schema = json.loads((ROOT / 'schemas' / name).read_text())
        Draft202012Validator.check_schema(schema)
        return Draft202012Validator(schema).is_valid(workflow)

    def assert_agreement(self, workflow, valid):
        schema_valid = self.schema_valid(workflow)
        errors = validate_workflow_structured(workflow)
        self.assertEqual(schema_valid, valid, 'JSON Schema verdict')
        self.assertEqual(not errors, valid, errors)

    def test_all_committed_workflow_examples_pass_both_contracts(self):
        for path in sorted((ROOT / 'examples/workflows').glob('*.workflow.json')):
            with self.subTest(example=path.name):
                self.assert_agreement(json.loads(path.read_text()), True)
        from tests.test_agent_connector import source
        self.assert_agreement(compile_ir_to_workflow(parse_skill_text(source())), True)

    def test_illegal_known_field_shapes_have_matching_verdicts(self):
        original = json.loads((ROOT / 'examples/workflows/approval-flow.workflow.json').read_text())
        cases = []
        for key in ('schema_version', 'workflow', 'entry', 'nodes', 'edges'):
            cases.append(('missing ' + key, (key,), MISSING))
        for key in ('id', 'name', 'version', 'status'):
            cases.extend([(key + ' missing', ('workflow', key), MISSING),
                          (key + ' nonstring', ('workflow', key), 7),
                          (key + ' empty', ('workflow', key), '')])
        cases.append(('unknown lifecycle', ('workflow', 'status'), 'unknown'))
        for key in ('id', 'type', 'title'):
            cases.extend([(key + ' absent', ('nodes', 1, key), MISSING),
                          (key + ' nonstring', ('nodes', 1, key), 7),
                          (key + ' empty', ('nodes', 1, key), '')])
        cases.extend([
            ('schema version not string', ('schema_version',), []),
            ('entry not string', ('entry',), []),
            ('unknown type', ('nodes', 1, 'type'), 'mystery'),
            ('nodes not array', ('nodes',), {}), ('edges not array', ('edges',), {}),
            ('state schema not object', ('state_schema',), []), ('guards not array', ('guards',), {}),
            ('guard definition invalid', ('guards',), [{'id': 'g'}]),
            ('checkpoints not array', ('checkpoints',), {}), ('checkpoint not object', ('checkpoints',), [3]),
            ('requires not array', ('nodes', 1, 'requires'), 'input'), ('requires item', ('nodes', 1, 'requires'), [3]),
            ('produces not array', ('nodes', 1, 'produces'), 'result'), ('produces item', ('nodes', 1, 'produces'), [3]),
            ('guard invalid', ('nodes', 1, 'guard'), []), ('action invalid', ('nodes', 1, 'action'), []),
            ('metadata invalid', ('nodes', 1, 'metadata'), []), ('description invalid', ('nodes', 1, 'description'), 7),
            ('retry invalid', ('nodes', 1, 'retry'), []), ('negative retry', ('nodes', 1, 'retry'), {'max_attempts': -1}),
            ('timeout invalid', ('nodes', 1, 'timeout_ms'), True),
            ('success transition absent', ('nodes', 1, 'on_success'), MISSING),
            ('success transition empty', ('nodes', 1, 'on_success'), ''),
            ('human failure absent', ('nodes', 3, 'on_failure'), MISSING),
            ('policies null', ('policies',), None),
            ('default retry null', ('policies', 'default_retry'), None),
            ('edge label invalid', ('edges', 0, 'label'), []), ('edge condition invalid', ('edges', 0, 'condition'), []),
            ('bad input schema', ('input_schema',), {'type': 'object', 'pattern': 'unsupported'}),
        ])
        for name, path, value in cases:
            with self.subTest(case=name):
                workflow = copy.deepcopy(original)
                parent = workflow
                for part in path[:-1]:
                    parent = parent[part]
                if value is MISSING:
                    parent.pop(path[-1])
                else:
                    parent[path[-1]] = value
                self.assert_agreement(workflow, False)

    def test_http_and_decision_agent_shapes_match_versioned_schemas(self):
        original = json.loads((ROOT / 'examples/workflows/http-connector.workflow.json').read_text())
        index = next(i for i, node in enumerate(original['nodes']) if node['type'] == 'tool_call')
        bindings = [
            {'id': 'http'}, {'id': 'http', 'request': None}, {'id': 7, 'request': {}},
            {'id': 'http', 'kind': 7, 'request': {}},
            {'id': 'http', 'request': {'url': 7}}, {'id': 'http', 'request': {'method': 7}},
            {'id': 'http', 'request': {'headers': []}}, {'id': 'http', 'credentials': {}, 'request': {}},
            {'id': 'http_assert', 'request': {'url': 'https://example.invalid'}},
            {'id': 'http_assert', 'request': {'url': 'https://example.invalid'}, 'assertions': []},
        ]
        for binding in bindings:
            with self.subTest(binding=binding):
                workflow = copy.deepcopy(original)
                workflow['nodes'][index]['connector'] = binding
                self.assert_agreement(workflow, False)
        original = json.loads((ROOT / 'examples/workflows/risk-routing.workflow.json').read_text())
        for change in (lambda n: n.pop('default'), lambda n: n.update(branches=[]),
                       lambda n: n['branches'][0].update(when={'path': '/input/x', 'gt': True}),
                       lambda n: n['branches'][0].update(when={'path': '/input/x', 'expr': 'x > 2'})):
            with self.subTest(change=change):
                workflow = copy.deepcopy(original)
                change(workflow['nodes'][2])
                self.assert_agreement(workflow, False)

    def test_graph_semantics_are_explicitly_beyond_json_schema_shapes(self):
        workflow = json.loads((ROOT / 'examples/workflows/risk-routing.workflow.json').read_text())
        workflow['nodes'][2]['default'] = 'missing'
        self.assertTrue(self.schema_valid(workflow))
        self.assertIn('decision_default_missing', [error['code'] for error in validate_workflow_structured(workflow)])

    def test_nested_input_contract_keywords_match_their_declared_types(self):
        workflow = json.loads((ROOT / 'examples/workflows/approval-flow.workflow.json').read_text())
        for child in ({'type': 'number', 'minLength': 1}, {'type': 'string', 'minimum': 1},
                      {'type': 'boolean', 'properties': {}}, {'type': 'object', 'items': {'type': 'string'}},
                      {'type': 'array', 'required': []}):
            with self.subTest(child=child):
                workflow['input_schema'] = {'type': 'object', 'properties': {'value': child}}
                self.assert_agreement(workflow, False)
