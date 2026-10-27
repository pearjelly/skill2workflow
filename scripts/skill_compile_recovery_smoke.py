#!/usr/bin/env python3
"""Qualify safe Skill compile recovery through the selected CLI and owned loopback."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

try:
    from draft_input_ui_smoke import request
except ImportError:
    from scripts.draft_input_ui_smoke import request


VERSION = 'skill2workflow-skill-compile-diagnostic-0.1.0'
EXTENDED_VERSION = 'skill2workflow-skill-compile-diagnostic-0.2.0'
DUPLICATE = '---\nname: reviewed\ndescription: Synthetic example.\nname: private-value-canary\n---\n## Steps\n1. Review\n'
CORRECTED = '---\nname: reviewed\ndescription: Synthetic example.\n---\n## Steps\n1. Review\n'
UNCLOSED = ('---\nname: reviewed\n---\n## Checklist\n1. Ask for approval\n2. Verify draft\n'
            '    ~~~markdown\n    private-value-canary\n~~~\n3. Deliver output\n')
CLOSED = UNCLOSED.replace('\n~~~\n', '\n    ~~~\n')
INFERRED_ACTION = ('## Steps\n1. Review <!-- skill2workflow: human_gate -->\n'
                   '2. Run private-command-canary\n')


def qualify(executable=None, browser_module_tests=False):
    root = Path(__file__).resolve().parents[1]
    command = [str(executable)] if executable else [sys.executable, '-m', 'skill2workflow.cli']
    environment = dict(os.environ)
    if executable:
        environment.pop('PYTHONPATH', None)
        environment['PYTHONNOUSERSITE'] = '1'
    else:
        environment['PYTHONPATH'] = str(root / 'src')
    verified = diagnostics = legacy = cli = 0
    with tempfile.TemporaryDirectory(prefix='s2w-compile-recovery-') as temporary:
        directory = Path(temporary)
        fixtures = []
        cases = [
            (DUPLICATE, True, 'frontmatter_duplicate_key', 4),
            ('---\nname: reviewed\ndescription: "private-value-canary\n---', True, 'frontmatter_invalid', 3),
            ('---\nname: reviewed\ndescription: *private-value-canary\n---', True, 'frontmatter_unsupported', 3),
            ('## Workflow\n1. Review\n## Steps\n1. Deliver\n', True, 'skill_invalid', None),
            (DUPLICATE, None, None, None), (DUPLICATE, False, None, None),
            (DUPLICATE, 1, None, None), (CORRECTED, True, None, None),
        ]
        for index, (source, flag, code, line) in enumerate(cases):
            payload = {'skill_markdown': source}
            if flag is not None:
                payload['diagnostics'] = flag
            status, headers, raw = request(command, environment, directory, 'POST', '/api/v1/skill-compiles', json.dumps(payload).encode())
            reply = json.loads(raw)
            if headers.get('Cache-Control') != 'no-store':
                raise RuntimeError('Skill compile cache boundary failed')
            if index < 7:
                if status != 400 or len(raw) > 1024 or any(value in raw for value in (b'private-value-canary', str(directory).encode(), b'Traceback')):
                    raise RuntimeError('Skill compile refusal boundary failed')
                expected = {'error': 'skill compile rejected'}
                if code:
                    expected['diagnostic'] = {'schema_version': VERSION, 'code': code, 'line': line}
                elif index == 6:
                    expected = {'error': 'skill compile body is malformed'}
                if reply != expected:
                    raise RuntimeError('Skill compile recovery contract failed')
                if code:
                    diagnostics += 1
                    fixtures.append({'source': source, 'reply': reply})
                elif index in (4, 5):
                    legacy += 1
            elif status != 200 or set(reply) != {'workflow', 'review'} or reply['workflow']['workflow']['id'] != 'workflow_reviewed':
                raise RuntimeError('Skill compile correction failed')
            verified += 1
        for source, version in ((UNCLOSED, None), (UNCLOSED, '0.2.0'), (CLOSED, '0.2.0')):
            payload = {'skill_markdown': source, 'diagnostics': True}
            if version:
                payload['diagnostic_version'] = version
            status, headers, raw = request(command, environment, directory, 'POST', '/api/v1/skill-compiles', json.dumps(payload).encode())
            reply = json.loads(raw)
            if headers.get('Cache-Control') != 'no-store':
                raise RuntimeError('Fence compile cache boundary failed')
            if source == UNCLOSED:
                expected = {'error': 'skill compile rejected', 'diagnostic': {
                    'schema_version': EXTENDED_VERSION if version else VERSION,
                    'code': 'unclosed_fence' if version else 'skill_invalid', 'line': 7 if version else None}}
                if status != 400 or reply != expected or len(raw) > 1024 or any(value in raw for value in
                        (b'private-value-canary', str(directory).encode(), b'Traceback')):
                    raise RuntimeError('Fence compile refusal boundary failed')
                diagnostics += 1
                if version:
                    fixtures.append({'source': source, 'reply': reply})
            else:
                if status != 200 or set(reply) != {'workflow', 'review'} or b'private-value-canary' in raw:
                    raise RuntimeError('Fence compile correction failed')
                steps = [node for node in reply['workflow']['nodes'] if node.get('metadata', {}).get('source', {}).get('kind') == 'ordered_step']
                if [node['title'] for node in steps] != ['Ask for approval', 'Verify draft', 'Deliver output'] or [node['metadata']['source']['line'] for node in steps] != [5, 6, 10]:
                    raise RuntimeError('Fence compile correction lost steps')
            verified += 1
        status, headers, raw = request(command, environment, directory, 'POST', '/api/v1/skill-compiles',
                                       json.dumps({'skill_markdown': INFERRED_ACTION, 'diagnostics': True}).encode())
        action_reply = json.loads(raw)
        if status != 200 or headers.get('Cache-Control') != 'no-store' or set(action_reply) != {'workflow', 'review'}:
            raise RuntimeError('Inferred action compile qualification failed')
        nodes = action_reply['workflow']['nodes']
        if (sum(node.get('type') == 'tool_call' and node.get('connector') == {'id': 'http', 'kind': 'http'}
                for node in nodes) != 1 or 'private-command-canary' in json.dumps(action_reply['review'])):
            raise RuntimeError('Inferred action compile contract failed')
        verified += 1
        if list(directory.iterdir()):
            raise RuntimeError('Skill compile requests created unexpected state')
        modules = {}
        for name, url in [('app.js', '/web/app.js'), ('index.html', '/web/'),
                          ('litegraph.js', '/web/vendor/litegraph-0.7.18/litegraph.min.js')]:
            status, _, raw = request(command, environment, directory, 'GET', url)
            if status != 200 or not raw:
                raise RuntimeError('Skill compile editor module unavailable')
            modules[name] = raw
        for name, source, expected_status in [('invalid-SKILL.md', DUPLICATE, 1), ('corrected-SKILL.md', CORRECTED, 0), ('unclosed-SKILL.md', UNCLOSED, 1)]:
            path = directory / name
            path.write_text(source, encoding='utf-8')
            result = subprocess.run(command + ['compile', str(path)], cwd=str(directory), env=environment, capture_output=True, text=True, timeout=10)
            if result.returncode != expected_status:
                raise RuntimeError('Skill compile CLI recovery failed')
            if expected_status:
                expected_message = ('line 7', 'unclosed') if source == UNCLOSED else ('line 4', 'one declaration')
                if result.stdout or any(item not in result.stderr for item in expected_message) or 'private-value-canary' in result.stderr or str(directory) in result.stderr:
                    raise RuntimeError('Skill compile CLI refusal boundary failed')
            elif json.loads(result.stdout)['workflow']['id'] != 'workflow_reviewed':
                raise RuntimeError('Skill compile CLI correction failed')
            cli += 1
            verified += 1
        if browser_module_tests:
            for name, raw in modules.items():
                (directory / name).write_bytes(raw)
            reports = directory / 'diagnostics.json'
            reports.write_text(json.dumps(fixtures), encoding='utf-8')
            action_report = directory / 'inferred-action.json'
            action_report.write_text(json.dumps({'source': INFERRED_ACTION, 'reply': action_reply}), encoding='utf-8')
            node_environment = dict(environment, S2W_EDITOR_MODULE=str(directory / 'app.js'),
                                    S2W_EDITOR_VENDOR=str(directory / 'litegraph.js'), S2W_COMPILE_DIAGNOSTICS=str(reports),
                                    S2W_COMPILE_ACTION=str(action_report), S2W_EDITOR_INDEX=str(directory / 'index.html'))
            subprocess.run(['node', '--test', str(root / 'tests/test_skill_compile_recovery.cjs'),
                            str(root / 'tests/test_draft_load_ownership.cjs')], cwd=str(directory), env=node_environment,
                           capture_output=True, check=True, timeout=20)
    result = {'ok': True, 'installed': executable is not None, 'cases_verified': verified,
              'diagnostic_cases_verified': diagnostics, 'legacy_cases_verified': legacy,
              'cli_cases_verified': cli, 'module_served': True}
    if browser_module_tests:
        result['browser_module_verified'] = True
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path)
    parser.add_argument('--browser-module-tests', action='store_true', help='Require Node tests against served editor/vendor modules and real reports (development only).')
    arguments = parser.parse_args()
    print(json.dumps(qualify(arguments.executable, arguments.browser_module_tests)))
