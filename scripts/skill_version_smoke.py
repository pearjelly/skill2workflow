#!/usr/bin/env python3
"""Prove versioned Skill iteration through the selected CLI, without a provider."""
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


CHECKS = ('compile', 'artifacts', 'repair', 'bundles', 'publication',
          'immutable_conflict', 'pinned_runs', 'quickstart', 'ui', 'invalid_source')
SKILL = ('---\nname: versioned-team-review\nmetadata:\n  version: unrelated-metadata-canary\n---\n'
         '<!-- skill2workflow: workflow_version VERSION -->\n'
         '## Steps\n1. Review <!-- skill2workflow: human_gate -->\n2. DELIVERY\n')


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
    with tempfile.TemporaryDirectory(prefix='s2w-skill-version-') as temporary:
        directory = Path(temporary)

        def invoke(*arguments, expected=0):
            result = subprocess.run(command + [str(value) for value in arguments], cwd=str(directory), env=environment,
                                    capture_output=True, text=True, timeout=15)
            if result.returncode != expected:
                raise RuntimeError('versioned Skill command qualification failed')
            return result

        def run(*arguments):
            return json.loads(invoke(*arguments).stdout)

        def require(condition, check):
            if not condition:
                raise RuntimeError('versioned Skill ' + check + ' qualification failed')
            checks[check] = True

        sources, artifacts, bundles, workflows = [], [], [], []
        versions = ('0.1.0', '0.2.0')
        for index, (version, delivery) in enumerate(zip(versions, ('Deliver output', 'Deliver reviewed output'))):
            source = directory / ('v' + str(index + 1) + '-SKILL.md')
            source.write_text(SKILL.replace('VERSION', version).replace('DELIVERY', delivery), encoding='utf-8')
            compiled = run('compile', source, '--review')
            if compiled['workflow']['workflow']['version'] != version or compiled['workflow']['workflow']['id'] != 'workflow_versioned_team_review':
                raise RuntimeError('versioned Skill compile identity failed')
            destination = directory / ('set-' + version)
            exported = run('authoring-export', source, '--output-dir', destination)
            verified = run('authoring-verify', destination)
            workflow = json.loads((destination / 'workflow.json').read_text(encoding='utf-8'))
            if exported['workflow_version'] != version or verified.get('valid') is not True or workflow['workflow']['version'] != version:
                raise RuntimeError('versioned Skill artifacts failed')
            if workflow['schema_version'] != '0.1.0' or any(node.get('metadata', {}).get('source', {}).get('file', 'SKILL.md') != 'SKILL.md' for node in workflow['nodes']):
                raise RuntimeError('versioned Skill portable boundary failed')
            bundle = directory / ('v' + str(index + 1) + '.s2w')
            run('authoring-bundle', destination, '-o', bundle)
            if run('bundle-verify', bundle).get('valid') is not True:
                raise RuntimeError('versioned Skill bundle failed')
            sources.append(source)
            artifacts.append(destination)
            bundles.append(bundle)
            workflows.append(workflow)
        default_source = directory / 'default-SKILL.md'
        default_source.write_text(SKILL.replace('<!-- skill2workflow: workflow_version VERSION -->', '').replace('DELIVERY', 'Deliver output'), encoding='utf-8')
        require(run('compile', default_source)['workflow']['version'] == '0.1.0', 'compile')
        require(all(w['workflow']['version'] == version for w, version in zip(workflows, versions)), 'artifacts')
        difference = run('bundle-diff', bundles[0], bundles[1])
        require(bool(difference['changes']['nodes']['added']), 'bundles')

        (artifacts[1] / 'workflow.json').write_text('{}', encoding='utf-8')
        backup = directory / 'before-repair'
        preview = run('authoring-repair', sources[1], artifacts[1], '--backup-dir', backup, '--dry-run')
        if preview['workflow_version'] != versions[1] or backup.exists() or (artifacts[1] / 'workflow.json').read_text() != '{}':
            raise RuntimeError('versioned Skill repair preview failed')
        repaired = run('authoring-repair', sources[1], artifacts[1], '--backup-dir', backup)
        require(repaired['workflow_version'] == versions[1] and run('authoring-verify', artifacts[1]).get('valid') is True
                and (backup / 'workflow.json').read_text() == '{}', 'repair')

        state = directory / 'state'
        state_args = ('--state-dir', state, '--storage', 'sqlite')
        first = run('authoring-publish', artifacts[0], *state_args)
        old_run = run('run-published', first['workflow_id'], '--version', versions[0], *state_args)
        second = run('authoring-publish', artifacts[1], *state_args)
        inventory_before = run('workflows', *state_args)
        published_before = {record['artifact']: (state / record['artifact']).read_bytes() for record in inventory_before}
        require([first['version'], second['version']] == list(versions) and len(inventory_before) == 2
                and bool(run('workflow-diff', first['workflow_id'], '--from-version', versions[0], '--to-version', versions[1], *state_args)['changes']['nodes']['added']), 'publication')
        new_run = run('run-published', second['workflow_id'], '--version', versions[1], *state_args)
        completed = run('resume-published', new_run['run_id'], *state_args)
        still_waiting = run('show', old_run['run_id'], *state_args)
        rejected = run('resume-published', old_run['run_id'], '--reject', *state_args)
        require(old_run['status'] == new_run['status'] == still_waiting['status'] == 'waiting'
                and completed['status'] == 'completed' and completed['workflow_version'] == versions[1]
                and still_waiting['workflow_version'] == rejected['workflow_version'] == versions[0] and rejected['status'] == 'failed', 'pinned_runs')

        conflict_source = directory / 'conflict-SKILL.md'
        conflict_source.write_text(SKILL.replace('VERSION', versions[1]).replace('DELIVERY', 'Deliver conflicting output'), encoding='utf-8')
        conflict = directory / 'conflict-set'
        run('authoring-export', conflict_source, '--output-dir', conflict)
        refusal = invoke('authoring-publish', conflict, *state_args, expected=1)
        require('immutable' in refusal.stderr and not refusal.stdout and run('workflows', *state_args) == inventory_before
                and all((state / name).read_bytes() == payload for name, payload in published_before.items()), 'immutable_conflict')

        quickstart = run('quickstart', '--skill', sources[1], '--root', directory / 'quickstart')
        require(quickstart['workflow_version'] == versions[1] and quickstart['run_status'] == 'waiting', 'quickstart')
        status, headers, raw = request(command, environment, directory, 'POST', '/api/v1/skill-compiles',
                                       json.dumps({'skill_markdown': sources[1].read_text(encoding='utf-8')}).encode())
        require(status == 200 and headers.get('Cache-Control') == 'no-store'
                and json.loads(raw)['workflow']['workflow']['version'] == versions[1], 'ui')

        invalid_source = directory / 'invalid-SKILL.md'
        invalid_source.write_text(SKILL.replace('VERSION', '../private-version-canary').replace('DELIVERY', 'Deliver output'), encoding='utf-8')
        output = directory / 'must-not-exist'
        refusal = invoke('authoring-export', invalid_source, '--output-dir', output, expected=1)
        require(not output.exists() and not refusal.stdout and refusal.stderr.strip() == 'Invalid Skill workflow version declaration', 'invalid_source')
    return {'ok': True, 'installed': executable is not None, 'checks': checks}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path)
    print(json.dumps(qualify(parser.parse_args().executable)))
