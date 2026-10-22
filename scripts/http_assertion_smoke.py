#!/usr/bin/env python3
"""Qualify actual CLI HTTP assertions, optionally using an installed wheel."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.request_count += 1
        payload = json.dumps({'ready': self.path == '/ready', 'private': 'response-canary'}).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('X-Private', 'header-canary')
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
    server.request_count = 0
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for ready in (True, False):
                initial_requests = server.request_count
                config = {
                    'request': {'url': f'http://127.0.0.1:{server.server_port}/' + ('ready' if ready else 'unready')},
                    'assertions': [{'path': '/ready', 'equals': True}],
                }
                skill = root / 'SKILL.md'
                skill.write_text('## Steps\n1. 校验结果 <!-- skill2workflow: http_assert ' + json.dumps(config) + ' -->\n2. Deliver\n', encoding='utf-8')
                source = root / 'workflow.json'
                for arguments in (['compile', str(skill), '--review', '-o', str(source)],
                                  ['validate', str(source), '--format', 'json'],
                                  ['run', str(source), '--state-dir', str(root / str(ready)), '--storage', 'sqlite']):
                    result = subprocess.run(command + arguments, cwd=str(root), env=environment,
                                            capture_output=True, text=True, timeout=30)
                    if result.returncode:
                        raise RuntimeError('HTTP assertion CLI qualification failed')
                    if arguments[0] != 'run' and server.request_count != initial_requests:
                        raise RuntimeError('Skill compilation or validation made an HTTP request')
                    if arguments[0] == 'compile' and json.loads(result.stdout).get('verification_node_count') != 1:
                        raise RuntimeError('Skill HTTP assertion review count is invalid')
                state = json.loads(result.stdout)
                workflow = json.loads(source.read_text(encoding='utf-8'))
                check = workflow['nodes'][1]
                if (check['type'] != 'tool_call' or check['connector']['id'] != 'http_assert'
                        or check['title'] != '校验结果' or check['metadata']['source']['line'] != 2):
                    raise RuntimeError('Skill HTTP assertion compilation qualification failed')
                if state['status'] != ('completed' if ready else 'failed') or ('node_002_deliver' in state['node_results']) != ready:
                    raise RuntimeError('HTTP assertion transition qualification failed')
                if server.request_count != initial_requests + 1:
                    raise RuntimeError('HTTP assertion request count is invalid')
                if any(marker in json.dumps(state) for marker in ('response-canary', 'header-canary')):
                    raise RuntimeError('HTTP assertion retained response values')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print(json.dumps({'ok': True, 'installed': bool(args.executable), 'cases_verified': 2}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
