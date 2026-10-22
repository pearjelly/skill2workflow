#!/usr/bin/env python3
"""Qualify the draft-input UI using only the selected CLI and owned loopback."""
import argparse
import copy
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time


def qualify(executable=None, browser_module_tests=False):
    command = [str(executable)] if executable else [sys.executable, '-m', 'skill2workflow.cli']
    environment = dict(os.environ)
    if executable:
        environment.pop('PYTHONPATH', None)
        environment['PYTHONNOUSERSITE'] = '1'
    else:
        environment['PYTHONPATH'] = str(Path(__file__).resolve().parents[1] / 'src')
    with tempfile.TemporaryDirectory(prefix='s2w-draft-input-') as temporary:
        directory = Path(temporary)
        skill = directory / 'SKILL.md'
        schema = {'type': 'object', 'properties': {'id': {'type': 'string', 'minLength': 1}},
                  'required': ['id'], 'additionalProperties': False}
        action = {'request': {'url': 'https://example.invalid/tasks', 'method': 'POST',
                             'input_mapping': [{'from': '/input/id', 'to': '/body/id'}]}}
        skill.write_text('---\nname: input-review-smoke\n---\n<!-- skill2workflow: input_schema '
                         + json.dumps(schema) + ' -->\n## Steps\n'
                         '1. Review <!-- skill2workflow: human_gate -->\n'
                         '2. Submit <!-- skill2workflow: http ' + json.dumps(action) + ' -->\n3. Deliver\n', encoding='utf-8')
        compiled = subprocess.run(command + ['compile', str(skill)], env=environment,
                                  capture_output=True, text=True, check=True, timeout=10)
        workflow = json.loads(compiled.stdout)
        cases = [({'workflow': workflow}, False),
                 ({'workflow': workflow, 'input': {'id': 12}}, False),
                 ({'workflow': workflow, 'input': {'id': 'private-smoke-input-canary'}}, True)]
        untyped = dict(workflow)
        untyped.pop('input_schema')
        cases.append(({'workflow': untyped, 'input': {}}, False))
        for payload, ready in cases:
            status, headers, raw = request(command, environment, directory, 'POST', '/api/v1/draft-input-preflights',
                                           json.dumps(payload).encode('utf-8'))
            report = json.loads(raw)
            if status != 200 or report.get('ready') is not ready or headers.get('Cache-Control') != 'no-store':
                raise RuntimeError('draft input UI qualification failed')
            if b'private-smoke-input-canary' in raw or b'https://' in raw or report.get('safety') != {
                'side_effect_free': True, 'connector_calls': False, 'credentials_resolved': False, 'raw_values_included': False
            }:
                raise RuntimeError('draft input UI response boundary failed')
        diagnostics = []
        reason_cases = [
            ('input_required', {}, {}), ('input_type', {}, {'id': 12}),
            ('input_enum', {'enum': ['allowed']}, {'id': 'private-smoke-input-canary'}),
            ('input_string_too_short', {}, {'id': ''}),
            ('input_string_too_long', {'maxLength': 2}, {'id': 'private-smoke-input-canary'}),
            ('input_number_too_small', {'type': 'number', 'minimum': 2}, {'id': 1}),
            ('input_number_too_large', {'type': 'number', 'maximum': 2}, {'id': 3}),
            ('input_unknown_property', {}, {'id': 'valid', 'private-key-canary': True}),
        ]
        for code, constraints, supplied in reason_cases:
            candidate = copy.deepcopy(workflow)
            candidate['input_schema']['properties']['id'] = dict({'type': 'string', 'minLength': 1}, **constraints)
            if constraints.get('type') == 'number':
                candidate['input_schema']['properties']['id'].pop('minLength')
            status, _, raw = request(command, environment, directory, 'POST', '/api/v1/draft-input-preflights',
                                     json.dumps({'workflow': candidate, 'input': supplied}).encode())
            result = json.loads(raw)
            expected_path = ['input', 'private-key-canary' if code == 'input_unknown_property' else 'id']
            if status != 200 or result.get('ready') is not False or result['input']['error_code'] != code or result['input']['error_path'] != expected_path:
                raise RuntimeError('draft input diagnostic qualification failed')
            if b'private-smoke-input-canary' in raw:
                raise RuntimeError('draft input diagnostic value boundary failed')
            diagnostics.append({'workflow': candidate, 'report': result})
        status, _, raw = request(command, environment, directory, 'POST', '/api/v1/draft-input-preflights',
                                  b'{"workflow":{},"workflow":{}}')
        if status != 400 or json.loads(raw) != {'error': 'draft input preflight rejected'}:
            raise RuntimeError('draft input UI refusal failed')
        status, _, raw = request(command, environment, directory, 'GET', '/web/input-review.js')
        if status != 200 or b'draft-input-preflights' not in raw or b'credentials: "omit"' not in raw:
            raise RuntimeError('draft input UI module missing')
        if set(directory.iterdir()) != {skill}:
            raise RuntimeError('draft input UI created unexpected state')
        if browser_module_tests:
            module = directory / 'input-review.js'
            fixture = directory / 'diagnostics.json'
            module.write_bytes(raw)
            fixture.write_text(json.dumps(diagnostics), encoding='utf-8')
            node_environment = dict(environment, S2W_INPUT_REVIEW_MODULE=str(module), S2W_INPUT_REVIEW_DIAGNOSTICS=str(fixture))
            subprocess.run(['node', '--test', str(Path(__file__).resolve().parents[1] / 'tests/test_input_review.cjs')],
                           cwd=str(directory), env=node_environment, capture_output=True, check=True, timeout=20)
    result = {'ok': True, 'installed': executable is not None, 'cases_verified': 13, 'module_served': True, 'diagnostics_verified': 8}
    if browser_module_tests:
        result['browser_module_verified'] = True
    return result


def request(command, environment, directory, method, path, body=None):
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    process = subprocess.Popen(command + ['ui', '--port', str(port), '--once'], cwd=str(directory), env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    connection = None
    try:
        deadline = time.monotonic() + 5
        while True:
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
            try:
                connection.connect()
                break
            except OSError:
                connection.close()
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError('draft input UI server unavailable')
                time.sleep(.03)
        connection.request(method, path, body=body, headers={'Content-Type': 'application/json'})
        response = connection.getresponse()
        result = response.status, dict(response.headers), response.read()
        connection.close()
        process.wait(timeout=5)
        if process.returncode != 0:
            raise RuntimeError('draft input UI did not close cleanly')
        return result
    finally:
        if connection: connection.close()
        if process.poll() is None: process.kill()
        process.communicate(timeout=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path)
    parser.add_argument('--browser-module-tests', action='store_true', help='Require Node tests against the served module and real reports (development qualification only).')
    arguments = parser.parse_args()
    print(json.dumps(qualify(arguments.executable, arguments.browser_module_tests)))
