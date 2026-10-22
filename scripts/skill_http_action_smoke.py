#!/usr/bin/env python3
"""Qualify Skill-to-published HTTP actions against an isolated loopback server."""

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.parse import parse_qs, urlsplit


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))))
        self.server.events.append(('POST', body))
        if self.path != '/tasks' or self.headers.get('Authorization') != 'qualification-credential':
            self._reply(400, {'private': 'response-body-canary'})
            return
        self.server.records[body['id']] = body
        self._reply(500 if body['id'] == 'http_failure' else 201, {'private': 'response-body-canary'})

    def do_GET(self):
        record_id = parse_qs(urlsplit(self.path).query).get('id', [''])[0]
        self.server.events.append(('GET', record_id))
        self._reply(200, {'ready': record_id in self.server.records and record_id != 'mismatch',
                          'private': 'response-body-canary'})

    def _reply(self, status, value):
        payload = json.dumps(value).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('X-Private', 'response-header-canary')
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path)
    args = parser.parse_args()
    environment = os.environ.copy()
    environment['PYTHONNOUSERSITE'] = '1'
    if args.executable:
        command = [str(args.executable.resolve())]
        environment.pop('PYTHONPATH', None)
    else:
        command = [sys.executable, '-m', 'skill2workflow.cli']
        environment['PYTHONPATH'] = str(Path(__file__).resolve().parents[1] / 'src')
    server = HTTPServer(('127.0.0.1', 0), Handler)
    server.events, server.records = [], {}
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            def run(*arguments):
                result = subprocess.run(command + list(arguments), cwd=str(root), env=environment,
                                        capture_output=True, text=True, timeout=30)
                if result.returncode:
                    raise RuntimeError('Skill HTTP action CLI qualification failed')
                return json.loads(result.stdout)
            origin = 'http://127.0.0.1:' + str(server.server_port)
            action = {'request': {'method': 'POST', 'url': origin + '/tasks', 'allowed_origins': [origin],
                                  'body': {'source': 'workflow'}, 'input_mapping': [
                                      {'from': '/input/record_id', 'to': '/body/id'},
                                      {'from': '/input/title', 'to': '/body/title'}]},
                      'credentials': [{'target': 'header', 'name': 'Authorization', 'handle': 'task_token'}]}
            check = {'request': {'url': origin + '/status', 'allowed_origins': [origin],
                                 'input_mapping': [{'from': '/input/record_id', 'to': '/query/id'}]},
                     'assertions': [{'path': '/ready', 'equals': True}]}
            skill, source, inputs, credentials = [root / name for name in ('SKILL.md', 'workflow.json', 'input.json', 'credentials.json')]
            skill.write_text('---\nname: http-action-journey\n---\n## Steps\n'
                             '1. 负责人审批 <!-- skill2workflow: human_gate -->\n'
                             '2. 提交请求 <!-- skill2workflow: http ' + json.dumps(action) + ' -->\n'
                             '3. 校验结果 <!-- skill2workflow: http_assert ' + json.dumps(check) + ' -->\n'
                             '4. Deliver\n', encoding='utf-8')
            credentials.write_text(json.dumps({'credentials': {'task_token': 'qualification-credential'}}), encoding='utf-8')
            credentials.chmod(0o600)
            review = run('compile', str(skill), '--review', '-o', str(source))
            workflow = json.loads(source.read_text(encoding='utf-8'))
            if (review['verification_node_count'] != 1 or review['human_gate_count'] != 1
                    or workflow['nodes'][2]['connector']['request']['response_mode'] != 'metadata'):
                raise RuntimeError('Skill HTTP action compilation qualification failed')
            run('validate', str(source), '--format', 'json')
            if server.events:
                raise RuntimeError('Skill HTTP compilation or validation made a request')
            for outcome in ('match', 'mismatch', 'http_failure', 'reject'):
                start = len(server.events)
                state_dir = root / outcome
                common = ('--state-dir', str(state_dir), '--storage', 'sqlite')
                run('publish', str(source), *common)
                inputs.write_text(json.dumps({'record_id': outcome, 'title': 'Example task'}), encoding='utf-8')
                triggered = run('trigger', 'workflow_http_action_journey', '--version', '0.1.0',
                                '--source', 'local-qualification', '--idempotency-key', outcome,
                                '--input', str(inputs), *common)
                if triggered['run_status'] != 'waiting' or len(server.events) != start:
                    raise RuntimeError('HTTP action bypassed human approval')
                rejection = ('--reject',) if outcome == 'reject' else ()
                state = run('resume-published', triggered['run_id'], '--credential-file', str(credentials), *rejection, *common)
                expected_calls = 0 if outcome == 'reject' else 1 if outcome == 'http_failure' else 2
                if (state['status'] != ('completed' if outcome == 'match' else 'failed')
                        or ('node_004_deliver' in state['node_results']) != (outcome == 'match')
                        or len(server.events) != start + expected_calls):
                    raise RuntimeError('HTTP action failure transition qualification failed: '
                                       + outcome + ', status=' + str(state['status'])
                                       + ', calls=' + str(len(server.events) - start))
                if expected_calls:
                    if server.events[start] != ('POST', {'source': 'workflow', 'id': outcome, 'title': 'Example task'}):
                        raise RuntimeError('HTTP action input mapping qualification failed')
                durable_evidence = json.dumps({'state': state, 'audit': run('audit', *common)})
                if any(value in durable_evidence for value in ('qualification-credential', 'response-body-canary', 'response-header-canary')):
                    raise RuntimeError('HTTP action retained credential or response values')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print(json.dumps({'ok': True, 'installed': bool(args.executable), 'cases_verified': 4}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
