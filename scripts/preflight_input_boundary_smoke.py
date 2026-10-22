#!/usr/bin/env python3
"""Qualify input admission parity through an actual selected CLI only."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


LIMIT = 1024 * 1024
CHECKS = ('exact_ascii', 'exact_unicode', 'oversize_ascii', 'oversize_unicode',
          'numeric_expansion', 'bundle_parity', 'refusal_no_effects', 'valid_trigger')
ERROR = 'preflight input must be a finite JSON object of at most 1048576 UTF-8 bytes'


def qualify(executable=None):
    root = Path(__file__).resolve().parents[1]
    command = [str(executable)] if executable else [sys.executable, '-m', 'skill2workflow.cli']
    environment = dict(os.environ)
    if executable:
        environment.pop('PYTHONPATH', None)
        environment['PYTHONNOUSERSITE'] = '1'
    else:
        environment['PYTHONPATH'] = str(root / 'src')
    checks = {name: False for name in CHECKS}
    with tempfile.TemporaryDirectory(prefix='s2w-preflight-boundary-') as temporary:
        directory = Path(temporary)

        def invoke(*arguments, expected=0):
            result = subprocess.run(command + [str(value) for value in arguments], cwd=str(directory), env=environment,
                                    capture_output=True, text=True, timeout=15)
            if result.returncode != expected:
                raise RuntimeError('preflight input ' + str(arguments[0]) + ' qualification failed')
            return result

        def run(*arguments):
            return json.loads(invoke(*arguments).stdout)

        def require(condition, check):
            if not condition:
                raise RuntimeError('preflight input ' + check + ' qualification failed')
            checks[check] = True

        skill = directory / 'SKILL.md'
        skill.write_text('---\nname: qualified-input\n---\n## Steps\n'
                         '1. Review <!-- skill2workflow: human_gate -->\n2. Finish\n', encoding='utf-8')
        workflow = directory / 'workflow.json'
        invoke('compile', skill.name, '-o', workflow)
        metadata = json.loads(workflow.read_text(encoding='utf-8'))['workflow']
        state = directory / 'state'
        options = ('--state-dir', state, '--storage', 'sqlite')
        run('publish', workflow, *options)
        before = (run('control-runs', *options), run('audit', *options))
        bundle = directory / 'reviewed.s2w'
        run('bundle-create', workflow, '--output', bundle)
        input_file = directory / 'input.json'
        overhead = len(json.dumps({'payload': ''}, separators=(',', ':')).encode('utf-8'))
        for label, character in (('ascii', 'x'), ('unicode', '界')):
            count, remainder = divmod(LIMIT - overhead, len(character.encode('utf-8')))
            value = {'payload': character * count + 'x' * remainder}
            input_file.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
            report = run('preflight', workflow, '--input', input_file)
            require(report.get('ready') is True and report.get('safety', {}).get('connector_calls') is False, 'exact_' + label)
            value['payload'] += 'x'
            input_file.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
            refused = invoke('preflight', workflow, '--input', input_file, expected=1)
            require(refused.stdout == '' and refused.stderr.strip() == ERROR, 'oversize_' + label)
            invoke('trigger', metadata['id'], '--version', metadata['version'], *options,
                   '--source', 'boundary-smoke', '--idempotency-key', label, '--input', input_file, expected=1)
        input_file.write_text('{"payload":[' + ','.join(['1e5'] * 125000) + ']}', encoding='utf-8')
        refused = invoke('preflight', workflow, '--input', input_file, expected=1)
        require(input_file.stat().st_size < LIMIT and refused.stdout == '' and refused.stderr.strip() == ERROR, 'numeric_expansion')
        invoke('bundle-preflight', bundle, '--input', input_file, expected=1)
        input_file.write_text('{"payload":"reviewed"}', encoding='utf-8')
        require(run('bundle-preflight', bundle, '--input', input_file).get('ready') is True, 'bundle_parity')
        require((run('control-runs', *options), run('audit', *options)) == before, 'refusal_no_effects')
        input_file.write_text(json.dumps({'payload': 'x' * (LIMIT - overhead)}, separators=(',', ':')), encoding='utf-8')
        triggered = run('trigger', metadata['id'], '--version', metadata['version'], *options,
                        '--source', 'boundary-smoke', '--idempotency-key', 'exact-limit', '--input', input_file)
        detail = run('control-run', triggered['run_id'], *options)
        require(detail.get('status') == 'waiting', 'valid_trigger')
    if not all(checks.values()):
        raise RuntimeError('incomplete preflight input qualification')
    return {'ok': True, 'installed': executable is not None, 'checks': checks}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path)
    print(json.dumps(qualify(parser.parse_args().executable)))
