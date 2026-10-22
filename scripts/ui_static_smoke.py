#!/usr/bin/env python3
"""Qualify fixed static serving in an owned installed-wheel environment."""
import argparse
import json
import os
from pathlib import Path
import tempfile

try:
    from .draft_input_ui_smoke import request
except ImportError:
    from draft_input_ui_smoke import request


def qualify(executable):
    executable = Path(executable).resolve()
    root = executable.parent.parent / 'share/skill2workflow'
    if not (root / 'web/index.html').is_file():
        raise RuntimeError('installed UI asset root unavailable')
    environment = dict(os.environ)
    environment.pop('PYTHONPATH', None)
    environment['PYTHONNOUSERSITE'] = '1'
    command = [str(executable)]
    refusal = b'{"error":"UI asset is not available"}'
    with tempfile.TemporaryDirectory(prefix='s2w-static-check-') as cwd, \
         tempfile.TemporaryDirectory(prefix='s2w-private-', dir=str(root / 'web')) as private:
        private_file = Path(private) / 'canary.json'
        private_file.write_text('synthetic-private-file-canary', encoding='utf-8')
        private_path = '/' + private_file.relative_to(root).as_posix()
        cases = [('/', 'GET', 307), ('/web/index.html', 'HEAD', 200),
                 ('/web/control.html', 'GET', 200), ('/web/app.js?v=1', 'GET', 200),
                 (private_path, 'GET', 404), (private_path, 'HEAD', 404),
                 ('/examples/', 'GET', 404), ('/web/%2e%2e/README.md', 'GET', 404),
                 ('/web/../web/app.js', 'GET', 404), ('/api/v1/control-snapshot', 'HEAD', 404)]
        for path, method, expected in cases:
            status, headers, body = request(command, environment, Path(cwd), method, path)
            if (status != expected or headers.get('Cache-Control') != 'no-store'
                    or headers.get('X-Content-Type-Options') != 'nosniff'
                    or b'synthetic-private-file-canary' in body):
                raise RuntimeError('installed UI static boundary qualification failed')
            if status == 307:
                if body or headers.get('Location') != '/web/':
                    raise RuntimeError('installed UI editor redirect qualification failed')
            elif method == 'HEAD':
                if body or int(headers.get('Content-Length', '0')) <= 0:
                    raise RuntimeError('installed UI HEAD qualification failed')
            elif status == 404:
                if body != refusal:
                    raise RuntimeError('installed UI refusal qualification failed')
            elif len(body) != int(headers.get('Content-Length', '-1')) or not body:
                raise RuntimeError('installed UI asset qualification failed')
    return {'ok': True, 'installed': True, 'cases_verified': 10, 'private_file_excluded': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True,
                        help='CLI inside the disposable qualification environment')
    arguments = parser.parse_args()
    print(json.dumps(qualify(arguments.executable)))
