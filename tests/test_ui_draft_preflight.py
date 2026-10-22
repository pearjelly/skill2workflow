import copy
import http.client
import json
import threading
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from skill2workflow.preflight import build_workflow_preflight
from skill2workflow.ui import serve_ui


ROOT = Path(__file__).resolve().parents[1]
PATH = '/api/v1/draft-input-preflights'


def workflow():
    value = json.loads((ROOT / 'examples/workflows/http-action-flow.workflow.json').read_text(encoding='utf-8'))
    return value


def post(payload, path=PATH, headers=None, raw=None):
    ready = threading.Event()
    address = {}
    def callback(server):
        address['port'] = server.server_port
        ready.set()
    thread = threading.Thread(target=serve_ui, kwargs={'port': 0, 'once': True, 'ready_callback': callback}, daemon=True)
    thread.start()
    if not ready.wait(3):
        raise AssertionError('local UI did not start')
    connection = http.client.HTTPConnection('127.0.0.1', address['port'], timeout=3)
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8') if raw is None else raw
    try:
        if isinstance(headers, list):
            connection.putrequest('POST', path)
            for key, value in headers:
                connection.putheader(key, value)
            connection.endheaders(body)
        else:
            connection.request('POST', path, body=body, headers=headers or {'Content-Type': 'application/json'})
        response = connection.getresponse()
        result = response.status, dict(response.headers), response.read()
    finally:
        connection.close()
        thread.join(3)
    if thread.is_alive():
        raise AssertionError('local UI did not close')
    return result


class DraftInputPreflightTests(TestCase):
    def test_editor_input_review_wiring_is_ephemeral_and_requires_source(self):
        page = (ROOT / 'web/index.html').read_text(encoding='utf-8')
        app = (ROOT / 'web/app.js').read_text(encoding='utf-8')
        module = (ROOT / 'web/input-review.js').read_text(encoding='utf-8')
        self.assertLess(page.index('id="workflow-input-panel"'), page.index('id="node-form"'))
        self.assertLess(page.index('./input-review.js'), page.index('./app.js'))
        self.assertIn('inputReview.reset(currentWorkflowDsl)', app)
        self.assertIn('inputReview.invalidate()', app)
        self.assertIn('Read-only source contract', page)
        self.assertIn('not in exports', page)
        self.assertNotIn('localStorage', module)
        self.assertNotIn('downloadJson', module)
        guide = (ROOT / 'docs/authoring.md').read_text(encoding='utf-8')
        for phrase in ('Check Draft Input In The Editor', 'ephemeral test data',
                       '3 MiB + 1 KiB', 'stale asynchronous responses', '1,000 nodes'):
            self.assertIn(phrase, guide)

    def test_installed_gate_requires_all_case_and_module_evidence(self):
        from scripts import package_smoke
        complete = {'ok': True, 'installed': True, 'cases_verified': 13, 'module_served': True, 'diagnostics_verified': 8}
        for value in (complete, {}, dict(complete, cases_verified=5), dict(complete, module_served=False), dict(complete, diagnostics_verified=0)):
            with patch('scripts.package_smoke._run', return_value=json.dumps(value)):
                if value == complete:
                    self.assertTrue(package_smoke._qualify_installed_draft_input_ui(Path('/repo'), Path('/bin/cli'), Path('/isolated')))
                else:
                    with self.assertRaisesRegex(RuntimeError, 'qualification failed'):
                        package_smoke._qualify_installed_draft_input_ui(Path('/repo'), Path('/bin/cli'), Path('/isolated'))

    def test_local_report_matches_existing_preflight_and_never_calls_a_provider(self):
        draft = workflow()
        supplied = {'record_id': 'private-input-canary', 'title': 'Synthetic request'}
        before = copy.deepcopy((draft, supplied))
        with patch('skill2workflow.connectors._open_http_request') as transport, \
             patch('skill2workflow.ui.read_service_bearer_token') as token:
            for payload in ({'workflow': draft}, {'workflow': draft, 'input': supplied}):
                status, headers, raw = post(payload)
                self.assertEqual(status, 200)
                self.assertEqual(headers['Cache-Control'], 'no-store')
                expected = build_workflow_preflight(draft, payload.get('input'), input_present='input' in payload)
                self.assertEqual(json.loads(raw), expected)
                self.assertNotIn(b'private-input-canary', raw)
                self.assertNotIn(b'https://', raw)
            transport.assert_not_called()
            token.assert_not_called()
        self.assertEqual((draft, supplied), before)

    def test_invalid_types_and_missing_mapping_return_blocked_not_an_execution(self):
        draft = workflow()
        for value in ({'record_id': 3, 'title': 'x'}, {'record_id': 'x', 'title': 'x', 'extra': True}):
            status, _, raw = post({'workflow': draft, 'input': value})
            self.assertEqual(status, 200)
            self.assertFalse(json.loads(raw)['ready'])
        draft.pop('input_schema')
        status, _, raw = post({'workflow': draft, 'input': {}})
        self.assertEqual(status, 200)
        report = json.loads(raw)
        self.assertFalse(report['ready'])
        self.assertIn('required_mapping_input_missing', {issue['code'] for issue in report['issues']})

    def test_malformed_input_has_fixed_value_free_refusal(self):
        draft = workflow()
        bodies = [b'{private-canary}', b'\xff', b'[]', b'{"workflow":{},"workflow":{}}',
                  json.dumps({'workflow': draft, 'input': {'value': float('nan')}}).encode(),
                  json.dumps({'workflow': draft, 'input': {'value': float('inf')}}).encode()]
        payloads = [{}, {'workflow': draft, 'extra': 'private-canary'},
                    {'workflow': draft, 'input': None}, {'workflow': draft, 'input': []},
                    {'workflow': {'private-canary': 'private-value'}},
                    {'workflow': draft, 'input': {'large': 'x' * 1048576}},
                    {'workflow': draft, 'input': {str(i): i for i in range(129)}}]
        for raw in bodies:
            with self.subTest(raw=raw[:35]):
                status, _, result = post(None, raw=raw)
                self.assertEqual(status, 400)
                self.assertEqual(json.loads(result), {'error': 'draft input preflight rejected'})
        for payload in payloads:
            with self.subTest(keys=list(payload)):
                status, _, result = post(payload)
                self.assertEqual(status, 400)
                self.assertEqual(json.loads(result), {'error': 'draft input preflight rejected'})

    def test_transport_path_and_response_limits_fail_closed(self):
        status, _, raw = post({}, path=PATH + '?debug=1')
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(raw), {'error': 'draft input preflight path is not available'})
        status, _, raw = post(None, raw=b'x', headers={'Content-Length': str(4 * 1024 * 1024)})
        self.assertEqual(status, 413)
        self.assertEqual(json.loads(raw), {'error': 'draft input preflight body is too large'})
        status, _, raw = post(None, raw=b'{}', headers={'Transfer-Encoding': 'chunked'})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(raw), {'error': 'draft input preflight rejected'})

    def test_header_and_response_bounds_have_fixed_refusals(self):
        for headers in ([], [('Content-Length', '-1')], [('Content-Length', 'invalid')],
                        [('Content-Length', '2'), ('Content-Length', '2')]):
            status, _, raw = post(None, raw=b'{}', headers=headers)
            self.assertEqual(status, 400)
            self.assertEqual(json.loads(raw), {'error': 'draft input preflight rejected'})
        with patch('skill2workflow.ui.build_workflow_preflight', return_value={'canary': 'x' * 65536}):
            status, _, raw = post({'workflow': workflow()})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(raw), {'error': 'draft input preflight rejected'})
