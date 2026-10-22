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
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for ready in (True, False):
                workflow = {
                    'schema_version': '0.1.0',
                    'workflow': {'id': 'assertion-smoke', 'name': 'Assertion smoke', 'version': '0.1.0', 'status': 'draft'},
                    'entry': 'probe',
                    'nodes': [
                        {'id': 'probe', 'type': 'tool_call', 'title': 'Verify readiness',
                         'on_success': 'deliver', 'on_failure': 'failure',
                         'connector': {'id': 'http_assert', 'kind': 'http_assert',
                                       'request': {'url': f'http://127.0.0.1:{server.server_port}/' + ('ready' if ready else 'unready')},
                                       'assertions': [{'path': '/ready', 'equals': True}]}},
                        {'id': 'deliver', 'type': 'step', 'title': 'Deliver', 'on_success': 'end', 'on_failure': 'failure'},
                        {'id': 'failure', 'type': 'failure', 'title': 'Failure'},
                        {'id': 'end', 'type': 'end', 'title': 'End'},
                    ],
                    'edges': [{'id': f'e{index}', 'from': source, 'to': target}
                              for index, (source, target) in enumerate([
                                  ('probe', 'deliver'), ('probe', 'failure'), ('deliver', 'end'), ('deliver', 'failure')])],
                }
                source = root / 'workflow.json'
                source.write_text(json.dumps(workflow), encoding='utf-8')
                for arguments in (['validate', str(source), '--format', 'json'],
                                  ['run', str(source), '--state-dir', str(root / str(ready)), '--storage', 'sqlite']):
                    result = subprocess.run(command + arguments, cwd=str(root), env=environment,
                                            capture_output=True, text=True, timeout=30)
                    if result.returncode:
                        raise RuntimeError('HTTP assertion CLI qualification failed')
                state = json.loads(result.stdout)
                if state['status'] != ('completed' if ready else 'failed') or ('deliver' in state['node_results']) != ready:
                    raise RuntimeError('HTTP assertion transition qualification failed')
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
